"""Provenance, model identity, and ranked/experimental phase classification.

Two-phase logging policy (see
[knowledge-base/decisions/2026-05-24-ranked-vs-experimental.md]):

- **ranked** runs update `agent_elo.json` and write to `ranked.csv`. A run is
  ranked iff the live chess repo is on `main`. Untracked files (e.g. per-game
  JSON logs) do not disqualify a run; only being on a non-main branch does.
  Feature branches are always experimental.
- **experimental** runs write to `experimental.csv` only. ELO state is not
  touched. This covers ad-hoc lobby games and any batch initiated from a
  feature branch (e.g. while iterating on a PR before merge).

Provenance fields recorded with each game row:

- `branch`: live git branch at game-record time
- `commit_sha`: live git HEAD commit at game-record time (forensic precision)
- `model`, `temperature`: model identity from env + effective sampling temp
- `phase`: "ranked" or "experimental" (derived from `is_ranked_context`)
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from app.config import BACKEND_DIR


logger = logging.getLogger(__name__)


Phase = Literal["ranked", "experimental"]


@dataclass(frozen=True)
class GitState:
    """Snapshot of the chess repo's git state at one point in time.

    Used to (a) stamp provenance onto CSV rows and (b) decide whether the
    current process is allowed to write a ranked game.
    """

    branch: str          # e.g. "main", "feat/foo", "" if not a repo
    commit_sha: str      # full HEAD SHA, "" if not a repo
    dirty: bool          # True if working tree has uncommitted changes
    is_repo: bool        # False if .git is missing

    @property
    def short_sha(self) -> str:
        return self.commit_sha[:8] if self.commit_sha else ""


def _run_git(*args: str) -> tuple[int, str]:
    """Run git with a short timeout. Returns (returncode, stdout-stripped)."""
    repo_root = BACKEND_DIR.parent  # experiments/chess/
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return result.returncode, result.stdout.strip()
    except Exception:  # noqa: BLE001
        return 1, ""


def live_git_state() -> GitState:
    """Read the current git state. Not cached — must reflect live tree."""
    code, sha = _run_git("rev-parse", "HEAD")
    if code != 0:
        return GitState(branch="", commit_sha="", dirty=False, is_repo=False)
    _, branch = _run_git("rev-parse", "--abbrev-ref", "HEAD")
    _, status = _run_git("status", "--porcelain")
    return GitState(
        branch=branch,
        commit_sha=sha,
        dirty=bool(status),
        is_repo=True,
    )


def is_ranked_context() -> tuple[bool, str]:
    """Return (allowed, reason).

    A ranked write is allowed iff:
      - the repo exists, and
      - HEAD is on the `main` branch.

    Untracked files (e.g. per-game JSON logs written during play) do not
    disqualify a run — only being on a non-main branch does. The reason
    string is human-readable and intended for UI / log surfacing.
    """
    state = live_git_state()
    if not state.is_repo:
        return False, "not a git repo"
    if state.branch != "main":
        return False, f"on branch '{state.branch}', not main"
    return True, "main"


def current_phase() -> Phase:
    """Convenience wrapper: 'ranked' iff is_ranked_context() is allowed."""
    allowed, _ = is_ranked_context()
    return "ranked" if allowed else "experimental"


# ── Legacy alias preserved for any code path still calling it ─────────────


@lru_cache
def chess_repo_sha() -> str:
    """Return the chess experiment git HEAD SHA, or "" if not a repo.

    DEPRECATED: prefer ``live_git_state().commit_sha``. This function is
    cached for the process lifetime and so cannot reflect commits that
    arrive after the backend starts; the new logging path reads the live
    git state on each record.
    """
    code, sha = _run_git("rev-parse", "HEAD")
    return sha if code == 0 else ""


def agent_model() -> str:
    """Return the model name from SKILL_AGENT_OPENAI_MODEL (e.g. 'google/gemma-4-31B-it')."""
    return os.getenv("SKILL_AGENT_OPENAI_MODEL", "")


def agent_temperature() -> str:
    # The SDK does not set a temperature on ModelSettings; vLLM/Azure default
    # is 1.0. Recorded as the effective sampling temperature for reproducibility.
    return "1.0"
