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
from _eval import MATERIAL, PIECE_NAMES, parse_move, static_exchange_eval  # noqa: E402
from _live import board_with_history, fetch_state  # noqa: E402


def _blunder_gate(board: chess.Board, move: chess.Move) -> tuple[str, bool] | None:
    """One-ply mechanical safety check at the commit boundary.

    Returns ``(warning, hard)`` when the move (a) lets the opponent capture a
    piece that has zero defenders (a free capture — the single pattern behind
    every lost mating exercise on 2026-06-12: Kd6?? abandoning the rook,
    Qd4+?? adjacent to the king), (b) delivers stalemate, or (c) instantly
    draws by repetition/50-move while the mover is ahead on raw material.

    ``hard`` marks losses that ``confirm=true`` must NOT override, because no
    intention can justify them: a move that drops to insufficient material
    (throws away the win outright), or hangs a ROOK-or-better to the bare /
    nearly-bare enemy king in a basic-mate position (there is no sacrifice
    when the opponent has no army — game ab02f31d, 2026-06-13: the agent
    reflexively confirm=true'd Rb6+?? Kxb6 on move 2 of a ladder). Ordinary
    free captures stay soft (``hard=False``) — a real sacrifice is one extra
    call.

    This is the same geometry chess__imagine_move reports, enforced where it
    cannot be skipped. It makes no strategic judgement: legal replies,
    defender counts, material counts, and the draw rules of chess only.
    """
    after = board.copy()
    after.push(move)
    mover = board.turn

    if after.is_checkmate():
        return None  # nothing after mate matters

    if after.is_stalemate():
        return (
            "this move delivers STALEMATE — the game instantly ends in a "
            "draw. If you are winning, this throws away the win.", True
        )

    # Is the opponent reduced to a bare (or pawns-only) king? Then any free
    # gift of a rook-or-better is never a real sacrifice — it is a basic-mate
    # blunder, and confirm must not wave it through.
    opp_has_no_pieces = not any(
        p.color != mover and p.piece_type not in (chess.KING, chess.PAWN)
        for p in board.piece_map().values()
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
                f"ahead on material. Pick a move that makes progress instead.",
                True,
            )

    # A move that merely RECREATES an earlier position (its second occurrence)
    # is not yet a claimable draw — but when you are WINNING AGAINST A BARE KING
    # it is pure anti-progress and the on-ramp to a repetition draw: the
    # opponent completes the threefold on ITS move, which this gate (seeing only
    # your move) cannot block later. So forbid feeding the repetition at all
    # during a basic-mate conversion. Observed: game 987fc4c7 (K+R+N vs bare K)
    # drew exactly this way — White played Kc7 then Nb4+, each recreating a
    # prior position, and Black's reply claimed the threefold. Pure rules:
    # position recurrence + material count; never fires when the move is mate.
    if board.move_stack and opp_has_no_pieces and not after.is_checkmate() \
            and after.is_repetition(2):
        my_mat = sum(MATERIAL[p.piece_type] for p in board.piece_map().values()
                     if p.color == mover and p.piece_type != chess.KING)
        their_mat = sum(MATERIAL[p.piece_type] for p in board.piece_map().values()
                        if p.color != mover and p.piece_type != chess.KING)
        if my_mat > their_mat:
            return (
                "this move RECREATES a position already seen this game. You are "
                "winning against a bare king, so repeating makes NO progress and "
                "walks toward a draw by repetition (the opponent claims it on "
                "its move). Pick a move that makes progress — shrink the enemy "
                "king's box or mobility, drive it toward the edge/corner.",
                True,
            )

    # Losing trades, via static exchange evaluation on the moved piece's
    # square. SEE plays out the forced recapture sequence on that one square
    # and returns the material the OPPONENT nets if they initiate captures
    # there. This subsumes the old "free capture into an undefended square"
    # check AND catches the defended-but-losing trade the count-based version
    # missed (game 9b0d7590 16.Nxd6??/9.Nd2??, game f2d158d4 16.Ne5?? — a
    # piece moved to a square defended only by a pawn). It is pure
    # rules-of-chess arithmetic on a single square: no move-tree search, no
    # positional judgement (2026-06-15 ruling: extend the gate to all
    # single-square losing trades, since random blundering — not strategy —
    # is what keeps the agent from ever reaching a won position).
    #
    # Netting: SEE already accounts for what the move captured (the captured
    # piece is the first item on the swap-off list), so a fair trade nets 0
    # and is not flagged.
    sq = move.to_square
    see_loss = static_exchange_eval(after, sq, not mover)
    worst: tuple[int, str, int] | None = None
    if see_loss >= 150:
        moved = after.piece_at(sq)
        moved_name = PIECE_NAMES[moved.piece_type] if moved else "piece"
        value = see_loss
        # An uncompensated loss that leaves us unable to EVER win outranks raw
        # value: losing the last pawn in K+P vs K is an instant draw (game
        # 9d2e1e58: Kc7?? Kxe7). Approximate by checking insufficient material
        # after the opponent's cheapest capture on the square.
        cheapest = min(
            (r for r in after.legal_moves if r.to_square == sq and after.is_capture(r)),
            key=lambda r: MATERIAL.get(after.piece_at(r.from_square).piece_type, 0),
            default=None,
        )
        if cheapest is not None:
            b2 = after.copy(stack=False)
            b2.push(cheapest)
            if b2.has_insufficient_material(mover):
                value = 10_000
        desc = (
            f"after this move you LOSE MATERIAL on {chess.square_name(sq)}: "
            f"the opponent wins about {see_loss} centipawns "
            f"(~{see_loss // 100} pawn(s)) in the exchange there — your "
            f"{moved_name} is not adequately defended for its value. "
            f"'Defended' by count is not the same as safe."
        )
        if value >= 10_000:
            desc += (
                ". Worse: it leaves you with INSUFFICIENT MATERIAL TO WIN — "
                "the game would be dead drawn"
            )
        worst = (value, desc, moved.piece_type if moved else chess.PAWN)

    # Side-effect hangs: a move can leave a DIFFERENT own piece losing
    # material — the "abandon a defender" blunder (game 9b0d7590 9.Nd2??
    # left the c3 knight to bxc3 bxc3). Scan own pieces (excluding the moved
    # piece's square) that were SAFE before the move and are SEE-losing
    # after. Gating on "safe before" is essential: it flags only losses this
    # move CAUSED, never a pre-existing hang the move didn't create (which
    # might be unavoidable / not this move's fault).
    for piece_type in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        for psq in after.pieces(piece_type, mover):
            if psq == sq:
                continue  # the moved piece itself — handled above
            if board.piece_at(psq) is None or board.piece_at(psq).color != mover:
                continue  # not a piece that existed (and was ours) before
            safe_before = static_exchange_eval(board, psq, not mover) < 150
            loss_after = static_exchange_eval(after, psq, not mover)
            if not (safe_before and loss_after > 0):
                continue
            # Losing this piece may leave us unable to ever win (the last-pawn
            # case: K+P vs K, Kc7?? Kxe7 is an instant draw — game 9d2e1e58).
            # That outranks raw value, and matters even for a 100cp pawn that
            # is below the normal 150 threshold.
            value = loss_after
            cheapest = min(
                (r for r in after.legal_moves
                 if r.to_square == psq and after.is_capture(r)),
                key=lambda r: MATERIAL.get(after.piece_at(r.from_square).piece_type, 0),
                default=None,
            )
            if cheapest is not None:
                b2 = after.copy(stack=False)
                b2.push(cheapest)
                if b2.has_insufficient_material(mover):
                    value = 10_000
            if value < 150:
                continue  # ordinary sub-threshold loss (a bare pawn) — skip
            if worst is None or value > worst[0]:
                desc = (
                    f"this move leaves your {PIECE_NAMES[piece_type]} "
                    f"on {chess.square_name(psq)} losing material: the "
                    f"opponent wins about {loss_after} centipawns "
                    f"(~{loss_after // 100} pawn(s)) in the exchange "
                    f"there. Moving away a defender (or opening a line) "
                    f"hangs it — find a move that keeps it protected."
                )
                if value >= 10_000:
                    desc = (
                        f"this move abandons your {PIECE_NAMES[piece_type]} "
                        f"on {chess.square_name(psq)} — the opponent takes it "
                        f"and you are left with INSUFFICIENT MATERIAL TO WIN "
                        f"(dead draw). Keep it defended."
                    )
                worst = (value, desc, piece_type)

    # Promotion straight into a capture: a special, common, and especially
    # costly case the agent reliably misreads (it banks the +800 promotion
    # and ignores the immediate recapture — observed repeatedly). Flag it
    # loudly and make it reflect on whether the promotion actually helps.
    if move.promotion is not None and see_loss >= 150:
        desc = (
            f"you promoted to a {PIECE_NAMES[move.promotion]} on "
            f"{chess.square_name(sq)}, but the opponent can capture it "
            f"immediately and you cannot recapture for equal value — the "
            f"promotion gains material on paper but loses it next move. "
            f"Promoting is only worth it if the new piece SURVIVES or its "
            f"capture wins you something bigger. Reflect: does this promotion "
            f"actually strengthen your position, or just hand back a pawn? "
            f"If not, promote on a safe square or prepare the push first."
        )
        worst = (max(see_loss, worst[0] if worst else 0), desc,
                 move.promotion)

    if worst is not None and worst[0] >= 150:
        # `severe` controls the LOUDNESS of the (advisory) warning and the
        # friction on overriding it — it is NOT a block (the gate is advisory;
        # see decisions/2026-06-20-blunder-gate-advisory-only.md). A move that
        # loses a whole PIECE (minor or major) or throws the win away outright
        # is severe; losing only a pawn (or a sub-piece amount) stays ordinary.
        # The ranked batch on 2026-06-20 showed the agent confidently
        # confirm=true'ing queen-hangs that were merely "ordinary" warnings —
        # losing easily-won games — so every piece-level blunder must read loud.
        severe = worst[2] != chess.PAWN or worst[0] >= 10_000
        return worst[1], severe

    # Rescuable hanging piece (SOFT only): the move doesn't CAUSE a loss, but
    # after it one of your pieces is still losing-by-value AND a different
    # legal move this turn would have saved it. This catches "fail to rescue
    # an already-hanging piece" — game 9b0d7590, where the c3 knight was
    # already hanging (8...b4) and the agent played Nd2 instead of retreating
    # it. Soft because the loss may be unavoidable elsewhere or an intended
    # sacrifice; we only nudge when a rescue demonstrably existed. Computing
    # "could it be saved" scans this turn's legal moves — bounded, mechanical,
    # no positional judgement (2026-06-15 ruling).
    for piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT):
        for psq in after.pieces(piece_type, mover):
            if psq == sq:
                continue
            if static_exchange_eval(after, psq, not mover) < 150:
                continue  # this piece is safe after the move
            # Was it hanging before too? (if not, the move-caused scan above
            # would have flagged it). Either way, check a rescue existed.
            saved = False
            for alt in board.legal_moves:
                a2 = board.copy(stack=False)
                a2.push(alt)
                # the piece may itself be the one that moves to safety
                check_sq = alt.to_square if alt.from_square == psq else psq
                if a2.piece_at(check_sq) is None:
                    continue
                if static_exchange_eval(a2, check_sq, not mover) < 150:
                    saved = True
                    break
            if saved:
                return (
                    f"heads up: your {PIECE_NAMES[piece_type]} on "
                    f"{chess.square_name(psq)} is hanging (the opponent wins "
                    f"material in the exchange there), and a move this turn "
                    f"could save it — you are leaving it to be taken. If that "
                    f"is not a deliberate sacrifice, rescue it instead.",
                    False,
                )
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
            "Override a SOFT safety warning (an ordinary free capture that "
            "may be a genuine sacrifice). Pass confirm=true only when the "
            "sacrifice is intentional. It does NOT override a HARD warning — "
            "a move that loses the game outright (stalemate, draw-while-"
            "winning, or hanging a major piece to a king with no army) is "
            "refused regardless."
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

    # Mechanical safety gate. Runs ALWAYS (even with confirm=true) so a HARD
    # warning — throwing the win away outright, or hanging a major to a king
    # with no army — cannot be waved through; soft warnings are overridable
    # with confirm. Best-effort: if the live state cannot be fetched or the
    # move does not parse, fall through — the endpoint is the authoritative
    # validator and reports those errors.
    gate = None
    try:
        board = board_with_history(fetch_state())
        candidate = parse_move(board, move_str)
        if candidate in board.legal_moves:
            gate = _blunder_gate(board, candidate)
    except (SystemExit, Exception):
        gate = None  # endpoint is the authoritative validator
    if gate is not None and not args.confirm:
        warning, severe = gate
        # Advisory-only: the gate never REFUSES a legal move (that would be the
        # tool making the decision, not the agent — unfair, and it deadlocks
        # when every legal move trips a rule). It warns; the agent commits by
        # re-calling with confirm=true. The wording is stronger for the
        # catastrophic cases (`severe`), but they are equally overridable.
        # See decisions/2026-06-20-blunder-gate-advisory-only.md.
        if severe:
            prefix = (
                "⛔ SAFETY CHECK (severe) — move NOT committed: " + warning +
                " This hangs a PIECE / throws the game away — it is almost "
                "certainly a losing blunder, and blundering pieces is the #1 way "
                "this agent loses won games. The default is to PICK A DIFFERENT, "
                "SAFE MOVE. You may override with confirm=true ONLY if it is a "
                "forced checkmate, OR you can state in `reasoning` the exact "
                "forced line (move by move, with the opponent's replies) that "
                "WINS THE MATERIAL BACK or mates. If you cannot name that line, "
                "do NOT override — choose a move that keeps your pieces."
            )
        else:
            prefix = (
                "SAFETY CHECK — move NOT yet committed: " + warning +
                " If this is intentional (a real sacrifice), call "
                "chess__make_move again with the same move and confirm=true. "
                "Otherwise pick a different move."
            )
        print(json.dumps({"ok": False, "error": prefix}))
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
