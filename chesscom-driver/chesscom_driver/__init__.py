"""chesscom_driver — play chess.com Engine bots from Python via Playwright."""

from __future__ import annotations

from .driver import ChessComDriver, GameStart
from .exceptions import (
    ChessComDriverError,
    ChessComGameError,
    ChessComIllegalMove,
    ChessComMoveTimeout,
    ChessComSetupError,
)
from .mapping import (
    MAX_RATING,
    MIN_RATING,
    POSITION_TO_RATING,
    RATING_TO_POSITION,
    available_ratings,
    closest_position,
)
from .player import ChessComPlayer

__all__ = [
    "ChessComDriver",
    "ChessComPlayer",
    "GameStart",
    "ChessComDriverError",
    "ChessComSetupError",
    "ChessComGameError",
    "ChessComIllegalMove",
    "ChessComMoveTimeout",
    "POSITION_TO_RATING",
    "RATING_TO_POSITION",
    "MIN_RATING",
    "MAX_RATING",
    "available_ratings",
    "closest_position",
]

__version__ = "0.1.0"
