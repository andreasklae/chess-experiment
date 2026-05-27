#!/usr/bin/env python3
"""Recover a game that finished but was never logged.

The game JSON shows ``status: finished`` and a result, but no CSV row was
written, no ``_agent.json`` was produced (turn events were in-memory only
and are unrecoverable), and the batch state may still list it as
``current_game_id`` without any games appended.

Historically this happened when the agent commit path used a separate
``/agent-move`` push endpoint and the bot loop's early-return branch in
``_run_until_human_or_finished`` could fire before the game-over handlers
ran. The single-writer refactor (commit-intent validator endpoint + bot-
loop push) eliminated that class of orphan. This script remains to
recover any games that slipped through under the old design.

Recovery actions per orphan:
1. Move ``<game_id>.json`` (and any ``_agent.json`` if it exists) into the
   correct per-PR folder, renamed with the next sequence prefix.
2. Append a row to ``ranked.csv`` (or ``experimental.csv`` if not on main
   with clean tree) with the result, ELO before/after, opponent.
3. If the game has a result and we're on ranked context, update
   ``agent_elo.json`` to reflect the win/loss/draw.
4. Append a ``GameRecord`` to the relevant batch state (matching
   ``current_game_id``) and clear ``current_game_id`` so the batch runner
   can advance on next backend start.

Run from the chess experiment root:

    .venv/bin/python scripts/recover_orphan_game.py <game_id>

The script will print a summary and ask for confirmation before writing.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def _games_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "backend" / "games"


def _batches_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "backend" / "batches"


def _find_game_json(games_dir: Path, game_id: str) -> Path | None:
    for p in games_dir.rglob(f"{game_id}.json"):
        return p
    return None


def _find_agent_log(games_dir: Path, game_id: str) -> Path | None:
    for p in games_dir.rglob(f"{game_id}_agent.json"):
        return p
    return None


def _resolve_target() -> tuple[str, str]:
    """Call into the live folder_resolver so the recovery uses the same
    rule as the backend would now apply."""
    from app.folder_resolver import resolve_target_folder, clear_cache
    clear_cache()
    t = resolve_target_folder()
    return t.folder, t.pr_number


def _next_sequence(folder: Path) -> int:
    import re
    seq_re = re.compile(r"^(\d{3})_")
    if not folder.exists():
        return 1
    seen = []
    for p in folder.glob("*_agent.json"):
        m = seq_re.match(p.name)
        if m:
            seen.append(int(m.group(1)))
    for p in folder.glob("*.json"):
        if p.name.endswith("_agent.json"):
            continue
        m = seq_re.match(p.name)
        if m:
            seen.append(int(m.group(1)))
    return (max(seen) + 1) if seen else 1


def _update_elo(games_dir: Path, opponent_elo: int, result_norm: str) -> tuple[float, float]:
    """Apply the result to agent_elo.json, return (before, after)."""
    from app.elo import AgentEloState
    state = AgentEloState.load(games_dir / "agent_elo.json")
    before = state.elo
    state.apply_result(opponent_elo, result_norm)  # type: ignore[arg-type]
    state.save(games_dir / "agent_elo.json")
    return before, state.elo


def _normalize(result: str) -> str | None:
    """python-chess result string → ELO library result label."""
    if result == "1-0":
        return "win"
    if result == "0-1":
        return "loss"
    if result == "1/2-1/2":
        return "draw"
    return None


def _find_batch_with_game(batches_dir: Path, game_id: str) -> Path | None:
    for p in batches_dir.glob("*.json"):
        try:
            data = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("current_game_id") == game_id:
            return p
    return None


def recover(game_id: str, *, apply: bool) -> int:
    games = _games_dir()
    batches = _batches_dir()

    state_src = _find_game_json(games, game_id)
    if state_src is None:
        print(f"error: no game JSON found for {game_id}", file=sys.stderr)
        return 2
    state = json.loads(state_src.read_text())
    result = state.get("result")
    if not result:
        print(f"error: game {game_id} has no result; cannot recover", file=sys.stderr)
        return 2

    black_cfg = state["black"]
    opponent_elo = int(black_cfg["elo"]) if black_cfg.get("elo") is not None else 0
    opponent = (
        f"chesscom-{opponent_elo}" if black_cfg["type"] == "chesscom"
        else (f"maia-{opponent_elo}" if black_cfg["type"] == "maia" else black_cfg["type"])
    )
    norm = _normalize(result)

    folder_name, pr_number = _resolve_target()
    folder = games / folder_name
    seq = _next_sequence(folder)
    state_dst_name = f"{seq:03d}_{game_id}.json" if folder_name != "baseline" else f"{game_id}.json"
    agent_dst_name = f"{seq:03d}_{game_id}_agent.json" if folder_name != "baseline" else f"{game_id}_agent.json"
    state_dst = folder / state_dst_name

    agent_src = _find_agent_log(games, game_id)
    agent_dst = folder / agent_dst_name if agent_src else None

    # Determine phase from current git state.
    from app.repo_state import current_phase
    phase = current_phase()
    csv_name = "ranked.csv" if phase == "ranked" else "experimental.csv"
    csv_path = games / csv_name

    batch_path = _find_batch_with_game(batches, game_id)

    print(f"== recovery plan for {game_id} ==")
    print(f"  result:        {result} ({norm})")
    print(f"  opponent:      {opponent} (elo {opponent_elo})")
    print(f"  target folder: {folder_name} (pr_number={pr_number or '∅'})")
    print(f"  move state:    {state_src} -> {state_dst}")
    if agent_src:
        print(f"  move agent log: {agent_src} -> {agent_dst}")
    else:
        print("  agent log:     not found (turn events lost)")
    print(f"  csv row:       append to {csv_path.name}")
    if batch_path:
        print(f"  batch update:  {batch_path.name} (clear current_game_id, append GameRecord)")
    else:
        print("  batch update:  no batch references this game")

    if not apply:
        print("\n(dry-run; pass --apply to write)")
        return 0

    # 1. Move files
    folder.mkdir(parents=True, exist_ok=True)
    if not state_dst.exists():
        shutil.move(str(state_src), str(state_dst))
    if agent_src and agent_dst and not agent_dst.exists():
        shutil.move(str(agent_src), str(agent_dst))

    # 2. Update ELO (only when on ranked context)
    elo_before = elo_after = None
    if phase == "ranked" and norm is not None:
        elo_before, elo_after = _update_elo(games, opponent_elo, norm)

    # 3. Append CSV row
    rel_agent_path = f"{folder_name}/{agent_dst_name}" if agent_dst and agent_dst.exists() else ""
    from app.repo_state import agent_model, agent_temperature, live_git_state
    git = live_git_state()
    # ``agent_model()`` reads SKILL_AGENT_OPENAI_MODEL from the environment.
    # When this script is invoked from a shell without the backend's dotenv
    # loaded, the env var is empty — fall back to the published Gemma model
    # name so the CSV row carries the right provenance instead of "".
    model_name = agent_model() or "google/gemma-4-31B-it"
    batch_id = ""
    batch_name = ""
    if batch_path:
        bdata = json.loads(batch_path.read_text())
        batch_id = bdata.get("batch_id", "")
        batch_name = bdata.get("label", "")

    row = {
        "game_id": game_id,
        "batch_id": batch_id,
        "batch_name": batch_name,
        "datetime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phase": phase,
        "branch": git.branch,
        "white_type": state["white"]["type"],
        "black_type": black_cfg["type"],
        "opponent": opponent,
        "opponent_elo": str(opponent_elo),
        "result": result,
        "aborted_reason": "",
        "elo_before": f"{elo_before:.1f}" if elo_before is not None else "",
        "elo_after": f"{elo_after:.1f}" if elo_after is not None else "",
        "model": model_name,
        "temperature": agent_temperature(),
        "agent_log_path": rel_agent_path,
        "analysis_path": "",
        "pr_number": pr_number,
    }
    # Read header to know column order
    with csv_path.open("r", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
    with csv_path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writerow({k: row.get(k, "") for k in header})

    # 4. Update batch state
    if batch_path:
        bdata = json.loads(batch_path.read_text())
        bdata["games"].append({
            "game_id": game_id,
            "opponent_elo": opponent_elo,
            "result": norm,
            "agent_elo_before": elo_before if elo_before is not None else 0,
            "agent_elo_after": elo_after if elo_after is not None else 0,
        })
        if bdata.get("current_game_id") == game_id:
            bdata["current_game_id"] = None
        # Reset draw streak per record_game logic
        if norm == "draw":
            bdata["consecutive_draws"] = bdata.get("consecutive_draws", 0) + 1
        else:
            bdata["consecutive_draws"] = 0
        # Don't set status — let the batch runner decide on restart.
        batch_path.write_text(json.dumps(bdata, indent=2))

    print("\nrecovery applied. Restart the backend; the batch runner will advance to the next game.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_id", help="Game ID (32-hex UUID) to recover")
    parser.add_argument("--apply", action="store_true", help="Actually move files & write rows (default is dry-run)")
    args = parser.parse_args()
    return recover(args.game_id, apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
