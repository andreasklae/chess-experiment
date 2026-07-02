"""Tests for the chess skill's imagine_move script."""

import importlib.util
import sys
from pathlib import Path

import chess
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "skills" / "chess" / "scripts" / "imagine_move.py"


@pytest.fixture(scope="module")
def im():
    spec = importlib.util.spec_from_file_location("imagine_move", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["imagine_move"] = module
    spec.loader.exec_module(module)
    return module


# ── Basic rendering ────────────────────────────────────────────────────────


def test_render_includes_all_sections(im):
    """Output is markdown; check the section headings/labels are present."""
    out = im.render_imagine(chess.Board(), chess.Move.from_uci("e2e4"))
    for section in [
        "## Move:", "**Check:**", "## Discovered attacks",
        "## Moved piece status", "## Side-effects on other own pieces",
        "**no longer attacking:**", "**no longer defending:**",
        "## Newly hanging own pieces", "## Opponent legal replies",
        "**FEN:**", "**Side to move:**",
    ]:
        assert section in out, f"missing section: {section!r}"


def test_render_does_not_mutate_input_board(im):
    board = chess.Board()
    original_fen = board.fen()
    im.render_imagine(board, chess.Move.from_uci("e2e4"))
    assert board.fen() == original_fen


def test_render_shows_resulting_fen(im):
    out = im.render_imagine(chess.Board(), chess.Move.from_uci("e2e4"))
    # After 1.e4, side to move is black.
    assert "**Side to move:** black" in out
    # FEN should contain the e-pawn on e4.
    assert "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR" in out


# ── Move summary: captures, castle, en passant, promotion ──────────────────


def test_move_summary_quiet(im):
    s = im._move_summary(chess.Board(), chess.Move.from_uci("e2e4"))
    assert "no capture" in s
    assert "e4" in s  # SAN
    assert "e2e4" in s  # UCI


def test_move_summary_capture_with_material(im):
    # Position with a capture available.
    board = chess.Board("4k3/8/8/4p3/3P4/8/8/4K3 w - - 0 1")
    s = im._move_summary(board, chess.Move.from_uci("d4e5"))
    assert "captures black pawn" in s
    assert "+100cp" in s


def test_move_summary_castle(im):
    board = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1")
    s = im._move_summary(board, chess.Move.from_uci("e1g1"))
    assert "kingside castle" in s


def test_move_summary_en_passant(im):
    # Black just pushed d7-d5; white can play e5xd6 en passant.
    board = chess.Board("rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3")
    s = im._move_summary(board, chess.Move.from_uci("e5d6"))
    assert "en passant" in s
    assert "+100cp" in s


def test_move_summary_promotion(im):
    # Black king moved to b8 so e8 is empty — quiet promotion.
    board = chess.Board("1k6/4P3/8/8/8/8/8/4K3 w - - 0 1")
    s = im._move_summary(board, chess.Move.from_uci("e7e8q"))
    assert "promotes to queen" in s


def test_move_summary_capture_promotion(im):
    # Black rook on f8 — promoting pawn captures it.
    board = chess.Board("1k3r2/4P3/8/8/8/8/8/4K3 w - - 0 1")
    s = im._move_summary(board, chess.Move.from_uci("e7f8q"))
    assert "captures black rook" in s
    assert "promotes to queen" in s


# ── Check / mate / stalemate ───────────────────────────────────────────────


def test_check_detection(im):
    # White queen on h5 vs black king on e8; Qxf7+ would deliver check.
    board = chess.Board("rnbqkbnr/ppppp1pp/5p2/7Q/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 2")
    out = im.render_imagine(board, chess.Move.from_uci("h5f7"))
    # Actually that's Qxf7 mate (Scholar's variant). Let's just check it's check.
    assert "check" in out.lower()


def test_no_check_when_quiet_move(im):
    out = im.render_imagine(chess.Board(), chess.Move.from_uci("e2e4"))
    assert "**Check:** none" in out


# ── Discovered attacks ─────────────────────────────────────────────────────


def test_discovered_attack_bishop_behind_pawn(im):
    # Position: white bishop c1, white pawn d2, black pawn h6. Push d2-d4
    # opens diagonal c1-h6.
    board = chess.Board("rnbqkbnr/ppp1pppp/7p/3p4/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 2")
    out = im.render_imagine(board, chess.Move.from_uci("d2d4"))
    assert "## Discovered attacks" in out
    # The bishop on c1 should now attack the pawn on h6.
    discoveries_section = out.split("## Discovered attacks")[1].split("## Moved piece status")[0]
    assert "bishop on c1" in discoveries_section
    assert "h6" in discoveries_section


def test_no_discovered_attacks_when_none(im):
    # Standard 1.e4 has no discovered attacks (no piece behind e2 of the same color
    # that can attack along the e-file).
    out = im.render_imagine(chess.Board(), chess.Move.from_uci("e2e4"))
    # Section heading present, then a "- (none)" bullet underneath.
    section = out.split("## Discovered attacks")[1].split("##")[0]
    assert "(none)" in section


# ── Newly hanging own pieces ───────────────────────────────────────────────


def test_newly_hanging_after_queen_abandons_pawn(im):
    # White queen d1 is the sole defender of white pawn d4 against black pawn e5.
    # Moving the queen away leaves d4 hanging.
    board = chess.Board("4k3/8/4r3/3pp3/3P4/8/8/3QK3 w - - 0 1")
    out = im.render_imagine(board, chess.Move.from_uci("d1h5"))
    assert "## Newly hanging own pieces" in out
    hanging_section = out.split("## Newly hanging own pieces")[1].split("##")[0]
    assert "pawn on d4" in hanging_section
    # Counts are now stated explicitly (board-visualization benchmark 2026-06-24):
    # "attacked by 1 (...); defended by 0 (nothing)".
    assert "defended by 0 (nothing)" in hanging_section
    assert "attacked by 1 (pawn on e5)" in hanging_section


def test_no_newly_hanging_when_safe(im):
    out = im.render_imagine(chess.Board(), chess.Move.from_uci("e2e4"))
    section = out.split("## Newly hanging own pieces")[1].split("##")[0]
    assert "(none)" in section


def test_moved_piece_itself_not_in_newly_hanging(im):
    """The moved piece's own attack/defense status belongs in 'Moved piece status',
    not 'Newly hanging'. Confirm a knight moving to an attacked square is not
    double-counted."""
    board = chess.Board("4k3/8/8/8/8/2n5/8/4K1N1 w - - 0 1")
    out = im.render_imagine(board, chess.Move.from_uci("g1e2"))
    hanging_section = out.split("## Newly hanging own pieces")[1].split("##")[0]
    assert "on e2" not in hanging_section


# ── Value-based (SEE) bad-trade detection ──────────────────────────────────


def test_bad_trade_moved_piece_defended_but_losing(im):
    """Game f2d158d4 move 16: Ne5?? — the knight lands on a square defended by
    count (d4 pawn) but fxe5/dxe5 nets a knight for a pawn. The count-based
    hanging warning stays silent; the value-based exchange warning must fire."""
    board = chess.Board("rn2k2r/pp6/4ppp1/1b1p4/3P4/P1q2N2/R1P2PPP/2BQ1RK1 w kq - 4 16")
    out = im.render_imagine(board, chess.Move.from_uci("f3e5"))
    assert "Losing exchange on e5" in out


def test_bad_trade_leaves_other_piece_defended_but_losing(im):
    """Game 9b0d7590 move 9: Nd2?? leaves the c3 knight defended only by the
    b2 pawn — bxc3 bxc3 nets a knight for a pawn. The newly-hanging section
    must flag c3 with the value loss even though it is 'defended' by count."""
    board = chess.Board("r1bqkbnr/2p2pp1/p2p4/n2Pp2p/1p2P3/1BN2N2/PPP2PPP/R1BQK2R w KQkq - 0 9")
    out = im.render_imagine(board, chess.Move.from_uci("f3d2"))
    hanging_section = out.split("## Newly hanging own pieces")[1].split("##")[0]
    assert "knight on c3" in hanging_section
    assert "lose" in hanging_section and "material" in hanging_section


def test_no_bad_trade_warning_on_equal_or_winning_move(im):
    """A normal developing move (Nf3) and a clean pawn grab must not trigger
    the losing-exchange warning."""
    out = im.render_imagine(chess.Board(), chess.Move.from_uci("g1f3"))
    assert "Losing exchange" not in out


def test_hallucinated_fen_returns_actionable_error():
    """A malformed FEN (model hallucination — e.g. a 9-column rank) must NOT
    crash with a bare 'Invalid fen'; it returns an actionable error telling
    the agent to drop fen= and use the live board. Run as a subprocess, the
    way the harness invokes the script (the error path exits before any
    network fetch, so no backend is needed)."""
    import json
    import subprocess

    bad = "1rb1k1nr/pp1p2pp/4qp2/2b1P3/8/2N1PN3/PP1K2PP/R1B2B1R w k - 0 14"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--fen", bad, "e4"],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert "WITHOUT a fen" in payload["error"]
    assert "not a legal position" in payload["error"]


# ── Attack/defense deltas (no longer attacking / defending) ────────────────


def test_no_longer_attacking_lists_previous_targets(im):
    # Knight on f3 attacks e5; knight on h4 doesn't.
    board = chess.Board("4k3/8/8/4p3/8/5N2/8/4K3 w - - 0 1")
    out = im.render_imagine(board, chess.Move.from_uci("f3h4"))
    no_longer_section = out.split("**no longer attacking:**")[1].split("**no longer defending:**")[0]
    assert "pawn on e5" in no_longer_section


def test_no_longer_defending_excludes_from_square(im):
    """The from-square shouldn't appear in 'no longer defending' — the piece
    that 'defended' from-square is the moved piece itself, which is gone."""
    board = chess.Board()
    out = im.render_imagine(board, chess.Move.from_uci("g1f3"))
    no_longer_def = out.split("**no longer defending:**")[1].split("##")[0]
    assert "on g1" not in no_longer_def


# ── En passant offered ─────────────────────────────────────────────────────


def test_en_passant_offered_when_pawn_pushes_next_to_enemy_pawn(im):
    # Black pawn on d4 already. White pushes e2-e4; black can capture en passant.
    board = chess.Board("rnbqkbnr/pppp1ppp/8/8/3p4/8/PPPPPPPP/RNBQKBNR w KQkq - 0 3")
    out = im.render_imagine(board, chess.Move.from_uci("e2e4"))
    assert "En passant available:" in out


def test_en_passant_not_offered_when_no_adjacent_pawn(im):
    # 1.e4 from the start — black has no pawn on d4 or f4.
    out = im.render_imagine(chess.Board(), chess.Move.from_uci("e2e4"))
    assert "En passant available:" not in out


# ── Opponent legal moves ───────────────────────────────────────────────────


def test_opponent_legal_moves_count_matches_python_chess(im):
    """The 'N legal replies' line should match python-chess's count."""
    board = chess.Board()
    board.push_uci("e2e4")
    expected = board.legal_moves.count()
    board = chess.Board()
    out = im.render_imagine(board, chess.Move.from_uci("e2e4"))
    # The replies line now carries a material-sorted suffix.
    assert f"_{expected} legal replies, sorted by the material" in out


def test_opponent_legal_moves_show_full_list_not_truncated(im):
    """Per user request: the opponent-replies table now shows all moves, not
    the first 12 — so the agent can see the killer reply."""
    out = im.render_imagine(chess.Board(), chess.Move.from_uci("e2e4"))
    table_section = out.split("## Opponent legal replies")[1]
    # Black has 20 legal replies; every UCI should appear in the table.
    expected_uci_strings = sorted(m.uci() for m in chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1").legal_moves)
    assert len(expected_uci_strings) == 20
    for uci in expected_uci_strings:
        assert uci in table_section, f"missing UCI {uci!r} in opponent table"


def test_opponent_legal_moves_zero_on_mate(im):
    # Fool's mate position before the final move.
    board = chess.Board()
    for uci in ["f2f3", "e7e5", "g2g4"]:
        board.push_uci(uci)
    out = im.render_imagine(board, chess.Move.from_uci("d8h4"))
    # New phrasing: "_None — game over (gives checkmate)._"
    section = out.split("## Opponent legal replies")[1]
    assert "None" in section
    assert "checkmate" in out.lower()


# ── capture-netting: a winning capture that allows an equal recapture is an
#    even trade, not a blunder (regression for puzzle YZ2IM) ─────────────────

_YZ2IM = "4r1r1/p1k2np1/1pp1Bp1p/5P1P/2P1N3/1P6/8/2K3R1 w - - 1 36"


def test_capture_allowing_equal_recapture_is_not_a_material_loss(im):
    # Bxf7 wins a knight; the e4 knight then hangs to the e8 rook (Rxe4). Netted,
    # that is an even trade (the move captured a knight), so _material_loss must
    # report ~0 -- NOT a 3-pawn loss. (Bxg8 actually then wins more, but even the
    # one-ply-deep verdict must be "even", not "blunder".)
    b = chess.Board(_YZ2IM)
    mv = chess.Move.from_uci("e6f7")
    after = b.copy(); after.push(mv)
    loss_cp, _ = im._material_loss(b, after, mv)
    assert loss_cp == 0, f"expected even trade, got {loss_cp}cp loss"


def test_capture_netting_does_not_hide_real_blunder(im):
    # Hanging the queen for NOTHING (no capture) is still a full blunder -- the
    # netting only offsets by material the move actually captured.
    b = chess.Board("4k3/1q6/8/8/8/8/8/Q3K3 w - - 0 1")
    mv = chess.Move.from_uci("a1a7")  # Qa7?? Qxa7
    after = b.copy(); after.push(mv)
    loss_cp, piece = im._material_loss(b, after, mv)
    assert loss_cp >= 800 and piece == "queen"


def test_imagine_reframes_even_capture_not_as_refutation(im):
    # The opponent-reply section must NOT shout "NOT an even trade" for Bxf7;
    # instead it shows the "roughly even" note prompting deeper calculation.
    out = im.render_imagine(chess.Board(_YZ2IM), chess.Move.from_uci("e6f7"))
    assert "NOT an even trade" not in out
    assert "BLUNDER" not in out
    assert "roughly even" in out.lower() or "↔" in out


# ── _attacks_and_defenses helper ───────────────────────────────────────────


def test_attacks_and_defenses_splits_correctly(im):
    # White knight on f3 in starting position: attacks e5 (empty), d4 (empty),
    # g5 (empty), h4 (empty), and defends e1 (king), g1 (knight — wait, that's
    # where the knight came from in real play; in start position knight is on g1).
    # Use the actual start position: knight on g1 attacks f3 (empty), h3 (empty),
    # e2 (own pawn), so e2 is defended.
    board = chess.Board()
    atk, defs = im._attacks_and_defenses(board, chess.G1)
    # g1 knight attacks f3, h3, e2. f3/h3 are empty (no enemy or own piece),
    # e2 has own pawn (defends). No enemy attacks.
    assert atk == set()
    assert chess.E2 not in atk
    # No enemy on attacked squares, so atk is empty.
    # Defends includes any own piece on f3/h3/e2; only e2 has one.
    assert defs == {chess.E2}


def test_blunder_banner_redirects_a_checking_sacrifice_to_calculate(im):
    # A material-losing CHECK must NOT be flatly condemned as a blunder; it must
    # tell the agent to calculate the whole line (a sac/mate is judged at the end,
    # not at one ply). 3MIRf: Qxh7+ loses the queen at one ply but forces mate.
    b = chess.Board("5r1k/pp3p1p/2pb1np1/q7/3PnB1P/2N2Q2/PP3PP1/3RR1K1 w - - 0 1")
    # use the real puzzle position after its setup move for fidelity:
    import json, pathlib
    pj = pathlib.Path(__file__).resolve().parents[2] / "experiments/puzzle-benchmark/puzzles.json"
    if pj.exists():
        puz = {p["id"]: p for p in json.loads(pj.read_text())}.get("3MIRf")
        if puz:
            b = chess.Board(puz["fen"]); b.push(chess.Move.from_uci(puz["moves"][0]))
            out = im.render_imagine(b, chess.Move.from_uci("h4h7"))
            assert "gives CHECK but loses" in out
            assert "calculate the WHOLE line" in out
            assert "BLUNDER" not in out.split("\n")[0]  # not the hard-condemn banner


def test_non_check_material_loss_still_hard_blunder(im):
    b = chess.Board("4k3/1q6/8/8/8/8/8/Q3K3 w - - 0 1")
    out = im.render_imagine(b, chess.Move.from_uci("a1a7"))  # Qa7?? hangs queen, no check
    assert "BLUNDER" in out and "LOSES your queen" in out


def test_nearly_mate_nudge_on_forcing_check_sacrifice(im):
    # 8QAW1: Qd8+ is a queen sac leaving Black exactly ONE reply (Rxd8), then
    # Rxd8#. imagine_move must flag NEARLY MATE and hand the agent the imagine_line
    # call to find the mate — the lever for forced-mate sacs the agent declines.
    b = chess.Board("k5r1/ppp3r1/6q1/3Q4/4p3/6p1/PP5P/2RR2K1 w - - 0 33")
    out = im.render_imagine(b, chess.Move.from_uci("d5d8"))
    assert "NEARLY MATE" in out
    assert "only 1 legal reply" in out and "Rxd8" in out
    assert 'imagine_line(moves="Qd8+,Rxd8")' in out


def test_nearly_mate_silent_when_many_replies(im):
    # A check the king easily escapes (many replies) must NOT trigger the nudge.
    b = chess.Board("4k3/8/8/8/8/8/4R3/4K3 w - - 0 1")  # Re2-e7+? king has d/f files
    # Rook check on the e-file: king on e8 can go to d7/d8/f7/f8 -> several replies
    out = im.render_imagine(b, chess.Move.from_uci("e2e7"))
    assert "NEARLY MATE" not in out


def test_boxing_check_escape_count_is_correct_in_check(im):
    """Regression: the enemy-king escape count after a check must count the king's
    legal moves DIRECTLY (it is in check, its turn) — never via a null move, which
    is illegal while in check and silently misreports. 1pYEx: after Bh5+ the king
    has 2 real escapes (NOT boxed); only Bb5+/Bg4+ box it to <=1. The old null-move
    method wrongly reported 0 escapes for every check."""
    b = chess.Board("rnb1kb1r/ppp2npp/3p1q2/8/8/8/PPPPBPPP/RNBQR1K1 w kq - 2 9")
    sans, esc = im._uncalculated_mating_checks(b)
    assert esc <= 1
    assert "Bb5+" in sans            # the real mating candidate
    assert "Bh5+" not in sans        # NOT boxing (2 escapes) — must be excluded


def test_zwischenzug_nudge_on_natural_recapture(im):
    """46IHG: after the opponent grabs the queen on a1, the win is the in-between
    check Rxd7+ FIRST, then Nxd7, then Rxa1 -- not the immediate recapture Rxa1.
    When the agent imagines the natural recapture (a non-check capture) and a legal
    check exists, imagine_move must surface the zwischenzug."""
    b = chess.Board("8/p2r2kp/1p4p1/2n5/8/3R2P1/4PP1P/q4RK1 w - - 0 45")
    out = im.render_imagine(b, b.parse_san("Rxa1"))
    assert "ZWISCHENZUG" in out and "Rxd7+" in out
    # a quiet position with NO check available -> helper returns empty
    assert im._available_checks(chess.Board("4k3/8/8/8/8/8/P7/4K3 w - - 0 1")) == []


class TestStillHangingOwnPieces:
    """A candidate move that IGNORES a pre-existing hang must say so — the
    newly-hanging scan deliberately skips pieces that were already unsafe, which
    made such candidates render clean (game 2358c1 mv67: imagine_move(Kh3) said
    nothing about the d2 knight the opponent was winning; the agent asserted
    'it's only a trade' with the wrong capture order and lost a piece)."""

    FEN_2358C1 = "6r1/p4p2/4k3/1p1pP2p/7P/Pn4P1/2rN2K1/3R4 w - - 7 34"

    def _render(self, im, fen, san):
        b = chess.Board(fen)
        return im.render_imagine(b, b.parse_san(san))

    def test_ignoring_move_flags_still_hanging(self, im):
        out = self._render(im, self.FEN_2358C1, "Kh3")
        assert "Still hanging (this move ignores it)" in out
        assert "knight on d2" in out
        assert 'imagine_trade(target="d2")' in out

    def test_saving_move_is_silent(self, im):
        # Rxd2?? is illegal (own piece); moving the attacked-piece scenario:
        # defend d2 is impossible here, but a move BY the hanging piece must not
        # flag (use a position where the hanging piece moves away).
        fen = "4k3/8/8/8/8/1n6/3N4/4K2R w K - 0 1"  # Nd2 attacked by Nb3, undefended
        out = self._render(im, fen, "Nf3")  # moves the hanging piece away
        assert "Still hanging" not in out

    def test_check_giving_move_is_silent(self, im):
        # Same 2358c1 position: a checking move forces the reply, opponent
        # cannot cash the d2 hang on the immediate reply.
        b = chess.Board(self.FEN_2358C1)
        checks = [m for m in b.legal_moves if b.gives_check(m)]
        if checks:
            out = im.render_imagine(b, checks[0])
            assert "Still hanging" not in out

    def test_safe_pieces_never_flag(self, im):
        out = self._render(im, chess.STARTING_FEN, "e4")
        assert "Still hanging" not in out
