"""Tests for the chess skill's mate & draw radar (_radar.py).

The radar must stay a mechanics tool: material counting, geometry, and the
rules of chess. These tests pin down when each line fires and — just as
important — when the radar stays silent.
"""

import sys
from pathlib import Path

import chess

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "chess" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _radar import render_radar  # noqa: E402


def radar(fen, moves=(), move_cap=None):
    board = chess.Board(fen)
    for m in moves:
        board.push_san(m)
    return render_radar(board, move_cap=move_cap)


class TestMatingMaterial:
    def test_two_majors_points_to_ladder(self):
        out = radar("4k3/8/8/8/8/8/8/R2QK3 w - - 0 1")
        assert "bare king" in out
        assert "ladder-mate.md" in out

    def test_lone_queen_points_to_kq_page(self):
        out = radar("4k3/8/8/8/8/8/8/3QK3 w - - 0 1")
        assert "king-queen-mate.md" in out

    def test_lone_rook_points_to_kr_page(self):
        out = radar("4k3/8/8/8/8/8/8/R3K3 w - - 0 1")
        assert "king-rook-mate.md" in out

    def test_minors_plus_pawn_recommends_promotion(self):
        out = radar("4k3/8/8/8/8/8/4P3/1N2KB2 w - - 0 1")
        assert "promote" in out.lower()

    def test_insufficient_material_warns(self):
        out = radar("4k3/8/8/8/8/8/8/1N2K3 w - - 0 1")
        assert "cannot checkmate" in out

    def test_silent_when_opponent_has_pieces(self):
        out = radar(chess.STARTING_FEN) or ""
        assert "bare king" not in out
        assert "ladder" not in out

    def test_opponent_king_and_pawns_counts_as_matable(self):
        out = radar("4k3/4p3/8/8/8/8/8/3QK3 w - - 0 1")
        assert "king and 1 pawn(s)" in out


class TestKingGeometry:
    def test_cornered_king_reported(self):
        out = radar("k7/8/1K6/8/8/8/8/7R w - - 0 1")
        assert "corner" in out
        assert "legal king move" in out

    def test_open_midgame_king_not_reported(self):
        out = radar(chess.STARTING_FEN) or ""
        assert "legal king move" not in out


class TestBackRank:
    def test_undefended_back_rank_flagged(self):
        # Black king g8 behind f7/g7/h7, no major guards rank 8.
        out = radar("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")
        assert "back rank" in out
        assert "back-rank-mate.md" in out
        assert "no enemy major piece guards" in out

    def test_defended_back_rank_names_guard(self):
        out = radar("r5k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")
        assert "guarded by major piece(s) on a8" in out

    def test_king_with_luft_not_flagged(self):
        out = radar("6k1/5pp1/7p/8/8/8/8/R5K1 w - - 0 1") or ""
        assert "trapped on its back rank" not in out


class TestPassedPawns:
    def test_own_passer_reported_with_distance(self):
        out = radar("6k1/5ppp/P7/8/8/8/5PPP/6K1 w - - 0 1")
        assert "a6 (2 move(s) from promotion)" in out

    def test_enemy_passer_reported(self):
        out = radar("6k1/5pp1/8/8/8/p7/5PP1/6K1 w - - 0 1")
        assert "Opponent passed pawn(s): a3" in out

    def test_blocked_file_not_passed(self):
        out = radar("6k1/p4ppp/P7/8/8/8/5PPP/6K1 w - - 0 1") or ""
        assert "Your passed pawn" not in out


class TestDrawRules:
    def test_repetition_warning(self):
        moves = ["Nf3", "Nf6", "Ng1", "Ng8", "Nf3", "Nf6", "Ng1", "Ng8"]
        out = radar(chess.STARTING_FEN, moves=moves)
        assert "Repetition warning" in out

    def test_halfmove_clock_warning(self):
        fen = "4k3/8/8/8/8/8/8/R3K3 w - - 70 80"
        out = radar(fen)
        assert "50-move rule: 70/100" in out

    def test_move_cap_warning_near_cap(self):
        board = chess.Board()
        for m in ["Nf3", "Nf6", "Ng1", "Ng8"] * 31:  # 124 plies
            board.push_san(m)
        out = render_radar(board, move_cap=150)
        assert "Move cap" in out
        assert "13 of your moves remain" in out

    def test_move_cap_silent_far_from_cap(self):
        board = chess.Board()
        for m in ["Nf3", "Nf6", "Ng1", "Ng8"]:
            board.push_san(m)
        out = render_radar(board, move_cap=150) or ""
        assert "Move cap" not in out

    def test_quiet_position_renders_nothing(self):
        assert radar(chess.STARTING_FEN) is None
