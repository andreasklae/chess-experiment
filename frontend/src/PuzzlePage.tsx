import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChessBoard } from './ChessBoard';
import { AgentPanel } from './AgentPanel';
import {
  listPuzzles, startPuzzleRun, puzzleRunStatus, puzzleRunEventsUrl,
  currentGame, gameEventsUrl,
  type PuzzleResult,
} from './api';
import type { GameState } from './types';

interface RunEvent {
  type: string;
  i?: number; n?: number; id?: string; topic?: string; rating?: number;
  band?: string; fen?: string; agent_color?: string;
}

export function PuzzlePage() {
  const [topics, setTopics] = useState<Record<string, number>>({});
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [quick, setQuick] = useState(true);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<{ i: number; n: number } | null>(null);
  const [current, setCurrent] = useState<RunEvent | null>(null);
  const [results, setResults] = useState<PuzzleResult[]>([]);
  const [game, setGame] = useState<GameState | null>(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    listPuzzles().then((d) => { setTopics(d.topics); setTotal(d.total); }).catch((e) => setMessage(String(e)));
    puzzleRunStatus().then((s) => {
      setRunning(s.running); setResults(s.results);
      if (s.n) setProgress({ i: s.idx, n: s.n });
    }).catch(() => {});
  }, []);

  useEffect(() => {
    const src = new EventSource(puzzleRunEventsUrl());
    src.onmessage = (e) => {
      const ev = JSON.parse(e.data) as RunEvent & Partial<PuzzleResult>;
      if (ev.type === 'puzzle_begin') {
        setCurrent(ev as RunEvent); setProgress({ i: ev.i ?? 0, n: ev.n ?? 0 }); setRunning(true);
      } else if (ev.type === 'puzzle_result') {
        setResults((r) => [...r.filter((x) => x.puzzle_id !== (ev as PuzzleResult).puzzle_id), ev as unknown as PuzzleResult]);
      } else if (ev.type === 'run_done') {
        setRunning(false); setCurrent(null);
      }
    };
    src.onerror = () => {};
    return () => src.close();
  }, []);

  // poll the current puzzle game for the live board while running
  useEffect(() => {
    if (!running) { setGame(null); return; }
    let stop = false;
    const tick = () => currentGame().then((g) => { if (!stop) setGame(g); }).catch(() => {});
    tick();
    const id = setInterval(tick, 1200);
    return () => { stop = true; clearInterval(id); };
  }, [running, current?.id]);

  useEffect(() => {
    if (!game) return;
    const src = new EventSource(gameEventsUrl(game.game_id));
    src.addEventListener('state', (e) => setGame(JSON.parse((e as MessageEvent).data) as GameState));
    return () => src.close();
  }, [game?.game_id]);

  const toggle = (t: string) => setSelected((s) => {
    const n = new Set(s); n.has(t) ? n.delete(t) : n.add(t); return n;
  });

  const plannedCount = useMemo(() => {
    const chosen = selected.size ? [...selected] : Object.keys(topics);
    if (quick) return chosen.length * 4;
    return chosen.reduce((sum, t) => sum + (topics[t] ?? 0), 0);
  }, [selected, topics, quick]);

  const start = async () => {
    try {
      const body: { topics?: string[]; limit?: number } = {};
      if (selected.size) body.topics = [...selected];
      if (quick) body.limit = plannedCount;
      const r = await startPuzzleRun(body);
      setResults([]); setRunning(true); setProgress({ i: 0, n: r.n });
      setMessage(`Started ${r.n} puzzles`);
    } catch (e) { setMessage(String(e)); }
  };

  const byTopic = useMemo(() => {
    const m: Record<string, { solved: number; total: number }> = {};
    for (const r of results) {
      const k = r.topic || 'unknown';
      m[k] = m[k] || { solved: 0, total: 0 };
      m[k].total += 1; if (r.solved) m[k].solved += 1;
    }
    return m;
  }, [results]);

  const overall = useMemo(() => {
    const t = results.length, s = results.filter((r) => r.solved).length;
    return { total: t, solved: s, pct: t ? Math.round((100 * s) / t) : 0 };
  }, [results]);

  return (
    <main className="lobby puzzle-page">
      <div className="lobby-header">
        <h1>Puzzle Benchmark</h1>
        <Link to="/" className="back-link">← Lobby</Link>
      </div>

      <p className="puzzle-intro">
        The agent solves Lichess puzzles with its full game machinery — perception
        tools, the knowledge wiki, move-by-move reasoning. <strong>Strict scoring:</strong>{' '}
        every move must match the solution. It is told only “you are X to move,
        find the best move” — no theme, no hint that a tactic exists. {total} puzzles
        across {Object.keys(topics).length} topics &amp; 4 rating bands.
      </p>

      {/* ── launcher ── */}
      <section className="puzzle-launcher">
        <div className="puzzle-topics">
          {Object.entries(topics).sort().map(([t, n]) => (
            <button key={t} type="button"
              className={`puzzle-chip${selected.has(t) ? ' is-selected' : ''}`}
              onClick={() => toggle(t)}>
              {t.replace(/-/g, ' ')} <span className="puzzle-chip-count">{n}</span>
            </button>
          ))}
        </div>
        <div className="puzzle-controls">
          <label className="puzzle-quick">
            <input type="checkbox" checked={quick} onChange={(e) => setQuick(e.target.checked)} />
            quick run (4 / topic)
          </label>
          <span className="puzzle-plan">{plannedCount} puzzle{plannedCount === 1 ? '' : 's'} selected</span>
          <button type="button" className="btn-primary" onClick={start} disabled={running}>
            {running ? 'Running…' : selected.size ? `Run ${selected.size} topic${selected.size > 1 ? 's' : ''}` : 'Run all topics'}
          </button>
          {selected.size > 0 && (
            <button type="button" className="btn-ghost" onClick={() => setSelected(new Set())}>clear</button>
          )}
        </div>
        {message && <p className="puzzle-message">{message}</p>}
      </section>

      {/* ── progress + score banner ── */}
      {(running || results.length > 0) && (
        <section className="puzzle-scorebar">
          <div className="puzzle-score">
            <span className="puzzle-score-value">{overall.solved}/{overall.total}</span>
            <span className="puzzle-score-label">solved ({overall.pct}%)</span>
          </div>
          {progress && (
            <div className="puzzle-progress">
              <div className="puzzle-progress-bar">
                <div className="puzzle-progress-fill"
                  style={{ width: `${progress.n ? (100 * (progress.i + (running ? 0 : 1))) / progress.n : 0}%` }} />
              </div>
              <span className="puzzle-progress-text">
                {progress.i + (running ? 1 : 0)} / {progress.n}
              </span>
            </div>
          )}
        </section>
      )}

      {/* ── live solving view ── */}
      {running && (
        <section className="puzzle-live">
          <div className="puzzle-live-board">
            {current && (
              <div className="puzzle-live-meta">
                <span className="puzzle-live-topic">{current.topic?.replace(/-/g, ' ')}</span>
                <span className="puzzle-live-sub">
                  rating {current.rating} · agent plays {current.agent_color} · #{current.id}
                </span>
              </div>
            )}
            <div className="board-frame">
              <ChessBoard game={game} canMove={false} onMove={() => {}} />
            </div>
          </div>
          <div className="puzzle-live-reasoning">
            {game ? <AgentPanel gameId={game.game_id} /> : <div className="agent-idle">Loading position…</div>}
          </div>
        </section>
      )}

      {/* ── results: per-topic solve rate ── */}
      {Object.keys(byTopic).length > 0 && (
        <section className="puzzle-results">
          <h2>Solve rate by topic</h2>
          <div className="puzzle-topic-grid">
            {Object.entries(byTopic).sort().map(([t, v]) => {
              const pct = Math.round((100 * v.solved) / v.total);
              return (
                <div key={t} className="puzzle-topic-row">
                  <span className="puzzle-topic-name">{t.replace(/-/g, ' ')}</span>
                  <div className="puzzle-topic-track">
                    <div className={`puzzle-topic-fill ${pct >= 67 ? 'good' : pct >= 34 ? 'mid' : 'bad'}`}
                      style={{ width: `${pct}%` }} />
                  </div>
                  <span className="puzzle-topic-score">{v.solved}/{v.total} · {pct}%</span>
                </div>
              );
            })}
          </div>

          <h2>Recent attempts</h2>
          <div className="puzzle-attempts">
            {[...results].reverse().slice(0, 60).map((r) => {
              const wrong = r.attempts.find((a) => !a.correct);
              return (
                <div key={r.puzzle_id} className="puzzle-attempt">
                  <span className={`chip-${r.solved ? 'win' : 'loss'} puzzle-attempt-mark`}>
                    {r.solved ? '✓' : '✗'}
                  </span>
                  <span className="puzzle-attempt-topic">{r.topic.replace(/-/g, ' ')}</span>
                  <span className="puzzle-attempt-meta">#{r.puzzle_id} · r{r.rating} · {r.solved_plies}/{r.total_plies}</span>
                  {!r.solved && wrong && (
                    <span className="puzzle-attempt-fail">
                      played {wrong.played_san || wrong.played_uci || '—'}, expected {wrong.expected_san}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}
    </main>
  );
}
