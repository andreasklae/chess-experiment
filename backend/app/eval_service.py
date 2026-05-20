"""Stockfish-backed position evaluator for the live advantage needle.

A single long-lived UCI engine is spawned on first use. `evaluate(board)`
returns a dict shaped:

    {"cp": int | None, "mate": int | None}

`cp` is centipawns from White's perspective (positive = White better,
negative = Black better). `mate` is a positive integer if White is mating
in N (small positive = White wins quickly), negative if Black is mating.
Exactly one of `cp`/`mate` is set per call; the other is `None`.

If stockfish is unavailable (binary missing, init fails, runtime error),
all evaluate() calls return `{"cp": None, "mate": None}` silently.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

import chess
import chess.engine


logger = logging.getLogger(__name__)


class EvalService:
    def __init__(self, stockfish_path: str, depth: int) -> None:
        self._path = stockfish_path
        self._depth = depth
        self._engine: chess.engine.SimpleEngine | None = None
        self._unavailable = False
        self._lock = asyncio.Lock()

    def _ensure_engine(self) -> bool:
        if self._engine is not None:
            return True
        if self._unavailable:
            return False
        if shutil.which(self._path) is None and not Path(self._path).exists():
            logger.warning("Stockfish not found at %r; advantage needle disabled.", self._path)
            self._unavailable = True
            return False
        try:
            self._engine = chess.engine.SimpleEngine.popen_uci(self._path)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Stockfish failed to start (%s); advantage needle disabled.", exc)
            self._unavailable = True
            return False

    async def evaluate(self, board: chess.Board) -> dict[str, int | None]:
        """Return {"cp": int|None, "mate": int|None} from White's perspective.

        Runs the blocking python-chess engine call in a thread; serialised
        via a per-service asyncio lock so callers don't trample the engine.
        """
        empty = {"cp": None, "mate": None}
        if board.is_game_over(claim_draw=False):
            return empty
        async with self._lock:
            if not self._ensure_engine():
                return empty
            try:
                info = await asyncio.to_thread(
                    self._engine.analyse,  # type: ignore[union-attr]
                    board.copy(stack=False),
                    chess.engine.Limit(depth=self._depth),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Stockfish evaluation failed (%s); disabling.", exc)
                self._unavailable = True
                try:
                    if self._engine is not None:
                        self._engine.quit()
                except Exception:
                    pass
                self._engine = None
                return empty

        score: chess.engine.PovScore = info["score"]
        white_score = score.white()
        if white_score.is_mate():
            mate = white_score.mate()
            return {"cp": None, "mate": int(mate) if mate is not None else None}
        cp = white_score.score()
        return {"cp": int(cp) if cp is not None else None, "mate": None}

    def close(self) -> None:
        if self._engine is not None:
            try:
                self._engine.quit()
            except Exception:
                pass
            self._engine = None
