"""Move quality classification and accuracy — the chess.com / Lichess-style scoring.

The core idea (Lichess's, which chess.com mirrors): you do NOT classify a move by a
raw centipawn drop, because losing 300cp in an equal position is a disaster while
losing 300cp when already +900 is nothing. Instead you map the engine eval to a
**win probability**, and judge a move by how much win% it threw away. All formulas
here are the published Lichess ones (https://lichess.org/page/accuracy) plus the
standard win%-drop bands used for the inaccuracy/mistake/blunder labels.

Everything is pure arithmetic — no engine, no model — so it is trivially testable and
deterministic. Evals are centipawns from the MOVING player's perspective (positive =
good for the player who just moved); callers convert from White-POV before calling.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Mate scores are folded to a large centipawn value so win% saturates near 0/100.
MATE_CP = 10_000


def cp_from_score(cp: int | None, mate: int | None) -> int:
    """Fold a (cp, mate) engine score into a single centipawn number, clamped.
    A mate-in-N is worth ~MATE_CP (the closer the mate, the more extreme), so win%
    saturates. From whatever POV the inputs are in; sign is preserved."""
    if mate is not None:
        # closer mates slightly more extreme, but all near the saturation rail
        return MATE_CP - max(0, abs(mate)) * 10 if mate > 0 else -(MATE_CP - max(0, abs(mate)) * 10)
    if cp is None:
        return 0
    return max(-MATE_CP, min(MATE_CP, int(cp)))


def win_percent(cp: int) -> float:
    """Centipawns (mover's POV) -> win% in [0, 100]. Lichess's logistic model:
    Win% = 50 + 50 * (2 / (1 + exp(-0.00368208 * cp)) - 1)."""
    cp = max(-MATE_CP, min(MATE_CP, cp))
    return 50.0 + 50.0 * (2.0 / (1.0 + math.exp(-0.00368208 * cp)) - 1.0)


def accuracy_percent(win_before: float, win_after: float) -> float:
    """Per-move accuracy% from the win% the mover had before vs after their move.
    Lichess: 103.1668 * exp(-0.04354 * (winBefore - winAfter)) - 3.1669, clamped to
    [0, 100]. winBefore/winAfter are BOTH from the mover's POV; a move that doesn't
    lose win% scores ~100."""
    drop = max(0.0, win_before - win_after)
    acc = 103.1668 * math.exp(-0.04354 * drop) - 3.1669
    return max(0.0, min(100.0, acc))


def game_accuracy(move_accuracies: list[float]) -> float | None:
    """A player's game accuracy from their per-move accuracies. We use the mean
    (simple, stable, and what most reviewers report); Lichess blends a volatility-
    weighted mean and a harmonic mean, but the plain mean is within a point or two
    and far easier to reason about for our learning use-case."""
    vals = [a for a in move_accuracies if a is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 1)


# ── move classification ────────────────────────────────────────────────────────
# Labels by win% lost (the chess.com / Lichess tiering). A move is judged on the
# win% it threw away vs the position's best move. "Best" is reserved for actually
# playing the engine's top move; "brilliant"/"great" need extra structural tests
# (a sound sacrifice / a found-only-good-move) handled in reviewer.py.

# win% drop thresholds (mover's POV, vs best move)
_INACCURACY = 5.0    # threw away >= 5% win chance
_MISTAKE = 10.0      # >= 10%
_BLUNDER = 20.0      # >= 20%


@dataclass
class MoveQuality:
    label: str          # best | excellent | good | inaccuracy | mistake | blunder | brilliant | great | forced
    win_loss: float     # win% thrown away vs the best move (>= 0)
    cpl: int            # centipawn loss vs the best move (>= 0), mover's POV
    is_best: bool       # the move played == engine's top move


def classify(
    win_before_best: float,
    win_after_played: float,
    cpl: int,
    *,
    is_best: bool,
    only_good_move: bool = False,
    is_sound_sacrifice: bool = False,
    forced: bool = False,
) -> MoveQuality:
    """Classify one move.

    win_before_best  : win% of the position if the BEST move is played (mover POV)
    win_after_played : win% after the move actually PLAYED (mover POV)
    cpl              : centipawn loss vs best (mover POV, >= 0)
    is_best          : played the engine's #1 move
    only_good_move   : the played (best) move was the ONLY non-losing move (=> 'great')
    is_sound_sacrifice: the played (best) move sacrifices material yet stays best (=> 'brilliant')
    forced           : the mover had a single legal move (=> 'forced', not graded)
    """
    win_loss = max(0.0, win_before_best - win_after_played)
    if forced:
        return MoveQuality("forced", win_loss, cpl, is_best)
    if is_best:
        # the move IS best; upgrade to brilliant/great when it was hard to find
        if is_sound_sacrifice:
            return MoveQuality("brilliant", win_loss, cpl, True)
        if only_good_move:
            return MoveQuality("great", win_loss, cpl, True)
        return MoveQuality("best", win_loss, cpl, True)
    if win_loss >= _BLUNDER:
        label = "blunder"
    elif win_loss >= _MISTAKE:
        label = "mistake"
    elif win_loss >= _INACCURACY:
        label = "inaccuracy"
    elif win_loss >= 2.0:
        label = "good"
    else:
        label = "excellent"
    return MoveQuality(label, win_loss, cpl, False)


# canonical label order / weights for summaries
LABELS = ["brilliant", "great", "best", "excellent", "good",
          "inaccuracy", "mistake", "blunder", "forced"]
MISTAKE_LABELS = {"inaccuracy", "mistake", "blunder"}
