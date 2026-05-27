#!/usr/bin/env python3
"""Submit a move for the current game. This actually commits the move on the board.

Positional args (exactly two):
  move       The move in UCI (e2e4, g1f3, e7e8q) or SAN (e4, Nf3, O-O, e8=Q).
             Trailing + or # is ignored.
  reasoning  Your note to yourself about this move. Required. Free text —
             punctuation, apostrophes, quotes are all fine because the harness
             passes each list element straight to sys.argv. The text is
             injected verbatim as the first message on your NEXT turn so you
             remember what you did and why.

Example:
  run_script("chess", "make_move.py", ["e2e4", "Pushed pawn to control the center."])
  run_script("chess", "make_move.py", ["Nf3", "Developed knight; pressures e5."])

Reads CHESS_API_BASE and CHESS_GAME_ID from environment (injected by AgentPlayer).
POSTs the move to the backend, which validates and applies it.

Prints on success:
  {"ok": true, "move": "<original input>", "reasoning": "...", "message": "Move committed. Your turn is over."}

Prints on error (illegal or invalid):
  {"ok": false, "error": "...", "legal_moves": [...]}
"""

import argparse
import json
import os
import sys
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("move", nargs="?", default="")
    # Capture everything after the move as reasoning. argparse.REMAINDER
    # joins the tail without splitting punctuation; whitespace tokens are
    # rejoined with single spaces below.
    parser.add_argument("reasoning", nargs=argparse.REMAINDER, default=[])
    parser.add_argument("-h", "--help", action="store_true")
    args = parser.parse_args()

    if args.help:
        print(__doc__)
        return

    if not args.move:
        print(json.dumps({
            "ok": False,
            "error": (
                "Missing move. Call with two positional args: the move (UCI or SAN) "
                "and a reasoning note. Example: "
                "run_script(\"chess\", \"make_move.py\", [\"e2e4\", \"Pushed pawn to control center.\"])."
            ),
        }))
        sys.exit(1)

    reasoning = " ".join(args.reasoning).strip()
    if not reasoning:
        print(json.dumps({
            "ok": False,
            "error": (
                "Missing reasoning. You must explain your move — this text is your memory "
                "for the next turn. Pass it as the second positional arg. Example: "
                "run_script(\"chess\", \"make_move.py\", [\"e2e4\", \"I played e4 to control the center. "
                "Rejected d2d4 (slower). Watch: opponent may push c5.\"])."
            ),
        }))
        sys.exit(1)

    api_base = os.environ.get("CHESS_API_BASE", "http://localhost:8000").rstrip("/")
    game_id = os.environ.get("CHESS_GAME_ID", "")
    if not game_id:
        print(json.dumps({"ok": False, "error": "CHESS_GAME_ID not set"}))
        sys.exit(1)

    # Strip trailing check/mate notation — descriptive, not part of move identity.
    move_str = args.move.strip().rstrip("+#")

    url = f"{api_base}/api/games/{game_id}/agent-move"
    payload = json.dumps({"move": move_str}).encode()
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
                "move": args.move,
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
