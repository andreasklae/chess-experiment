# Thesis analysis pipeline

Reproducible datasets + figures for the thesis results chapter. Narrative and
provenance: `knowledge-base/work/experiment-chess-results-and-phases.md`.

## Files

- `build_dataset.py` — builds `data/games.csv` (one row per logged agent game:
  phase, opponent, result, Elo, review metrics, tool/log metrics) and
  `data/wiki_growth.csv`. **Incremental**: per-game reviews are cached in
  `backend/games/reviews/<id>.json` and skipped when present.
- `analysis.ipynb` — renders the thesis figures into `figures/`.
- Review engine: `backend/app/review/` (Lichess-published formulas, Stockfish
  depth 12 single-threaded ⇒ deterministic; see its README).

## Adding new games (e.g. after a batch finishes)

```bash
# from experiments/chess/
.venv/bin/python analysis/build_dataset.py        # reviews only the NEW games
# then re-run the notebook
```

Phase mapping (P1 minimal-tools → P4 autonomous-loop) and PR anchors live in
the `build_dataset.py` header — update `PR_MERGES` if a new PR merges.
