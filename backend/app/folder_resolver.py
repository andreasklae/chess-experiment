"""Resolve which subfolder of ``backend/games/`` a game should be written to.

Game files (``<game_id>.json``, ``<game_id>_agent.json``) are organised by
the PR or branch that produced them. This module decides the target folder
and the corresponding ``pr_number`` value for CSV rows.

Resolution order:

1. ``gh pr view --json number,headRefName`` succeeds → use ``headRefName``
   as the folder and ``number`` as ``pr_number``. This is the steady-state
   path: feature branches with an open or merged PR.
2. On ``main`` (a merged-PR commit, ``gh pr view`` fails because the
   working branch isn't a PR head anymore) → look back through the recent
   ``main`` history for a "Merge pull request #N from <owner>/<branch>"
   commit and use ``<branch>`` as the folder + ``N`` as ``pr_number``.
   This covers calibration batches run on ``main`` post-merge.
3. ``gh`` not installed and not on ``main`` → use the live branch name as
   the folder, leaving ``pr_number`` empty.
4. Last resort (no git, no PRs ever merged) → ``baseline`` folder.
   ``baseline/`` is also the explicit home for pre-PR ranked games; new
   writes only land there when there's no merged-PR signal at all.

The result is cached for 60 seconds so a batch of games written back-to-back
doesn't re-shell to git. Cache is process-local — restarting the backend
re-resolves.
"""

from __future__ import annotations

import json
import re
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


# Match git's default merge-commit subject:
#   ``Merge pull request #123 from owner/branch-name``
# Captures (pr_number, branch_name). The owner/ prefix is optional because
# squash-merges and rebase-merges via the GitHub UI can produce different
# variants — we accept any token after ``from `` and split on ``/``.
_MERGE_RE = re.compile(
    r"Merge pull request #(?P<num>\d+) from (?:[^/\s]+/)?(?P<branch>\S+)"
)


def _query_merged_pr() -> TargetFolder | None:
    """When ``gh pr view`` fails (typical on ``main`` post-merge), scan the
    recent ``main`` history for the latest ``Merge pull request`` commit and
    return its (branch, pr_number). This keeps post-merge calibration
    batches writing into the just-merged PR's folder rather than into
    ``baseline/``.
    """
    try:
        result = subprocess.run(
            ["git", "log", "--max-count=50", "--pretty=%s", "main"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None
    for line in result.stdout.splitlines():
        m = _MERGE_RE.search(line)
        if m:
            return TargetFolder(folder=m.group("branch"), pr_number=m.group("num"))
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
            # Feature branch with no open PR — fall back to branch name.
            result = TargetFolder(folder=git.branch, pr_number="")
        else:
            # On main (or no git): try to use the most recent merged PR.
            via_merge = _query_merged_pr()
            if via_merge is not None:
                result = via_merge
            else:
                result = TargetFolder(folder="baseline", pr_number="")

    _CACHE = (now, result)
    return result


def clear_cache() -> None:
    """Reset the cache. Used by tests that mutate git state mid-process."""
    global _CACHE
    _CACHE = None
