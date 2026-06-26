"""Select a fixed, reproducible puzzle set for the agent benchmark.

Modes:
  (default)     OFFENSIVE — the agent PLAYS the motif (fork/pin/skewer/…). This
                is the agent-SOLVING benchmark (puzzles.json).
  --defensive   DEPRECATED, do not use. It selects `defensiveMove` + motif, which
                was *assumed* to mean "defend against the opponent's fork" but
                does NOT: verified against the Lichess tagger source
                (ornicar/lichess-puzzler), every motif theme describes the
                SOLVER's own move, so `fork` always means "the solver forks". The
                resulting set is mostly counter-attacks, not defence. The genuine
                defensive work is a DETECTOR-verification harness over flipped
                positions instead — see `flip_puzzles.py` + `verify_threat_warnings.py`.
                This mode is kept only so the deprecation is self-documenting.

Pulls puzzles from the local Lichess puzzle DB slice, binned per TOPIC by rating
band so each theme is tested across the full difficulty range. The agent ALWAYS
plays White, so only puzzles whose solver side (the side to move AFTER the
opponent's setup move = moves[0]) is White are kept — black-to-move puzzles are
dropped.

Output: puzzles.json (offensive) or puzzles-defensive.json (--defensive) — a
fixed list (id, fen, moves, rating, themes, topic, band). The agent run reads
this so the test is reproducible.

Lichess puzzle CSV columns: PuzzleId, FEN, Moves, Rating, RatingDeviation,
Popularity, NbPlays, Themes, GameUrl, OpeningTags.
The FEN is the position BEFORE the first move; the FIRST move is the opponent's
setup; then solver/opponent alternate.
"""
from __future__ import annotations

import argparse
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


# --- OFFENSIVE topics: the puzzle must carry this single theme. -------------
OFFENSIVE_TOPICS = {
    # tactics
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
    # endgames / pawns
    "pawn-endgame": "pawnEndgame",
    "advanced-pawn": "advancedPawn",
    "promotion": "promotion",
    # king safety / defense
    "exposed-king": "exposedKing",
    "defensive-move": "defensiveMove",
}

# --- DEFENSIVE topics: the puzzle must carry `defensiveMove` AND the motif, so
# the solver's task is to PREVENT/ESCAPE the opponent's tactic. Limited to the
# high-value defenses (most material + most instructive); the rare ones
# (interference/capturingDefender, etc.) are intentionally skipped. ----------
DEFENSIVE_REQUIRED = "defensiveMove"
DEFENSIVE_TOPICS = {
    "defend-hanging": "hangingPiece",        # save your attacked/undefended piece
    "defend-fork": "fork",                   # avoid or escape a fork
    "defend-pin": "pin",                     # neutralise / break a pin
    "defend-promotion": "promotion",         # stop a pawn from promoting
    "defend-advanced-pawn": "advancedPawn",  # blockade / catch a runner
    "defend-exposed-king": "exposedKing",    # defend your exposed king
}


# Rating bands: easy → very hard. 4 per band per topic.
BANDS = [(0, 1000), (1000, 1400), (1400, 1800), (1800, 4000)]
PER_BAND = 4
# Keep puzzles short-to-medium so a failure is interpretable (not a 12-move slog),
# but include some longer ones. Solution length = number of plies in Moves.
MAX_PLIES = 12
MIN_POPULARITY = 80   # well-vetted puzzles only (popularity is the upvote score)


def _matches(topic_theme: str, themes: set[str], defensive: bool) -> bool:
    """Does this puzzle belong to a topic defined by `topic_theme`?
    Offensive: carries the motif. Defensive: carries defensiveMove AND the motif."""
    if defensive:
        return DEFENSIVE_REQUIRED in themes and topic_theme in themes
    return topic_theme in themes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", nargs="?", default="/tmp/puz_xl.csv",
                    help="Lichess puzzle DB CSV (decompressed slice).")
    ap.add_argument("--defensive", action="store_true",
                    help="Select DEFENSIVE puzzles (defensiveMove + motif) into "
                         "puzzles-defensive.json instead of the offensive set.")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    topics = DEFENSIVE_TOPICS if args.defensive else OFFENSIVE_TOPICS
    out = Path(__file__).resolve().parent / (
        "puzzles-defensive.json" if args.defensive else "puzzles.json")
    title_suffix = "(defend)" if args.defensive else ""

    random.seed(42)  # reproducible selection
    buckets: dict[tuple[str, int], list[dict]] = {}
    wanted_themes = set(topics.values())

    with csv_path.open() as f:
        r = csv.DictReader(f)
        for row in r:
            if not row.get("Themes") or not row.get("Moves") or not row.get("FEN"):
                continue  # truncated/malformed row (partial decompress tail)
            themes = set(row["Themes"].split())
            # In defensive mode every candidate must carry defensiveMove.
            if args.defensive and DEFENSIVE_REQUIRED not in themes:
                continue
            if not (wanted_themes & themes):
                continue
            try:
                rating = int(row["Rating"])
                pop = int(row["Popularity"])
                plies = len(row["Moves"].split())
            except Exception:
                continue
            if pop < MIN_POPULARITY or plies > MAX_PLIES or plies < 2:
                continue
            # The agent ALWAYS plays White: the solver side (to move AFTER the
            # opponent's setup move = moves[0]) must be White. Drop the rest.
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
            for topic, theme in topics.items():
                if _matches(theme, themes, args.defensive):
                    buckets.setdefault((topic, band), []).append(row)

    selected = []
    seen_ids = set()
    summary: dict[str, list[int]] = {}
    for topic in topics:
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
                label = topic.replace("-", " ").title()
                selected.append({
                    "id": row["PuzzleId"],
                    "fen": row["FEN"],
                    "moves": row["Moves"].split(),
                    "rating": rating,
                    "difficulty": _difficulty(rating),
                    "title": f"{label} · {_difficulty(rating)} ({rating}) {title_suffix}".strip(),
                    "popularity": int(row["Popularity"]),
                    "themes": row["Themes"].split(),
                    "topic": topic,
                    "band": f"{BANDS[band][0]}-{BANDS[band][1]}",
                    "kind": "defensive" if args.defensive else "offensive",
                    "lichess_url": f"https://lichess.org/training/{row['PuzzleId']}",
                })
                picked += 1
                if picked >= PER_BAND:
                    break
            per_band_counts.append(picked)
        summary[topic] = per_band_counts

    out.write_text(json.dumps(selected, indent=2))
    mode = "DEFENSIVE" if args.defensive else "OFFENSIVE"
    print(f"[{mode}] Selected {len(selected)} puzzles across {len(topics)} topics -> {out}\n")
    print(f"{'topic':22} " + " ".join(f"{lo}-{hi}".rjust(9) for lo, hi in BANDS) + "   total")
    for topic, counts in summary.items():
        print(f"{topic:22} " + " ".join(str(c).rjust(9) for c in counts) + f"   {sum(counts)}")
    short = [t for t, c in summary.items() if any(x < PER_BAND for x in c)]
    if short:
        print(f"\nNote: under-filled (< {PER_BAND}/band): {short}")


if __name__ == "__main__":
    main()
