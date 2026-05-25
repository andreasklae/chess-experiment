import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { agentEventsUrl } from './api';

interface TurnEntry {
  kind: 'turn';
  content: string;
}

interface ReasoningEntry {
  kind: 'reasoning';
  content: string;
  complete: boolean;
}

interface PostMoveEntry {
  kind: 'post-move';
  content: string;
  complete: boolean;
}

interface ActionEntry {
  kind: 'action';
  tool: string;
  args: Record<string, unknown>;
}

interface ResultEntry {
  kind: 'result';
  tool: string;
  toolCallArgs: Record<string, unknown>;
  result: unknown;
}

type ChatEntry = TurnEntry | ReasoningEntry | PostMoveEntry | ActionEntry | ResultEntry;

// Gemma 4 wraps its chain of thought in <|channel>thought ... <channel|> markers.
// Strip the markers; keep the prose between them as the visible reasoning text.
function stripGemmaChannelMarkers(text: string): string {
  return text
    .replace(/<\|channel\|?>thought\s*/g, '')
    .replace(/<channel\|?>\s*/g, '');
}

function scriptFilename(tool: string, args: Record<string, unknown>): string | null {
  if (tool !== 'run_script') return null;
  return (args.filename as string | undefined) ?? null;
}

function friendlyToolCall(tool: string, args: Record<string, unknown>): string {
  if (tool === 'run_script') {
    const file = args.filename as string | undefined;
    const scriptArgs = args.args as string | undefined;
    if (file === 'list_legal_moves.py') return 'list_legal_moves()';
    if (file === 'show_position.py') return 'show_position()';
    if (file === 'imagine_move.py') {
      const m = scriptArgs?.match(/--uci\s+(\S+)/);
      return m ? `imagine_move(${m[1]})` : 'imagine_move()';
    }
    if (file === 'evaluate_position.py') {
      const m = scriptArgs?.match(/--moves\s+(\S+)/);
      return m ? `evaluate_position(${m[1]})` : 'evaluate_position()';
    }
    if (file === 'make_move.py' && scriptArgs) {
      const m = scriptArgs.match(/--uci\s+(\S+)/);
      return m ? `make_move(${m[1]})` : `make_move(${scriptArgs})`;
    }
    return file ?? tool;
  }
  if (tool === 'use_skill') return `use_skill(${args.skill_name ?? ''})`;
  return tool;
}

interface FriendlyResult {
  label: string;
  detail: string | null;
  /** Multi-line text to render in a <pre> block below the label. */
  pre: string | null;
}

interface ScriptOutput {
  stdout: string;
  stderr: string;
  ok: boolean;
}

/** Pull stdout/stderr/ok out of a possibly-stringified script-runner result.
 * Returns null if the result isn't a recognisable script result. */
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
  } catch {
    /* not JSON */
  }
  return null;
}

function extractStdout(result: unknown): string | null {
  return extractScriptOutput(result)?.stdout ?? null;
}

function friendlyToolResult(
  tool: string,
  toolArgs: Record<string, unknown>,
  result: unknown,
): FriendlyResult {
  const file = scriptFilename(tool, toolArgs);
  const scriptOutput = extractScriptOutput(result);
  const stdout = scriptOutput?.stdout ?? null;

  // Script failed: surface stderr so the agent's error is visible.
  if (scriptOutput && !scriptOutput.ok) {
    const errBody = scriptOutput.stderr || scriptOutput.stdout || 'script failed';
    return { label: 'error', detail: null, pre: errBody };
  }

  // show_position prints multi-line text. Always render the full body.
  if (file === 'show_position.py' && stdout !== null) {
    return { label: 'position', detail: null, pre: stdout };
  }

  // imagine_move prints a multi-line tactical report.
  if (file === 'imagine_move.py' && stdout !== null) {
    // Pull the Move: line up as the headline so the feed is scannable.
    const moveLine = stdout.split('\n').find((l) => l.startsWith('Move:'));
    const headline = moveLine?.replace(/^Move:\s+/, '') ?? 'imagined';
    return { label: headline, detail: null, pre: stdout };
  }

  // evaluate_position prints a multi-line summary; show it all.
  if (file === 'evaluate_position.py' && stdout !== null) {
    // Headline is the line starting with "Evaluation:".
    const evalLine = stdout.split('\n').find((l) => l.startsWith('Evaluation:'));
    const headline = evalLine?.replace(/^Evaluation:\s*/, '') ?? 'evaluation';
    return { label: headline, detail: null, pre: stdout };
  }

  // list_legal_moves prints a JSON array of UCI strings.
  if (file === 'list_legal_moves.py' && stdout !== null) {
    try {
      const moves = JSON.parse(stdout);
      if (Array.isArray(moves)) {
        return { label: `${moves.length} legal moves`, detail: null, pre: null };
      }
    } catch { /* fall through */ }
  }

  // make_move prints a JSON object {ok, move, message} or {ok: false, error, ...}.
  if (file === 'make_move.py' && stdout !== null) {
    try {
      const inner = JSON.parse(stdout);
      if (inner?.ok && inner?.move) return { label: `played ${inner.move}`, detail: null, pre: null };
      if (inner?.ok === false) return { label: 'error', detail: inner.error ?? stdout, pre: null };
    } catch { /* fall through */ }
  }

  // Fallback for unknown scripts: show the full stdout so future tools
  // surface their output without needing a frontend change.
  if (stdout !== null) {
    return { label: file ?? 'output', detail: null, pre: stdout || '(empty)' };
  }

  // Non-script tool results: stringify and truncate (existing behaviour).
  if (typeof result === 'string') {
    return { label: result.slice(0, 80) || 'done', detail: null, pre: null };
  }
  return { label: JSON.stringify(result).slice(0, 80), detail: null, pre: null };
}

// True when the given tool_call event is a make_move.py invocation. Text deltas
// that arrive after this is true (within the same turn) are post-hoc commentary,
// not reasoning that informed the move.
function isMakeMoveCall(event: Record<string, unknown>): boolean {
  if (event.type !== 'tool_call') return false;
  if (event.tool !== 'run_script') return false;
  const args = (event.args as Record<string, unknown> | undefined) ?? {};
  return args.filename === 'make_move.py';
}

export function AgentPanel({ gameId }: { gameId: string }) {
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  // Tracks whether make_move.py has been called this turn. Reset on every
  // new `prompt` event (which marks the start of a turn).
  const moveCommittedRef = useRef(false);
  // The args of the most recent tool_call, used to render the matching
  // tool_result (which carries `tool` but not the original args).
  const lastToolArgsRef = useRef<Record<string, unknown>>({});

  useEffect(() => {
    const source = new EventSource(agentEventsUrl(gameId));

    source.addEventListener('agent', (e) => {
      const event = JSON.parse((e as MessageEvent).data) as Record<string, unknown>;

      setEntries((prev) => {
        const next = [...prev];

        if (event.type === 'prompt') {
          moveCommittedRef.current = false;
          next.push({ kind: 'turn', content: event.content as string });
        } else if (event.type === 'text_delta') {
          const cleaned = stripGemmaChannelMarkers(event.content as string);
          if (!cleaned) return next;
          const targetKind: 'reasoning' | 'post-move' = moveCommittedRef.current ? 'post-move' : 'reasoning';
          const last = next[next.length - 1];
          if (last?.kind === targetKind && !last.complete) {
            next[next.length - 1] = { ...last, content: last.content + cleaned };
          } else {
            next.push({ kind: targetKind, content: cleaned, complete: false });
          }
        } else if (event.type === 'tool_call') {
          const last = next[next.length - 1];
          if ((last?.kind === 'reasoning' || last?.kind === 'post-move') && !last.complete) {
            next[next.length - 1] = { ...last, complete: true };
          }
          if (isMakeMoveCall(event)) {
            moveCommittedRef.current = true;
          }
          const args = (event.args as Record<string, unknown>) ?? {};
          lastToolArgsRef.current = args;
          next.push({ kind: 'action', tool: event.tool as string, args });
        } else if (event.type === 'tool_result') {
          next.push({
            kind: 'result',
            tool: event.tool as string,
            toolCallArgs: lastToolArgsRef.current,
            result: event.result,
          });
        }

        return next;
      });
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
          if (entry.kind === 'turn') {
            return (
              <div key={i} className="agent-entry agent-turn">
                <span className="entry-label">turn</span>
                <span className="entry-text">{entry.content}</span>
              </div>
            );
          }
          if (entry.kind === 'reasoning') {
            return (
              <div key={i} className={`agent-entry agent-reasoning${entry.complete ? ' complete' : ' streaming'}`}>
                <span className="entry-label">reasoning</span>
                <div className="entry-text markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.content}</ReactMarkdown>
                  {!entry.complete && <span className="cursor" aria-hidden="true" />}
                </div>
              </div>
            );
          }
          if (entry.kind === 'post-move') {
            return (
              <div key={i} className={`agent-entry agent-post-move${entry.complete ? ' complete' : ' streaming'}`}>
                <span className="entry-label">post-move</span>
                <div className="entry-text markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.content}</ReactMarkdown>
                  {!entry.complete && <span className="cursor" aria-hidden="true" />}
                </div>
              </div>
            );
          }
          if (entry.kind === 'action') {
            return (
              <div key={i} className="agent-entry agent-action">
                <span className="entry-label">action</span>
                <code className="entry-text">⚙ {friendlyToolCall(entry.tool, entry.args)}</code>
              </div>
            );
          }
          if (entry.kind === 'result') {
            const { label, detail, pre } = friendlyToolResult(entry.tool, entry.toolCallArgs, entry.result);
            return (
              <div key={i} className="agent-entry agent-result">
                <span className="entry-label">result</span>
                <div className="entry-text">
                  <div>
                    ✓ {label}
                    {detail && <span className="result-detail"> — {detail}</span>}
                  </div>
                  {pre && <pre className="agent-result-pre">{pre}</pre>}
                </div>
              </div>
            );
          }
          return null;
        })}
        <div ref={bottomRef} />
      </div>
    </aside>
  );
}
