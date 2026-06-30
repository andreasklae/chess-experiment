import asyncio
import json
import logging
import os
import shutil
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated


def _configure_logging() -> None:
    """One-shot logging setup for the FastAPI process.

    Honours CHESS_LOG_LEVEL env var (defaults to INFO). Uvicorn installs its
    own handler on root; we just set the level on `app.*` loggers so our
    info/debug calls are visible without making uvicorn extra noisy.
    """
    level_name = os.getenv("CHESS_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s · %(message)s",
        datefmt="%H:%M:%S",
    ))
    root = logging.getLogger("app")
    root.setLevel(level)
    root.handlers = [handler]
    root.propagate = False


_configure_logging()
logger = logging.getLogger("app.main")

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pydantic import BaseModel, Field

from app.batch_runner import BatchRunner
from app.batch_service import Batch, BatchService
from app.config import Settings, get_settings
from app.eval_service import EvalService
from app.game_service import GameService
from app.players import PlayerFactory
from app.schemas import AgentCommitRequest, CHESSCOM_ELOS, CreateGameRequest, GameState, GameSummary, HealthResponse, MAIA_ELOS, MoveRequest, PlayerTypeInfo


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info("startup · games_dir=%s batches_dir=%s", settings.games_dir, settings.batches_dir)
    logger.info("startup · stockfish=%r lc0=%r", settings.stockfish_path, settings.lc0_path)
    fastapi_app.state.game_service = build_game_service()
    batch_service = BatchService(settings.batches_dir, settings.games_dir)
    fastapi_app.state.batch_service = batch_service
    fastapi_app.state.batch_runner = BatchRunner(batch_service, fastapi_app.state.game_service)
    fastapi_app.state.puzzle_run = None  # the current/last PuzzleRun, if any
    fastapi_app.state.puzzle_task = None
    # Named puzzle SETS registry (each: puzzle JSON + its own progress file). The
    # agent-SOLVING benchmark is the offensive set. (A defensiveMove-tagged
    # 'solving' set was tried and removed: verified against the Lichess tagger
    # source, motif themes describe the SOLVER's own move, so they don't yield
    # genuine 'defend against the opponent's tactic' puzzles. The defensive work
    # instead lives as a DETECTOR-verification harness over flipped positions —
    # see experiments/puzzle-benchmark/flip_puzzles.py + verify_threat_warnings.py.)
    from app.puzzle_progress import PuzzleProgress
    _pb = Path(__file__).resolve().parents[2] / "experiments" / "puzzle-benchmark"
    fastapi_app.state.puzzle_sets = {
        "offensive": {
            "puzzles": _pb / "puzzles.json",
            "progress": PuzzleProgress(_pb / "results" / "progress.json"),
        },
        # Defensive set: pre-blunder positions mined from agent-lost-by-mate games,
        # Stockfish-verified that a holding move existed. The agent must find ANY
        # move that holds (graded via acceptable_uci). See
        # experiments/puzzle-benchmark/puzzles_defensive.json + the Item-P note.
        "defensive": {
            "puzzles": _pb / "puzzles_defensive.json",
            "progress": PuzzleProgress(_pb / "results" / "progress_defensive.json"),
        },
        # London set: London-System opening puzzles from the Lichess DB (white solver),
        # split into 'book' (the solution is a London theory move) and 'tactic' (a
        # London-middlegame tactic the wiki/guide should help with). Tests the opening
        # wiki + the chess__opening_book / chess__opening_guide tools.
        "london": {
            "puzzles": _pb / "puzzles_london.json",
            "progress": PuzzleProgress(_pb / "results" / "progress_london.json"),
        },
    }
    fastapi_app.state.puzzle_progress = fastapi_app.state.puzzle_sets["offensive"]["progress"]
    logger.info("startup · ready")
    try:
        yield
    finally:
        logger.info("shutdown · closing game service and eval service")
        await fastapi_app.state.game_service.shutdown()
        if hasattr(fastapi_app.state, "eval_service"):
            fastapi_app.state.eval_service.close()


app = FastAPI(title="Chess Experiment Backend", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    # localhost for desktop dev, plus any private-LAN host on the Vite dev port
    # so a phone on the same wifi (e.g. http://192.168.1.7:5173) can reach the
    # API. Scoped to :5173 and RFC-1918 ranges — not a wide-open CORS policy.
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"http://(192\.168|10|172\.(1[6-9]|2\d|3[01]))\.[\d.]+:5173",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def build_game_service() -> GameService:
    settings = get_settings()
    eval_service = EvalService(settings.stockfish_path, settings.stockfish_eval_depth)
    app.state.eval_service = eval_service
    return GameService(
        PlayerFactory(settings),
        games_dir=settings.games_dir,
        eval_service=eval_service,
    )


SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_game_service() -> GameService:
    return app.state.game_service


GameServiceDep = Annotated[GameService, Depends(get_game_service)]


def get_batch_runner() -> BatchRunner:
    return app.state.batch_runner


def get_batch_service() -> BatchService:
    return app.state.batch_service


BatchRunnerDep = Annotated[BatchRunner, Depends(get_batch_runner)]
BatchServiceDep = Annotated[BatchService, Depends(get_batch_service)]


class CreateBatchRequest(BaseModel):
    label: str = Field(default="", max_length=80)
    pool: str = Field(..., pattern="^(maia|chesscom)$")
    total_games: int = Field(..., ge=1, le=500)


class AgentEloResponse(BaseModel):
    elo: float
    games_played: int
    last_result: str | None
    streak: int


@app.get("/api/health")
async def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        ok=True,
        lc0_path=settings.lc0_path,
        lc0_found=shutil.which(settings.lc0_path) is not None,
        maia_weights_dir=str(settings.maia_weights_dir),
    )


@app.get("/api/repo-state")
async def repo_state() -> dict:
    """Live git state and ranked/experimental phase for the UI banner.

    The frontend uses this to surface whether the next batch will be
    ranked (writes to ranked.csv, updates ELO) or experimental (writes to
    experimental.csv, ELO frozen). See
    knowledge-base/decisions/2026-05-24-ranked-vs-experimental.md.
    """
    from app.repo_state import is_ranked_context, live_git_state
    git = live_git_state()
    ranked, reason = is_ranked_context()
    return {
        "phase": "ranked" if ranked else "experimental",
        "reason": reason,
        "branch": git.branch,
        "commit_sha": git.commit_sha,
        "short_sha": git.short_sha,
        "dirty": git.dirty,
        "is_repo": git.is_repo,
    }


@app.get("/api/player-types")
async def player_types() -> list[PlayerTypeInfo]:
    return [
        PlayerTypeInfo(type="human", elo_required=False),
        PlayerTypeInfo(type="maia", elo_required=True, allowed_elos=list(MAIA_ELOS)),
        PlayerTypeInfo(type="agent", elo_required=False),
        PlayerTypeInfo(type="chesscom", elo_required=True, allowed_elos=list(CHESSCOM_ELOS)),
    ]


@app.get("/api/games")
def list_games(service: GameServiceDep) -> list[GameSummary]:
    # Plain def on purpose: list_summaries does a synchronous recursive scan
    # of every game JSON on disk. Under iCloud, evicted files can block reads
    # for seconds; as an async route this wedged the entire event loop (every
    # endpoint "pending") once the lobby started polling. FastAPI runs sync
    # routes in a threadpool, so a slow scan can no longer stall the server.
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


@app.post("/api/games/{game_id}/agent-commit")
async def submit_agent_commit(
    game_id: str, request: AgentCommitRequest, service: GameServiceDep
) -> dict:
    """Validate an agent commit-intent (legality, turn, move shape).

    Pure validator: never pushes to the board. See
    ``GameService.submit_agent_commit`` for the full contract.
    """
    return await service.submit_agent_commit(game_id, request.move, request.reasoning)


@app.post("/api/games/{game_id}/pause")
async def pause_game(game_id: str, service: GameServiceDep) -> GameState:
    service.get_state(game_id)  # 404 if not the current game
    service.set_paused(True)
    return service.get_state(game_id)


@app.post("/api/games/{game_id}/resume")
async def resume_game(game_id: str, service: GameServiceDep) -> GameState:
    service.get_state(game_id)
    service.set_paused(False)
    return service.get_state(game_id)


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


@app.get("/api/batches")
async def list_batches(runner: BatchRunnerDep) -> list[Batch]:
    return runner.list_all()


@app.get("/api/batches/active")
async def active_batch(runner: BatchRunnerDep) -> Batch | None:
    return runner.get_active()


@app.post("/api/batches")
async def create_batch(request: CreateBatchRequest, service: BatchServiceDep) -> Batch:
    return service.create(label=request.label, pool=request.pool, total_games=request.total_games)


@app.get("/api/batches/{batch_id}")
async def get_batch(batch_id: str, runner: BatchRunnerDep) -> Batch:
    batch = runner.get(batch_id)
    if batch is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Batch not found.")
    return batch


@app.post("/api/batches/{batch_id}/start")
async def start_batch(batch_id: str, runner: BatchRunnerDep) -> Batch:
    try:
        return await runner.start(batch_id)
    except (ValueError, RuntimeError) as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/batches/{batch_id}/pause")
async def pause_batch(batch_id: str, runner: BatchRunnerDep) -> Batch:
    try:
        return await runner.pause(batch_id)
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/batches/{batch_id}/stop")
async def stop_batch(batch_id: str, runner: BatchRunnerDep) -> Batch:
    try:
        return await runner.stop(batch_id)
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/api/batches/{batch_id}", status_code=204)
async def delete_batch(batch_id: str, runner: BatchRunnerDep) -> Response:
    await runner.delete(batch_id)
    return Response(status_code=204)


@app.get("/api/agent-elo")
async def get_agent_elo(service: BatchServiceDep) -> AgentEloResponse:
    state = service.load_agent_elo()
    return AgentEloResponse(elo=state.elo, games_played=state.games_played, last_result=state.last_result, streak=state.streak)


@app.post("/api/agent-elo/reset")
async def reset_agent_elo(service: BatchServiceDep) -> AgentEloResponse:
    state = service.reset_agent_elo()
    return AgentEloResponse(elo=state.elo, games_played=state.games_played, last_result=state.last_result, streak=state.streak)


@app.get("/api/games/{game_id}/agent-events")
async def agent_events(game_id: str, service: GameServiceDep) -> StreamingResponse:
    # Subscribe first, then read history — this ordering ensures no live events
    # are dropped: events that arrive between history-read and queue-subscribe
    # would be lost, but subscribing first then replaying past events is safe
    # (the live queue may contain some events that are also in history for the
    # current in-progress turn, but the frontend deduplicates by re-rendering
    # state, so a few duplicates are harmless).
    queue = await service.subscribe_agent_events(game_id)
    past_events = service.get_past_agent_events(game_id)

    async def stream() -> AsyncIterator[str]:
        try:
            for event in past_events:
                yield f"event: agent\ndata: {json.dumps(event)}\n\n"
            while True:
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=20)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            service.unsubscribe_agent_events(game_id, queue)

    return StreamingResponse(stream(), media_type="text/event-stream")


# ============================================================================
# PUZZLE BENCHMARK
# ============================================================================

from pydantic import BaseModel as _BaseModel  # noqa: E402

_PUZZLE_SET_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments" / "puzzle-benchmark" / "puzzles.json"
)


class PuzzleRunRequest(_BaseModel):
    mode: str = "all"                 # all | unsolved | untested | failed
    set: str = "offensive"            # which puzzle set: offensive | defensive
    topics: list[str] | None = None   # filter to these topics (None = all)
    difficulties: list[str] | None = None  # filter by difficulty (easy/medium/hard/expert)
    per_topic: int | None = None      # cap N puzzles PER TOPIC (None = no cap)
    limit: int | None = None          # legacy flat cap on total (None = no cap)
    ids: list[str] | None = None      # run only these puzzle ids (overrides filters)


def _resolve_set(name: str):
    """Return (puzzles_path, progress_store) for a named puzzle set, or 400."""
    sets = app.state.puzzle_sets
    if name not in sets:
        raise HTTPException(status_code=400,
                            detail=f"Unknown puzzle set '{name}'. Known: {sorted(sets)}.")
    return sets[name]["puzzles"], sets[name]["progress"]


def _load_specs(puzzles_path=None):
    from app.puzzle_service import load_puzzle_set
    return load_puzzle_set(puzzles_path or _PUZZLE_SET_PATH)


@app.get("/api/puzzles")
def list_puzzles(set: str = "offensive") -> dict:
    """The fixed puzzle set: counts per topic/band so the UI can show the menu."""
    puzzles_path, _ = _resolve_set(set)
    specs = _load_specs(puzzles_path)
    topics: dict[str, int] = {}
    for s in specs:
        topics[s.topic] = topics.get(s.topic, 0) + 1
    import json as _json
    raw = {p["id"]: p for p in _json.loads(puzzles_path.read_text())}
    return {"total": len(specs), "set": set, "topics": topics,
            "puzzles": [{"id": s.id, "topic": s.topic, "rating": s.rating,
                         "band": s.band, "themes": s.themes,
                         "title": raw.get(s.id, {}).get("title", s.topic),
                         "difficulty": raw.get(s.id, {}).get("difficulty", ""),
                         "lichess_url": raw.get(s.id, {}).get("lichess_url", "")}
                        for s in specs]}


@app.post("/api/puzzles/run")
async def start_puzzle_run(request: PuzzleRunRequest) -> dict:
    import asyncio as _asyncio
    from app.puzzle_runner import PuzzleRun, run_puzzles

    existing = app.state.puzzle_task
    if existing is not None and not existing.done():
        raise HTTPException(status_code=409, detail="A puzzle run is already in progress.")

    puzzles_path, progress = _resolve_set(request.set)
    specs = _load_specs(puzzles_path)
    if request.ids:
        idset = set(request.ids)
        specs = [s for s in specs if s.id in idset]
    else:
        if request.topics:
            tset = set(request.topics)
            specs = [s for s in specs if s.topic in tset]
        if request.difficulties:
            dset = set(request.difficulties)
            specs = [s for s in specs if s.difficulty in dset]
        # Apply the run mode (all / unsolved / untested / failed) using the
        # persistent progress store, so a run can resume only what's needed.
        allowed = set(progress.filter_ids([s.id for s in specs], request.mode))
        specs = [s for s in specs if s.id in allowed]
        # Cap N per topic (after mode/difficulty filtering) so the slider gives
        # a balanced sample across topics rather than a flat head-of-list cut.
        if request.per_topic:
            seen: dict[str, int] = {}
            capped = []
            for s in specs:
                if seen.get(s.topic, 0) < request.per_topic:
                    capped.append(s); seen[s.topic] = seen.get(s.topic, 0) + 1
            specs = capped
        elif request.limit:
            specs = specs[: request.limit]
    if not specs:
        raise HTTPException(status_code=400,
                            detail=f"No puzzles match (mode={request.mode}). "
                                   "Everything in scope may already be solved.")

    out_path = _PUZZLE_SET_PATH.parent / "results" / f"run_{int(time.time())}.jsonl"
    run = PuzzleRun(specs, out_path, progress=progress, mode=request.mode)
    run.set_name = request.set  # which set this run belongs to (for the status view)
    app.state.puzzle_run = run
    service = app.state.game_service
    app.state.puzzle_task = _asyncio.create_task(run_puzzles(service, run))
    return {"started": True, "n": len(specs), "set": request.set,
            "mode": request.mode, "out_path": str(out_path)}


@app.post("/api/puzzles/run/abort")
async def abort_puzzle_run() -> dict:
    """Abort the in-progress puzzle run: stop before the next puzzle, and end the
    currently-playing puzzle game now (deleting it makes the agent turn unwind)."""
    run = app.state.puzzle_run
    if run is None or not run.running:
        raise HTTPException(status_code=409, detail="No puzzle run is in progress.")
    run.stop_requested = True
    gid = run.current_game_id
    if gid:
        try:
            await app.state.game_service.delete(gid)
        except Exception:
            pass  # game may have already finished; the loop stop-check handles it
    return {"aborting": True, "completed": len(run.results)}


@app.get("/api/puzzles/progress")
def puzzle_progress(set: str = "offensive") -> dict:
    """Persistent per-topic / per-difficulty solved-failed-untested overview."""
    puzzles_path, progress = _resolve_set(set)
    return progress.overview(_load_specs(puzzles_path))


@app.get("/api/puzzles/progress/{puzzle_id}")
def puzzle_progress_detail(puzzle_id: str, set: str = "offensive") -> dict:
    _, progress = _resolve_set(set)
    rec = progress.get(puzzle_id)
    if rec is None:
        return {"status": "untested"}
    return rec


@app.get("/api/puzzles/run")
def puzzle_run_status() -> dict:
    run = app.state.puzzle_run
    if run is None:
        return {"running": False, "results": []}
    solved = sum(1 for r in run.results if r.get("solved"))
    return {"running": run.running, "idx": run.idx, "n": len(run.specs),
            "set": getattr(run, "set_name", "offensive"),
            "completed": len(run.results), "solved": solved,
            "results": run.results}


@app.get("/api/puzzles/run/events")
async def puzzle_run_events() -> StreamingResponse:
    """Persistent puzzle-run event stream. Stays open even when idle, and
    attaches to whatever run is current — so a run launched from anywhere
    (the UI, a script, this API) is picked up live without a page refresh.

    The stream follows `app.state.puzzle_run` across runs: it subscribes to the
    active run, forwards its events, and when that run ends it goes back to
    waiting for the next one. A late subscriber catches up via a replayed
    `puzzle_result` per completed puzzle plus a `run_status` snapshot."""

    async def stream() -> AsyncIterator[str]:
        seen_run = None          # the run object we are currently attached to
        queue = None

        while True:
            run = app.state.puzzle_run

            # A new run appeared (or the first one): attach + replay catch-up.
            if run is not None and run is not seen_run:
                seen_run = run
                queue = run.subscribe()
                started = {"type": "run_started", "n": len(run.specs),
                           "running": run.running, "mode": run.mode}
                yield f"data: {json.dumps(started)}\n\n"
                for r in run.results:        # catch a late subscriber up
                    yield f"data: {json.dumps({'type': 'puzzle_result', **r})}\n\n"

            if queue is None:
                # No run yet — idle heartbeat so the connection stays open and
                # the client keeps listening for the next run.
                await asyncio.sleep(2)
                yield ": idle\n\n"
                continue

            try:
                evt = await asyncio.wait_for(queue.get(), timeout=15)
                yield f"data: {json.dumps(evt)}\n\n"
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"

            # Current run finished and drained: emit run_done, then detach and
            # loop back to wait for the next run (do NOT close the stream).
            if seen_run is not None and not seen_run.running and queue.empty():
                yield f"data: {json.dumps({'type': 'run_done', 'n': len(seen_run.results)})}\n\n"
                seen_run = None
                queue = None

    return StreamingResponse(stream(), media_type="text/event-stream")
