#!/usr/bin/env python3
"""chess__opening_book — the move from our prepared London opening book, if any.

This is the agent's *memorised opening theory*: a finite, tutor-authored repertoire
(see `_opening_book.py`). Given the current position, it returns the book move(s) for
White WITH the line name and the idea behind it — exactly what a human who has studied
the London "knows" to play. It is NOT an engine: it only answers for positions in the
book, and out of book it tells you so and points you at the theory pages. It never
searches or evaluates to pick a move.

Use it on your move in the opening: if there is a book move, you can play it (it is
prepared theory), but you still decide — read the idea and sanity-check it fits. Once
out of book, think for yourself / consult the openings wiki.

No arguments — reads the live position. (Offline: pass --fen "<FEN>".)
"""

import argparse
import sys
from pathlib import Path

import chess

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import _opening_book as book  # noqa: E402


def _route_out_of_book(board: chess.Board) -> str:
    """When the position is not in book, point at the matching theory page (the
    opening_guide does the full routing; here we give a short hint)."""
    hints = []
    bq_b6 = board.piece_at(chess.B6)
    if bq_b6 and bq_b6.piece_type == chess.QUEEN and bq_b6.color == chess.BLACK:
        hints.append("Black's ...Qb6 hits b2 → read `openings/london-vs-qb6`")
    nh5 = board.piece_at(chess.H5)
    if nh5 and nh5.piece_type == chess.KNIGHT and nh5.color == chess.BLACK:
        hints.append("...Nh5 hits your bishop → read `openings/london-vs-nh5`")
    g6 = board.piece_at(chess.G6)
    if g6 and g6.piece_type == chess.PAWN and g6.color == chess.BLACK:
        hints.append("Black fianchettoed (...g6) → read `openings/london-vs-kings-indian`")
    bd3 = board.piece_at(chess.D3)
    if bd3 and bd3.piece_type == chess.BISHOP and bd3.color == chess.WHITE:
        hints.append("your Bd3 aims at h7 — before any Bxh7+ read `openings/london-bxh7-greek-gift`")
    return "\n".join(f"- {h}" for h in hints)


def render(board: chess.Board) -> str:
    if board.turn != chess.WHITE:
        return ("_Not White to move — the opening book only covers White's repertoire._")
    entry = book.lookup(board)
    if entry is None:
        out = ["**Out of book.** This position is not in our prepared London repertoire — "
               "play it yourself (use `chess__show_position` and the `openings/` wiki). "
               "An opening book is memorised theory, not a calculator; past the book you "
               "are on your own."]
        hint = _route_out_of_book(board)
        if hint:
            out += ["", "Relevant theory:", hint]
        return "\n".join(out)

    moves = entry.moves
    tag = "line" if entry.source == "line" else "setup rule"
    head = (f"**Book move: {moves[0]}**" if len(moves) == 1
            else f"**Book moves: {', '.join(moves)}** (any is theory; pick by the idea)")
    lines = [
        head,
        f"_Line:_ {entry.line}  ·  _({tag})_",
        f"_Idea:_ {entry.idea}",
        "",
        "This is prepared theory — you may play it, but it is YOUR decision: read the "
        "idea, confirm it fits, then commit with `chess__make_move`. When the position "
        "leaves the book, `chess__opening_book` will say so.",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--fen", default=None)
    ap.add_argument("-h", "--help", action="store_true")
    args = ap.parse_args()
    if args.help:
        print(__doc__); return
    if args.fen:
        board = chess.Board(args.fen)
    else:
        from _live import board_with_history, fetch_state  # noqa: E402
        board = board_with_history(fetch_state())
    print(render(board))


if __name__ == "__main__":
    main()
