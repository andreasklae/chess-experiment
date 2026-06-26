#!/usr/bin/env python3
"""Imagine a SHORT LINE of moves and see the position at its end — a multi-ply
look-ahead for planning, where chess__imagine_move only sees one ply.

Use it ONE MOVE AT A TIME. Do NOT type a whole 5-move line up front: add a
single move, read the result, then decide the next move. You may **branch**
(change the last move and call again) and **backtrack** (drop moves from the
end). The line is at most **8 moves (plies) ahead** — that is the planning
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

# Planning horizon. Raised 5 → 8 (2026-06-27): forced lines — especially
# endgame checks and mating nets — routinely run longer than 5 plies, and the
# agent was hitting the cap mid-combination and abandoning sound sacrifices. 8
# plies still fits the context budget (only the LAST move renders a full report;
# earlier plies collapse to the breadcrumb).
_MAX_PLIES = 8


def _testing_replies(board: chess.Board, exclude: chess.Move | None = None,
                     k: int = 3) -> list[str]:
    """Up to k of the side-to-move's most TESTING replies (checks first, then
    captures, then the rest) as SAN — the moves worth branching into. Pure
    rules: check/capture flags only, no evaluation."""
    moves = [m for m in board.legal_moves if m != exclude]

    def rank(m: chess.Move) -> int:
        return -((2 if board.gives_check(m) else 0) + (1 if board.is_capture(m) else 0))

    moves.sort(key=rank)
    return [board.san(m) for m in moves[:k]]


_MAT_VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}


def _material(board: chess.Board, color: bool) -> int:
    return sum(_MAT_VAL[pt] * len(board.pieces(pt, color))
               for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN))


def _leaf_verdict(start: chess.Board, leaf: chess.Board, agent_color: bool) -> str:
    """State the OUTCOME at the end of the calculated line, as facts a human would
    read off the final position: is it forced mate, and what is the net material
    swing (start → leaf) from the agent's side. This is the result of the agent's
    OWN calculation — not an engine verdict, not a move recommendation. The agent
    still has to choose the line because it now understands the resulting
    position. (A line is 'forced' only as far as the agent supplied the opponent's
    replies; the branch nudges below remind it to test the alternatives.)"""
    # Mate / stalemate at the leaf.
    if leaf.is_checkmate():
        # whoever is to move is mated
        mated = leaf.turn
        if mated != agent_color:
            return ("✅ **THIS LINE ENDS IN CHECKMATE — you mate the opponent.** If every "
                    "opponent reply in it was forced (their only legal/safe move), this WINS: "
                    "play the first move. Re-check that each of their replies was truly forced.")
        return ("⛔ **THIS LINE ENDS IN CHECKMATE AGAINST YOU.** Do not play it — backtrack and "
                "find another move.")
    if leaf.is_stalemate():
        return ("⚠ **THIS LINE ENDS IN STALEMATE (draw).** If you are winning, avoid it; "
                "backtrack and keep a move for the opponent.")
    # Material tally start → leaf, agent-relative.
    start_diff = _material(start, agent_color) - _material(start, not agent_color)
    leaf_diff = _material(leaf, agent_color) - _material(leaf, not agent_color)
    swing = leaf_diff - start_diff
    sign = "+" if leaf_diff >= 0 else "−"
    swing_txt = (f"you GAIN ~{swing}" if swing > 0
                 else (f"you LOSE ~{-swing}" if swing < 0 else "material is unchanged"))
    verdict = (
        f"**End-of-line material (count it yourself): {sign}{abs(leaf_diff)} for you** "
        f"(start was {'+' if start_diff>=0 else '−'}{abs(start_diff)}; over this line {swing_txt}). "
    )
    # Is the ENEMY king nearly mated at this leaf? Count its escape squares (give
    # it the move). A boxed king (≤1 square) means this is a MATING ATTACK in
    # progress — material is the wrong yardstick here, and a "you're down
    # material, backtrack" verdict would wrongly abandon a forced mate that is
    # just 1–2 moves further (mate-in-3+). This is the key fix for the agent
    # bailing out of a winning sacrifice mid-line.
    enemy_king = leaf.king(not agent_color)
    king_escapes = None
    if enemy_king is not None:
        # count the enemy king's own legal moves; give it the move if it's not
        # already its turn (so we measure how boxed the king is regardless of
        # whose move the leaf is).
        if leaf.turn == (not agent_color):
            probe = leaf
        else:
            probe = leaf.copy(stack=False)
            try:
                probe.push(chess.Move.null())
            except Exception:
                probe = None
        if probe is not None:
            king_escapes = sum(1 for m in probe.legal_moves if m.from_square == enemy_king)

    # A king with ≤1 escape square is in a mating net. A forced mate DOMINATES any
    # material assessment — whether the agent is up, even, or down material at the
    # leaf — so when the king is that boxed, lead with "keep hunting the mate"
    # regardless of the material swing. (Down-material bailout AND up-material
    # complacency both make the agent stop short of a mate one move further:
    # jJAE7 Qxf7+ Kh8 [0 escapes, +1 material] Qf8+ Rxf8 Rxf8#.)
    mating_attack = king_escapes is not None and king_escapes <= 1

    if mating_attack:
        verdict += (
            f"**⚠ The enemy king is nearly mated here — only {king_escapes} escape square(s).** This is "
            f"a MATING ATTACK: material is NOT the yardstick — KEEP EXTENDING the line (add your next "
            f"forcing check) and hunt for CHECKMATE a move or two further. Do not settle for the "
            f"material count (up OR down) while the king is boxed; a mate is worth any material."
        )
    elif swing > 0:
        verdict += ("This line WINS material if the opponent's replies were forced — but a one-ply "
                    "loss earlier in the line can still be regained later, so trust the END count, "
                    "not the scary middle. Verify each opponent reply was their best.")
    elif swing < 0:
        verdict += ("You end down material here — unless this leaf is a forced mate/winning attack "
                    "you can name, this line is bad; backtrack.")
    else:
        verdict += ("Even material — decide on position (king safety, activity), or look for a "
                    "more forcing line.")
    return verdict


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
    start_board = board.copy()  # snapshot for the start→leaf material tally
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
        # The verdict at the END of the line you calculated — the material count
        # and mate status a human would read off the final position. It is the
        # result of YOUR calculation, not an engine's recommendation; you still
        # choose the move because you now see why the resulting position is good.
        _leaf_verdict(start_board, board, agent_color),
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
        # Branching nudge: do NOT trust a single line. Push the agent to test
        # the opponent's OTHER reasonable replies. (Skip when the line ended the
        # game.) Two cases by who moved last.
        if not (board.is_checkmate() or board.is_stalemate()):
            last_was_agent = board_before_last.turn == agent_color
            if last_was_agent:
                # Opponent is to move now — branch over THEIR replies.
                opts = _testing_replies(board, k=3)
                if len(opts) >= 2:
                    out += [
                        "",
                        "---",
                        "",
                        "**⮕ Branch over the opponent's replies — don't assume one.** "
                        "It is the opponent's move now; their most testing replies "
                        f"are **{', '.join(opts)}** (checks/captures first). Re-run "
                        "`chess__imagine_line` continuing this line with EACH of them "
                        "and confirm your move holds against all — a move that only "
                        "works against one reply is not calculated.",
                    ]
            else:
                # It is YOUR move now at the leaf — show YOUR forcing continuations
                # (checks, captures) so you carry the combination through instead
                # of stopping. This is the CCT discipline applied mid-line.
                forcing = [s for s in _testing_replies(board, k=4)
                           if "+" in s or "#" in s or "x" in s]
                if forcing:
                    out += [
                        "",
                        "---",
                        "",
                        f"**⮕ It is YOUR move here — keep checking forcing moves (Checks, Captures, "
                        f"Threats).** Your most forcing continuations are **{', '.join(forcing)}**. "
                        f"A combination often needs one MORE forcing move to pay off — extend the line "
                        f"with the promising one (you have up to {_MAX_PLIES} plies) and read the leaf "
                        f"verdict before concluding the line fails.",
                    ]
                # fall through to the assumed-opponent-reply alternatives below
            if not last_was_agent:
                # You supplied ONE opponent reply — name the alternatives.
                alts = _testing_replies(board_before_last, exclude=last_move, k=3)
                if alts:
                    played = board_before_last.san(last_move)
                    out += [
                        "",
                        "---",
                        "",
                        f"**⮕ You assumed the opponent plays {played}.** Their other "
                        f"testing replies are **{', '.join(alts)}**. Re-run "
                        "`chess__imagine_line` with each instead of "
                        f"{played} — your move is only good if it holds against all.",
                    ]
    else:
        out.append("_(no move rendered)_")
    print("\n".join(out))


if __name__ == "__main__":
    main()
