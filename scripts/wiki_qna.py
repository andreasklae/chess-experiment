#!/usr/bin/env python3
"""Wiki navigation Q&A harness — test whether the agent finds and reads the
right wiki page for a chess question, with NO navigation hints in the prompt.

This is a standalone probe (no game, no board, no move loop). It builds the
SAME agent the chess experiment uses (same skill, same disabled tools, same
system prompt) and asks it a plain chess question. It records every tool call
— crucially the ``read_reference`` / ``chess__search_wiki`` paths — and the
final free-text answer, then scores navigation against an expected page.

The point is to measure the wiki's *navigability*: given only what the SKILL.md
and system prompt tell it about how to use the wiki, does the agent route to
the correct page, reason from it, and answer correctly? We deliberately do NOT
say "read endgames/..." in the question — that would test reading, not finding.

Usage:
    cd experiments/chess
    .venv/bin/python scripts/wiki_qna.py                  # run the built-in set
    .venv/bin/python scripts/wiki_qna.py --only two-rook   # one case by id
    .venv/bin/python scripts/wiki_qna.py --json out.json   # machine-readable log

Requires the eX3 vLLM env vars (SKILL_AGENT_EX3_BASE_URL etc.) the same way a
real game does. One question at a time — the eX3 server serves one request set
at a time (see [[chess-one-game-at-a-time]]).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Make `app` importable (mirrors how the backend runs).
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.agent_player import _build_agent  # noqa: E402


@dataclass
class QnaCase:
    """One navigation question and what a correct response looks like."""
    id: str
    question: str
    # Page path(s) (relative to references/) any of which counts as correct
    # navigation. A list because some topics are legitimately covered on more
    # than one page (e.g. the stalemate trap lives both in principles/avoid-
    # stalemate and inside the K+Q drill's "Watch out for").
    expect_pages: list[str]
    # Lower-cased substrings the final answer should contain to count as
    # chess-correct (any one match per group; all groups must hit).
    answer_must_mention: list[list[str]] = field(default_factory=list)


# Questions carry NO navigation hints — only a chess situation and a question.
# expect_page uses the POST-restructure paths; update if the layout changes.
CASES: list[QnaCase] = [
    QnaCase(
        id="two-rook",
        question=(
            "I have a king and two rooks against my opponent's lone king. "
            "What is the standard technique to checkmate, and what is the "
            "single most common way players throw the win away?"
        ),
        expect_pages=["mates/two-rook-ladder-mate.md"],
        answer_must_mention=[
            ["fence", "cut off", "cut-off", "wall"],
            ["other rook", "check with the other", "alternate", "leapfrog"],
            ["edge", "rank", "back rank"],
        ],
    ),
    QnaCase(
        id="king-rook",
        question=(
            "I have only a king and one rook left against a lone enemy king. "
            "How do I force checkmate? Where does the mate happen?"
        ),
        expect_pages=["mates/king-rook-mate.md"],
        answer_must_mention=[
            ["opposition"],
            ["edge"],
        ],
    ),
    QnaCase(
        id="back-rank",
        question=(
            "My opponent's king is castled kingside behind three unmoved "
            "pawns on the back rank, and I have a rook that can reach the "
            "back rank. What mate should I look for, and what defends against it?"
        ),
        expect_pages=["mates/back-rank-mate.md"],
        answer_must_mention=[
            ["back rank", "back-rank"],
            ["luft", "escape square", "push a pawn", "pawn move"],
        ],
    ),
    QnaCase(
        id="stalemate",
        question=(
            "I am completely winning with a queen against a lone king but I am "
            "worried about accidentally drawing. What is the specific danger "
            "and how do I avoid it?"
        ),
        expect_pages=["principles/avoid-stalemate.md", "mates/king-queen-mate.md"],
        answer_must_mention=[
            ["stalemate"],
            ["check", "leave the king a square", "escape square", "legal move"],
        ],
    ),
]


# Tool names that read or search the wiki — what we track for navigation.
_WIKI_READ = "read_reference"
_WIKI_SEARCH = "chess__search_wiki"


def _norm_path(args: dict) -> str | None:
    """Extract a normalised references-relative path from a read_reference call."""
    p = args.get("path")
    if not isinstance(p, str):
        return None
    p = p.strip().lstrip("/")
    if p.startswith("references/"):
        p = p[len("references/"):]
    return p or None


@dataclass
class CaseResult:
    id: str
    pages_read: list[str]
    searched: list[list[str]]
    tool_sequence: list[str]
    answer: str
    nav_hit: bool
    answer_hit: bool


async def run_case(case: QnaCase) -> CaseResult:
    # Fresh agent per case — no cross-question memory. game_id is a dummy; the
    # Q&A never calls the board scripts, but _build_agent injects it into env.
    agent = _build_agent(game_id=f"qna-{case.id}")

    prompt = (
        "You are a chess tutor answering a student's question. Use your chess "
        "skill and its knowledge wiki to give an accurate, specific answer. "
        "First load the skill if you have not, then find and read the most "
        "relevant wiki page, then answer in plain prose.\n\n"
        f"QUESTION: {case.question}"
    )

    pages_read: list[str] = []
    searched: list[list[str]] = []
    tool_sequence: list[str] = []
    answer_buf: list[str] = []

    # Import event types lazily (same module the player streams from).
    from skill_agent import TextDeltaEvent, ToolCallEvent, ToolResultEvent  # type: ignore

    async for event in agent.run_stream(prompt):
        if isinstance(event, TextDeltaEvent):
            answer_buf.append(event.content)
        elif isinstance(event, ToolCallEvent):
            name = event.name
            args = getattr(event, "args", {}) or {}
            tool_sequence.append(name)
            if name == _WIKI_READ:
                p = _norm_path(args if isinstance(args, dict) else {})
                if p:
                    pages_read.append(p)
            elif name == _WIKI_SEARCH:
                a = args.get("args") if isinstance(args, dict) else None
                searched.append(a if isinstance(a, list) else [str(a)])

    answer = "".join(answer_buf).strip()
    nav_hit = any(p in pages_read for p in case.expect_pages)
    answer_hit = _answer_matches(answer, case.answer_must_mention)

    return CaseResult(
        id=case.id,
        pages_read=pages_read,
        searched=searched,
        tool_sequence=tool_sequence,
        answer=answer,
        nav_hit=nav_hit,
        answer_hit=answer_hit,
    )


def _answer_matches(answer: str, groups: list[list[str]]) -> bool:
    """All groups must hit; a group hits if any of its substrings is present."""
    low = answer.lower()
    return all(any(sub in low for sub in group) for group in groups)


def _print_result(r: CaseResult) -> None:
    nav = "✓" if r.nav_hit else "✗"
    ans = "✓" if r.answer_hit else "✗"
    print(f"\n{'='*70}\nCASE {r.id}   nav {nav}   answer {ans}")
    print(f"  tool sequence : {' → '.join(r.tool_sequence) or '(none)'}")
    print(f"  pages read    : {r.pages_read or '(none)'}")
    if r.searched:
        print(f"  searched      : {r.searched}")
    print(f"  answer        : {r.answer[:600]}{'…' if len(r.answer) > 600 else ''}")


async def main_async(args: argparse.Namespace) -> int:
    cases = CASES
    if args.only:
        cases = [c for c in CASES if args.only in c.id]
        if not cases:
            print(f"No case id matches '{args.only}'. Have: {[c.id for c in CASES]}")
            return 2

    results: list[CaseResult] = []
    for case in cases:
        print(f"\n>>> Asking [{case.id}]: {case.question}")
        try:
            r = await run_case(case)
        except Exception as exc:  # one bad case shouldn't kill the run
            print(f"  ERROR running case {case.id}: {exc!r}")
            continue
        _print_result(r)
        results.append(r)

    nav = sum(r.nav_hit for r in results)
    ans = sum(r.answer_hit for r in results)
    print(f"\n{'='*70}\nSUMMARY: navigation {nav}/{len(results)}  ·  answer {ans}/{len(results)}")

    if args.json:
        Path(args.json).write_text(
            json.dumps([r.__dict__ for r in results], indent=2), encoding="utf-8"
        )
        print(f"wrote {args.json}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", help="run only cases whose id contains this string")
    ap.add_argument("--json", help="write machine-readable results to this path")
    raise SystemExit(asyncio.run(main_async(ap.parse_args())))


if __name__ == "__main__":
    main()
