#!/usr/bin/env python3
"""List all legal moves for the current game position.

Reads CHESS_API_BASE and CHESS_GAME_ID from environment (injected by AgentPlayer).

Prints a JSON array of UCI move strings to stdout, e.g.:
  ["e2e4", "d2d4", "g1f3", ...]
"""

import json
import os
import sys
import urllib.request


def main() -> None:
    api_base = os.environ.get("CHESS_API_BASE", "http://localhost:8000").rstrip("/")
    game_id = os.environ.get("CHESS_GAME_ID", "")
    if not game_id:
        print(json.dumps({"error": "CHESS_GAME_ID not set"}))
        sys.exit(1)

    url = f"{api_base}/api/games/{game_id}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)

    moves = data.get("legal_moves", [])
    print(json.dumps(moves))


if __name__ == "__main__":
    main()
