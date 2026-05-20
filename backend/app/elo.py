"""Agent ELO state, classical Elo update formula, and opponent selection.

Methodology choices recorded in
[knowledge-base/decisions/2026-05-20-elo-and-batch-runner.md].

- K-factor: 32 (online-chess default; aggressive enough to converge within
  ~30 games starting from 1200).
- Initial ELO: 1200.
- Opponent selection: closest available rating strictly above (last won) or
  strictly below (lost or drew) the current agent ELO. Draws round down so
  that a stuck draw streak does not inflate the agent's effective ladder.
- Expected score: standard Elo logistic with 400-point scale.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


K_FACTOR = 32
INITIAL_ELO = 1200

# Maia weights covering the mid-range. Single source of truth referenced from
# `app.schemas.MAIA_ELOS`; duplicated here to avoid an import cycle and to
# make this module self-contained for unit testing.
MAIA_ELOS = (1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900)

# chess.com Engine bot 25 discrete ratings.
CHESSCOM_ELOS = (
    250, 400, 550, 700, 850, 1000, 1100, 1200, 1300, 1400, 1500, 1600,
    1700, 1800, 1900, 2000, 2100, 2200, 2300, 2400, 2500, 2600, 2800, 3000, 3200,
)

OpponentPool = Literal["maia", "chesscom"]
Result = Literal["win", "loss", "draw"]


def expected_score(own: float, opponent: float) -> float:
    """Standard Elo logistic. Returns probability `own` beats `opponent`."""
    return 1.0 / (1.0 + 10.0 ** ((opponent - own) / 400.0))


def update_elo(own: float, opponent: float, result: Result, k: int = K_FACTOR) -> float:
    """Return new own-side ELO after one game."""
    score = {"win": 1.0, "draw": 0.5, "loss": 0.0}[result]
    return own + k * (score - expected_score(own, opponent))


def parse_game_result(result_string: str | None, agent_color: str) -> Result | None:
    """Translate a python-chess result string ("1-0" / "0-1" / "1/2-1/2") into
    a win/loss/draw label from the agent's perspective.

    Returns None for unfinished games or unrecognised results.
    """
    if result_string in (None, "", "*"):
        return None
    if result_string == "1/2-1/2":
        return "draw"
    if result_string == "1-0":
        return "win" if agent_color == "white" else "loss"
    if result_string == "0-1":
        return "loss" if agent_color == "white" else "win"
    return None


def pick_opponent_elo(
    agent_elo: float,
    last_result: Result | None,
    pool: OpponentPool,
) -> int:
    """Choose the next opponent's ELO from the given pool.

    Rules:
    - Won last game: closest opponent rating strictly above `agent_elo`. If
      `agent_elo` is at or above the pool ceiling, return the ceiling.
    - Lost or drew: closest opponent rating strictly below `agent_elo`. If
      `agent_elo` is at or below the pool floor, return the floor.
    - No previous result (first game of a batch): closest available rating to
      `agent_elo` (ties broken downward).
    """
    ratings = MAIA_ELOS if pool == "maia" else CHESSCOM_ELOS
    sorted_ratings = sorted(ratings)

    if last_result == "win":
        above = [r for r in sorted_ratings if r > agent_elo]
        return above[0] if above else sorted_ratings[-1]
    if last_result in ("loss", "draw"):
        below = [r for r in sorted_ratings if r < agent_elo]
        return below[-1] if below else sorted_ratings[0]
    # First game of batch: nearest available.
    return min(sorted_ratings, key=lambda r: (abs(r - agent_elo), r))


# ── Persistent state ─────────────────────────────────────────────────────────


@dataclass
class AgentEloState:
    """Single-source-of-truth ELO state for the agent.

    Persisted to `<games_dir>/agent_elo.json`. The CSV log is an event stream;
    this file is the materialised current state, derivable from the CSV but
    cheaper to read directly.
    """

    elo: float = float(INITIAL_ELO)
    games_played: int = 0
    last_result: Result | None = None

    @classmethod
    def load(cls, path: Path) -> "AgentEloState":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text())
            return cls(
                elo=float(data.get("elo", INITIAL_ELO)),
                games_played=int(data.get("games_played", 0)),
                last_result=data.get("last_result"),
            )
        except Exception:
            return cls()

    def save(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                {
                    "elo": self.elo,
                    "games_played": self.games_played,
                    "last_result": self.last_result,
                },
                indent=2,
            )
        )

    def apply_result(self, opponent_elo: int, result: Result) -> None:
        self.elo = update_elo(self.elo, float(opponent_elo), result)
        self.games_played += 1
        self.last_result = result
