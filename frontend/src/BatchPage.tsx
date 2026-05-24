import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  createBatch,
  deleteBatch,
  getActiveBatch,
  getAgentElo,
  listBatches,
  pauseBatch,
  resetAgentElo,
  startBatch,
  stopBatch,
} from './api';
import { RepoStateBanner } from './RepoStateBanner';
import type { AgentElo, Batch, BatchPool, BatchResult } from './types';

function statusLabel(status: Batch['status']): string {
  return status.replace(/^\w/, (c) => c.toUpperCase());
}

function resultChip(result: BatchResult): { label: string; cls: string } {
  if (result === 'win') return { label: 'W', cls: 'chip-win' };
  if (result === 'loss') return { label: 'L', cls: 'chip-loss' };
  if (result === 'draw') return { label: 'D', cls: 'chip-draw' };
  return { label: '–', cls: 'chip-unknown' };
}

function CreateBatchForm({ onCreated }: { onCreated: (b: Batch) => void }) {
  const [label, setLabel] = useState('');
  const [pool, setPool] = useState<BatchPool>('maia');
  const [totalGames, setTotalGames] = useState(10);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const batch = await createBatch(label.trim(), pool, totalGames);
      onCreated(batch);
      setLabel('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create batch.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="new-game-form" onSubmit={submit}>
      <h2>New batch</h2>
      <label>
        Batch name (short label, e.g. "elo calibration")
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="elo calibration"
          maxLength={80}
        />
      </label>
      <div className="player-grid">
        <label>
          Opponent pool
          <select value={pool} onChange={(e) => setPool(e.target.value as BatchPool)}>
            <option value="maia">Maia (1100–1900)</option>
            <option value="chesscom">chess.com (250–3200)</option>
          </select>
        </label>
        <label>
          Number of games
          <input
            type="number"
            min={1}
            max={500}
            value={totalGames}
            onChange={(e) => setTotalGames(Number(e.target.value))}
          />
        </label>
      </div>
      <button type="submit" disabled={busy}>{busy ? 'Creating…' : 'Create batch'}</button>
      {error && <p className="message">{error}</p>}
    </form>
  );
}

function ActiveBatch({
  batch,
  onChanged,
}: {
  batch: Batch;
  onChanged: (b: Batch) => void;
}) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function doAction(action: () => Promise<Batch>) {
    setBusy(true);
    setError('');
    try {
      onChanged(await action());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Action failed.');
    } finally {
      setBusy(false);
    }
  }

  const last10 = batch.games.slice(-10);
  const progressPct = batch.total_games > 0
    ? Math.round((batch.games.length / batch.total_games) * 100)
    : 0;

  const isRunning = batch.status === 'running';
  const isPaused = batch.status === 'paused';
  const isPending = batch.status === 'pending';
  const isTerminal = batch.status === 'completed' || batch.status === 'stopped' || batch.status === 'failed';

  return (
    <section className="batch-active">
      <header className="batch-header">
        <div>
          <h2>{batch.label || '(unnamed batch)'}</h2>
          <p className="batch-subtitle">
            <span className={`batch-status status-${batch.status}`}>{statusLabel(batch.status)}</span>
            {' · '}
            {batch.pool === 'maia' ? 'Maia' : 'chess.com'}
            {' · '}
            game {batch.games.length} of {batch.total_games}
          </p>
        </div>
        <div className="batch-actions">
          {(isPending || isPaused) && (
            <button type="button" onClick={() => doAction(() => startBatch(batch.batch_id))} disabled={busy}>
              ▶ {isPaused ? 'Resume' : 'Start'}
            </button>
          )}
          {isRunning && (
            <button type="button" onClick={() => doAction(() => pauseBatch(batch.batch_id))} disabled={busy}>
              ⏸ Pause
            </button>
          )}
          {!isTerminal && (
            <button
              type="button"
              className="btn-danger"
              onClick={() => {
                if (window.confirm('Stop this batch? It cannot be resumed.')) {
                  void doAction(() => stopBatch(batch.batch_id));
                }
              }}
              disabled={busy}
            >
              ⏹ Stop
            </button>
          )}
        </div>
      </header>

      <div className="batch-progress">
        <div className="progress-bar"><div className="progress-fill" style={{ width: `${progressPct}%` }} /></div>
      </div>

      {batch.current_game_id && (
        <button
          type="button"
          className="btn-ghost batch-current-link"
          onClick={() => navigate(`/games/${batch.current_game_id}`)}
        >
          View current game →
        </button>
      )}

      {batch.last_error && <p className="message">{batch.last_error}</p>}

      {last10.length > 0 && (
        <div className="batch-last10">
          <h3>Last 10 results</h3>
          <div className="result-chips">
            {last10.map((g) => {
              const chip = resultChip(g.result);
              return (
                <span key={g.game_id} className={`result-chip ${chip.cls}`} title={`vs ${g.opponent_elo}, ${g.agent_elo_before.toFixed(0)}→${g.agent_elo_after.toFixed(0)}`}>
                  {chip.label}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {batch.games.length > 0 && (
        <details className="batch-history">
          <summary>All games ({batch.games.length})</summary>
          <table className="batch-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Opp ELO</th>
                <th>Result</th>
                <th>ELO before</th>
                <th>ELO after</th>
                <th>Game</th>
              </tr>
            </thead>
            <tbody>
              {batch.games.map((g, i) => {
                const chip = resultChip(g.result);
                return (
                  <tr key={g.game_id}>
                    <td>{i + 1}</td>
                    <td>{g.opponent_elo}</td>
                    <td><span className={`result-chip ${chip.cls}`}>{chip.label}</span></td>
                    <td>{g.agent_elo_before.toFixed(0)}</td>
                    <td>{g.agent_elo_after.toFixed(0)}</td>
                    <td><Link to={`/games/${g.game_id}`}>{g.game_id.slice(0, 8)}</Link></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </details>
      )}

      {error && <p className="message">{error}</p>}
    </section>
  );
}

export function BatchPage() {
  const navigate = useNavigate();
  const [batches, setBatches] = useState<Batch[]>([]);
  const [active, setActive] = useState<Batch | null>(null);
  const [elo, setElo] = useState<AgentElo | null>(null);
  const [message, setMessage] = useState('');

  async function refresh() {
    try {
      const [b, a, e] = await Promise.all([listBatches(), getActiveBatch(), getAgentElo()]);
      setBatches(b);
      setActive(a);
      setElo(e);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not load batches.');
    }
  }

  useEffect(() => {
    refresh();
    // Lightweight poll so the active batch's progress updates while the
    // backend runs. ~1s is fine because the actual game runs much slower.
    const id = setInterval(refresh, 1500);
    return () => clearInterval(id);
  }, []);

  // Auto-navigate to the live game whenever the active batch advances to a
  // new game. Avoids the user having to click "View current game →" every
  // round. We compare against `active.current_game_id` rather than the URL
  // because we're on /batch, not on /games/<id>.
  useEffect(() => {
    if (active?.current_game_id && active.status === 'running') {
      navigate(`/games/${active.current_game_id}`);
    }
  }, [active?.current_game_id, active?.status, navigate]);

  async function handleResetElo() {
    if (!window.confirm('Reset agent ELO to 1200? This does not affect past batches.')) return;
    try {
      setElo(await resetAgentElo());
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Could not reset ELO.');
    }
  }

  return (
    <main className="lobby">
      <RepoStateBanner />
      <div className="lobby-header">
        <h1>Batches</h1>
        <Link to="/" className="back-link">← Lobby</Link>
      </div>

      <section className="agent-elo-banner">
        <div>
          <span className="agent-elo-label">Agent ELO</span>
          <span className="agent-elo-value">{elo ? elo.elo.toFixed(0) : '—'}</span>
          <span className="agent-elo-meta">
            {elo ? `${elo.games_played} games played` : ''}
            {elo?.last_result ? ` · last: ${elo.last_result}` : ''}
            {elo && elo.streak !== 0 ? ` · streak ${elo.streak > 0 ? '+' : ''}${elo.streak}` : ''}
          </span>
        </div>
        <button type="button" className="btn-ghost" onClick={handleResetElo}>Reset</button>
      </section>

      {active && <ActiveBatch batch={active} onChanged={(b) => { setActive(b); void refresh(); }} />}

      <CreateBatchForm onCreated={(b) => { setBatches((bs) => [b, ...bs]); }} />

      {message && <p className="message">{message}</p>}

      {batches.length === 0 ? (
        <p className="lobby-empty">No batches yet.</p>
      ) : (
        <ul className="game-list">
          {batches.map((b) => (
            <li key={b.batch_id} className="game-row">
              <div className="game-row-info">
                <span className="game-row-players">
                  {b.label || '(unnamed)'} <span className="vs">·</span> {b.pool}
                </span>
                <span className={`game-row-status ${b.status === 'completed' || b.status === 'stopped' ? 'finished' : 'active'}`}>
                  {statusLabel(b.status)} — {b.games.length}/{b.total_games}
                </span>
                <span className="game-row-meta">{new Date(b.created_at).toLocaleString()}</span>
              </div>
              <div className="game-row-actions">
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      setActive(await startBatch(b.batch_id));
                      await refresh();
                    } catch (e) {
                      setMessage(e instanceof Error ? e.message : 'Could not start.');
                    }
                  }}
                  disabled={b.status === 'completed' || b.status === 'stopped' || b.status === 'failed'}
                >
                  {b.status === 'paused' || b.status === 'pending' ? 'Start' : 'View'}
                </button>
                <button
                  type="button"
                  className="btn-danger"
                  onClick={async () => {
                    if (!window.confirm(`Delete batch "${b.label || b.batch_id.slice(0, 8)}"? This cannot be undone.`)) return;
                    try {
                      await deleteBatch(b.batch_id);
                      await refresh();
                    } catch (e) {
                      setMessage(e instanceof Error ? e.message : 'Could not delete.');
                    }
                  }}
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
