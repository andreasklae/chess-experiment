#!/usr/bin/env bash
# Recover from a broken uv venv state.
#
# Symptoms this fixes:
# - "chess.com players require the chesscom-driver package" at runtime
# - ImportError on pydantic internals
# - any package's .dist-info is present but the module won't import
#
# Root cause: uv sometimes leaves the project's editable installs in a
# broken state after reconciling unrelated packages. Reinstalling the
# editable workspace members restores them.
#
# Usage:
#   ./scripts/repair-env.sh

set -euo pipefail

cd "$(dirname "$0")/.."

echo "Repairing uv environment at $(pwd)/.venv …"
uv sync --reinstall-package chess-experiment-backend --reinstall-package chesscom-driver

echo "Verifying imports …"
.venv/bin/python -c "from chesscom_driver import ChessComPlayer; from app.main import app; print('  ok')"
