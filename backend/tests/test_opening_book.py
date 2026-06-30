"""Tests for the London opening book + the two opening tools.

The book is tutor-authored prepared theory (fair: memorised repertoire, not an engine).
These tests pin the contract: every book move is LEGAL, the move-order-dependent ...Qb6
answer is correct, out-of-book returns nothing, and the tools render sensibly.
"""
import sys
from pathlib import Path

import chess
import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "skills/chess/scripts"
sys.path.insert(0, str(_SCRIPTS))

import _opening_book as ob  # noqa: E402
import opening_book as obt  # noqa: E402
import opening_guide as ogt  # noqa: E402


def _board(*sans):
    b = chess.Board()
    for s in sans:
        b.push_san(s)
    return b


# ── the book ─────────────────────────────────────────────────────────────────────

def test_every_book_move_is_legal_for_its_position():
    """Exact-book: each stored move must be legal in the position it is keyed to."""
    for key, entry in ob.EXACT_BOOK.items():
        placement, stm, castling, ep = key.split(" ")
        board = chess.Board(f"{placement} {stm} {castling} {ep} 0 1")
        for san in entry.moves:
            mv = board.parse_san(san)
            assert mv in board.legal_moves, f"{san} illegal in {key}"


def test_qb6_response_is_move_order_dependent():
    """The crux the generic prompt got wrong: Qb3 only after c3, else Qc1/b3."""
    no_c3 = _board("d4", "d5", "Bf4", "c5", "e3", "Qb6")
    e = ob.lookup(no_c3)
    assert e and e.moves[0] in ("Qc1", "b3") and "Qb3" not in e.moves
    # and Qb3 is genuinely illegal there (the reason)
    with pytest.raises(Exception):
        no_c3.parse_san("Qb3")

    with_c3 = _board("d4", "d5", "Bf4", "Nf6", "e3", "c5", "c3", "Qb6")
    e2 = ob.lookup(with_c3)
    assert e2 and e2.moves[0] == "Qb3"


def test_setup_rules_fill_transpositions():
    """A London position reached by a different move order still gets a book move via
    the setup-rule layer (exact-only would miss it)."""
    # 1.d4 Nf6 2.Bf4 d5 3.e3 (a different order than the main line) — still book.
    b = _board("d4", "Nf6", "Bf4", "d5", "e3", "e6", "Nf3")  # White to move next? it's black
    # after 7...(black) ... take a White-to-move setup spot:
    b = _board("d4", "Nf6", "Bf4", "d5")   # White to move, needs e3
    e = ob.lookup(b)
    assert e is not None and e.moves[0] == "e3"


def test_bishop_out_before_e3():
    """The defining London rule: with d4 played and bishop still on c1, the book says
    Bf4 (outside the chain), not e3."""
    b = _board("d4", "d5")
    e = ob.lookup(b)
    assert e and e.moves[0] == "Bf4"


def test_out_of_book_returns_none():
    # Sicilian-ish, not our repertoire
    b = chess.Board("rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2")
    assert ob.lookup(b) is None
    # also: never answers for Black
    b2 = _board("d4")
    assert b2.turn == chess.BLACK and ob.lookup(b2) is None


def test_book_never_suggests_an_illegal_move_on_a_sweep():
    """Random-ish London-reachable positions: any book move returned must be legal."""
    import random
    random.seed(3)
    openings = [["d4", "d5", "Bf4"], ["d4", "Nf6", "Bf4", "g6"],
                ["d4", "d5", "Bf4", "c5", "e3"], ["d4", "Nf6", "Bf4", "d5", "e3", "c5", "c3"]]
    for seq in openings:
        b = chess.Board()
        for s in seq:
            b.push_san(s)
        # walk a few plies, checking book legality at each White move
        for _ in range(6):
            if b.turn == chess.WHITE:
                e = ob.lookup(b)
                if e:
                    for san in e.moves:
                        assert b.parse_san(san) in b.legal_moves
            moves = list(b.legal_moves)
            if not moves:
                break
            b.push(random.choice(moves))


# ── the tools render ───────────────────────────────────────────────────────────

def test_opening_book_tool_renders_move_and_out_of_book():
    b = _board("d4", "d5")
    out = obt.render(b)
    assert "Book move: Bf4" in out
    sic = chess.Board("rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2")
    assert "Out of book" in obt.render(sic)


def test_opening_guide_routes_qb6_and_greek_gift():
    qb6 = _board("d4", "d5", "Bf4", "c5", "e3", "Qb6")
    g = ogt.render(qb6)
    assert "london-vs-qb6" in g
    # greek-gift route: Bd3 vs castled black king, no Nf6
    gg = chess.Board("r1bq1rk1/pppn1ppp/3bp3/3pP3/3P4/3B1N2/PPP2PPP/RNBQ1RK1 w - - 0 1")
    assert "london-bxh7-greek-gift" in ogt.render(gg)


def test_tools_only_answer_for_white():
    b = _board("d4")  # black to move
    assert "Not White to move" in obt.render(b)
    assert "Not White to move" in ogt.render(b)
