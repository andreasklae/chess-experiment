"""Tests for make_move.py's commit-time mechanical safety gate.

The gate exists because every lost mating exercise on 2026-06-12 ended the
same way: the agent committed a move the perception tools would have flagged,
without imagining it first. Cases below replay the real blunders.
"""

import importlib.util
import sys
from pathlib import Path

import chess
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "skills" / "chess" / "scripts" / "make_move.py"


@pytest.fixture(scope="module")
def mm():
    spec = importlib.util.spec_from_file_location("make_move", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["make_move"] = module
    spec.loader.exec_module(module)
    return module


def _gate(mm, fen: str, uci: str) -> str | None:
    """Warning text only (or None) — keeps the existing string-based tests."""
    res = _gate_full(mm, fen, uci)
    return res[0] if res is not None else None


def _gate_full(mm, fen: str, uci: str):
    """Full (warning, hard) tuple, or None."""
    board = chess.Board(fen)
    move = chess.Move.from_uci(uci)
    assert move in board.legal_moves, f"test setup: {uci} illegal in {fen}"
    return mm._blunder_gate(board, move)


class TestFreeCaptures:
    def test_abandoning_rook_defender_flagged(self, mm):
        # Game 62427a9b: 27.Kd6?? left Rb7 to Kxb7 after 54 plies of drill.
        w = _gate(mm, "k7/1R6/2K5/8/8/8/8/8 w - - 0 1", "c6d6")
        assert w is not None and "FOR FREE" in w and "rook" in w

    def test_queen_adjacent_to_king_flagged(self, mm):
        # Game ba6cd737: 3.Qd4+?? Kxd4 — K+Q vs K thrown away on move 3.
        w = _gate(mm, "8/8/8/4k3/8/3Q4/8/4K3 w - - 0 1", "d3d4")
        assert w is not None and "FOR FREE" in w and "queen" in w

    def test_defended_adjacent_queen_passes(self, mm):
        # Contact checks protected by the king are the K+Q mating method.
        assert _gate(mm, "3Q4/8/6k1/8/5K2/8/8/8 w - - 0 1", "d8g5") is None

    def test_pawn_trade_passes(self, mm):
        # Recapture exists / pawn-level losses are not gated.
        assert _gate(mm, "8/8/3p4/4p3/3P4/8/8/4K2k w - - 0 1", "d4e5") is None

    def test_hanging_last_pawn_flagged(self, mm):
        # Game 9d2e1e58: Kc7?? abandoned the e7 pawn to Kxe7 — a 100cp loss
        # by value, but it leaves insufficient material: dead draw.
        w = _gate(mm, "4k3/4P3/3K4/8/8/8/8/8 w - - 0 1", "d6c7")
        assert w is not None and "INSUFFICIENT MATERIAL" in w


class TestGameEndingTraps:
    def test_checkmate_passes(self, mm):
        assert _gate(mm, "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1", "a1a8") is None

    def test_stalemate_flagged(self, mm):
        w = _gate(mm, "k7/8/K7/8/8/8/8/1R6 w - - 0 1", "b1b2")
        assert w is not None and "STALEMATE" in w

    def test_inadvertent_stalemate_by_king_step_flagged(self, mm):
        # Kc7 here boxes the bare king with no legal reply — stalemate.
        w = _gate(mm, "k7/1R6/2K5/8/8/8/8/8 w - - 0 1", "c6c7")
        assert w is not None and "STALEMATE" in w

    def test_repetition_draw_while_ahead_flagged(self, mm):
        # Shuffle Ra1-a2-a1... third occurrence with rook up must be gated.
        board = chess.Board("k7/8/2K5/8/8/8/8/R7 w - - 0 1")
        for uci in ("a1a2", "a8b8", "a2a1", "b8a8", "a1a2", "a8b8",
                    "a2a1", "b8a8", "a1a2", "a8b8"):
            board.push(chess.Move.from_uci(uci))
        # The next a2a1 creates the position's third occurrence — instant draw.
        move = chess.Move.from_uci("a2a1")
        assert board.is_legal(move)
        res = mm._blunder_gate(board, move)
        assert res is not None and "repetition" in res[0].lower()


class TestHardVsSoft:
    """Catastrophic losses are HARD (confirm cannot override); ordinary free
    gifts are soft. Game ab02f31d: agent reflexively confirm=true'd Rb6+??
    Kxb6 hanging a rook to the bare king on move 2 of a ladder."""

    def test_hang_rook_to_bare_king_is_hard(self, mm):
        # Bare black king on c6; Rb6+?? Kxb6 hangs the rook with no army to
        # justify any sacrifice.
        res = _gate_full(mm, "8/8/2k5/R7/8/8/8/1R4K1 w - - 2 2", "b1b6")
        assert res is not None and res[1] is True

    def test_draw_while_ahead_is_hard(self, mm):
        board = chess.Board("k7/8/2K5/8/8/8/8/R7 w - - 0 1")
        for uci in ("a1a2", "a8b8", "a2a1", "b8a8", "a1a2", "a8b8",
                    "a2a1", "b8a8", "a1a2", "a8b8"):
            board.push(chess.Move.from_uci(uci))
        res = mm._blunder_gate(board, chess.Move.from_uci("a2a1"))
        assert res is not None and res[1] is True

    def test_ordinary_free_gift_is_soft(self, mm):
        # Same rook-hang geometry as the hard case, but the opponent still has
        # a piece (a knight) — so a gift COULD be a real sacrifice; the gate
        # flags it but leaves it overridable with confirm.
        res = _gate_full(mm, "8/8/2k5/R7/8/8/8/1R5n w - - 2 2", "b1b6")
        assert res is not None and res[1] is False
