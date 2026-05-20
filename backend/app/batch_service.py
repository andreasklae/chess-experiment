"""Batch runner: sequential agent-vs-opponent games with auto-progression.

A batch is a fixed number of games where the agent (white) plays a series of
opponents drawn from one pool (Maia or chess.com). Between games:

1. The just-finished game's result updates the agent's persistent ELO.
2. The next opponent's ELO is chosen via `app.elo.pick_opponent_elo`:
     win  → closest opponent ELO strictly above the agent's current ELO
     loss → closest opponent ELO strictly below the agent's current ELO
     draw → closest opponent ELO strictly below the agent's current ELO
3. A new game is created against that opponent. The previous game's agent is
   discarded — each game gets a fresh `Agent` instance so no conversation
   context carries over.

Batches persist to `<batches_dir>/<batch_id>.json` so they survive backend
restarts. The runner picks up where it left off when the service starts.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.elo import (
    AgentEloState,
    INITIAL_ELO,
    OpponentPool,
    parse_game_result,
    pick_opponent_elo,
)
from app.schemas import CreateGameRequest, PlayerConfig


logger = logging.getLogger(__name__)


BatchStatus = Literal["pending", "running", "paused", "completed", "stopped", "failed"]


@dataclass
class GameRecord:
    game_id: str
    opponent_elo: int
    result: str | None  # "win" | "loss" | "draw" | None if aborted
    agent_elo_before: float
    agent_elo_after: float


@dataclass
class Batch:
    batch_id: str
    label: str
    pool: OpponentPool
    total_games: int
    status: BatchStatus
    created_at: str
    games: list[GameRecord] = field(default_factory=list)
    current_game_id: str | None = None
    last_error: str = ""

    @property
    def completed_count(self) -> int:
        return len(self.games)

    @property
    def is_terminal(self) -> bool:
        return self.status in ("completed", "stopped", "failed")

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Batch":
        games = [GameRecord(**g) for g in data.get("games", [])]
        return cls(
            batch_id=data["batch_id"],
            label=data.get("label", ""),
            pool=data["pool"],
            total_games=int(data["total_games"]),
            status=data.get("status", "pending"),
            created_at=data["created_at"],
            games=games,
            current_game_id=data.get("current_game_id"),
            last_error=data.get("last_error", ""),
        )


class BatchService:
    """Owns batch lifecycle and persistence. The runner task is owned by
    GameService — BatchService is purely state + persistence.
    """

    def __init__(self, batches_dir: Path, games_dir: Path):
        self._dir = batches_dir
        self._games_dir = games_dir
        batches_dir.mkdir(parents=True, exist_ok=True)
        self._elo_state_path = games_dir / "agent_elo.json"
        self._lock = asyncio.Lock()

    # ── Persistence ──────────────────────────────────────────────────────

    def _path(self, batch_id: str) -> Path:
        return self._dir / f"{batch_id}.json"

    def save(self, batch: Batch) -> None:
        self._path(batch.batch_id).write_text(json.dumps(batch.to_dict(), indent=2))

    def load(self, batch_id: str) -> Batch | None:
        path = self._path(batch_id)
        if not path.exists():
            return None
        return Batch.from_dict(json.loads(path.read_text()))

    def delete(self, batch_id: str) -> None:
        path = self._path(batch_id)
        if path.exists():
            path.unlink()

    def list_all(self) -> list[Batch]:
        out = []
        for path in sorted(self._dir.glob("*.json")):
            try:
                out.append(Batch.from_dict(json.loads(path.read_text())))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not load batch %s: %s", path.name, exc)
        # Newest first
        out.sort(key=lambda b: b.created_at, reverse=True)
        return out

    # ── Agent ELO state ──────────────────────────────────────────────────

    def load_agent_elo(self) -> AgentEloState:
        return AgentEloState.load(self._elo_state_path)

    def save_agent_elo(self, state: AgentEloState) -> None:
        state.save(self._elo_state_path)

    def reset_agent_elo(self) -> AgentEloState:
        state = AgentEloState(elo=float(INITIAL_ELO), games_played=0, last_result=None)
        self.save_agent_elo(state)
        return state

    # ── Creation ─────────────────────────────────────────────────────────

    def create(self, *, label: str, pool: OpponentPool, total_games: int) -> Batch:
        batch = Batch(
            batch_id=uuid.uuid4().hex,
            label=label,
            pool=pool,
            total_games=total_games,
            status="pending",
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        self.save(batch)
        return batch

    # ── Helpers for building the next CreateGameRequest ──────────────────

    def next_create_request(self, batch: Batch, agent_elo: float) -> tuple[CreateGameRequest, int]:
        """Return (request, opponent_elo) for the next game in the batch.

        Uses the *last completed game's* result (or None if this is the first
        game) to drive the opponent-selection algorithm.
        """
        last_result = None
        if batch.games:
            last_result = batch.games[-1].result  # type: ignore[assignment]
        opp_elo = pick_opponent_elo(agent_elo, last_result, batch.pool)
        opp_config = PlayerConfig(type=batch.pool, elo=opp_elo)
        white = PlayerConfig(type="agent")
        return CreateGameRequest(white=white, black=opp_config), opp_elo


def normalize_result(result_string: str | None, agent_color: str = "white") -> str | None:
    """Public helper duplicating elo.parse_game_result for batch records."""
    return parse_game_result(result_string, agent_color)
