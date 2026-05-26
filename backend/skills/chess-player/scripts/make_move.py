#!/usr/bin/env python3
"""Submit a move for the current game. This actually commits the move on the board.

Usage: make_move.py --uci <move> --reasoning <your note to yourself>

Reads CHESS_API_BASE and CHESS_GAME_ID from environment (injected by AgentPlayer).
POSTs the move to the backend, which validates and applies it immediately.

--reasoning is required. Write whatever you want — it is injected verbatim as
the first message on your NEXT turn so you remember what you did and why.
The move will NOT commit if --reasoning is omitted.

Prints on success:
  {"ok": true, "move": "e2e4", "reasoning": "...", "message": "Move committed. Your turn is over."}

Prints on error (illegal or invalid):
  {"ok": false, "error": "...", "legal_moves": [...]}
"""

import argparse
import json
import os
import sys
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uci", required=True, help="Move in UCI notation, e.g. e2e4")
    parser.add_argument(
        "--reasoning",
        nargs=argparse.REMAINDER,
        default=[],
        help="Your note to yourself about this move (required, free text, no quoting needed)",
    )
    args = parser.parse_args()

    reasoning = " ".join(args.reasoning).strip()
    if not reasoning:
        print(json.dumps({
            "ok": False,
            "error": (
                "Missing --reasoning. You must explain your move — this text is your memory "
                "for the next turn. "
                "Example: --uci e2e4 --reasoning I played e4 to control the center. "
                "Rejected d2d4 (slower). Watch: opponent may push c5. Sequence: none."
            ),
        }))
        sys.exit(1)

    api_base = os.environ.get("CHESS_API_BASE", "http://localhost:8000").rstrip("/")
    game_id = os.environ.get("CHESS_GAME_ID", "")
    if not game_id:
        print(json.dumps({"ok": False, "error": "CHESS_GAME_ID not set"}))
        sys.exit(1)

    url = f"{api_base}/api/games/{game_id}/agent-move"
    payload = json.dumps({"move": args.uci}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
            print(json.dumps({
                "ok": True,
                "move": args.uci,
                "reasoning": reasoning,
                "message": "Move committed. Your turn is over.",
            }))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        try:
            detail = json.loads(body).get("detail", body)
        except Exception:
            detail = body
        # Fetch legal moves to help the model recover
        legal_moves = []
        try:
            with urllib.request.urlopen(
                f"{api_base}/api/games/{game_id}", timeout=5
            ) as r:
                legal_moves = json.loads(r.read().decode()).get("legal_moves", [])
        except Exception:
            pass
        print(json.dumps({
            "ok": False,
            "error": str(detail),
            "legal_moves": legal_moves,
        }))
        sys.exit(1)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"Request failed: {exc}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
