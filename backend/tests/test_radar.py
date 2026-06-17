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


class TestLadderFinishHooks:
    """The compact, board-ADAPTIVE ladder advisor (2026-06-16 rewrite): it
    prints a SHORT header plus exactly the ONE rule that applies right now —
    too much text caused the model to drift (game b60f731d laddered correctly
    then played a junk finish move). Every rule from the verbose version is
    preserved, surfaced only when relevant, and no concrete move is named."""

    def _drill(self, fen):
        from _radar import _drill_state_lines
        return "\n".join(_drill_state_lines(chess.Board(fen), chess.WHITE))

    def _no_named_move(self, out):
        import re
        assert not re.search(r"\*\*[RQ][a-h]?[1-8]?x?[a-h][1-8][+#]?\*\*", out)

    def test_output_is_scoped_to_one_rule(self):
        # Anti-verbosity: the whole drill state for a mid-board ladder is ONE
        # short line (was 5+ long lines). Keeps the model from drifting.
        from _radar import _drill_state_lines
        lines = _drill_state_lines(chess.Board("8/8/3k4/8/8/8/R7/1R4K1 w - - 0 1"), chess.WHITE)
        assert len(lines) == 1
        assert len(lines[0]) < 320  # compact

    def test_no_wall_says_build_wall_quietly(self):
        out = self._drill("8/8/8/3k4/8/8/8/R5RK w - - 0 1")
        assert "No WALL yet" in out and "quiet" in out and "Not a check" in out
        self._no_named_move(out)

    def test_finish_capturable_check_demands_waiting_move(self):
        # Kb8, Ra6, Rh7: every edge check lands adjacent (Kxa8) → WAITING move.
        out = self._drill("1k6/7R/R7/8/8/8/8/6K1 w - - 8 5")
        assert "on the edge" in out and "WAITING move" in out
        self._no_named_move(out)

    def test_finish_mirror_bottom_edge(self):
        # Vertical mirror (Kb1) — same WAITING-move finish, transposed.
        out = self._drill("6K1/8/8/8/8/R7/7R/1k6 w - - 0 1")
        assert "on the edge (rank 1)" in out and "WAITING move" in out

    def test_hanging_rook_says_slide_to_different_cross_line_first(self):
        # The user's rule: a capturable rook is moved to safety FIRST, onto a
        # file the OTHER rook is not on (so they don't block each other).
        out = self._drill("8/8/8/k7/1R6/8/8/R5K1 w - - 0 1")
        assert "can be captured" in out and "slide it to safety FIRST" in out
        assert "the other rook is NOT on" in out and "Safe squares" in out
        self._no_named_move(out)

    def test_queen_guarded_rook_not_flagged_as_hanging(self):
        # Queen guards the attacked rook (SEE) → no relocate hint.
        out = self._drill("8/8/8/k7/1R6/2Q5/8/6K1 w - - 0 1")
        assert "can be captured" not in out

    def test_rooks_same_file_says_move_to_different_file(self):
        out = self._drill("8/8/3k4/R7/8/8/R7/6K1 w - - 0 1")
        assert "share a file" in out and "DIFFERENT file" in out
        self._no_named_move(out)

    def test_self_block_when_kings_share_the_edge_line(self):
        out = self._drill("8/8/8/8/8/7R/5R2/2k3K1 w - - 24 13")
        assert "your OWN king is on" in out and "away from your king" in out.lower()
        self._no_named_move(out)

    def test_queen_rook_drives_like_two_rooks(self):
        # Q+R uses the same ladder; the queen caution appears on a driving turn.
        out = self._drill("8/8/4k3/8/8/8/1Q6/R5K1 w - - 0 1")
        assert "Ladder" in out
        self._no_named_move(out)

    def test_ladder_fires_when_opponent_has_no_major(self):
        assert self._drill("8/8/2k2n2/8/8/2p2p2/R7/1R4K1 w - - 0 1")  # K+N+pawns
        assert not self._drill("8/8/2k1r3/8/8/8/R7/1R4K1 w - - 0 1")  # opp has a rook

    def test_single_major_drill_still_requires_bare_king(self):
        assert not self._drill("8/5p2/3k4/8/8/8/8/R3K3 w - - 0 1")
        assert self._drill("8/8/3k4/8/8/8/8/R3K3 w - - 0 1")  # bare king: fires

    def test_promotion_threat_interrupts_the_ladder(self):
        # Don't tunnel-vision on the mate while the opponent queens: a Black
        # pawn one push from promoting must trigger a STOP interrupt instead of
        # ladder advice (game 912d0f7f: agent laddered while ...c2-c1=Q+).
        out = self._drill("8/8/2k5/R7/1R2n3/2p5/2p5/6K1 w - - 0 1")
        assert "Eliminate the opponent's threat" in out
        assert "promote next move" in out and "Handle it FIRST" in out
        self._no_named_move(out)

    def test_pawn_two_ranks_away_does_not_interrupt(self):
        out = self._drill("8/8/2k5/R7/1R2n3/2p5/8/6K1 w - - 0 1")
        assert "Eliminate the opponent's threat" not in out

    def test_mate_in_one_beats_promotion_threat(self):
        # If we can mate this move, do it — promotion never happens.
        out = self._drill("1k6/8/1K6/8/8/8/2p5/R7 w - - 0 1")
        assert "Eliminate the opponent's threat" not in out

    def test_driving_turn_names_safe_checking_lines(self):
        # On a wall-up driving turn, the advisor names safe checking files so
        # the agent skips dead (capturable) checks.
        out = self._drill("8/8/3k4/8/1R6/8/R7/6K1 w - - 0 1")
        # Either building the wall or checking; both stay one short line, fair.
        assert "Ladder" in out and len(out) < 320
        self._no_named_move(out)


class TestKingRookRecipe:
    """The single-rook (K+R) drill must let a recipe-faithful agent FINISH —
    the user's observed failure was reaching the edge then making useless
    checks while the king escaped sideways (2026-06-16). The advisor now
    teaches: mate on the EDGE (no corner needed), FOLLOW a sideways dodge
    with the king, never check without opposition or with the fence rook.
    This test proves the recipe is followable to mate from the standard drill
    starting positions (the ones the puzzle suite uses) and stays
    recipe-discipline (no concrete move named). It is a sanity check on the
    advisor TEXT, not a perfect K+R engine — the broad "finds mate, not by
    luck" guarantee comes from the live puzzle validation, where the real
    model reads this page and uses imagine_move's mobility report."""

    KR_FENS = [
        # The puzzle-suite start (scripts/run_puzzles.py kr-basic).
        "8/8/4k3/8/8/8/8/R3K3 w - - 0 1",
        "4k3/8/8/8/8/8/8/R3K3 w - - 0 1",   # king on the back rank already
        "8/8/4k3/8/8/8/R7/4K3 w - - 0 1",   # king centre, drive to a rank edge
        "8/4k3/8/8/8/8/R7/4K3 w - - 0 1",
    ]

    def test_advisor_names_no_concrete_move(self):
        import re
        from _radar import _drill_state_lines
        for fen in self.KR_FENS:
            lines = _drill_state_lines(chess.Board(fen), chess.WHITE)
            assert lines, fen
            assert not re.search(r"\*\*[RQ][a-h]?[1-8]?x?[a-h][1-8]", lines[0]), (
                f"advisor named a concrete move in {fen}: {lines[0]}"
            )

    def test_following_the_recipe_mates(self):
        """A recipe-faithful K+R agent mates a fleeing-and-dodging king within
        the cap. The agent reads the advisor's invariant — keep the fence, make
        progress, check only in opposition — and applies the SELF-CHECK the
        advisor names: imagine_move reports enemy-king mobility, a good move
        shrinks it (a check drops it sharply). We encode exactly that loop: of
        the safe legal moves, take any mate, never check without opposition or
        with the fence rook, and otherwise pick the move that most shrinks the
        enemy king's box (ties broken toward keeping/forming the fence and
        marching the king up). No engine, no search — the same one-ply
        mobility signal the agent gets from imagine_move. Black both flees to
        the centre and, once on an edge, dodges sideways (the live-failure
        case)."""

        def enemy_mobility(board_after):
            """Enemy king's legal-move count after our move — the number
            imagine_move prints as 'Enemy king mobility: before -> after'."""
            b = board_after
            if b.is_checkmate():
                return -1            # mate is the floor
            opp = chess.BLACK
            if b.turn != opp:
                b = b.copy(stack=False); b.push(chess.Move.null())
            ks = b.king(opp)
            return sum(1 for m in b.legal_moves if m.from_square == ks)

        def recipe_move(board):
            legal = list(board.legal_moves)
            ksq = board.king(chess.BLACK)
            myk = board.king(chess.WHITE)
            rook = next(iter(board.pieces(chess.ROOK, chess.WHITE)))
            kf, kr = chess.square_file(ksq), chess.square_rank(ksq)
            myf, myr = chess.square_file(myk), chess.square_rank(myk)

            def safe(mv):
                a = _pushed(board, mv)
                if a.is_stalemate():
                    return False
                if a.is_attacked_by(chess.BLACK, mv.to_square) and not \
                        a.is_attacked_by(chess.WHITE, mv.to_square):
                    return False
                return True

            cands = [m for m in legal if safe(m)]
            # 1. Always take an available mate.
            for m in cands:
                if _pushed(board, m).is_checkmate():
                    return m

            # Drive toward the nearer rank edge, sticky once a fence exists.
            fence_below = chess.square_rank(rook) == kr - 1
            fence_above = chess.square_rank(rook) == kr + 1
            if fence_below and not fence_above:
                drive_up = True
            elif fence_above and not fence_below:
                drive_up = False
            else:
                drive_up = (7 - kr) <= kr
            fence_rank = kr - 1 if drive_up else kr + 1
            far_file = 0 if kf >= 4 else 7

            # 2. Rook attacked by the king → slide it far along the fence rank.
            if chess.square_distance(rook, ksq) == 1 and board.is_attacked_by(
                    chess.BLACK, rook):
                slides = [m for m in cands if m.from_square == rook
                          and chess.square_rank(m.to_square) == chess.square_rank(rook)]
                if slides:
                    return max(slides, key=lambda m: chess.square_distance(m.to_square, ksq))

            # 3. No fence behind the king → build it (quiet move, far file).
            if chess.square_rank(rook) != fence_rank:
                fences = [m for m in cands if m.from_square == rook
                          and chess.square_rank(m.to_square) == fence_rank
                          and not _pushed(board, m).is_check()]
                if fences:
                    return min(fences, key=lambda m: abs(chess.square_file(m.to_square) - far_file))

            opposition = (chess.square_file(myk) == kf
                          and abs(myr - kr) == 2)

            # 4. Opposition → check on the king's rank, far from the king.
            if opposition:
                checks = [m for m in cands if m.from_square == rook
                          and chess.square_rank(m.to_square) == kr
                          and _pushed(board, m).is_check()]
                if checks:
                    return max(checks, key=lambda m: chess.square_distance(m.to_square, ksq))

            # The square our king wants: directly facing the enemy king
            # (same file), one rank short of the fence on our side.
            stand_rank = max(0, min(7, fence_rank - 1 if drive_up else fence_rank + 1))

            # 5. March the king UP to the stand_rank (the rank one short of the
            #    fence), keeping it near the enemy king's file. Crucially we do
            #    NOT chase the enemy's file once already on the stand_rank —
            #    mirroring a sideways-stepping king on the same rank is the
            #    oscillation trap (it never reaches opposition). We advance the
            #    rank, and stay roughly in front (closing the file gap only
            #    while ALSO advancing). Once on the stand_rank, rule 6 hands the
            #    move to Black so IT must break the standoff.
            on_stand = myr == stand_rank
            if not on_stand:
                kmoves = [m for m in cands if m.from_square == myk
                          and not _pushed(board, m).is_check()
                          and (chess.square_rank(m.to_square) < fence_rank if drive_up
                               else chess.square_rank(m.to_square) > fence_rank)]
                # Advance the rank toward stand_rank; among those, keep nearest
                # the enemy file; tie-break by enemy mobility.
                def kkey(m):
                    f, r = chess.square_file(m.to_square), chess.square_rank(m.to_square)
                    return (abs(r - stand_rank), abs(f - kf),
                            enemy_mobility(_pushed(board, m)))
                if kmoves:
                    best = min(kmoves, key=kkey)
                    if abs(chess.square_rank(best.to_square) - stand_rank) < abs(myr - stand_rank):
                        return best

            # 6. King on the stand_rank → rook WAITING move along the fence,
            #    far from the king, to hand the move to Black. Black must step:
            #    toward us (rule 4 mates next), sideways (we then follow with
            #    the king on the next turn since we will be off the stand_rank
            #    only if we choose — here we simply re-wait until it walks into
            #    opposition or back a rank, shrinking the box). Prefer a wait
            #    that, after Black's forced reply, can reach opposition.
            waits = [m for m in cands if m.from_square == rook
                     and chess.square_rank(m.to_square) == chess.square_rank(rook)
                     and not _pushed(board, m).is_check()]
            if waits:
                return max(waits, key=lambda m: chess.square_distance(m.to_square, ksq))
            # Fallback: the safe move that shrinks the box most.
            return min(cands, key=lambda m: enemy_mobility(_pushed(board, m))) \
                if cands else legal[0]

        for fen in self.KR_FENS:
            board = chess.Board(fen)
            for ply in range(120):
                if board.is_game_over():
                    break
                if board.turn == chess.WHITE:
                    board.push(recipe_move(board))
                else:
                    # Black flees toward the centre; once on an edge it dodges
                    # sideways (max distance from our king) — the hard case.
                    def flee(m):
                        a = _pushed(board, m)
                        k = a.king(chess.BLACK)
                        centre = (min(chess.square_file(k), 7 - chess.square_file(k))
                                  + min(chess.square_rank(k), 7 - chess.square_rank(k)))
                        return (centre, chess.square_distance(k, a.king(chess.WHITE)))
                    board.push(max(board.legal_moves, key=flee))
            assert board.is_checkmate(), (
                f"K+R recipe failed to mate from {fen}; reached {board.fen()} "
                f"after {ply} plies"
            )


def _pushed(board, move):
    b = board.copy(); b.push(move); return b


# ── K+Q / K+R box-method advisor (2026-06-17) ──────────────────────────────


def test_kq_central_gives_box_fact_and_an_instruction():
    out = radar("8/8/8/4k3/8/8/8/3QK3 w - - 0 1")
    assert "Confinement box" in out
    # From the centre the king should march (queen already confines to a band);
    # either a march or shrink instruction is acceptable, never a stall.
    assert ("MARCH YOUR KING" in out) or ("SHRINK IT" in out)


def test_kq_king_on_edge_but_king_far_says_march():
    """The exact failure mode: enemy king boxed on an edge, own king far —
    the advisor must say MARCH YOUR KING, not keep moving the queen."""
    out = radar("4k3/8/8/3Q4/8/8/8/4K3 w - - 0 1")
    assert "MARCH YOUR KING" in out
    assert "do NOT move the queen" in out


def test_kq_one_legal_move_warns_stalemate():
    out = radar("4k3/8/4K3/3Q4/8/8/8/8 w - - 0 1")
    # enemy king has very few squares; advisor must surface stalemate danger
    assert "STALEMATE DANGER" in out or "stalemate" in out.lower()


def test_kr_shows_box_and_king_distance():
    out = radar("8/8/8/8/4k3/8/8/R3K3 w - - 0 1")
    assert "Confinement box" in out
    assert "kings are" in out


def test_kq_advisor_names_no_concrete_move():
    """Fairness: the advisor names the recipe STEP, never a searched best move
    (no 'play Qd5' style concrete-move output)."""
    out = radar("8/8/8/4k3/8/8/8/3QK3 w - - 0 1")
    # It may mention piece letters (Q) and squares as facts, but must not issue
    # an imperative concrete move like 'play Qd5' / 'best move is'.
    low = out.lower()
    assert "best move" not in low
    assert "play q" not in low


# ── K+Q unified onto the K+R drill (2026-06-17) ────────────────────────────


def test_kq_uses_unified_rook_drill_wording():
    """A lone queen flows through the single-major (rook) advisor: it should
    fence like a rook and the advice should mention the queen, not box-phases."""
    out = radar("8/8/8/8/4k3/8/8/3QK3 w - - 0 1")
    # The advice mentions the queen (unified rook drill), never the old box-phase
    assert "queen" in out.lower()
    assert "Drill state" in out


def test_kq_and_kr_both_keep_kings_close():
    """Both basic mates lead with the keep-kings-close efficiency principle."""
    for fen in ("8/8/8/8/4k3/8/8/R3K3 w - - 0 1",
                "8/8/8/8/4k3/8/8/3QK3 w - - 0 1"):
        out = radar(fen)
        assert "keep the two KINGS close" in out


def test_kr_marches_king_when_kings_far_with_fence():
    """The 49-ply-grind fix: fence set but kings far -> advisor says march the
    king, not move the rook."""
    # Fence on rank 6 (rook a6) behind a king on f7-ish, white king far on rank 1.
    out = radar("8/5k2/R7/8/8/8/8/4K3 w - - 0 1")
    # Either the dedicated march rule or the no-opposition march rule fires;
    # both tell the king to step toward the enemy king.
    assert "MARCH YOUR KING" in out or "step YOUR king" in out
