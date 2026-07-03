import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChessBoard } from './ChessBoard';
import { AgentPanel } from './AgentPanel';
import {
  listPuzzles, startPuzzleRun, abortPuzzleRun, puzzleRunStatus, puzzleRunEventsUrl,
  puzzleProgress, currentGame, gameEventsUrl,
  type PuzzleResult, type PuzzleRunMode, type PuzzleProgressOverview, type PuzzleSet,
} from './api';
import type { GameState } from './types';

interface RunEvent {
  type: string;
  i?: number; n?: number; id?: string; topic?: string; rating?: number;
  band?: string; fen?: string; agent_color?: string;
  title?: string; difficulty?: string; lichess_url?: string;
}

export function PuzzlePage() {
  const [topics, setTopics] = useState<Record<string, number>>({});
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [perTopic, setPerTopic] = useState(4);   // 0 = no cap (all per topic, up to 16)
  const ALL_DIFFS = ['easy', 'medium', 'hard', 'expert'] as const;
  const [difficulties, setDifficulties] = useState<Set<string>>(new Set(ALL_DIFFS));
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<{ i: number; n: number } | null>(null);
  const [current, setCurrent] = useState<RunEvent | null>(null);
  const [results, setResults] = useState<PuzzleResult[]>([]);
  const [game, setGame] = useState<GameState | null>(null);
  const [message, setMessage] = useState('');
  const [mode, setMode] = useState<PuzzleRunMode>('unsolved');
  const puzzleSet: PuzzleSet = 'offensive';  // solving benchmark is offensive-only
  const [prog, setProg] = useState<PuzzleProgressOverview | null>(null);

  const refreshProgress = () =>
    puzzleProgress(puzzleSet).then(setProg).catch(() => {});

  // Reload the topic menu + progress whenever the selected set changes.
  useEffect(() => {
    setSelected(new Set()); setResults([]);
    listPuzzles(puzzleSet).then((d) => { setTopics(d.topics); setTotal(d.total); }).catch((e) => setMessage(String(e)));
    puzzleProgress(puzzleSet).then(setProg).catch(() => {});
  }, [puzzleSet]);

  useEffect(() => {
    puzzleRunStatus().then((s) => {
      setRunning(s.running); setResults(s.results);
      if (s.n) setProgress({ i: s.idx, n: s.n });
    }).catch(() => {});
  }, []);

  // Persistent run-event stream. The backend keeps this open even when idle and
  // attaches to whatever run is current, so a run launched from anywhere (UI,
  // script, API) shows up live with no page refresh. EventSource auto-reconnects
  // on transient errors; we just keep the handler resilient.
  useEffect(() => {
    const src = new EventSource(puzzleRunEventsUrl());
    src.onmessage = (e) => {
      const ev = JSON.parse(e.data) as RunEvent & Partial<PuzzleResult> & { running?: boolean };
      if (ev.type === 'run_started') {
        // A new run began somewhere — clear the old run's results and light up.
        setResults([]); setCurrent(null); setRunning(true);
        if (ev.n) setProgress({ i: 0, n: ev.n });
        setMessage('');
        refreshProgress();
      } else if (ev.type === 'puzzle_begin') {
        setCurrent(ev as RunEvent); setProgress({ i: ev.i ?? 0, n: ev.n ?? 0 }); setRunning(true);
      } else if (ev.type === 'puzzle_result') {
        setResults((r) => [...r.filter((x) => x.puzzle_id !== (ev as PuzzleResult).puzzle_id), ev as unknown as PuzzleResult]);
        refreshProgress();  // persistent overview updates as each puzzle resolves
      } else if (ev.type === 'run_done' || ev.type === 'run_aborted') {
        setRunning(false); setCurrent(null); refreshProgress();
        if (ev.type === 'run_aborted') setMessage('Run aborted');
      }
    };
    src.onerror = () => {};  // EventSource reconnects on its own
    return () => src.close();
  }, []);

  // Safety net: even if an SSE event is missed, poll run-status periodically so
  // a run launched externally is reflected (and a finished run clears). Cheap.
  useEffect(() => {
    const id = setInterval(() => {
      puzzleRunStatus().then((s) => {
        setRunning((was) => {
          if (s.running && !was) { refreshProgress(); }
          return s.running;
        });
        if (s.running && s.n) setProgress({ i: s.idx, n: s.n });
        if (s.results?.length) setResults((r) => (r.length === s.results.length ? r : s.results));
      }).catch(() => {});
    }, 3000);
    return () => clearInterval(id);
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

  // Accurate preview: apply the SAME filters the backend will (topic, difficulty,
  // mode, per-topic cap) over the per-puzzle progress list when we have it.
  const plannedCount = useMemo(() => {
    if (!prog) {
      const chosen = selected.size ? [...selected] : Object.keys(topics);
      const cap = perTopic || 16;
      return chosen.reduce((sum, t) => sum + Math.min(perTopic ? cap : (topics[t] ?? 0), topics[t] ?? 0), 0);
    }
    let pool = prog.puzzles;
    if (selected.size) pool = pool.filter((p) => selected.has(p.topic));
    if (difficulties.size && difficulties.size < ALL_DIFFS.length)
      pool = pool.filter((p) => difficulties.has(p.difficulty));
    if (mode === 'unsolved') pool = pool.filter((p) => p.status !== 'solved');
    else if (mode === 'untested') pool = pool.filter((p) => p.status === 'untested');
    else if (mode === 'failed') pool = pool.filter((p) => p.status === 'failed');
    if (perTopic) {
      const seen: Record<string, number> = {};
      pool = pool.filter((p) => (seen[p.topic] = (seen[p.topic] ?? 0) + 1) <= perTopic);
    }
    return pool.length;
  }, [prog, selected, topics, difficulties, mode, perTopic]);

  const start = async () => {
    try {
      const body: { mode: PuzzleRunMode; set: PuzzleSet; topics?: string[]; difficulties?: string[]; per_topic?: number } = { mode, set: puzzleSet };
      if (selected.size) body.topics = [...selected];
      if (difficulties.size && difficulties.size < ALL_DIFFS.length) body.difficulties = [...difficulties];
      if (perTopic) body.per_topic = perTopic;
      const r = await startPuzzleRun(body);
      setResults([]); setRunning(true); setProgress({ i: 0, n: r.n });
      setMessage(`Started ${r.n} ${puzzleSet} puzzles (${mode})`);
    } catch (e) { setMessage(String(e)); }
  };

  const abort = async () => {
    try {
      const r = await abortPuzzleRun();
      setMessage(`Aborting… (${r.completed} completed)`);
    } catch (e) { setMessage(String(e)); }
  };

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
        <div className="puzzle-modes" role="group" aria-label="Which puzzles to run">
          {([
            ['unsolved', 'Unsolved', prog ? prog.totals.failed + prog.totals.untested : null],
            ['untested', 'Untested', prog?.totals.untested ?? null],
            ['failed', 'Failed only', prog?.totals.failed ?? null],
            ['all', 'All', prog?.totals.total ?? null],
          ] as [PuzzleRunMode, string, number | null][]).map(([m, label, count]) => (
            <button key={m} type="button"
              className={`puzzle-mode-chip${mode === m ? ' is-active' : ''}`}
              onClick={() => setMode(m)} title={`Run ${label.toLowerCase()} puzzles`}>
              {label}{count != null ? <span className="puzzle-chip-count">{count}</span> : null}
            </button>
          ))}
        </div>
        <div className="puzzle-difficulties" role="group" aria-label="Difficulty filter">
          {ALL_DIFFS.map((d) => (
            <button key={d} type="button"
              className={`puzzle-diff-chip ${d}${difficulties.has(d) ? ' is-active' : ''}`}
              onClick={() => setDifficulties((s) => {
                const n = new Set(s); n.has(d) ? n.delete(d) : n.add(d);
                return n.size ? n : new Set(ALL_DIFFS);  // never empty
              })}>
              {d}
            </button>
          ))}
        </div>
        <div className="puzzle-controls">
          <label className="puzzle-slider">
            <span>per topic: <strong>{perTopic === 0 ? 'all' : perTopic}</strong></span>
            <input type="range" min={0} max={16} step={1} value={perTopic}
              onChange={(e) => setPerTopic(Number(e.target.value))} />
          </label>
          <span className="puzzle-plan">
            ≈ <strong>{plannedCount}</strong> puzzle{plannedCount === 1 ? '' : 's'} · mode <strong>{mode}</strong>{selected.size ? ` · ${selected.size} topic${selected.size > 1 ? 's' : ''}` : ''}
          </span>
          <button type="button" className="btn-primary" onClick={start} disabled={running}>
            {running ? 'Running…' : `Run ${mode}${selected.size ? ` · ${selected.size} topic${selected.size > 1 ? 's' : ''}` : ''}`}
          </button>
          {running && (
            <button type="button" className="btn-danger" onClick={abort}>Abort run</button>
          )}
          {selected.size > 0 && (
            <button type="button" className="btn-ghost" onClick={() => setSelected(new Set())}>clear topics</button>
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

      {/* ── live solving view ── reuses the normal game board+agent layout so
           the board never overlaps the reasoning log (game-layout with-agent). */}
      {running && (
        <>
          {current && (
            <div className="puzzle-live-meta">
              <span className="puzzle-live-topic">
                {current.title || current.topic?.replace(/-/g, ' ')}
              </span>
              <span className="puzzle-live-sub">
                {current.difficulty ? `${current.difficulty} · ` : ''}rating {current.rating}
                {' · agent plays '}{current.agent_color}
                {current.lichess_url
                  ? <> · <a href={current.lichess_url} target="_blank" rel="noreferrer">#{current.id}</a></>
                  : <> · #{current.id}</>}
              </span>
            </div>
          )}
          <section className="game-layout with-agent">
            <div className="board-with-eval">
              <ChessBoard game={game} canMove={false} onMove={() => {}} />
            </div>
            {game
              ? <AgentPanel gameId={game.game_id} />
              : <div className="agent-idle">Loading position…</div>}
          </section>
        </>
      )}

      {/* ── persistent progress overview: solved / failed / untested per topic.
           Survives across runs and restarts (from the backend progress store). */}
      {prog && (
        <section className="puzzle-results">
          <div className="puzzle-overview-head">
            <h2>Progress by topic</h2>
            <span className="puzzle-overview-totals">
              <span className="seg solved">{prog.totals.solved} solved</span>
              <span className="seg failed">{prog.totals.failed} failed</span>
              <span className="seg untested">{prog.totals.untested} untested</span>
              <span className="seg total">/ {prog.totals.total}</span>
            </span>
          </div>
          <div className="puzzle-topic-grid">
            {Object.entries(prog.by_topic).sort().map(([t, v]) => {
              const w = (n: number) => `${(100 * n) / v.total}%`;
              return (
                <div key={t} className="puzzle-topic-row" title={`${v.solved} solved · ${v.failed} failed · ${v.untested} untested`}>
                  <span className="puzzle-topic-name">{t.replace(/-/g, ' ')}</span>
                  <div className="puzzle-topic-track stacked">
                    <div className="seg-fill solved" style={{ width: w(v.solved) }} />
                    <div className="seg-fill failed" style={{ width: w(v.failed) }} />
                    <div className="seg-fill untested" style={{ width: w(v.untested) }} />
                  </div>
                  <span className="puzzle-topic-score">
                    {v.solved}/{v.total} solved{v.failed ? ` · ${v.failed} failed` : ''}{v.untested ? ` · ${v.untested} untested` : ''}
                  </span>
                </div>
              );
            })}
          </div>

          {results.length > 0 && <h2>This run — recent attempts</h2>}
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
