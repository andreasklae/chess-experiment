"""Game logging: two CSV files (ranked + experimental) and per-game agent JSON.

Each agent game is written to exactly one of:

- ``ranked.csv`` — official thesis record. Only games played on a clean ``main``
  branch are appended here, and only these games update ``agent_elo.json``.
- ``experimental.csv`` — everything else: lobby games, batches run from a feature
  branch, and any game where the live git state isn't a clean ``main``.

The phase decision is made by ``repo_state.is_ranked_context()`` at game-record
time, not at game-create time. That means a long-running batch reads the live
git state for every game; mid-batch branch changes (which the operator
shouldn't do anyway) would split a batch across both files.

Schema and rationale: see
[knowledge-base/decisions/2026-05-24-ranked-vs-experimental.md].
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


# CSV schema — shared by ranked.csv and experimental.csv so analysis tooling
# only has to know one shape. Keep additive: new columns go at the end so old
# rows still parse.
CSV_COLUMNS = [
    "game_id",
    "batch_id",
    "batch_name",
    "datetime",
    "phase",             # "ranked" or "experimental"
    "branch",            # git branch at record time
    "commit_sha",        # full HEAD SHA at record time
    "white_type",
    "black_type",
    "opponent",
    "opponent_elo",
    "result",            # "1-0"/"0-1"/"1/2-1/2" or "" for aborted
    "aborted_reason",    # empty for finished games
    "elo_before",        # only meaningful for ranked rows
    "elo_after",         # only meaningful for ranked rows
    "model",
    "temperature",
    "agent_log_path",    # relative path to <game_id>_agent.json
    "analysis_path",     # relative path to external analysis (lichess/chess.com etc.); empty by default
]


@dataclass
class AgentTurn:
    move_number: int
    prompt: str
    events: list[dict[str, Any]] = field(default_factory=list)
    move_chosen: str | None = None
    # Per-move evaluation telemetry, populated by record_move_evals() after
    # the move commits. cp values are centipawns from white's perspective;
    # None when Stockfish was unavailable or the position was game-over.
    stockfish_eval_cp_before: int | None = None
    stockfish_eval_cp_after: int | None = None
    static_eval_cp_before: int | None = None
    static_eval_cp_after: int | None = None
    move_time_ms: int | None = None


class LoggingService:
    """Writes ranked.csv / experimental.csv and per-game agent JSON files."""

    RANKED_CSV = "ranked.csv"
    EXPERIMENTAL_CSV = "experimental.csv"

    def __init__(self, games_dir: Path) -> None:
        self._games_dir = games_dir
        games_dir.mkdir(parents=True, exist_ok=True)
        self._ranked_path = games_dir / self.RANKED_CSV
        self._experimental_path = games_dir / self.EXPERIMENTAL_CSV
        self._ensure_csv_header(self._ranked_path)
        self._ensure_csv_header(self._experimental_path)
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

    def get_past_agent_events(self, game_id: str) -> list[dict]:
        """Return all events from completed turns plus any events already emitted
        in the current in-progress turn. Used to replay history when a new SSE
        subscriber connects mid-game."""
        past_events: list[dict] = []
        for turn in self._agent_turns.get(game_id, []):
            past_events.extend(turn.events)
        current = self._current_turns.get(game_id)
        if current is not None:
            past_events.extend(current.events)
        return past_events

    def record_move_evals(
        self,
        game_id: str,
        *,
        stockfish_cp_before: int | None,
        stockfish_cp_after: int | None,
        static_cp_before: int | None,
        static_cp_after: int | None,
        move_time_ms: int | None,
    ) -> None:
        """Attach per-move evaluation telemetry to the most-recent closed
        agent turn for this game. Called by game_service after the agent's
        move has been applied to the board. No-op when there's no turn to
        attach to — this lets the call site be unconditional even for
        non-agent games."""
        turns = self._agent_turns.get(game_id)
        if not turns:
            return
        latest = turns[-1]
        latest.stockfish_eval_cp_before = stockfish_cp_before
        latest.stockfish_eval_cp_after = stockfish_cp_after
        latest.static_eval_cp_before = static_cp_before
        latest.static_eval_cp_after = static_cp_after
        latest.move_time_ms = move_time_ms

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
        temperature: str = "",
        aborted_reason: str = "",
        analysis_path: str = "",
    ) -> None:
        """Append one row to ranked.csv or experimental.csv based on git state.

        The phase decision is delegated to ``repo_state.is_ranked_context``;
        see that function for the policy (main + clean tree = ranked).
        """
        from app.repo_state import current_phase, live_git_state

        agent_log_path = ""
        if game_id in self._agent_turns or game_id in self._current_turns:
            agent_log_path = self._write_agent_log(game_id, model)

        phase = current_phase()
        git = live_git_state()
        target_path = self._ranked_path if phase == "ranked" else self._experimental_path

        row = {
            "game_id": game_id,
            "batch_id": batch_id,
            "batch_name": batch_name,
            "datetime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "phase": phase,
            "branch": git.branch,
            "commit_sha": git.commit_sha,
            "white_type": white_type,
            "black_type": black_type,
            "opponent": opponent,
            "opponent_elo": opponent_elo,
            "result": result or "",
            "aborted_reason": aborted_reason,
            "elo_before": elo_before if phase == "ranked" else "",
            "elo_after": elo_after if phase == "ranked" else "",
            "model": model,
            "temperature": temperature,
            "agent_log_path": agent_log_path,
            "analysis_path": analysis_path,
        }
        with open(target_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writerow(row)

        logger.info(
            "record_game · phase=%s file=%s game=%s result=%s",
            phase,
            target_path.name,
            game_id[:8],
            result or (f"aborted({aborted_reason[:40]})" if aborted_reason else "—"),
        )

        # Clean up in-memory accumulator
        self._agent_turns.pop(game_id, None)
        self._current_turns.pop(game_id, None)

    # ── Internals ────────────────────────────────────────────────────────

    def _ensure_csv_header(self, path: Path) -> None:
        if not path.exists():
            with open(path, "w", newline="", encoding="utf-8") as f:
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
                    "evals": {
                        "stockfish_cp_before": t.stockfish_eval_cp_before,
                        "stockfish_cp_after": t.stockfish_eval_cp_after,
                        "static_cp_before": t.static_eval_cp_before,
                        "static_cp_after": t.static_eval_cp_after,
                        "move_time_ms": t.move_time_ms,
                    },
                }
                for t in turns
            ],
        }
        filename = f"{game_id}_agent.json"
        path = self._games_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return filename
