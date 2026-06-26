"""Tests for the structural puzzle categorizer (mover piece, targets, branching,
move kind) — the features that make agent weaknesses sliceable in analysis.
Uses real puzzles from the set so the categorization is verified end-to-end."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.puzzle_categorize import categorize  # noqa: E402


def test_knight_fork_categorized():
    # fqeTF: after the setup (Bd4xe5), White's knight forks king + bishop.
    c = categorize("5k2/5p2/p3pN1p/K3P1p1/3b2P1/8/7P/8 b - - 1 42",
                   ["d4e5", "f6d7"])
    assert c["mover_piece"] == "knight"
    assert c["n_targets"] >= 2
    assert "king" in c["targets"]
    assert c["targets_king"] is True
    assert "double-attack" in c["signature"]


def test_quiet_pawn_move_categorized():
    # ooIJX: the solver's move is a quiet pawn push (no capture, no check).
    c = categorize("r4rk1/pppbqp2/2nb3p/4p3/2B3P1/P1PP3Q/1P1N1PP1/R3K2R b KQ - 1 18",
                   ["e7f6", "g4g5"])
    assert c["mover_piece"] == "pawn"
    assert c["first_move_is_quiet"] is True
    assert c["first_move_is_check"] is False
    assert c["first_move_is_capture"] is False
    assert c["signature"] == "quiet pawn move"


def test_branching_and_basic_fields_present():
    c = categorize("r4rk1/pppbqp2/2nb3p/4p3/2B3P1/P1PP3Q/1P1N1PP1/R3K2R b KQ - 1 18",
                   ["e7f6", "g4g5"])
    assert isinstance(c["legal_moves_count"], int) and c["legal_moves_count"] > 0
    assert c["solver_color"] == "white"          # White solves after the black setup
    assert "material_before" in c and "solution_plies" in c


def test_bad_input_returns_error_not_crash():
    c = categorize("not a fen", ["x"])
    assert "categorize_error" in c
