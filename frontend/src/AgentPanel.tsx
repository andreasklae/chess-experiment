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

function friendlyToolCall(tool: string, args: Record<string, unknown>): string {
  if (tool === 'run_script') {
    const file = args.filename as string | undefined;
    const scriptArgs = args.args as string | undefined;
    if (file === 'list_legal_moves.py') return 'list_legal_moves()';
    if (file === 'make_move.py' && scriptArgs) {
      const m = scriptArgs.match(/--uci\s+(\S+)/);
      return m ? `make_move(${m[1]})` : `make_move(${scriptArgs})`;
    }
    return file ?? tool;
  }
  if (tool === 'use_skill') return `use_skill(${args.skill_name ?? ''})`;
  return tool;
}

function friendlyToolResult(tool: string, result: unknown): { label: string; detail: string | null } {
  if (typeof result === 'string') {
    try {
      const outer = JSON.parse(result);
      if (typeof outer === 'object' && 'stdout' in outer) {
        const stdout = (outer.stdout as string).trim();
        try {
          const moves = JSON.parse(stdout);
          if (Array.isArray(moves)) {
            return { label: `${moves.length} legal moves`, detail: null };
          }
        } catch { /* not an array */ }
        try {
          const inner = JSON.parse(stdout);
          if (inner?.ok && inner?.move) {
            return { label: `played ${inner.move}`, detail: null };
          }
          if (inner?.ok === false) {
            return { label: 'error', detail: inner.error ?? stdout };
          }
        } catch { /* not json */ }
        return { label: stdout.slice(0, 80) || 'done', detail: null };
      }
      if (outer?.ok && outer?.move) return { label: `played ${outer.move}`, detail: null };
    } catch { /* not json */ }
    return { label: result.slice(0, 80) || 'done', detail: null };
  }
  return { label: JSON.stringify(result).slice(0, 80), detail: null };
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
          next.push({ kind: 'action', tool: event.tool as string, args: (event.args as Record<string, unknown>) ?? {} });
        } else if (event.type === 'tool_result') {
          next.push({ kind: 'result', tool: event.tool as string, result: event.result });
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
            const { label, detail } = friendlyToolResult(entry.tool, entry.result);
            return (
              <div key={i} className="agent-entry agent-result">
                <span className="entry-label">result</span>
                <span className="entry-text">
                  ✓ {label}
                  {detail && <span className="result-detail"> — {detail}</span>}
                </span>
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
