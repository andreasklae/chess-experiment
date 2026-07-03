"""Drives a sequence of puzzles through GameService and collects scored results.

For each puzzle: create a puzzle game (agent vs PuzzlePlayer), wait for it to
finish, then assemble a result from the PuzzlePlayer's per-move scoring + the
agent's per-move reasoning (captured from the agent event stream). Results stream
out via an async queue so the frontend / a CLI can watch live, and the full run
is written to a JSONL file for analysis.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

import chess

from app.game_service import GameService
from app.puzzle_service import PuzzleSpec

logger = logging.getLogger("uvicorn.error")


class PuzzleRun:
    """One run over a list of puzzles. Holds live state + a broadcast queue."""

    def __init__(self, specs: list[PuzzleSpec], out_path: Path, progress=None, mode: str = "all"):
        self.specs = specs
        self.out_path = out_path
        self.progress = progress          # PuzzleProgress | None
        self.mode = mode                  # the run mode that produced this set
        self.run_id = out_path.stem       # e.g. run_1719...
        self.results: list[dict] = []
        self.idx = 0
        self.running = False
        self.stop_requested = False       # set by the abort endpoint
        self.current_game_id: str | None = None  # the in-flight puzzle game
        self.subscribers: set[asyncio.Queue] = set()
        self._current_reasonings: dict[int, str] = {}

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self.subscribers.add(q)
        return q

    def _broadcast(self, event: dict) -> None:
        for q in list(self.subscribers):
            try:
                q.put_nowait(event)
            except Exception:
                pass


async def run_puzzles(service: GameService, run: PuzzleRun) -> None:
    """Execute every puzzle in `run`, sequentially, recording results."""
    run.running = True
    run.out_path.parent.mkdir(parents=True, exist_ok=True)
    fout = run.out_path.open("w")
    try:
        for i, spec in enumerate(run.specs):
            if run.stop_requested:
                logger.info("puzzle run aborted before puzzle %d/%d", i, len(run.specs))
                run._broadcast({"type": "run_aborted", "completed": len(run.results)})
                break
            run.idx = i
            try:
                from app.puzzle_categorize import categorize
                _cat = categorize(spec.fen, spec.moves)
            except Exception:
                _cat = {}
            run._broadcast({"type": "puzzle_begin", "i": i, "n": len(run.specs),
                            "id": spec.id, "topic": spec.topic, "rating": spec.rating,
                            "band": spec.band, "fen": spec.start_fen,
                            "title": spec.title, "difficulty": spec.difficulty,
                            "lichess_url": spec.lichess_url,
                            "category": _cat, "signature": _cat.get("signature"),
                            "agent_color": "white" if spec.agent_color == chess.WHITE else "black"})
            try:
                result = await _run_one(service, spec, run)
            except Exception as e:  # never let one puzzle kill the run
                logger.exception("puzzle %s crashed", spec.id)
                result = {"puzzle_id": spec.id, "topic": spec.topic, "band": spec.band,
                          "rating": spec.rating, "themes": spec.themes,
                          "solved": False, "solved_plies": 0,
                          "total_plies": spec.total_solver_plies,
                          "aborted_reason": f"runner_error: {e}", "attempts": []}
            run.results.append(result)
            fout.write(json.dumps(result) + "\n"); fout.flush()
            # Persist the outcome so progress survives across runs/restarts.
            if run.progress is not None:
                try:
                    run.progress.record(result, run.run_id)
                except Exception:
                    logger.exception("failed to persist progress for %s", spec.id)
            run._broadcast({"type": "puzzle_result", "i": i, **result})
    finally:
        fout.close()
        run.running = False
        run._broadcast({"type": "run_done", "n": len(run.results)})


async def _run_one(service: GameService, spec: PuzzleSpec, run: PuzzleRun) -> dict:
    """Create the puzzle game, subscribe to agent events for reasoning, await
    completion, assemble the scored result."""
    game = await service.create_puzzle_game(spec)
    puzzle_player = game.puzzle_player  # type: ignore[attr-defined]
    run.current_game_id = game.game_id

    # Capture per-turn reasoning from the agent event stream. The make_move tool
    # result carries the agent's reasoning note; we also forward thinking/tool
    # events to the run subscribers so the UI can show the agent's process live.
    reasonings: dict[int, str] = {}
    stop = asyncio.Event()

    ordered_notes: list[str] = []   # committed reasoning, in move order
    tool_calls: dict[str, int] = {} # tool name -> call count (analysis: did the
                                    # agent calculate? imagine_line/imagine_move/
                                    # show_position/search_wiki/read_reference)

    async def pump_agent_events():
        q = await service.subscribe_agent_events(game.game_id)
        try:
            while not stop.is_set():
                try:
                    raw = await asyncio.wait_for(q.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue
                run._broadcast({"type": "agent_event", "puzzle_id": spec.id, "raw": raw})
                # The queue carries SSE-framed strings ("event: agent\ndata: {json}\n\n").
                # Extract the JSON payload from the data: line before parsing.
                evt = raw
                if isinstance(raw, str):
                    payload = None
                    for ln in raw.splitlines():
                        if ln.startswith("data:"):
                            payload = ln[5:].strip()
                            break
                    if payload is None:
                        continue
                    try:
                        evt = json.loads(payload)
                    except Exception:
                        continue
                if isinstance(evt, dict) and evt.get("type") == "tool_call":
                    tool = evt.get("tool") or "?"
                    tool_calls[tool] = tool_calls.get(tool, 0) + 1
                    # The reasoning is in the make_move TOOL_CALL args (the model
                    # passes move/goal/reasoning/plan IN); the tool_result only
                    # confirms the commit. Capture from the call.
                    if tool == "chess__make_move":
                        note = _extract_reasoning(evt.get("args"))
                        if note:
                            ordered_notes.append(note)
        finally:
            service.unsubscribe_agent_events(game.game_id, q)

    pump = asyncio.create_task(pump_agent_events())

    # Wait for the game task to finish (PuzzlePlayer raises a terminal exception
    # which the bot loop turns into a finished game).
    try:
        if game.task is not None:
            await asyncio.wait_for(game.task, timeout=600)
    except asyncio.TimeoutError:
        logger.warning("puzzle %s timed out", spec.id)
    finally:
        stop.set()
        await asyncio.gather(pump, return_exceptions=True)

    # Merge PuzzlePlayer scoring (exact per-ply correctness) with the agent's
    # committed reasoning, captured live from the make_move events in move order.
    attempts = puzzle_player.attempts
    notes = ordered_notes or _reasonings_from_log(service, game.game_id)
    for k, att in enumerate(attempts):
        if k < len(notes):
            att["reasoning"] = notes[k]

    solved = bool(getattr(game, "puzzle_solved", False))
    _ = reasonings  # (live-stream buffer; authoritative notes come from the log)
    return _result_dict(spec, game, attempts, solved, puzzle_player.solved_plies,
                        tool_calls=tool_calls)


def _extract_reasoning(args) -> str | None:
    """Pull the agent's note out of a make_move tool_call's args. The model
    passes move/reasoning/goal/plan in; reasoning is the per-move note, with
    goal/plan as fallbacks. `args` is a dict or a JSON string."""
    if args is None:
        return None
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            return args[:300] or None
    if isinstance(args, dict):
        parts = []
        for key in ("reasoning", "goal", "plan"):
            v = args.get(key)
            if v:
                parts.append(f"{key}: {v}" if key != "reasoning" else str(v))
        return " · ".join(parts) if parts else None
    return None


def _reasonings_from_log(service: GameService, game_id: str) -> list[str]:
    """The agent's committed reasoning per move, in order, from the agent log.
    Each successful turn ends with a chess__make_move tool_result carrying the
    reasoning note the model wrote."""
    notes: list[str] = []
    try:
        events = service.get_past_agent_events(game_id)
    except Exception:
        return notes
    for evt in events:
        if not isinstance(evt, dict) or evt.get("type") != "tool_result":
            continue
        if evt.get("tool") != "chess__make_move":
            continue
        res = evt.get("result")
        note = None
        if isinstance(res, dict):
            note = res.get("reasoning")
        elif isinstance(res, str):
            # result may be a JSON string
            try:
                note = json.loads(res).get("reasoning")
            except Exception:
                note = res[:300]
        if note:
            notes.append(note)
    return notes


def _result_dict(spec: PuzzleSpec, game, attempts: list[dict], solved: bool,
                 solved_plies: int, tool_calls: dict[str, int] | None = None) -> dict:
    tool_calls = tool_calls or {}
    # Structural category of the puzzle (mover piece, targets, branching, etc.)
    # so a run can be sliced by motif variant to find where the agent is weak.
    try:
        from app.puzzle_categorize import categorize
        category = categorize(spec.fen, spec.moves)
    except Exception:
        category = {}
    # Derived tool-use analysis: total calls and the calculation-depth signal
    # (how often the agent reached for imagine_line / imagine_move). A solved-vs-
    # failed split on these tells us whether failures are "didn't calculate" vs
    # "calculated but mis-judged".
    total_calls = sum(tool_calls.values())
    return {
        "puzzle_id": spec.id, "topic": spec.topic, "band": spec.band,
        "rating": spec.rating, "themes": spec.themes,
        "title": spec.title, "difficulty": spec.difficulty,
        "lichess_url": spec.lichess_url,
        "agent_color": "white" if spec.agent_color == chess.WHITE else "black",
        "solved": solved,
        "solved_plies": solved_plies,
        "total_plies": spec.total_solver_plies,
        "aborted_reason": None if solved else getattr(game, "puzzle_detail", "") or "failed",
        "category": category,
        "tool_calls": tool_calls,
        "tool_calls_total": total_calls,
        "imagine_line_calls": tool_calls.get("chess__imagine_line", 0),
        "imagine_move_calls": tool_calls.get("chess__imagine_move", 0),
        "attempts": attempts,
    }
