"""Game review engine — chess.com-style analysis built on local Stockfish + this
experiment's own mechanical detector stack.

Quick use:

    from app.review import review_game, write_review
    review = review_game(moves=["e2e4", "e7e5", ...])      # or pgn="..."
    write_review(review)                                   # -> games/reviews/<id>.json

Or from the CLI:

    python -m app.review.cli --pgn game.pgn
    python -m app.review.cli --game-json backend/games/<folder>/<id>.json

Output (per move): eval before/after (cp + win%), centipawn loss, win% lost, accuracy,
a quality label (brilliant…blunder), the engine's best move + line, and the mechanical
"why" (situation/priority, salient features, and — for mistakes — what the move allowed
the opponent + the better line). Plus per-player accuracy / CPL / label counts / worst
moments / weakness tags, and a batch aggregate (`aggregate_weaknesses`).
"""

from app.review.reviewer import review_game
from app.review.io import (
    write_review, load_reviews, aggregate_weaknesses, write_aggregate,
)

__all__ = [
    "review_game", "write_review", "load_reviews",
    "aggregate_weaknesses", "write_aggregate",
]
