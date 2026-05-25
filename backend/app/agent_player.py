"""AgentPlayer: skillful-agent backed chess player for the white side."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

import chess
from dotenv import load_dotenv

from app.config import BACKEND_DIR, SKILLFUL_AGENT_ENV
from app.players import AgentResignedError, Player, PlayerError

try:
    from skill_agent import AgentContextOverflowError
except ImportError:
    # Older skillful-agent versions don't expose the typed overflow exception.
    # Use a never-matched sentinel so provider 400s bubble up as plain Exceptions.
    class AgentContextOverflowError(Exception):  # type: ignore[no-redef]
        requested_input_tokens: int | None = None
        model_context_limit: int | None = None

SKILLS_DIR = BACKEND_DIR / "skills"
API_BASE = os.getenv("CHESS_API_BASE", "http://localhost:8000")

# Load credentials from skillful-agent's .env (only if not already in environment)
load_dotenv(SKILLFUL_AGENT_ENV, override=False)

# Max attempts per chess turn. Each attempt is a fresh run_stream with cleared
# conversation. Retries handle the case where the model finishes a run without
# calling make_move.py (observed with Gemma 4 after illegal-move recovery).
_MAX_ATTEMPTS = 30


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
            "You are playing chess as white in a live game.\n\n"
            "The chess-player skill documents the scripts available to you and how "
            "to use them well. Call use_skill at the start of every turn to load it, "
            "then follow its guidance.\n\n"
            "make_move.py COMMITS the move immediately — the board advances and your "
            "turn ends the moment it returns ok=true. Do not continue calling tools "
            "after that. If it returns ok=false, choose a different move from the "
            "legal_moves list in the error response and call make_move.py again.\n\n"
            "Take the time you need to think, but avoid loops. If you find yourself "
            "calling the same tool repeatedly on the same position, or oscillating "
            "between candidates without converging, commit the move you currently "
            "believe is best rather than continuing to deliberate.\n\n"
            "If you do not call make_move.py within the turn, that counts as resignation (a loss)."
        ),
        # Per-request output cap (provider truncates at this limit). Each
        # response is reasoning text + at most one tool call, so 1024 is
        # plenty for the model to react to a single tool's output before
        # calling the next one. Prevents runaway single responses.
        max_tokens=1024,
        # Per-run request cap. Typical turn under the tool flow uses 4–9
        # requests (use_skill + show_position + 1–3 imagine_move calls +
        # optional evaluate_position + make_move, with reasoning text between).
        # 16 leaves headroom for one or two illegal-move retries inside a
        # single run_stream before the harness-level retry kicks in.
        max_turns=16,
    )
    return Agent(model=model, skills_dir=SKILLS_DIR, config=cfg)


def _committed_move_from_tool_log(tool_log: list[Any]) -> str | None:
    """Return the UCI move from the last successful make_move.py call, or None.

    make_move.py POSTs to /agent-move and on success prints
    {"ok": true, "move": "..."}. run_script wraps it as
    {"ok": bool, "stdout": str, ...} in output_preview.
    """
    for record in reversed(tool_log):
        if record.tool != "run_script":
            continue
        if record.input.get("filename") != "make_move.py":
            continue
        try:
            outer = json.loads(record.output_preview or "")
            inner = json.loads(outer.get("stdout") or "")
        except (json.JSONDecodeError, TypeError):
            continue
        if inner.get("ok") and inner.get("move"):
            return inner["move"]
    return None


class AgentPlayer(Player):
    """White-only player backed by the skillful-agent SDK.

    make_move.py commits the move to the board via POST /api/games/{id}/agent-move.
    The harness breaks the stream as soon as make_move.py returns ok=true — the
    move is already applied at that point and the turn is over.

    If a run finishes without a committed move (Gemma 4 sometimes reasons
    correctly but dispatches the wrong tool), the same prompt is retried with a
    cleared conversation. Per-turn fresh context is already the baseline (see
    decisions/2026-05-24-per-turn-fresh-context.md), so the retry is just another
    attempt — no special framing needed.
    """

    is_human = False

    def __init__(self, game_id: str, event_sink: Callable[[dict[str, Any]], None]) -> None:
        self._game_id = game_id
        self._event_sink = event_sink
        self._agent = _build_agent(game_id)

    async def get_move(self, board: chess.Board, last_san: str | None = None) -> chess.Move:
        from skill_agent import TextDeltaEvent, ToolCallEvent, ToolResultEvent
        from pydantic_ai.exceptions import UsageLimitExceeded

        if last_san:
            prompt = f"Opponent played {last_san}.\n\nCurrent position (FEN):\n{board.fen()}"
        else:
            prompt = f"Game start.\n\nCurrent position (FEN):\n{board.fen()}"
        self._event_sink({"type": "prompt", "content": prompt})

        _thinking_buf = ""

        def _flush_thinking() -> None:
            nonlocal _thinking_buf
            if _thinking_buf:
                self._event_sink({"type": "thinking", "content": _thinking_buf})
                _thinking_buf = ""

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            # Per-turn fresh context — see ADR 2026-05-24-per-turn-fresh-context.
            self._agent.clear_conversation()
            if attempt > 1:
                self._event_sink({"type": "retry", "attempt": attempt})

            try:
                async for event in self._agent.run_stream(prompt):
                    if isinstance(event, TextDeltaEvent):
                        _thinking_buf += event.content
                        self._event_sink({"type": "text_delta", "content": event.content})

                    elif isinstance(event, ToolCallEvent):
                        _flush_thinking()
                        self._event_sink({
                            "type": "tool_call",
                            "tool": event.name,
                            "args": getattr(event, "args", {}),
                        })

                    elif isinstance(event, ToolResultEvent):
                        _flush_thinking()
                        tool_log = list(self._agent._deps.tool_log)
                        result_preview = next(
                            (r.output_preview for r in reversed(tool_log) if r.tool == event.name),
                            "",
                        )
                        self._event_sink({
                            "type": "tool_result",
                            "tool": event.name,
                            "result": result_preview,
                        })
                        # As soon as make_move.py committed, the backend has
                        # already advanced the board. Stop streaming.
                        if event.name == "run_script":
                            committed = _committed_move_from_tool_log(tool_log)
                            if committed is not None:
                                return chess.Move.from_uci(committed)

            except AgentContextOverflowError as exc:
                # Infrastructure limit — not the agent's fault. Abort with no
                # ELO update. See decisions/2026-05-24-per-turn-fresh-context.md.
                raise PlayerError(
                    f"context_overflow: requested {exc.requested_input_tokens} input "
                    f"tokens, model limit {exc.model_context_limit}."
                ) from exc
            except UsageLimitExceeded:
                # Model exhausted its per-run request budget (max_turns) without
                # committing a move. Treat as "no move this attempt" — the outer
                # loop retries with fresh context, and if all retries fail the
                # agent resigns. This is an agent capability failure, not an
                # infrastructure abort.
                _flush_thinking()
                continue

            _flush_thinking()
            # Run ended without a committed move — loop and retry.

        # Capability failure after every retry exhausted → resignation.
        # See knowledge-base/decisions/2026-05-25-agent-resigns-when-stuck.md.
        raise AgentResignedError(
            f"agent_resigned_no_move: no legal move committed after {_MAX_ATTEMPTS} attempts."
        )
