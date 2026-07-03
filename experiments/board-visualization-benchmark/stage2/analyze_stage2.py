"""Stage 2 analysis — accuracy per format + Wilson CIs + paired McNemar.

Re-runnable: reads results/stage2_trials.jsonl, writes results/stage2_summary.json
and prints a report. No model calls.

Stats stance (per the design ADR — deliberately lightweight):
  - Wilson 95% CIs on each format's accuracy (correct for proportions near 0/1).
  - One paired McNemar test on the DECIDING head-to-head: the best-scoring drawn
    format vs the FEN control. Paired because the SAME probes are asked of both.
  - No power analysis / no multiple-comparison machinery — this is an
    instrumental benchmark, not a confirmatory cognition trial.

Pairing unit for McNemar: (probe_id, rep) — the identical question put to two
formats. We compare correctness on each matched pair.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
TRIALS = RESULTS / "stage2_trials.jsonl"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Wilson score interval. Returns (point, lo, hi)."""
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (round(p, 4), round(max(0, centre - half), 4), round(min(1, centre + half), 4))


def mcnemar(b: int, c: int) -> dict:
    """Exact McNemar (binomial) on discordant pairs.
    b = pairs where format X correct, FEN wrong.
    c = pairs where FEN correct, format X wrong.
    Two-sided exact test on b vs (b+c) under p=0.5."""
    n = b + c
    if n == 0:
        return {"b": b, "c": c, "discordant": 0, "p_value": 1.0,
                "note": "no discordant pairs"}
    p = binomtest(b, n, 0.5, alternative="two-sided").pvalue
    return {"b": b, "c": c, "discordant": n, "p_value": round(p, 5)}


def load_trials():
    meta, rows = None, []
    for line in TRIALS.read_text().splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        if "_meta" in o:
            meta = o["_meta"]
        else:
            rows.append(o)
    return meta, rows


def main():
    meta, rows = load_trials()
    rows = [r for r in rows if r["ok"]]
    formats = meta["formats"]

    # overall accuracy per format
    per_fmt = defaultdict(lambda: [0, 0])  # fmt -> [correct, total]
    per_fmt_phase = defaultdict(lambda: [0, 0])
    per_fmt_kind = defaultdict(lambda: [0, 0])
    # correctness lookup for pairing: (fmt, probe_id, rep) -> bool
    correct_at = {}
    for r in rows:
        per_fmt[r["format"]][0] += int(r["correct"])
        per_fmt[r["format"]][1] += 1
        per_fmt_phase[(r["format"], r["phase"])][0] += int(r["correct"])
        per_fmt_phase[(r["format"], r["phase"])][1] += 1
        per_fmt_kind[(r["format"], r["kind"])][0] += int(r["correct"])
        per_fmt_kind[(r["format"], r["kind"])][1] += 1
        correct_at[(r["format"], r["probe_id"], r["rep"])] = bool(r["correct"])

    overall = {}
    for fmt in formats:
        k, n = per_fmt[fmt]
        p, lo, hi = wilson(k, n)
        overall[fmt] = {"correct": k, "total": n, "acc": p, "ci95": [lo, hi]}

    # rank drawn formats; pick best NON-fen as challenger to the FEN control
    ranked = sorted(formats, key=lambda f: overall[f]["acc"], reverse=True)
    best = ranked[0]
    best_drawn = next((f for f in ranked if f != "fen"), None)

    # paired McNemar: best_drawn vs fen  (and best vs fen if best is fen)
    pairs_keys = [(r["probe_id"], r["rep"]) for r in rows if r["format"] == "fen"]
    pairs_keys = sorted(set(pairs_keys))
    def discordance(fmt_x: str, fmt_y: str):
        b = c = 0
        for pid, rep in pairs_keys:
            x = correct_at.get((fmt_x, pid, rep))
            y = correct_at.get((fmt_y, pid, rep))
            if x is None or y is None:
                continue
            if x and not y:
                b += 1
            elif y and not x:
                c += 1
        return b, c

    mcnemar_tests = {}
    if best_drawn:
        b, c = discordance(best_drawn, "fen")  # b: drawn-correct/fen-wrong
        mcnemar_tests[f"{best_drawn}_vs_fen"] = mcnemar(b, c)

    summary = {
        "meta": meta,
        "n_trials_ok": len(rows),
        "overall_accuracy": overall,
        "ranked": ranked,
        "best_format": best,
        "best_drawn_format": best_drawn,
        "by_phase": {
            f"{fmt}|{ph}": {"correct": v[0], "total": v[1],
                            "acc": round(v[0]/v[1], 4) if v[1] else None}
            for (fmt, ph), v in sorted(per_fmt_phase.items())
        },
        "by_kind": {
            f"{fmt}|{kind}": {"correct": v[0], "total": v[1],
                              "acc": round(v[0]/v[1], 4) if v[1] else None}
            for (fmt, kind), v in sorted(per_fmt_kind.items())
        },
        "mcnemar": mcnemar_tests,
    }
    (RESULTS / "stage2_summary.json").write_text(json.dumps(summary, indent=2))

    # report
    print("=" * 72)
    print("STAGE 2 SUMMARY — which representation does the model READ best?")
    print("=" * 72)
    print(f"\nOverall accuracy ({len(rows)} ok trials), Wilson 95% CI:")
    for fmt in ranked:
        d = overall[fmt]
        bar = "#" * round(d["acc"] * 40)
        print(f"  {fmt:13} {d['acc']:.3f}  [{d['ci95'][0]:.3f}, {d['ci95'][1]:.3f}]  "
              f"{d['correct']}/{d['total']}  {bar}")
    print(f"\nBest overall: {best}   |   Best drawn (non-FEN): {best_drawn}")

    print("\nBy game phase (accuracy):")
    phases = ["opening", "middlegame", "endgame"]
    print(f"  {'format':13} " + " ".join(f"{ph:>11}" for ph in phases))
    for fmt in ranked:
        cells = []
        for ph in phases:
            v = per_fmt_phase.get((fmt, ph))
            cells.append(f"{(v[0]/v[1]):>11.3f}" if v and v[1] else f"{'-':>11}")
        print(f"  {fmt:13} " + " ".join(cells))

    print("\nBy probe kind (accuracy):")
    kinds = sorted({k for (_, k) in per_fmt_kind})
    print(f"  {'format':13} " + " ".join(f"{k[:10]:>11}" for k in kinds))
    for fmt in ranked:
        cells = []
        for kind in kinds:
            v = per_fmt_kind.get((fmt, kind))
            cells.append(f"{(v[0]/v[1]):>11.3f}" if v and v[1] else f"{'-':>11}")
        print(f"  {fmt:13} " + " ".join(cells))

    print("\nPaired McNemar (deciding head-to-head):")
    for name, t in mcnemar_tests.items():
        verdict = ("SIGNIFICANT (p<0.05)" if t["p_value"] < 0.05 else "not significant")
        print(f"  {name}: b(drawn✓/fen✗)={t['b']} c(fen✓/drawn✗)={t['c']} "
              f"discordant={t['discordant']} p={t['p_value']}  -> {verdict}")
    print(f"\nWrote {RESULTS / 'stage2_summary.json'}")


if __name__ == "__main__":
    main()
