# Defensive puzzle set (`puzzles_defensive.json`)

A benchmark for **item P — king safety / not getting mated** (see the future-work
kanban). Unlike the offensive set (sourced from Lichess), these are **mined from the
agent's own lost games**, because Lichess has no theme for "the opponent threatens
mate against you — defend/escape" (every Lichess theme is framed from the solver's
*offensive* seat; see the `lichess2026api` KB page).

## What each puzzle is

A position the agent (White) actually reached in a game it went on to **lose by
checkmate**, taken **one move before it blundered** — where the Stockfish eval fell
from non-losing to clearly lost. The task is defensive: **find a move that holds the
position** (don't get mated / don't collapse). There is no single forced answer.

Schema (superset of `puzzles.json`):
- `fen`, `moves` — `moves[0]` is the opponent's setup move (Lichess convention: `fen`
  is the position *before* it); `moves[1]` is one model holding move (Stockfish's best).
- **`acceptable_uci`** — ALL Stockfish-verified holding moves. The grader passes the
  agent if it plays **any** of these (`accepted_as="holds"`), not just `moves[1]`.
- `blunder_played`, `blunder_cp`, `best_cp`, `n_holding/n_legal`, `source_game` —
  provenance + difficulty signal.

## Fairness

This does **not** break the tool-fairness rule. Stockfish is used only to *grade* and
to *select fair positions* (a holding move must exist, the agent's actual move must
have lost, and not every move can hold — so it's a real test). The agent is never
handed the move; it must find a hold on its own, exactly as for the offensive set.

## Regenerating (idempotent, deterministic)

```bash
# from experiments/chess/ — needs Stockfish on PATH (or $STOCKFISH)
.venv/bin/python experiments/puzzle-benchmark/build_defensive_puzzles.py
```

Stockfish runs single-threaded at fixed depth, so the set regenerates **identically**.
The pipeline (mine → Stockfish-verify → export) lives in that one script.

## Running the benchmark

Registered as the named set `defensive` (its own progress file
`results/progress_defensive.json`):

```bash
curl -XPOST localhost:8000/api/puzzles/run -H 'content-type: application/json' \
  -d '{"set":"defensive","mode":"all"}'
```

The metric: does the agent pick a holding move (break free) rather than repeat the
blunder? Pair with the **king-danger / walk-into-mate radar** (item P proper) once
built, and iterate like the offensive puzzles.
