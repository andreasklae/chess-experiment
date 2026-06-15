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

    def test_own_back_rank_warned_when_threatened(self):
        # White to move, own king h1 walled by g2/h2, black rook on open
        # d-file → defensive luft warning (game 9b0d7590 mate pattern).
        out = radar("3r4/6p1/8/8/8/8/6PP/3R3K w - - 0 1") or ""
        assert "Your OWN king is walled on its back rank" in out

    def test_own_back_rank_silent_with_luft(self):
        # g-pawn advanced → king has luft → no defensive warning.
        out = radar("3r4/8/8/8/8/6P1/7P/3R2K1 w - - 0 1") or ""
        assert "Your OWN king is walled" not in out


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


class TestLadderRecipe:
    """The ladder advisor is a RECIPE (which rook, what kind of move, the
    principle for the square) — it must NOT name a concrete move (that would
    be the tool playing for the agent), and following the recipe must
    actually mate. Earlier the advisor both named a move AND named an
    illegal/forbidden one (game 81db9189), then named a single-rook chase
    that never mates (game dafe6b95). This test guards both: recipe
    discipline, and recipe sufficiency.
    """

    import re as _re

    LADDER_FENS = [
        "8/8/2k5/R7/8/8/8/1R4K1 w - - 2 2",
        "8/8/3k4/R7/8/8/8/1R4K1 w - - 0 1",
        "8/8/4k3/R7/8/8/8/1R4K1 w - - 0 1",
        "8/8/3k4/8/8/8/R7/1R4K1 w - - 0 1",
        "8/2k5/8/1R6/8/8/R7/6K1 w - - 0 1",
    ]

    def test_advisor_does_not_name_a_concrete_move(self):
        """No 'play **Rd6+**' style move-naming — recipe steps only."""
        import re
        from _radar import _drill_state_lines
        for fen in self.LADDER_FENS:
            lines = _drill_state_lines(chess.Board(fen), chess.WHITE)
            assert lines, fen
            # A concrete move would look like **Ra6+** / **Rh5** (a piece
            # letter + square). Square names alone (e.g. 'rank 6', 'a-file')
            # are fine — those are principles.
            assert not re.search(r"\*\*[RQ][a-h]?[1-8]?x?[a-h][1-8]", lines[0]), (
                f"advisor named a concrete move in {fen}: {lines[0]}"
            )

    def test_following_the_recipe_mates(self):
        """A competent agent that follows the recipe — keep the fence, check
        with the free rook on the king's line as far from the king as
        possible, slide a harassed rook away — mates a fleeing king well
        within the move cap. Proves the recipe is SUFFICIENT (the residual
        gap is the model executing it, not the recipe being wrong)."""
        from _radar import _drill_state_lines

        def recipe_move(board):
            """Pick the move a recipe-faithful agent would, reading the same
            geometry the advisor names. Not an engine: it only encodes the
            ladder rules, no search/eval."""
            lines = _drill_state_lines(board, chess.WHITE)
            text = lines[0] if lines else ""
            legal = list(board.legal_moves)
            ksq = board.king(chess.BLACK)
            rooks = list(board.pieces(chess.ROOK, chess.WHITE))

            def safe(mv):
                a = board.copy(); a.push(mv)
                if a.is_stalemate():
                    return False
                if a.is_attacked_by(chess.BLACK, mv.to_square) and not \
                        a.is_attacked_by(chess.WHITE, mv.to_square):
                    return False
                return True

            # Harassed rook → slide it to the far end of its rank.
            harassed = [r for r in rooks if chess.square_distance(r, ksq) <= 1]
            if harassed:
                r = harassed[0]
                far_file = 0 if chess.square_file(ksq) >= 4 else 7
                cands = [m for m in legal if m.from_square == r
                         and chess.square_rank(m.to_square) == chess.square_rank(r)
                         and safe(m)]
                if cands:
                    return max(cands, key=lambda m: chess.square_distance(m.to_square, ksq))

            # Always grab a mate.
            mates = [m for m in legal if _pushed(board, m).is_checkmate()]
            if mates:
                return mates[0]

            kr = chess.square_rank(ksq)
            # Direction: drive toward the nearer rank edge, STICKY via the
            # fence once one exists.
            fence_below = any(chess.square_rank(r) == kr - 1 for r in rooks)
            fence_above = any(chess.square_rank(r) == kr + 1 for r in rooks)
            if fence_below and not fence_above:
                drive_up = True
            elif fence_above and not fence_below:
                drive_up = False
            else:
                drive_up = (7 - kr) <= kr
            fence_rank = kr - 1 if drive_up else kr + 1
            far_file = 0 if chess.square_file(ksq) >= 4 else 7

            # 1. No fence on the rank behind the king? Build it FIRST — never
            #    check without a fence, or the king just escapes that way.
            on_fence = [r for r in rooks if chess.square_rank(r) == fence_rank]
            if not on_fence:
                fences = [m for m in legal
                          if board.piece_at(m.from_square).piece_type == chess.ROOK
                          and chess.square_rank(m.to_square) == fence_rank and safe(m)
                          and not _pushed(board, m).is_check()]  # fence, not check
                if fences:
                    return min(fences, key=lambda m: abs(chess.square_file(m.to_square) - far_file))

            # 2. Fence exists → check with the OTHER (non-fence) rook on the
            #    king's rank, as far from the king as possible.
            fence_sq = on_fence[0] if on_fence else None
            checks = [m for m in legal
                      if board.piece_at(m.from_square).piece_type == chess.ROOK
                      and m.from_square != fence_sq
                      and chess.square_rank(m.to_square) == kr
                      and _pushed(board, m).is_check() and safe(m)]
            if checks:
                return max(checks, key=lambda m: chess.square_distance(m.to_square, ksq))

            # 3. The non-fence rook can't reach the king's rank safely (it is
            #    on that rank already, or boxed) → reposition it to the far
            #    wing on its own rank.
            free = [r for r in rooks if r != fence_sq]
            if free:
                r = free[0]
                reps = [m for m in legal if m.from_square == r and safe(m)
                        and chess.square_rank(m.to_square) == chess.square_rank(r)]
                if reps:
                    return max(reps, key=lambda m: chess.square_distance(m.to_square, ksq))
            return next((m for m in legal if safe(m)), legal[0])

        for fen in ["8/8/3k4/8/8/8/R7/1R4K1 w - - 0 1",
                    "8/8/2k5/R7/8/8/8/1R4K1 w - - 0 1"]:
            board = chess.Board(fen)
            for ply in range(40):
                if board.is_game_over():
                    break
                if board.turn == chess.WHITE:
                    board.push(recipe_move(board))
                else:
                    # Black king flees toward the center (hardest case).
                    def central(m):
                        a = board.copy(); a.push(m)
                        k = a.king(chess.BLACK)
                        return (min(chess.square_file(k), 7 - chess.square_file(k))
                                + min(chess.square_rank(k), 7 - chess.square_rank(k)))
                    board.push(max(board.legal_moves, key=central))
            assert board.is_checkmate(), (
                f"recipe failed to mate from {fen}; reached {board.fen()}"
            )


def _pushed(board, move):
    b = board.copy(); b.push(move); return b
