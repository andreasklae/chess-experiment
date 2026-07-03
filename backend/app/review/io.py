"""Persisting reviews to a folder of JSON files.

Each review is one JSON file under `backend/games/reviews/` (override with `out_dir`),
named `<game_id>.json` (or a content hash when no id is given). A `batch_summary.py`-
style aggregate over many reviews can be built on top of `aggregate_weaknesses`.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from app.config import get_settings
from app.review import classify as C


def _default_dir() -> Path:
    return get_settings().games_dir / "reviews"


def write_review(review: dict, *, out_dir: Path | str | None = None) -> Path:
    """Write one review dict to <out_dir>/<game_id-or-hash>.json. Returns the path."""
    d = Path(out_dir) if out_dir is not None else _default_dir()
    d.mkdir(parents=True, exist_ok=True)
    gid = review.get("game_id")
    if not gid:
        blob = json.dumps(review.get("moves", []), sort_keys=True)[:4096]
        gid = "review_" + hashlib.sha1(blob.encode()).hexdigest()[:10]
        review = {**review, "game_id": gid}
    path = d / f"{gid}.json"
    path.write_text(json.dumps(review, indent=1))
    return path


def load_reviews(in_dir: Path | str | None = None) -> list[dict]:
    d = Path(in_dir) if in_dir is not None else _default_dir()
    if not d.exists():
        return []
    out = []
    for f in sorted(d.glob("*.json")):
        if f.name == "_aggregate.json":
            continue
        try:
            out.append(json.loads(f.read_text()))
        except Exception:
            continue
    return out


def aggregate_weaknesses(reviews: list[dict], *, player: str = "white") -> dict:
    """Roll up many reviews into one weakness report for `player` — the point of the
    whole module for the experiment: where (phase / in-check / under-threat / …) does
    the player blunder most, across a batch of games. mistake_rate-ranked."""
    tag_totals: dict[str, dict] = defaultdict(lambda: {"n_total": 0, "n_mistakes": 0})
    label_counts: dict[str, int] = defaultdict(int)
    accs: list[float] = []
    cpls: list[float] = []
    worst: list[dict] = []

    for r in reviews:
        side = (r.get("summary") or {}).get(player) or {}
        if side.get("accuracy_pct") is not None:
            accs.append(side["accuracy_pct"])
        if side.get("avg_centipawn_loss") is not None:
            cpls.append(side["avg_centipawn_loss"])
        for lbl, n in (side.get("move_counts") or {}).items():
            label_counts[lbl] += n
        for tag, v in (side.get("weakness_tags") or {}).items():
            tag_totals[tag]["n_total"] += v.get("n_total", 0)
            tag_totals[tag]["n_mistakes"] += v.get("n_mistakes", 0)
        for w in side.get("worst_moments", []):
            worst.append({**w, "game_id": r.get("game_id")})

    for v in tag_totals.values():
        v["mistake_rate"] = round(v["n_mistakes"] / v["n_total"], 3) if v["n_total"] else 0.0
    ranked_tags = dict(sorted(tag_totals.items(), key=lambda kv: -kv[1]["mistake_rate"]))
    worst.sort(key=lambda w: -w.get("win_pct_lost", 0))

    return {
        "player": player,
        "n_games": len(reviews),
        "mean_accuracy_pct": round(sum(accs) / len(accs), 1) if accs else None,
        "mean_avg_centipawn_loss": round(sum(cpls) / len(cpls), 1) if cpls else None,
        "label_counts": {lbl: label_counts.get(lbl, 0) for lbl in C.LABELS},
        "weakness_tags": ranked_tags,
        "worst_moments": worst[:25],
    }


def write_aggregate(reviews: list[dict], *, out_dir: Path | str | None = None) -> Path:
    d = Path(out_dir) if out_dir is not None else _default_dir()
    d.mkdir(parents=True, exist_ok=True)
    agg = {p: aggregate_weaknesses(reviews, player=p) for p in ("white", "black")}
    path = d / "_aggregate.json"
    path.write_text(json.dumps(agg, indent=1))
    return path
