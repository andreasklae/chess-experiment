"""AgentPlayer: skillful-agent backed chess player for the white side.

A turn proceeds as a sequence of ``run_stream`` calls (attempts). On the very
first turn of a game the conversation is empty. On subsequent turns, the
conversation carries the agent's own reasoning from the previous turn as the
sole prior context ("turn memory").

Turn memory is agent-authored: ``make_move.py`` requires a ``--reasoning``
argument. The agent writes whatever it wants there — intent, rejected
candidates, threats to watch, ongoing plans. On success the script echoes the
reasoning back in the response JSON; the harness stores it in ``_pending_summary``
without any further LLM processing.

Injection is done via a pydantic-ai ``HistoryProcessor`` registered on the game
agent at construction time. The processor reads from ``_pending_summary``: if a
note is waiting, it replaces the incoming message history with a minimal
two-message exchange (prior-turn prompt → agent's reasoning) and clears the
slot. This fires before every ``run_stream_events`` call — including retries
within a turn — so failed attempts see the correct prior-turn context with no
manual reset needed.

``clear_conversation()`` is only called between games, not between turns.

See ``decisions/2026-05-24-per-turn-fresh-context.md`` for the original
per-turn fresh-context baseline, ``2026-05-25-agent-resigns-when-stuck.md``
for the resignation policy, ``2026-05-26-stabilization.md`` for the
budget-warning mechanism, and ``2026-05-26-agent-turn-memory.md`` for the
agent-authored turn memory decision.
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
# stabilization testing. After use_skill, the chess agent's surface is the
# skill's own scripts (exposed as typed tools chess__show_position,
# chess__make_move, …) plus read_reference for the knowledge wiki.
_DISABLED_TOOLS = [
    "manage_todos",          # no plan/todo workflow needed for chess
    "register_skill",
    "scaffold_skill",
    "write_skill_file",
    "list_skill_files",      # wiki is navigated via its index pages, not a flat file list
    "call_client_function",
    "compress_message",      # compaction is harness-driven, not agent-driven
    "retrieve_message",
    "compress_all",
    "read_thread",           # no inter-agent threads
    "reply_to_thread",
    "archive_thread",
    "spawn_agent",
]
# read_reference is intentionally NOT disabled: it is how the agent reads
# wiki pages (path-based since skillful-agent @435fa8d). search_wiki.py
# (a skill script, exposed as chess__search_wiki) finds pages by keyword;
# read_reference reads the page body.

_SYSTEM_PROMPT_EXTRA = (
    "You are playing chess as white. "
    "Your FIRST action every turn must be to call use_skill('chess') — "
    "it contains all instructions for how to play, and loading it reveals "
    "the chess tools (chess__show_position, chess__imagine_move, "
    "chess__make_move, and others). Do not call any chess__ tool before you "
    "have called use_skill."
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

def _build_agent(game_id: str, history_processor=None):
    """Create a skillful-agent Agent for one chess game.

    ``CHESS_GAME_ID`` and ``CHESS_API_BASE`` are injected into the environment
    so skill scripts can read live state without taking CLI arguments.

    ``history_processor`` is an optional pydantic-ai HistoryProcessor callable
    registered on the agent to inject the prior-turn summary before every
    model request.

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
        from pydantic_ai.models.openai import OpenAIModelProfile
        provider = OpenAIProvider(base_url=ex3_base_url, api_key="dummy")
        model_name = os.getenv("SKILL_AGENT_OPENAI_MODEL", "google/gemma-4-31B-it")
        # vLLM / Gemma 4: disable strict tool definitions and tool_choice=required.
        # The default OpenAI profile sends both; vLLM does not support strict, and
        # tool_choice=required behaviour is undefined for Gemma. These cause
        # intermittent HTTP 400 errors with malformed JSON messages.
        model_profile = OpenAIModelProfile(
            openai_supports_strict_tool_definition=False,
            openai_supports_tool_choice_required=False,
        )
    elif azure_endpoint:
        from pydantic_ai.providers.azure import AzureProvider
        provider = AzureProvider(
            azure_endpoint=azure_endpoint,
            api_version=os.getenv("SKILL_AGENT_AZURE_API_VERSION", "2024-07-01-preview"),
            api_key=os.environ["SKILL_AGENT_AZURE_API_KEY"],
        )
        model_name = os.getenv("SKILL_AGENT_OPENAI_MODEL", "gpt-4o-mini")
        model_profile = None
    else:
        from pydantic_ai.providers.openai import OpenAIProvider
        provider = OpenAIProvider(api_key=os.environ["OPENAI_API_KEY"])
        model_name = os.getenv("SKILL_AGENT_OPENAI_MODEL", "gpt-4o-mini")
        model_profile = None

    cfg = AgentConfig(
        disabled_tools=_DISABLED_TOOLS,
        disable_native_skills=True,           # skip web-search-free etc.
        system_prompt_extra=_SYSTEM_PROMPT_EXTRA,
        # Per-response output cap. Reasoning text + one tool call. 2048 gives
        # the model enough room to write a thinking paragraph before calling a
        # tool; 1024 was too tight and caused the model to skip reasoning
        # entirely to fit the tool call under the cap.
        max_tokens=2048,
        # Per-run request cap. A thorough turn uses 4–9 requests (use_skill +
        # show_position + 1–3 imagine_move + make_move, with reasoning text
        # between). 16 leaves headroom for one or two illegal-move retries
        # inside a single run_stream before the harness-level retry kicks in.
        max_turns=16,
        history_processors=[history_processor] if history_processor is not None else [],
    )
    model = OpenAIChatModel(model_name, provider=provider)
    return Agent(model=model, skills_dir=SKILLS_DIR, config=cfg)


# The make_move script is exposed as this typed tool after use_skill.
# (skillful-agent registers each scripts/<name>.py as ``<skill>__<name>``.)
_MAKE_MOVE_TOOL = "chess__make_move"


def _committed_move_from_result(
    tool_name: str, result: Any
) -> tuple[str, str] | None:
    """Return ``(uci, reasoning)`` from a successful ``chess__make_move`` result, or None.

    ``make_move.py`` prints ``{"ok": true, "move": "...", "reasoning": "...", ...}``
    on success; the script-tool handler wraps it as
    ``{"ok": ..., "stdout": "...", ...}``. Detection keys on the tool name and
    the result payload — not on call args — because typed script tools do not
    record their input to ``tool_log``.
    """
    if tool_name != _MAKE_MOVE_TOOL:
        return None
    if not isinstance(result, str):
        return None
    try:
        outer = json.loads(result)
        inner = json.loads(outer.get("stdout") or "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        return None
    if inner.get("ok") and inner.get("move"):
        return inner["move"], inner.get("reasoning", "")
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

_NO_MOVE_REMINDER_TEMPLATE = (
    "**You did not submit a move in your previous attempt.** "
    "You MUST call `make_move.py` with `args=[<move>, <reasoning>]` before your "
    "turn ends. Describing a move in text is not enough — use the tool.\n\n"
    "{prior_reasoning}"
)

# ── Turn memory ───────────────────────────────────────────────────────────
#
# Turn memory is agent-authored. make_move.py requires a --reasoning argument;
# the agent writes its own note there (intent, rejected candidates, threats,
# ongoing plans). On success the script echoes reasoning back in the response
# JSON; the harness stores it in ``_pending_summary`` without any further LLM
# processing.
#
# A HistoryProcessor registered on the game agent reads ``_pending_summary``
# before every model request: if a note is waiting, it replaces the incoming
# message history with a minimal two-message exchange (prior-turn prompt →
# agent's reasoning) and clears the slot. This fires automatically on every
# run_stream_events call, including retries, so no manual history reset is
# needed between attempts.


def _make_turn_memory_processor(pending: list):
    """Return a HistoryProcessor that injects the pending turn memory.

    ``pending`` is a one-element list used as a mutable container:
      - Empty    → no prior turn; pass history through unchanged.
      - [(p, r)] → ``p`` is the original prompt, ``r`` is the agent's
                   reasoning from --reasoning; replace the entire incoming
                   message history with the minimal two-message exchange and
                   clear the slot.

    Fires before every ``run_stream_events`` call (including retries within a
    turn), so the correct prior-turn context is always in place.
    """
    from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

    def processor(messages):
        if not pending:
            return messages
        current_request = messages[-1]
        original_prompt, reasoning = pending[0]
        pending.clear()
        return [
            ModelRequest(parts=[UserPromptPart(content=original_prompt)]),
            ModelResponse(parts=[TextPart(content=reasoning)]),
            current_request,
        ]

    return processor


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
        # Shared mutable slot used to pass the prior-turn summary to the
        # HistoryProcessor. Empty at game start and after the processor
        # consumes it. Set by _compact_turn after each committed move.
        self._pending_summary: list = []
        processor = _make_turn_memory_processor(self._pending_summary)
        self._agent = _build_agent(game_id, history_processor=processor)

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
        no_move_attempt = False  # previous attempt ended cleanly but without make_move
        prior_attempt_thinking: str = ""  # thinking text from the last attempt

        def emit(event: dict[str, Any]) -> None:
            self._event_sink(event)

        def flush_thinking() -> None:
            """Emit the buffered chain-of-thought as one `thinking` event.

            The frontend has its own stripper as a defensive belt on the live
            text_delta stream; this strip is what guarantees the recorded
            *_agent.json contains clean reasoning prose."""
            nonlocal thinking_buf, prior_attempt_thinking
            if not thinking_buf:
                return
            cleaned = _strip_gemma_channel_markers(thinking_buf).strip()
            if cleaned:
                emit({"type": "thinking", "content": cleaned})
                prior_attempt_thinking = cleaned
            thinking_buf = ""

        emit({"type": "prompt", "content": base_prompt})

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            # Build this attempt's prompt — base_prompt, optionally prefixed
            # with a reminder based on why the previous attempt failed.
            if attempt > 1:
                emit({"type": "retry", "attempt": attempt})
                if warn_next_attempt:
                    prefix = _BUDGET_REMINDER_TEMPLATE.format(threshold=warn_threshold)
                elif no_move_attempt:
                    prior = (
                        f"Your reasoning from the previous attempt:\n{prior_attempt_thinking}\n\n"
                        if prior_attempt_thinking else ""
                    )
                    prefix = _NO_MOVE_REMINDER_TEMPLATE.format(prior_reasoning=prior)
                else:
                    prefix = ""  # provider_error_recovered — just retry
                prompt = prefix + base_prompt
                emit({"type": "prompt", "content": prompt})
                warn_next_attempt = False
                no_move_attempt = False
                prior_attempt_thinking = ""
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
                        if event.name == _MAKE_MOVE_TOOL:
                            result = _committed_move_from_result(event.name, event.result)
                            if result is not None:
                                committed_uci, reasoning = result
                                flush_thinking()
                                # Compaction fires only on a successful commit.
                                # Store the agent's own reasoning as the
                                # turn memory; the HistoryProcessor will
                                # inject it as prior-turn context before the
                                # next get_move call.
                                self._pending_summary[:] = [(base_prompt, reasoning)]
                                emit({"type": "context_summary", "content": reasoning})
                                # ``committed_uci`` here is the canonical UCI
                                # returned by ``/agent-commit`` — already
                                # validated against the live board, so a bare
                                # from_uci is safe. The bot loop will push
                                # this move; the board has NOT yet advanced
                                # at this point (the endpoint is validation-
                                # only).
                                return chess.Move.from_uci(committed_uci)

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
            # Run ended cleanly but without a committed move.
            no_move_attempt = True

        raise AgentResignedError(
            f"agent_resigned_no_move: no legal move committed after {_MAX_ATTEMPTS} attempts."
        )
