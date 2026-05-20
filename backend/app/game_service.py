import asyncio
import json
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chess
from fastapi import HTTPException

from app.logging_service import LoggingService
from app.persistence import (
    delete_game_file,
    ensure_dir,
    list_game_files,
    load_game_file,
    save_game,
)
from app.players import Player, PlayerError, PlayerFactory
from app.schemas import CreateGameRequest, GameState, GameSummary, PlayerConfig


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
        return self.board.is_game_over(claim_draw=self._claim_draw)

    def result(self) -> str | None:
        return self.board.result(claim_draw=self._claim_draw) if self.is_over() else None

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
    ):
        self._player_factory = player_factory
        self._game: Game | None = None
        from app.config import BACKEND_DIR
        self._games_dir: Path = games_dir if games_dir is not None else BACKEND_DIR / "games"
        ensure_dir(self._games_dir)
        self._logging = logging_service or LoggingService(self._games_dir)

    async def create_game(self, request: CreateGameRequest) -> GameState:
        if self._game is not None:
            await self._game.close_players()
        try:
            self._player_factory.validate_config(request.white)
            self._player_factory.validate_config(request.black)
            created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            game_id = uuid.uuid4().hex
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
            )
        except PlayerError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            await game.start_players()
        except Exception as exc:
            await game.close_players()
            raise HTTPException(status_code=502, detail=f"Failed to start player: {exc}") from exc

        self._game = game
        self._persist(game)
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
        )
        self._game = game
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
            await self._publish(game)

        self._schedule_bot_turns(game)
        return game.state()

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
                        self._record_game_end(game)
                        await game.close_players()
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

            try:
                move = await player.get_move(board, last_san=last_san)
            except Exception as exc:
                await self._publish_error(game, str(exc))
                self._logging.close_agent_turn(game.game_id, None)
                return

            async with game.lock:
                if game.is_over() or game.player_to_move().is_human:
                    self._logging.close_agent_turn(game.game_id, None)
                    return
                self._push_move(game, move)
                await self._publish(game)

            self._logging.close_agent_turn(game.game_id, move.uci())

    def _push_uci_move(self, game: Game, move_uci: str) -> None:
        try:
            move = chess.Move.from_uci(move_uci)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Move must be valid UCI notation.") from exc
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
        )

    def _record_game_end(self, game: Game) -> None:
        result = game.result()
        white_type = game.white_config.type
        black_type = game.black_config.type
        opponent = (
            f"maia-{game.black_config.elo}" if black_type == "maia"
            else black_type
        )
        model = os.getenv("SKILL_AGENT_OPENAI_MODEL", "") if white_type == "agent" else ""
        self._logging.record_game(
            game_id=game.game_id,
            white_type=white_type,
            black_type=black_type,
            opponent=opponent,
            result=result,
            model=model,
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

    async def _publish_error(self, game: Game, message: str) -> None:
        payload = f"event: error\ndata: {json.dumps({'message': message})}\n\n"
        for queue in list(game.subscribers):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                game.subscribers.discard(queue)

    def _event_payload(self, game: Game) -> str:
        return f"event: state\ndata: {game.state().model_dump_json()}\n\n"
