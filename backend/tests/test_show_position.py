"""Tests for the chess skill's show_position script — focused on
the x-ray battery detection and pinned annotation."""

import importlib.util
import sys
from pathlib import Path

import chess
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "skills" / "chess" / "scripts" / "show_position.py"


@pytest.fixture(scope="module")
def sp():
    spec = importlib.util.spec_from_file_location("show_position", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["show_position"] = module
    spec.loader.exec_module(module)
    return module


def _chain_to_names(board: chess.Board, chain):
    return [(chess.square_name(sq), is_xray) for sq, is_xray in chain]


def test_no_attackers(sp):
    board = chess.Board()  # starting position; nothing attacks anything across the line
    assert sp.compute_attack_chain(board, chess.BLACK, chess.E4) == []
    assert sp.compute_attack_chain(board, chess.WHITE, chess.E5) == []


def test_immediate_attacker_no_xray(sp):
    # Knight on f3 attacks e5; no x-ray possible behind a knight.
    board = chess.Board("4k3/8/8/4p3/8/5N2/8/4K3 w - - 0 1")
    chain = sp.compute_attack_chain(board, chess.WHITE, chess.E5)
    assert _chain_to_names(board, chain) == [("f3", False)]


def test_bishop_xray_behind_pawn_diagonal(sp):
    # Pawn c4 attacks d5; bishop b3 sits behind on the b3-c4-d5 diagonal.
    # Removing c4 reveals bishop attacking d5.
    board = chess.Board("4k3/8/8/3p4/2P5/1B6/8/4K3 w - - 0 1")
    chain = sp.compute_attack_chain(board, chess.WHITE, chess.D5)
    assert _chain_to_names(board, chain) == [("c4", False), ("b3", True)]


def test_queen_xray_behind_rook_on_file(sp):
    # Rook d3 attacks d5; queen d2 sits behind on the d-file. Black pawn on d5.
    board = chess.Board("4k3/8/8/3p4/8/3R4/3Q4/4K3 w - - 0 1")
    chain = sp.compute_attack_chain(board, chess.WHITE, chess.D5)
    assert _chain_to_names(board, chain) == [("d3", False), ("d2", True)]


def test_chained_xray_rook_rook_queen(sp):
    # d-file stack: target on d8 (black king area), white rook d4, rook d3, queen d2.
    # Use a synthetic position; ensure both chained sliders are reported in order.
    board = chess.Board("3p3k/8/8/8/3R4/3R4/3Q4/4K3 w - - 0 1")
    chain = sp.compute_attack_chain(board, chess.WHITE, chess.D8)
    assert _chain_to_names(board, chain) == [("d4", False), ("d3", True), ("d2", True)]


def test_xray_blocked_by_wrong_color(sp):
    # Pawn c4 attacks d5. Behind on b3 is a *black* bishop — not an xray for white.
    board = chess.Board("4k3/8/8/3p4/2P5/1b6/8/4K3 w - - 0 1")
    chain = sp.compute_attack_chain(board, chess.WHITE, chess.D5)
    assert _chain_to_names(board, chain) == [("c4", False)]


def test_xray_blocked_by_non_slider(sp):
    # Pawn c4 attacks d5. Behind on b3 is a white knight — knights don't extend along the diagonal.
    board = chess.Board("4k3/8/8/3p4/2P5/1N6/8/4K3 w - - 0 1")
    chain = sp.compute_attack_chain(board, chess.WHITE, chess.D5)
    assert _chain_to_names(board, chain) == [("c4", False)]


def test_rook_not_an_xray_on_diagonal(sp):
    # Pawn c4 attacks d5. Behind on b3 is a white *rook* — rooks don't move on diagonals.
    board = chess.Board("4k3/8/8/3p4/2P5/1R6/8/4K3 w - - 0 1")
    chain = sp.compute_attack_chain(board, chess.WHITE, chess.D5)
    assert _chain_to_names(board, chain) == [("c4", False)]


def test_bishop_not_an_xray_on_file(sp):
    # Rook d3 attacks d5. Behind on d2 is a white bishop — bishops don't move on files.
    board = chess.Board("4k3/8/8/3p4/8/3R4/3B4/4K3 w - - 0 1")
    chain = sp.compute_attack_chain(board, chess.WHITE, chess.D5)
    assert _chain_to_names(board, chain) == [("d3", False)]


def test_two_immediate_attackers_each_with_xray(sp):
    # Black pawn d5; white attackers: pawn c4 (with bishop b3 xray) and pawn e4 (with bishop f3 xray).
    board = chess.Board("4k3/8/8/3p4/2P1P3/1B3B2/8/4K3 w - - 0 1")
    chain = sp.compute_attack_chain(board, chess.WHITE, chess.D5)
    names = _chain_to_names(board, chain)
    # Cheapest-first ordering puts both pawns first (each followed by its own xray).
    assert names == [("c4", False), ("b3", True), ("e4", False), ("f3", True)]


def test_pinned_annotation_in_format_chain(sp):
    # Black queen pins white bishop on e2 to the white king on e1 along the e-file.
    # The bishop attacks (say) d3 but is pinned. The chain should mark it (pinned).
    board = chess.Board("4k3/8/8/8/8/3p4/4B3/4K2q b - - 0 1")
    # White bishop on e2 attacks d3. Is it pinned? Queen h1 pins along rank 1, not e-file. Adjust:
    board = chess.Board("4k3/8/8/8/8/3p4/4B3/4K2r w - - 0 1")
    # Rook h1 pins bishop e2 along rank 1? No, e2 is rank 2, not rank 1. Need a true pin.
    # Real pin: black queen on e8, white king e1, white bishop e2 in between, pinned along e-file.
    board = chess.Board("4q3/8/8/8/8/3p4/4B3/4K3 w - - 0 1")
    assert board.is_pinned(chess.WHITE, chess.E2)
    chain = sp.compute_attack_chain(board, chess.WHITE, chess.D3)
    rendered = sp.format_chain(board, chess.WHITE, chain)
    assert "bishop on e2 (pinned)" in rendered


def test_not_pinned_no_annotation(sp):
    # Bishop on c3 attacks e5 along the c3-d4-e5 diagonal; nothing pins it.
    board = chess.Board("4k3/8/8/4p3/8/2B5/8/4K3 w - - 0 1")
    chain = sp.compute_attack_chain(board, chess.WHITE, chess.E5)
    rendered = sp.format_chain(board, chess.WHITE, chain)
    assert "(pinned)" not in rendered
    assert "bishop on c3" in rendered


def test_defender_chain_excludes_self(sp):
    # White pawn on e4, defended by pawn on d3. Black knight on f6 attacks e4.
    # When listing defenders of e4, e4 itself must not appear.
    board = chess.Board("4k3/8/5n2/8/4P3/3P4/8/4K3 b - - 0 1")
    attacker_chain = sp.compute_attack_chain(board, chess.BLACK, chess.E4)
    defender_chain = [(s, x) for s, x in sp.compute_attack_chain(board, chess.WHITE, chess.E4) if s != chess.E4]
    assert _chain_to_names(board, attacker_chain) == [("f6", False)]
    assert _chain_to_names(board, defender_chain) == [("d3", False)]


def test_render_position_smoke(sp):
    """End-to-end: render a real middlegame and check key sections appear.
    Output is markdown, so checks use the markdown structure."""
    board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
    output = sp.render_position(board)
    assert "**Side to move:** white" in output
    assert "**FEN:**" in output
    assert "## Your pieces under attack" in output
    assert "## Opponent pieces you are attacking" in output
    # Knight f3 attacks pawn e5; pawn e5 defended by knight c6.
    assert "pawn on e5" in output
    assert "knight on f3" in output
    assert "knight on c6" in output
    # Move 3, full piece count -> early opening.
    assert "**Phase:** early opening" in output
    # Material balance line is now embedded in show_position output.
    assert "Material balance:" in output


# ── phase detection ─────────────────────────────────────────────────────────


def test_phase_score_starting_position(sp):
    assert sp.phase_score(chess.Board()) == 24


def test_phase_score_after_queen_trade(sp):
    # Both queens off, otherwise full material -> 24 - 2*4 = 16.
    board = chess.Board("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1")
    assert sp.phase_score(board) == 16


def test_phase_score_only_kings(sp):
    board = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
    assert sp.phase_score(board) == 0


def test_phase_early_opening_move_1(sp):
    label, score, move = sp.detect_phase(chess.Board())
    assert label == "early opening"
    assert score == 24
    assert move == 1


def test_phase_early_opening_move_6(sp):
    # Move 6, full material -> still early opening.
    board = chess.Board()
    for san in ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "d3", "d6", "Nc3", "Nf6", "Bg5"]:
        board.push_san(san)
    assert board.fullmove_number == 6
    label, _, _ = sp.detect_phase(board)
    assert label == "early opening"


def test_phase_late_opening_move_7(sp):
    # Move 7, full material -> late opening.
    board = chess.Board()
    for san in ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "d3", "d6", "Nc3", "Nf6", "Bg5", "h6", "Bh4"]:
        board.push_san(san)
    assert board.fullmove_number == 7
    label, _, _ = sp.detect_phase(board)
    assert label == "late opening"


def test_phase_early_middlegame_after_minor_trades(sp):
    # One bishop off each side -> score = 24 - 2 = 22... still opening band.
    # We need score in 20-23 AND move > 15 to land in early middlegame.
    # Drop one knight and one bishop per side: 24 - 4 = 20.
    # Back rank: RN.QKB.R (knight b1, queen d1, king e1, bishop f1, rooks a1+h1).
    board = chess.Board("rn1qkb1r/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RN1QKB1R w KQkq - 0 16")
    assert sp.phase_score(board) == 20
    label, _, _ = sp.detect_phase(board)
    assert label == "early middlegame"


def test_phase_late_middlegame(sp):
    # Score in 14-19 with queens still on. Drop both bishops per side: 24 - 4 = 20 (still early MG).
    # Drop both bishops AND one knight per side: 24 - 6 = 18 -> late middlegame.
    board = chess.Board("rn1qk2r/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RN1QK2R w KQkq - 0 20")
    assert sp.phase_score(board) == 18
    label, _, _ = sp.detect_phase(board)
    assert label == "late middlegame"


def test_phase_endgame_no_queens_keeps_material(sp):
    # Score 16 (queens off, otherwise full) -> queen rule forces endgame even though score is "middlegame".
    board = chess.Board("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 10")
    assert sp.phase_score(board) == 16
    label, _, _ = sp.detect_phase(board)
    assert label in ("early endgame", "late endgame")  # specifically score>=8 -> early
    assert label == "early endgame"


def test_phase_early_endgame_by_score(sp):
    # Score 10, queens still on (somehow) -> early endgame by score.
    # Both rooks gone (–8), both bishops gone (–4), both knights gone (–4) leaves queens only: 8 score.
    # Let's hit exactly score 10: queens + 1 minor each = 8 + 2 = 10.
    board = chess.Board("3qk1n1/pppppppp/8/8/8/8/PPPPPPPP/3QK1N1 w - - 0 25")
    assert sp.phase_score(board) == 10
    label, _, _ = sp.detect_phase(board)
    assert label == "early endgame"


def test_phase_late_endgame(sp):
    # Score < 8: just kings and pawns.
    board = chess.Board("4k3/pppppppp/8/8/8/8/PPPPPPPP/4K3 w - - 0 40")
    assert sp.phase_score(board) == 0
    label, _, _ = sp.detect_phase(board)
    assert label == "late endgame"


def test_phase_queens_off_takes_priority(sp):
    # Move 8, only queens missing (score 16) — queen rule says endgame, not middlegame.
    board = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNB1KBNR w KQkq - 0 8")
    assert sp.phase_score(board) == 16
    label, _, _ = sp.detect_phase(board)
    assert label == "early endgame"


def test_phase_score_overrides_opening_move_when_score_low(sp):
    # Move 5 (early), but score already at 14 (heavy early trades) -> middlegame, not opening.
    # Per side: Q (4) + R (2) + N (1) = 7. Total = 14. Queens still on.
    board = chess.Board("rn1qk3/pppppppp/8/8/8/8/PPPPPPPP/3QKN1R w K - 0 5")
    assert sp.phase_score(board) == 14
    label, _, move = sp.detect_phase(board)
    assert move == 5
    # Score-driven (14-19 with queens still on) -> late middlegame, even though move is early.
    assert label == "late middlegame"
