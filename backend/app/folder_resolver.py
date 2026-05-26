"""Resolve which subfolder of ``backend/games/`` a game should be written to.

Game files (``<game_id>.json``, ``<game_id>_agent.json``) are organised by
the PR or branch that produced them. This module decides the target folder
and the corresponding ``pr_number`` value for CSV rows.

Resolution order:

1. ``gh pr view --json number,headRefName`` succeeds → use ``headRefName`` as
   the folder and ``number`` as ``pr_number``. This is the steady-state path:
   feature branches with an open or merged PR.
2. ``gh`` not installed or no PR for the current branch → use the live git
   branch name as the folder, leaving ``pr_number`` empty. Lets the agent
   work in branches that haven't been pushed/opened as PRs yet.
3. On ``main`` (no PR detectable on a merge commit yet) → fall back to the
   ``baseline`` folder. The baseline calibration batch lives here; future
   merged-PR games should be rewritten by a one-shot migration when their
   PR number becomes known.

The result is cached for 60 seconds so a batch of games written back-to-back
doesn't hit ``gh`` repeatedly. Cache is process-local — restarting the
backend re-resolves.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass

from app.repo_state import live_git_state


@dataclass(frozen=True)
class TargetFolder:
    folder: str       # subfolder name relative to games_dir, e.g. "baseline" or "my-feature"
    pr_number: str    # PR number as string, or "" when no PR resolvable


_CACHE: tuple[float, TargetFolder] | None = None
_CACHE_TTL_SECONDS = 60.0


def _query_gh_pr() -> TargetFolder | None:
    """Return TargetFolder if `gh pr view` succeeds, else None."""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "number,headRefName"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None
    try:
        data = json.loads(result.stdout)
        return TargetFolder(folder=data["headRefName"], pr_number=str(data["number"]))
    except (json.JSONDecodeError, KeyError):
        return None


def resolve_target_folder(force_refresh: bool = False) -> TargetFolder:
    """Return the folder + pr_number this process should write games to.

    See module docstring for the resolution order. The result is cached for
    60 seconds so repeated calls during a batch are cheap.
    """
    global _CACHE
    now = time.monotonic()
    if not force_refresh and _CACHE is not None:
        cached_at, value = _CACHE
        if now - cached_at < _CACHE_TTL_SECONDS:
            return value

    via_gh = _query_gh_pr()
    if via_gh is not None:
        result = via_gh
    else:
        git = live_git_state()
        if git.branch and git.branch != "main":
            result = TargetFolder(folder=git.branch, pr_number="")
        else:
            result = TargetFolder(folder="baseline", pr_number="")

    _CACHE = (now, result)
    return result


def clear_cache() -> None:
    """Reset the cache. Used by tests that mutate git state mid-process."""
    global _CACHE
    _CACHE = None
