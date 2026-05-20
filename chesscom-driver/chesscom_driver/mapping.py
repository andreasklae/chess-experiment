"""Engine bot slider position -> rating table for chess.com /play/computer.

The Engine bot group exposes a 25-step slider (``min=1, max=25, step=1``).
The mapping below was verified empirically by stepping the slider through
every position and reading ``.selected-bot-introduction-rating``.

The step size is not uniform across the full range:

- Positions 1-5  step by 150 (250, 400, 550, 700, 850).
- Positions 5-20 step by 100/150 (850 -> 2400).
- Positions 20-25 jump 100/200/200/200/200 (2400 -> 3200).

This table is intentionally hard-coded; chess.com does not expose the
mapping anywhere queryable and the slider's React state debounces too
aggressively to discover it at runtime.
"""

from __future__ import annotations


POSITION_TO_RATING: dict[int, int] = {
    1: 250,
    2: 400,
    3: 550,
    4: 700,
    5: 850,
    6: 1000,
    7: 1100,
    8: 1200,
    9: 1300,
    10: 1400,
    11: 1500,
    12: 1600,
    13: 1700,
    14: 1800,
    15: 1900,
    16: 2000,
    17: 2100,
    18: 2200,
    19: 2300,
    20: 2400,
    21: 2500,
    22: 2600,
    23: 2800,
    24: 3000,
    25: 3200,
}

RATING_TO_POSITION: dict[int, int] = {rating: pos for pos, rating in POSITION_TO_RATING.items()}

MIN_RATING: int = min(POSITION_TO_RATING.values())
MAX_RATING: int = max(POSITION_TO_RATING.values())


def closest_position(target_elo: int) -> tuple[int, int]:
    """Return ``(position, actual_rating)`` for the bot closest to ``target_elo``.

    Ties (equidistant ratings) prefer the lower rating because the chess.com
    Engine bots tend to play noisily and lower-rated bots are easier to
    survive against without giant variance swings.
    """

    if not POSITION_TO_RATING:  # pragma: no cover - safety net
        raise ValueError("POSITION_TO_RATING is empty")

    best_pos = min(
        POSITION_TO_RATING,
        key=lambda p: (abs(POSITION_TO_RATING[p] - target_elo), POSITION_TO_RATING[p]),
    )
    return best_pos, POSITION_TO_RATING[best_pos]


def available_ratings() -> list[int]:
    """Return all selectable Engine bot ratings in ascending order."""

    return sorted(POSITION_TO_RATING.values())
