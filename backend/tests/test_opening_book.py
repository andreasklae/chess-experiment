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


def test_recapture_on_d4_is_book_not_a_developing_move():
    """Regression (real game 1705bcb5): after 1.d4 Nf6 2.Bf4 c5 3.e3 cxd4 the book told
    the agent to play the routine developing move Nf3, so it had to IMPROVISE the exd4
    recapture. Recapturing the centre pawn is core London theory — it must be BOOK.
    """
    b = _board("d4", "Nf6", "Bf4", "c5", "e3", "cxd4")
    e = ob.lookup(b)
    assert e is not None and e.moves == ["exd4"], f"expected exd4 as book, got {e and e.moves}"
    assert e.source == "rule" and "recapture" in e.line.lower()
    assert e.wiki == "openings/london-central-break"
    # with c3 already in, BOTH recaptures are book candidates (exd4 first — Carlsbad)
    b2 = _board("d4", "d5", "Bf4", "Nf6", "e3", "c5", "c3", "Nc6", "Nf3", "cxd4")
    e2 = ob.lookup(b2)
    assert e2 is not None and e2.moves[0] == "exd4" and "cxd4" in e2.moves
    # the recapture rule carries assumptions + exceptions (agent still reasons)
    assert e.assumes and e.exceptions
    # a plain quiet position (no pawn on d4) does NOT trigger the recapture rule
    quiet = _board("d4", "d5", "Bf4", "Nf6")  # White to move, needs e3 — not a recapture
    eq = ob.lookup(quiet)
    assert eq is not None and "recapture" not in eq.line.lower()


def test_dark_bishop_attacked_by_pawn_is_book_not_a_setup_move():
    """Regression (real game 5166674a): after 1.d4 d6 2.Bf4 e5, the …e5 pawn attacks the
    f4-bishop, but the book offered the routine setup move e3 — the agent had to improvise
    dxe5. Reacting to a pawn attack on the London bishop is theory, so it must be BOOK.
    """
    b = _board("d4", "d6", "Bf4", "e5")
    e = ob.lookup(b)
    assert e is not None and "dark bishop" in e.line.lower()
    # dxe5 (challenge the attacker) is offered first, then safe retreats — NOT plain e3
    assert e.moves[0] == "dxe5" and "e3" not in e.moves
    # never a bishop capture that loses the piece (Bxe5 answered by …dxe5)
    assert "Bxe5" not in e.moves
    # every offered move is legal
    for san in e.moves:
        assert b.parse_san(san) in b.legal_moves
    assert e.wiki == "openings/london-vs-kings-indian" and e.assumes and e.exceptions
    # …g5 hitting f4 → a safe retreat is book
    b2 = _board("d4", "d5", "Bf4", "h6", "e3", "g5")
    e2 = ob.lookup(b2)
    assert e2 is not None and "dark bishop" in e2.line.lower() and e2.moves
    # control: quiet position (bishop not attacked) still gives the normal setup move
    quiet = _board("d4", "d5", "Bf4", "Nf6")
    eq = ob.lookup(quiet)
    assert eq is not None and "dark bishop" not in eq.line.lower()


def test_recapture_a_traded_minor_is_book():
    """Regression (10 Maia games, move 7): after …Bxf4 trading the London dark bishop,
    the book returned NOTHING (the material tactic-guard misread the exf4 recapture as a
    'winning capture' and deferred), so the agent improvised exf4 every game. Recapturing
    a traded piece is theory — and the recapture must never be suppressed by the guard.
    Generalised to the light bishop on d3 (…Bxd3, seen in batch-3 game 8).
    """
    b = _board("d4", "d5", "Bf4", "Nc6", "e3", "Nf6", "Nf3", "e6", "Bd3", "Bd6", "c3", "Bxf4")
    e = ob.lookup(b)
    assert e is not None and e.moves[0] == "exf4" and "traded minor" in e.line.lower()
    assert e.wiki == "openings/london-central-break" and e.assumes and e.exceptions
    # …Nxg3 (bishop on g3) → hxg3 opens the h-file, also book (pawn recapture first)
    b2 = _board("d4", "d5", "Bf4", "Nf6", "e3", "c5", "c3", "Nc6", "Nf3", "Nh5", "Bg3", "Nxg3")
    e2 = ob.lookup(b2)
    assert e2 is not None and "hxg3" in e2.moves and "traded minor" in e2.line.lower()
    # …Bxd3 (light bishop) → Qxd3 first (keeps pawns healthy), cxd3 also offered
    b3 = _board("d4", "d6", "Bf4", "Be6", "e3", "Qd7", "Nf3", "Bf5", "Bd3", "Bxd3")
    e3 = ob.lookup(b3)
    assert e3 is not None and e3.moves[0] == "Qxd3" and "traded minor" in e3.line.lower()
    # a real MATE-in-1 still beats a recapture (reaction rules bypass the *material* guard
    # but not mate): pure back-rank mate position → book stays silent.
    mate = chess.Board("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")
    assert ob.lookup(mate) is None


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
    assert "Bf4" in out and "Book candidate" in out
    # a book move carries its assumptions + the "you decide" framing (not an oracle)
    assert "Assumes:" in out and "You decide" in out
    sic = chess.Board("rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2")
    assert "Out of book" in obt.render(sic)


def test_book_entries_carry_assumptions_and_exceptions():
    """Every book entry (exact line or setup rule) must come WITH its assumptions and
    exceptions, so the agent reasons over it rather than treating it as an oracle."""
    # every entry carries assumptions + exceptions + a wiki pointer
    for seq in (["d4", "d5", "Bf4", "c5", "e3", "Qb6"],   # exact-line ...Qb6 (Qc1)
                ["d4", "d5"]):                            # setup rule (Bf4)
        e = ob.lookup(_board(*seq))
        assert e is not None
        assert len(e.moves) >= 1 and e.assumes and e.exceptions and e.wiki
    # the ...Qb6 SETUP RULE (deep position, not an exact line) carries the
    # "position moved on -> may be a blunder" exception so the agent reasons.
    deep_qb6 = chess.Board("r3kb1r/pp3ppp/1qn5/4P3/2p1pBb1/2P1PN2/PPQ2PPP/R3KB1R w KQkq - 0 11")
    e2 = ob.lookup(deep_qb6)
    assert e2 is not None and e2.source == "rule"
    assert "no longer" in e2.exceptions.lower() or "moved on" in e2.exceptions.lower()


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


def test_setup_rule_defers_to_a_mate_in_1():
    """The book must NOT suggest a quiet setup move when a forcing tactic (mate-in-1 /
    winning capture) is on the board — that would mislead. Position: White can play a
    setup move structurally, but Qh7# is available → book stays silent."""
    # White to move, London-ish structure, but mate-in-1 Qh7# available.
    b = chess.Board("6rk/6pp/8/8/8/8/5PPP/3Q1RK1 w - - 0 1")
    # Qh7 is not mate here; build a clean mate-in-1 instead:
    b = chess.Board("7k/6pp/8/8/8/7Q/6PP/6K1 w - - 0 1")  # Qxh7#? h7 occupied by pawn
    b = chess.Board("5rk1/6pp/8/8/8/6Q1/6PP/6K1 w - - 0 1")  # Qg3-g7? not mate
    # Simplest reliable mate-in-1: back-rank.
    b = chess.Board("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")  # Ra8#
    assert any((lambda m: (lambda c: (c.push(m), c.is_checkmate())[1])(b.copy()))(m)
               for m in b.legal_moves)
    # The exact-book/rule lookup should not invent a setup move in a non-London bare
    # position anyway; the point is the guard helper detects the tactic.
    assert ob._strong_tactic_available(b) is True


def test_strong_tactic_helper_quiet_position_is_false():
    quiet = chess.Board("rnbqkb1r/ppp1pppp/5n2/3p4/3P1B2/4P3/PPP2PPP/RN1QKBNR w KQkq - 0 3")
    assert ob._strong_tactic_available(quiet) is False
    # and the book still gives the setup move in this quiet position
    e = ob.lookup(quiet)
    assert e is not None
