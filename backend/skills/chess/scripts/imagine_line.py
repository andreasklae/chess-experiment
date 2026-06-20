#!/usr/bin/env python3
"""Imagine a SEQUENCE of moves and watch the position evolve — a multi-ply
look-ahead for planning a maneuver, where chess__imagine_move only sees one ply.

You supply the WHOLE line yourself (your moves AND the opponent's replies you
expect): the tool plays them out on a copy of the board and reports, after each
move, how the position changed — most importantly the lone king's **free region**
(its 'net') and mobility, so you can see whether your plan actually shrinks the
net toward the mating corner. This is calculation YOU drive (the tool searches
nothing and recommends nothing); it just lets you see several moves ahead at
once, which is how the bishop-pair and bishop+knight mates are planned.

The live game is NOT changed — nothing is committed. Use chess__make_move to
play the first move of a line you like.

Arguments:
  moves   Comma-separated moves in UCI or SAN, alternating sides starting with
          YOURS, e.g. "Bd3,Kg7,Bg5,Kf7" or "f1d3,g8g7,c1g5". Required.
  --fen   Start from this position instead of the live game (chain from a FEN a
          previous tool returned).

Exposed as chess__imagine_line after use_skill('chess'). Example:
  chess__imagine_line(moves="Kc3,Ke5,Bd3,Kd5,Ne3,Ke5")

If a move in the line is illegal, the tool reports which one and why, and shows
the position reached just before it.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import chess

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from _eval import (  # noqa: E402
    bishop_corner_targets,
    classify_illegal_move,
    king_free_region,
    parse_move,
    render_king_net,
)
from _live import board_with_history, fetch_state  # noqa: E402


def _lone_king_color(board: chess.Board):
    """Colour reduced to king (+ pawns) while the other side has pieces, else None."""
    for color in (chess.WHITE, chess.BLACK):
        force = sum(len(board.pieces(pt, color))
                    for pt in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT))
        other = sum(len(board.pieces(pt, not color))
                    for pt in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT))
        if force == 0 and other > 0:
            return color
    return None


def _king_mobility(board: chess.Board, color: bool) -> int:
    b = board.copy(stack=False)
    if b.turn != color:
        try:
            b.push(chess.Move.null())
        except (AssertionError, ValueError):
            return 0
    ksq = board.king(color)
    return sum(1 for m in b.legal_moves if m.from_square == ksq)


def _stats(board: chess.Board) -> str:
    """One-line geometry readout focused on a lone-king mate: net size, the
    lone king's mobility, and its distance to the nearest target corner."""
    lk = _lone_king_color(board)
    if lk is None:
        return ""
    winner = not lk
    region = len(king_free_region(board, lk))
    mob = _king_mobility(board, lk)
    corners = bishop_corner_targets(board, winner)
    ek = board.king(lk)
    cd = min(chess.square_distance(ek, c) for c in corners) if ek is not None else "-"
    return f"net={region} kingmoves={mob} corner_dist={cd}"


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
              "Missing moves. Call e.g. chess__imagine_line(moves=\"Kc3,Ke5,Bd3\")."}))
        sys.exit(1)

    if args.fen:
        try:
            board = chess.Board(args.fen)
        except ValueError:
            board = board_with_history(fetch_state())
    else:
        board = board_with_history(fetch_state())

    tokens = [t.strip() for t in args.moves.replace(" ", ",").split(",") if t.strip()]
    lines = ["# Imagine line", "", f"Start: `{board.fen()}`", "",
             f"Start position — {_stats(board) or 'not a lone-king ending'}", ""]
    rows = ["| # | side | move | net | kmoves | corner_d | flag |",
            "|---|------|------|-----|--------|----------|------|"]
    for i, tok in enumerate(tokens, 1):
        try:
            mv = parse_move(board, tok)
        except ValueError as exc:
            lines.append(f"⚠ move {i} (`{tok}`) is illegal in the position "
                         f"reached: {exc}")
            lines.append(f"Position reached before it: `{board.fen()}`")
            break
        san = board.san(mv)
        mover = "white" if board.turn == chess.WHITE else "black"
        board.push(mv)
        flag = ("mate" if board.is_checkmate() else "stalemate" if board.is_stalemate()
                else "check" if board.is_check() else "")
        st = _stats(board)
        net = mob = cd = "-"
        if st:
            parts = dict(p.split("=") for p in st.split())
            net, mob, cd = parts.get("net", "-"), parts.get("kingmoves", "-"), parts.get("corner_dist", "-")
        rows.append(f"| {i} | {mover} | {san} | {net} | {mob} | {cd} | {flag} |")
        if board.is_checkmate() or board.is_stalemate():
            break

    lines += rows
    lines += ["", "Final position:", "```", render_king_net(board, _lone_king_color(board), None)
              if _lone_king_color(board) is not None else board.unicode(), "```",
              f"FEN: `{board.fen()}`",
              "", "_Read the net column: it should fall toward the corner. This is your "
              "own calculation — nothing here is a recommendation._"]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
