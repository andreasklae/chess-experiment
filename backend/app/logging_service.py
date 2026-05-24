"""Game logging: append-only CSV + per-game agent JSON traces."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CSV_COLUMNS = [
    "game_id",
    "batch_id",
    "batch_name",
    "datetime",
    "white_type",
    "black_type",
    "opponent",
    "opponent_elo",
    "result",
    "aborted_reason",
    "elo_before",
    "elo_after",
    "skill_repo_sha",
    "model",
    "temperature",
    "agent_log_path",
]


@dataclass
class AgentTurn:
    move_number: int
    prompt: str
    events: list[dict[str, Any]] = field(default_factory=list)
    move_chosen: str | None = None


class LoggingService:
    """Manages games.csv and per-game agent JSON files."""

    def __init__(self, games_dir: Path) -> None:
        self._games_dir = games_dir
        games_dir.mkdir(parents=True, exist_ok=True)
        self._csv_path = games_dir / "games.csv"
        self._ensure_csv_header()
        # In-memory accumulator: game_id -> list of AgentTurn
        self._agent_turns: dict[str, list[AgentTurn]] = {}
        # Current open turn per game
        self._current_turns: dict[str, AgentTurn | None] = {}

    # ── Agent turn accumulation ──────────────────────────────────────────

    def start_agent_turn(self, game_id: str, move_number: int, prompt: str) -> None:
        """Open a new agent turn. Call when AgentPlayer.get_move() begins."""
        turn = AgentTurn(move_number=move_number, prompt=prompt)
        self._current_turns[game_id] = turn

    def append_agent_event(self, game_id: str, event: dict[str, Any]) -> None:
        """Append a streaming event to the current open turn."""
        turn = self._current_turns.get(game_id)
        if turn is not None:
            turn.events.append(event)

    def close_agent_turn(self, game_id: str, move_chosen: str | None) -> None:
        """Close the current turn and store it. Call after AgentPlayer.get_move() returns."""
        turn = self._current_turns.pop(game_id, None)
        if turn is None:
            return
        turn.move_chosen = move_chosen
        self._agent_turns.setdefault(game_id, []).append(turn)

    # ── CSV record ───────────────────────────────────────────────────────

    def record_game(
        self,
        *,
        game_id: str,
        white_type: str,
        black_type: str,
        opponent: str,
        opponent_elo: str = "",
        result: str | None,
        model: str = "",
        batch_id: str = "",
        batch_name: str = "",
        elo_before: str = "",
        elo_after: str = "",
        skill_repo_sha: str = "",
        temperature: str = "",
        aborted_reason: str = "",
    ) -> None:
        """Append one row to games.csv and write the agent JSON if applicable.

        Aborted games (player exception mid-play) have result="" and a
        non-empty aborted_reason. ELO before/after will be equal because
        BatchRunner skips ELO updates when parse_game_result returns None.
        """
        agent_log_path = ""
        if game_id in self._agent_turns or game_id in self._current_turns:
            agent_log_path = self._write_agent_log(game_id, model)

        row = {
            "game_id": game_id,
            "batch_id": batch_id,
            "batch_name": batch_name,
            "datetime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "white_type": white_type,
            "black_type": black_type,
            "opponent": opponent,
            "opponent_elo": opponent_elo,
            "result": result or "",
            "aborted_reason": aborted_reason,
            "elo_before": elo_before,
            "elo_after": elo_after,
            "skill_repo_sha": skill_repo_sha,
            "model": model,
            "temperature": temperature,
            "agent_log_path": agent_log_path,
        }
        with open(self._csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writerow(row)

        # Clean up in-memory accumulator
        self._agent_turns.pop(game_id, None)
        self._current_turns.pop(game_id, None)

    # ── Internals ────────────────────────────────────────────────────────

    def _ensure_csv_header(self) -> None:
        if not self._csv_path.exists():
            with open(self._csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()

    def _write_agent_log(self, game_id: str, model: str) -> str:
        """Serialize accumulated turns to <game_id>_agent.json. Returns relative path."""
        turns = self._agent_turns.get(game_id, [])
        payload = {
            "game_id": game_id,
            "model": model,
            "turns": [
                {
                    "move_number": t.move_number,
                    "prompt": t.prompt,
                    "events": t.events,
                    "move_chosen": t.move_chosen,
                }
                for t in turns
            ],
        }
        filename = f"{game_id}_agent.json"
        path = self._games_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return filename
