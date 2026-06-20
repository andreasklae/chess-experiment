"""Tests for chess__imagine_line — the incremental, branchable, 5-ply
look-ahead — and for render_imagine's opponent-move perspective framing.

imagine_line reuses imagine_move.render_imagine for the frontier (last) move,
passing agent_color so an opponent move is rendered with a clear orientation
banner and relabeled headers.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import chess
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "chess" / "scripts"
LINE = SCRIPTS / "imagine_line.py"


@pytest.fixture(scope="module")
def im():
    spec = importlib.util.spec_from_file_location("imagine_move", SCRIPTS / "imagine_move.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["imagine_move"] = module
    spec.loader.exec_module(module)
    return module


# A lone-ish-king position used across cases: White Ke4,Rb5,Bd6 vs Black Kc2,Rf5.
FEN = "8/8/3B4/1R3r2/4K3/8/2k5/8 w - - 0 1"


def _run(args: list[str]):
    return subprocess.run(
        [sys.executable, str(LINE), *args],
        capture_output=True, text=True, cwd=str(SCRIPTS),
    )


# ----- render_imagine perspective (unit) -----

class TestPerspective:
    def test_own_move_no_banner(self, im):
        board = chess.Board(FEN)  # white to move
        out = im.render_imagine(board, board.parse_san("Rb8"), agent_color=chess.WHITE)
        assert "OPPONENT" not in out
        assert "## Opponent legal replies" in out
        assert "## Newly hanging own pieces" in out

    def test_none_agent_color_is_mover_relative(self, im):
        # imagine_move passes None — unchanged behavior regardless of side.
        board = chess.Board(FEN)
        out = im.render_imagine(board, board.parse_san("Rb8"))
        assert "OPPONENT" not in out
        assert "## Opponent legal replies" in out

    def test_opponent_move_gets_banner_and_relabels(self, im):
        # After 1.Rb8 it is Black to move; render Black's reply for a White agent.
        board = chess.Board(FEN)
        board.push_san("Rb8")
        out = im.render_imagine(board, board.parse_san("Rf4"), agent_color=chess.WHITE)
        assert "OPPONENT" in out and "black" in out.lower()
        assert "Your (white) replies after this line" in out
        assert "Black's newly hanging pieces (opponent's)" in out
        assert "## Opponent legal replies" not in out


# ----- imagine_line end-to-end (subprocess) -----

class TestImagineLine:
    def test_white_ending_line_has_frontier_report_no_banner(self):
        r = _run(["--fen", FEN, "Rb8,Rf4,Ke5"])
        assert r.returncode == 0, r.stderr
        assert "Line: 1.W Rb8" in r.stdout
        assert "## Move:" in r.stdout            # frontier report present
        assert "OPPONENT" not in r.stdout        # ends on White's move

    def test_black_ending_line_shows_banner(self):
        r = _run(["--fen", FEN, "Rb8,Rf4"])
        assert r.returncode == 0, r.stderr
        assert "OPPONENT" in r.stdout
        assert "Your (white) replies after this line" in r.stdout

    def test_cap_at_five_plies(self):
        r = _run(["--fen", FEN, "Rb8,Rf4,Ke5,Rf1,Kd4,Rf4"])  # 6 plies
        assert r.returncode != 0
        assert "at most 5 ahead" in r.stdout

    def test_five_plies_allowed(self):
        r = _run(["--fen", FEN, "Rb8,Rf4,Ke5,Rf1,Kd4"])  # exactly 5
        assert r.returncode == 0, r.stderr
        assert "## Move:" in r.stdout

    def test_illegal_move_reports_pre_move_fen(self):
        r = _run(["--fen", FEN, "Rb8,Qh1"])  # no queen — illegal
        assert r.returncode != 0
        assert "illegal" in r.stdout.lower()
        assert "Position reached before it" in r.stdout

    def test_missing_moves_errors(self):
        r = _run(["--fen", FEN, ""])
        assert r.returncode != 0
        assert "ONE move at a time" in r.stdout


class TestImagineLineNudge:
    """imagine_move (agent_color=None) nudges the agent to calculate the LINE
    on sharp/forcing/material-changing moves; it stays silent on quiet moves and
    when imagine_line itself is rendering the frontier (agent_color set)."""

    NUDGE = "Calculate before committing"

    def _out(self, im, fen, san, agent=None):
        b = chess.Board(fen)
        return im.render_imagine(b, b.parse_san(san), agent_color=agent)

    def test_trade_nudges(self, im):
        # Bxc6: capture that is recaptured (bxc6/dxc6) — a trade.
        fen = "r1bqkbnr/1ppp1ppp/p1n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4"
        assert self.NUDGE in self._out(im, fen, "Bxc6")

    def test_check_nudges(self, im):
        out = self._out(im, "4k3/8/8/8/8/8/8/R5K1 w - - 0 1", "Ra8+")
        assert self.NUDGE in out and "CHECK" in out

    def test_quiet_move_no_nudge(self, im):
        out = self._out(im, "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", "Nf3")
        assert self.NUDGE not in out

    def test_no_nudge_inside_imagine_line(self, im):
        # agent_color set => rendered by imagine_line; must not nudge (no recursion).
        fen = "r1bqkbnr/1ppp1ppp/p1n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4"
        assert self.NUDGE not in self._out(im, fen, "Bxc6", agent=chess.WHITE)
