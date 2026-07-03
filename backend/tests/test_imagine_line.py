import pathlib
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
        assert "This is the OPPONENT's" not in out  # the perspective banner, not the features header
        assert "## Opponent legal replies" in out
        assert "## Newly hanging own pieces" in out

    def test_none_agent_color_is_mover_relative(self, im):
        # imagine_move passes None — unchanged behavior regardless of side.
        board = chess.Board(FEN)
        out = im.render_imagine(board, board.parse_san("Rb8"))
        assert "This is the OPPONENT's" not in out  # the perspective banner, not the features header
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
        assert "This is the OPPONENT's" not in r.stdout  # perspective banner absent; ends on White's move

    def test_black_ending_line_shows_banner(self):
        r = _run(["--fen", FEN, "Rb8,Rf4"])
        assert r.returncode == 0, r.stderr
        assert "OPPONENT" in r.stdout
        assert "Your (white) replies after this line" in r.stdout

    def test_cap_at_eight_plies(self):
        # 9 plies exceeds the (raised) 8-ply horizon.
        r = _run(["--fen", FEN, "Rb8,Rf4,Ke5,Rf1,Kd4,Rf4,Ke5,Rf1,Kd4"])  # 9 plies
        assert r.returncode != 0
        assert "at most 8" in r.stdout

    def test_eight_plies_allowed(self):
        # exactly 8 plies (the raised horizon), a verified-legal sequence.
        r = _run(["--fen", FEN, "Bb4,Kb1,Re5,Rxe5+,Kd3,Ka2,Kc4,Re6"])
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


class TestBranchingFooter:
    """imagine_line must push the agent to test SEVERAL opponent replies, not
    assume one. The footer differs by who moved last in the line."""

    F = "r1bqkbnr/1ppp1ppp/p1n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4"

    def test_line_ending_on_own_move_prompts_branching(self):
        r = _run(["--fen", self.F, "Bxc6"])  # White move; opponent to reply
        assert r.returncode == 0, r.stderr
        assert "Branch over the opponent's replies" in r.stdout
        # names concrete testing replies (the recaptures)
        assert "dxc6" in r.stdout or "bxc6" in r.stdout

    def test_line_ending_on_opponent_move_names_alternatives(self):
        r = _run(["--fen", self.F, "Bxc6,bxc6"])  # opponent reply supplied
        assert r.returncode == 0, r.stderr
        assert "You assumed the opponent plays bxc6" in r.stdout
        assert "dxc6" in r.stdout  # an alternative reply

    def test_no_branching_footer_on_mate(self):
        r = _run(["--fen", "4k3/8/4K3/8/8/8/8/7R w - - 0 1", "Rh8"])  # Rh8#
        assert r.returncode == 0, r.stderr
        assert "Branch over" not in r.stdout and "You assumed" not in r.stdout


class TestLeafVerdict:
    """The end-of-line verdict: material count + mate status the agent reads off
    the final position it calculated (human-fair: count pieces, see the mate)."""

    def test_forced_mate_line_announces_checkmate(self):
        # A clean back-rank mate line (Ra8#): the leaf verdict must announce
        # checkmate-for-you so the agent commits the first move of the line.
        r = _run(["--fen", "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1", "Ra8"])
        assert r.returncode == 0
        assert "CHECKMATE" in r.stdout and "mate the opponent" in r.stdout

    def test_material_count_reported_at_leaf(self):
        # A simple winning capture line: White wins a free rook. The verdict must
        # state the end-of-line material for the agent.
        r = _run(["--fen", "6k1/8/8/8/8/8/r7/R3K3 w - - 0 1", "Rxa2"])
        assert r.returncode == 0
        assert "End-of-line material" in r.stdout


def test_agent_side_cct_nudge_when_agent_to_move_at_leaf():
    """When a line ends with it being the AGENT's move, imagine_line nudges it to
    keep checking forcing moves (CCT) and lists its checks/captures — so it
    carries a combination through. 3MIRf: after Qxh7+ Kxh7 it's White to move and
    Rh4+ is the next move of the forced mate."""
    fen = "6rk/4nbpp/p2b1p2/1p2pP2/3pP1RQ/q6P/5P2/3BK1R1 w - - 0 33"
    r = _run(["--fen", fen, "Qxh7+,Kxh7"])
    assert r.returncode == 0, r.stderr
    assert "It is YOUR move here" in r.stdout
    assert "forcing continuations" in r.stdout
    assert "Rh4+" in r.stdout   # the mating continuation must be among them


def test_leaf_verdict_mating_attack_overrides_material_when_king_boxed():
    """Down material at the leaf, but the enemy king has <=1 escape square -> the
    verdict must say 'MATING ATTACK, keep extending' instead of 'backtrack'. This
    is the fix for the agent bailing out of a forced-mate sacrifice mid-line
    (8QAW1: Qd8+ Rxd8 [boxed] Rxd8#)."""
    import importlib.util, sys as _sys
    from pathlib import Path as _P
    spec = importlib.util.spec_from_file_location("imagine_line", LINE)
    il = importlib.util.module_from_spec(spec); _sys.modules["imagine_line"] = il
    spec.loader.exec_module(il)
    b = chess.Board("k5r1/ppp3r1/6q1/3Q4/4p3/6p1/PP5P/2RR2K1 w - - 0 33")
    start = b.copy()
    leaf = b.copy(); leaf.push_san("Qd8+"); leaf.push_san("Rxd8")
    v = il._leaf_verdict(start, leaf, chess.WHITE)
    assert "MATING ATTACK" in v and "KEEP EXTENDING" in v
    # it tells the agent material is not the yardstick while the king is boxed
    assert "material is NOT the yardstick" in v


def test_leaf_verdict_mating_attack_fires_even_when_up_material():
    # jJAE7: Qxf7+ Kh8 -> king fully boxed (0 escapes) and White is UP material.
    # The mating-attack signal must STILL fire (a forced mate beats settling for
    # the material lead) -- the agent was stopping at 'WINS material' and missing
    # Qf8+ Rxf8 Rxf8#.
    import importlib.util, sys as _sys
    spec = importlib.util.spec_from_file_location("imagine_line", LINE)
    il = importlib.util.module_from_spec(spec); _sys.modules["imagine_line"] = il
    spec.loader.exec_module(il)
    b = chess.Board("5rk1/pp3Qpp/8/8/8/8/PP4PP/4R1K1 w - - 0 1")  # constructed: Qxg7? use real
    import json, pathlib
    pj = pathlib.Path(__file__).resolve().parents[2] / "experiments/puzzle-benchmark/puzzles.json"
    if pj.exists():
        p = {x["id"]: x for x in json.loads(pj.read_text())}.get("jJAE7")
        if p:
            b = chess.Board(p["fen"]); b.push(chess.Move.from_uci(p["moves"][0]))
            start = b.copy()
            leaf = b.copy(); leaf.push(chess.Move.from_uci(p["moves"][1])); leaf.push(chess.Move.from_uci(p["moves"][2]))
            v = il._leaf_verdict(start, leaf, chess.WHITE)
            assert "MATING ATTACK" in v


def test_leaf_verdict_no_mating_attack_when_king_has_room():
    import importlib.util, sys as _sys
    spec = importlib.util.spec_from_file_location("imagine_line", LINE)
    il = importlib.util.module_from_spec(spec); _sys.modules["imagine_line"] = il
    spec.loader.exec_module(il)
    # down material, enemy king has many squares -> ordinary 'backtrack' verdict
    b = chess.Board("4k3/8/8/8/8/8/r7/4K3 w - - 0 1")  # white down a rook, black king free
    v = il._leaf_verdict(b, b, chess.WHITE)
    assert "MATING ATTACK" not in v


def test_quiet_move_nudge_lists_all_boxing_checks():
    """idFVb: three checks (Qg8+/Qe8+/Qc8+) all box the king to 0 escapes but only
    Qe8+ mates. When the agent imagines a QUIET move, imagine_move must list ALL
    boxing checks (not just one), or it sends the agent to calculate the wrong one
    and wrongly conclude 'no mate'."""
    import importlib.util, sys as _sys
    here = pathlib.Path(__file__).resolve()
    mvp = here.parents[1] / "skills/chess/scripts/imagine_move.py"
    spec = importlib.util.spec_from_file_location("imagine_move", mvp)
    im = importlib.util.module_from_spec(spec); _sys.modules["imagine_move"] = im
    spec.loader.exec_module(im)
    b = chess.Board("1k5r/ppp5/4Qpn1/3p1n2/PP1P2q1/2P2N2/6BP/4R1K1 w - - 12 29")
    res = im._uncalculated_mating_checks(b)
    assert res is not None
    sans, esc = res
    assert esc == 0
    assert {"Qg8+", "Qe8+", "Qc8+"}.issubset(set(sans))
    # quiet position with no boxing check returns None
    assert im._uncalculated_mating_checks(chess.Board()) is None


class TestLineProofAudit:
    """The leaf verdict must not certify a line the tool can mechanically see is
    unproven. Two audits (2026-07-02, from 40 replayed blunder-overrides): the
    FORCEDNESS of each opponent reply (32/40 lines contained replies the agent
    chose for the opponent) and leaf QUIESCENCE (18/40 counted material while
    the capturing piece was still en prise). Game 35e18d89 move 45 (Qxh7+,
    eval +250 -> -498) is the canonical case: imagine_line said '+2 WINS
    material' over Qxh7+ Kxh7 Ng5+ Kg8 Nxf7, where Kg8 was hand-picked (Kg7/Kg6
    refute) and the leaf knight on f7 hung."""

    QXH7_FEN = "2r2rk1/4nq1p/2p5/p2p4/P7/1P1Q1N1P/5PP1/1R2R1K1 w - - 2 23"

    def test_chosen_opponent_reply_makes_gain_unproven(self):
        r = _run(["--fen", self.QXH7_FEN, "Qxh7+,Kxh7,Ng5+,Kg8,Nxf7"])
        assert r.returncode == 0, r.stderr
        assert "UNPROVEN" in r.stdout
        assert "PICKED the opponent's replies" in r.stdout
        # names the step-4 alternatives that actually refute the sacrifice
        assert "Kg7" in r.stdout or "Kg6" in r.stdout
        # the old unconditional endorsement must be gone
        assert "trust the END count, not the scary middle" not in r.stdout

    def test_non_quiescent_leaf_flags_unsettled_count(self):
        r = _run(["--fen", self.QXH7_FEN, "Qxh7+,Kxh7,Ng5+,Kg8,Nxf7"])
        assert r.returncode == 0, r.stderr
        assert "COUNT NOT SETTLED" in r.stdout
        # reports the settled count after the recapture, not the rosy one
        assert "~−1" in r.stdout

    def test_forced_quiet_gain_is_proven(self):
        # Free rook, no opponent replies in the line, quiet leaf -> PROVEN.
        r = _run(["--fen", "6k1/8/8/8/8/8/r7/R3K3 w - - 0 1", "Rxa2"])
        assert r.returncode == 0, r.stderr
        assert "PROVEN" in r.stdout
        assert "UNPROVEN" not in r.stdout
        assert "COUNT NOT SETTLED" not in r.stdout

    def test_forced_mate_stays_proven(self):
        r = _run(["--fen", "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1", "Ra8"])
        assert r.returncode == 0, r.stderr
        assert "The mate is PROVEN" in r.stdout

    def test_mate_via_chosen_replies_is_flagged(self):
        # Scholar's mate from the start position: mate ONLY because we chose
        # every black reply for them. Must not be called proven.
        r = _run(["--fen", chess.Board().fen(),
                  "e4,e5,Qh5,Nc6,Bc4,Nf6,Qxf7"])
        assert r.returncode == 0, r.stderr
        assert "CHECKMATE" in r.stdout
        assert "only if they cooperate" in r.stdout
        assert "The mate is PROVEN" not in r.stdout


class TestForcingRepliesEnumeration:
    """Branch footers list the COMPLETE forcing set (every check and capture,
    annotated with what it captures), not a top-3 — visualization service per
    the 2026-07-03 fairness ruling: enumeration + arithmetic on demand is fair;
    evaluate-and-rank is not. The agent picks which lines to run."""

    F = "r1bqkbnr/1ppp1ppp/p1n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4"

    def test_footer_lists_all_forcing_with_annotations(self):
        r = _run(["--fen", self.F, "Bxc6"])
        assert r.returncode == 0, r.stderr
        assert "ALL their forcing replies" in r.stdout
        assert "dxc6 (captures your bishop" in r.stdout
        assert "bxc6 (captures your bishop" in r.stdout

    def test_assumed_reply_footer_annotates_alternatives(self):
        r = _run(["--fen", self.F, "Bxc6,bxc6"])
        assert r.returncode == 0, r.stderr
        assert "You assumed the opponent plays bxc6" in r.stdout
        assert "dxc6 (captures your bishop" in r.stdout
