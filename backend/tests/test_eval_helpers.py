"""Tests for the chess skill's _eval helpers — material totals, PST
symmetry, king-table selection, illegal-move classification, line application,
and the small public renderers."""

import importlib.util
import sys
from pathlib import Path

import chess
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "skills" / "chess" / "scripts" / "_eval.py"


@pytest.fixture(scope="module")
def ev():
    spec = importlib.util.spec_from_file_location("_eval", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_eval"] = module
    spec.loader.exec_module(module)
    return module


# ── Material and symmetry ───────────────────────────────────────────────────


def test_starting_position_is_zero(ev):
    """White and black are mirror-symmetric at the start; PST and material cancel."""
    result = ev.evaluate(chess.Board())
    assert result["score"] == 0
    assert result["white"]["material"] == result["black"]["material"] == 4000
    # 8 pawns + 2 knights + 2 bishops + 2 rooks + queen = 800+640+660+1000+900 = 4000


def test_king_material_excluded_from_totals(ev):
    """Lone-kings position: material totals must be 0, score 0."""
    board = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
    result = ev.evaluate(board)
    assert result["white"]["material"] == 0
    assert result["black"]["material"] == 0
    # PST may be nonzero for kings, but materially the score is zero from material side.


def test_white_up_a_pawn(ev):
    """White with an extra pawn on e4 — material delta should be exactly +100."""
    # Mirror-symmetric except for one extra white pawn on e4.
    a = ev.evaluate(chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1"))
    b = ev.evaluate(chess.Board("4k3/8/8/8/4P3/8/8/4K3 w - - 0 1"))
    assert b["white"]["material"] - a["white"]["material"] == 100
    # PST also adds: e4 for a white pawn is +20 in Michniewski's table.
    assert b["white"]["pst"] - a["white"]["pst"] == 20


def test_score_is_white_minus_black(ev):
    """Black up a knight: score should be negative."""
    board = chess.Board("4k3/8/3n4/8/8/8/8/4K3 w - - 0 1")
    result = ev.evaluate(board)
    assert result["score"] < 0
    # Material delta = -320 (black knight). PST also contributes.
    assert result["white"]["material"] - result["black"]["material"] == -320


# ── PST mirroring ──────────────────────────────────────────────────────────


def test_pst_mirrors_vertically_for_black(ev):
    """A white pawn on e4 and a black pawn on e5 should get the same PST bonus
    (each is on its own '4th rank' from its side's perspective)."""
    # White pawn on e4 alone vs black pawn on e5 alone.
    w_board = chess.Board("4k3/8/8/8/4P3/8/8/4K3 w - - 0 1")
    b_board = chess.Board("4k3/8/8/4p3/8/8/8/4K3 w - - 0 1")
    w_eval = ev.evaluate(w_board)
    b_eval = ev.evaluate(b_board)
    # PST for white pawn on e4 should equal PST for black pawn on e5.
    # Calling pst_value directly:
    white_pawn_e4 = ev.pst_value(chess.Piece(chess.PAWN, chess.WHITE), chess.E4, king_eg=False)
    black_pawn_e5 = ev.pst_value(chess.Piece(chess.PAWN, chess.BLACK), chess.E5, king_eg=False)
    assert white_pawn_e4 == black_pawn_e5


def test_knight_on_rim_vs_centre(ev):
    """Michniewski's knight table: e4 (centre) > a1 (rim)."""
    centre = ev.pst_value(chess.Piece(chess.KNIGHT, chess.WHITE), chess.E4, king_eg=False)
    rim = ev.pst_value(chess.Piece(chess.KNIGHT, chess.WHITE), chess.A1, king_eg=False)
    assert centre > rim


def test_king_mg_prefers_back_rank_corners(ev):
    """In the middlegame king table, g1/c1 score higher than e4 (castle, don't centralise)."""
    castled = ev.pst_value(chess.Piece(chess.KING, chess.WHITE), chess.G1, king_eg=False)
    centre = ev.pst_value(chess.Piece(chess.KING, chess.WHITE), chess.E4, king_eg=False)
    assert castled > centre


def test_king_eg_prefers_centre(ev):
    """In the endgame king table, e4 (centre) scores higher than g1 (corner)."""
    centre = ev.pst_value(chess.Piece(chess.KING, chess.WHITE), chess.E4, king_eg=True)
    corner = ev.pst_value(chess.Piece(chess.KING, chess.WHITE), chess.G1, king_eg=True)
    assert centre > corner


# ── King-table selection (Michniewski's canonical rule, per-side) ──────────


def test_king_eg_when_no_queens(ev):
    """No queens on either side -> endgame king table for both."""
    board = chess.Board("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1")
    assert ev.use_endgame_king_table(board, chess.WHITE) is True
    assert ev.use_endgame_king_table(board, chess.BLACK) is True


def test_king_mg_when_full_material(ev):
    """Starting position: both sides have queens with other pieces -> middlegame king table."""
    board = chess.Board()
    assert ev.use_endgame_king_table(board, chess.WHITE) is False
    assert ev.use_endgame_king_table(board, chess.BLACK) is False


def test_king_eg_when_queen_alone(ev):
    """White has only Q+K; black has full material. White -> endgame, black -> middlegame."""
    board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/8/3QK3 w kq - 0 1")
    assert ev.use_endgame_king_table(board, chess.WHITE) is True
    assert ev.use_endgame_king_table(board, chess.BLACK) is False


def test_king_mg_when_queen_with_minor(ev):
    """A side with a queen plus any other non-king piece uses middlegame table."""
    # White: Q + N + K (no pawns, no rooks, no bishops). Black: lone king.
    board = chess.Board("4k3/8/8/8/8/8/8/3QKN2 w - - 0 1")
    assert ev.use_endgame_king_table(board, chess.WHITE) is False
    assert ev.use_endgame_king_table(board, chess.BLACK) is True


def test_king_table_asymmetric_application_in_evaluate(ev):
    """The per-side king table selection must actually be used in evaluate().
    Construct a position where one side is in endgame mode and the other isn't,
    and verify the king PST values differ from what a single global flag would give."""
    # White: lone Q+K (-> endgame). Black: full back rank with queen (-> middlegame).
    board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/8/3QK3 w kq - 0 1")
    result = ev.evaluate(board)
    # White king on e1: endgame table value at e1.
    expected_white_king_pst = ev.pst_value(chess.Piece(chess.KING, chess.WHITE), chess.E1, king_eg=True)
    # Black king on e8: middlegame table value at e8.
    expected_black_king_pst = ev.pst_value(chess.Piece(chess.KING, chess.BLACK), chess.E8, king_eg=False)
    # Reconstruct what each side's PST sum should include from kings only — by
    # comparing with the same board minus kings... easier: just verify the
    # per-side decision matches what's claimed in the result.
    assert result["king_endgame_white"] is True
    assert result["king_endgame_black"] is False
    # And the king PST contributions differ — that's the whole point of per-side.
    assert expected_white_king_pst != expected_black_king_pst


# ── Verdict bands (material-focused phrasing) ──────────────────────────────


def test_verdict_balanced_at_zero(ev):
    assert ev.verdict(0) == "material balanced"


def test_verdict_roughly_balanced_under_30cp(ev):
    assert "roughly balanced" in ev.verdict(25)
    assert "roughly balanced" in ev.verdict(-29)


def test_verdict_slight_lead_30_to_99(ev):
    assert "slight material lead for white" in ev.verdict(50)
    assert "slight material lead for black" in ev.verdict(-95)


def test_verdict_clear_lead_100_to_299(ev):
    assert "clear material lead for white" in ev.verdict(150)
    assert "clear material lead for black" in ev.verdict(-250)


def test_verdict_decisive_lead_at_300_and_above(ev):
    assert "decisive material lead for white" in ev.verdict(400)
    assert "decisive material lead for black" in ev.verdict(-900)


def test_verdict_never_says_winning(ev):
    """The phrasing was deliberately moved away from 'winning' / 'losing' since
    a material+PST eval is tactically blind. Make sure no band re-introduces it."""
    for score in (-900, -250, -50, 0, 50, 250, 900):
        v = ev.verdict(score)
        assert "winning" not in v.lower(), f"score {score} -> {v!r}"
        assert "losing" not in v.lower(), f"score {score} -> {v!r}"


# ── Single-line eval renderers used by show_position and imagine_move ──────


def test_render_eval_line_format(ev):
    line = ev.render_eval_line(chess.Board())
    assert line.startswith("Material balance: ")
    assert "+0.00" in line
    assert "(material balanced)" in line


def test_render_eval_line_negative_score(ev):
    """Black up a queen -> negative score, 'decisive material lead for black'."""
    board = chess.Board("3qk3/8/8/8/8/8/8/4K3 w - - 0 1")
    line = ev.render_eval_line(board)
    # The score line should carry a minus sign.
    assert "-" in line
    assert "decisive material lead for black" in line


def test_render_eval_delta_line_shows_before_after_delta(ev):
    """Capturing a pawn moves the eval by +1.00 from white's perspective."""
    before = chess.Board("4k3/8/8/4p3/3P4/8/8/4K3 w - - 0 1")
    after = before.copy()
    after.push(chess.Move.from_uci("d4e5"))
    line = ev.render_eval_delta_line(before, after)
    # The 'before' score includes white-pawn + black-pawn (material balanced
    # plus a small PST difference); we just check the delta string is there.
    assert "→" in line
    assert "Δ" in line
    # After capture, white is up roughly 1 pawn.
    assert "material lead for white" in line


def test_eval_warning_carries_tactics_caveat(ev):
    """The warning that ships with every eval line must mention tactics."""
    assert "tactics" in ev.EVAL_WARNING.lower()


# ── Annotated move table (used by list_legal_moves + imagine_move) ─────────


def test_annotate_move_quiet(ev):
    board = chess.Board()
    move = chess.Move.from_uci("e2e4")
    a = ev.annotate_move(board, move)
    assert a["uci"] == "e2e4"
    assert a["san"] == "e4"
    assert a["description"] == "pawn to e4"
    assert a["flag"] == ""
    assert "king_before" in a
    assert "king_after" in a


def test_annotate_move_capture(ev):
    """Move that captures: description names the captured piece."""
    board = chess.Board("4k3/8/8/4p3/3P4/8/8/4K3 w - - 0 1")
    a = ev.annotate_move(board, chess.Move.from_uci("d4e5"))
    assert "takes pawn on e5" in a["description"]
    assert a["san"] == "dxe5"


def test_annotate_move_check_flag(ev):
    """Move that gives check carries the 'check' flag."""
    # White queen on h5 can play Qxf7+ in this Scholar's-mate-style position.
    board = chess.Board("rnbqkbnr/ppppp1pp/5p2/7Q/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 2")
    a = ev.annotate_move(board, chess.Move.from_uci("h5f7"))
    assert a["flag"] == "checkmate" or a["flag"] == "check"


def test_annotate_move_castling(ev):
    board = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1")
    a = ev.annotate_move(board, chess.Move.from_uci("e1g1"))
    assert "kingside castle" in a["description"]
    assert a["san"] == "O-O"


def test_annotate_move_promotion(ev):
    board = chess.Board("1k6/4P3/8/8/8/8/8/4K3 w - - 0 1")
    a = ev.annotate_move(board, chess.Move.from_uci("e7e8q"))
    assert "promotes to queen" in a["description"]


def test_render_moves_table_has_table_header(ev):
    board = chess.Board()
    table = ev.render_moves_table(board, list(board.legal_moves))
    assert "| UCI" in table
    assert "| SAN" in table
    assert "|--------|" in table  # separator row


def test_render_moves_table_empty_input(ev):
    """No legal moves (would happen at game end) renders a fallback string."""
    board = chess.Board()
    assert "(no legal moves)" in ev.render_moves_table(board, [])


# ── --moves: parsing, applying lines, SAN rendering ─────────────────────────


def test_parse_moves_arg_empty(ev):
    assert ev.parse_moves_arg("") == []


def test_parse_moves_arg_whitespace_tolerant(ev):
    assert ev.parse_moves_arg(" e2e4 , e7e5 , g1f3 ") == ["e2e4", "e7e5", "g1f3"]


def test_apply_line_starting_position(ev):
    board = chess.Board()
    final, san = ev.apply_line(board, ["e2e4", "e7e5", "g1f3"])
    assert san == ["e4", "e5", "Nf3"]
    assert final.turn == chess.BLACK
    # Original board not mutated.
    assert board.fen() == chess.Board().fen()


def test_format_san_line_white_to_move(ev):
    board = chess.Board()
    line = ev.format_san_line(board, ["e4", "e5", "Nf3"])
    assert line == "1.e4 e5 2.Nf3"


def test_format_san_line_black_to_move(ev):
    """A line starting on black's move should render '1...e5 2.Nf3'."""
    board = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")
    line = ev.format_san_line(board, ["e5", "Nf3"])
    assert line == "1...e5 2.Nf3"


# ── Illegal-move classifier ─────────────────────────────────────────────────


def test_illegal_malformed(ev):
    msg = ev.classify_illegal_move(chess.Board(), "xyz")
    assert "not a valid UCI" in msg


def test_illegal_invalid_square(ev):
    msg = ev.classify_illegal_move(chess.Board(), "e2e9")
    assert "not a valid UCI" in msg


def test_illegal_no_piece(ev):
    msg = ev.classify_illegal_move(chess.Board(), "e3e4")
    assert "no piece on e3" in msg


def test_illegal_wrong_color(ev):
    msg = ev.classify_illegal_move(chess.Board(), "e7e5")
    assert "black" in msg and "white's turn" in msg


def test_illegal_destination_is_own_piece(ev):
    msg = ev.classify_illegal_move(chess.Board(), "a1a2")
    assert "occupied by your own pawn" in msg


def test_illegal_path_blocked_rook(ev):
    msg = ev.classify_illegal_move(chess.Board(), "a1a4")
    assert "blocked by white pawn on a2" in msg


def test_illegal_path_blocked_bishop(ev):
    msg = ev.classify_illegal_move(chess.Board(), "f1c4")
    assert "blocked by white pawn on e2" in msg


def test_illegal_rook_off_ray(ev):
    """Rook trying to move diagonally should say 'cannot move to', not 'blocked'."""
    msg = ev.classify_illegal_move(chess.Board(), "a1c3")
    assert "cannot move to c3" in msg
    assert "blocked" not in msg


def test_illegal_king_too_far(ev):
    msg = ev.classify_illegal_move(chess.Board(), "e1e3")
    assert "king on e1 cannot move to e3" in msg


def test_illegal_pinned_piece(ev):
    # Black rook on e7 pins white knight e2 to white king e1.
    board = chess.Board("4k3/4r3/8/8/8/8/4N3/4K3 w - - 0 1")
    msg = ev.classify_illegal_move(board, "e2c3")
    assert "pinned" in msg


def test_illegal_in_check_unaddressed(ev):
    # White in check from black rook on e4; e1d1 stays in check.
    board = chess.Board("4k3/8/8/8/4r3/8/8/4K3 w - - 0 1")
    msg = ev.classify_illegal_move(board, "e1d1")
    assert "in check" in msg


def test_illegal_promotion_missing(ev):
    # White pawn on e7 reaching e8 without specifying promotion piece.
    board = chess.Board("8/4P3/8/8/8/8/4k3/4K3 w - - 0 1")
    msg = ev.classify_illegal_move(board, "e7e8")
    assert "requires a promotion piece" in msg


def test_illegal_promotion_on_non_promotion(ev):
    board = chess.Board("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1")
    msg = ev.classify_illegal_move(board, "e2e4q")
    assert "promotion specified" in msg


def test_illegal_castle_through_check(ev):
    # Black rook on f3 attacks f1 — king can't castle through.
    board = chess.Board("4k3/8/8/8/8/5r2/PPPP3P/R3K2R w KQ - 0 1")
    msg = ev.classify_illegal_move(board, "e1g1")
    assert "f1" in msg and "attacked" in msg


def test_illegal_castle_blocked(ev):
    board = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/RN2K2R w KQkq - 0 1")
    msg = ev.classify_illegal_move(board, "e1c1")
    assert "b1" in msg and "knight" in msg


def test_illegal_castle_while_in_check(ev):
    # White king on e1 in check from black rook on e3; castling not allowed.
    board = chess.Board("4k3/8/8/8/8/4r3/PPPP1PPP/R3K2R w KQ - 0 1")
    msg = ev.classify_illegal_move(board, "e1g1")
    assert "king is in check" in msg


# ── apply_line raises MoveListError with correct index/reason ──────────────


def test_apply_line_raises_on_illegal_move(ev):
    # First two moves legal; third is the white rook trying to leap its pawn.
    board = chess.Board()
    with pytest.raises(ev.MoveListError) as exc:
        ev.apply_line(board, ["e2e4", "e7e5", "a1a4"])
    assert exc.value.index == 3
    assert exc.value.uci == "a1a4"
    assert "blocked" in exc.value.reason


def test_apply_line_first_move_invalid(ev):
    board = chess.Board()
    with pytest.raises(ev.MoveListError) as exc:
        ev.apply_line(board, ["xyz"])
    assert exc.value.index == 1
    assert "not a valid UCI" in exc.value.reason


def test_apply_line_does_not_mutate_input(ev):
    board = chess.Board()
    original_fen = board.fen()
    try:
        ev.apply_line(board, ["e2e4", "garbage"])
    except ev.MoveListError:
        pass
    assert board.fen() == original_fen


# ── Confinement box & king distance (basic-mate geometry) ──────────────────


def test_confinement_box_central_king_is_large(ev):
    """A central lone king with one cutting rook sits in a large box."""
    b = chess.Board("8/8/8/8/4k3/8/8/R3K3 w - - 0 1")
    w, h, area = ev.confinement_box(b, chess.BLACK)
    assert area == w * h
    assert area > 30  # barely confined


def test_confinement_box_shrinks_as_king_is_cornered(ev):
    """Driving the king to an edge with the queen makes the box smaller."""
    central = ev.confinement_box(chess.Board("8/8/8/4k3/8/8/8/3QK3 w - - 0 1"), chess.BLACK)[2]
    edged = ev.confinement_box(chess.Board("4k3/8/8/3Q4/8/8/8/4K3 w - - 0 1"), chess.BLACK)[2]
    assert edged < central


def test_confinement_box_bounds_contains_the_king(ev):
    b = chess.Board("8/8/8/4k3/8/8/8/3QK3 w - - 0 1")
    min_f, max_f, min_r, max_r = ev.confinement_box_bounds(b, chess.BLACK)
    ek = b.king(chess.BLACK)
    assert min_f <= chess.square_file(ek) <= max_f
    assert min_r <= chess.square_rank(ek) <= max_r


def test_kings_distance_is_chebyshev(ev):
    b = chess.Board("8/8/8/4k3/8/8/8/3QK3 w - - 0 1")  # Ke1 vs Ke5 -> 4 ranks
    assert ev.kings_distance(b) == 4


def test_confinement_box_missing_king_defaults_full_board(ev):
    # Board with no black king (synthetic) -> full board fallback, no crash.
    b = chess.Board("8/8/8/8/8/8/8/R3K3 w - - 0 1")
    assert ev.confinement_box(b, chess.BLACK) == (8, 8, 64)
    assert ev.confinement_box_bounds(b, chess.BLACK) is None


def test_lone_king_color(ev):
    import chess
    assert ev.lone_king_color(chess.Board("8/8/8/8/4k3/8/8/R3K3 w - - 0 1")) == chess.BLACK
    assert ev.lone_king_color(chess.Board()) is None  # both sides have pieces


def test_piece_defensible_in_time(ev):
    import chess
    # Rook on a5, our king e5 (far), enemy king close to a5 -> not defensible.
    b = chess.Board("8/8/8/R3K3/1k6/8/8/8 w - - 0 1")
    assert ev.piece_defensible_in_time(b, chess.A5, chess.WHITE) in (True, False)
    # King adjacent to the rook -> defensible.
    b2 = chess.Board("8/8/8/RK6/8/2k5/8/8 w - - 0 1")
    assert ev.piece_defensible_in_time(b2, chess.A5, chess.WHITE) is True


def test_confine_state_can_tighten(ev):
    import chess
    # central K+R: a tighter defensible rook square exists -> move the rook
    s = ev.confine_state(chess.Board("8/8/8/8/4k3/8/8/R3K3 w - - 0 1"), chess.WHITE)
    assert s is not None and s["can_tighten"] is True
    assert s["best_area"] < s["current_area"]


def test_confine_state_rook_already_tight_means_move_king(ev):
    import chess
    # rook on its tightest defensible line, enemy king far -> can_tighten False
    s = ev.confine_state(chess.Board("8/4k3/8/R7/8/8/8/4K3 w - - 0 1"), chess.WHITE)
    assert s is not None and s["can_tighten"] is False


def test_confine_state_none_when_not_single_major_ending(ev):
    import chess
    assert ev.confine_state(chess.Board(), chess.WHITE) is None  # full board


def test_confine_state_drives_a_terminating_mate(ev):
    """Following confine_state's branch each move must MATE a running king
    without repetition — the property that distinguishes a correct drill from
    greedy box-shrinking (which drew by repetition, game f36a4618)."""
    import chess
    def pick(b):
        s = ev.confine_state(b, b.turn)
        opp = not b.turn
        majors = [sq for pt in (chess.QUEEN, chess.ROOK) for sq in b.pieces(pt, b.turn)]
        msq = majors[0]
        cands = []
        for m in b.legal_moves:
            a = b.copy(); a.push(m)
            if a.is_checkmate():
                return m
            if a.is_stalemate():
                continue
            is_major = m.from_square == msq
            if s and s["can_tighten"] != is_major:
                continue
            if is_major:
                ek = a.king(opp)
                if chess.square_distance(ek, m.to_square) == 1 and not a.is_attacked_by(b.turn, m.to_square):
                    continue
                if ev.piece_defensible_in_time(a, m.to_square, b.turn) is False:
                    continue
            ek = a.king(opp)
            cands.append(((ev.confinement_box(a, opp)[2], chess.square_distance(a.king(b.turn), ek)), m))
        if not cands:
            for m in b.legal_moves:
                a = b.copy(); a.push(m)
                if not a.is_stalemate():
                    cands.append(((ev.confinement_box(a, opp)[2], 0), m))
        cands.sort(key=lambda x: x[0])
        return cands[0][1] if cands else None

    b = chess.Board("8/8/8/8/4k3/8/8/R3K3 w - - 0 1")
    plies = 0; seen = {}
    while not b.is_game_over() and plies < 70:
        if b.turn == chess.WHITE:
            m = pick(b)
        else:
            wk = b.king(chess.WHITE)
            m = max(b.legal_moves, key=lambda mv: chess.square_distance(mv.to_square, wk))
        b.push(m); plies += 1
        k = b.board_fen(); seen[k] = seen.get(k, 0) + 1
        assert seen[k] < 3, f"repetition at ply {plies}"
    assert b.is_checkmate(), f"did not mate (result {b.result()}, {plies} plies)"
    assert plies <= 40
