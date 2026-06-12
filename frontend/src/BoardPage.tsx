import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AgentPanel } from './AgentPanel';
import { ChessBoard } from './ChessBoard';
import { EvalBar } from './EvalBar';
import { gameEventsUrl, getActiveBatch, getAgentElo, getGame, listGames, loadGame, pauseGame, resumeGame, submitMove } from './api';
import type { AgentElo, Batch, GameState, PlayerConfig } from './types';

function formatPlayer(config: PlayerConfig): string {
  if (config.type === 'maia') return `maia ${config.elo}`;
  if (config.type === 'chesscom') return `chess.com ${config.elo}`;
  if (config.type === 'agent') return 'agent';
  return 'human';
}

function formatTermination(t: string | null): string {
  if (!t) return '';
  return t.toLowerCase().replace(/_/g, ' ');
}

function describeOutcome(game: GameState): { headline: string; detail: string; kind: 'win' | 'draw' } {
  const term = game.termination ?? '';
  if (term === 'CHECKMATE') {
    const winner = game.result === '1-0' ? 'White' : 'Black';
    return { headline: `${winner} wins by checkmate`, detail: game.result ?? '', kind: 'win' };
  }
  const drawReasons: Record<string, string> = {
    STALEMATE: 'Draw by stalemate',
    INSUFFICIENT_MATERIAL: 'Draw by insufficient material',
    SEVENTYFIVE_MOVES: 'Draw by 75-move rule',
    FIVEFOLD_REPETITION: 'Draw by fivefold repetition',
    FIFTY_MOVES: 'Draw by fifty-move rule',
    THREEFOLD_REPETITION: 'Draw by threefold repetition',
  };
  if (term in drawReasons) {
    return { headline: drawReasons[term], detail: game.result ?? '½-½', kind: 'draw' };
  }
  // Decisive result without checkmate label, or unknown termination.
  if (game.result === '1-0' || game.result === '0-1') {
    const winner = game.result === '1-0' ? 'White' : 'Black';
    return { headline: `${winner} wins`, detail: formatTermination(term) || game.result, kind: 'win' };
  }
  return { headline: 'Game over', detail: formatTermination(term) || (game.result ?? ''), kind: 'draw' };
}

export function BoardPage() {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();
  const [game, setGame] = useState<GameState | null>(null);
  const [message, setMessage] = useState('');
  const [agentElo, setAgentElo] = useState<AgentElo | null>(null);
  const [activeBatch, setActiveBatch] = useState<Batch | null>(null);

  useEffect(() => {
    if (!gameId) return;
    // If this game is already the active in-memory game (e.g. just created),
    // GET succeeds and we avoid reloading players. Otherwise fall back to
    // POST /load which instantiates them.
    getGame(gameId)
      .then(setGame)
      .catch(() => loadGame(gameId).then(setGame).catch((e: Error) => setMessage(e.message)));
  }, [gameId]);

  // Poll backend for agent ELO + active batch state. Two purposes:
  //   (1) keep the status bar's ELO and batch-progress fields fresh,
  //   (2) auto-navigate to the next game when the active batch advances.
  useEffect(() => {
    if (!gameId) return undefined;
    let cancelled = false;
    async function tick() {
      try {
        const [active, elo] = await Promise.all([getActiveBatch(), getAgentElo()]);
        if (cancelled) return;
        setActiveBatch(active);
        setAgentElo(elo);
        if (
          active?.current_game_id &&
          active.current_game_id !== gameId &&
          active.status === 'running'
        ) {
          navigate(`/games/${active.current_game_id}`);
          return;
        }
        // No batch driving the board: follow standalone game sequences too
        // (the puzzle runner starts a fresh game the moment one finishes).
        const games = await listGames();
        if (cancelled) return;
        const current = games.find((g) => g.game_id === gameId);
        const nextActive = games.find(
          (g) => g.status === 'active' && g.game_id !== gameId,
        );
        if (nextActive && (!current || current.status === 'finished')) {
          navigate(`/games/${nextActive.game_id}`);
        }
      } catch {
        // ignore — keep polling
      }
    }
    void tick();
    const id = setInterval(tick, 1500);
    return () => { cancelled = true; clearInterval(id); };
  }, [gameId, navigate]);

  // Is the current game part of the active batch? If so we show the
  // batch's game number and label in the status bar.
  const batchForThisGame =
    activeBatch && activeBatch.current_game_id === gameId ? activeBatch : null;
  const batchProgress = batchForThisGame
    ? `${batchForThisGame.games.length + 1}/${batchForThisGame.total_games}`
    : null;

  useEffect(() => {
    if (!game) return undefined;
    const source = new EventSource(gameEventsUrl(game.game_id));
    source.addEventListener('state', (event) => setGame(JSON.parse((event as MessageEvent).data) as GameState));
    source.addEventListener('error', (event) => {
      const data = (event as MessageEvent).data;
      if (data) setMessage(JSON.parse(data).message);
    });
    return () => source.close();
  }, [game?.game_id]);

  const isHumanTurn = useMemo(() => {
    if (!game || game.status === 'finished') return false;
    return (game.turn === 'white' ? game.white : game.black).type === 'human';
  }, [game]);

  const handleMove = useCallback(async (move: string) => {
    if (!game || !isHumanTurn) return;
    setMessage('');
    try {
      setGame(await submitMove(move));
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Could not submit move.');
    }
  }, [game, isHumanTurn]);

  const handlePauseToggle = useCallback(async () => {
    if (!game) return;
    setMessage('');
    try {
      setGame(game.paused ? await resumeGame(game.game_id) : await pauseGame(game.game_id));
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Could not toggle pause.');
    }
  }, [game]);

  const hasAgent = game?.white.type === 'agent' || game?.black.type === 'agent';
  const standardStart = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
  const isPuzzle = Boolean(game && game.initial_fen && game.initial_fen !== standardStart);
  const showPauseControls = Boolean(hasAgent && game && game.status === 'active');

  return (
    <main className="app-shell">
      <section className="setup-panel" aria-label="Game navigation">
        <div className="panel-header">
          <Link to="/" className="back-link">← Games</Link>
          {game && (
            <span className="board-page-title">
              {formatPlayer(game.white)} vs {formatPlayer(game.black)}
            </span>
          )}
        </div>
        {message ? <p className="message">{message}</p> : null}
      </section>

      {game && game.aborted_reason ? (
        <div className="result-banner draw" role="status">
          <span className="result-headline">Game aborted</span>
          <span className="result-detail">{game.aborted_reason}</span>
        </div>
      ) : null}

      {game && game.status === 'finished' && (() => {
        const o = describeOutcome(game);
        return (
          <div className={`result-banner ${o.kind}`} role="status">
            <span className="result-headline">{o.headline}</span>
            {o.detail ? <span className="result-detail">{o.detail}</span> : null}
          </div>
        );
      })()}

      {showPauseControls && (
        <div className="game-controls">
          <button type="button" onClick={handlePauseToggle}>
            {game?.paused ? '▶ Resume' : '⏸ Pause'}
          </button>
          {game?.paused && <span className="paused-indicator">Paused — current turn finishes, then pauses</span>}
        </div>
      )}

      {game && (
        <section className="status-bar" aria-label="Game status">
          <div className="status-bar-item">
            <span className="status-bar-label">Game</span>
            <span className="status-bar-value mono">{game.game_id.slice(0, 8)}</span>
          </div>
          <div className="status-bar-item">
            <span className="status-bar-label">White</span>
            <span className="status-bar-value">{formatPlayer(game.white)}</span>
          </div>
          <div className="status-bar-item">
            <span className="status-bar-label">Black</span>
            <span className="status-bar-value">{formatPlayer(game.black)}</span>
          </div>
          <div className="status-bar-item">
            <span className="status-bar-label">Turn</span>
            <span className="status-bar-value">{game.turn}</span>
          </div>
          <div className="status-bar-item">
            <span className="status-bar-label">Plies</span>
            <span className="status-bar-value mono">
              {game.uci_moves.length}{game.move_cap ? ` / ${game.move_cap}` : ''}
            </span>
          </div>
          {isPuzzle && (
            <div className="status-bar-item">
              <span className="status-bar-label">Mode</span>
              <span className="status-bar-value">puzzle</span>
            </div>
          )}
          <div className="status-bar-item">
            <span className="status-bar-label">Result</span>
            <span className="status-bar-value">
              {game.result ?? game.status}
              {game.termination ? ` · ${formatTermination(game.termination)}` : ''}
            </span>
          </div>
          {hasAgent && (
            <div className="status-bar-item">
              <span className="status-bar-label">Agent ELO</span>
              <span className="status-bar-value mono">
                {agentElo ? agentElo.elo.toFixed(0) : '—'}
              </span>
            </div>
          )}
          {batchForThisGame && (
            <div className="status-bar-item">
              <span className="status-bar-label">Batch</span>
              <span className="status-bar-value">
                {batchProgress}
                {batchForThisGame.label ? ` · ${batchForThisGame.label}` : ''}
              </span>
            </div>
          )}
        </section>
      )}

      <section className={`game-layout${game?.white.type === 'agent' ? ' with-agent' : ''}`}>
        <div className="board-with-eval">
          <EvalBar game={game} />
          <ChessBoard game={game} canMove={isHumanTurn} onMove={handleMove} />
        </div>
        {game?.white.type === 'agent' ? (
          <AgentPanel gameId={game.game_id} />
        ) : (
          <aside className="status-panel" aria-label="Move list">
            <h3>Moves</h3>
            {game ? (
              <ol className="move-list">
                {game.san_moves.map((move, index) => (
                  <li key={`${move}-${index}`}>{move}</li>
                ))}
              </ol>
            ) : (
              <p>Loading game…</p>
            )}
          </aside>
        )}
      </section>
    </main>
  );
}
