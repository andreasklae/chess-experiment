import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Chessground } from 'chessground';
import type { Api } from 'chessground/api';
import type { Config } from 'chessground/config';
import type { Key } from 'chessground/types';
import type { GameState } from './types';

type PromoPiece = 'q' | 'r' | 'b' | 'n';

const PROMO_LABELS: Record<PromoPiece, string> = { q: 'Queen', r: 'Rook', b: 'Bishop', n: 'Knight' };
const PROMO_PIECES: PromoPiece[] = ['q', 'r', 'b', 'n'];

function fenBoard(fen: string): string {
  return fen.split(' ')[0];
}

function legalDests(legalMoves: string[]): Map<Key, Key[]> {
  const dests = new Map<Key, Key[]>();
  for (const move of legalMoves) {
    const from = move.slice(0, 2) as Key;
    const to = move.slice(2, 4) as Key;
    const existing = dests.get(from) ?? [];
    if (!existing.includes(to)) {
      existing.push(to);
    }
    dests.set(from, existing);
  }
  return dests;
}

function isPromotion(legalMoves: string[], from: Key, to: Key): boolean {
  const prefix = `${from}${to}`;
  return legalMoves.some((m) => m.startsWith(prefix) && m.length === 5);
}

function matchingUciMove(legalMoves: string[], from: Key, to: Key, promo?: PromoPiece): string | undefined {
  const prefix = `${from}${to}`;
  if (promo) return legalMoves.find((m) => m === `${prefix}${promo}`);
  return legalMoves.find((m) => m === prefix);
}

export function ChessBoard({ game, canMove, onMove }: { game: GameState | null; canMove: boolean; onMove: (move: string) => void }) {
  const elementRef = useRef<HTMLDivElement | null>(null);
  const apiRef = useRef<Api | null>(null);
  const [pendingPromo, setPendingPromo] = useState<{ from: Key; to: Key } | null>(null);

  const legalMoves = game?.legal_moves ?? [];

  const handleAfterMove = useCallback((from: Key, to: Key) => {
    if (isPromotion(legalMoves, from, to)) {
      setPendingPromo({ from, to });
    } else {
      const move = matchingUciMove(legalMoves, from, to);
      if (move) onMove(move);
    }
  }, [legalMoves, onMove]);

  const handlePromoChoice = useCallback((piece: PromoPiece) => {
    if (!pendingPromo) return;
    const move = matchingUciMove(legalMoves, pendingPromo.from, pendingPromo.to, piece);
    setPendingPromo(null);
    if (move) onMove(move);
  }, [pendingPromo, legalMoves, onMove]);

  const config = useMemo<Config>(() => {
    const activeColor = canMove ? game?.turn : undefined;
    return {
      fen: game ? fenBoard(game.fen) : undefined,
      turnColor: game?.turn,
      viewOnly: false,
      selectable: { enabled: Boolean(game && canMove) },
      draggable: { enabled: Boolean(game && canMove) },
      movable: {
        color: activeColor,
        free: false,
        dests: legalDests(legalMoves),
        showDests: true,
        events: { after: handleAfterMove },
      },
    };
  }, [canMove, game, legalMoves, handleAfterMove]);

  useEffect(() => {
    if (!elementRef.current) return;
    apiRef.current = Chessground(elementRef.current, config);
    const observer = new ResizeObserver(() => {
      apiRef.current?.redrawAll();
    });
    observer.observe(elementRef.current);
    return () => { observer.disconnect(); apiRef.current?.destroy(); apiRef.current = null; };
  }, []);

  useEffect(() => {
    apiRef.current?.set(config);
    apiRef.current?.redrawAll();
  }, [config]);

  return (
    <div className="board-panel">
      <div className="turn-hint">
        {game ? (canMove ? `Move ${game.turn}` : `${game.turn} is controlled by ${game.turn === 'white' ? game.white.type : game.black.type}`) : 'Create a game'}
      </div>
      <div style={{ position: 'relative', display: 'inline-block' }}>
        <div className="board-frame" ref={elementRef} />
        {pendingPromo && (
          <div className="promo-overlay">
            <div className="promo-modal">
              <div className="promo-title">Promote to</div>
              <div className="promo-choices">
                {PROMO_PIECES.map((p) => (
                  <button key={p} className="promo-btn" onClick={() => handlePromoChoice(p)}>
                    {PROMO_LABELS[p]}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
