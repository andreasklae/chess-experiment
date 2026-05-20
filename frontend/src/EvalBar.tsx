import type { GameState } from './types';

/**
 * Vertical advantage needle. Renders as a tall thin bar next to the board.
 *
 * The bar fills from the bottom (white winning) upward, with black filling
 * from the top downward. A neutral position sits at 50/50. We clamp the
 * centipawn evaluation to ±1000 (10 pawns) for visualisation — the position
 * is already lost long before that, but the bar should saturate cleanly.
 *
 * Mate scores collapse the bar fully to one side.
 */
function whiteFraction(cp: number | null, mate: number | null): number {
  if (mate !== null) {
    return mate > 0 ? 1 : 0;
  }
  if (cp === null) return 0.5;
  const clamped = Math.max(-1000, Math.min(1000, cp));
  // Sigmoid-ish mapping so middle evaluations feel meaningful but extremes
  // saturate. Lichess uses 2 / (1 + exp(-0.004*cp)) - 1.
  const win = 2 / (1 + Math.exp(-0.004 * clamped)) - 1;
  return 0.5 + 0.5 * win;
}

function formatScore(cp: number | null, mate: number | null): string {
  if (mate !== null) {
    if (mate === 0) return mate >= 0 ? '#' : '#';
    return mate > 0 ? `M${mate}` : `-M${Math.abs(mate)}`;
  }
  if (cp === null) return '';
  const pawns = cp / 100;
  return (pawns >= 0 ? '+' : '') + pawns.toFixed(1);
}

export function EvalBar({ game }: { game: GameState | null }) {
  if (!game) {
    return <div className="eval-bar"><div className="eval-bar-fill" style={{ height: '50%' }} /></div>;
  }
  const frac = whiteFraction(game.eval_cp, game.eval_mate);
  const label = formatScore(game.eval_cp, game.eval_mate);
  const whiteOnTop = label.startsWith('+') || label.startsWith('M');
  return (
    <div className="eval-bar" aria-label={`Evaluation: ${label}`}>
      <div className="eval-bar-fill" style={{ height: `${frac * 100}%` }} />
      <div
        className={`eval-bar-label ${whiteOnTop ? 'eval-bar-label-bottom' : 'eval-bar-label-top'}`}
      >
        {label}
      </div>
    </div>
  );
}
