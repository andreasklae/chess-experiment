#!/usr/bin/env python3
"""Imagine a SHORT LINE of moves and see the position at its end — a multi-ply
look-ahead for planning, where chess__imagine_move only sees one ply.

Use it ONE MOVE AT A TIME. Do NOT type a whole 5-move line up front: add a
single move, read the result, then decide the next move. You may **branch**
(change the last move and call again) and **backtrack** (drop moves from the
end). The line is at most **5 moves (plies) ahead** — that is the planning
horizon; beyond it, commit a move and re-plan.

You supply the moves yourself (yours AND the opponent's replies you expect),
alternating, starting with YOUR move. The tool plays them on a copy of the
board and shows, for the LAST move of the line, the SAME full report as
chess__imagine_move (check/mate, material, the moved piece's safety, newly
hanging pieces, the legal replies, and basic-mate confinement facts). A
breadcrumb of the line so far is shown above it.

This is calculation YOU drive — the tool searches nothing and recommends
nothing. The live game is NOT changed; nothing is committed. When you like a
line, play its FIRST move with chess__make_move.

Perspective: when the last move of the line is the OPPONENT's, the report is
shown from their side with a clear banner — 'replies' there are then YOUR
options, and 'enemy king mobility' is your own king's.

Arguments:
  moves   Comma/space-separated moves in UCI or SAN, alternating, starting with
          YOURS. 1-5 plies. e.g. "Bd3,Kg7,Bg5" or "f1d3 g8g7 c1g5".
  --fen   Start from this position instead of the live game (chain from a FEN a
          previous tool returned).

Exposed as chess__imagine_line after use_skill('chess'). Example:
  chess__imagine_line(moves="Kc3")          # one move at a time
  chess__imagine_line(moves="Kc3,Ke5,Bd3")  # extend, having seen Kc3's result
"""

import argparse
import json
import sys
from pathlib import Path

import chess

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from _eval import parse_move  # noqa: E402
from _live import board_with_history, fetch_state  # noqa: E402
from imagine_move import render_imagine  # noqa: E402

_MAX_PLIES = 5


def _flag(board: chess.Board) -> str:
    if board.is_checkmate():
        return "#"
    if board.is_stalemate():
        return "stalemate"
    if board.move_stack and (
        board.can_claim_threefold_repetition() or board.can_claim_fifty_moves()
    ):
        return "draw"
    if board.is_check():
        return "+"
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--fen", default=None)
    parser.add_argument("moves", nargs="?", default="")
    parser.add_argument("-h", "--help", action="store_true")
    args = parser.parse_args()

    if args.help:
        print(__doc__)
        return
    if not args.moves.strip():
        print(json.dumps({"ok": False, "error":
              "Missing moves. Imagine ONE move at a time, e.g. "
              "chess__imagine_line(moves=\"Kc3\"); then extend it move by move "
              "(max 5 ahead)."}))
        sys.exit(1)

    if args.fen:
        try:
            board = chess.Board(args.fen)
        except ValueError:
            board = board_with_history(fetch_state())
    else:
        board = board_with_history(fetch_state())

    agent_color = board.turn  # the side to move on the live/start board = you
    tokens = [t.strip() for t in args.moves.replace(" ", ",").split(",") if t.strip()]

    if len(tokens) > _MAX_PLIES:
        print(json.dumps({"ok": False, "error":
              f"Too many moves ({len(tokens)}). Imagine at most {_MAX_PLIES} "
              f"ahead, ONE move at a time: add a single move, read the result, "
              f"then decide the next. Drop moves to backtrack; change the last "
              f"move to branch."}))
        sys.exit(1)

    # Apply all but the last move silently; render the LAST move in full.
    breadcrumb: list[str] = []
    last_move = None
    board_before_last = None
    for i, tok in enumerate(tokens, 1):
        try:
            mv = parse_move(board, tok)
        except ValueError as exc:
            print("\n".join([
                "# Imagine line",
                "",
                "Breadcrumb: " + (" ".join(breadcrumb) if breadcrumb else "(none)"),
                "",
                f"⚠ Move {i} (`{tok}`) is illegal in the position reached: {exc}",
                f"Position reached before it: `{board.fen()}`",
                "Fix that move (or backtrack) and call again — one move at a time.",
            ]))
            sys.exit(1)
        side = "W" if board.turn == chess.WHITE else "B"
        san = board.san(mv)
        if i == len(tokens):
            board_before_last = board.copy()
            last_move = mv
        board.push(mv)
        breadcrumb.append(f"{i}.{side} {san}{_flag(board)}")
        if board.is_checkmate() or board.is_stalemate():
            # The line ends here regardless of remaining tokens.
            if i < len(tokens):
                breadcrumb.append(f"(line ends — {_flag(board) or 'game over'})")
            board_before_last = board_before_last if last_move else None
            break

    out = [
        "# Imagine line  (your own calculation — nothing committed)",
        "",
        f"Line: {' '.join(breadcrumb)}",
        "",
        f"_Showing the full report for the LAST move below. Extend ONE move at a "
        f"time (max {_MAX_PLIES} ahead); change the last move to branch, drop "
        f"moves to backtrack._",
        "",
        "---",
        "",
    ]
    if last_move is not None and board_before_last is not None:
        out.append(render_imagine(board_before_last, last_move, agent_color=agent_color))
    else:
        out.append("_(no move rendered)_")
    print("\n".join(out))


if __name__ == "__main__":
    main()
