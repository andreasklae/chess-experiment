"""Tests for the puzzle benchmark mechanics (no LLM): PuzzlePlayer scoring +
the Lichess move convention. The agent run is integration-tested separately.
"""
import asyncio
import sys
from pathlib import Path

import chess
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.puzzle_service import (  # noqa: E402
    PuzzleSpec, PuzzlePlayer, PuzzleComplete, PuzzleFailed, load_puzzle_set,
)

_PUZZLES = Path(__file__).resolve().parents[2] / "experiments/puzzle-benchmark/puzzles.json"


def _simulate(spec: PuzzleSpec, agent_moves: list[str]):
    """Drive the PuzzlePlayer the way the REAL bot loop does.

    Crucially: after the agent's move, if the board is game-over the real loop
    (_run_until_human_or_finished) returns WITHOUT calling the opponent's
    get_move, and instead calls PuzzlePlayer.finalize(board). We mirror that so
    this test catches the mate-ending false-negative the finalize path fixes."""
    pp = PuzzlePlayer(spec)
    board = chess.Board(spec.start_fen)
    loop = asyncio.new_event_loop()
    try:
        ai = 0
        while True:
            board.push(chess.Move.from_uci(agent_moves[ai])); ai += 1
            if board.is_game_over():
                # Real loop skips get_move and finalizes the puzzle here.
                solved = pp.finalize(board.copy(stack=False))
                return ("solved" if solved else "failed"), pp
            try:
                # Mirror the real bot loop: get_move receives a STACKLESS copy,
                # so the PuzzlePlayer must derive the agent's move by board diff.
                reply = loop.run_until_complete(pp.get_move(board.copy(stack=False)))
            except PuzzleComplete as e:
                return ("solved" if e.solved else "incomplete"), pp
            except PuzzleFailed:
                return "failed", pp
            board.push(reply)
    finally:
        loop.close()


def test_convention_agent_is_side_to_move_after_setup():
    # ISRIb: black setup Rxc8, then White (agent) forks with Ne7+/Nxc8.
    spec = PuzzleSpec(
        id="ISRIb",
        fen="5rk1/p4ppp/2Nnp3/8/4p3/2P3P1/P4KP1/4R3 b - - 3 25",
        moves=["f8c8", "c6e7", "g8f8", "e7c8"], topic="fork")
    assert spec.agent_color == chess.WHITE
    assert [m.uci() for m in spec.solver_line[0::2]] == ["c6e7", "e7c8"]


def test_correct_solution_scores_solved():
    spec = PuzzleSpec(
        id="ISRIb",
        fen="5rk1/p4ppp/2Nnp3/8/4p3/2P3P1/P4KP1/4R3 b - - 3 25",
        moves=["f8c8", "c6e7", "g8f8", "e7c8"], topic="fork")
    outcome, pp = _simulate(spec, ["c6e7", "e7c8"])
    assert outcome == "solved"
    assert pp.solved_plies == 2
    assert all(a["correct"] for a in pp.attempts)


def test_wrong_first_move_scores_failed_at_ply0():
    spec = PuzzleSpec(
        id="ISRIb",
        fen="5rk1/p4ppp/2Nnp3/8/4p3/2P3P1/P4KP1/4R3 b - - 3 25",
        moves=["f8c8", "c6e7", "g8f8", "e7c8"], topic="fork")
    outcome, pp = _simulate(spec, ["c6d8", "e7c8"])  # c6d8 is wrong
    assert outcome == "failed"
    assert pp.solved_plies == 0
    assert pp.attempts[0]["correct"] is False


def test_wrong_second_move_records_partial_progress():
    spec = PuzzleSpec(
        id="ISRIb",
        fen="5rk1/p4ppp/2Nnp3/8/4p3/2P3P1/P4KP1/4R3 b - - 3 25",
        moves=["f8c8", "c6e7", "g8f8", "e7c8"], topic="fork")
    # correct first (Ne7+), then a wrong second move
    outcome, pp = _simulate(spec, ["c6e7", "e7d5"])
    assert outcome == "failed"
    assert pp.solved_plies == 1  # got the first move right


def test_mate_ending_solution_scores_solved():
    # 868Fk: Qxf8+ Qc8 Rxc8# — the agent's FINAL move is checkmate, so the real
    # bot loop ends the game without calling get_move to score it. finalize must
    # score it as solved (regression for the mate-ending false-negative).
    spec = PuzzleSpec(
        id="868Fk",
        fen="k4r2/pp1q2pp/5p2/2QPn3/8/8/P4PPP/2R3K1 b - - 0 25",
        moves=["e5d3", "c5f8", "d7c8", "c1c8"], topic="hanging-piece")
    outcome, pp = _simulate(spec, ["c5f8", "c1c8"])
    assert outcome == "solved", [a for a in pp.attempts]
    assert pp.solved_plies == 2
    assert all(a["correct"] for a in pp.attempts)


def test_alternative_final_mate_accepted():
    # K+Q position with two distinct mates after the setup (Qf8# and Qa8#). The
    # agent plays Qa8# while the puzzle expects Qf8#; Lichess's alt-mate rule
    # accepts any mate on the final move. (Position verified by brute force.)
    spec = PuzzleSpec(
        id="ALTM",
        fen="6k1/8/6K1/8/8/Q7/8/8 b - - 0 1",
        moves=["g8h8", "a3f8"], topic="exposed-king")  # expected final = Qf8#
    b = chess.Board(spec.start_fen)
    assert b.san(chess.Move.from_uci("a3f8")).endswith("#")
    alt = chess.Move.from_uci("a3a8")                   # Qa8# — different mate
    assert alt in b.legal_moves and _mates(b, alt)
    outcome, pp = _simulate(spec, ["a3a8"])
    assert outcome == "solved"
    assert pp.attempts[-1]["accepted_as"] == "alt-mate"


def _mates(board: chess.Board, mv: chess.Move) -> bool:
    b = board.copy(); b.push(mv); return b.is_checkmate()


@pytest.mark.skipif(not _PUZZLES.exists(), reason="puzzle set not generated")
def test_puzzle_set_all_legal_and_oriented():
    specs = load_puzzle_set(_PUZZLES)
    assert len(specs) >= 100
    for s in specs:
        b = chess.Board(s.fen)
        for uci in s.moves:           # full line must be legal
            mv = chess.Move.from_uci(uci)
            assert mv in b.legal_moves, f"{s.id} illegal {uci}"
            b.push(mv)
        assert s.total_solver_plies >= 1
