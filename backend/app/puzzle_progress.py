"""Persistent per-puzzle progress for the puzzle benchmark.

Tracks, across runs and backend restarts, the latest outcome of every puzzle:
  status: 'untested' (never run) | 'solved' | 'failed'
plus the last attempt's detail (solved_plies/total, deviation, timestamp, the
run it belonged to). Stored as a single JSON file so a run can be resumed, only
unsolved puzzles re-run, and a clear per-topic overview rendered.

The puzzle SET (puzzles.json) is the source of truth for which puzzles exist;
this store only records outcomes keyed by puzzle id. Puzzles in the set with no
record are 'untested'.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path


class PuzzleProgress:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except Exception:
                self._data = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2))
        tmp.replace(self.path)

    def record(self, result: dict, run_id: str) -> None:
        """Record a puzzle result (the dict the runner produces)."""
        pid = result["puzzle_id"]
        with self._lock:
            self._data[pid] = {
                "status": "solved" if result.get("solved") else "failed",
                "topic": result.get("topic", ""),
                "difficulty": result.get("difficulty", ""),
                "rating": result.get("rating", 0),
                "solved_plies": result.get("solved_plies", 0),
                "total_plies": result.get("total_plies", 0),
                "aborted_reason": result.get("aborted_reason"),
                "run_id": run_id,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "attempts": result.get("attempts", []),
            }
            self._save()

    def status_of(self, pid: str) -> str:
        rec = self._data.get(pid)
        return rec["status"] if rec else "untested"

    def get(self, pid: str) -> dict | None:
        return self._data.get(pid)

    def filter_ids(self, all_ids: list[str], mode: str) -> list[str]:
        """Select puzzle ids by run mode:
          'all'      -> every puzzle in the set
          'unsolved' -> failed OR untested (everything not yet solved)
          'untested' -> only those with no record yet
          'failed'   -> only those whose last outcome was failed
        """
        if mode == "all":
            return list(all_ids)
        out = []
        for pid in all_ids:
            st = self.status_of(pid)
            if mode == "unsolved" and st in ("failed", "untested"):
                out.append(pid)
            elif mode == "untested" and st == "untested":
                out.append(pid)
            elif mode == "failed" and st == "failed":
                out.append(pid)
        return out

    def overview(self, specs) -> dict:
        """Per-topic + per-difficulty solved/failed/untested counts over the set.
        `specs` is the list of PuzzleSpec (the source of truth for membership)."""
        topics: dict[str, dict] = {}
        difficulty: dict[str, dict] = {}
        totals = {"solved": 0, "failed": 0, "untested": 0, "total": 0}
        per_puzzle = []
        for s in specs:
            st = self.status_of(s.id)
            rec = self.get(s.id)
            t = topics.setdefault(s.topic, {"solved": 0, "failed": 0, "untested": 0, "total": 0})
            d = difficulty.setdefault(s.difficulty or "?", {"solved": 0, "failed": 0, "untested": 0, "total": 0})
            t[st] += 1; t["total"] += 1
            d[st] += 1; d["total"] += 1
            totals[st] += 1; totals["total"] += 1
            per_puzzle.append({
                "id": s.id, "topic": s.topic, "difficulty": s.difficulty,
                "rating": s.rating, "title": s.title, "status": st,
                "solved_plies": (rec or {}).get("solved_plies"),
                "total_plies": (rec or {}).get("total_plies", s.total_solver_plies),
                "ts": (rec or {}).get("ts"),
            })
        return {"totals": totals, "by_topic": topics, "by_difficulty": difficulty,
                "puzzles": per_puzzle}
