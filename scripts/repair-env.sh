#!/usr/bin/env bash
# Recover from a broken uv venv state.
#
# Root cause: the project path contains an em-dash ("Dokumenter – MacBook Air")
# which Python's .pth processor silently skips. uv's editable installs write
# .pth files with this path, so neither `app` nor `chesscom_driver` end up on
# sys.path even though their .dist-info entries are present.
#
# Fix: symlink both packages directly into site-packages. Symlinks are
# resolved at import time and bypass the .pth processor entirely. uv sync
# does not touch manually-placed symlinks, so this fix persists across syncs.
#
# Run this once after initial uv sync, and again if you ever wipe .venv.
#
# Usage:
#   ./scripts/repair-env.sh

set -euo pipefail

cd "$(dirname "$0")/.."

REPO_ROOT="$(pwd)"
SITE="$REPO_ROOT/.venv/lib/python3.12/site-packages"

echo "Syncing uv workspace …"
uv sync

echo "Symlinking packages into site-packages …"
ln -sfn "$REPO_ROOT/backend/app"             "$SITE/app"
ln -sfn "$REPO_ROOT/backend/chesscom_driver" "$SITE/chesscom_driver"
echo "  app            → $SITE/app"
echo "  chesscom_driver → $SITE/chesscom_driver"

echo "Verifying imports …"
.venv/bin/python -c "from chesscom_driver import ChessComPlayer; from app.main import app; print('  ok')"
