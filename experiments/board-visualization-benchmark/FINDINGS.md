# Findings — Board-Visualization Benchmark

**Run date:** 2026-06-23 (Stage 1+2), 2026-06-24 (combination) ·
**Model:** google/gemma-4-31B-it (eX3 vLLM) ·
**Data:** `results/stage1_calls.jsonl` (104), `results/stage2_trials.jsonl`
(1500), `results/stage2_combo_trials.jsonl` (375). All ok.

## Verdict

**No single representation dominates. The best representation is task-dependent.**
FEN is the best *overall* and is significantly better for relational yes/no
judgments (is-this-attacked, is-this-hanging); a drawn **grid is decisively
better for spatial counting** (how many pieces attack a square). They trade off,
which is why the overall accuracies tie. The naive null ("FEN is sufficient,
everything else is noise") is **rejected at the per-task level** even though it
holds on the aggregate.

This is the thesis-level point in one line: **representation choice is a real,
measurable lever on model comprehension — and the right choice depends on the
question being asked, not on which format looks best to a human.**

## Stage 1 — what the model is fluent in (discovery)

| Condition | Result |
|---|---|
| **A** unconstrained ("generate a chess position", n=40) | Leads with a **letter grid 58%**, **piece-list 25%**, unicode 10%, boxed 8%. **FEN present in 83%** of responses (alongside a visual). |
| **B** anchored ("generate this position: `<FEN>`", n=64) | Produces a **boxed grid 95%**; **FEN-echo fidelity = 64/64 (1.00)** across all phases. |

Two takeaways: (1) the model's native attractors are a drawn grid + a coordinate
piece-list, with FEN almost always included — validating the Stage-2 candidate
set (`fen`, `ascii_grid`, `unicode_grid`, `piece_list`); (2) **the model
transcribes FEN flawlessly** — so any FEN *comprehension* failure in Stage 2 is a
reading/reasoning gap, not a parsing gap. Transcription ≠ comprehension.

## Stage 2 — comprehension accuracy (the verdict)

Overall accuracy (1500 trials, Wilson 95% CI):

| Format | Accuracy | 95% CI | n |
|---|---|---|---|
| **fen** | **0.800** | [0.757, 0.837] | 300/375 |
| ascii_grid | 0.776 | [0.731, 0.815] | 291/375 |
| piece_list | 0.776 | [0.731, 0.815] | 291/375 |
| unicode_grid | 0.768 | [0.723, 0.808] | 288/375 |

CIs overlap heavily. Deciding head-to-head (best drawn = ascii_grid vs fen):
**McNemar p = 0.29, not significant.** On the aggregate, no drawn format beats
FEN — and FEN is numerically top.

### The interaction the average hides (the real finding)

Per-probe-kind McNemar, **ascii_grid vs fen** (b = grid-correct/fen-wrong,
c = fen-correct/grid-wrong):

| Probe kind | b | c | p | winner |
|---|---|---|---|---|
| **count_attackers** | 15 | 0 | **0.0001** | **grid** (every discordant pair) |
| **attacked** | 0 | 9 | **0.004** | **fen** (every discordant pair) |
| **hanging** | 3 | 12 | **0.035** | **fen** |
| defended | 6 | 9 | 0.61 | — |
| occupancy | 0 | 3 | 0.25 | — |
| in_check | 0 | 0 | 1.00 | tie (both ~0.94) |

`count_attackers` accuracy by format: **ascii_grid 0.70, unicode_grid 0.60,
piece_list 0.30, fen 0.20.** Counting attackers requires scanning multiple lines
converging on a square — a 2-D grid affords it; a linear FEN/piece-list does not.
Conversely, FEN wins the relational yes/no probes (`attacked`, `hanging`): the
grid **over-reports** threats in dense opening positions (clean `yes` when the
answer is `no` — verified in raw trials, not a parsing artifact). The gains and
losses cancel, producing the aggregate tie.

## The combination test — does showing FEN + grid together capture both strengths? (2026-06-24)

The natural next question: each format has a different strength, so give the
model **both** (FEN + ASCII grid, shown neutrally, **no hint** about which to use
for what — a pure perception test, the routing layer is held out). 375 trials,
same positions/probes as the baseline (paired).

**Answer: no. The combination does not capture both strengths — it ≈ FEN, at
3.3× the cost.**

| Format | Overall acc | count_attackers | attacked | hanging | mean tokens/board | acc / 1k board-tokens |
|---|---|---|---|---|---|---|
| fen | 0.800 | **0.20** | **0.80** | 0.875 | 41.8 | **19.1** |
| ascii_grid | 0.776 | **0.70** | 0.68 | 0.688 | 97.0 | 8.0 |
| **fen_plus_grid** | 0.808 | **0.30** | 0.80 | 0.938 | 139.8 | **5.8** |

- **No accuracy gain over FEN.** Combo 0.808 vs FEN 0.800, McNemar **p=0.66**
  (not significant). It keeps FEN's relational strength but does **not** gain the
  grid's counting strength: on `count_attackers` the combo scores **0.30**,
  barely above FEN's 0.20 and far below the grid's 0.70.
- **The model anchors on the FEN and ignores the grid for counting.** On counting
  trials the combo gave the **same answer as FEN-alone on 27/30** (the same wrong
  answers — both say "2" when the truth is "1"). Combo-vs-grid on counting:
  b=0, c=12, **p=0.0005** — the grid beats the combo on every discordant counting
  pair, even though the grid is *right there in the prompt*.
- **Worst value of all three.** Accuracy-per-1k-board-tokens: FEN 19.1, grid 8.0,
  **combo 5.8.** The combination pays 3.3× the FEN token cost for a
  statistically-zero accuracy gain.

**Why this matters (it is itself a finding):** complementary encodings only help
if the model *switches to the right one per task*. This model doesn't — handed
both, it defaults to the FEN and leaves the grid's counting advantage unused.
This is the representation-layer echo of the perception–action gap: surfacing the
better view is not enough; the model has to *act on* it, and unprompted it does
not. "Just give it everything" is the wrong instinct — more representation is
more tokens and a view the model won't consult without being told to.

## What this means for the chess tools (recommendation)

- **Do not replace FEN with a grid wholesale** — FEN is at least as good
  overall and better for the threat-relation judgments the blunder gate cares
  about (`attacked`, `hanging`).
- **Standardize for consistency, not for a single winner.** The tools currently
  mix a letter-grid (`show_position`) and prose (`imagine_move`/`_radar`); the
  model already receives FEN every turn. The benchmark says: **keep FEN as the
  spine** (the model reads it as well as anything and transcribes it perfectly),
  and **add a grid only where a spatial/counting judgment is being surfaced**
  (e.g. attacker-count lines in the radar) — the one place a grid measurably
  helps. Don't pay context for a unicode grid: it never wins and costs more
  tokens than letters.
- **Do not just show both ("FEN + grid").** The combination test settled this:
  it does not improve accuracy over FEN (p=0.66) and costs 3.3× the tokens,
  because the model ignores the grid for counting when the FEN is present. If the
  grid is added, it must be added **at the specific decision point that needs it**
  (so the model is effectively routed to it), not stacked onto every board dump.
- **The deeper lever is unchanged:** the tools should keep surfacing the
  *computed relation as an explicit fact* (this piece is attacked by N; this
  piece is hanging) rather than expecting the model to derive it from any board
  rendering — consistent with the perception–action-gap finding that inline
  facts beat representations the model must parse.

## Limitations

- One model (Gemma 4 31B-it). Cross-tier replication (Haiku/Sonnet) is the
  obvious extension; the design supports it (`model.py` takes a `ModelSpec`).
- The combination was tested **FEN-first** (the natural deployment order, since
  FEN is the canonical state). A grid-first ordering might shift the anchoring;
  not tested — it would be a follow-up curiosity, not a change to the "don't
  combine" verdict (the cost argument stands regardless of order).
- 16 positions / 125 probes; enough for stable rates and the significant per-kind
  effects above, not for fine phase×kind×format cells.
- Probes are single-relation; multi-step reasoning over a representation is not
  tested here.
- Format preambles were matched in spirit but not length-controlled; the effects
  survive that (the count/relational crossover is structural, not phrasing).
