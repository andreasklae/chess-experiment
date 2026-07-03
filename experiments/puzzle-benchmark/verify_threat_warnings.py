#!/usr/bin/env python3
"""Verify the SYMMETRIC tools fire the correct WARNING on flipped (defensive)
positions. The metric is detector coverage, NOT solving: in each flipped
position White is to move and Black threatens a known motif; does the
show_position assessment (and radar) warn about that motif?
"""
import sys, json
from pathlib import Path
CHESS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CHESS / "backend/skills/chess/scripts"))
import chess
import _features, _radar

# threat motif -> substrings that count as the matching OPPONENT warning
MATCH = {
    "fork":            ["FORK"],
    "pin":             ["PIN"],
    "skewer":          ["SKEWER"],
    "discovered-attack": ["DISCOVER", "screen"],
    "hanging-piece":   ["UNDEFENDED", "loose", "hanging"],
    "promotion":       ["promote", "promotion"],
    "advanced-pawn":   ["passed pawn", "promote", "advanced"],
    "exposed-king":    ["exposed", "back rank", "king"],
}


def opp_warning_texts(board: chess.Board):
    """All warning text the agent sees about a looming threat: detector
    OPPONENT-findings (side=False) PLUS the agent's own-side 'lose' warnings
    (a hanging White piece is a side=True 'lose' finding — the correct symmetric
    warning that the opponent can win it) PLUS the radar (opponent-aware)."""
    texts = [f.text for f in _features.detect_all(board)
             if (not f.side) or f.kind == "lose"]
    r = _radar.render_radar(board)
    if r:
        texts.append(r)
    return texts


def main():
    flip = json.loads((CHESS / "experiments/puzzle-benchmark/puzzles-flipped.json").read_text())
    from collections import defaultdict, Counter
    per_topic = defaultdict(lambda: {"fired": 0, "missed": 0})
    misses = defaultdict(list)
    for p in flip:
        motif = p["threat_motif"]
        keys = MATCH.get(motif, [])
        texts = opp_warning_texts(chess.Board(p["fen"]))
        blob = " ".join(texts).lower()
        fired = any(k.lower() in blob for k in keys)
        bucket = per_topic[p["topic"]]
        if fired:
            bucket["fired"] += 1
        else:
            bucket["missed"] += 1
            misses[p["topic"]].append(p["id"])
    print(f"{'topic':22} {'fired':>6} {'missed':>7}  coverage")
    tot_f = tot_m = 0
    for t in sorted(per_topic):
        b = per_topic[t]; n = b["fired"] + b["missed"]
        tot_f += b["fired"]; tot_m += b["missed"]
        print(f"{t:22} {b['fired']:>6} {b['missed']:>7}  {100*b['fired']//n}%")
    print(f"\nTOTAL fired={tot_f} missed={tot_m}  ({100*tot_f//(tot_f+tot_m)}% coverage)")
    print("\nsample misses:")
    for t, ids in misses.items():
        print(f"  {t}: {ids[:5]}")


if __name__ == "__main__":
    main()
