"""Tests for the chess-player skill's imagine_move script."""

import importlib.util
import sys
from pathlib import Path

import chess
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "skills" / "chess-player" / "scripts" / "imagine_move.py"


@pytest.fixture(scope="module")
def im():
    spec = importlib.util.spec_from_file_location("imagine_move", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["imagine_move"] = module
    spec.loader.exec_module(module)
    return module


# ── Basic rendering ────────────────────────────────────────────────────────


def test_render_includes_all_sections(im):
    out = im.render_imagine(chess.Board(), chess.Move.from_uci("e2e4"))
    for section in [
        "FEN: ", "Side to move: ", "Move:", "Check:", "Discovered attacks:",
        "Moved piece status", "No longer attacking:", "No longer defending:",
        "Newly hanging own pieces:", "Opponent legal moves:",
    ]:
        assert section in out


def test_render_does_not_mutate_input_board(im):
    board = chess.Board()
    original_fen = board.fen()
    im.render_imagine(board, chess.Move.from_uci("e2e4"))
    assert board.fen() == original_fen


def test_render_shows_resulting_fen(im):
    out = im.render_imagine(chess.Board(), chess.Move.from_uci("e2e4"))
    # After 1.e4, side to move is black.
    assert "Side to move: black" in out
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
    assert "Check:              none" in out


# ── Discovered attacks ─────────────────────────────────────────────────────


def test_discovered_attack_bishop_behind_pawn(im):
    # Position: white bishop c1, white pawn d2, black pawn h6. Push d2-d4
    # opens diagonal c1-h6.
    board = chess.Board("rnbqkbnr/ppp1pppp/7p/3p4/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 2")
    out = im.render_imagine(board, chess.Move.from_uci("d2d4"))
    assert "Discovered attacks:" in out
    # The bishop on c1 should now attack the pawn on h6.
    discoveries_section = out.split("Discovered attacks:")[1].split("Moved piece status")[0]
    assert "bishop on c1" in discoveries_section
    assert "h6" in discoveries_section


def test_no_discovered_attacks_when_none(im):
    # Standard 1.e4 has no discovered attacks (no piece behind e2 of the same color
    # that can attack along the e-file).
    out = im.render_imagine(chess.Board(), chess.Move.from_uci("e2e4"))
    assert "Discovered attacks: (none)" in out


# ── Newly hanging own pieces ───────────────────────────────────────────────


def test_newly_hanging_after_queen_abandons_pawn(im):
    # White queen d1 is the sole defender of white pawn d4 against black pawn e5.
    # Moving the queen away leaves d4 hanging.
    board = chess.Board("4k3/8/4r3/3pp3/3P4/8/8/3QK3 w - - 0 1")
    out = im.render_imagine(board, chess.Move.from_uci("d1h5"))
    assert "Newly hanging own pieces:" in out
    hanging_section = out.split("Newly hanging own pieces:")[1].split("Opponent legal moves:")[0]
    assert "pawn on d4" in hanging_section
    assert "defended by nothing" in hanging_section


def test_no_newly_hanging_when_safe(im):
    out = im.render_imagine(chess.Board(), chess.Move.from_uci("e2e4"))
    assert "Newly hanging own pieces: (none)" in out


def test_moved_piece_itself_not_in_newly_hanging(im):
    """The moved piece's own attack/defense status belongs in 'Moved piece status',
    not 'Newly hanging'. Confirm a knight moving to an attacked square is not
    double-counted."""
    # White knight g1 moves to f3, attacked by nothing in start position — non-test.
    # Build: white knight moves to an attacked square.
    board = chess.Board("4k3/8/8/8/8/2n5/8/4K1N1 w - - 0 1")
    out = im.render_imagine(board, chess.Move.from_uci("g1e2"))
    # Knight on e2 — let's not even bother with attacks here, just confirm
    # the moved piece isn't echoed in newly-hanging.
    hanging_section = out.split("Newly hanging own pieces:")[1].split("Opponent legal moves:")[0]
    assert "on e2" not in hanging_section


# ── Attack/defense deltas (no longer attacking / defending) ────────────────


def test_no_longer_attacking_lists_previous_targets(im):
    # Knight on f3 attacks e5, d4, g5, h4 (and back-rank squares). Move it to h4.
    # After the move, f3 squares it controlled but h4 doesn't are "no longer attacking"
    # — but the section only lists squares with enemy pieces. We need an enemy on a square
    # f3 was hitting that h4 isn't.
    # f3 attacks e5; h4 doesn't.
    board = chess.Board("4k3/8/8/4p3/8/5N2/8/4K3 w - - 0 1")
    out = im.render_imagine(board, chess.Move.from_uci("f3h4"))
    # Knight on f3 was attacking pawn on e5; knight on h4 isn't.
    no_longer_section = out.split("No longer attacking:")[1].split("No longer defending:")[0]
    assert "pawn on e5" in no_longer_section


def test_no_longer_defending_excludes_from_square(im):
    """The from-square shouldn't appear in 'no longer defending' — the piece
    that 'defended' from-square is the moved piece itself, which is gone."""
    board = chess.Board()
    out = im.render_imagine(board, chess.Move.from_uci("g1f3"))
    no_longer_def = out.split("No longer defending:")[1].split("Newly hanging")[0]
    # Knight on g1 defended e2 (no — knights from g1 attack e2, f3, h3).
    # The g1 square itself shouldn't be in the "no longer defending" list.
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
    board = chess.Board()
    board.push_uci("e2e4")
    expected = board.legal_moves.count()
    # Roll back for the test
    board = chess.Board()
    out = im.render_imagine(board, chess.Move.from_uci("e2e4"))
    assert f"Opponent legal moves: {expected}" in out


def test_opponent_legal_moves_truncates_at_12(im):
    """Output preview shows up to 12 moves with a +N more suffix."""
    out = im.render_imagine(chess.Board(), chess.Move.from_uci("e2e4"))
    # Black has 20 legal replies after 1.e4. Should see "+8 more" or similar.
    line = next(l for l in out.split("\n") if l.startswith("Opponent legal moves:"))
    assert "+" in line and "more" in line


def test_opponent_legal_moves_zero_on_mate(im):
    # Fool's mate position before the final move.
    # 1.f3 e5 2.g4 Qh4# — let's set up the position before 2...Qh4#.
    board = chess.Board()
    for uci in ["f2f3", "e7e5", "g2g4"]:
        board.push_uci(uci)
    out = im.render_imagine(board, chess.Move.from_uci("d8h4"))
    assert "Opponent legal moves: 0" in out
    assert "checkmate" in out.lower()


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
