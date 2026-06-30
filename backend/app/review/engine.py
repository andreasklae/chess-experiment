"""A small synchronous multi-PV Stockfish wrapper for offline game review.

Separate from `app.eval_service.EvalService` (which is async, single-PV, and tuned for
the live advantage needle): review needs MULTIPV — the ranked top-K moves with evals
at each position — so it can name the best move(s) and score the move actually played
against them. One long-lived engine process, reused across a whole game/batch.

All evals are returned from WHITE's perspective (cp positive = White better), matching
the rest of the codebase; the caller flips to the mover's POV for win%/classification.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

import chess
import chess.engine

logger = logging.getLogger(__name__)


@dataclass
class ScoredMove:
    """One engine candidate at a position, White-POV."""
    move: chess.Move
    san: str
    cp: int | None      # centipawns, White POV (None if mate)
    mate: int | None    # mate-in-N, White POV (None if cp)
    pv: list[str]       # principal variation in SAN (the line the engine expects)


class ReviewEngine:
    """Multi-PV Stockfish, reused across positions. Use as a context manager.

    >>> with ReviewEngine(depth=18, multipv=3) as eng:
    ...     cands = eng.best_moves(board)   # ranked best-first, White POV
    """

    def __init__(self, stockfish_path: str = "stockfish", *, depth: int = 18,
                 multipv: int = 3, threads: int = 1, hash_mb: int = 128) -> None:
        self._path = stockfish_path
        self._depth = depth
        self._multipv = multipv
        self._threads = threads
        self._hash = hash_mb
        self._engine: chess.engine.SimpleEngine | None = None

    # -- lifecycle --------------------------------------------------------------
    def __enter__(self) -> "ReviewEngine":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    @property
    def available(self) -> bool:
        return self._engine is not None

    def open(self) -> bool:
        if self._engine is not None:
            return True
        if shutil.which(self._path) is None and not Path(self._path).exists():
            logger.warning("Stockfish not found at %r; review disabled.", self._path)
            return False
        try:
            self._engine = chess.engine.SimpleEngine.popen_uci(self._path)
            # single-threaded + fixed hash => deterministic, reproducible reviews
            self._engine.configure({"Threads": self._threads, "Hash": self._hash})
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Stockfish failed to start (%s); review disabled.", exc)
            self._engine = None
            return False

    def close(self) -> None:
        if self._engine is not None:
            try:
                self._engine.quit()
            except Exception:
                pass
            self._engine = None

    # -- analysis ---------------------------------------------------------------
    def best_moves(self, board: chess.Board, *, depth: int | None = None,
                   multipv: int | None = None) -> list[ScoredMove]:
        """Ranked candidate moves (best first), White POV. Empty if game over or
        the engine is unavailable."""
        if board.is_game_over(claim_draw=False) or not self.open():
            return []
        k = multipv if multipv is not None else self._multipv
        limit = chess.engine.Limit(depth=depth if depth is not None else self._depth)
        try:
            infos = self._engine.analyse(board.copy(stack=False), limit, multipv=k)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Stockfish analyse failed (%s).", exc)
            self.close()
            return []
        if isinstance(infos, dict):       # multipv=1 returns a single dict
            infos = [infos]
        out: list[ScoredMove] = []
        for info in infos:
            pv_moves = info.get("pv") or []
            if not pv_moves:
                continue
            mv = pv_moves[0]
            score = info["score"].white()
            cp = None if score.is_mate() else score.score()
            mate = score.mate() if score.is_mate() else None
            out.append(ScoredMove(
                move=mv, san=board.san(mv), cp=cp, mate=mate,
                pv=_pv_to_san(board, pv_moves),
            ))
        return out


def _pv_to_san(board: chess.Board, pv: list[chess.Move], max_len: int = 8) -> list[str]:
    """Render a PV (list of Moves) to SAN from `board`, capped for readability."""
    b = board.copy(stack=False)
    out: list[str] = []
    for mv in pv[:max_len]:
        try:
            out.append(b.san(mv))
            b.push(mv)
        except Exception:
            break
    return out
