#!/usr/bin/env python3
"""List all legal moves in the current position, annotated with SAN, a short
human description, and a tactical flag (check / checkmate / stalemate).

Reads CHESS_API_BASE and CHESS_GAME_ID from environment (injected by
AgentPlayer). No arguments needed.

Output is a markdown table:

    | UCI    | SAN    | Description                       | Flag       |
    |--------|--------|-----------------------------------|------------|
    | e2e4   | e4     | pawn to e4                        |            |
    | g1f3   | Nf3    | knight to f3                      |            |
    | f1c4   | Bxc4   | bishop takes knight on c4         |            |
    | d1h5   | Qh5+   | queen to h5                       | check      |

The UCI strings in the first column (or the SAN strings in the second) are
ready to pass as the move argument to `make_move.py` or `imagine_move.py`.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

import chess


_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from _eval import render_moves_table  # noqa: E402


def main() -> None:
    api_base = os.environ.get("CHESS_API_BASE", "http://localhost:8000").rstrip("/")
    game_id = os.environ.get("CHESS_GAME_ID", "")
    if not game_id:
        print("error: CHESS_GAME_ID not set", file=sys.stderr)
        sys.exit(1)

    url = f"{api_base}/api/games/{game_id}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    fen = data.get("fen")
    if not fen:
        print("error: backend response missing 'fen'", file=sys.stderr)
        sys.exit(1)

    board = chess.Board(fen)
    legal = list(board.legal_moves)
    if not legal:
        print(f"_(no legal moves — {'checkmate' if board.is_checkmate() else 'stalemate'})_")
        return
    print(f"_{len(legal)} legal moves_:")
    print()
    print(render_moves_table(board, legal))


if __name__ == "__main__":
    main()
