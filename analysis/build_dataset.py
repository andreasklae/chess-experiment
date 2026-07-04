#!/usr/bin/env python3
"""Build the thesis analysis dataset for the chess experiment.

Re-runnable and incremental: reviews are cached one JSON per game in
``backend/games/reviews/`` (skipped when present), so running this again after
new games finish only processes the new ones. Output is a tidy per-game CSV at
``analysis/data/games.csv`` plus ``analysis/data/wiki_growth.csv`` (wiki size
over time from git history). The notebook ``analysis/analysis.ipynb`` consumes
these.

Usage (from the chess repo root, chess venv):
    .venv/bin/python analysis/build_dataset.py            # everything
    .venv/bin/python analysis/build_dataset.py --ranked-only
    .venv/bin/python analysis/build_dataset.py --no-review  # metrics only

Review settings: Stockfish depth 12, multipv 3, single-threaded → deterministic
(documented in the KB; the review engine's formulas are Lichess-published, see
backend/app/review/README.md).

Development-phase periodization (thesis narrative; see
knowledge-base/work/experiment-chess-results-and-phases.md):
  P1 minimal-tools      — legal moves + make_move only (baseline folder / pre-PR1)
  P2 visualization      — show_position & context management (PR #1, merged 2026-05-26)
  P3 mating-blunders    — mating curriculum, gates, imagine_line (PRs #2-#4, → 2026-06-23)
  P4 autonomous-loop    — puzzle/review-driven iteration, wiki expansion, fix loop
                          (post-PR4 dev; ranked measurement from PR #5, 2026-07-03)
For EXPERIMENTAL games the phase is the dev branch the game was played on (the
work in progress); for RANKED games it is the last-merged PR at game time (the
configuration actually measured).
"""
import argparse
import csv
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
GAMES = BACKEND / "games"
REVIEWS = GAMES / "reviews"
OUT = REPO / "analysis" / "data"
sys.path.insert(0, str(BACKEND))

STANDARD_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

PR_MERGES = [  # (merged_at_utc, pr, phase-from-then-on for RANKED games)
    ("2026-05-26T18:26:16", 1, "P2-visualization"),
    ("2026-06-15T10:00:24", 2, "P3-mating-blunders"),
    ("2026-07-03T14:37:31", 5, "P4-autonomous-loop"),
]
FOLDER_PHASE = {  # dev branch -> phase (EXPERIMENTAL games)
    "baseline": "P1-minimal-tools",
    "visualization-and-context-management": "P2-visualization",
    "mating-patterns-and-strategy": "P3-mating-blunders",
    "chess-mate-conversion-and-driver-fixes": "P3-mating-blunders",
    "board-representation-and-context-fidelity": "P4-autonomous-loop",
    "line-proof-audit": "P4-autonomous-loop",
}


def ranked_phase(dt: str) -> str:
    phase = "P1-minimal-tools"
    for merged, _pr, ph in PR_MERGES:
        if dt >= merged:
            phase = ph
    return phase


def find_state_file(gid: str) -> Path | None:
    for f in GAMES.glob(f"**/*{gid}.json"):
        if not f.name.endswith("_agent.json"):
            return f
    return None


def find_agent_file(gid: str) -> Path | None:
    """Newest per-turn snapshot (highest numeric prefix), else the bare one."""
    best, best_seq = None, -1
    for f in GAMES.glob(f"**/*{gid}_agent.json"):
        m = re.match(r"(\d+)_", f.name)
        seq = int(m.group(1)) if m else 0
        if seq > best_seq:
            best, best_seq = f, seq
    return best


def ensure_review(gid: str, state: dict, depth: int, engine_cache: dict) -> dict | None:
    out = REVIEWS / f"{gid}.json"
    if out.exists():
        try:
            return json.loads(out.read_text())
        except Exception:
            pass
    moves = state.get("uci_moves") or []
    if len(moves) < 4:
        return None
    from app.review import review_game, write_review
    start_fen = state.get("initial_fen") or None
    try:
        review = review_game(moves=moves, start_fen=start_fen, depth=depth,
                             game_id=gid, stockfish_path=engine_cache["sf"])
        write_review(review, out_dir=REVIEWS)
        return review
    except Exception as exc:
        print(f"  review failed {gid[:8]}: {exc}", flush=True)
        return None


def agent_metrics(path: Path | None) -> dict:
    m = dict(n_turns=None, tool_calls=None, tools_per_turn=None, confirms=None,
             gate_rejections=None, imagine_line_calls=None, imagine_line_max_plies=None,
             wiki_reads=None, wiki_searches=None, prompt_chars_mean=None,
             reasoning_chars_mean=None, tool_mix=None)
    if path is None:
        return m
    try:
        d = json.loads(path.read_text())
    except Exception:
        return m
    turns = d.get("turns") or []
    calls = Counter()
    confirms = rejections = il_calls = 0
    il_max = 0
    plens, rlens = [], []
    for t in turns:
        plens.append(len(t.get("prompt") or ""))
        for e in t.get("events", []):
            if e.get("type") == "tool_call":
                tool = e.get("tool") or "?"
                calls[tool] += 1
                args = e.get("args") or {}
                if tool == "chess__make_move":
                    if args.get("confirm"):
                        confirms += 1
                    if args.get("reasoning"):
                        rlens.append(len(str(args["reasoning"])))
                if tool == "chess__imagine_line":
                    il_calls += 1
                    toks = [x for x in re.split(r"[,\s]+", str(args.get("moves", ""))) if x]
                    il_max = max(il_max, len(toks))
            elif e.get("type") == "tool_result" and e.get("tool") == "chess__make_move":
                r = str(e.get("result", ""))
                if '"ok": false' in r and ("SAFETY CHECK" in r or "NOT committed" in r
                                           or "NOT yet committed" in r):
                    rejections += 1
    n = len(turns)
    total = sum(calls.values())
    m.update(
        n_turns=n, tool_calls=total,
        tools_per_turn=round(total / n, 2) if n else None,
        confirms=confirms, gate_rejections=rejections,
        imagine_line_calls=il_calls, imagine_line_max_plies=il_max or None,
        wiki_reads=calls.get("read_reference", 0),
        wiki_searches=calls.get("chess__search_wiki", 0),
        prompt_chars_mean=round(sum(plens) / len(plens)) if plens else None,
        reasoning_chars_mean=round(sum(rlens) / len(rlens)) if rlens else None,
        tool_mix=json.dumps(dict(calls.most_common()), separators=(",", ":")),
    )
    return m


def review_metrics(review: dict | None, agent_color: str = "white") -> dict:
    m = dict(accuracy=None, acpl=None, blunders=None, mistakes=None,
             inaccuracies=None, best_moves=None, opp_accuracy=None,
             worst_winpct_drop=None)
    if not review:
        return m
    summary = review.get("summary") or {}
    me = summary.get(agent_color) or {}
    opp = summary.get("black" if agent_color == "white" else "white") or {}
    labels = me.get("move_counts") or {}
    worst = me.get("worst_moments") or []
    m.update(
        accuracy=me.get("accuracy_pct"), acpl=me.get("avg_centipawn_loss"),
        blunders=labels.get("blunder", 0), mistakes=labels.get("mistake", 0),
        inaccuracies=labels.get("inaccuracy", 0),
        best_moves=(labels.get("best", 0) + labels.get("great", 0)
                    + labels.get("brilliant", 0)),
        opp_accuracy=opp.get("accuracy_pct"),
        worst_winpct_drop=(max((w.get("win_pct_lost") or 0) for w in worst)
                           if worst else None),
    )
    return m


def wiki_growth() -> list[dict]:
    """Wiki size over time from git history: commits touching references/."""
    ref = "backend/skills/chess/references"
    log = subprocess.run(
        ["git", "log", "--reverse", "--format=%H %cI", "--", ref],
        cwd=REPO, capture_output=True, text=True).stdout.strip().splitlines()
    rows, seen_dates = [], set()
    for line in log:
        sha, date = line.split()
        day = date[:10]
        if day in seen_dates:
            continue  # one sample per day (last commit of the day wins below)
    # take the LAST commit per day instead:
    per_day = {}
    for line in log:
        sha, date = line.split()
        per_day[date[:10]] = sha
    for day, sha in sorted(per_day.items()):
        ls = subprocess.run(["git", "ls-tree", "-r", "--name-only", sha, ref],
                            cwd=REPO, capture_output=True, text=True).stdout.splitlines()
        pages = [p for p in ls if p.endswith(".md")]
        words = 0
        for p in pages:
            blob = subprocess.run(["git", "show", f"{sha}:{p}"], cwd=REPO,
                                  capture_output=True, text=True).stdout
            words += len(blob.split())
        rows.append(dict(date=day, commit=sha[:8], pages=len(pages), words=words))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ranked-only", action="store_true")
    ap.add_argument("--no-review", action="store_true")
    ap.add_argument("--depth", type=int, default=12)
    args = ap.parse_args()

    import os
    engine_cache = {"sf": os.environ.get("CHESS_STOCKFISH_PATH", "stockfish")}
    OUT.mkdir(parents=True, exist_ok=True)
    REVIEWS.mkdir(parents=True, exist_ok=True)

    sources = [("ranked", GAMES / "ranked.csv")]
    if not args.ranked_only:
        sources.append(("experimental", GAMES / "experimental.csv"))

    rows_out = []
    for kind, csv_path in sources:
        with open(csv_path) as fh:
            for row in csv.DictReader(fh):
                gid = row["game_id"]
                state_f = find_state_file(gid)
                state = {}
                if state_f:
                    try:
                        state = json.loads(state_f.read_text())
                    except Exception:
                        pass
                folder = state_f.parent.name if state_f else ""
                is_puzzle = bool(state.get("initial_fen")
                                 and state["initial_fen"] != STANDARD_FEN)
                aborted = bool((row.get("aborted_reason") or "").strip())
                dt = (row.get("datetime") or "").replace("Z", "")
                phase = (ranked_phase(dt) if kind == "ranked"
                         else FOLDER_PHASE.get(folder, "P4-autonomous-loop"))
                review = None
                if not args.no_review and state and not aborted:
                    review = ensure_review(gid, state, args.depth, engine_cache)
                out = dict(
                    game_id=gid, kind=kind, datetime=row.get("datetime"),
                    phase=phase, folder=folder, branch=row.get("branch"),
                    pr_number=row.get("pr_number"),
                    opponent=row.get("opponent"), opponent_elo=row.get("opponent_elo"),
                    result=row.get("result"), aborted=aborted,
                    aborted_reason=(row.get("aborted_reason") or "")[:80],
                    is_puzzle_mode=is_puzzle,
                    plies=len(state.get("uci_moves") or []) or None,
                    elo_before=row.get("elo_before"), elo_after=row.get("elo_after"),
                    model=row.get("model"), temperature=row.get("temperature"),
                )
                out.update(review_metrics(review))
                out.update(agent_metrics(find_agent_file(gid)))
                rows_out.append(out)
                if len(rows_out) % 25 == 0:
                    print(f"  …{len(rows_out)} games processed", flush=True)

    fields = list(rows_out[0].keys())
    with open(OUT / "games.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows_out)
    print(f"wrote {len(rows_out)} rows -> {OUT/'games.csv'}")

    wg = wiki_growth()
    with open(OUT / "wiki_growth.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["date", "commit", "pages", "words"])
        w.writeheader()
        w.writerows(wg)
    print(f"wrote {len(wg)} rows -> {OUT/'wiki_growth.csv'}")


if __name__ == "__main__":
    main()
