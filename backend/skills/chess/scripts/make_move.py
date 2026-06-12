#!/usr/bin/env python3
"""Commit your chosen move for this turn. This is the mandatory closing action.

Arguments:
  move       Required. The move in UCI (e2e4, g1f3, e7e8q) or SAN (e4, Nf3,
             O-O, e8=Q). Trailing + or # is ignored.
  reasoning  Required. Your note to yourself about THIS move. Free text —
             punctuation, apostrophes, quotes are all fine. Shown back to you
             on your next turn, then replaced by the next note.
  plan       Optional. Your LONG-TERM standing plan (goal + method, 1-2
             sentences). It persists across turns until you pass a new plan,
             and is shown back to you every turn. Omit it to keep your
             current plan; pass it when you form, change, or complete a plan;
             pass plan="none" to clear it.
  goal       Optional. Your SHORT-TERM objective — what the next 1-3 moves
             must achieve (e.g. "drive the king from e6 to the 8th rank").
             Same persistence rules as plan; pass goal="none" to clear it.
  dismiss_references  Optional. Comma-separated wiki paths whose content is
             no longer relevant to your strategy (e.g. after switching from
             a promotion plan to a mating plan). Their text is dropped from
             your context next turn; you can always re-read them. Pass "all"
             to drop every page you have read.

Exposed as the tool chess__make_move after use_skill('chess'). Examples:
  chess__make_move(move="Nf3", reasoning="Developed knight; pressures e5.")
  chess__make_move(move="a6", reasoning="Pushed the passer; b7 guards a7.",
                   plan="Promote the a-pawn: escort with the queen, then ladder mate.",
                   goal="Get the pawn to a8 in the next two moves.")

Reads CHESS_API_BASE and CHESS_GAME_ID from environment (injected by AgentPlayer).

This script does NOT push the move to the board. It POSTs a commit-intent to
``/api/games/{id}/agent-commit``, which validates the move against the live
board (legality, turn, move shape). The bot loop is the single board writer:
it reads this script's result, parses out the canonical UCI, and pushes the
move under its own lock. That keeps every player (agent, chesscom, maia,
human) on the same contract — players return moves, the bot loop pushes them.

Prints on success:
  {"ok": true, "move": "<canonical-uci>", "reasoning": "...", "plan": "..."|null, "message": "Move committed. Your turn is over."}

Prints on failure (illegal move, wrong turn, parse error):
  {"ok": false, "error": "...", "legal_moves": [...]}
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

import chess

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from _eval import MATERIAL, PIECE_NAMES, parse_move  # noqa: E402
from _live import board_with_history, fetch_state  # noqa: E402


def _blunder_gate(board: chess.Board, move: chess.Move) -> str | None:
    """One-ply mechanical safety check at the commit boundary.

    Returns a warning string when the move (a) lets the opponent capture a
    piece that has zero defenders (a free capture — the single pattern behind
    every lost mating exercise on 2026-06-12: Kd6?? abandoning the rook,
    Qd4+?? adjacent to the king), (b) delivers stalemate, or (c) instantly
    draws by repetition/50-move while the mover is ahead on raw material.

    This is the same geometry chess__imagine_move reports, enforced where it
    cannot be skipped. It makes no judgement calls: legal replies, defender
    counts, and the draw rules of chess only. The agent can always override
    with confirm=true (a real sacrifice is one extra call).
    """
    after = board.copy()
    after.push(move)
    mover = board.turn

    if after.is_checkmate():
        return None  # nothing after mate matters

    if after.is_stalemate():
        return (
            "this move delivers STALEMATE — the game instantly ends in a "
            "draw. If you are winning, this throws away the win."
        )

    # The backend ends non-chesscom games with claim_draw=True, so the
    # moment a draw is CLAIMABLE it is a draw — can_claim_* (not the stricter
    # is_repetition(3)/is_fifty_moves) is the rule that actually ends games.
    # Observed: game 185afd0b drew on a Qd5 where is_repetition(3) was False
    # but can_claim_threefold_repetition() was True.
    if board.move_stack and (
        after.can_claim_threefold_repetition() or after.can_claim_fifty_moves()
    ):
        my_mat = sum(MATERIAL[p.piece_type] for p in board.piece_map().values()
                     if p.color == mover and p.piece_type != chess.KING)
        their_mat = sum(MATERIAL[p.piece_type] for p in board.piece_map().values()
                        if p.color != mover and p.piece_type != chess.KING)
        if my_mat > their_mat:
            rule = (
                "threefold repetition"
                if after.can_claim_threefold_repetition()
                else "the 50-move rule"
            )
            return (
                f"this move instantly DRAWS the game by {rule} while you are "
                f"ahead on material. Pick a move that makes progress instead."
            )

    # Free captures: an opponent reply that takes a piece nobody recaptures.
    worst: tuple[int, str] | None = None
    for reply in after.legal_moves:
        if not after.is_capture(reply):
            continue
        victim = after.piece_at(reply.to_square)
        if victim is None:  # en passant — pawn-for-pawn, never free
            continue
        defenders = after.attackers(mover, reply.to_square)
        if defenders:
            continue
        value = MATERIAL.get(victim.piece_type, 0)
        if worst is None or value > worst[0]:
            taker = after.piece_at(reply.from_square)
            worst = (value, (
                f"after this move the opponent can play "
                f"{after.san(reply)} and take your "
                f"{PIECE_NAMES[victim.piece_type]} on "
                f"{chess.square_name(reply.to_square)} FOR FREE — no piece "
                f"of yours defends that square (capturer: "
                f"{PIECE_NAMES[taker.piece_type]} from "
                f"{chess.square_name(reply.from_square)})"
            ))
    if worst is not None and worst[0] >= 300:  # minor piece or better
        return worst[1]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    # --plan must be declared before the REMAINDER positional: the harness's
    # build_argv emits flags first, and argparse stops option parsing once
    # REMAINDER starts consuming.
    parser.add_argument(
        "--plan",
        default=None,
        help=(
            "Your long-term standing plan (goal + method). Persists across "
            "turns until you pass a new one; omit to keep the current plan; "
            "pass 'none' to clear it."
        ),
    )
    parser.add_argument(
        "--goal",
        default=None,
        help=(
            "Your short-term objective: what the next 1-3 moves must achieve. "
            "Persists like plan; pass 'none' to clear it."
        ),
    )
    parser.add_argument(
        "--dismiss_references",
        default=None,
        help=(
            "Comma-separated wiki paths to drop from your context next turn "
            "(no longer relevant to your strategy), or 'all'."
        ),
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help=(
            "Override the mechanical safety check. Required when your move "
            "gives away a piece for free, stalemates, or instantly draws "
            "while ahead — pass confirm=true only when that is intentional "
            "(e.g. a genuine sacrifice)."
        ),
    )
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

    # Mechanical safety gate (skipped with confirm=true). Best-effort: if the
    # live state cannot be fetched or the move does not parse, fall through —
    # the endpoint is the authoritative validator and reports those errors.
    if not args.confirm:
        warning = None
        try:
            board = board_with_history(fetch_state())
            candidate = parse_move(board, move_str)
            if candidate in board.legal_moves:
                warning = _blunder_gate(board, candidate)
        except (SystemExit, Exception):
            warning = None  # endpoint is the authoritative validator
        if warning is not None:
            print(json.dumps({
                "ok": False,
                "error": (
                    f"SAFETY CHECK — move NOT committed: {warning} "
                    f"If this is intentional (a real sacrifice), call "
                    f"chess__make_move again with the same move and "
                    f"confirm=true. Otherwise pick a different move."
                ),
            }))
            sys.exit(1)

    # The endpoint caps reasoning at 4000 chars (schemas.AgentCommitRequest).
    # Truncate rather than let the whole commit be rejected for verbosity —
    # observed in game bf129584: a LEGAL winning move bounced because the
    # note was too long, costing the turn.
    if len(reasoning) > 3900:
        reasoning = reasoning[:3880] + " [trimmed]"

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
            plan = args.plan.strip() if isinstance(args.plan, str) else None
            goal = args.goal.strip() if isinstance(args.goal, str) else None
            dismissed = None
            if isinstance(args.dismiss_references, str) and args.dismiss_references.strip():
                dismissed = [
                    p.strip() for p in args.dismiss_references.split(",") if p.strip()
                ]
            print(json.dumps({
                "ok": True,
                "move": canonical,
                "reasoning": reasoning,
                "plan": plan if plan else None,
                "goal": goal if goal else None,
                "dismissed_references": dismissed,
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
