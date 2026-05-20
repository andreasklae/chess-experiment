import asyncio
import shutil
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.game_service import GameService
from app.players import PlayerFactory
from app.schemas import CHESSCOM_ELOS, CreateGameRequest, GameState, GameSummary, HealthResponse, MAIA_ELOS, MoveRequest, PlayerTypeInfo


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    fastapi_app.state.game_service = build_game_service()
    try:
        yield
    finally:
        await fastapi_app.state.game_service.shutdown()


app = FastAPI(title="Chess Experiment Backend", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def build_game_service() -> GameService:
    settings = get_settings()
    return GameService(PlayerFactory(settings), games_dir=settings.games_dir)


SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_game_service() -> GameService:
    return app.state.game_service


GameServiceDep = Annotated[GameService, Depends(get_game_service)]


@app.get("/api/health")
async def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        ok=True,
        lc0_path=settings.lc0_path,
        lc0_found=shutil.which(settings.lc0_path) is not None,
        maia_weights_dir=str(settings.maia_weights_dir),
    )


@app.get("/api/player-types")
async def player_types() -> list[PlayerTypeInfo]:
    return [
        PlayerTypeInfo(type="human", elo_required=False),
        PlayerTypeInfo(type="maia", elo_required=True, allowed_elos=list(MAIA_ELOS)),
        PlayerTypeInfo(type="agent", elo_required=False),
        PlayerTypeInfo(type="chesscom", elo_required=True, allowed_elos=list(CHESSCOM_ELOS)),
    ]


@app.get("/api/games")
async def list_games(service: GameServiceDep) -> list[GameSummary]:
    return service.list_summaries()


@app.post("/api/games")
async def create_game(request: CreateGameRequest, service: GameServiceDep) -> GameState:
    return await service.create_game(request)


@app.get("/api/game")
async def get_current_game(service: GameServiceDep) -> GameState:
    return service.get_current_state()


@app.get("/api/games/{game_id}")
async def get_game(game_id: str, service: GameServiceDep) -> GameState:
    return service.get_state(game_id)


@app.post("/api/games/{game_id}/load")
async def load_game(game_id: str, service: GameServiceDep) -> GameState:
    return await service.load_game(game_id)


@app.delete("/api/games/{game_id}", status_code=204)
async def delete_game(game_id: str, service: GameServiceDep) -> Response:
    await service.delete(game_id)
    return Response(status_code=204)


@app.post("/api/game/moves")
async def submit_current_move(request: MoveRequest, service: GameServiceDep) -> GameState:
    return await service.submit_current_human_move(request.move)


@app.post("/api/games/{game_id}/moves")
async def submit_move(game_id: str, request: MoveRequest, service: GameServiceDep) -> GameState:
    return await service.submit_human_move(game_id, request.move)


@app.get("/api/game/events")
async def current_game_events(service: GameServiceDep) -> StreamingResponse:
    queue = await service.subscribe_current()

    async def stream() -> AsyncIterator[str]:
        try:
            while True:
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=20)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            service.unsubscribe_current(queue)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/games/{game_id}/events")
async def game_events(game_id: str, service: GameServiceDep) -> StreamingResponse:
    queue = await service.subscribe(game_id)

    async def stream() -> AsyncIterator[str]:
        try:
            while True:
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=20)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            service.unsubscribe(game_id, queue)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/games/{game_id}/agent-events")
async def agent_events(game_id: str, service: GameServiceDep) -> StreamingResponse:
    queue = await service.subscribe_agent_events(game_id)

    async def stream() -> AsyncIterator[str]:
        try:
            while True:
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=20)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            service.unsubscribe_agent_events(game_id, queue)

    return StreamingResponse(stream(), media_type="text/event-stream")
