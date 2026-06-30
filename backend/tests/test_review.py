"""Tests for the game-review engine (app.review).

The formulas (classify) are pure and tested directly. The reviewer is tested with a
STUB engine so the suite doesn't need a Stockfish binary; an integration test that uses
the real engine is skipped unless one is on PATH.
"""
import shutil
import sys
from pathlib import Path

import chess
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.review import classify as C
from app.review.engine import ScoredMove
from app.review import reviewer as R


# ── classify: the published formulas ────────────────────────────────────────────

def test_win_percent_is_50_at_zero_and_monotonic():
    assert abs(C.win_percent(0) - 50.0) < 1e-6
    assert C.win_percent(100) > C.win_percent(0) > C.win_percent(-100)
    assert C.win_percent(C.MATE_CP) > 99.0
    assert C.win_percent(-C.MATE_CP) < 1.0


def test_accuracy_is_100_when_no_win_lost_and_drops_with_loss():
    assert C.accuracy_percent(60.0, 60.0) >= 99.0      # kept all win%
    assert C.accuracy_percent(60.0, 40.0) < C.accuracy_percent(60.0, 55.0)
    assert 0.0 <= C.accuracy_percent(90.0, 10.0) <= 100.0


def test_cp_from_score_folds_mate():
    assert C.cp_from_score(None, 1) > 9000
    assert C.cp_from_score(None, -1) < -9000
    assert C.cp_from_score(250, None) == 250
    assert C.cp_from_score(99999, None) == C.MATE_CP   # clamped


def test_classify_labels_by_win_percent_lost():
    # not best, lost 25% win -> blunder; 12% -> mistake; 6% -> inaccuracy; 1% -> excellent
    assert C.classify(60, 35, 300, is_best=False).label == "blunder"
    assert C.classify(60, 48, 150, is_best=False).label == "mistake"
    assert C.classify(60, 54, 80, is_best=False).label == "inaccuracy"
    assert C.classify(60, 59, 10, is_best=False).label == "excellent"


def test_classify_best_move_variants():
    assert C.classify(60, 60, 0, is_best=True).label == "best"
    assert C.classify(60, 60, 0, is_best=True, only_good_move=True).label == "great"
    assert C.classify(60, 60, 0, is_best=True, is_sound_sacrifice=True).label == "brilliant"
    assert C.classify(60, 60, 0, is_best=False, forced=True).label == "forced"


# ── reviewer with a STUB engine (no Stockfish needed) ───────────────────────────

class _StubEngine:
    """Deterministic fake: 'best move' is the first legal move; everything evals 0.
    Enough to exercise the reviewer's wiring/JSON shape without a real engine."""
    available = True
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def open(self): return True
    def best_moves(self, board, *, depth=None, multipv=None):
        cands = []
        for mv in list(board.legal_moves)[: (multipv or 3)]:
            cands.append(ScoredMove(move=mv, san=board.san(mv), cp=0, mate=None,
                                    pv=[board.san(mv)]))
        return cands


def test_review_game_shape_with_stub(monkeypatch):
    monkeypatch.setattr(R, "ReviewEngine", lambda *a, **k: _StubEngine())
    r = R.review_game(moves=["e2e4", "e7e5", "g1f3"], depth=8)
    assert r["schema_version"] == 1
    assert len(r["moves"]) == 3
    m0 = r["moves"][0]
    for key in ("ply", "mover", "played", "classification", "win_before_pct",
                "win_after_pct", "accuracy_pct", "best_move", "situation"):
        assert key in m0
    assert m0["mover"] == "white" and r["moves"][1]["mover"] == "black"
    assert set(r["summary"]) == {"white", "black"}
    assert "weakness_tags" in r["summary"]["white"]


def test_review_accepts_pgn_with_stub(monkeypatch):
    monkeypatch.setattr(R, "ReviewEngine", lambda *a, **k: _StubEngine())
    pgn = '[Event "t"]\n[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 *\n'
    r = R.review_game(pgn=pgn, depth=8)
    assert len(r["moves"]) == 4
    assert r["headers"].get("Event") == "t"


# ── integration: real Stockfish (skipped if absent) ─────────────────────────────

def _sf():
    import os
    return os.environ.get("CHESS_STOCKFISH_PATH") or shutil.which("stockfish")


@pytest.mark.skipif(not _sf(), reason="Stockfish not on PATH")
def test_real_review_detects_scholars_mate_blunder():
    r = R.review_game(moves=["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6", "h5f7"],
                      stockfish_path=_sf(), depth=12)
    assert r["engine_available"]
    assert r["result"] == "1-0"
    nf6 = r["moves"][5]
    assert nf6["played"]["san"] == "Nf6" and nf6["classification"] == "blunder"
    assert nf6["why_suboptimal"]["better_move"] is not None
    # the mechanical why must flag the mate threat
    assert nf6["situation"]["threat_against_mover"]["kind"] == "mate"
    last = r["moves"][6]
    assert last["played"]["san"] == "Qxf7#" and last["is_best_move"]
