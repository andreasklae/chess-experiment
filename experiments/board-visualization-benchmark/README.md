# Board-Visualization Benchmark

**Question:** which board representation does the chess agent's model read most
accurately? Equivalently: does drawing the board help at all over the FEN the
model already receives every turn — and if so, which rendering is best?

This is apparatus for `experiment-chess`. It does **not** touch the live skill
tools. A representation is adopted only after this benchmark produces a verdict.
Design rationale and the stats stance are in the KB ADR
[`2026-06-23-board-visualization-benchmark.md`](../../../../knowledge-base/decisions/2026-06-23-board-visualization-benchmark.md).

Motivation: the experiment's most robust finding is the perception–action gap —
the binding constraint is *comprehension of surfaced facts*, not perception
coverage. If one representation is read more accurately, standardizing on it is
a pure model-independent infrastructure win. If FEN-only ties, that is itself a
finding ("represent information for the model, not for humans").

## Two stages

**Stage 1 — discover candidates (the model nominates).** Two sterile prompt
conditions, no format hints:
- *A (unconstrained):* "Generate a chess position." → the model's native
  attractor (form only, no correctness).
- *B (anchored):* "Generate this position: `<FEN>`." → preferred form for a
  known position **and** fidelity (does its FEN echo match the target?).

**Stage 2 — score comprehension (the verdict).** Render each position in every
candidate format + controls, ask relational probes (is-defended / attacked /
in-check / hanging / occupancy / count-attackers), score against a python-chess
oracle. Paired design (same probes across formats), Wilson CIs, one McNemar test
on the deciding head-to-head (best drawn format vs FEN).

## Layout

```
board-visualization-benchmark/
├── README.md                  # this file
├── lib/
│   ├── positions.py           # 16 curated FENs, stratified opening/middlegame/endgame
│   ├── renderers.py           # the formats: fen, ascii_grid, unicode_grid, piece_list
│   ├── probes.py              # relational probe generator + python-chess oracle + scoring
│   └── model.py               # logged client over the eX3 vLLM endpoint (Gemma 4 31B-it)
├── stage1/
│   ├── run_stage1.py          # → results/stage1_calls.jsonl
│   └── analyze_stage1.py      # → results/stage1_summary.json
├── stage2/
│   ├── run_stage2.py          # → results/stage2_trials.jsonl
│   └── analyze_stage2.py      # → results/stage2_summary.json
├── results/                   # all raw + summarized data (full audit trail)
└── FINDINGS.md                # written after the runs — the verdict + evidence
```

## Reproduce

Requires the eX3 tunnel up (`google/gemma-4-31B-it` at `localhost:11500/v1`;
see `module-llm-server`). From this directory, using the chess venv:

```bash
PY=../../.venv/bin/python
$PY lib/positions.py            # validate corpus
$PY lib/probes.py               # probe counts + oracle self-check
$PY stage1/run_stage1.py        # ~104 model calls
$PY stage1/analyze_stage1.py
$PY stage2/run_stage2.py        # formats x probes x reps trials
$PY stage2/analyze_stage2.py
```

All model calls are logged to `results/*.jsonl` (prompt in, raw text out,
timestamps) so the runs are auditable and re-analyzable without re-querying.

## Success criterion

A confident statement of either: (a) the best representation, with effect size
and CI, or (b) the null — FEN is sufficient and added renderings don't measurably
help comprehension. Both are valid thesis outcomes.
