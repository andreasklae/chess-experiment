"""Combination analysis — does showing FEN + grid together beat either alone?

Loads the baseline trials (results/stage2_trials.jsonl: fen, ascii_grid, ...)
and the combo trials (results/stage2_combo_trials.jsonl: fen_plus_grid), which
share the SAME positions/probes/reps, and compares:

  - overall accuracy (Wilson CI) for fen, ascii_grid, fen_plus_grid
  - per-probe-kind accuracy — does the combo KEEP fen's relational strength
    (attacked/hanging) AND GAIN the grid's counting strength (count_attackers)?
  - paired McNemar: fen_plus_grid vs fen, and vs ascii_grid (same probes)
  - accuracy-per-token: the combo ~3.5x the board footprint, so it must win by
    enough to justify the context cost (token counts measured on the actual
    rendered boards via the model's tokenizer if available, else a char/4 proxy).

Pure offline analysis; no model calls. Re-runnable.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
RESULTS = ROOT / "results"

from positions import load_positions       # noqa: E402
from renderers import RENDERERS            # noqa: E402

COMPARE = ["fen", "ascii_grid", "fen_plus_grid"]


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / d
    h = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (round(p, 4), round(max(0, ctr - h), 4), round(min(1, ctr + h), 4))


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return {"b": b, "c": c, "discordant": 0, "p_value": 1.0}
    return {"b": b, "c": c, "discordant": n,
            "p_value": round(binomtest(b, n, 0.5, alternative="two-sided").pvalue, 5)}


def load(path):
    rows = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        if "_meta" not in o:
            rows.append(o)
    return rows


def token_counts():
    """Mean tokens per rendered board, per format. Uses the served tokenizer via
    transformers if the model id is available locally; otherwise a char/4 proxy
    (clearly labelled). The RELATIVE cost is what matters and char/4 preserves it."""
    positions = load_positions()
    method = "char_over_4_proxy"
    enc = None
    try:
        from transformers import AutoTokenizer
        enc = AutoTokenizer.from_pretrained("google/gemma-4-31B-it")
        method = "gemma_tokenizer"
    except Exception:
        enc = None
    counts = {}
    for fmt in COMPARE:
        vals = []
        for p in positions:
            s = RENDERERS[fmt](p.board)
            vals.append(len(enc.encode(s)) if enc else len(s) / 4)
        counts[fmt] = round(sum(vals) / len(vals), 1)
    return counts, method


def main():
    base = load(RESULTS / "stage2_trials.jsonl")
    combo = load(RESULTS / "stage2_combo_trials.jsonl")
    rows = [r for r in (base + combo) if r["ok"] and r["format"] in COMPARE]

    correct_at = {}
    per_fmt = defaultdict(lambda: [0, 0])
    per_fmt_kind = defaultdict(lambda: [0, 0])
    for r in rows:
        per_fmt[r["format"]][0] += int(r["correct"]); per_fmt[r["format"]][1] += 1
        key = (r["format"], r["kind"])
        per_fmt_kind[key][0] += int(r["correct"]); per_fmt_kind[key][1] += 1
        correct_at[(r["format"], r["probe_id"], r["rep"])] = bool(r["correct"])

    overall = {f: dict(zip(("acc", "lo", "hi"), wilson(*per_fmt[f]))) | {
        "correct": per_fmt[f][0], "total": per_fmt[f][1]} for f in COMPARE}

    # pairing keys present for all three formats
    keys = sorted(set((r["probe_id"], r["rep"]) for r in rows if r["format"] == "fen"))
    def discord(fx, fy):
        b = c = 0
        for pid, rep in keys:
            x = correct_at.get((fx, pid, rep)); y = correct_at.get((fy, pid, rep))
            if x is None or y is None:
                continue
            if x and not y: b += 1
            elif y and not x: c += 1
        return mcnemar(b, c)

    tests = {
        "combo_vs_fen": discord("fen_plus_grid", "fen"),
        "combo_vs_ascii": discord("fen_plus_grid", "ascii_grid"),
    }
    # per-kind combo vs fen and vs ascii
    kinds = sorted({k for (_, k) in per_fmt_kind})
    def discord_kind(fx, fy, kind):
        kk = sorted(set((r["probe_id"], r["rep"]) for r in rows
                        if r["format"] == "fen" and r["kind"] == kind))
        b = c = 0
        for pid, rep in kk:
            x = correct_at.get((fx, pid, rep)); y = correct_at.get((fy, pid, rep))
            if x and not y: b += 1
            elif y and not x: c += 1
        return mcnemar(b, c)
    per_kind_tests = {
        kind: {"vs_fen": discord_kind("fen_plus_grid", "fen", kind),
               "vs_ascii": discord_kind("fen_plus_grid", "ascii_grid", kind)}
        for kind in kinds
    }

    toks, tok_method = token_counts()
    acc_per_ktok = {f: round(overall[f]["acc"] / toks[f] * 1000, 4) for f in COMPARE}

    summary = {
        "compared": COMPARE,
        "overall_accuracy": overall,
        "by_kind": {f"{f}|{k}": {"correct": v[0], "total": v[1],
                                 "acc": round(v[0]/v[1], 4) if v[1] else None}
                    for (f, k), v in sorted(per_fmt_kind.items())},
        "mcnemar": tests,
        "mcnemar_by_kind": per_kind_tests,
        "mean_tokens_per_board": toks,
        "token_method": tok_method,
        "acc_per_1k_tokens": acc_per_ktok,
    }
    (RESULTS / "stage2_combo_summary.json").write_text(json.dumps(summary, indent=2))

    # report
    print("=" * 74)
    print("COMBINATION ANALYSIS — does FEN+grid beat either alone? (pure perception)")
    print("=" * 74)
    print("\nOverall accuracy (Wilson 95% CI):")
    for f in sorted(COMPARE, key=lambda x: -overall[x]["acc"]):
        d = overall[f]
        print(f"  {f:15} {d['acc']:.3f}  [{d['lo']:.3f}, {d['hi']:.3f}]  {d['correct']}/{d['total']}")

    print("\nPer-probe-kind accuracy (does combo capture BOTH strengths?):")
    print(f"  {'kind':16} {'fen':>8} {'ascii':>8} {'combo':>8}")
    for k in kinds:
        row = []
        for f in COMPARE:
            v = per_fmt_kind.get((f, k))
            row.append(f"{(v[0]/v[1]):>8.3f}" if v and v[1] else f"{'-':>8}")
        print(f"  {k:16} " + " ".join(row))

    print("\nPaired McNemar (b = combo✓/other✗,  c = other✓/combo✗):")
    for name, t in tests.items():
        verdict = "SIGNIFICANT" if t["p_value"] < 0.05 else "not significant"
        print(f"  {name:16} b={t['b']:3} c={t['c']:3} disc={t['discordant']:3} p={t['p_value']}  -> {verdict}")

    print("\nPer-kind McNemar, combo vs fen / combo vs ascii (where it matters):")
    for k in ("count_attackers", "attacked", "hanging"):
        tf, ta = per_kind_tests[k]["vs_fen"], per_kind_tests[k]["vs_ascii"]
        print(f"  {k:16} vs_fen: b={tf['b']} c={tf['c']} p={tf['p_value']}   "
              f"vs_ascii: b={ta['b']} c={ta['c']} p={ta['p_value']}")

    print(f"\nCost ({tok_method}):")
    print(f"  mean tokens/board: " + "  ".join(f"{f}={toks[f]}" for f in COMPARE))
    print(f"  accuracy per 1k board-tokens: " +
          "  ".join(f"{f}={acc_per_ktok[f]}" for f in COMPARE))
    print(f"\nWrote {RESULTS / 'stage2_combo_summary.json'}")


if __name__ == "__main__":
    main()
