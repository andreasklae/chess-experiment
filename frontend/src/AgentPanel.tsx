import { useEffect, useRef, useState } from 'react';
import { agentEventsUrl } from './api';

interface PromptEntry {
  kind: 'prompt';
  content: string;
}

interface ThinkingEntry {
  kind: 'thinking';
  content: string;
  complete: boolean;
}

interface ToolCallEntry {
  kind: 'tool_call';
  tool: string;
  args: Record<string, unknown>;
}

interface ToolResultEntry {
  kind: 'tool_result';
  tool: string;
  result: unknown;
}

type ChatEntry = PromptEntry | ThinkingEntry | ToolCallEntry | ToolResultEntry;

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
      // run_script wrapper: {"ok": bool, "stdout": "...", "stderr": "..."}
      if (typeof outer === 'object' && 'stdout' in outer) {
        const stdout = (outer.stdout as string).trim();
        // list_legal_moves returns a JSON array
        try {
          const moves = JSON.parse(stdout);
          if (Array.isArray(moves)) {
            return { label: `${moves.length} legal moves`, detail: null };
          }
        } catch { /* not an array */ }
        // make_move returns {"ok": true, "move": "e2e4"}
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

export function AgentPanel({ gameId }: { gameId: string }) {
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const source = new EventSource(agentEventsUrl(gameId));

    source.addEventListener('agent', (e) => {
      const event = JSON.parse((e as MessageEvent).data) as Record<string, unknown>;

      setEntries((prev) => {
        const next = [...prev];

        if (event.type === 'prompt') {
          next.push({ kind: 'prompt', content: event.content as string });
        } else if (event.type === 'text_delta') {
          const last = next[next.length - 1];
          if (last?.kind === 'thinking' && !last.complete) {
            next[next.length - 1] = { ...last, content: last.content + (event.content as string) };
          } else {
            next.push({ kind: 'thinking', content: event.content as string, complete: false });
          }
        } else if (event.type === 'tool_call') {
          const last = next[next.length - 1];
          if (last?.kind === 'thinking' && !last.complete) {
            next[next.length - 1] = { ...last, complete: true };
          }
          next.push({ kind: 'tool_call', tool: event.tool as string, args: (event.args as Record<string, unknown>) ?? {} });
        } else if (event.type === 'tool_result') {
          next.push({ kind: 'tool_result', tool: event.tool as string, result: event.result });
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
          if (entry.kind === 'prompt') {
            return (
              <div key={i} className="agent-entry agent-prompt">
                <span className="entry-label">prompt</span>
                <span className="entry-text">{entry.content}</span>
              </div>
            );
          }
          if (entry.kind === 'thinking') {
            return (
              <div key={i} className={`agent-entry agent-thinking${entry.complete ? ' complete' : ' streaming'}`}>
                <span className="entry-label">thinking</span>
                <span className="entry-text">
                  {entry.content}
                  {!entry.complete && <span className="cursor" aria-hidden="true" />}
                </span>
              </div>
            );
          }
          if (entry.kind === 'tool_call') {
            return (
              <div key={i} className="agent-entry agent-tool-call">
                <span className="entry-label">tool</span>
                <code className="entry-text">⚙ {friendlyToolCall(entry.tool, entry.args)}</code>
              </div>
            );
          }
          if (entry.kind === 'tool_result') {
            const { label, detail } = friendlyToolResult(entry.tool, entry.result);
            return (
              <div key={i} className="agent-entry agent-tool-result">
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
