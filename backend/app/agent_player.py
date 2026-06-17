"""AgentPlayer: skillful-agent backed chess player for the white side.

Memory model (blocklist, since 2026-06-12): the conversation PERSISTS across
turns within a game — the skill stays loaded, wiki pages the agent read stay
in context, the system prompt is always present. A pydantic-ai history
processor prunes what is provably stale before every model request: old
perception-tool dumps are collapsed to a marker, old thinking text is
truncated. See ``_make_pruning_processor`` for the exact keep/drop sets.

The agent still authors two explicit memory channels on ``make_move``:
``reasoning`` (its note, kept in history naturally) and ``plan`` (the
standing plan, tracked in ``TurnMemory`` and re-stated in every turn prompt
together with the legal-move list).

``clear_conversation()`` is only called between games, not between turns.

Decision trail: 2026-05-24-per-turn-fresh-context (baseline) →
2026-05-26-agent-turn-memory (single note) → 2026-06-10-structured-turn-memory
(plan channel + system-prompt-loss fix) → this blocklist model (persistent
pruned context; motivated by repetitions/phantom pieces/illegal moves traced
to per-turn re-derivation of the position).
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
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
    "On your FIRST turn of the game, call use_skill('chess') — it contains "
    "all instructions for how to play and reveals the chess tools "
    "(chess__show_position, chess__imagine_move, chess__make_move, and "
    "others). The skill and its instructions STAY LOADED for the whole "
    "game — do not reload it on later turns unless the chess__ tools are "
    "missing from your tool list. Earlier turns of this game remain in your "
    "context; stale tool outputs from previous turns are pruned and marked "
    "as such — re-run a tool if you need fresh eyes on the position. "
    "**PAWN WARNINGS:** The position radar will warn you about opponent passed pawns, "
    "especially ones 1–2 moves from promotion. When imagining your move, if the output says "
    "'PAWN PROMOTION WARNING', it means opponent CAN promote after your move — examine the "
    "opponent's legal replies carefully. If they have ANY safe move (not check, not mate for you), "
    "they promote and you likely lose. Only play moves that allow promotion if it delivers "
    "checkmate to them or forces mate faster than stopping the pawn. "
    "**CRITICAL — WIKI READING ON MOVE 1:** After calling use_skill, call `chess__show_position` "
    "to see the board and the radar. The radar will name specific wiki pages to read (e.g., "
    "'two-rook-mate', 'ladder-mate'). IMMEDIATELY read the page it names BEFORE doing anything else. "
    "For example, if the radar says 'read endgames/two-rook-mate.md', call "
    "`read_reference(skill_name=\"chess\", path=\"endgames/two-rook-mate.md\")` and study the "
    "\"What to do\" drill before you plan or move. The wiki page has the EXACT technique you need. "
    "This is not optional — read it first, then plan, then move. "
    "**RE-READ WHEN MATERIAL CHANGES - MANDATORY:** Every turn, check your standing plan (shown "
    "at the start of the turn). If your plan says 'K+2R herding' but you now have only K+R (one rook), "
    "your plan is STALE. IMMEDIATELY: (1) call `read_reference(skill_name=\"chess\", "
    "path=\"endgames/king-rook-mate.md\")` to learn K+R technique (fence-and-opposition, completely "
    "different), (2) update your plan to name the K+R technique, then move. Do NOT skip this step. "
    "Your instinct says 'I know how to play king and rook', but K+R requires a specific drill "
    "(opposite corner, then fence). Herding does not work. Wiki pages stay in your context; "
    "re-reading is FREE. Check your plan every turn — material changes invalidate it. "
    "**IMPORTANT: On move 1, after reading the wiki page, write a standing plan via the `plan` argument. "
    "The plan must be 2–3 sentences that name: (1) the mating pattern or "
    "objective (e.g., 'Ladder mate: drive king to rank 8'), (2) the immediate "
    "tactical aim for the next 2–3 moves (e.g., 'eliminate passed pawns first, "
    "then coordinate rooks'), and (3) your target edge/rank for the king. "
    "Refer to this plan EXPLICITLY on every subsequent move before playing "
    "(e.g., 'Per my plan: eliminate threats, now playing X'). Update the plan "
    "each time your position or tactic changes, not just once. Every move "
    "requires you to write a DETAILED reasoning line (2–3 sentences minimum) "
    "that cites your plan and explains what threat you are addressing or what "
    "progress you are making. Write so a reader can verify you knew what you "
    "were doing. "
    "**CRITICAL FOR MATING PATTERNS: When you have read the ladder-mate page, "
    "follow its instructions precisely. If a move would hang a rook but the "
    "opponent's ONLY reply gives check/mate (or loses material), PLAY IT—do not "
    "flinch. Check the opponent's legal replies in the imagine_move output; if "
    "all replies are bad for them, the hanging piece is irrelevant. This is how "
    "rook ladders and mating nets work: you push through temporary threats because "
    "the opponent has no good answer. Count the replies: if the only move preserves "
    "the king's position (moving into check), you proceed. Hesitating and changing "
    "moves turns a 5-move mate into a 50-move grind."
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
        max_turns=24,
        history_processors=[history_processor] if history_processor is not None else [],
    )
    model = OpenAIChatModel(model_name, provider=provider)
    return Agent(model=model, skills_dir=SKILLS_DIR, config=cfg)


# The make_move script is exposed as this typed tool after use_skill.
# (skillful-agent registers each scripts/<name>.py as ``<skill>__<name>``.)
_MAKE_MOVE_TOOL = "chess__make_move"


def _committed_move_from_result(
    tool_name: str, result: Any
) -> dict[str, Any] | None:
    """Return the inner payload dict from a successful ``chess__make_move``
    result, or None. Carries ``move``, ``reasoning``, and the optional memory
    channels ``plan``, ``goal``, and ``dismissed_references``.

    ``make_move.py`` prints ``{"ok": true, "move": "...", "reasoning": "...",
    "plan": ..., ...}`` on success; the script-tool handler wraps it as
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
        return inner
    return None


def _result_says_game_vanished(result: Any) -> bool:
    """True when a chess tool result indicates the backend no longer has the
    game (deleted, superseded, or finished out from under the agent). Without
    this check the turn loop burns all its attempts re-asking a dead game for
    state — observed as a 10-attempt 404 cascade in game 291e7938 (2026-06-12)."""
    if not isinstance(result, str):
        return False
    return "Game not found" in result or "HTTP Error 404" in result


def _looks_like_provider_400(exc: Exception) -> bool:
    """True for vLLM/OpenAI 400s caused by Gemma producing malformed tool-call
    JSON. The harness recovers by retrying the turn with cleared conversation."""
    msg = str(exc)
    bad_request = "400" in msg or "BadRequest" in msg or "status_code: 400" in msg
    json_parse = ("Expecting" in msg and "delimiter" in msg) or "JSONDecodeError" in msg
    return bad_request or json_parse


def _looks_like_transient_network(exc: Exception) -> bool:
    """True for network blips between laptop and eX3 (the SSH tunnel
    stalling or dropping mid-stream). These deserve a retry attempt, not a
    game abort: the position is unchanged and the next attempt opens a
    fresh connection. Persistent outages still abort once the per-turn
    attempt budget is exhausted."""
    name = type(exc).__name__
    msg = str(exc)
    return (
        "ReadTimeout" in name or "ReadTimeout" in msg
        or "ConnectTimeout" in name
        or "APIConnectionError" in name
        or "Connection error" in msg
        or "ConnectionResetError" in name
    )


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
# Turn memory is agent-authored and structured. make_move.py requires
# --reasoning (the note about this move) and accepts an optional --plan (the
# standing multi-move plan). The harness stores both in a TurnMemory without
# any further LLM processing, and renders them back as the agent's own prior
# message at the start of every subsequent attempt.
#
# Retention policy (deliberately aggressive — the reader is a weak model):
#   kept      : standing plan (until replaced/cleared), last move + note,
#               previous turn's prompt (opponent move + FEN).
#   forgotten : everything else — older notes, tool transcripts, failed
#               attempts. The FEN is the complete game state; the radar in
#               show_position covers repetition/draw-rule history.


@dataclass
class TurnMemory:
    """Curated cross-turn memory for one game."""

    plan: str | None = None
    plan_move: int | None = None        # fullmove number when the plan was set
    goal: str | None = None             # short-term objective (next 1-3 moves)
    goal_move: int | None = None        # fullmove number when the goal was set
    last_prompt: str | None = None      # previous turn's user prompt
    last_reasoning: str | None = None   # agent's note at last commit
    last_move_uci: str | None = None
    last_move_number: int | None = None
    # Wiki pages the agent has dismissed as no-longer-relevant. The pruning
    # processor collapses their read_reference results from the next model
    # request onward. "all" (the literal string) wipes every page read so far.
    dismissed_refs: set[str] | None = None
    # Set by get_move before each run_stream attempt; consumed by the history
    # processor on the attempt's first model request. Within-attempt requests
    # (tool-call loops) pass through so the in-flight conversation survives.
    armed: bool = False

    _CLEAR_WORDS = frozenset({"none", "no plan", "no goal", "clear", "-", ""})

    def record_commit(
        self, *, prompt: str, uci: str, reasoning: str,
        plan: str | None, move_number: int,
        goal: str | None = None, dismissed: list[str] | None = None,
    ) -> None:
        self.last_prompt = prompt
        self.last_reasoning = reasoning
        self.last_move_uci = uci
        self.last_move_number = move_number
        if plan is not None:
            cleaned = plan.strip()
            if cleaned.lower() in self._CLEAR_WORDS:
                self.plan = None
                self.plan_move = None
            else:
                self.plan = cleaned
                self.plan_move = move_number
        if goal is not None:
            cleaned = goal.strip()
            if cleaned.lower() in self._CLEAR_WORDS:
                self.goal = None
                self.goal_move = None
            else:
                self.goal = cleaned
                self.goal_move = move_number
        if dismissed:
            if self.dismissed_refs is None:
                self.dismissed_refs = set()
            for path in dismissed:
                cleaned = path.strip().lstrip("/")
                if cleaned.startswith("references/"):
                    cleaned = cleaned[len("references/"):]
                if cleaned:
                    self.dismissed_refs.add(cleaned)

    def has_memory(self) -> bool:
        return self.last_prompt is not None

    def render_note(self) -> str:
        """The synthetic assistant message: the agent's memory in its own
        voice. Kept short by construction — one note plus one plan."""
        parts: list[str] = []
        if self.last_reasoning:
            parts.append(
                f"My note on the move I just played ({self.last_move_uci}): "
                f"{self.last_reasoning}"
            )
        if self.plan:
            age = ""
            if (
                self.last_move_number is not None
                and self.plan_move is not None
                and self.last_move_number - self.plan_move >= 10
            ):
                age = (
                    f", {self.last_move_number - self.plan_move} moves ago — "
                    f"I should check it still fits the position"
                )
            parts.append(
                f"My standing plan (set on move {self.plan_move}{age}): {self.plan}"
            )
        else:
            parts.append(
                "I have no standing plan. Unless a tactic decides this move, "
                "I should form one and record it via the plan argument of "
                "chess__make_move."
            )
        return "\n\n".join(parts)


def _make_pruning_processor(memory: TurnMemory):
    """Blocklist memory: the conversation persists across turns; this
    processor only PRUNES what is provably stale, before every model
    request.

    Kept in full: the system prompt, every user prompt, tool calls
    (names+args), make_move results, use_skill output (the skill stays
    loaded), and read_reference results (theory the agent chose to read
    stays available). Pruned: perception-tool outputs from earlier turns
    (show_position / imagine_move / list_legal_moves dumps describe stale
    positions and dominate token count), and old thinking text is truncated
    to its head. The current turn (everything after the last user prompt)
    is never touched.

    Rationale (2026-06-12 session review): the previous allowlist memory
    forced the model to re-derive the position every turn, producing
    repetitions, phantom pieces, and illegal moves. Persistent-but-pruned
    context keeps theory and intentions while preventing overflow.
    """
    from pydantic_ai.messages import (
        ModelRequest, ModelResponse, TextPart, ToolCallPart, ToolReturnPart,
        UserPromptPart,
    )
    import dataclasses

    KEEP_TOOLS = ("use_skill", "read_reference", "chess__make_move", "chess__search_wiki")
    PRUNED_NOTE = "[stale output from an earlier turn pruned - re-run the tool for the current position]"
    DISMISSED_NOTE = "[wiki page dismissed by you as no longer relevant - re-read it with read_reference if it becomes relevant again]"
    # Old thinking text is kept up to this length; the head usually carries
    # the conclusion ("I will play X because..."), the tail the rambling.
    THINKING_KEEP = 600

    def _ref_path_of_call(pt) -> str | None:
        """Wiki path from a read_reference ToolCallPart, normalised the same
        way TurnMemory.record_commit normalises dismissals."""
        args = pt.args
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except (json.JSONDecodeError, TypeError):
                return None
        if not isinstance(args, dict):
            return None
        path = str(args.get("path") or "").strip().lstrip("/")
        if path.startswith("references/"):
            path = path[len("references/"):]
        return path or None

    def processor(messages):
        # Find the start of the current turn: the last ModelRequest that
        # carries a UserPromptPart.
        last_user_idx = 0
        for i, m in enumerate(messages):
            if isinstance(m, ModelRequest) and any(
                isinstance(pt, UserPromptPart) for pt in m.parts
            ):
                last_user_idx = i

        # Map read_reference tool_call_ids to wiki paths so dismissals (which
        # name paths) can find the results to collapse.
        dismissed = memory.dismissed_refs or set()
        dismissed_call_ids: set[str] = set()
        if dismissed:
            wipe_all = "all" in dismissed
            for m in messages:
                if not isinstance(m, ModelResponse):
                    continue
                for pt in m.parts:
                    if isinstance(pt, ToolCallPart) and pt.tool_name == "read_reference":
                        path = _ref_path_of_call(pt)
                        if wipe_all or (path is not None and path in dismissed):
                            dismissed_call_ids.add(pt.tool_call_id)

        out = []
        for i, m in enumerate(messages):
            if i >= last_user_idx:
                out.append(m)
                continue
            if isinstance(m, ModelRequest):
                parts = []
                for pt in m.parts:
                    if isinstance(pt, ToolReturnPart) and isinstance(pt.content, str):
                        if pt.tool_call_id in dismissed_call_ids:
                            pt = dataclasses.replace(pt, content=DISMISSED_NOTE)
                        elif pt.tool_name not in KEEP_TOOLS and len(pt.content) > 400:
                            pt = dataclasses.replace(pt, content=PRUNED_NOTE)
                    parts.append(pt)
                out.append(dataclasses.replace(m, parts=parts))
            elif isinstance(m, ModelResponse):
                parts = []
                for pt in m.parts:
                    if isinstance(pt, TextPart) and len(pt.content) > THINKING_KEEP:
                        pt = dataclasses.replace(
                            pt, content=pt.content[:THINKING_KEEP - 20] + " [truncated]"
                        )
                    parts.append(pt)
                out.append(dataclasses.replace(m, parts=parts))
            else:
                out.append(m)
        return out

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
        # Structured cross-turn memory (standing plan + last note). Updated
        # at each successful commit; rendered into the synthetic prior
        # exchange by the history processor at the start of each attempt.
        self._memory = TurnMemory()
        processor = _make_pruning_processor(self._memory)
        self._agent = _build_agent(game_id, history_processor=processor)

    async def get_move(self, board: chess.Board, last_san: str | None = None) -> chess.Move:
        from skill_agent import AgentContextOverflowError, TextDeltaEvent, ToolCallEvent, ToolResultEvent
        from pydantic_ai.exceptions import UsageLimitExceeded

        # Re-assert ownership of the process-global script env every turn.
        # Skill scripts read CHESS_GAME_ID from os.environ at exec time; if
        # another AgentPlayer was built since (game replaced mid-turn), the
        # var points at the wrong game and commits cross games. Belt to the
        # GameService._teardown braces.
        os.environ["CHESS_GAME_ID"] = self._game_id
        os.environ["CHESS_API_BASE"] = API_BASE

        legal_sans = [board.san(m) for m in board.legal_moves]
        legal_line = ", ".join(legal_sans[:90])
        plan_line = (
            f"\nYour standing plan (long-term, set on move {self._memory.plan_move}): "
            f"{self._memory.plan}"
            if self._memory.plan else ""
        )
        goal_line = (
            f"\nYour current goal (short-term, set on move {self._memory.goal_move}): "
            f"{self._memory.goal}"
            if self._memory.goal else ""
        )
        # After turn 1 the chess skill is already loaded and its chess__*
        # tools are live. The SDK's own system prompt says "always use_skill
        # before a skill's work", which the model obeys ritually every turn —
        # wasting a tool call and a round-trip (34 of 35 turns in game
        # 9b0d7590). Reassert here, at the point of action, that it is loaded
        # and must NOT be called again.
        skill_line = (
            ""
            if last_san is None
            else (
                "\n\nThe `chess` skill is ALREADY loaded and its chess__ tools "
                "are live — do NOT call use_skill again. Go straight to "
                "chess__show_position."
            )
        )
        # The turn prompt carries only bare facts (whose move, the FEN, the
        # legal moves) plus the agent's own standing plan/goal. It deliberately
        # does NOT analyse the position or hint at moves — all of that (the
        # mate/draw radar, the basic-mate drill state, threats) comes from the
        # agent's TOOLS (chess__show_position), so the prompt stays a neutral
        # "your turn" and the model does the reasoning via the tools.
        base_prompt = (
            (f"Opponent played {last_san}." if last_san else "Game start.")
            + f"\n\nCurrent position (FEN):\n{board.fen()}"
            + f"\nLegal moves: {legal_line}"
            + plan_line
            + goal_line
            + skill_line
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
                        # A dead game means no number of retries can produce
                        # a move — abort the game instead of looping through
                        # the attempt budget against 404s.
                        if (
                            event.name.startswith("chess__")
                            and _result_says_game_vanished(event.result)
                        ):
                            raise PlayerError(
                                "game_vanished: backend no longer has this game "
                                "(404/Game not found from a chess tool)."
                            )
                        # Check directly against the result we just received,
                        # rather than scanning the SDK's tool_log. This works
                        # because the most recent tool_call's args are the
                        # ones that produced this result (the model is
                        # serially driven; no parallel tool calls).
                        if event.name == _MAKE_MOVE_TOOL:
                            inner = _committed_move_from_result(event.name, event.result)
                            if inner is not None:
                                committed_uci = inner["move"]
                                reasoning = inner.get("reasoning", "")
                                flush_thinking()
                                # Memory update fires only on a successful
                                # commit: the note replaces last turn's; the
                                # plan/goal persist unless the agent wrote new
                                # ones. The processor renders both at the
                                # start of the next turn's first attempt.
                                self._memory.record_commit(
                                    prompt=base_prompt,
                                    uci=committed_uci,
                                    reasoning=reasoning,
                                    plan=inner.get("plan") or None,
                                    goal=inner.get("goal") or None,
                                    dismissed=inner.get("dismissed_references") or None,
                                    move_number=board.fullmove_number,
                                )
                                emit({
                                    "type": "context_summary",
                                    "content": reasoning,
                                    "plan": self._memory.plan,
                                    "goal": self._memory.goal,
                                })
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

            except PlayerError:
                raise  # game_vanished and friends — never retried as transient

            except Exception as exc:
                if _looks_like_provider_400(exc) or _looks_like_transient_network(exc):
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
