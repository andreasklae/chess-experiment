#!/usr/bin/env python3
"""Select and submit a move for the current game.

Usage: make_move.py --uci <move>

Reads CHESS_API_BASE and CHESS_GAME_ID from environment (injected by AgentPlayer).
Validates the move against the legal moves list, then prints the chosen UCI to stdout.

The backend (not this script) is responsible for actually applying the move.

Prints on success:
  {"ok": true, "move": "e2e4"}

Prints on error (illegal or invalid):
  {"ok": false, "error": "..."}
"""

import argparse
import json
import os
import sys
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uci", required=True, help="Move in UCI notation, e.g. e2e4")
    args = parser.parse_args()

    api_base = os.environ.get("CHESS_API_BASE", "http://localhost:8000").rstrip("/")
    game_id = os.environ.get("CHESS_GAME_ID", "")
    if not game_id:
        print(json.dumps({"ok": False, "error": "CHESS_GAME_ID not set"}))
        sys.exit(1)

    url = f"{api_base}/api/games/{game_id}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"Could not fetch game state: {exc}"}))
        sys.exit(1)

    legal_moves = data.get("legal_moves", [])
    if args.uci not in legal_moves:
        print(json.dumps({
            "ok": False,
            "error": f"{args.uci!r} is not a legal move. Legal moves: {legal_moves}"
        }))
        sys.exit(1)

    # Declare the move — the backend applies it
    print(json.dumps({"ok": True, "move": args.uci}))


if __name__ == "__main__":
    main()
