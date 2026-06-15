"""Tests for the repetition / 50-move draw flags in the perception scripts
(_live.draw_flag, render_moves_table integration, imagine_move warning).

These exist because two of the first puzzle-session games were lost to
threefold repetition: the agent shuffled between two positions even after
the radar warned. The flags make the draw visible on the *candidate move*,
before it is played.
"""

import sys
from pathlib import Path

import chess

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "chess" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _live import board_with_history, draw_flag  # noqa: E402
from _eval import render_moves_table  # noqa: E402
from imagine_move import render_imagine  # noqa: E402


def shuffled_board():
    """Knight-shuffle position: pushing Ng1 once more recreates the start
    position for the second time; after black mirrors, a third occurrence
    looms."""
    b = chess.Board()
    for san in ["Nf3", "Nf6", "Ng1", "Ng8", "Nf3", "Nf6"]:
        b.push_san(san)
    return b  # white to move; Ng1 -> 2nd occurrence of start, ...Ng8 -> 3rd


class TestDrawFlag:
    def test_second_occurrence_flagged_repeats(self):
        b = chess.Board()
        for san in ["Nf3", "Nf6"]:
            b.push_san(san)
        # Ng1 then ...Ng8 returns to start (2nd occurrence). White's Ng1
        # creates a position seen once before? No — flag fires on ...Ng8.
        b.push_san("Ng1")
        assert draw_flag(b, b.parse_san("Ng8")) == "repeats!"

    def test_third_occurrence_flagged_draw(self):
        b = shuffled_board()
        b.push_san("Ng1")
        assert draw_flag(b, b.parse_san("Ng8")) == "draw:repetition"

    def test_progress_move_unflagged(self):
        b = shuffled_board()
        assert draw_flag(b, b.parse_san("e4")) == ""

    def test_fifty_move_rule_flagged(self):
        b = chess.Board("4k3/8/8/8/8/8/8/R3K3 w - - 99 80")
        b.push_san("Ra2")  # halfmove clock hits 100 - but no stack history...
        # draw_flag needs the move on a board; rebuild properly:
        b = chess.Board("4k3/8/8/8/8/8/8/R3K3 w - - 99 80")
        assert draw_flag(b, b.parse_san("Ra2")) == "draw:50-move"
        # a pawnless capture-free check is also flagged; a capture resets
        assert draw_flag(b, b.parse_san("Ke2")) == "draw:50-move"

    def test_bare_board_reports_nothing_for_repetition(self):
        b = chess.Board()  # no stack
        assert draw_flag(b, b.parse_san("Nf3")) == ""


class TestMovesTableIntegration:
    def test_flag_column_carries_draw_warning(self):
        b = shuffled_board()
        b.push_san("Ng1")
        table = render_moves_table(b, list(b.legal_moves))
        row = next(r for r in table.splitlines() if "g8f6" in r or "Ng8" in r.replace(" ", ""))
        # ...Ng8 immediately allows threefold claim
        assert "draw:repetition" in row

    def test_quiet_position_has_no_draw_flags(self):
        b = chess.Board()
        table = render_moves_table(b, list(b.legal_moves))
        assert "repeats!" not in table and "draw:" not in table


class TestImagineWarning:
    def test_imagine_warns_on_immediate_threefold(self):
        b = shuffled_board()
        b.push_san("Ng1")
        out = render_imagine(b, b.parse_san("Ng8"))
        assert "Draw warning" in out and "threefold" in out

    def test_imagine_warns_on_second_occurrence(self):
        b = chess.Board()
        for san in ["Nf3", "Nf6", "Ng1"]:
            b.push_san(san)
        out = render_imagine(b, b.parse_san("Ng8"))
        assert "Draw warning" in out and "one more repetition" in out

    def test_imagine_silent_on_progress_move(self):
        b = shuffled_board()
        out = render_imagine(b, b.parse_san("e4"))
        assert "Draw warning" not in out


class TestBoardWithHistory:
    def test_replays_from_initial_fen(self):
        start = "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"
        data = {"fen": None, "initial_fen": start, "uci_moves": ["a1a2", "g8f8"]}
        b0 = chess.Board(start)
        b0.push_uci("a1a2"); b0.push_uci("g8f8")
        data["fen"] = b0.fen()
        b = board_with_history(data)
        assert len(b.move_stack) == 2

    def test_bad_history_falls_back_to_fen(self):
        data = {"fen": "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1",
                "uci_moves": ["e2e4"]}  # illegal from this position
        b = board_with_history(data)
        assert b.fen() == data["fen"]
        assert not b.move_stack


class TestHypotheticalPrimitives:
    """The fen= / pass primitives let the agent compose its own threat
    detection (imagine candidate -> pass on the resulting FEN -> read own
    follow-ups). Mechanics only: the tool lists moves, the agent concludes."""

    def test_pass_lists_other_sides_moves_with_mate_flags(self):
        from imagine_move import render_pass
        b = chess.Board("6k1/5ppp/8/8/8/8/8/R5K1 b - - 0 1")
        out = render_pass(b)
        assert "white" in out and "checkmate" in out  # Ra8# would be the threat

    def test_pass_refused_in_check(self):
        from imagine_move import render_pass
        b = chess.Board("4k3/8/8/8/8/8/8/4R1K1 b - - 0 1")  # black in check from Re1
        out = render_pass(b)
        assert "Cannot imagine a pass" in out

    def test_render_position_works_on_arbitrary_fen(self):
        from show_position import render_position
        out = render_position(chess.Board("7k/8/5N2/8/8/8/8/R6K w - - 0 1"))
        assert "Pattern trigger" in out  # radar runs on hypothetical boards too
