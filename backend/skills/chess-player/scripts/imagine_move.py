#!/usr/bin/env python3
"""Imagine a single move from the current position. Shows the resulting board,
the static eval before/after, the attack/defense map for the moved piece on
its new square, deltas (attacks/defenses gained and lost), discovered
attacks, newly hanging own pieces, check/mate status, captures, and the
opponent's legal replies.

Reads CHESS_API_BASE and CHESS_GAME_ID from environment (injected by
AgentPlayer). The live board state is **not** mutated; everything is computed
on a copy.

Argument:
  --uci <move>    UCI move to imagine (e.g. e2e4, g1f3, e1g1, e7e8q).

If the move is illegal, the script exits nonzero with a categorised error
(no piece, blocked, pinned, etc.).

Output is markdown so it renders cleanly in the agent UI.
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

import chess


# Sibling imports — `from _eval import ...` and `from show_position import ...`.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from _eval import (  # noqa: E402
    EVAL_WARNING,
    MATERIAL,
    PIECE_NAMES,
    annotate_move,
    classify_illegal_move,
    color_name,
    describe_piece,
    enemy_king_mobility,
    render_eval_delta_line,
    render_moves_table,
)
from show_position import (  # noqa: E402
    compute_attack_chain,
    format_chain,
    render_ascii,
)


def _attacks_and_defenses(board: chess.Board, square: int) -> tuple[set[int], set[int]]:
    """Return (squares_attacking_opponent, squares_defending_own) for the
    piece on `square`. Splits board.attacks() by colour of pieces on
    controlled squares."""
    piece = board.piece_at(square)
    if piece is None:
        return set(), set()
    attacks_enemy: set[int] = set()
    defends_own: set[int] = set()
    for sq in board.attacks(square):
        target = board.piece_at(sq)
        if target is None:
            continue
        if target.color == piece.color:
            defends_own.add(sq)
        else:
            attacks_enemy.add(sq)
    return attacks_enemy, defends_own


def _format_squares_with_pieces(board: chess.Board, squares: set[int]) -> str:
    if not squares:
        return "(none)"
    return ", ".join(describe_piece(board, s) for s in sorted(squares))


def _move_summary(board_before: chess.Board, move: chess.Move) -> str:
    """One-line description of the move itself."""
    piece = board_before.piece_at(move.from_square)
    piece_name = PIECE_NAMES[piece.piece_type]
    from_name = chess.square_name(move.from_square)
    to_name = chess.square_name(move.to_square)
    san = board_before.san(move)

    is_ep = board_before.is_en_passant(move)
    is_castle = board_before.is_castling(move)

    if is_castle:
        side = "kingside" if chess.square_file(move.to_square) > chess.square_file(move.from_square) else "queenside"
        return f"`{move.uci()}` ({san}) — {side} castle"

    captured = board_before.piece_at(move.to_square)
    if is_ep:
        ep_sq = chess.square(chess.square_file(move.to_square), chess.square_rank(move.from_square))
        captured = board_before.piece_at(ep_sq)
        value = MATERIAL[chess.PAWN]
        return (
            f"`{move.uci()}` ({san}) — {piece_name} {from_name} → {to_name}, "
            f"en passant captures {color_name(captured.color)} pawn on {chess.square_name(ep_sq)} (+{value}cp)"
        )

    promo_extra = f", promotes to {PIECE_NAMES[move.promotion]}" if move.promotion is not None else ""

    if captured is not None:
        value = MATERIAL[captured.piece_type] if captured.piece_type != chess.KING else 0
        return (
            f"`{move.uci()}` ({san}) — {piece_name} {from_name} → {to_name}, "
            f"captures {color_name(captured.color)} {PIECE_NAMES[captured.piece_type]} (+{value}cp){promo_extra}"
        )

    return f"`{move.uci()}` ({san}) — {piece_name} {from_name} → {to_name} (no capture){promo_extra}"


def _check_status(board_after: chess.Board) -> str:
    if board_after.is_checkmate():
        return "gives checkmate"
    if board_after.is_stalemate():
        return "stalemate (no legal reply)"
    if board_after.is_check():
        return f"gives check to {color_name(board_after.turn)} king"
    return "none"


def _discovered_attacks(board_before: chess.Board, board_after: chess.Board, move: chess.Move) -> list[str]:
    """Find pieces (other than the moved piece) of the moving side that now
    attack squares they didn't attack before."""
    mover_color = board_before.turn
    discoveries: list[str] = []
    for sq in chess.SQUARES:
        if sq == move.to_square:
            continue
        piece = board_before.piece_at(sq)
        if piece is None or piece.color != mover_color:
            continue
        if board_after.piece_at(sq) is None or board_after.piece_at(sq).color != mover_color:
            continue
        before_atks = set(board_before.attacks(sq))
        after_atks = set(board_after.attacks(sq))
        gained = after_atks - before_atks
        if not gained:
            continue
        relevant = {g for g in gained if board_after.piece_at(g) is not None
                    and board_after.piece_at(g).color != mover_color}
        if not relevant:
            continue
        for target in sorted(relevant):
            discoveries.append(
                f"{PIECE_NAMES[piece.piece_type]} on {chess.square_name(sq)} now attacks "
                f"{PIECE_NAMES[board_after.piece_at(target).piece_type]} on {chess.square_name(target)}"
            )
    return discoveries


def _newly_hanging_own_pieces(board_before: chess.Board, board_after: chess.Board, move: chess.Move) -> list[str]:
    """List own pieces (other than the moved piece) that became unsafe as a
    side-effect of this move (was safe before, has attackers ≥ defenders now)."""
    mover_color = board_before.turn
    enemy_color = not mover_color
    new_hanging: list[str] = []
    for sq in chess.SQUARES:
        if sq == move.to_square:
            continue
        piece = board_after.piece_at(sq)
        if piece is None or piece.color != mover_color:
            continue
        before_piece = board_before.piece_at(sq)
        if before_piece is None or before_piece.color != mover_color:
            continue

        attackers_after = list(board_after.attackers(enemy_color, sq))
        if not attackers_after:
            continue
        attackers_before = list(board_before.attackers(enemy_color, sq))
        defenders_before = list(board_before.attackers(mover_color, sq))
        defenders_after = [s for s in board_after.attackers(mover_color, sq) if s != sq]

        was_safe_before = not attackers_before or len(defenders_before) >= len(attackers_before)
        is_unsafe_now = not defenders_after or len(attackers_after) > len(defenders_after)
        if not (was_safe_before and is_unsafe_now):
            continue
        atk_str = ", ".join(describe_piece(board_after, a) for a in sorted(attackers_after))
        def_str = (", ".join(describe_piece(board_after, d) for d in sorted(defenders_after))
                   if defenders_after else "nothing")
        new_hanging.append(
            f"{describe_piece(board_after, sq)} — attacked by {atk_str}; defended by {def_str}"
        )
    return new_hanging


def _en_passant_offered(board_after: chess.Board) -> str | None:
    """If this move grants the opponent an en-passant capture, describe it."""
    if board_after.ep_square is None:
        return None
    ep_sq = board_after.ep_square
    pawn_squares = [s for s in board_after.pieces(chess.PAWN, board_after.turn)
                    if ep_sq in board_after.attacks(s)]
    if not pawn_squares:
        return None
    capturers = ", ".join(chess.square_name(s) for s in sorted(pawn_squares))
    return f"yes — {color_name(board_after.turn)} pawn on {capturers} may capture en passant on {chess.square_name(ep_sq)}"


def _moved_piece_hanging_warning(
    board_after: chess.Board,
    move: chess.Move,
    attacker_chain: list,
    defender_chain: list,
) -> str | None:
    """Return a prominent warning when the moved piece is left undefended on
    its new square (more immediate attackers than immediate defenders).

    Skipped when:
    - The piece is a king (illegal king-into-check is rejected by python-chess
      before we ever get here).
    - The opponent is in check AND none of their legal replies captures the
      moved piece. (If the king itself can take it, the piece is still hanging.)
    - There are no opponent attackers, or defenders >= attackers.
    """
    moved_piece = board_after.piece_at(move.to_square)
    if moved_piece is None or moved_piece.piece_type == chess.KING:
        return None
    attackers = [sq for sq, is_xray in attacker_chain if not is_xray]
    defenders = [sq for sq, is_xray in defender_chain if not is_xray]
    if not attackers or len(defenders) >= len(attackers):
        return None
    # When in check, only warn if at least one legal reply actually captures
    # the hanging piece (e.g. king takes the checking rook).
    if board_after.is_check():
        can_capture = any(
            m.to_square == move.to_square for m in board_after.legal_moves
        )
        if not can_capture:
            return None
    atk_str = ", ".join(describe_piece(board_after, s) for s in attackers)
    def_str = ", ".join(describe_piece(board_after, s) for s in defenders) if defenders else "nothing"
    return (
        f"⚠ **{describe_piece(board_after, move.to_square)} is hanging** — "
        f"attacked by {atk_str}; defended by {def_str}. "
        f"The opponent can capture it immediately."
    )


def render_imagine(board_before: chess.Board, move: chess.Move) -> str:
    """Markdown-formatted one-ply look-ahead report for `move` from `board_before`.
    Caller must have already verified the move is legal."""
    board_after = board_before.copy()
    board_after.push(move)

    mover_color = board_before.turn
    moved_piece = board_after.piece_at(move.to_square)

    attacker_chain = compute_attack_chain(board_after, not mover_color, move.to_square)
    defender_chain = [
        (s, x) for s, x in compute_attack_chain(board_after, mover_color, move.to_square)
        if s != move.to_square
    ]

    now_attacks, now_defends = _attacks_and_defenses(board_after, move.to_square)
    before_attacks_enemy, before_defends_own = _attacks_and_defenses(board_before, move.from_square)
    no_longer_attacking = before_attacks_enemy - now_attacks
    no_longer_defending = before_defends_own - now_defends
    no_longer_defending.discard(move.from_square)

    discoveries = _discovered_attacks(board_before, board_after, move)
    newly_hanging = _newly_hanging_own_pieces(board_before, board_after, move)
    ep_text = _en_passant_offered(board_after)
    check_text = _check_status(board_after)

    moved_pinned = board_after.is_pinned(mover_color, move.to_square)
    moved_label = (
        f"{chess.square_name(move.to_square)}, {PIECE_NAMES[moved_piece.piece_type]}"
        f"{' (pinned)' if moved_pinned else ''}"
    )

    hanging_warning = _moved_piece_hanging_warning(
        board_after, move, attacker_chain, defender_chain
    )

    king_before = enemy_king_mobility(board_before)
    king_after = sum(
        1 for m in board_after.legal_moves
        if board_after.piece_at(m.from_square) is not None
        and board_after.piece_at(m.from_square).piece_type == chess.KING
    )
    king_delta = king_after - king_before
    king_sign = "−" if king_delta < 0 else ("+" if king_delta > 0 else "")
    king_mobility_line = (
        f"**Enemy king mobility:** {king_before} → {king_after} "
        f"({king_sign}{abs(king_delta)} squares)"
    )

    out: list[str] = []
    out.append(f"## Move: {_move_summary(board_before, move)}")
    out.append("")
    out.append(f"**Check:** {check_text}")
    out.append(king_mobility_line)
    out.append("")
    if hanging_warning:
        out.append(hanging_warning)
        out.append("")
    out.append(f"**{render_eval_delta_line(board_before, board_after)}**")
    out.append(EVAL_WARNING)
    out.append("")
    out.append("```")
    out.append(render_ascii(board_after))
    out.append("```")
    out.append("")
    out.append(f"**FEN:** `{board_after.fen()}`")
    out.append(f"**Side to move:** {color_name(board_after.turn)}")
    out.append("")

    out.append("## Discovered attacks")
    out.append("")
    if discoveries:
        for d in discoveries:
            out.append(f"- {d}")
    else:
        out.append("- (none)")
    out.append("")

    out.append(f"## Moved piece status ({moved_label})")
    out.append("")
    out.append(f"- **attacked by:** "
               f"{format_chain(board_after, not mover_color, attacker_chain) if attacker_chain else '(none)'}")
    out.append(f"- **defended by:** "
               f"{format_chain(board_after, mover_color, defender_chain) if defender_chain else '(none)'}")
    out.append(f"- **now attacks:** {_format_squares_with_pieces(board_after, now_attacks)}")
    out.append(f"- **now defends:** {_format_squares_with_pieces(board_after, now_defends)}")
    out.append("")

    out.append("## Side-effects on other own pieces")
    out.append("")
    out.append(f"- **no longer attacking:** {_format_squares_with_pieces(board_before, no_longer_attacking)}")
    out.append(f"- **no longer defending:** {_format_squares_with_pieces(board_before, no_longer_defending)}")
    out.append("")

    out.append("## Newly hanging own pieces")
    out.append("")
    if newly_hanging:
        for h in newly_hanging:
            out.append(f"- {h}")
    else:
        out.append("- (none)")
    out.append("")

    if ep_text:
        out.append(f"**En passant available:** {ep_text}")
        out.append("")

    out.append("## Opponent legal replies")
    out.append("")
    legal = list(board_after.legal_moves)
    if not legal:
        out.append(f"_None — game over ({check_text})._")
    else:
        out.append(f"_{len(legal)} legal replies_:")
        out.append("")
        out.append(render_moves_table(board_after, legal))

    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--uci", type=str, default="")
    parser.add_argument("-h", "--help", action="store_true")
    args = parser.parse_args()

    if args.help or not args.uci:
        print(__doc__)
        if not args.uci:
            sys.exit(1)
        return

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

    try:
        move = chess.Move.from_uci(args.uci)
    except Exception:
        print(f"error: --uci ({args.uci}) is illegal: {classify_illegal_move(board, args.uci)}", file=sys.stderr)
        sys.exit(1)
    if move not in board.legal_moves:
        print(f"error: --uci ({args.uci}) is illegal: {classify_illegal_move(board, args.uci)}", file=sys.stderr)
        sys.exit(1)

    print(render_imagine(board, move))


if __name__ == "__main__":
    main()
