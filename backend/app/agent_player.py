"""AgentPlayer: skillful-agent backed chess player for the white side.

A turn proceeds as a sequence of ``run_stream`` calls (attempts) on a freshly
cleared conversation. The harness drives the loop until ``make_move.py``
commits a move (success path), or until ``_MAX_ATTEMPTS`` is reached without
a commit (resignation). Provider-level transients (vLLM JSON-parse 400s) and
``UsageLimitExceeded`` from the runner are treated as failed attempts, not
infrastructure aborts.

See ``decisions/2026-05-24-per-turn-fresh-context.md`` for the rationale
behind per-turn ``clear_conversation``, ``2026-05-25-agent-resigns-when-stuck.md``
for the resignation policy, and ``2026-05-26-stabilization.md`` for the
budget-warning mechanism.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from typing import Any

import chess
from dotenv import load_dotenv

from app.config import BACKEND_DIR, SKILLFUL_AGENT_ENV
from app.players import AgentResignedError, Player, PlayerError

SKILLS_DIR = BACKEND_DIR / "skills"
API_BASE = os.getenv("CHESS_API_BASE", "http://localhost:8000")

# Load credentials from skillful-agent's .env (only if not already in environment).
load_dotenv(SKILLFUL_AGENT_ENV, override=False)


# ── Tuning knobs ─────────────────────────────────────────────────────────

# Max attempts per chess turn. Each attempt is a fresh run_stream with cleared
# conversation. With manage_todos disabled and the budget warning between
# attempts in place, retries are rare; 10 leaves comfortable margin before the
# resignation path triggers.
_MAX_ATTEMPTS = 10

# Fraction of an attempt's tool budget (max_turns) at which we emit a UI
# budget warning AND prepend a "commit now" reminder to the NEXT attempt's
# prompt. Mid-stream injection into a live pydantic-ai run isn't possible, so
# the warning's mechanical effect on the model lands between attempts.
_BUDGET_WARN_FRACTION = 0.7

# Built-in SDK tools the chess agent doesn't need. Narrowing the surface is
# the single biggest factor in keeping turns from looping — manage_todos
# alone accounted for roughly half of a 169-tool-call runaway turn during
# stabilization testing. Only ``use_skill`` and ``run_script`` remain.
_DISABLED_TOOLS = [
    "manage_todos",          # no plan/todo workflow needed for chess
    "register_skill",
    "scaffold_skill",
    "write_skill_file",
    "read_reference",        # chess-player has no references/ dir
    "call_client_function",
    "compress_message",      # per-turn fresh context bounds the budget
    "retrieve_message",
    "compress_all",
    "read_thread",           # no inter-agent threads
    "reply_to_thread",
    "archive_thread",
    "spawn_agent",
]

_SYSTEM_PROMPT_EXTRA = (
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
)


# ── Gemma 4 thought-channel marker stripping ─────────────────────────────
#
# Gemma 4 wraps its chain-of-thought in ``<|channel>thought ... <channel|>``
# markers. The tokens arrive split across multiple streaming deltas (e.g.
# ``<|channel>``, ``thought``, ``\n``, ``<channel|>``) so per-delta stripping
# never matches. We accumulate raw deltas in a buffer and strip on the full
# string at flush time, before emitting the consolidated ``thinking`` event.

_GEMMA_OPEN_RE = re.compile(r"<\|channel\|?>thought\s*", re.IGNORECASE)
_GEMMA_CLOSE_RE = re.compile(r"<channel\|?>\s*")


def _strip_gemma_channel_markers(text: str) -> str:
    """Remove Gemma's ``<|channel>thought ... <channel|>`` framing tokens.

    Idempotent — safe to call on already-clean text."""
    return _GEMMA_CLOSE_RE.sub("", _GEMMA_OPEN_RE.sub("", text))


# ── Agent build ──────────────────────────────────────────────────────────

def _build_agent(game_id: str):
    """Create a skillful-agent Agent for one chess game.

    ``CHESS_GAME_ID`` and ``CHESS_API_BASE`` are injected into the environment
    so skill scripts can read live state without taking CLI arguments.

    Backend selection (matches skillful-agent's server priority):
      1. ``SKILL_AGENT_EX3_BASE_URL`` set → local vLLM on eX3 via OpenAIProvider.
      2. ``SKILL_AGENT_AZURE_ENDPOINT`` set → Azure OpenAI.
      3. Otherwise → OpenAI public API (requires ``OPENAI_API_KEY``).
    """
    from pydantic_ai.models.openai import OpenAIChatModel
    from skill_agent import Agent, AgentConfig

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

    cfg = AgentConfig(
        disabled_tools=_DISABLED_TOOLS,
        disable_native_skills=True,           # skip web-search-free etc.
        system_prompt_extra=_SYSTEM_PROMPT_EXTRA,
        # Per-response output cap. Each response is reasoning text + at most
        # one tool call; 1024 leaves room to react to a tool result before
        # the next call. Prevents runaway monolithic responses.
        max_tokens=1024,
        # Per-run request cap. A thorough turn uses 4–9 requests (use_skill +
        # show_position + 1–3 imagine_move + make_move, with reasoning text
        # between). 16 leaves headroom for one or two illegal-move retries
        # inside a single run_stream before the harness-level retry kicks in.
        max_turns=16,
    )
    model = OpenAIChatModel(model_name, provider=provider)
    return Agent(model=model, skills_dir=SKILLS_DIR, config=cfg)


def _committed_move_from_result(tool_name: str, args: dict, result: Any) -> str | None:
    """Return the UCI move from a successful ``make_move.py`` result, or None.

    ``make_move.py`` prints ``{"ok": true, "move": "...", "message": ...}`` on
    success; the SDK wraps it as ``{"ok": ..., "stdout": "...", ...}``.
    """
    if tool_name != "run_script" or args.get("filename") != "make_move.py":
        return None
    if not isinstance(result, str):
        return None
    try:
        outer = json.loads(result)
        inner = json.loads(outer.get("stdout") or "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        return None
    if inner.get("ok") and inner.get("move"):
        return inner["move"]
    return None


def _looks_like_provider_400(exc: Exception) -> bool:
    """True for vLLM/OpenAI 400s caused by Gemma producing malformed tool-call
    JSON. The harness recovers by retrying the turn with cleared conversation."""
    msg = str(exc)
    bad_request = "400" in msg or "BadRequest" in msg or "status_code: 400" in msg
    json_parse = ("Expecting" in msg and "delimiter" in msg) or "JSONDecodeError" in msg
    return bad_request or json_parse


_BUDGET_REMINDER_TEMPLATE = (
    "**Budget warning:** in your previous attempt this turn you ran more than "
    "{threshold} tools without committing a move. Do not run an extended "
    "investigation this time. Pick the best move you can see — quickly — and "
    "call make_move.py.\n\n"
)


class AgentPlayer(Player):
    """White-only player backed by the skillful-agent SDK.

    Each ``get_move`` runs the model under per-turn fresh context. The turn
    ends when ``make_move.py`` commits a move (success), when every retry has
    been exhausted (resignation), or when an infrastructure error fires
    (context overflow → abort without ELO change).

    The UI consumes the event stream via ``event_sink``; see ``AgentPanel.tsx``
    for the rendering contract.
    """

    is_human = False

    def __init__(self, game_id: str, event_sink: Callable[[dict[str, Any]], None]) -> None:
        self._game_id = game_id
        self._event_sink = event_sink
        self._agent = _build_agent(game_id)

    async def get_move(self, board: chess.Board, last_san: str | None = None) -> chess.Move:
        from skill_agent import AgentContextOverflowError, TextDeltaEvent, ToolCallEvent, ToolResultEvent
        from pydantic_ai.exceptions import UsageLimitExceeded

        base_prompt = (
            f"Opponent played {last_san}.\n\nCurrent position (FEN):\n{board.fen()}"
            if last_san else
            f"Game start.\n\nCurrent position (FEN):\n{board.fen()}"
        )

        max_turns_cfg = getattr(self._agent._config, "max_turns", None) or 16
        warn_threshold = max(1, int(max_turns_cfg * _BUDGET_WARN_FRACTION))

        # Mutable per-turn state. Closures rather than self.* — these reset
        # naturally at the start of each get_move call.
        thinking_buf = ""
        warn_next_attempt = False

        def emit(event: dict[str, Any]) -> None:
            self._event_sink(event)

        def flush_thinking() -> None:
            """Emit the buffered chain-of-thought as one `thinking` event.

            The frontend has its own stripper as a defensive belt on the live
            text_delta stream; this strip is what guarantees the recorded
            *_agent.json contains clean reasoning prose."""
            nonlocal thinking_buf
            if not thinking_buf:
                return
            cleaned = _strip_gemma_channel_markers(thinking_buf).strip()
            if cleaned:
                emit({"type": "thinking", "content": cleaned})
            thinking_buf = ""

        emit({"type": "prompt", "content": base_prompt})

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            self._agent.clear_conversation()

            # Build this attempt's prompt — base_prompt, optionally prefixed
            # with a strong "commit now" reminder when the previous attempt
            # exceeded the budget threshold.
            if attempt > 1:
                emit({"type": "retry", "attempt": attempt})
                prompt = (
                    _BUDGET_REMINDER_TEMPLATE.format(threshold=warn_threshold) + base_prompt
                    if warn_next_attempt else base_prompt
                )
                emit({"type": "prompt", "content": prompt})
                warn_next_attempt = False
            else:
                prompt = base_prompt

            tool_call_count = 0
            budget_warning_emitted = False

            try:
                async for event in self._agent.run_stream(prompt):
                    if isinstance(event, TextDeltaEvent):
                        thinking_buf += event.content
                        emit({"type": "text_delta", "content": event.content})

                    elif isinstance(event, ToolCallEvent):
                        flush_thinking()
                        tool_call_count += 1
                        emit({
                            "type": "tool_call",
                            "tool": event.name,
                            "args": getattr(event, "args", {}),
                        })
                        if not budget_warning_emitted and tool_call_count >= warn_threshold:
                            budget_warning_emitted = True
                            warn_next_attempt = True
                            emit({
                                "type": "budget_warning",
                                "tool_calls": tool_call_count,
                                "threshold": warn_threshold,
                                "max_turns": max_turns_cfg,
                            })

                    elif isinstance(event, ToolResultEvent):
                        flush_thinking()
                        emit({"type": "tool_result", "tool": event.name, "result": event.result})
                        # Check directly against the result we just received,
                        # rather than scanning the SDK's tool_log. This works
                        # because the most recent tool_call's args are the
                        # ones that produced this result (the model is
                        # serially driven; no parallel tool calls).
                        if event.name == "run_script":
                            tool_log = self._agent._deps.tool_log
                            last_args = tool_log[-1].input if tool_log else {}
                            committed = _committed_move_from_result(event.name, last_args, event.result)
                            if committed is not None:
                                return chess.Move.from_uci(committed)

            except AgentContextOverflowError as exc:
                # Infrastructure limit — abort game with no ELO update.
                raise PlayerError(
                    f"context_overflow: requested {exc.requested_input_tokens} input "
                    f"tokens, model limit {exc.model_context_limit}."
                ) from exc

            except UsageLimitExceeded:
                # Hit max_turns without committing — by definition past the
                # warning threshold, so flag the next attempt.
                flush_thinking()
                warn_next_attempt = True
                continue

            except Exception as exc:
                if _looks_like_provider_400(exc):
                    flush_thinking()
                    emit({"type": "provider_error_recovered", "message": str(exc)[:300]})
                    continue
                raise

            flush_thinking()
            # Run ended without a committed move — loop to the next attempt.

        raise AgentResignedError(
            f"agent_resigned_no_move: no legal move committed after {_MAX_ATTEMPTS} attempts."
        )
