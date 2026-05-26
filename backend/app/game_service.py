import asyncio
import json
import logging
import os
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import chess
from fastapi import HTTPException

if TYPE_CHECKING:
    from app.eval_service import EvalService

logger = logging.getLogger(__name__)

from app.logging_service import LoggingService
from app.persistence import (
    delete_game_file,
    ensure_dir,
    existing_subfolder,
    list_game_files,
    load_game_file,
    save_game,
)
from app.players import AgentResignedError, Player, PlayerError, PlayerFactory
from app.schemas import CreateGameRequest, GameState, GameSummary, PlayerConfig


# Per-move Stockfish probe: shallow + time-capped so it doesn't slow games
# meaningfully. The UX-facing advantage needle uses the configured depth
# unchanged; this is a separate, log-only call.
_PER_MOVE_STOCKFISH_TIME_MS = 200

# Path to the chess-player skill's _eval.py — we import its `evaluate` for
# the static per-move eval. We do this lazily because the skill directory
# is technically optional (a backend without the skill should still serve
# games); when missing, static_cp_before/after will be None.
_EVAL_HELPERS_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "chess-player"
    / "scripts"
    / "_eval.py"
)
_static_eval_fn: Callable[[chess.Board], dict] | None = None


def _static_eval_cp(board: chess.Board) -> int | None:
    """Return the chess-player skill's material+PST eval as centipawns,
    white-positive. Returns None if the helper isn't available."""
    global _static_eval_fn
    if _static_eval_fn is None:
        if not _EVAL_HELPERS_PATH.exists():
            return None
        import importlib.util

        spec = importlib.util.spec_from_file_location("_eval", _EVAL_HELPERS_PATH)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules["_eval"] = module
        spec.loader.exec_module(module)
        _static_eval_fn = module.evaluate
    try:
        result = _static_eval_fn(board)
        return int(result["score"])
    except Exception:
        logger.exception("static eval failed")
        return None


def color_name(color: chess.Color) -> str:
    return "white" if color == chess.WHITE else "black"


@dataclass
class Game:
    game_id: str
    board: chess.Board
    white_config: PlayerConfig
    black_config: PlayerConfig
    white_player: Player
    black_player: Player
    created_at: str
    uci_moves: list[str] = field(default_factory=list)
    san_moves: list[str] = field(default_factory=list)
    subscribers: set[asyncio.Queue[str]] = field(default_factory=set)
    agent_event_subscribers: set[asyncio.Queue[str]] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    task: asyncio.Task[None] | None = None
    paused: bool = False
    eval_cp: int | None = None
    eval_mate: int | None = None
    # Optional batch coupling — see BatchService. Empty string for ad-hoc games.
    batch_id: str = ""
    batch_name: str = ""
    # Agent ELO snapshot used for CSV provenance. Strings so an empty value
    # serialises cleanly to "".
    agent_elo_before: str = ""
    agent_elo_after: str = ""
    # Set when a player exception aborts the game mid-play. Non-empty value
    # means "game did not finish naturally"; recorded in games.csv and
    # signals the batch runner not to update ELO for this game.
    aborted_reason: str = ""
    # When set, overrides the python-chess board result — used for resignation
    # paths where the game ended for a reason the board doesn't know about
    # (e.g. agent_resigned_no_move sets result_override="0-1"). is_over() and
    # result() honour it. See decisions/2026-05-25-agent-resigns-when-stuck.md.
    result_override: str | None = None
    # Forced-draw cap. When the half-move count reaches this limit the game
    # is declared a draw (1/2-1/2) regardless of position. Prevents infinite
    # endgames where neither bot can deliver mate. Default 150 = 75 full moves.
    max_half_moves: int = 150
    # Subfolder under ``games_dir`` where this game's JSON lives. Resolved
    # once at game creation by ``folder_resolver.resolve_target_folder`` so
    # every write during the game lands in the same place even if git state
    # changes mid-play. Empty for legacy code paths and tests.
    subfolder: str = ""

    def player_to_move(self) -> Player:
        return self.white_player if self.board.turn == chess.WHITE else self.black_player

    @property
    def _claim_draw(self) -> bool:
        # chess.com does not auto-claim 3-fold repetition or 50-move draws,
        # so if we claim them on the host the two sides desync. For chesscom
        # games we only end on mandatory terminations (mate, stalemate,
        # 5-fold, 75-move, insufficient material).
        has_chesscom = self.white_config.type == "chesscom" or self.black_config.type == "chesscom"
        return not has_chesscom

    def is_over(self) -> bool:
        if self.result_override is not None:
            return True
        if len(self.uci_moves) >= self.max_half_moves:
            return True
        return self.board.is_game_over(claim_draw=self._claim_draw)

    def result(self) -> str | None:
        if self.result_override is not None:
            return self.result_override
        if not self.is_over():
            return None
        if len(self.uci_moves) >= self.max_half_moves and not self.board.is_game_over(claim_draw=self._claim_draw):
            return "1/2-1/2"
        return self.board.result(claim_draw=self._claim_draw)

    def outcome(self):
        return self.board.outcome(claim_draw=self._claim_draw)

    async def close_players(self) -> None:
        for player in (self.white_player, self.black_player):
            if hasattr(player, "close"):
                try:
                    await player.close()
                except Exception:
                    pass

    async def start_players(self) -> None:
        for player in (self.white_player, self.black_player):
            if hasattr(player, "start"):
                await player.start()

    def state(self) -> GameState:
        outcome = self.outcome()
        result = outcome.result() if outcome else None
        termination = outcome.termination.name if outcome else None
        return GameState(
            game_id=self.game_id,
            fen=self.board.fen(),
            turn=color_name(self.board.turn),
            white=self.white_config,
            black=self.black_config,
            legal_moves=[move.uci() for move in self.board.legal_moves],
            uci_moves=self.uci_moves,
            san_moves=self.san_moves,
            status="finished" if result else "active",
            result=result,
            termination=termination,
            eval_cp=self.eval_cp,
            eval_mate=self.eval_mate,
            paused=self.paused,
        )

    def summary(self) -> GameSummary:
        result = self.result()
        return GameSummary(
            game_id=self.game_id,
            white=self.white_config,
            black=self.black_config,
            status="finished" if result else "active",
            result=result,
            turn=color_name(self.board.turn),
            move_count=len(self.uci_moves),
            last_move_san=self.san_moves[-1] if self.san_moves else None,
            created_at=self.created_at,
        )


class GameService:
    def __init__(
        self,
        player_factory: PlayerFactory,
        games_dir: Path | None = None,
        logging_service: LoggingService | None = None,
        eval_service: "EvalService | None" = None,
    ):
        self._player_factory = player_factory
        self._game: Game | None = None
        from app.config import BACKEND_DIR
        self._games_dir: Path = games_dir if games_dir is not None else BACKEND_DIR / "games"
        ensure_dir(self._games_dir)
        self._logging = logging_service or LoggingService(self._games_dir)
        self._eval = eval_service
        # Callback fired when a game finishes naturally (game-over detected in
        # the bot loop). Used by BatchRunner to advance the batch. Receives
        # the finished Game.
        self._on_game_finished: Callable[[Game], None] | None = None

    def set_on_game_finished(self, cb: Callable[[Game], None] | None) -> None:
        self._on_game_finished = cb

    async def cancel_current_game(self) -> None:
        """Forcibly end the active game (used when a batch is stopped).

        Cancels the bot-loop task, closes player resources, clears the game
        slot. The on-game-finished callback will not fire because we don't
        go through the normal game-over branch.
        """
        game = self._game
        if game is None:
            return
        logger.info("cancel_current_game · %s", game.game_id[:8])
        if game.task is not None and not game.task.done():
            game.task.cancel()
            try:
                await game.task
            except (asyncio.CancelledError, Exception):
                pass
        await game.close_players()
        self._game = None
        logger.info("cancel_current_game · cleared")

    def set_paused(self, paused: bool) -> bool:
        """Pause/resume the active game. Returns the new state."""
        game = self._game
        if game is None:
            return False
        game.paused = paused
        if not paused:
            # Resuming kicks the bot loop in case it had stopped at a pause.
            self._schedule_bot_turns(game)
        # Publish so the UI sees the new flag.
        asyncio.create_task(self._publish(game))
        return paused

    async def create_game(self, request: CreateGameRequest) -> GameState:
        logger.info("create_game · white=%s black=%s%s",
                    request.white.type,
                    request.black.type,
                    f" (elo {request.black.elo})" if request.black.elo is not None else "")
        if self._game is not None:
            logger.info("create_game · closing prior game %s", self._game.game_id[:8])
            await self._game.close_players()
        try:
            self._player_factory.validate_config(request.white)
            self._player_factory.validate_config(request.black)
            created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            game_id = uuid.uuid4().hex
            from app.folder_resolver import resolve_target_folder
            subfolder = resolve_target_folder().folder
            game = Game(
                game_id=game_id,
                board=chess.Board(),
                white_config=request.white,
                black_config=request.black,
                white_player=self._player_factory.create(
                    request.white,
                    game_id=game_id,
                    event_sink=lambda evt, gid=game_id: self._on_agent_event(gid, evt),
                ),
                black_player=self._player_factory.create(
                    request.black,
                    game_id=game_id,
                    event_sink=lambda evt, gid=game_id: self._on_agent_event(gid, evt),
                ),
                created_at=created_at,
                subfolder=subfolder,
            )
        except PlayerError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            await game.start_players()
        except Exception as exc:
            logger.exception("create_game · failed to start players: %s", exc)
            await game.close_players()
            raise HTTPException(status_code=502, detail=f"Failed to start player: {exc}") from exc

        self._game = game
        logger.info("create_game · started %s", game.game_id[:8])
        self._persist(game)
        asyncio.create_task(self._update_eval(game))
        self._schedule_bot_turns(game)
        return game.state()

    async def load_game(self, game_id: str) -> GameState:
        try:
            data = load_game_file(self._games_dir, game_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Game not found.")
        board = chess.Board()
        for uci in data["uci_moves"]:
            board.push(chess.Move.from_uci(uci))
        white_config = PlayerConfig(**data["white"])
        black_config = PlayerConfig(**data["black"])

        has_chesscom = white_config.type == "chesscom" or black_config.type == "chesscom"
        game_over = board.is_game_over(claim_draw=not has_chesscom)
        if has_chesscom and not game_over:
            raise HTTPException(
                status_code=400,
                detail="Active chess.com games cannot be resumed — start a new game.",
            )

        if self._game is not None:
            await self._game.close_players()

        try:
            white_player = self._player_factory.create(
                white_config,
                game_id=data["game_id"],
                event_sink=lambda evt, gid=data["game_id"]: self._on_agent_event(gid, evt),
            )
            black_player = self._player_factory.create(
                black_config,
                game_id=data["game_id"],
                event_sink=lambda evt, gid=data["game_id"]: self._on_agent_event(gid, evt),
            )
        except PlayerError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        game = Game(
            game_id=data["game_id"],
            board=board,
            white_config=white_config,
            black_config=black_config,
            white_player=white_player,
            black_player=black_player,
            created_at=data["created_at"],
            uci_moves=list(data["uci_moves"]),
            san_moves=list(data["san_moves"]),
            subfolder=existing_subfolder(self._games_dir, data["game_id"]),
        )
        self._game = game
        asyncio.create_task(self._update_eval(game))
        if not game_over:
            self._schedule_bot_turns(game)
        return game.state()

    def list_summaries(self) -> list[GameSummary]:
        summaries = []
        for data in list_game_files(self._games_dir):
            try:
                board = chess.Board()
                for uci in data["uci_moves"]:
                    board.push(chess.Move.from_uci(uci))
                result = board.result(claim_draw=True) if board.is_game_over(claim_draw=True) else None
                san_moves = data["san_moves"]
                summaries.append(GameSummary(
                    game_id=data["game_id"],
                    white=PlayerConfig(**data["white"]),
                    black=PlayerConfig(**data["black"]),
                    status="finished" if result else "active",
                    result=result,
                    turn=color_name(board.turn),
                    move_count=len(data["uci_moves"]),
                    last_move_san=san_moves[-1] if san_moves else None,
                    created_at=data["created_at"],
                ))
            except Exception:
                pass
        return summaries

    async def delete(self, game_id: str) -> None:
        try:
            delete_game_file(self._games_dir, game_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Game not found.")
        if self._game is not None and self._game.game_id == game_id:
            await self._game.close_players()
            self._game = None

    async def shutdown(self) -> None:
        if self._game is not None:
            await self._game.close_players()
            self._game = None

    def get_current_state(self) -> GameState:
        return self._get_current_game().state()

    def get_state(self, game_id: str) -> GameState:
        return self._get_game(game_id).state()

    async def submit_current_human_move(self, move_uci: str) -> GameState:
        return await self._submit_human_move(self._get_current_game(), move_uci)

    async def submit_human_move(self, game_id: str, move_uci: str) -> GameState:
        return await self._submit_human_move(self._get_game(game_id), move_uci)

    async def submit_agent_move(self, game_id: str, move_uci: str) -> GameState:
        """Apply a move submitted by the agent script (no is_human check).

        Called via POST /api/games/{id}/agent-move from make_move.py.
        The agent's turn is running inside AgentPlayer.get_move(), which holds
        no lock — so we can acquire it here safely.
        """
        game = self._get_game(game_id)
        async with game.lock:
            if game.is_over():
                raise HTTPException(status_code=400, detail="Game is already finished.")
            if game.board.turn != chess.WHITE or game.white_config.type != "agent":
                raise HTTPException(
                    status_code=400,
                    detail="It is not the agent's turn.",
                )
            self._push_uci_move(game, move_uci)
            asyncio.create_task(self._update_eval(game))
            await self._publish(game)
        return game.state()

    async def subscribe_current(self) -> asyncio.Queue[str]:
        return await self._subscribe(self._get_current_game())

    def unsubscribe_current(self, queue: asyncio.Queue[str]) -> None:
        if self._game is not None:
            self._game.subscribers.discard(queue)

    async def subscribe(self, game_id: str) -> asyncio.Queue[str]:
        return await self._subscribe(self._get_game(game_id))

    def unsubscribe(self, game_id: str, queue: asyncio.Queue[str]) -> None:
        game = self._game
        if game is not None and game.game_id == game_id:
            game.subscribers.discard(queue)

    def get_past_agent_events(self, game_id: str) -> list[dict]:
        """Return all events from completed turns for this game. Used to replay
        history when a new SSE subscriber connects mid-game."""
        return self._logging.get_past_agent_events(game_id)

    async def subscribe_agent_events(self, game_id: str) -> asyncio.Queue[str]:
        game = self._get_game(game_id)
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=200)
        game.agent_event_subscribers.add(queue)
        return queue

    def unsubscribe_agent_events(self, game_id: str, queue: asyncio.Queue[str]) -> None:
        game = self._game
        if game is not None and game.game_id == game_id:
            game.agent_event_subscribers.discard(queue)

    # ── Internal ──────────────────────────────────────────────────────────

    def _on_agent_event(self, game_id: str, event: dict[str, Any]) -> None:
        """Called from AgentPlayer (sync context) to fan-out agent events."""
        game = self._game
        if game is None or game.game_id != game_id:
            return
        self._logging.append_agent_event(game_id, event)
        payload = f"event: agent\ndata: {json.dumps(event)}\n\n"
        stale: list[asyncio.Queue[str]] = []
        for queue in game.agent_event_subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                stale.append(queue)
        for q in stale:
            game.agent_event_subscribers.discard(q)

    async def _submit_human_move(self, game: Game, move_uci: str) -> GameState:
        async with game.lock:
            if game.is_over():
                raise HTTPException(status_code=400, detail="Game is already finished.")
            if not game.player_to_move().is_human:
                raise HTTPException(status_code=400, detail=f"It is {color_name(game.board.turn)}'s turn, and that player is not human.")
            self._push_uci_move(game, move_uci)
            asyncio.create_task(self._update_eval(game))
            await self._publish(game)

        self._schedule_bot_turns(game)
        return game.state()

    async def _record_per_move_evals(
        self,
        game_id: str,
        *,
        board_after: chess.Board,
        static_cp_before: int | None,
        stockfish_before_task: asyncio.Task | None,
        move_time_ms: int,
    ) -> None:
        """Capture Stockfish + static eval before/after for one agent move.

        The "before" Stockfish task was kicked off in parallel with the agent's
        thinking so its wall-clock cost is hidden behind the model. The "after"
        evaluation is sequential — short (~200ms) and runs only after the move
        has applied. Exceptions are logged and treated as None values rather
        than aborting the turn."""
        static_cp_after = _static_eval_cp(board_after)
        stockfish_cp_before: int | None = None
        stockfish_cp_after: int | None = None

        if stockfish_before_task is not None:
            try:
                stockfish_cp_before = (await stockfish_before_task).get("cp")
            except Exception:
                logger.exception("stockfish before-eval failed")

        if self._eval is not None:
            try:
                after_eval = await self._eval.evaluate(
                    board_after, time_limit_ms=_PER_MOVE_STOCKFISH_TIME_MS
                )
                stockfish_cp_after = after_eval.get("cp")
            except Exception:
                logger.exception("stockfish after-eval failed")

        self._logging.record_move_evals(
            game_id,
            stockfish_cp_before=stockfish_cp_before,
            stockfish_cp_after=stockfish_cp_after,
            static_cp_before=static_cp_before,
            static_cp_after=static_cp_after,
            move_time_ms=move_time_ms,
        )

    async def _update_eval(self, game: Game) -> None:
        """Compute a fresh stockfish evaluation and publish the new state."""
        if self._eval is None:
            return
        try:
            board_copy = game.board.copy(stack=False)
            result = await self._eval.evaluate(board_copy)
        except Exception:
            return
        # Skip if the game moved on (we don't want a stale eval to clobber a
        # newer one — naive sequencing, but evals take ~100-300ms and the bot
        # loop is sequential so racing in practice is rare).
        if self._game is not game or game.board.fen() != board_copy.fen():
            return
        game.eval_cp = result.get("cp")
        game.eval_mate = result.get("mate")
        await self._publish(game)

    async def _subscribe(self, game: Game) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=20)
        game.subscribers.add(queue)
        await queue.put(self._event_payload(game))
        return queue

    def _get_current_game(self) -> Game:
        if self._game is None:
            raise HTTPException(status_code=404, detail="No game has been created.")
        return self._game

    def _get_game(self, game_id: str) -> Game:
        game = self._game
        if game is None or game.game_id != game_id:
            raise HTTPException(status_code=404, detail="Game not found.")
        return game

    def _schedule_bot_turns(self, game: Game) -> None:
        if game.task is None or game.task.done():
            game.task = asyncio.create_task(self._run_until_human_or_finished(game))

    async def _run_until_human_or_finished(self, game: Game) -> None:
        while True:
            async with game.lock:
                if game.is_over() or game.player_to_move().is_human:
                    if game.is_over():
                        logger.info("game over · %s result=%s moves=%d",
                                    game.game_id[:8], game.result(), len(game.uci_moves))
                        # Pre-CSV hook: lets BatchRunner stamp ELO updates
                        # onto the Game before the row is written.
                        if self._on_game_finished is not None:
                            try:
                                self._on_game_finished(game)
                            except Exception:
                                logger.exception("on_game_finished callback failed")
                        self._record_game_end(game)
                        await game.close_players()
                    return
                if game.paused:
                    return
                player = game.player_to_move()
                board = game.board.copy(stack=False)
                move_number = len(game.uci_moves) + 1

            last_san = game.san_moves[-1] if game.san_moves else None

            # Open agent turn logging before releasing lock
            if not player.is_human:
                prompt = (
                    f"Opponent played {last_san}.\n\nCurrent position (FEN):\n{board.fen()}"
                    if last_san else
                    f"Game start.\n\nCurrent position (FEN):\n{board.fen()}"
                )
                self._logging.start_agent_turn(game.game_id, move_number, prompt)

            # Per-move eval telemetry: capture the static "before" eval now
            # (cheap, can't fail). Stockfish "before" is captured below in
            # parallel with the agent's thinking so we don't add wall-clock
            # latency to the turn. For non-agent players these stay None.
            board_before = board
            static_cp_before: int | None = None
            stockfish_eval_before_task: asyncio.Task | None = None
            move_start = time.monotonic()
            if not player.is_human:
                static_cp_before = _static_eval_cp(board_before)
                if self._eval is not None:
                    stockfish_eval_before_task = asyncio.create_task(
                        self._eval.evaluate(board_before, time_limit_ms=_PER_MOVE_STOCKFISH_TIME_MS)
                    )

            try:
                move = await player.get_move(board, last_san=last_san)
            except AgentResignedError as exc:
                # Capability failure → resignation. White (the agent) loses by
                # forfeit. The batch runner sees a normal chess loss via the
                # result_override; aborted_reason preserves the forensic detail.
                # See decisions/2026-05-25-agent-resigns-when-stuck.md.
                logger.warning("resign · %s agent could not commit a move: %s",
                               game.game_id[:8], exc)
                override = "0-1" if game.white_config.type == "agent" else "1-0"
                await self._finish_game_with_error(
                    game,
                    publish_message=f"Agent resigned: {exc}",
                    aborted_reason="agent_resigned_no_move",
                    result_override=override,
                )
                return
            except Exception as exc:
                # Infrastructure / environmental error — no chess result, no
                # ELO change. result_override stays None so game.result()
                # returns None and BatchRunner skips the ELO update.
                logger.exception("move · %s player %s raised: %s",
                                 game.game_id[:8], type(player).__name__, exc)
                reason = str(exc) or type(exc).__name__
                await self._finish_game_with_error(
                    game,
                    publish_message=str(exc),
                    aborted_reason=reason,
                )
                return

            async with game.lock:
                # The agent may have already committed the move via the
                # /agent-move HTTP endpoint while ``get_move`` was awaiting.
                # If that move ended the game (mate, stalemate, draw), the
                # board now reflects it but the game-over branch at the top
                # of the loop hasn't run yet. Close this agent turn with the
                # committed move (so the per-move evals attach to the right
                # turn) and loop back; the next iteration's ``is_over`` check
                # will fire ``_record_game_end`` and the batch handler.
                already_applied = len(game.uci_moves) >= move_number
                if already_applied:
                    logger.info("move · %s already applied by agent script, skipping push",
                                game.game_id[:8])
                elif game.is_over() or game.player_to_move().is_human:
                    # Game finished while the agent was thinking (e.g. opponent
                    # resigned through a side channel) or control switched to a
                    # human player. Close the turn without recording the move.
                    self._logging.close_agent_turn(game.game_id, None)
                    return
                else:
                    logger.info("move · %s %s (%s) move=%s",
                                game.game_id[:8],
                                "white" if game.board.turn == chess.WHITE else "black",
                                type(player).__name__,
                                move.uci())
                    self._push_move(game, move)
                move_time_ms = int((time.monotonic() - move_start) * 1000)
                board_after = game.board.copy(stack=False)
                # Kick off an evaluation in the background; don't block the loop.
                asyncio.create_task(self._update_eval(game))
                await self._publish(game)

            self._logging.close_agent_turn(game.game_id, move.uci())

            # Per-move eval logging — runs after close_agent_turn so the turn
            # entry exists for record_move_evals to attach to. No-op for human
            # players (no turn to attach to).
            if not player.is_human:
                await self._record_per_move_evals(
                    game.game_id,
                    board_after=board_after,
                    static_cp_before=static_cp_before,
                    stockfish_before_task=stockfish_eval_before_task,
                    move_time_ms=move_time_ms,
                )

    def _push_uci_move(self, game: Game, move_uci: str) -> None:
        try:
            move = chess.Move.from_uci(move_uci)
        except ValueError:
            try:
                move = game.board.parse_san(move_uci)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid move '{move_uci}': not valid UCI (e.g. e2e4) or SAN (e.g. Nf3).",
                ) from exc
        # chess.com's driver auto-queens (autoPromote=true). If the opponent is
        # chess.com and the agent picked an underpromotion, force it to queen
        # so host and browser stay in sync.
        if move.promotion and move.promotion != chess.QUEEN:
            opponent = game.black_config if game.board.turn == chess.WHITE else game.white_config
            if opponent.type == "chesscom":
                move = chess.Move(move.from_square, move.to_square, promotion=chess.QUEEN)
        if move not in game.board.legal_moves:
            raise HTTPException(status_code=400, detail=f"Illegal move: {move_uci}")
        self._push_move(game, move)

    def _push_move(self, game: Game, move: chess.Move) -> None:
        san = game.board.san(move)
        game.board.push(move)
        game.uci_moves.append(move.uci())
        game.san_moves.append(san)
        self._persist(game)

    def _persist(self, game: Game) -> None:
        result = game.result()
        save_game(
            self._games_dir,
            game_id=game.game_id,
            white=game.white_config.model_dump(),
            black=game.black_config.model_dump(),
            uci_moves=list(game.uci_moves),
            san_moves=list(game.san_moves),
            status="finished" if result else "active",
            result=result,
            created_at=game.created_at,
            # Agent ELO snapshot for this game. These are populated by the
            # batch runner ([before] at game start; [after] when the game
            # finishes and ELO settles). Older games where the agent was
            # never given an ELO will omit the field entirely.
            agent_elo_before=getattr(game, "agent_elo_before", "") or None,
            agent_elo_after=getattr(game, "agent_elo_after", "") or None,
            subfolder=game.subfolder,
        )

    def _record_game_end(self, game: Game) -> None:
        # Only agent games are logged. Lobby agent games and batch agent games
        # both end up in the CSVs; `LoggingService.record_game` decides ranked
        # vs experimental based on the live git state. Human-vs-Maia ad-hoc
        # games are not part of the experiment record.
        white_type = game.white_config.type
        black_type = game.black_config.type
        if white_type != "agent" and black_type != "agent":
            return

        from app.repo_state import agent_model, agent_temperature

        result = game.result()
        opponent = (
            f"maia-{game.black_config.elo}" if black_type == "maia"
            else (f"chesscom-{game.black_config.elo}" if black_type == "chesscom"
                  else black_type)
        )
        opponent_elo = (
            str(game.black_config.elo)
            if black_type in ("maia", "chesscom") and game.black_config.elo is not None
            else ""
        )
        self._logging.record_game(
            game_id=game.game_id,
            white_type=white_type,
            black_type=black_type,
            opponent=opponent,
            opponent_elo=opponent_elo,
            result=result,
            model=agent_model(),
            temperature=agent_temperature(),
            batch_id=game.batch_id,
            batch_name=getattr(game, "batch_name", ""),
            elo_before=getattr(game, "agent_elo_before", ""),
            elo_after=getattr(game, "agent_elo_after", ""),
            aborted_reason=getattr(game, "aborted_reason", ""),
        )

    async def _publish(self, game: Game) -> None:
        payload = self._event_payload(game)
        stale: list[asyncio.Queue[str]] = []
        for queue in game.subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                stale.append(queue)
        for queue in stale:
            game.subscribers.discard(queue)

    async def _finish_game_with_error(
        self,
        game: Game,
        *,
        publish_message: str,
        aborted_reason: str,
        result_override: str | None = None,
    ) -> None:
        """Terminate a game that ended badly mid-turn.

        Two callers: the AgentResignedError path (result_override set, ELO
        updates as a loss) and the generic exception path (result_override
        None, game logged as aborted with ELO unchanged). Either way we close
        the agent-turn log, fire the on-game-finished callback so the batch
        advances, write the CSV row, and tear down players.
        """
        await self._publish_error(game, publish_message)
        self._logging.close_agent_turn(game.game_id, None)
        game.aborted_reason = aborted_reason
        if result_override is not None:
            game.result_override = result_override
        if self._on_game_finished is not None:
            try:
                self._on_game_finished(game)
            except Exception:
                logger.exception("on_game_finished callback failed during error finish")
        self._record_game_end(game)
        await game.close_players()

    async def _publish_error(self, game: Game, message: str) -> None:
        payload = f"event: error\ndata: {json.dumps({'message': message})}\n\n"
        for queue in list(game.subscribers):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                game.subscribers.discard(queue)

    def _event_payload(self, game: Game) -> str:
        return f"event: state\ndata: {game.state().model_dump_json()}\n\n"
