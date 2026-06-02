#!/usr/bin/env python3
"""Commit your chosen move for this turn. This is the mandatory closing action.

Arguments (both required):
  move       The move in UCI (e2e4, g1f3, e7e8q) or SAN (e4, Nf3, O-O, e8=Q).
             Trailing + or # is ignored.
  reasoning  Your note to yourself about this move. Required. Free text —
             punctuation, apostrophes, quotes are all fine. The text is
             injected verbatim as the first message on your NEXT turn so you
             remember what you did and why.

Exposed as the tool chess__make_move after use_skill('chess'). Example:
  chess__make_move(move="e2e4", reasoning="Pushed pawn to control the center.")
  chess__make_move(move="Nf3", reasoning="Developed knight; pressures e5.")

Reads CHESS_API_BASE and CHESS_GAME_ID from environment (injected by AgentPlayer).

This script does NOT push the move to the board. It POSTs a commit-intent to
``/api/games/{id}/agent-commit``, which validates the move against the live
board (legality, turn, move shape). The bot loop is the single board writer:
it reads this script's result, parses out the canonical UCI, and pushes the
move under its own lock. That keeps every player (agent, chesscom, maia,
human) on the same contract — players return moves, the bot loop pushes them.

Prints on success:
  {"ok": true, "move": "<canonical-uci>", "reasoning": "...", "message": "Move committed. Your turn is over."}

Prints on failure (illegal move, wrong turn, parse error):
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
                "Missing move. Call with both arguments: the move (UCI or SAN) "
                "and a reasoning note. Example: "
                "chess__make_move(move=\"e2e4\", reasoning=\"Pushed pawn to control center.\")."
            ),
        }))
        sys.exit(1)

    reasoning = " ".join(args.reasoning).strip()
    if not reasoning:
        print(json.dumps({
            "ok": False,
            "error": (
                "Missing reasoning. You must explain your move — this text is your memory "
                "for the next turn. Pass it in the reasoning argument. Example: "
                "chess__make_move(move=\"e2e4\", reasoning=\"I played e4 to control the center. "
                "Rejected d2d4 (slower). Watch: opponent may push c5.\")."
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

    url = f"{api_base}/api/games/{game_id}/agent-commit"
    payload = json.dumps({"move": move_str, "reasoning": reasoning}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
            # The endpoint returns the canonical UCI it validated. Echo that
            # back so AgentPlayer.get_move's tool-result parser sees a string
            # that chess.Move.from_uci can consume without ambiguity.
            canonical = body.get("move", move_str)
            print(json.dumps({
                "ok": True,
                "move": canonical,
                "reasoning": reasoning,
                "message": "Move committed. Your turn is over.",
            }))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        try:
            detail = json.loads(body).get("detail", body)
        except Exception:
            detail = body
        # Fetch legal moves to help the model recover from an illegal move
        # without burning another tool call on list_legal_moves.py.
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
