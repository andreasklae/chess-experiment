"""AgentPlayer: skillful-agent backed chess player for the white side."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

import chess
from dotenv import load_dotenv

from app.config import BACKEND_DIR, SKILLFUL_AGENT_ENV
from app.players import Player, PlayerError

SKILLS_DIR = BACKEND_DIR / "skills"
API_BASE = os.getenv("CHESS_API_BASE", "http://localhost:8000")

# Load credentials from skillful-agent's .env (only if not already in environment)
load_dotenv(SKILLFUL_AGENT_ENV, override=False)


def _build_agent(game_id: str):
    """Create a skillful-agent Agent. Chess tools live in the skill's scripts/.

    CHESS_GAME_ID and CHESS_API_BASE are injected into the environment so scripts
    can read them without the agent having to pass them as CLI arguments.

    Backend selection (matches skillful-agent's server/app.py priority):
      1. SKILL_AGENT_EX3_BASE_URL set → local vLLM on eX3 via OpenAIProvider(base_url=...)
      2. SKILL_AGENT_AZURE_ENDPOINT set → Azure OpenAI
      3. Otherwise → OpenAI public API (requires OPENAI_API_KEY)
    """
    from pydantic_ai.models.openai import OpenAIChatModel
    from skill_agent import Agent, AgentConfig

    # Inject game context for scripts — they read these instead of accepting CLI args
    os.environ["CHESS_GAME_ID"] = game_id
    os.environ["CHESS_API_BASE"] = API_BASE

    ex3_base_url = os.getenv("SKILL_AGENT_EX3_BASE_URL")
    azure_endpoint = os.getenv("SKILL_AGENT_AZURE_ENDPOINT")

    if ex3_base_url:
        from pydantic_ai.providers.openai import OpenAIProvider
        provider = OpenAIProvider(base_url=ex3_base_url, api_key="dummy")
        model_name = os.getenv("SKILL_AGENT_OPENAI_MODEL", "google/gemma-4-31B-it")
    elif azure_endpoint:
        from pydantic_ai.providers.azure import AzureProvider
        provider = AzureProvider(
            azure_endpoint=azure_endpoint,
            api_version=os.getenv("SKILL_AGENT_AZURE_API_VERSION", "2024-07-01-preview"),
            api_key=os.environ["SKILL_AGENT_AZURE_API_KEY"],
        )
        model_name = os.getenv("SKILL_AGENT_OPENAI_MODEL", "gpt-4o-mini")
    else:
        from pydantic_ai.providers.openai import OpenAIProvider
        provider = OpenAIProvider(api_key=os.environ["OPENAI_API_KEY"])
        model_name = os.getenv("SKILL_AGENT_OPENAI_MODEL", "gpt-4o-mini")

    model = OpenAIChatModel(model_name, provider=provider)
    cfg = AgentConfig(
        system_prompt_extra=(
            "You are a chess engine playing white.\n\n"
            "Required sequence for every move — follow it strictly:\n"
            "  1. Call `use_skill` with skill_name='chess-player' (only on the very first move).\n"
            "  2. Call `run_script` to invoke list_legal_moves.py and read the legal moves.\n"
            "  3. **Before calling make_move.py, write 2–4 sentences of explicit reasoning** "
            "as plain text: name 2–3 candidate moves, compare them briefly, and state which "
            "one you will play and why. This reasoning step is mandatory and must come before "
            "the make_move.py call, not after.\n"
            "  4. Call `run_script` to invoke make_move.py with your chosen move.\n"
            "  5. End the turn. Do not write any more text after make_move.py — the move is "
            "already committed and further commentary serves no purpose.\n\n"
            "Reasoning before the move is the only commentary the experiment records as "
            "informing the choice. Reasoning written after make_move.py is treated as "
            "post-hoc and is discarded for analysis."
        ),
        max_turns=20,
    )
    return Agent(model=model, skills_dir=SKILLS_DIR, config=cfg)


def _extract_move_from_tool_log(tool_log: list[Any]) -> str | None:
    """Scan agent._deps.tool_log for a successful make_move.py call and return the UCI string.

    ToolResultEvent has no payload — the actual script stdout is only accessible via the
    tool_log that skillful-agent maintains in _deps throughout the run.
    """
    for record in tool_log:
        if record.tool != "run_script":
            continue
        if record.input.get("filename") != "make_move.py":
            continue
        preview = record.output_preview or ""
        # output_preview is a JSON string: {"ok": true, "stdout": "{...}", ...}
        # or the raw response string — try both layers
        try:
            outer = json.loads(preview)
            # run_script wraps as {"ok": bool, "stdout": str, ...}
            stdout = outer.get("stdout", "")
            inner = json.loads(stdout) if stdout else {}
            if isinstance(inner, dict) and inner.get("ok") and inner.get("move"):
                return inner["move"]
            # Fallback: maybe output_preview is the inner JSON directly
            if isinstance(outer, dict) and outer.get("ok") and outer.get("move"):
                return outer["move"]
        except (json.JSONDecodeError, TypeError):
            pass
    return None


class AgentPlayer(Player):
    """White-only player backed by the skillful-agent SDK.

    Backend (Azure / OpenAI / eX3 vLLM) is selected by environment variables —
    see `_build_agent` for the priority order.

    The agent uses the chess-player skill's scripts/ directory for its tools:
      - list_legal_moves.py  — GET /api/games/{id} → legal_moves array
      - make_move.py         — POST /api/games/{id}/moves → confirms the move

    The move chosen by the agent is detected by watching for a successful
    make_move.py result in the event stream, then validated against python-chess.
    """

    is_human = False

    def __init__(self, game_id: str, event_sink: Callable[[dict[str, Any]], None]) -> None:
        self._game_id = game_id
        self._event_sink = event_sink
        self._agent = _build_agent(game_id)

    async def get_move(self, board: chess.Board, last_san: str | None = None) -> chess.Move:
        from skill_agent import TextDeltaEvent, ToolCallEvent, ToolResultEvent
        try:
            from skill_agent import AgentContextOverflowError
        except ImportError:
            # Older skillful-agent versions (pre-2026-05-24) don't expose the
            # typed overflow exception. Fall back to a never-matched sentinel
            # so the try/except below compiles; provider 400s will then bubble
            # up as plain Exceptions, caught by game_service's outer handler.
            class AgentContextOverflowError(Exception):  # type: ignore[no-redef]
                requested_input_tokens: int | None = None
                model_context_limit: int | None = None

        # Baseline calibration runs with per-turn fresh context: the agent sees
        # the system prompt, skill list, and one user message (opponent move + FEN).
        # Nothing from prior turns carries over. The FEN encodes complete game
        # state; cross-turn memory is a separate experimental variable that future
        # configurations will introduce and measure against this baseline.
        # See knowledge-base/decisions/2026-05-24-per-turn-fresh-context.md
        self._agent.clear_conversation()

        if last_san:
            prompt = f"Opponent played {last_san}.\n\nCurrent position (FEN):\n{board.fen()}"
        else:
            prompt = f"Game start.\n\nCurrent position (FEN):\n{board.fen()}"
        self._event_sink({"type": "prompt", "content": prompt})

        turn_events: list[dict[str, Any]] = []
        _thinking_buf: str = ""  # accumulate text deltas; flushed on tool_call or run end

        def _flush_thinking() -> None:
            nonlocal _thinking_buf
            if _thinking_buf:
                evt = {"type": "thinking", "content": _thinking_buf}
                turn_events.append(evt)
                _thinking_buf = ""

        try:
            async for event in self._agent.run_stream(prompt):
                if isinstance(event, TextDeltaEvent):
                    _thinking_buf += event.content
                    # Still stream individual deltas to SSE for live UI updates
                    self._event_sink({"type": "text_delta", "content": event.content})
                elif isinstance(event, ToolCallEvent):
                    _flush_thinking()
                    evt = {
                        "type": "tool_call",
                        "tool": event.name,
                        "args": getattr(event, "args", {}),
                    }
                    self._event_sink(evt)
                    turn_events.append(evt)
                elif isinstance(event, ToolResultEvent):
                    # ToolResultEvent only has .name — no content/payload.
                    # Enrich with output_preview from the tool_log if available.
                    tool_log = list(self._agent._deps.tool_log)
                    result_preview = ""
                    for record in reversed(tool_log):
                        if record.tool == event.name:
                            result_preview = record.output_preview
                            break
                    evt = {
                        "type": "tool_result",
                        "tool": event.name,
                        "result": result_preview,
                    }
                    self._event_sink(evt)
                    turn_events.append(evt)
        except AgentContextOverflowError as exc:
            # Surface to the bot loop as a PlayerError, which game_service
            # turns into an aborted game with this message as the reason.
            # Baseline calibration uses per-turn fresh context so this should
            # rarely fire; when it does, it usually means a single turn's
            # output was itself bigger than the window.
            raise PlayerError(
                f"context_overflow: requested {exc.requested_input_tokens} input "
                f"tokens, model limit {exc.model_context_limit}."
            ) from exc

        _flush_thinking()

        # After the stream ends, tool_log has all records for this run.
        chosen = _extract_move_from_tool_log(list(self._agent._deps.tool_log))
        if chosen is None:
            raise PlayerError("Agent did not successfully call make_move.py this turn.")

        try:
            move = chess.Move.from_uci(chosen)
        except ValueError as exc:
            raise PlayerError(f"Agent chose invalid UCI: {chosen}") from exc

        if move not in board.legal_moves:
            raise PlayerError(f"Agent chose illegal move: {chosen}")

        return move
