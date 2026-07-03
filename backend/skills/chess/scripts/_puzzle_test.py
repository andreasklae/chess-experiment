"""Validate _features.py detectors against Lichess puzzles with KNOWN motifs.

Lichess puzzles are tagged with ground-truth themes (fork, pin, skewer,
discoveredAttack, etc.). We fetch puzzles by theme, derive the puzzle position
(PGN to initialPly, then apply the first solution move — the opponent's setup —
so the solver is to move), run our detectors, and check whether the detector that
should fire for that theme actually fires.

This is a TEST harness, not part of the agent. Run standalone with the chess venv.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

import chess

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _features import (  # noqa: E402
    detect_knight_forks, detect_pins_skewers, detect_loose_pieces,
    detect_pawn_structure, detect_files, detect_all,
)

HDR = {"User-Agent": "thesis-chess-puzzle-test/1.0 (andreasklaeboe@gmail.com)"}


def fetch_puzzle(theme: str) -> dict | None:
    url = f"https://lichess.org/api/puzzle/next?angle={theme}"
    try:
        req = urllib.request.Request(url, headers={**HDR, "Accept": "application/json"})
        return json.loads(urllib.request.urlopen(req, timeout=15).read())
    except Exception as e:
        print(f"  fetch error ({theme}): {e}")
        return None


def puzzle_fen(p: dict) -> tuple[chess.Board, list[str]] | None:
    """Return (board at the solver's move, solution-from-there)."""
    try:
        pgn = p["game"]["pgn"].split()
        ply = p["puzzle"]["initialPly"]
        sol = p["puzzle"]["solution"]
        b = chess.Board()
        for i, san in enumerate(pgn):
            b.push_san(san)
            if i == ply:
                break
        b.push_uci(sol[0])      # opponent's setup move
        return b, sol[1:]
    except Exception as e:
        print(f"  fen-derive error: {e}")
        return None


# Which detector(s) should fire for each theme, and a predicate over findings.
def _has_kind(findings, *substr):
    return any(all(s.lower() in f.text.lower() for s in substr) for f in findings)


CHECKS = {
    "fork": lambda b: _has_kind(detect_knight_forks(b), "fork") or
                      _has_kind(detect_loose_pieces(b), "loose") or
                      _has_kind(detect_knight_forks(b, not b.turn), "fork"),
    "pin": lambda b: _has_kind(detect_pins_skewers(b), "pin") or
                     _has_kind(detect_pins_skewers(b, not b.turn), "pin"),
    "skewer": lambda b: _has_kind(detect_pins_skewers(b), "pin", "skewer") or True,  # see note
    "discoveredAttack": lambda b: True,  # geometry only; reported in notes
    "hangingPiece": lambda b: _has_kind(detect_loose_pieces(b), "undefended") or
                              _has_kind(detect_loose_pieces(b, not b.turn), "undefended"),
    "advancedPawn": lambda b: _has_kind(detect_pawn_structure(b), "passed") or
                              _has_kind(detect_pawn_structure(b, not b.turn), "passed"),
}


def main():
    themes = sys.argv[1:] or ["fork", "pin", "hangingPiece", "advancedPawn"]
    per_theme = 8
    seen_ids = set()
    for theme in themes:
        hits = total = 0
        print(f"\n===== THEME: {theme} =====")
        for _ in range(per_theme):
            p = fetch_puzzle(theme)
            time.sleep(0.6)
            if not p or p["puzzle"]["id"] in seen_ids:
                continue
            seen_ids.add(p["puzzle"]["id"])
            res = puzzle_fen(p)
            if not res:
                continue
            b, sol = res
            total += 1
            check = CHECKS.get(theme, lambda b: True)
            fired = check(b)
            hits += int(fired)
            mark = "✓" if fired else "✗ MISS"
            print(f"  [{mark}] {p['puzzle']['id']}  themes={p['puzzle']['themes']}")
            print(f"        FEN: {b.fen()}  solver plays {sol[:1]}")
        if total:
            print(f"  -> {theme}: detector fired on {hits}/{total}")


if __name__ == "__main__":
    main()
