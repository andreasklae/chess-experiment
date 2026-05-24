"""Capture provenance fields stamped into every agent game row.

- `skill_repo_sha`: HEAD commit of the chess experiment repo. The skills live
  at `backend/skills/chess-player/`, so the chess repo's HEAD is the unit
  of agent-configuration provenance — every commit advances the experiment.
- `model`, `temperature`: Model name + sampling temperature. The model is
  read from SKILL_AGENT_OPENAI_MODEL; when running locally via eX3 vLLM
  this is typically "google/gemma-4-31B-it". The skillful-agent SDK does
  not currently configure a temperature (see
  knowledge-base/decisions/2026-05-20-elo-and-batch-runner.md), so the
  effective temperature is the server-side default of 1.0. We write "1.0"
  so downstream analysis has the actual sampling temperature recorded,
  not an empty string.
"""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache

from app.config import BACKEND_DIR


@lru_cache
def chess_repo_sha() -> str:
    """Return the chess experiment git HEAD SHA, or "" if not a repo."""
    repo_root = BACKEND_DIR.parent  # experiments/chess/
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def agent_model() -> str:
    """Return the model name from SKILL_AGENT_OPENAI_MODEL (e.g. 'google/gemma-4-31B-it')."""
    return os.getenv("SKILL_AGENT_OPENAI_MODEL", "")


def agent_temperature() -> str:
    # The SDK does not set a temperature on ModelSettings; Azure OpenAI's
    # default for chat completions is 1.0. This value is recorded as the
    # effective sampling temperature for reproducibility.
    return "1.0"
