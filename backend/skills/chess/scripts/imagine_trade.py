#!/usr/bin/env python3
"""See a CAPTURE/TRADE on one square played out to the end — the running material
balance after every recapture, so you never misjudge a trade by stopping one
capture too early.

This is the trade-focused companion to chess__imagine_line. Where imagine_line is
a general multi-ply look-ahead, imagine_trade is SCOPED to the exchanges on a
single square: it answers "if I (or pieces) start capturing on <square>, who
recaptures, and what is the material balance at each step — and where should the
sequence stop?"

You drive it (the tool searches nothing and recommends no move):
  - give a SQUARE (e.g. "e5") to see the exchange there with the natural
    least-valuable-first recapture order, AND any sensible ALTERNATIVE first
    captures you have (capture with a different piece), each scored; or
  - give a CAPTURE MOVE (e.g. "Nxe5" / "d4e5") to force that as the first
    capture and see the sequence that follows.

For each line it prints the capture sequence and the RUNNING material balance
(from your side) after every ply, the net at the point a sane player would stop
(Static Exchange Evaluation), and a one-line verdict (winning / equal / losing
the exchange). The live game is NOT changed.

Arguments:
  target   A square ("e5") to evaluate the exchange on, OR a capture move in
           UCI/SAN ("Nxe5", "d4e5") to fix the first capture.
  --fen    Start from this position instead of the live game.

Exposed as chess__imagine_trade after use_skill('chess'). Examples:
  chess__imagine_trade(target="e5")     # all ways the e5 trade can go
  chess__imagine_trade(target="Rxe5")   # force Rxe5 first, then the sequence
"""
import argparse
import json
import sys
from pathlib import Path

import chess

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from _eval import MATERIAL, parse_move  # noqa: E402
from _live import board_with_history, fetch_state  # noqa: E402

_PN = {chess.PAWN: "pawn", chess.KNIGHT: "knight", chess.BISHOP: "bishop",
       chess.ROOK: "rook", chess.QUEEN: "queen", chess.KING: "king"}


def _val(pt: int) -> int:
    return MATERIAL.get(pt, 0)


def _square_arg(board: chess.Board, target: str):
    """Resolve the `target` arg to (square, forced_first_move|None). Accepts a
    bare square name, or a capture move in SAN/UCI (then the first capture is
    fixed to that move)."""
    t = target.strip()
    # bare square like "e5"
    if len(t) == 2 and t[0] in "abcdefgh" and t[1] in "12345678":
        return chess.parse_square(t), None
    # otherwise a move
    try:
        mv = parse_move(board, t)
    except Exception as exc:
        raise ValueError(f"'{target}' is not a square (e.g. e5) or a legal move "
                         f"(e.g. Nxe5): {exc}")
    if not board.is_capture(mv):
        raise ValueError(f"{board.san(mv)} is not a capture — imagine_trade is for "
                         f"exchanges on a square. Use chess__imagine_line for quiet moves.")
    return mv.to_square, mv


def _play_exchange(board: chess.Board, square: int, first: chess.Move | None):
    """Play out an exchange on `square` to its natural end and return a list of
    plies: each (san, capturing_color, running_balance_white_pov, captured_value).

    'Natural end' = each side recaptures with its LEAST VALUABLE attacker, and
    EITHER side stops as soon as continuing would lose material for it (standard
    SEE stopping). If `first` is given, it is forced as the first capture; after
    that the natural order resumes.
    """
    work = board.copy(stack=False)
    plies = []
    # running material balance from White's point of view (so it's stable across
    # whose turn it is). Start at the current balance.
    def bal_white(bd):
        return sum(_val(pt) * (len(bd.pieces(pt, chess.WHITE)) - len(bd.pieces(pt, chess.BLACK)))
                   for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN))

    start_bal = bal_white(work)

    # the side that moves first is the side to move on the board, unless `first`
    # forces a colour.
    mover = work.turn if first is None else work.piece_at(first.from_square).color

    step = 0
    while True:
        if step == 0 and first is not None:
            mv = first
        else:
            # least valuable attacker of `square` for `mover` that is a legal capture
            atk = [a for a in work.attackers(mover, square)]
            if not atk:
                break
            atk.sort(key=lambda a: _val(work.piece_at(a).piece_type))
            mv = None
            for a in atk:
                cand = chess.Move(a, square)
                # handle promotion captures onto the back rank
                if work.piece_at(a).piece_type == chess.PAWN and chess.square_rank(square) in (0, 7):
                    cand = chess.Move(a, square, promotion=chess.QUEEN)
                if cand in work.legal_moves:
                    mv = cand
                    break
            if mv is None:
                break
        victim = work.piece_at(square)
        cap_val = _val(victim.piece_type) if victim else 0
        try:
            san = work.san(mv)
        except Exception:
            break
        work.push(mv)
        plies.append((san, mover, bal_white(work) - start_bal + start_bal, cap_val, mover))
        mover = not mover
        step += 1
        # safety: an exchange on one square can't exceed ~16 plies
        if step > 16:
            break
    return start_bal, plies


def _see_stop(start_bal: int, plies, my_color: bool):
    """Given the full played-out sequence, find the balance at the point a sane
    player would STOP (each side stops when continuing loses for it). Returns
    (stop_index, balance_at_stop_white_pov). Uses the standard SEE minimax over
    the running balances."""
    # balances (white pov) after each ply, prefixed with the start
    bals = [start_bal] + [p[2] for p in plies]
    # Work backwards: at each node the side to move will only continue if it
    # improves their pov. side at ply i is plies[i][1] (the capturer).
    # Simpler and robust: the *initiator* gets to choose how far to go to
    # maximise their result, the defender to minimise. Do a backward minimax on
    # the white-pov balance, flipping by whose move it is.
    best_for_white = [0] * (len(bals))
    best_for_white[-1] = bals[-1]
    for i in range(len(plies) - 1, -1, -1):
        mover = plies[i][1]
        cont = best_for_white[i + 1]   # balance if we DO play ply i (and onward optimally)
        stop = bals[i]                 # balance if we stop here (before ply i)
        if mover == chess.WHITE:
            best_for_white[i] = max(stop, cont)
        else:
            best_for_white[i] = min(stop, cont)
    return best_for_white[0]


def _see_stop_from_ply1(start_bal: int, plies):
    """Like _see_stop, but the FIRST capture (ply 0) is taken as already played
    (the agent is evaluating that specific capture); minimax resumes from ply 1.
    Returns the white-pov balance the sequence settles on."""
    bals = [start_bal] + [p[2] for p in plies]
    if not plies:
        return start_bal
    best_for_white = [0] * len(bals)
    best_for_white[-1] = bals[-1]
    for i in range(len(plies) - 1, 0, -1):   # stop at i=1; ply 0 is forced
        mover = plies[i][1]
        cont = best_for_white[i + 1]
        stop = bals[i]
        best_for_white[i] = max(stop, cont) if mover == chess.WHITE else min(stop, cont)
    # ply 0 forced: take its continuation value (or its own balance if no further)
    return best_for_white[1] if len(plies) >= 1 else bals[0]


def _render(board: chess.Board, square: int, forced: chess.Move | None) -> str:
    sq_name = chess.square_name(square)
    me = board.turn
    out = [f"# Imagine trade on {sq_name}  (your own calculation — nothing committed)", ""]
    occupant = board.piece_at(square)
    if occupant is None and forced is None:
        # no piece to capture: list the captures you HAVE that land here, if any
        caps = [board.san(m) for m in board.legal_moves if m.to_square == square and board.is_capture(m)]
        out.append(f"_{sq_name} is empty — nothing to capture there._" if not caps
                   else f"_{sq_name} is empty; (en-passant captures: {', '.join(caps)})_")
        return "\n".join(out)

    # which side's piece sits on the square (the thing first captured)
    def line_for(first):
        start_bal, plies = _play_exchange(board, square, first)
        if not plies:
            return None
        # render from MY point of view (+ = good for me)
        sign = 1 if me == chess.WHITE else -1
        rows = ["| # | capture | by | running balance (you) |",
                "|---|---------|----|-----------------------|"]
        for i, (san, mover, bal_w, capv, _m) in enumerate(plies, 1):
            who = "you" if mover == me else "opp"
            my_bal = sign * (bal_w - start_bal)
            rows.append(f"| {i} | {san} | {who} | {my_bal:+d} |")
        # Two numbers the agent needs:
        #  - decline_net: SEE-optimal if you may CHOOSE not to start (0 if the
        #    first capture loses and you can simply not play it).
        #  - play_net: the result if you DO play the first capture, then both
        #    sides recapture optimally (the opponent may stop early). This is the
        #    one the agent is actually asking about.
        decline_white = _see_stop(start_bal, plies, me)
        play_white = _see_stop_from_ply1(start_bal, plies)
        decline_net = sign * (decline_white - start_bal)
        play_net = sign * (play_white - start_bal)
        if play_net > 0:
            verdict = f"playing it WINS ~{play_net:+d} — a good capture"
        elif play_net == 0:
            verdict = "playing it is an EVEN trade (~0)"
        else:
            verdict = (f"playing it LOSES ~{play_net:+d} — a BAD capture; "
                       f"better NOT to initiate it (declining keeps you at {decline_net:+d})")
        return rows, play_net, verdict, len(plies)

    lines = []
    if forced is not None:
        res = line_for(forced)
        if res:
            lines.append((f"Forcing {board.san(forced)} first:", res))
    else:
        # the natural sequence + each alternative FIRST capture you have
        first_caps = []
        if occupant is not None and occupant.color != me:
            for a in sorted(board.attackers(me, square), key=lambda a: _val(board.piece_at(a).piece_type)):
                cand = chess.Move(a, square)
                if board.piece_at(a).piece_type == chess.PAWN and chess.square_rank(square) in (0, 7):
                    cand = chess.Move(a, square, promotion=chess.QUEEN)
                if cand in board.legal_moves:
                    first_caps.append(cand)
        if not first_caps:
            out.append(f"_You have no capture of {sq_name} right now "
                       f"(the piece there may be yours, or unattacked by you)._")
            return "\n".join(out)
        for fc in first_caps:
            res = line_for(fc)
            if res:
                lines.append((f"Start with {board.san(fc)} ({_PN[board.piece_at(fc.from_square).piece_type]}):", res))

    if not lines:
        out.append(f"_No capture sequence resolves on {sq_name}._")
        return "\n".join(out)

    # If multiple first-captures, highlight which way is best for you.
    best_net = max(r[1][1] for r in lines)
    for header, (rows, net, verdict, nplies) in lines:
        star = "  ⬅ best for you" if net == best_net and len(lines) > 1 else ""
        out.append(f"**{header}**{star}")
        out += rows
        out.append(f"→ **{verdict}.** (Each side recaptures with its least valuable piece and stops "
                   f"when continuing would lose for it.)")
        out.append("")
    out.append("_This counts material only — it does not see tactics (a pin, a back-rank mate, a "
               "zwischenzug can change everything). Confirm there is no in-between check or a piece "
               "you leave hanging elsewhere; if the trade opens lines toward your king, weigh that too. "
               "The decision is yours._")
    if len(lines) > 1:
        out.append("_Different first captures give different results — pick the recapture order that is "
                   "best for you (you are not forced to take with the least valuable piece if another "
                   "capture wins more or sets up a tactic)._")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--fen", default=None)
    parser.add_argument("target", nargs="?", default="")
    parser.add_argument("-h", "--help", action="store_true")
    args = parser.parse_args()
    if args.help or not args.target.strip():
        print(__doc__)
        return
    if args.fen:
        try:
            board = chess.Board(args.fen)
        except ValueError:
            board = board_with_history(fetch_state())
    else:
        board = board_with_history(fetch_state())
    try:
        square, forced = _square_arg(board, args.target)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        sys.exit(1)
    print(_render(board, square, forced))


if __name__ == "__main__":
    main()
