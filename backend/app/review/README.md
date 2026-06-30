# Game review engine (`app.review`)

A chess.com / Lichess-style **game review** built on local Stockfish plus this
experiment's own mechanical detector stack. Input is a game's moves; output is a rich
JSON analysis (one file per game, in a folder) designed to be **easy to mine and learn
from** — not just an eval, but *why* each mistake was a mistake and *where* a player is
weak.

## Why we built our own

A chess.com review is not proprietary magic — it is a known algorithm on top of an
engine we already run. Building it in-house gives full control, no third-party
dependency, and lets us attach the **mechanical "why"** from our fair detector stack
(situation/priority, threats, what a blunder allowed) — capability no external service
offers. (See the 2026-06-30 KB note on the ChessCompass investigation.)

## What a review contains

**Per move:** eval before/after (cp + **win%**), centipawn loss, **win% lost**, per-move
**accuracy%**, a **classification** (`brilliant` · `great` · `best` · `excellent` ·
`good` · `inaccuracy` · `mistake` · `blunder` · `forced`), the engine's **best move +
principal variation**, and the **situation** (priority, material, phase, threat against
the mover, mate-savers). For a mistake/blunder it adds `why_suboptimal`: the better
move + line, **what the move allowed the opponent**, and the salient features that were
already on the board.

**Per player / per game:** accuracy%, average CPL, label counts, the 5 worst moments,
and **weakness tags** — mistakes sliced by phase / in-check / under-threat / had-forcing
-move / priority, each with a mistake-rate.

**Across a batch:** `aggregate_weaknesses` rolls many reviews into one weakness report
(mistake-rate-ranked tags) — the direct answer to "run Maia games → where is the agent
weak?".

## Scoring (the formulas)

Move quality is judged by **win% thrown away**, not raw centipawns (losing 3 pawns when
+9 ≠ losing 3 pawns when equal). Published Lichess formulas (`classify.py`):

- `Win% = 50 + 50·(2/(1+exp(−0.00368208·cp)) − 1)`
- `Accuracy% = 103.1668·exp(−0.04354·(winBefore − winAfter)) − 3.1669`
- labels by win% drop: ≥5 inaccuracy, ≥10 mistake, ≥20 blunder; `best`/`great`
  (only-good-move) / `brilliant` (sound sacrifice that's still best) for the top move.

Stockfish runs **single-threaded at a fixed depth → reviews are deterministic**.

## Use

```python
from app.review import review_game, write_review
review = review_game(moves=["e2e4", "e7e5", ...])     # UCI or SAN, or pgn="..."
write_review(review)                                  # -> games/reviews/<game_id>.json
```

CLI (from `backend/`, chess venv; Stockfish via `CHESS_STOCKFISH_PATH` or config):

```bash
python -m app.review.cli --pgn game.pgn
python -m app.review.cli --game-json games/baseline/<id>.json     # our game logs
python -m app.review.cli --games-dir games/<folder> --player white  # batch + weakness report
python -m app.review.cli --moves e2e4 e7e5 g1f3 ...
```

## Layout

| file | role |
|---|---|
| `classify.py` | pure win%/accuracy/classification formulas (no engine) |
| `engine.py` | `ReviewEngine` — synchronous multi-PV Stockfish wrapper |
| `features.py` | bridge to the skill's detector stack for the mechanical "why" |
| `reviewer.py` | `review_game()` — orchestrates per-move + per-game analysis |
| `io.py` | write/load reviews, `aggregate_weaknesses`, `write_aggregate` |
| `cli.py` | command-line entry point |

Tests: `backend/tests/test_review.py` (formulas + reviewer with a stub engine; a real-
Stockfish integration test runs when a binary is present).
