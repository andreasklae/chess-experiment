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

# Load Azure credentials from skillful-agent's .env (only if not already in environment)
load_dotenv(SKILLFUL_AGENT_ENV, override=False)


def _build_agent(game_id: str):
    """Create a skillful-agent Agent. Chess tools live in the skill's scripts/.

    CHESS_GAME_ID and CHESS_API_BASE are injected into the environment so scripts
    can read them without the agent having to pass them as CLI arguments.
    """
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.azure import AzureProvider
    from skill_agent import Agent, AgentConfig

    # Inject game context for scripts — they read these instead of accepting CLI args
    os.environ["CHESS_GAME_ID"] = game_id
    os.environ["CHESS_API_BASE"] = API_BASE

    provider = AzureProvider(
        azure_endpoint=os.environ["SKILL_AGENT_AZURE_ENDPOINT"],
        api_version=os.getenv("SKILL_AGENT_AZURE_API_VERSION", "2024-07-01-preview"),
        api_key=os.environ["SKILL_AGENT_AZURE_API_KEY"],
    )
    model = OpenAIChatModel(
        os.getenv("SKILL_AGENT_OPENAI_MODEL", "gpt-4o-mini"),
        provider=provider,
    )
    cfg = AgentConfig(
        system_prompt_extra=(
            "You are a chess engine playing white. "
            "Think out loud before every move. "
            "Load the chess-player skill, then use its scripts to list legal moves and make your move."
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
    """White-only player backed by the skillful-agent SDK (Azure OpenAI).

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
