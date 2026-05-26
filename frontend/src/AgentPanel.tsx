import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { agentEventsUrl } from './api';

// ── Entry model ───────────────────────────────────────────────────────────
//
// Each agent event becomes one entry in the feed. Text deltas accumulate into
// a single ReasoningEntry (or PostMoveEntry, if make_move has already been
// called this turn) until the next tool_call marks it complete.

interface TurnEntry { kind: 'turn'; content: string }
interface ReasoningEntry { kind: 'reasoning'; content: string; complete: boolean }
interface PostMoveEntry { kind: 'post-move'; content: string; complete: boolean }
interface ActionEntry { kind: 'action'; tool: string; args: Record<string, unknown> }
interface ResultEntry { kind: 'result'; tool: string; toolCallArgs: Record<string, unknown>; result: unknown }
interface BudgetWarningEntry { kind: 'budget-warning'; toolCalls: number; threshold: number; maxTurns: number }

type ChatEntry = TurnEntry | ReasoningEntry | PostMoveEntry | ActionEntry | ResultEntry | BudgetWarningEntry;

// Gemma 4 wraps its chain of thought in `<|channel>thought ... <channel|>`
// markers. They arrive split across multiple streaming tokens, so we strip on
// the accumulated content at render time rather than per-delta.
function stripGemmaChannelMarkers(text: string): string {
  return text
    .replace(/<\|channel\|?>thought\s*/g, '')
    .replace(/<channel\|?>\s*/g, '');
}

// ── Tool call / result presentation ───────────────────────────────────────

function friendlyToolCall(tool: string, args: Record<string, unknown>): string {
  if (tool === 'use_skill') return `use_skill(${args.skill_name ?? ''})`;
  if (tool !== 'run_script') return tool;

  const file = args.filename as string | undefined;
  const scriptArgs = (args.args as string | undefined) ?? '';
  const uci = scriptArgs.match(/--uci\s+(\S+)/)?.[1];

  if (file === 'list_legal_moves.py') return 'list_legal_moves()';
  if (file === 'show_position.py') return 'show_position()';
  if (file === 'imagine_move.py') return uci ? `imagine_move(${uci})` : 'imagine_move()';
  if (file === 'make_move.py') return uci ? `make_move(${uci})` : `make_move(${scriptArgs})`;
  return file ?? tool;
}

interface ScriptOutput { stdout: string; stderr: string; ok: boolean }

/** Pull stdout/stderr/ok out of a possibly-stringified script-runner result.
 *  Returns null if the result isn't a recognisable script envelope. */
function extractScriptOutput(result: unknown): ScriptOutput | null {
  if (typeof result !== 'string') return null;
  try {
    const outer = JSON.parse(result);
    if (typeof outer === 'object' && outer && 'stdout' in outer) {
      const o = outer as { stdout?: unknown; stderr?: unknown; ok?: unknown };
      return {
        stdout: ((o.stdout as string) ?? '').trim(),
        stderr: ((o.stderr as string) ?? '').trim(),
        ok: o.ok !== false,
      };
    }
  } catch { /* not JSON */ }
  return null;
}

interface FriendlyResult {
  label: string;
  detail: string | null;
  /** When set, renders with ReactMarkdown. Takes precedence over `pre`. */
  markdown: string | null;
  /** Multi-line plain text rendered in a <pre> block. Fallback for raw output. */
  pre: string | null;
}

const MD: (label: string, markdown: string) => FriendlyResult =
  (label, markdown) => ({ label, detail: null, markdown, pre: null });
const PRE: (label: string, pre: string) => FriendlyResult =
  (label, pre) => ({ label, detail: null, markdown: null, pre });
const TEXT: (label: string, detail?: string | null) => FriendlyResult =
  (label, detail = null) => ({ label, detail, markdown: null, pre: null });

function friendlyToolResult(
  tool: string,
  toolArgs: Record<string, unknown>,
  result: unknown,
): FriendlyResult {
  const file = tool === 'run_script' ? (toolArgs.filename as string | undefined) ?? null : null;
  const script = extractScriptOutput(result);
  const stdout = script?.stdout ?? null;

  if (script && !script.ok) {
    return PRE('error', script.stderr || script.stdout || 'script failed');
  }

  if (file === 'show_position.py' && stdout) return MD('position', stdout);

  if (file === 'imagine_move.py' && stdout) {
    const heading = stdout.split('\n').find((l) => l.startsWith('## Move:'));
    const label = heading?.replace(/^## Move:\s+/, '') ?? 'imagined';
    return MD(label, stdout);
  }

  if (file === 'list_legal_moves.py' && stdout) {
    const count = stdout.split('\n')[0]?.match(/(\d+)\s+legal moves/)?.[1];
    return MD(count ? `${count} legal moves` : 'legal moves', stdout);
  }

  if (file === 'make_move.py' && stdout) {
    try {
      const inner = JSON.parse(stdout);
      if (inner?.ok && inner?.move) return TEXT(`played ${inner.move}`);
      if (inner?.ok === false) return TEXT('error', inner.error ?? stdout);
    } catch { /* fall through to generic */ }
  }

  // Unknown script: render markdown if it looks markdown-shaped, else <pre>.
  if (stdout) {
    const looksMarkdown = /^#{1,6}\s|\n#{1,6}\s|\n\|.+\|/.test(stdout);
    return looksMarkdown ? MD(file ?? 'output', stdout) : PRE(file ?? 'output', stdout);
  }

  // Non-script results (e.g. use_skill returning a plain string).
  if (typeof result === 'string') return TEXT(result.slice(0, 80) || 'done');
  return TEXT(JSON.stringify(result).slice(0, 80));
}

function isMakeMoveCall(event: Record<string, unknown>): boolean {
  if (event.type !== 'tool_call' || event.tool !== 'run_script') return false;
  const args = (event.args as Record<string, unknown> | undefined) ?? {};
  return args.filename === 'make_move.py';
}

// ── Event → entries reducer ───────────────────────────────────────────────
//
// One step of the feed-state reducer, pulled out of the component so it can be
// reasoned about independently. Mutates a fresh copy of `entries` and returns
// it; refs carry one-event-spanning state (was the last tool_call make_move?
// what were the most recent tool_call args?).

interface ReducerRefs {
  moveCommitted: { current: boolean };
  lastToolArgs: { current: Record<string, unknown> };
}

function applyEvent(
  prev: ChatEntry[],
  event: Record<string, unknown>,
  refs: ReducerRefs,
): ChatEntry[] {
  const next = [...prev];
  const type = event.type;

  if (type === 'prompt') {
    refs.moveCommitted.current = false;
    next.push({ kind: 'turn', content: event.content as string });
    return next;
  }

  if (type === 'text_delta') {
    const raw = event.content as string;
    if (!raw) return next;
    // Accumulate into a streaming reasoning entry. The backend strips Gemma
    // channel markers before emitting `thinking` events, but `text_delta`
    // events carry raw tokens (including marker-only sequences). We strip at
    // render time via stripGemmaChannelMarkers; don't push empty-marker-only
    // deltas as new entries — just let them accumulate silently.
    const targetKind: 'reasoning' | 'post-move' = refs.moveCommitted.current ? 'post-move' : 'reasoning';
    const last = next[next.length - 1];
    if ((last?.kind === targetKind) && !last.complete) {
      next[next.length - 1] = { ...last, content: last.content + raw };
    } else {
      next.push({ kind: targetKind, content: raw, complete: false });
    }
    return next;
  }

  if (type === 'thinking') {
    // Backend-accumulated and marker-stripped reasoning block. Emitted once per
    // logical reasoning segment (after stripping Gemma's channel markers); if
    // content is empty after stripping, the backend suppresses the event.
    const content = event.content as string;
    if (!content) return next;
    const targetKind: 'reasoning' | 'post-move' = refs.moveCommitted.current ? 'post-move' : 'reasoning';
    const last = next[next.length - 1];
    if ((last?.kind === targetKind) && !last.complete) {
      // Merge into existing incomplete reasoning entry.
      next[next.length - 1] = { ...last, content: last.content + content, complete: true };
    } else {
      next.push({ kind: targetKind, content, complete: true });
    }
    return next;
  }

  if (type === 'tool_call') {
    const last = next[next.length - 1];
    if ((last?.kind === 'reasoning' || last?.kind === 'post-move') && !last.complete) {
      next[next.length - 1] = { ...last, complete: true };
    }
    if (isMakeMoveCall(event)) refs.moveCommitted.current = true;
    const args = (event.args as Record<string, unknown>) ?? {};
    refs.lastToolArgs.current = args;
    next.push({ kind: 'action', tool: event.tool as string, args });
    return next;
  }

  if (type === 'tool_result') {
    next.push({
      kind: 'result',
      tool: event.tool as string,
      toolCallArgs: refs.lastToolArgs.current,
      result: event.result,
    });
    return next;
  }

  if (type === 'budget_warning') {
    next.push({
      kind: 'budget-warning',
      toolCalls: (event.tool_calls as number) ?? 0,
      threshold: (event.threshold as number) ?? 0,
      maxTurns: (event.max_turns as number) ?? 0,
    });
    return next;
  }

  return next;
}

// ── Render helpers ────────────────────────────────────────────────────────
//
// Reasoning and post-move entries differ only by label/className, so share the
// streaming-markdown render.

function StreamingMarkdown({ content, complete, label, className }: {
  content: string; complete: boolean; label: string; className: string;
}) {
  const stripped = stripGemmaChannelMarkers(content);
  // Don't render marker-only entries that strip to nothing.
  if (!stripped.trim() && complete) return null;
  return (
    <div className={`agent-entry ${className}${complete ? ' complete' : ' streaming'}`}>
      <span className="entry-label">{label}</span>
      <div className="entry-text markdown-body">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{stripped}</ReactMarkdown>
        {!complete && <span className="cursor" aria-hidden="true" />}
      </div>
    </div>
  );
}

// ── Component ─────────────────────────────────────────────────────────────

export function AgentPanel({ gameId }: { gameId: string }) {
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  // Refs survive setState batching and don't trigger re-renders. They carry
  // state that spans events: which tool was called last, and whether the move
  // has been committed (text after that point is post-hoc commentary).
  const moveCommittedRef = useRef(false);
  const lastToolArgsRef = useRef<Record<string, unknown>>({});

  useEffect(() => {
    // Reset feed and refs when switching games — the EventSource for the new
    // game will replay history from the SSE endpoint.
    setEntries([]);
    moveCommittedRef.current = false;
    lastToolArgsRef.current = {};

    const source = new EventSource(agentEventsUrl(gameId));
    const refs: ReducerRefs = { moveCommitted: moveCommittedRef, lastToolArgs: lastToolArgsRef };

    source.addEventListener('agent', (e) => {
      const event = JSON.parse((e as MessageEvent).data) as Record<string, unknown>;
      setEntries((prev) => applyEvent(prev, event, refs));
    });

    return () => source.close();
  }, [gameId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  return (
    <aside className="agent-panel" aria-label="Agent activity">
      <h2>Agent</h2>
      <div className="agent-feed">
        {entries.length === 0 && <p className="agent-idle">Waiting for agent turn…</p>}
        {entries.map((entry, i) => {
          switch (entry.kind) {
            case 'turn':
              return (
                <div key={i} className="agent-entry agent-turn">
                  <span className="entry-label">turn</span>
                  <span className="entry-text">{entry.content}</span>
                </div>
              );

            case 'reasoning':
              return <StreamingMarkdown key={i}
                content={entry.content} complete={entry.complete}
                label="reasoning" className="agent-reasoning" />;

            case 'post-move':
              return <StreamingMarkdown key={i}
                content={entry.content} complete={entry.complete}
                label="post-move" className="agent-post-move" />;

            case 'action':
              return (
                <div key={i} className="agent-entry agent-action">
                  <span className="entry-label">action</span>
                  <code className="entry-text">⚙ {friendlyToolCall(entry.tool, entry.args)}</code>
                </div>
              );

            case 'result': {
              const { label, detail, markdown, pre } = friendlyToolResult(
                entry.tool, entry.toolCallArgs, entry.result,
              );
              return (
                <div key={i} className="agent-entry agent-result">
                  <span className="entry-label">result</span>
                  <div className="entry-text">
                    <div>
                      ✓ {label}
                      {detail && <span className="result-detail"> — {detail}</span>}
                    </div>
                    {markdown && (
                      <div className="agent-result-md markdown-body">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
                      </div>
                    )}
                    {!markdown && pre && <pre className="agent-result-pre">{pre}</pre>}
                  </div>
                </div>
              );
            }

            case 'budget-warning':
              return (
                <div key={i} className="agent-entry agent-budget-warning">
                  <span className="entry-label">⚠ budget</span>
                  <span className="entry-text">
                    {entry.toolCalls} of {entry.maxTurns} tool calls used —
                    the next retry (if any) will be reminded to commit.
                  </span>
                </div>
              );
          }
        })}
        <div ref={bottomRef} />
      </div>
    </aside>
  );
}
