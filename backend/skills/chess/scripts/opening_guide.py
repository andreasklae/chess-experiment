#!/usr/bin/env python3
"""chess__opening_guide — point me at the right London theory page for this position.

Looks at the current position and names the `openings/` wiki page that fits what is
happening (Black just played ...Qb6 / ...Nh5 / ...g6, your bishop aims at h7, or you
still need to finish the setup), with the exact `read_reference` call. It does NOT pick
a move — it routes you to the prepared theory so you can read the plan and decide. Pair
it with `chess__opening_book` (which gives the memorised move where one exists).

Use it in the opening when you are unsure what to do or what Black's move means. Pure
mechanics (which pieces are where); no engine.

No arguments — reads the live position. (Offline: pass --fen "<FEN>".)
"""

import argparse
import sys
from pathlib import Path

import chess

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def _is(board, sq, ptype, color) -> bool:
    p = board.piece_at(sq)
    return p is not None and p.piece_type == ptype and p.color == color


def _ref(path: str) -> str:
    return f'`read_reference(skill_name="chess", path="{path}")`'


def routes(board: chess.Board) -> list[tuple[str, str, str]]:
    """List (situation, page, why) for every London theory page that applies now,
    most specific (a Black trigger) first. Mechanics only."""
    W, B = chess.WHITE, chess.BLACK
    out: list[tuple[str, str, str]] = []

    # --- specific Black triggers ---
    if _is(board, chess.B6, chess.QUEEN, B) and board.attackers(B, chess.B2):
        out.append(("Black's ...Qb6 attacks your loose b2-pawn",
                    "openings/london-vs-qb6",
                    "the right defence is move-order-dependent (Qb3 only works after c3)"))
    if _is(board, chess.H5, chess.KNIGHT, B) and (
            board.attackers(B, chess.F4) or board.attackers(B, chess.G3)):
        out.append(("Black's ...Nh5 attacks your dark-squared bishop",
                    "openings/london-vs-nh5",
                    "save the bishop: Bh2 (if h3 in) / Bg5 / allow ...Nxg3 hxg3"))
    if _is(board, chess.G6, chess.PAWN, B):
        out.append(("Black is fianchettoing (...g6, King's Indian setup)",
                    "openings/london-vs-kings-indian",
                    "use Be2 not Bd3, and get h3 in"))

    # --- your attacking resource: Bd3 pointing at h7, Black castled, no Nf6 ---
    if _is(board, chess.D3, chess.BISHOP, W) and _is(board, chess.G8, chess.KING, B):
        no_f6_knight = not _is(board, chess.F6, chess.KNIGHT, B)
        flag = "the Greek-gift CHECKLIST may apply" if no_f6_knight else \
               "(but Black has a knight on f6, so Bxh7+ likely just loses — check anyway)"
        out.append(("your Bd3 aims at h7 and Black has castled",
                    "openings/london-bxh7-greek-gift",
                    f"before ANY Bxh7+ sacrifice, {flag}"))

    # --- always-available hub when still in the opening setup ---
    setup_done = (not _is(board, chess.C1, chess.BISHOP, W)  # dark bishop developed
                  and board.has_castling_rights(W) is False)
    if not setup_done:
        out.append(("you are still building the London setup",
                    "openings/london-system",
                    "the setup order (Bf4 before e3, then e3/Nf3/Bd3/c3/Nbd2/O-O) + the Ne5 plan"))
    return out


def render(board: chess.Board) -> str:
    if board.turn != chess.WHITE:
        return "_Not White to move — the opening guide covers White's London repertoire._"
    rs = routes(board)
    if not rs:
        return ("_No specific London theory page flagged for this position._ You are likely "
                "out of the opening — assess with `chess__show_position` and play on your own. "
                "For the general setup, read " + _ref("openings/london-system") + ".")
    lines = ["**London theory for this position — read the page that fits:**", ""]
    for situation, page, why in rs:
        lines.append(f"- **{situation}** → {_ref(page)}  ({why})")
    lines += ["", "_These point you at the prepared plan; you still choose the move. "
              "`chess__opening_book` gives the memorised move where one exists._"]
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
