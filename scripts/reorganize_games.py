#!/usr/bin/env python3
"""One-shot migration: reorganize ``backend/games/`` into per-PR subfolders.

The original layout dumped every per-game JSON (``<id>.json``,
``<id>_agent.json``) at the top level of ``backend/games/``. After the
``visualization-and-context-management`` branch landed we organise by the
PR / branch that produced the game so it's possible to tell at a glance
which agent version generated which games.

Rules applied here:

- ``ranked.csv`` rows → folder ``baseline/`` (all pre-PR main commits).
  Baseline files keep their bare UUID filenames; no numbering prefix is
  added (the user explicitly asked not to renumber existing games).
- ``experimental.csv`` rows → folder = the row's ``branch`` value. Files
  in non-baseline folders get a zero-padded ``NNN_`` chronological prefix
  computed from ``datetime`` ascending within each folder.
- Rows with an empty ``branch`` field land in ``misc/``.
- The CSV ``agent_log_path`` column is rewritten to the new relative path.
- A new ``pr_number`` column is appended to both CSVs (empty for existing
  rows; the backend populates it for future rows via ``gh pr view``).
- Files referenced by CSV rows but missing on disk are reported, not fatal.
- Orphan files (on disk but not in any CSV) are reported and left in place.

The script is idempotent: re-running it after a successful migration is a
no-op because the rewritten CSVs already reference the moved paths.

Run from the chess experiment root:

    .venv/bin/python scripts/reorganize_games.py [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from collections import defaultdict
from pathlib import Path

# The pre-PR baseline commit. Anything in ranked.csv carries this SHA; we
# group them by destination folder rather than by commit, so the explicit
# SHA isn't needed for the move logic — kept here as documentation.
BASELINE_FOLDER = "baseline"
MISC_FOLDER = "misc"

# New column to be added to both CSVs.
NEW_COLUMN = "pr_number"

# Files at the top level of games/ that are NOT game state and must be left in place.
SKIP_FILES = frozenset({"ranked.csv", "experimental.csv", "agent_elo.json"})


def _games_dir() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent / "backend" / "games"


def _read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    return fieldnames, rows


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    if NEW_COLUMN not in fieldnames:
        fieldnames = list(fieldnames) + [NEW_COLUMN]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            r.setdefault(NEW_COLUMN, "")
            writer.writerow(r)


def _target_folder_for(row: dict, *, is_ranked: bool) -> str:
    if is_ranked:
        return BASELINE_FOLDER
    branch = (row.get("branch") or "").strip()
    return branch or MISC_FOLDER


def _move(src: Path, dst: Path, *, dry_run: bool, plan: list[str], planned: set[str]) -> bool:
    if not src.exists():
        return False
    if dst.exists():
        # Already migrated — skip but treat as success.
        return True
    key = f"{src} -> {dst}"
    if key in planned:
        return True
    planned.add(key)
    plan.append(f"  mv {src.relative_to(src.parents[1])} -> {dst.relative_to(dst.parents[1])}")
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    return True


def _assign_sequence_numbers(rows: list[dict], folder: str) -> dict[str, int]:
    """For experimental rows in a non-baseline folder, return ``{game_id: seq}``.

    Sequence is assigned by ``datetime`` ascending. Rows without a datetime
    sort to the end. Ranked / baseline rows never call this — they keep
    their bare UUIDs.
    """
    if folder == BASELINE_FOLDER:
        return {}
    folder_rows = [r for r in rows if _target_folder_for(r, is_ranked=False) == folder]
    folder_rows.sort(key=lambda r: r.get("datetime") or "")
    seen: set[str] = set()
    ordered_ids: list[str] = []
    for r in folder_rows:
        gid = r.get("game_id", "")
        if gid and gid not in seen:
            seen.add(gid)
            ordered_ids.append(gid)
    return {gid: i + 1 for i, gid in enumerate(ordered_ids)}


def _new_filenames(game_id: str, folder: str, sequence: dict[str, int]) -> tuple[str, str]:
    """Return (state_filename, agent_log_filename) for the moved files."""
    if folder == BASELINE_FOLDER:
        return f"{game_id}.json", f"{game_id}_agent.json"
    seq = sequence.get(game_id)
    if seq is None:
        return f"{game_id}.json", f"{game_id}_agent.json"
    return f"{seq:03d}_{game_id}.json", f"{seq:03d}_{game_id}_agent.json"


# Branch name for orphan game JSONs (committed to this branch but never
# made it into a CSV — typically ad-hoc lobby games from the same period
# as branch development). Set to "" to leave orphans at the top level
# rather than sweeping them into a branch folder.
ORPHAN_DEFAULT_FOLDER = "visualization-and-context-management"


def reorganize(dry_run: bool) -> int:
    games = _games_dir()
    ranked_path = games / "ranked.csv"
    experimental_path = games / "experimental.csv"

    if not ranked_path.exists() or not experimental_path.exists():
        print(f"error: missing one of {ranked_path} / {experimental_path}", file=sys.stderr)
        return 2

    ranked_fields, ranked_rows = _read_csv(ranked_path)
    exp_fields, exp_rows = _read_csv(experimental_path)

    # Compute sequence numbering per experimental folder.
    folders_in_exp = {_target_folder_for(r, is_ranked=False) for r in exp_rows}
    sequence_by_folder: dict[str, dict[str, int]] = {
        f: _assign_sequence_numbers(exp_rows, f) for f in folders_in_exp
    }

    moves: list[str] = []
    planned: set[str] = set()
    missing: list[str] = []
    moved_files: set[str] = set()

    def process(row: dict, *, is_ranked: bool) -> None:
        folder = _target_folder_for(row, is_ranked=is_ranked)
        sequence = {} if is_ranked else sequence_by_folder.get(folder, {})
        gid = row.get("game_id", "")
        if not gid:
            return

        state_dst_name, agent_dst_name = _new_filenames(gid, folder, sequence)

        state_src = games / f"{gid}.json"
        state_dst = games / folder / state_dst_name
        if state_src.exists():
            _move(state_src, state_dst, dry_run=dry_run, plan=moves, planned=planned)
            moved_files.add(f"{gid}.json")
        elif state_dst.exists():
            pass  # already migrated
        # State file may legitimately not exist (some rows only have agent logs).

        agent_src = games / f"{gid}_agent.json"
        agent_dst = games / folder / agent_dst_name
        if agent_src.exists():
            _move(agent_src, agent_dst, dry_run=dry_run, plan=moves, planned=planned)
            moved_files.add(f"{gid}_agent.json")
        elif agent_dst.exists():
            pass  # already migrated
        else:
            existing_log = (row.get("agent_log_path") or "").strip()
            if existing_log:
                missing.append(f"{gid}: agent log not found at top level ({existing_log})")

        # Rewrite agent_log_path on the row to point at the new location.
        if agent_dst.exists() or agent_src.exists():
            row["agent_log_path"] = f"{folder}/{agent_dst_name}"

    # Group exp rows by game_id to share state-file moves across multiple
    # rows referencing the same id (e.g. retry rows after Connection error).
    exp_rows_by_game: dict[str, list[dict]] = defaultdict(list)
    for r in exp_rows:
        gid = r.get("game_id", "")
        if gid:
            exp_rows_by_game[gid].append(r)

    for r in ranked_rows:
        process(r, is_ranked=True)
    for gid, rows in exp_rows_by_game.items():
        # Move the files once; rewrite agent_log_path on every row.
        for i, r in enumerate(rows):
            process(r, is_ranked=False)

    # Survey orphans at the top level: per-game JSONs that aren't in any CSV.
    # If ORPHAN_DEFAULT_FOLDER is set, sweep them into that folder (no
    # sequence prefix — they have no CSV row to carry the new path, so the
    # bare UUID is the only stable identifier we can preserve).
    orphan_pairs: list[tuple[Path, Path]] = []  # (src, dst)
    for p in games.glob("*.json"):
        if p.name in SKIP_FILES:
            continue
        if p.name in moved_files:
            continue
        if not p.is_file():
            continue
        if ORPHAN_DEFAULT_FOLDER:
            dst = games / ORPHAN_DEFAULT_FOLDER / p.name
            orphan_pairs.append((p, dst))

    for src, dst in orphan_pairs:
        _move(src, dst, dry_run=dry_run, plan=moves, planned=planned)
    orphans = [str(src.name) for src, _ in orphan_pairs]

    print("== move plan ==")
    if moves:
        for line in moves:
            print(line)
    else:
        print("  (nothing to move; already reorganised)")

    if missing:
        print("\n== rows with missing files ==")
        for m in missing:
            print(f"  {m}")

    if orphans:
        dest = ORPHAN_DEFAULT_FOLDER or "(left in place)"
        print(f"\n== orphan files (no CSV row) -> swept into {dest}/ ==")
        for o in orphans:
            print(f"  {o}")

    if dry_run:
        print("\n(dry-run; no files were moved or CSVs rewritten)")
        return 0

    # Rewrite CSVs with the new column and updated paths.
    _write_csv(ranked_path, ranked_fields, ranked_rows)
    _write_csv(experimental_path, exp_fields, exp_rows)

    print("\nCSVs rewritten with pr_number column and updated agent_log_path values.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print plan without moving anything")
    args = parser.parse_args()
    return reorganize(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
