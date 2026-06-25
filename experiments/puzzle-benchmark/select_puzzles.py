"""Select a fixed, reproducible puzzle set for the agent benchmark.

Pulls puzzles from the local Lichess puzzle DB slice, binned per TOPIC by rating
band so we test each tactical/positional/endgame theme across the full difficulty
range. Mates are excluded — already covered by the prior mate-conversion sweep.

Output: puzzles.json  — a fixed list of puzzles (id, fen, moves, rating, themes,
topic, band). The agent run reads this so the test is reproducible.

Lichess puzzle CSV columns: PuzzleId, FEN, Moves, Rating, RatingDeviation,
Popularity, NbPlays, Themes, GameUrl, OpeningTags.
The FEN is the position BEFORE the first move; the FIRST move is the opponent's
setup; then solver/opponent alternate.
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

import chess


def _difficulty(rating: int) -> str:
    if rating < 1000:
        return "easy"
    if rating < 1400:
        return "medium"
    if rating < 1800:
        return "hard"
    return "expert"

CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/puz_xl.csv")
OUT = Path(__file__).resolve().parent / "puzzles.json"

# Topic -> the Lichess theme that defines it (the puzzle must carry this theme).
# Grouped so the report rolls up to a wiki page.
TOPICS = {
    # --- tactics ---
    "fork": "fork",
    "pin": "pin",
    "skewer": "skewer",
    "discovered-attack": "discoveredAttack",
    "discovered-check": "discoveredCheck",
    "deflection": "deflection",
    "attraction": "attraction",
    "interference": "interference",
    "clearance": "clearance",
    "capturing-defender": "capturingDefender",
    "intermezzo": "intermezzo",
    "hanging-piece": "hangingPiece",
    "sacrifice": "sacrifice",
    "quiet-move": "quietMove",
    # --- endgames / pawns ---
    "pawn-endgame": "pawnEndgame",
    "advanced-pawn": "advancedPawn",
    "promotion": "promotion",
    # --- king safety / defense ---
    "exposed-king": "exposedKing",
    "defensive-move": "defensiveMove",
}

# Rating bands: easy → very hard. ~4 per band per topic ≈ 16-20 per topic.
BANDS = [(0, 1000), (1000, 1400), (1400, 1800), (1800, 4000)]
PER_BAND = 4
# Keep puzzles short-to-medium so a failure is interpretable (not a 12-move slog),
# but include some longer ones. Solution length = number of plies in Moves.
MAX_PLIES = 12
MIN_POPULARITY = 80   # well-vetted puzzles only (popularity is the upvote score)


def main():
    random.seed(42)  # reproducible selection
    # bucket rows per (topic, band); reservoir-ish: collect candidates then sample
    buckets: dict[tuple[str, int], list[dict]] = {}
    wanted_themes = set(TOPICS.values())

    with CSV.open() as f:
        r = csv.DictReader(f)
        for row in r:
            if not row.get("Themes") or not row.get("Moves") or not row.get("FEN"):
                continue  # truncated/malformed row (partial decompress tail)
            themes = row["Themes"].split()
            if not (wanted_themes & set(themes)):
                continue
            try:
                rating = int(row["Rating"])
                pop = int(row["Popularity"])
                plies = len(row["Moves"].split())
            except Exception:
                continue
            if pop < MIN_POPULARITY or plies > MAX_PLIES or plies < 2:
                continue
            # The agent ALWAYS plays White, so the puzzle's solver side (the side
            # to move AFTER the opponent's setup move = moves[0]) must be White.
            # Drop black-to-move puzzles — the agent can't solve them.
            try:
                b = chess.Board(row["FEN"])
                b.push(chess.Move.from_uci(row["Moves"].split()[0]))
                if b.turn != chess.WHITE:
                    continue
            except Exception:
                continue
            band = next((i for i, (lo, hi) in enumerate(BANDS) if lo <= rating < hi), None)
            if band is None:
                continue
            for topic, theme in TOPICS.items():
                if theme in themes:
                    buckets.setdefault((topic, band), []).append(row)

    selected = []
    seen_ids = set()
    summary: dict[str, list[int]] = {}
    for topic in TOPICS:
        per_band_counts = []
        for band in range(len(BANDS)):
            cands = buckets.get((topic, band), [])
            random.shuffle(cands)
            picked = 0
            for row in cands:
                if row["PuzzleId"] in seen_ids:
                    continue
                seen_ids.add(row["PuzzleId"])
                rating = int(row["Rating"])
                selected.append({
                    "id": row["PuzzleId"],
                    "fen": row["FEN"],
                    "moves": row["Moves"].split(),
                    "rating": rating,
                    "difficulty": _difficulty(rating),
                    # Human-readable label (Lichess puzzles have no titles): the
                    # motif + difficulty, e.g. "Fork · easy (620)".
                    "title": f"{topic.replace('-', ' ').title()} · {_difficulty(rating)} ({rating})",
                    "popularity": int(row["Popularity"]),
                    "themes": row["Themes"].split(),
                    "topic": topic,
                    "band": f"{BANDS[band][0]}-{BANDS[band][1]}",
                    "lichess_url": f"https://lichess.org/training/{row['PuzzleId']}",
                })
                picked += 1
                if picked >= PER_BAND:
                    break
            per_band_counts.append(picked)
        summary[topic] = per_band_counts

    OUT.write_text(json.dumps(selected, indent=2))
    print(f"Selected {len(selected)} puzzles across {len(TOPICS)} topics -> {OUT}\n")
    print(f"{'topic':22} " + " ".join(f"{lo}-{hi}".rjust(9) for lo, hi in BANDS) + "   total")
    for topic, counts in summary.items():
        print(f"{topic:22} " + " ".join(str(c).rjust(9) for c in counts) + f"   {sum(counts)}")


if __name__ == "__main__":
    main()
