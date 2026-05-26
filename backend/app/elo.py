"""Agent ELO state, classical Elo update formula, and opponent selection.

Methodology choices recorded in
[knowledge-base/decisions/2026-05-20-elo-and-batch-runner.md] (initial design)
and the 2026-05-20 update covering adaptive K and streak-based opponent
stepping (same file, "Matchmaking strategy" section).

In brief:

- Classical Elo update. K is *adaptive*: 40 for the first
  `PROVISIONAL_GAMES` games (FIDE's provisional-player rule), then 20.
- Initial ELO 1200 (revised upward from 600; see decisions/2026-05-25-initial-elo-1200.md).
- Opponent selection uses **streak-based stepping** on the discrete pool
  (Maia 9-rating grid, chess.com 25-rating grid). A run of consecutive
  wins doubles the step up the ladder; a run of losses doubles the step
  down. Single results (no streak) step one notch in the natural direction.
  This is the cheap-and-defensible version of exponential search and
  matches how online "rating calibration" tournaments behave.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


# ── Constants ────────────────────────────────────────────────────────────────

INITIAL_ELO = 1200

# Adaptive K-factor: high during the calibration phase so the rating moves
# fast, then drops to a stable value matching common online-chess defaults
# (chess.com casual K=20; FIDE for established players is also in this band).
K_PROVISIONAL = 40
K_STABLE = 20
PROVISIONAL_GAMES = 15

# Maia weights covering the mid-range. Duplicated from app.schemas.MAIA_ELOS
# to keep this module self-contained for unit testing.
MAIA_ELOS = (1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900)

# chess.com Engine bots selectable in this experiment. Bottom 3 positions
# (250, 400, 550) excluded — see knowledge-base/decisions/2026-05-25-chesscom-pool-floor.md.
# Must match app.schemas.CHESSCOM_ELOS.
CHESSCOM_ELOS = (
    700, 850, 1000, 1100, 1200, 1300, 1400, 1500, 1600,
    1700, 1800, 1900, 2000, 2100, 2200, 2300, 2400, 2500, 2600, 2800, 3000, 3200,
)

OpponentPool = Literal["maia", "chesscom"]
Result = Literal["win", "loss", "draw"]


# ── Rating update ────────────────────────────────────────────────────────────


def k_factor(games_played: int) -> int:
    """Adaptive K-factor — high for the first PROVISIONAL_GAMES games, then
    stable. Mirrors the FIDE provisional-player rule used for unrated entrants.
    """
    return K_PROVISIONAL if games_played < PROVISIONAL_GAMES else K_STABLE


def expected_score(own: float, opponent: float) -> float:
    """Standard Elo logistic. Returns probability `own` beats `opponent`."""
    return 1.0 / (1.0 + 10.0 ** ((opponent - own) / 400.0))


def update_elo(own: float, opponent: float, result: Result, k: int) -> float:
    """Return new own-side ELO after one game.

    Caller supplies K explicitly — usually via `k_factor(games_played)`.
    Keeping K as a parameter (instead of looking it up here) keeps this
    function pure and testable.
    """
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


# ── Streak bookkeeping ───────────────────────────────────────────────────────


def update_streak(streak: int, result: Result) -> int:
    """Apply a result to the running win/loss streak.

    Convention: positive streak = consecutive wins, negative = consecutive
    losses. Draws decay the streak toward zero (halving), so a single draw
    in the middle of a long win streak doesn't fully reset the search.

    - Win after wins  : streak + 1
    - Loss after losses: streak - 1
    - Win after losses: reset to +1 (direction flipped)
    - Loss after wins: reset to -1 (direction flipped)
    - Draw: streak //= 2 (toward zero); a draw at streak 0 stays at 0
    """
    if result == "win":
        return streak + 1 if streak >= 0 else 1
    if result == "loss":
        return streak - 1 if streak <= 0 else -1
    # draw — pull half-way toward zero
    if streak > 0:
        return streak // 2
    if streak < 0:
        return -((-streak) // 2)
    return 0


def step_from_streak(streak: int) -> int:
    """How many pool-grid notches to move based on the current streak.

    Always one notch in the direction of the streak. Replaces the
    previous doubling policy (1, 2, 4, capped at 4) which was too
    aggressive at the bottom of the chess.com pool, where notches are
    150 ELO apart — a streak of 2 wins jumped from chesscom-700 past
    chesscom-850 straight to chesscom-1000, a 300-point gap from an
    agent rated ~700. The doubling was useful for the original 1200→300
    descent during initial calibration but is wrong for steady-state
    matchmaking around the agent's actual rating.

    Zero streak (only after a streak-resetting draw) returns 0 — caller
    treats that as "stay at the same opponent."
    """
    if streak == 0:
        return 0
    return 1 if streak > 0 else -1


# ── Opponent selection ──────────────────────────────────────────────────────


def pick_opponent_elo(
    agent_elo: float,
    streak: int,
    pool: OpponentPool,
) -> int:
    """Choose the next opponent's ELO from the given pool.

    Strategy:
    - The agent's current ELO is anchored to the nearest pool rating
      (ties round down). That's the "where we are now" position.
    - `step_from_streak(streak)` says how many grid notches to move from
      that anchor: positive for wins, negative for losses, zero after a
      draw that nulled the streak.
    - First game of a batch (streak=0, never played) anchors at the
      nearest rating.

    Clamps to the pool's floor/ceiling.
    """
    ratings = MAIA_ELOS if pool == "maia" else CHESSCOM_ELOS
    sorted_ratings = sorted(ratings)
    # Anchor to the nearest grid point.
    anchor_idx = min(
        range(len(sorted_ratings)),
        key=lambda i: (abs(sorted_ratings[i] - agent_elo), sorted_ratings[i]),
    )
    step = step_from_streak(streak)
    new_idx = max(0, min(len(sorted_ratings) - 1, anchor_idx + step))
    return sorted_ratings[new_idx]


# ── Persistent state ─────────────────────────────────────────────────────────


@dataclass
class AgentEloState:
    """Single-source-of-truth ELO state for the agent.

    Persisted to `<games_dir>/agent_elo.json`. The CSV log is an event
    stream; this file is the materialised current state, derivable from
    the CSV but cheaper to read directly.

    Fields:
    - `elo` — current rating after the last game.
    - `games_played` — count for K-factor adaptation.
    - `last_result` — most recent W/L/D (for the UI; matchmaking uses
      `streak`).
    - `streak` — signed streak counter driving opponent step. See
      `update_streak` / `step_from_streak`.
    """

    elo: float = float(INITIAL_ELO)
    games_played: int = 0
    last_result: Result | None = None
    streak: int = 0

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
                streak=int(data.get("streak", 0)),
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
                    "streak": self.streak,
                },
                indent=2,
            )
        )

    def apply_result(self, opponent_elo: int, result: Result) -> None:
        k = k_factor(self.games_played)
        self.elo = update_elo(self.elo, float(opponent_elo), result, k)
        self.games_played += 1
        self.last_result = result
        self.streak = update_streak(self.streak, result)
