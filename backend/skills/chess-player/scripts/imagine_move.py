#!/usr/bin/env python3
"""Imagine a single move from the current position: show the resulting board,
the attack/defense map for the moved piece on its new square, the deltas
(attacks/defenses gained and lost), discovered attacks, newly hanging own
pieces, check/mate status, captures, and the opponent's legal replies.

Reads CHESS_API_BASE and CHESS_GAME_ID from environment (injected by AgentPlayer).
The live board state is **not** mutated; everything is computed on a copy.

Argument:
  --uci <move>    UCI move to imagine (e.g. e2e4, g1f3, e1g1, e7e8q).

If the move is illegal, the script exits nonzero with the same categorised
error format as evaluate_position (no piece, blocked, pinned, etc.).

Output sections (flat, scannable):

  Move:           e2e4  —  pawn e2 → e4 (no capture)
  Check:          gives check / gives checkmate / stalemate / none
  Discovered:     bishop on c1 now attacks h6 (was blocked by pawn on e2)
  Captures:       captures black bishop on f6 (+330cp)
  Moved piece status (e4):
    attacked by:  ...
    defended by:  ...
    now attacks:  ...
    now defends:  ...
  No longer attacking:  ...   (squares the piece controlled before but doesn't now)
  No longer defending:  ...
  Newly hanging:        bishop on c4 — attacked by knight on c6, defended by nothing
  En passant available: yes — black pawn on d5 may capture en passant
  Opponent legal moves: 23 (e7e5, b8c6, ...)
"""

import argparse
import importlib.util
import json
import os
import sys
import urllib.request
from pathlib import Path

import chess


# Reuse helpers from show_position (chain rendering, piece labels, pinned, etc.).
_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("show_position", _HERE / "show_position.py")
_show_position = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("show_position", _show_position)
_spec.loader.exec_module(_show_position)

# And the illegal-move classifier from evaluate_position.
_spec_ep = importlib.util.spec_from_file_location("evaluate_position", _HERE / "evaluate_position.py")
_evaluate_position = importlib.util.module_from_spec(_spec_ep)
sys.modules.setdefault("evaluate_position", _evaluate_position)
_spec_ep.loader.exec_module(_evaluate_position)


PIECE_NAMES = _show_position.PIECE_NAMES
render_ascii = _show_position.render_ascii
compute_attack_chain = _show_position.compute_attack_chain
format_chain = _show_position.format_chain
piece_label = _show_position.piece_label
classify_illegal_move = _evaluate_position.classify_illegal_move
MATERIAL = _evaluate_position.MATERIAL


def _color_name(color: bool) -> str:
    return "white" if color == chess.WHITE else "black"


def _describe_piece(board: chess.Board, square: int) -> str:
    piece = board.piece_at(square)
    return f"{PIECE_NAMES[piece.piece_type]} on {chess.square_name(square)}"


def _attacks_from(board: chess.Board, square: int) -> set[int]:
    """Squares the piece on `square` controls (per board.attacks()).
    For pawns this is the diagonal squares only — pawn pushes are not attacks
    and don't belong in attack/defense deltas."""
    return set(board.attacks(square))


def _attacks_and_defenses(board: chess.Board, square: int) -> tuple[set[int], set[int]]:
    """Return (squares_attacking_opponent, squares_defending_own) for the
    piece on `square`. Splits board.attacks() by the color of the piece sitting
    on each controlled square."""
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
    parts = sorted(squares)
    return ", ".join(_describe_piece(board, s) for s in parts)


def _move_summary(board_before: chess.Board, move: chess.Move) -> str:
    """One-line description of the move itself."""
    piece = board_before.piece_at(move.from_square)
    piece_name = PIECE_NAMES[piece.piece_type]
    from_name = chess.square_name(move.from_square)
    to_name = chess.square_name(move.to_square)
    san = board_before.san(move)

    # Detect special move types.
    is_ep = board_before.is_en_passant(move)
    is_castle = board_before.is_castling(move)

    if is_castle:
        side = "kingside" if chess.square_file(move.to_square) > chess.square_file(move.from_square) else "queenside"
        return f"{move.uci()} ({san})  —  {side} castle"

    captured = board_before.piece_at(move.to_square)
    if is_ep:
        # The captured pawn sits on the from-rank, to-file.
        ep_sq = chess.square(chess.square_file(move.to_square), chess.square_rank(move.from_square))
        captured = board_before.piece_at(ep_sq)
        value = MATERIAL[chess.PAWN]
        return (
            f"{move.uci()} ({san})  —  {piece_name} {from_name} → {to_name}, "
            f"en passant captures {_color_name(captured.color)} pawn on {chess.square_name(ep_sq)} (+{value}cp)"
        )

    promo_extra = f", promotes to {PIECE_NAMES[move.promotion]}" if move.promotion is not None else ""

    if captured is not None:
        value = MATERIAL[captured.piece_type] if captured.piece_type != chess.KING else 0
        return (
            f"{move.uci()} ({san})  —  {piece_name} {from_name} → {to_name}, "
            f"captures {_color_name(captured.color)} {PIECE_NAMES[captured.piece_type]} (+{value}cp)"
            f"{promo_extra}"
        )

    return f"{move.uci()} ({san})  —  {piece_name} {from_name} → {to_name} (no capture){promo_extra}"


def _check_status(board_after: chess.Board) -> str:
    if board_after.is_checkmate():
        return "gives checkmate"
    if board_after.is_stalemate():
        return "stalemate (no legal reply)"
    if board_after.is_check():
        return f"gives check to {_color_name(board_after.turn)} king"
    return "none"


def _discovered_attacks(board_before: chess.Board, board_after: chess.Board, move: chess.Move) -> list[str]:
    """Find pieces (other than the moved piece) of the moving side that now
    attack squares they didn't attack before. Reports as
    'bishop on c1 now attacks h6 (was blocked by pawn on e2)' when the new
    attack runs along a ray that passed through the vacated from-square."""
    mover_color = board_before.turn
    from_sq = move.from_square

    discoveries: list[str] = []
    for sq in chess.SQUARES:
        if sq == move.to_square:
            continue  # the moved piece itself isn't a "discovery"
        piece = board_before.piece_at(sq)
        if piece is None or piece.color != mover_color:
            continue
        # Did this piece survive the move? (en passant / capture don't remove own pieces, so it survives.)
        if board_after.piece_at(sq) is None or board_after.piece_at(sq).color != mover_color:
            continue
        before_atks = set(board_before.attacks(sq))
        after_atks = set(board_after.attacks(sq))
        gained = after_atks - before_atks
        if not gained:
            continue
        # Only report gains that are "real" — i.e. landed on enemy pieces or
        # empty squares the piece now controls. Filter to enemy pieces to keep
        # the output focused on tactical content.
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
    """List own pieces (other than the moved piece) that have at least one
    enemy attacker after the move but did not before, or that had defenders
    before but don't now — i.e. became hanging as a side-effect of this move."""
    mover_color = board_before.turn
    enemy_color = not mover_color
    new_hanging: list[str] = []
    for sq in chess.SQUARES:
        if sq == move.to_square:
            continue  # moved piece's own status is reported separately
        piece = board_after.piece_at(sq)
        if piece is None or piece.color != mover_color:
            continue
        # The piece must have existed before too (we're not flagging the moved piece).
        before_piece = board_before.piece_at(sq)
        if before_piece is None or before_piece.color != mover_color:
            continue

        attackers_after = list(board_after.attackers(enemy_color, sq))
        if not attackers_after:
            continue
        attackers_before = list(board_before.attackers(enemy_color, sq))
        defenders_before = list(board_before.attackers(mover_color, sq))
        defenders_after = [s for s in board_after.attackers(mover_color, sq) if s != sq]

        was_safe_before = (not attackers_before) or (len(defenders_before) >= len(attackers_before))
        is_unsafe_now = (not defenders_after) or (len(attackers_after) > len(defenders_after))
        if was_safe_before and is_unsafe_now:
            atk_str = ", ".join(_describe_piece(board_after, a) for a in sorted(attackers_after))
            def_str = (", ".join(_describe_piece(board_after, d) for d in sorted(defenders_after))
                       if defenders_after else "nothing")
            new_hanging.append(
                f"{_describe_piece(board_after, sq)} — attacked by {atk_str}; defended by {def_str}"
            )
    return new_hanging


def _en_passant_offered(board_after: chess.Board) -> str | None:
    """If this move grants the opponent an en-passant capture, describe it."""
    if board_after.ep_square is None:
        return None
    ep_sq = board_after.ep_square
    # The opponent (now to move) needs a pawn that attacks ep_sq.
    pawn_squares = [s for s in board_after.pieces(chess.PAWN, board_after.turn)
                    if ep_sq in board_after.attacks(s)]
    if not pawn_squares:
        # Square is technically set in FEN but no opponent pawn can actually take.
        return None
    capturers = ", ".join(chess.square_name(s) for s in sorted(pawn_squares))
    return f"yes — {_color_name(board_after.turn)} pawn on {capturers} may capture en passant on {chess.square_name(ep_sq)}"


def _opponent_legal_moves(board_after: chess.Board) -> tuple[int, list[str]]:
    moves = sorted(m.uci() for m in board_after.legal_moves)
    return len(moves), moves


def render_imagine(board_before: chess.Board, move: chess.Move) -> str:
    """Build the full report for `move` from `board_before`. Caller must
    have already verified the move is legal."""
    board_after = board_before.copy()
    board_after.push(move)

    mover_color = board_before.turn
    moved_piece = board_after.piece_at(move.to_square)

    # Attack/defense map for the moved piece on its new square.
    attacker_chain = compute_attack_chain(board_after, not mover_color, move.to_square)
    defender_chain = [(s, x) for s, x in compute_attack_chain(board_after, mover_color, move.to_square) if s != move.to_square]

    now_attacks, now_defends = _attacks_and_defenses(board_after, move.to_square)

    # Deltas: what the piece attacked/defended from its old square that it no
    # longer reaches from its new square. Compute attacks-of from the BEFORE
    # board (the piece is still on from_sq there).
    before_attacks_enemy, before_defends_own = _attacks_and_defenses(board_before, move.from_square)
    # Map "still attacking after move" — the moved piece on its new square.
    no_longer_attacking = before_attacks_enemy - now_attacks
    no_longer_defending = before_defends_own - now_defends
    # But a piece can stop "defending" a square because the piece it was
    # defending is itself the moved piece — exclude the from_sq from the
    # "no longer defending" list (we already moved off it).
    no_longer_defending.discard(move.from_square)

    discoveries = _discovered_attacks(board_before, board_after, move)
    newly_hanging = _newly_hanging_own_pieces(board_before, board_after, move)
    ep_text = _en_passant_offered(board_after)
    n_replies, replies = _opponent_legal_moves(board_after)
    check_text = _check_status(board_after)

    moved_pinned = board_after.is_pinned(mover_color, move.to_square)

    lines: list[str] = []
    lines.append(render_ascii(board_after))
    lines.append("")
    lines.append(f"FEN: {board_after.fen()}")
    lines.append(f"Side to move: {_color_name(board_after.turn)}")
    lines.append("")
    lines.append(f"Move:               {_move_summary(board_before, move)}")
    lines.append(f"Check:              {check_text}")

    if discoveries:
        lines.append("Discovered attacks:")
        for d in discoveries:
            lines.append(f"  - {d}")
    else:
        lines.append("Discovered attacks: (none)")

    # Moved piece status block.
    lines.append("")
    lines.append(f"Moved piece status ({chess.square_name(move.to_square)}, "
                 f"{PIECE_NAMES[moved_piece.piece_type]}{' (pinned)' if moved_pinned else ''}):")
    lines.append(f"  attacked by:    "
                 f"{format_chain(board_after, not mover_color, attacker_chain) if attacker_chain else '(none)'}")
    lines.append(f"  defended by:    "
                 f"{format_chain(board_after, mover_color, defender_chain) if defender_chain else '(none)'}")
    lines.append(f"  now attacks:    {_format_squares_with_pieces(board_after, now_attacks)}")
    lines.append(f"  now defends:    {_format_squares_with_pieces(board_after, now_defends)}")

    # Deltas relative to the old square.
    lines.append("")
    lines.append(f"No longer attacking: {_format_squares_with_pieces(board_before, no_longer_attacking)}")
    lines.append(f"No longer defending: {_format_squares_with_pieces(board_before, no_longer_defending)}")

    # Side-effects on other own pieces.
    lines.append("")
    if newly_hanging:
        lines.append("Newly hanging own pieces:")
        for h in newly_hanging:
            lines.append(f"  - {h}")
    else:
        lines.append("Newly hanging own pieces: (none)")

    # En passant offered to opponent (if any).
    if ep_text:
        lines.append(f"En passant available: {ep_text}")

    # Opponent's legal replies.
    lines.append("")
    if n_replies == 0:
        lines.append(f"Opponent legal moves: 0 (game over — {check_text})")
    else:
        preview = ", ".join(replies[:12])
        suffix = f", ... (+{n_replies - 12} more)" if n_replies > 12 else ""
        lines.append(f"Opponent legal moves: {n_replies} ({preview}{suffix})")

    return "\n".join(lines)


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

    # Validate legality, using the same classifier as evaluate_position.
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
