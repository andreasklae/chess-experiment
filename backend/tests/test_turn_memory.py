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
    ToolReturnPart,
    UserPromptPart,
)

from app.agent_player import (
    TurnMemory,
    _committed_move_from_result,
    _make_pruning_processor,
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


class TestPruningProcessor:
    """Blocklist memory: history persists; only stale bulk is pruned."""

    def _history(self):
        return [
            ModelRequest(parts=[SystemPromptPart(content="SYS"), UserPromptPart(content="turn 1")]),
            ModelResponse(parts=[TextPart(content="thinking " * 100)]),
            ModelRequest(parts=[
                ToolReturnPart(tool_name="chess__show_position", content="X" * 2000, tool_call_id="1"),
                ToolReturnPart(tool_name="read_reference", content="WIKI " * 200, tool_call_id="2"),
            ]),
            ModelRequest(parts=[UserPromptPart(content="turn 2 prompt")]),
            ModelRequest(parts=[
                ToolReturnPart(tool_name="chess__show_position", content="FRESH" * 200, tool_call_id="3"),
            ]),
        ]

    def test_prunes_stale_perception_keeps_wiki_and_system(self):
        proc = _make_pruning_processor(TurnMemory())
        out = proc(self._history())
        assert any(isinstance(pt, SystemPromptPart) for pt in out[0].parts)
        stale = [pt for pt in out[2].parts if pt.tool_name == "chess__show_position"][0]
        assert "pruned" in stale.content
        wiki = [pt for pt in out[2].parts if pt.tool_name == "read_reference"][0]
        assert "WIKI" in wiki.content  # theory read stays available
        assert "thinking" in out[1].parts[0].content and "[truncated]" in out[1].parts[0].content

    def test_current_turn_untouched(self):
        proc = _make_pruning_processor(TurnMemory())
        out = proc(self._history())
        fresh = out[4].parts[0]
        assert fresh.content.startswith("FRESH")


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
