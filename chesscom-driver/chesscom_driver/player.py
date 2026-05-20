"""``ChessComPlayer`` — adapter that plugs the driver into a :class:`Player` ABC.

This module deliberately does NOT import the host project's ``Player`` class
to keep the package standalone. Instead it defines a ``PlayerProtocol`` and
its own ``Player`` base. Adapters for specific apps (such as the FastAPI
chess experiment) can subclass or wrap :class:`ChessComPlayer`.

Usage from the chess experiment::

    # in backend/app/players.py
    from chesscom_driver import ChessComPlayer as _Base

    class ChessComPlayer(_Base, Player):
        # The driver-side base already implements get_move() correctly.
        # We only inherit Player to satisfy isinstance checks elsewhere.
        pass

Or simpler — just import :class:`ChessComPlayer` directly; ``Player`` ABCs in
host projects typically only require ``get_move`` to exist with the right
signature, which it does.
"""

from __future__ import annotations

import logging
from pathlib import Path

import chess

from .driver import ChessComDriver, GameStart
from .exceptions import ChessComGameError, ChessComSetupError


logger = logging.getLogger(__name__)


class ChessComPlayer:
    """Player adapter that plays as black against a chess.com Engine bot.

    The agent plays white in the host application; the chess.com bot plays
    black through this adapter. The first call to :meth:`get_move` will:

    1. Lazily launch the browser and start a game at the requested ELO.
    2. Submit the agent's first white move (extracted from ``last_san``).
    3. Wait for chess.com's response and return it.

    Subsequent calls do (2) and (3) only.

    Attributes:
        is_human: Always ``False`` — exists so this matches host ABCs that
            expose ``is_human`` on every player type.
        target_elo: The ELO the caller asked for.
        actual_rating: Set after the first ``get_move`` call; ``None``
            before the game starts.
    """

    is_human: bool = False

    def __init__(
        self,
        target_elo: int,
        *,
        user_data_dir: str | Path,
        headless: bool = False,
        chrome_channel: str = "chrome",
        bot_move_timeout: float = 60.0,
    ) -> None:
        self.target_elo = target_elo
        self.actual_rating: int | None = None
        self._driver = ChessComDriver(
            user_data_dir=user_data_dir,
            headless=headless,
            chrome_channel=chrome_channel,
            bot_move_timeout=bot_move_timeout,
        )
        self._internal_board = chess.Board()
        self._started = False

    async def start(self) -> GameStart:
        """Eagerly launch the browser and start a game. Safe to call once."""
        return await self._ensure_started()

    async def _ensure_started(self) -> GameStart:
        if self._started:
            return GameStart(
                slider_position=-1,
                actual_rating=self.actual_rating or -1,
                target_elo=self.target_elo,
            )
        await self._driver.launch()
        start = await self._driver.start_game(self.target_elo)
        self.actual_rating = start.actual_rating
        self._started = True
        return start

    async def get_move(
        self, board: chess.Board, last_san: str | None = None
    ) -> chess.Move:
        """Return the chess.com bot's reply.

        Contract:
        - ``board`` is the position *before* the bot moves. The bot is to move.
        - ``last_san`` is the SAN of the most recently played move (which must
          be the agent's move, because the bot is to move now). May be ``None``
          only for the very first call when the agent has not yet moved — but
          that case does not arise in this experiment since the agent always
          plays white, so the bot is never to move on move 0.
        """
        await self._ensure_started()

        if last_san is None:
            raise ChessComGameError(
                "ChessComPlayer.get_move called with last_san=None. The agent "
                "must play first (always-white methodology) so the bot always "
                "has an opponent move to reply to."
            )

        # Parse the agent's move using our internal history-aware board, then
        # mirror it onto chess.com.
        try:
            agent_move = self._internal_board.parse_san(last_san)
        except (ValueError, chess.IllegalMoveError) as exc:
            raise ChessComGameError(
                f"Could not parse last_san={last_san!r} on internal board "
                f"(fen={self._internal_board.fen()})"
            ) from exc

        await self._driver.submit_move(agent_move)
        self._internal_board.push(agent_move)

        bot_move = await self._driver.wait_for_bot_move()

        # Validate the returned move against the position the host saw.
        if bot_move not in board.legal_moves:
            # Try to recover by parsing the SAN from history if available.
            raise ChessComGameError(
                f"chess.com returned a move illegal in the host's board: "
                f"move={bot_move.uci()} fen={board.fen()}"
            )
        self._internal_board.push(bot_move)
        return bot_move

    async def close(self) -> None:
        """Shut down the browser. Safe to call multiple times."""
        await self._driver.close()
        self._started = False

    async def __aenter__(self) -> "ChessComPlayer":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()
