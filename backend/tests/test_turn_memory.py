"""Tests for the structured turn memory (TurnMemory + history processor).

Covers the retention policy (plan persists, notes replace, everything else
is forgotten), the rendering, the per-attempt injection contract, and — as a
regression test — that the synthetic history carries the system prompt
(the previous implementation silently dropped it from turn 2 onward).
"""

import json

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)

from app.agent_player import (
    TurnMemory,
    _committed_move_from_result,
    _make_turn_memory_processor,
)


def commit(memory, move_number, uci="e2e4", reasoning="note", plan=None, prompt="prompt"):
    memory.record_commit(
        prompt=prompt, uci=uci, reasoning=reasoning, plan=plan, move_number=move_number
    )


class TestTurnMemoryState:
    def test_plan_persists_when_omitted(self):
        m = TurnMemory()
        commit(m, 5, plan="promote the a-pawn")
        commit(m, 6, plan=None)
        commit(m, 7, plan=None)
        assert m.plan == "promote the a-pawn"
        assert m.plan_move == 5

    def test_plan_replaced_when_given(self):
        m = TurnMemory()
        commit(m, 5, plan="old plan")
        commit(m, 9, plan="new plan")
        assert m.plan == "new plan"
        assert m.plan_move == 9

    def test_plan_cleared_with_none_word(self):
        m = TurnMemory()
        commit(m, 5, plan="old plan")
        commit(m, 6, plan="none")
        assert m.plan is None

    def test_note_is_replaced_each_commit(self):
        m = TurnMemory()
        commit(m, 5, reasoning="first note")
        commit(m, 6, reasoning="second note")
        assert m.last_reasoning == "second note"
        assert "first note" not in m.render_note()

    def test_no_memory_at_game_start(self):
        assert TurnMemory().has_memory() is False


class TestRenderNote:
    def test_renders_note_and_plan(self):
        m = TurnMemory()
        commit(m, 12, uci="a5a6", reasoning="pushed the passer", plan="promote the a-pawn")
        text = m.render_note()
        assert "a5a6" in text and "pushed the passer" in text
        assert "standing plan (set on move 12" in text
        assert "promote the a-pawn" in text

    def test_old_plan_gets_age_warning(self):
        m = TurnMemory()
        commit(m, 5, plan="promote the a-pawn")
        commit(m, 20)
        assert "15 moves ago" in m.render_note()

    def test_fresh_plan_has_no_age_warning(self):
        m = TurnMemory()
        commit(m, 5, plan="promote the a-pawn")
        commit(m, 7)
        assert "moves ago" not in m.render_note()

    def test_no_plan_nudges_to_form_one(self):
        m = TurnMemory()
        commit(m, 5)
        assert "no standing plan" in m.render_note().lower()


class TestProcessor:
    def _messages(self):
        return [
            ModelRequest(parts=[SystemPromptPart(content="SYS"), UserPromptPart(content="turn 1")]),
            ModelResponse(parts=[TextPart(content="old stuff")]),
            ModelRequest(parts=[UserPromptPart(content="turn 2 prompt")]),
        ]

    def test_armed_with_memory_replaces_history(self):
        m = TurnMemory()
        commit(m, 3, prompt="turn 1", reasoning="my note", plan="my plan")
        m.armed = True
        proc = _make_turn_memory_processor(m, lambda: "SYS")
        out = proc(self._messages())
        assert len(out) == 3
        sys_parts = [p for p in out[0].parts if isinstance(p, SystemPromptPart)]
        assert sys_parts and sys_parts[0].content == "SYS"
        assert isinstance(out[1], ModelResponse)
        assert "my note" in out[1].parts[0].content
        assert "my plan" in out[1].parts[0].content
        # current request preserved as the last message
        assert out[2].parts[-1].content == "turn 2 prompt"

    def test_disarms_after_first_request(self):
        m = TurnMemory()
        commit(m, 3)
        m.armed = True
        proc = _make_turn_memory_processor(m, lambda: "SYS")
        proc(self._messages())
        msgs = self._messages()
        assert proc(msgs) is msgs  # passthrough for within-attempt requests

    def test_unarmed_passes_through(self):
        m = TurnMemory()
        commit(m, 3)
        proc = _make_turn_memory_processor(m, lambda: "SYS")
        msgs = self._messages()
        assert proc(msgs) is msgs

    def test_no_memory_passes_through(self):
        m = TurnMemory()
        m.armed = True
        proc = _make_turn_memory_processor(m, lambda: "SYS")
        msgs = self._messages()
        assert proc(msgs) is msgs


class TestSystemPromptRegression:
    """Turn 2+ requests must carry the system prompt. The pre-2026-06-10
    injection rebuilt history without a SystemPromptPart, so the model
    received no system prompt after turn 1."""

    def test_turn_two_request_has_system_prompt(self):
        captured = []

        def model_fn(messages, info):
            captured.append(list(messages))
            return ModelResponse(parts=[TextPart(content="ok")])

        memory = TurnMemory()
        proc = _make_turn_memory_processor(memory, lambda: "SYSTEM PROMPT")
        try:
            from pydantic_ai.capabilities import ProcessHistory as Cap
        except ImportError:  # pydantic-ai 1.x name
            from pydantic_ai.capabilities import HistoryProcessor as Cap

        agent = Agent(
            FunctionModel(model_fn),
            system_prompt="SYSTEM PROMPT",
            capabilities=[Cap(proc)],
        )
        memory.armed = True
        r1 = agent.run_sync("turn 1 prompt")
        commit(memory, 1, prompt="turn 1 prompt", reasoning="note 1", plan="the plan")
        memory.armed = True
        agent.run_sync("turn 2 prompt", message_history=r1.all_messages())

        turn2 = captured[-1]
        sys_present = any(
            isinstance(p, SystemPromptPart)
            for msg in turn2
            if isinstance(msg, ModelRequest)
            for p in msg.parts
        )
        assert sys_present, "system prompt missing from turn-2 request"
        # and the memory exchange is present
        joined = " ".join(
            p.content
            for msg in turn2
            if isinstance(msg, ModelResponse)
            for p in msg.parts
            if isinstance(p, TextPart)
        )
        assert "the plan" in joined


class TestCommitParsing:
    def _wrap(self, inner: dict) -> str:
        return json.dumps({"ok": True, "stdout": json.dumps(inner), "stderr": "", "exit_code": 0})

    def test_parses_plan(self):
        result = self._wrap({"ok": True, "move": "e2e4", "reasoning": "r", "plan": "p"})
        assert _committed_move_from_result("chess__make_move", result) == ("e2e4", "r", "p")

    def test_missing_plan_is_none(self):
        result = self._wrap({"ok": True, "move": "e2e4", "reasoning": "r", "plan": None})
        assert _committed_move_from_result("chess__make_move", result) == ("e2e4", "r", None)

    def test_failed_commit_returns_none(self):
        result = self._wrap({"ok": False, "error": "illegal"})
        assert _committed_move_from_result("chess__make_move", result) is None

    def test_other_tool_returns_none(self):
        assert _committed_move_from_result("chess__show_position", "{}") is None
