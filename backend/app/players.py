import asyncio
import shutil
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any

import chess
import chess.engine

from app.config import Settings
from app.schemas import PlayerConfig

# Optional dependency: the chess.com driver lives in a sibling package and
# imports Playwright at runtime. If it's not installed, "chesscom" players
# simply aren't selectable; everything else keeps working.
try:
    from chesscom_driver import ChessComPlayer as _ChessComPlayerBase
    from chesscom_driver.mapping import available_ratings as _chesscom_ratings
except ImportError:  # pragma: no cover
    _ChessComPlayerBase = None  # type: ignore[assignment]
    _chesscom_ratings = None  # type: ignore[assignment]


def chesscom_available_elos() -> list[int]:
    return _chesscom_ratings() if _chesscom_ratings is not None else []


class PlayerError(RuntimeError):
    """Raised when a player cannot produce a move."""


class Player(ABC):
    is_human = False

    @abstractmethod
    async def get_move(self, board: chess.Board, last_san: str | None = None) -> chess.Move:
        """Return a legal move for the current board."""


class HumanPlayer(Player):
    is_human = True

    async def get_move(self, board: chess.Board, last_san: str | None = None) -> chess.Move:
        raise PlayerError("Human moves must be submitted through the move endpoint.")


class MaiaEngineRunner:
    def __init__(self, settings: Settings):
        self._settings = settings

    def validate_available(self, elo: int) -> None:
        if shutil.which(self._settings.lc0_path) is None and not Path(self._settings.lc0_path).exists():
            raise PlayerError(
                f"Maia requires lc0, but '{self._settings.lc0_path}' was not found. "
                "Set CHESS_LC0_PATH to the lc0 binary."
            )
        weights = self._settings.maia_weight_path(elo)
        if not weights.exists():
            raise PlayerError(
                f"Maia weights for elo {elo} were not found at {weights}. "
                "Set CHESS_MAIA_WEIGHTS_DIR or download maia-{elo}.pb.gz into that directory."
            )

    def play(self, board: chess.Board, elo: int) -> chess.Move:
        self.validate_available(elo)
        command = [self._settings.lc0_path, f"--weights={self._settings.maia_weight_path(elo)}"]
        engine = chess.engine.SimpleEngine.popen_uci(command)
        try:
            result = engine.play(board, chess.engine.Limit(nodes=1))
        finally:
            engine.quit()
        return result.move


class MaiaPlayer(Player):
    def __init__(self, elo: int, runner: MaiaEngineRunner):
        self._elo = elo
        self._runner = runner

    async def get_move(self, board: chess.Board, last_san: str | None = None) -> chess.Move:
        move = await asyncio.to_thread(self._runner.play, board.copy(stack=False), self._elo)
        if move not in board.legal_moves:
            raise PlayerError(f"Maia returned illegal move: {move.uci()}")
        return move


if _ChessComPlayerBase is not None:

    class ChessComPlayer(_ChessComPlayerBase, Player):
        """Player ABC adapter around the chesscom_driver package.

        Uses an ephemeral temp directory as the Chrome user-data dir so every
        game starts with a clean browser state (no leftover SingletonLock,
        no stale tabs). The temp dir is wiped when close() is called.
        """

        def __init__(self, target_elo: int, *, headless: bool, chrome_channel: str):
            self._tempdir = tempfile.mkdtemp(prefix="chesscom-")
            super().__init__(
                target_elo=target_elo,
                user_data_dir=self._tempdir,
                headless=headless,
                chrome_channel=chrome_channel,
            )

        async def close(self) -> None:
            try:
                await super().close()
            finally:
                shutil.rmtree(self._tempdir, ignore_errors=True)


class PlayerFactory:
    def __init__(self, settings: Settings, maia_runner: MaiaEngineRunner | None = None):
        self._settings = settings
        self._maia_runner = maia_runner or MaiaEngineRunner(settings)

    def validate_config(self, config: PlayerConfig) -> None:
        if config.type == "maia":
            assert config.elo is not None
            self._maia_runner.validate_available(config.elo)
        if config.type == "chesscom" and _ChessComPlayerBase is None:
            raise PlayerError(
                "chess.com players require the chesscom-driver package "
                "(pip install -e experiments/chess/chesscom-driver)."
            )

    def create(
        self,
        config: PlayerConfig,
        *,
        game_id: str = "",
        event_sink: Callable[[dict[str, Any]], None] | None = None,
    ) -> Player:
        if config.type == "human":
            return HumanPlayer()
        if config.type == "maia":
            assert config.elo is not None
            return MaiaPlayer(config.elo, self._maia_runner)
        if config.type == "agent":
            from app.agent_player import AgentPlayer
            if not game_id:
                raise PlayerError("AgentPlayer requires a game_id.")
            return AgentPlayer(game_id, event_sink or (lambda _: None))
        if config.type == "chesscom":
            if _ChessComPlayerBase is None:
                raise PlayerError(
                    "chess.com players require the chesscom-driver package."
                )
            assert config.elo is not None
            return ChessComPlayer(
                target_elo=config.elo,
                headless=self._settings.chesscom_headless,
                chrome_channel=self._settings.chesscom_chrome_channel,
            )
        raise PlayerError(f"Unsupported player type: {config.type}")
