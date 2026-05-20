import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { createGame, deleteGame, listGames, playerTypes } from './api';
import type { Color, GameSummary, PlayerConfig, PlayerTypeInfo } from './types';

const defaultElo = 1500;

const chesscomDefaultElo = 850;

function cleanConfig(config: PlayerConfig, info?: PlayerTypeInfo): PlayerConfig {
  if (config.type === 'maia') return { type: 'maia', elo: config.elo ?? defaultElo };
  if (config.type === 'agent') return { type: 'agent' };
  if (config.type === 'chesscom') {
    const allowed = info?.allowed_elos ?? [];
    const elo = config.elo && allowed.includes(config.elo)
      ? config.elo
      : (allowed.includes(chesscomDefaultElo) ? chesscomDefaultElo : (allowed[0] ?? chesscomDefaultElo));
    return { type: 'chesscom', elo };
  }
  return { type: 'human' };
}

function formatPlayer(config: PlayerConfig): string {
  if (config.type === 'maia') return `maia ${config.elo}`;
  if (config.type === 'agent') return 'agent';
  if (config.type === 'chesscom') return `chess.com ${config.elo}`;
  return 'human';
}

function PlayerSelector({
  color,
  config,
  types,
  onChange,
}: {
  color: Color;
  config: PlayerConfig;
  types: PlayerTypeInfo[];
  onChange: (config: PlayerConfig) => void;
}) {
  const maiaInfo = types.find((t) => t.type === 'maia');
  const chesscomInfo = types.find((t) => t.type === 'chesscom');
  // chess.com bots can only play as black; agents can only play as white.
  const availableTypes = types.filter((t) =>
    color === 'white' ? t.type !== 'chesscom' : t.type !== 'agent'
  );
  return (
    <fieldset className="player-box">
      <legend>{color}</legend>
      <label>
        Player
        <select
          value={config.type}
          onChange={(e) => {
            const t = e.target.value as PlayerConfig['type'];
            const info = types.find((ti) => ti.type === t);
            onChange(cleanConfig({ type: t, elo: defaultElo }, info));
          }}
        >
          {availableTypes.map((t) => (
            <option key={t.type} value={t.type}>{t.type}</option>
          ))}
        </select>
      </label>
      {config.type === 'maia' && maiaInfo ? (
        <label>
          Elo
          <select value={config.elo ?? defaultElo} onChange={(e) => onChange({ type: 'maia', elo: Number(e.target.value) })}>
            {maiaInfo.allowed_elos.map((elo) => (
              <option key={elo} value={elo}>{elo}</option>
            ))}
          </select>
        </label>
      ) : null}
      {config.type === 'chesscom' && chesscomInfo ? (
        <label>
          Elo
          <select value={config.elo ?? chesscomDefaultElo} onChange={(e) => onChange({ type: 'chesscom', elo: Number(e.target.value) })}>
            {chesscomInfo.allowed_elos.map((elo) => (
              <option key={elo} value={elo}>{elo}</option>
            ))}
          </select>
        </label>
      ) : null}
    </fieldset>
  );
}

function formatStatus(game: GameSummary): string {
  if (game.status === 'finished') {
    return game.result ?? 'finished';
  }
  return `${game.turn} to move`;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function LobbyPage() {
  const navigate = useNavigate();
  const [games, setGames] = useState<GameSummary[]>([]);
  const [types, setTypes] = useState<PlayerTypeInfo[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [white, setWhite] = useState<PlayerConfig>({ type: 'human' });
  const [black, setBlack] = useState<PlayerConfig>({ type: 'maia', elo: defaultElo });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  async function fetchGames() {
    try {
      setGames(await listGames());
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Could not load games.');
    }
  }

  useEffect(() => {
    Promise.all([listGames(), playerTypes()]).then(([g, t]) => {
      setGames(g);
      setTypes(t);
    }).catch((e: Error) => setMessage(e.message));
  }, []);

  async function handleCreate() {
    setBusy(true);
    const usingChesscom = white.type === 'chesscom' || black.type === 'chesscom';
    setMessage(usingChesscom ? 'Launching chess.com browser… this can take 10–20s.' : '');
    try {
      const whiteInfo = types.find((t) => t.type === white.type);
      const blackInfo = types.find((t) => t.type === black.type);
      const game = await createGame(cleanConfig(white, whiteInfo), cleanConfig(black, blackInfo));
      navigate(`/games/${game.game_id}`);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Could not create game.');
      setBusy(false);
    }
  }

  function handleOpen(gameId: string) {
    setMessage('');
    navigate(`/games/${gameId}`);
  }

  async function handleDelete(gameId: string) {
    if (!window.confirm('Delete this game?')) return;
    setMessage('');
    try {
      await deleteGame(gameId);
      await fetchGames();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Could not delete game.');
    }
  }

  return (
    <main className="lobby">
      <div className="lobby-header">
        <h1>Chess Experiment</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link to="/batch" className="back-link" style={{ alignSelf: 'center' }}>Batches →</Link>
          <button type="button" onClick={() => setShowForm((v) => !v)}>
            {showForm ? 'Cancel' : '+ New Game'}
          </button>
        </div>
      </div>

      {showForm && (
        <div className="new-game-form">
          <div className="player-grid">
            <PlayerSelector color="white" config={white} types={types} onChange={setWhite} />
            <PlayerSelector color="black" config={black} types={types} onChange={setBlack} />
          </div>
          <button type="button" onClick={handleCreate} disabled={busy || types.length === 0}>
            {busy ? 'Creating...' : 'Start game'}
          </button>
        </div>
      )}

      {message ? <p className="message">{message}</p> : null}

      {games.length === 0 ? (
        <p className="lobby-empty">No games yet. Start a new one above.</p>
      ) : (
        <ul className="game-list">
          {games.map((g) => (
            <li key={g.game_id} className="game-row">
              <div className="game-row-info">
                <span className="game-row-players">
                  {formatPlayer(g.white)} <span className="vs">vs</span> {formatPlayer(g.black)}
                </span>
                <span className={`game-row-status ${g.status}`}>{formatStatus(g)}</span>
                <span className="game-row-meta">
                  {g.move_count} move{g.move_count !== 1 ? 's' : ''}
                  {g.last_move_san ? ` · last: ${g.last_move_san}` : ''}
                  {' · '}{formatDate(g.created_at)}
                </span>
              </div>
              <div className="game-row-actions">
                <button type="button" onClick={() => handleOpen(g.game_id)}>Open</button>
                <button type="button" className="btn-danger" onClick={() => handleDelete(g.game_id)}>Delete</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
