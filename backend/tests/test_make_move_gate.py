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
        # Abandoning the rook leaves K vs K — insufficient material.
        w = _gate(mm, "k7/1R6/2K5/8/8/8/8/8 w - - 0 1", "c6d6")
        assert w is not None and "rook" in w and (
            "INSUFFICIENT MATERIAL" in w or "abandons" in w
        )

    def test_minor_for_pawn_into_undefended_flagged(self, mm):
        # Game 9b0d7590 move 16: Nxd6+?? Bxd6 gave a safe knight for one pawn.
        # Now caught by the moved-piece SEE check (defended-square losing
        # trade), not just the undefended free-capture case.
        w = _gate(
            mm,
            "r3kbnr/1q1b1pp1/p1pp4/3Pp2p/2N1P3/2P2P2/P1P3PP/R1BQ1R1K w kq - 1 16",
            "c4d6",
        )
        assert w is not None and "LOSE MATERIAL" in w

    def test_queen_adjacent_to_king_flagged(self, mm):
        # Game ba6cd737: 3.Qd4+?? Kxd4 — K+Q vs K thrown away on move 3.
        w = _gate(mm, "8/8/8/4k3/8/3Q4/8/4K3 w - - 0 1", "d3d4")
        assert w is not None and "LOSE MATERIAL" in w

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
    """The gate's second tuple element marks CATASTROPHIC losses (severe
    wording) vs ordinary free gifts. As of 2026-06-20 this is wording only —
    the commit boundary is advisory and EVERYTHING is overridable with
    confirm=true (decisions/2026-06-20-blunder-gate-advisory-only.md). These
    tests pin the severity flag the gate computes, not a refusal."""

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

    def test_no_commit_deadlock_when_every_move_is_flagged(self, mm):
        # Live game (agent vs chesscom-850, 2026-06-20): Ke5 in check from Rg5,
        # Rb5 hanging; ALL five legal king moves drop the rook into K+B-vs-K
        # (insufficient material). The old HARD gate refused every one, so the
        # agent could never commit and looped to exhaustion. The gate still
        # FLAGS them (severe), but the commit boundary is now advisory — so the
        # agent can confirm=true and the game reaches its true result (a draw).
        # This test pins the deadlock CONDITION (every legal move flagged); the
        # advisory override lives in make_move.main().
        board = chess.Board("8/8/3B4/1R2K1r1/8/8/2k5/8 w - - 8 86")
        legal = list(board.legal_moves)
        assert legal, "test setup: position has legal moves"
        assert all(mm._blunder_gate(board, mv) is not None for mv in legal), (
            "every legal move should be flagged — the deadlock condition"
        )


class TestSEELosingTrades:
    """The 2026-06-15 SEE extension: the gate refuses moves that lose material
    on a single square even when the square is DEFENDED by count — the pattern
    that decided both 1000-rated games."""

    def test_defended_square_losing_trade_blocked(self, mm):
        # Game f2d158d4 16.Ne5?? — e5 defended by the d4 pawn, but fxe5 dxe5
        # nets a knight for a pawn. Count says balanced; value says blunder.
        res = _gate_full(
            mm, "rn2k2r/pp6/4ppp1/1b1p4/3P4/P1q2N2/R1P2PPP/2BQ1RK1 w kq - 4 16",
            "f3e5",
        )
        assert res is not None and "LOSE MATERIAL" in res[0]

    def test_clean_pawn_win_not_blocked(self, mm):
        # Nxe5 wins a pawn cleanly — must not be flagged.
        assert _gate_full(
            mm, "rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
            "f3e5",
        ) is None

    def test_promotion_into_capture_blocked(self, mm):
        # g8=Q?? when a rook on h8 just takes it — promote-into-capture, the
        # "banks +800, ignores the recapture" blunder. Hard: no army gain.
        res = _gate_full(mm, "7r/6P1/8/8/8/8/8/4K1k1 w - - 0 1", "g7g8q")
        assert res is not None and "promot" in res[0].lower()

    def test_safe_promotion_allowed(self, mm):
        assert _gate_full(mm, "8/6P1/8/8/8/8/8/4K1k1 w - - 0 1", "g7g8q") is None

    def test_rescuable_hanging_piece_soft_warned(self, mm):
        # Game 9b0d7590: the c3 knight was already hanging (8...b4); Nd2
        # ignored it when a retreat (Nb1/Ne2/Na4) would have saved it. Soft
        # nudge, not a block.
        res = _gate_full(
            mm, "r1bqkbnr/2p2pp1/p2p4/n2Pp2p/1p2P3/1BN2N2/PPP2PPP/R1BQK2R w KQkq - 0 9",
            "f3d2",
        )
        assert res is not None and res[1] is False and "hanging" in res[0]

    def test_rescue_move_not_warned(self, mm):
        # Retreating the attacked knight to safety must NOT warn.
        assert _gate_full(
            mm, "r1bqkbnr/2p2pp1/p2p4/n2Pp2p/1p2P3/1BN2N2/PPP2PPP/R1BQK2R w KQkq - 0 9",
            "c3b1",
        ) is None

    def test_opening_moves_not_flagged(self, mm):
        # No false positives on normal development.
        for uci in ("e2e4", "g1f3", "d2d4", "b1c3"):
            assert _gate_full(mm, chess.STARTING_FEN, uci) is None, uci

    def test_sonnet_nxe5_blunder_blocked(self, mm):
        # Game 872bf552 (Sonnet+skill, 2026-06-15): a Ruy Lopez where 6.Nxe5??
        # nets a piece for pawns after the Nxe5/Nxc6/Bxc6 sequence. Confirms the
        # gate catches the SAME blunder class across models (Haiku, Gemma,
        # Sonnet all hung pieces this way). Position after
        # e4 e5 Nf3 Nc6 Bb5 Nf6 O-O Nxe4 Re1 d5:
        res = _gate_full(
            mm,
            "r1bqkb1r/ppp2ppp/2n5/1B1pp3/4n3/5N2/PPPP1PPP/RNBQR1K1 w kq - 0 6",
            "f3e5",
        )
        assert res is not None and "LOSE MATERIAL" in res[0]
