import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { AgentPanel } from './AgentPanel';
import { ChessBoard } from './ChessBoard';
import { gameEventsUrl, getGame, loadGame, submitMove } from './api';
import type { GameState, PlayerConfig } from './types';

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
  const [game, setGame] = useState<GameState | null>(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!gameId) return;
    // If this game is already the active in-memory game (e.g. just created),
    // GET succeeds and we avoid reloading players. Otherwise fall back to
    // POST /load which instantiates them.
    getGame(gameId)
      .then(setGame)
      .catch(() => loadGame(gameId).then(setGame).catch((e: Error) => setMessage(e.message)));
  }, [gameId]);

  useEffect(() => {
    if (!game) return undefined;
    const source = new EventSource(gameEventsUrl());
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

      {game && game.status === 'finished' && (() => {
        const o = describeOutcome(game);
        return (
          <div className={`result-banner ${o.kind}`} role="status">
            <span className="result-headline">{o.headline}</span>
            {o.detail ? <span className="result-detail">{o.detail}</span> : null}
          </div>
        );
      })()}

      <section className={`game-layout${game?.white.type === 'agent' ? ' with-agent' : ''}`}>
        <ChessBoard game={game} canMove={isHumanTurn} onMove={handleMove} />
        <aside className="status-panel" aria-label="Game status">
          <h2>Status</h2>
          {game ? (
            <>
              <dl>
                <dt>Game</dt>
                <dd>{game.game_id.slice(0, 8)}</dd>
                <dt>White</dt>
                <dd>{formatPlayer(game.white)}</dd>
                <dt>Black</dt>
                <dd>{formatPlayer(game.black)}</dd>
                <dt>Turn</dt>
                <dd>{game.turn}</dd>
                <dt>Result</dt>
                <dd>
                  {game.result ?? game.status}
                  {game.termination ? ` (${formatTermination(game.termination)})` : ''}
                </dd>
                <dt>FEN</dt>
                <dd className="fen">{game.fen}</dd>
              </dl>
              <h3>Moves</h3>
              <ol className="move-list">
                {game.san_moves.map((move, index) => (
                  <li key={`${move}-${index}`}>{move}</li>
                ))}
              </ol>
            </>
          ) : (
            <p>Loading game…</p>
          )}
        </aside>
        {game?.white.type === 'agent' && <AgentPanel gameId={game.game_id} />}
      </section>
    </main>
  );
}
