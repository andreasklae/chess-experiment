#!/usr/bin/env python3
"""Evaluate the current position with material + piece-square tables.

Reads CHESS_API_BASE and CHESS_GAME_ID from environment (injected by AgentPlayer).

Optional argument:
  --moves UCI[,UCI,...]   Comma-separated UCI moves to play out from the live
                          position before evaluating. Useful for comparing
                          candidate lines without actually committing a move.
                          Example: --moves e2e4,e7e5,g1f3

If any move in the list is illegal, the script exits with a categorised error
naming which move (1-indexed) failed and why, so the agent can revise its
candidate line. The board state is not mutated on the backend regardless.

Scoring:
  total = sum(piece scores for white) - sum(piece scores for black)
  piece score = base material value (centipawns) + PST bonus for that square
  King material (20000) is excluded from the total — only kings' PST contributes.

PSTs are Tomasz Michniewski's Simplified Evaluation Function tables.
Kings have two tables; choice is per-side using Michniewski's canonical rule:
  endgame king table iff that side has no queen, or has queen + no other pieces.

Phase annotation is delegated to show_position.detect_phase to keep the two
scripts in lockstep on phase classification.

Output (plain text):

    Line: 1.e4 e5 2.Nf3        (only when --moves is supplied)
    After: e2e4, e7e5, g1f3    (only when --moves is supplied)
    Side to move: black
    Evaluation: +0.30 (roughly equal)
    Material:   white 4000, black 4000 (+0)
    PST:        white +35, black +5 (+30)
    Phase:      early opening
"""

import argparse
import importlib.util
import json
import os
import sys
import urllib.request
from pathlib import Path

import chess


# Import phase detection from the sibling show_position.py.
_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("show_position", _HERE / "show_position.py")
_show_position = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("show_position", _show_position)
_spec.loader.exec_module(_show_position)
detect_phase = _show_position.detect_phase


# ── Material values (centipawns) ───────────────────────────────────────────

MATERIAL = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,  # used for king PST lookup only; excluded from totals
}


# ── Piece-square tables (Michniewski's Simplified Evaluation Function) ──────
#
# Each table is written from White's perspective with rank 8 as the first row
# (top, as a human reads a board diagram) and rank 1 as the last row.
# A flatten step below converts each table to a 64-element list indexed by
# python-chess square IDs (a1=0 .. h8=63) for White; Black mirrors vertically.

_PAWN_TABLE = [
    0,  0,  0,  0,  0,  0,  0,  0,
   50, 50, 50, 50, 50, 50, 50, 50,
   10, 10, 20, 30, 30, 20, 10, 10,
    5,  5, 10, 25, 25, 10,  5,  5,
    0,  0,  0, 20, 20,  0,  0,  0,
    5, -5,-10,  0,  0,-10, -5,  5,
    5, 10, 10,-20,-20, 10, 10,  5,
    0,  0,  0,  0,  0,  0,  0,  0,
]

_KNIGHT_TABLE = [
  -50,-40,-30,-30,-30,-30,-40,-50,
  -40,-20,  0,  0,  0,  0,-20,-40,
  -30,  0, 10, 15, 15, 10,  0,-30,
  -30,  5, 15, 20, 20, 15,  5,-30,
  -30,  0, 15, 20, 20, 15,  0,-30,
  -30,  5, 10, 15, 15, 10,  5,-30,
  -40,-20,  0,  5,  5,  0,-20,-40,
  -50,-40,-30,-30,-30,-30,-40,-50,
]

_BISHOP_TABLE = [
  -20,-10,-10,-10,-10,-10,-10,-20,
  -10,  0,  0,  0,  0,  0,  0,-10,
  -10,  0,  5, 10, 10,  5,  0,-10,
  -10,  5,  5, 10, 10,  5,  5,-10,
  -10,  0, 10, 10, 10, 10,  0,-10,
  -10, 10, 10, 10, 10, 10, 10,-10,
  -10,  5,  0,  0,  0,  0,  5,-10,
  -20,-10,-10,-10,-10,-10,-10,-20,
]

_ROOK_TABLE = [
    0,  0,  0,  0,  0,  0,  0,  0,
    5, 10, 10, 10, 10, 10, 10,  5,
   -5,  0,  0,  0,  0,  0,  0, -5,
   -5,  0,  0,  0,  0,  0,  0, -5,
   -5,  0,  0,  0,  0,  0,  0, -5,
   -5,  0,  0,  0,  0,  0,  0, -5,
   -5,  0,  0,  0,  0,  0,  0, -5,
    0,  0,  0,  5,  5,  0,  0,  0,
]

_QUEEN_TABLE = [
  -20,-10,-10, -5, -5,-10,-10,-20,
  -10,  0,  0,  0,  0,  0,  0,-10,
  -10,  0,  5,  5,  5,  5,  0,-10,
   -5,  0,  5,  5,  5,  5,  0, -5,
    0,  0,  5,  5,  5,  5,  0, -5,
  -10,  5,  5,  5,  5,  5,  0,-10,
  -10,  0,  5,  0,  0,  0,  0,-10,
  -20,-10,-10, -5, -5,-10,-10,-20,
]

_KING_MIDDLEGAME_TABLE = [
  -30,-40,-40,-50,-50,-40,-40,-30,
  -30,-40,-40,-50,-50,-40,-40,-30,
  -30,-40,-40,-50,-50,-40,-40,-30,
  -30,-40,-40,-50,-50,-40,-40,-30,
  -20,-30,-30,-40,-40,-30,-30,-20,
  -10,-20,-20,-20,-20,-20,-20,-10,
   20, 20,  0,  0,  0,  0, 20, 20,
   20, 30, 10,  0,  0, 10, 30, 20,
]

_KING_ENDGAME_TABLE = [
  -50,-40,-30,-20,-20,-30,-40,-50,
  -30,-20,-10,  0,  0,-10,-20,-30,
  -30,-10, 20, 30, 30, 20,-10,-30,
  -30,-10, 30, 40, 40, 30,-10,-30,
  -30,-10, 30, 40, 40, 30,-10,-30,
  -30,-10, 20, 30, 30, 20,-10,-30,
  -30,-30,  0,  0,  0,  0,-30,-30,
  -50,-30,-30,-30,-30,-30,-30,-50,
]


def _flatten_for_white(table: list[int]) -> list[int]:
    """Tables above are written top-down (rank 8 first). Convert to a
    64-element list indexed by python-chess square IDs (a1=0..h8=63)."""
    out = [0] * 64
    for printed_row in range(8):  # 0 = rank 8, 7 = rank 1
        rank = 7 - printed_row
        for file in range(8):
            out[chess.square(file, rank)] = table[printed_row * 8 + file]
    return out


_PST_WHITE = {
    chess.PAWN: _flatten_for_white(_PAWN_TABLE),
    chess.KNIGHT: _flatten_for_white(_KNIGHT_TABLE),
    chess.BISHOP: _flatten_for_white(_BISHOP_TABLE),
    chess.ROOK: _flatten_for_white(_ROOK_TABLE),
    chess.QUEEN: _flatten_for_white(_QUEEN_TABLE),
}
_KING_MG_WHITE = _flatten_for_white(_KING_MIDDLEGAME_TABLE)
_KING_EG_WHITE = _flatten_for_white(_KING_ENDGAME_TABLE)


def _mirror_square(square: int) -> int:
    """Flip a square vertically (a1<->a8, h2<->h7, etc.) for black PST lookup."""
    return chess.square(chess.square_file(square), 7 - chess.square_rank(square))


def pst_value(piece: chess.Piece, square: int, king_eg: bool) -> int:
    """Return the PST bonus for `piece` on `square`. `king_eg` selects the
    endgame king table when the piece is a king."""
    lookup_sq = square if piece.color == chess.WHITE else _mirror_square(square)
    if piece.piece_type == chess.KING:
        table = _KING_EG_WHITE if king_eg else _KING_MG_WHITE
        return table[lookup_sq]
    return _PST_WHITE[piece.piece_type][lookup_sq]


def use_endgame_king_table(board: chess.Board, color: bool) -> bool:
    """Michniewski's rule, per-side: endgame king table when this side has
    no queen, OR has a queen and no other pieces (just queen + king)."""
    queens = board.pieces(chess.QUEEN, color)
    if not queens:
        return True
    # Count this side's non-king, non-queen pieces.
    non_queen_non_king = 0
    for piece_type in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK):
        non_queen_non_king += len(board.pieces(piece_type, color))
    return non_queen_non_king == 0


def evaluate(board: chess.Board) -> dict:
    """Return a dict with per-side material and PST totals plus the net score
    (in centipawns, white positive). King material is excluded from totals."""
    sides = {chess.WHITE: {"material": 0, "pst": 0}, chess.BLACK: {"material": 0, "pst": 0}}
    king_eg = {color: use_endgame_king_table(board, color) for color in (chess.WHITE, chess.BLACK)}

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue
        if piece.piece_type != chess.KING:
            sides[piece.color]["material"] += MATERIAL[piece.piece_type]
        sides[piece.color]["pst"] += pst_value(piece, square, king_eg[piece.color])

    white_total = sides[chess.WHITE]["material"] + sides[chess.WHITE]["pst"]
    black_total = sides[chess.BLACK]["material"] + sides[chess.BLACK]["pst"]
    return {
        "white": sides[chess.WHITE],
        "black": sides[chess.BLACK],
        "white_total": white_total,
        "black_total": black_total,
        "score": white_total - black_total,
        "king_endgame_white": king_eg[chess.WHITE],
        "king_endgame_black": king_eg[chess.BLACK],
    }


def _verdict(score: int) -> str:
    """Plain-language band for the score (in centipawns, white-positive)."""
    if score == 0:
        return "equal"
    abs_score = abs(score)
    side = "white" if score > 0 else "black"
    if abs_score >= 300:
        return f"{side} winning"
    if abs_score >= 100:
        return f"{side} clearly better"
    if abs_score >= 30:
        return f"{side} slightly better"
    return "roughly equal"


_PIECE_NAMES = {
    chess.PAWN: "pawn", chess.KNIGHT: "knight", chess.BISHOP: "bishop",
    chess.ROOK: "rook", chess.QUEEN: "queen", chess.KING: "king",
}


def _color_name(color: bool) -> str:
    return "white" if color == chess.WHITE else "black"


def classify_illegal_move(board: chess.Board, uci: str) -> str:
    """Return a human-readable reason why `uci` is illegal in `board`.
    Assumes the move is known to be illegal (or malformed); inspects board
    state to categorise the failure. Goes through cases in priority order:
    malformed -> piece presence -> ownership -> geometry -> blocked path ->
    own-piece capture -> promotion mismatch -> castling -> in-check ->
    leaves-king-in-check (pin) -> generic."""
    # 1. Malformed: not a parseable UCI string at all.
    try:
        move = chess.Move.from_uci(uci)
    except Exception:
        return f"'{uci}' is not a valid UCI move (expected e.g. e2e4, g1f3, e7e8q)"

    from_sq, to_sq = move.from_square, move.to_square
    from_name, to_name = chess.square_name(from_sq), chess.square_name(to_sq)
    piece = board.piece_at(from_sq)

    # 2. No piece on source.
    if piece is None:
        return f"no piece on {from_name}"

    # 3. Wrong color.
    if piece.color != board.turn:
        return (
            f"the piece on {from_name} is {_color_name(piece.color)}, "
            f"but it's {_color_name(board.turn)}'s turn"
        )

    piece_name = _PIECE_NAMES[piece.piece_type]
    dest = board.piece_at(to_sq)

    # 4. Destination occupied by own piece (caught before geometry — a more
    # informative message than "can't move there").
    if dest is not None and dest.color == piece.color:
        return (
            f"destination {to_name} is occupied by your own "
            f"{_PIECE_NAMES[dest.piece_type]}"
        )

    # 5. Castling-specific. A king moving two squares is a castle attempt.
    if piece.piece_type == chess.KING and abs(chess.square_file(from_sq) - chess.square_file(to_sq)) == 2:
        return _castling_reason(board, move)

    # 6. Promotion mismatch.
    is_pawn = piece.piece_type == chess.PAWN
    to_rank = chess.square_rank(to_sq)
    reaches_back_rank = is_pawn and to_rank in (0, 7)
    if reaches_back_rank and move.promotion is None:
        return (
            f"pawn move to {to_name} requires a promotion piece "
            f"(e.g. {uci}q for queen, {uci}n for knight)"
        )
    if move.promotion is not None and not reaches_back_rank:
        return (
            f"promotion specified but {piece_name} on {from_name} -> {to_name} "
            f"is not a pawn reaching the last rank"
        )

    # 7. Blocked path — check this FIRST for sliders, since attacks()
    # already accounts for blocking and would mislabel a blocked move
    # as "cannot reach". Only checks along rays the piece can actually use.
    if piece.piece_type in (chess.ROOK, chess.BISHOP, chess.QUEEN):
        blocker = _first_blocker_for_piece(board, piece.piece_type, from_sq, to_sq)
        if blocker is not None:
            blocking_piece = board.piece_at(blocker)
            return (
                f"path from {from_name} to {to_name} is blocked by "
                f"{_color_name(blocking_piece.color)} {_PIECE_NAMES[blocking_piece.piece_type]} "
                f"on {chess.square_name(blocker)}"
            )

    # 8. Geometric reachability: does this piece type, in principle, move
    # like that? For sliders we've already cleared blockers; if attacks()
    # still doesn't include to_sq, the move isn't on a valid ray at all.
    if not _piece_can_reach(board, piece, from_sq, to_sq):
        return f"{piece_name} on {from_name} cannot move to {to_name}"

    # 9. The move is geometrically fine and the path is clear. The only
    # remaining reasons are king-safety: either you're in check and this
    # move doesn't address it, or the move exposes your king (pin).
    if board.is_check():
        return f"you are in check and {uci} does not resolve it"

    # Test whether the piece is pinned in a way that this move violates.
    if board.is_pinned(piece.color, from_sq):
        return (
            f"{piece_name} on {from_name} is pinned and cannot move to {to_name} "
            f"(would expose your king)"
        )

    # 10. Generic fallback — shouldn't normally reach here for legal-format
    # moves, but covers en-passant edge cases and anything else missed.
    return f"illegal move {uci}"


def _piece_can_reach(board: chess.Board, piece: chess.Piece, from_sq: int, to_sq: int) -> bool:
    """Does this piece type, on this square, attack/move-to `to_sq` ignoring
    pins and king safety? For pawns, also accepts forward pushes."""
    if piece.piece_type == chess.PAWN:
        # Forward push (1 or 2 squares from start rank), or diagonal capture.
        direction = 1 if piece.color == chess.WHITE else -1
        ff, fr = chess.square_file(from_sq), chess.square_rank(from_sq)
        tf, tr = chess.square_file(to_sq), chess.square_rank(to_sq)
        # Diagonal capture: attacks() handles it correctly (it reports the
        # squares a pawn attacks).
        if to_sq in board.attacks(from_sq):
            # Diagonal moves are only legal as captures or en passant.
            if board.piece_at(to_sq) is not None or to_sq == board.ep_square:
                return True
            return False
        # Forward push: must be on the same file with the right delta.
        if ff != tf:
            return False
        if tr - fr == direction:
            return board.piece_at(to_sq) is None
        if tr - fr == 2 * direction and fr == (1 if piece.color == chess.WHITE else 6):
            intermediate = chess.square(ff, fr + direction)
            return board.piece_at(intermediate) is None and board.piece_at(to_sq) is None
        return False
    # All other pieces: attacks() gives the squares the piece controls.
    return to_sq in board.attacks(from_sq)


def _first_blocker_for_piece(board: chess.Board, piece_type: int, from_sq: int, to_sq: int) -> int | None:
    """For a sliding piece, return the first occupied square strictly between
    from_sq and to_sq along a ray the piece can use. Returns None if the move
    is not on a usable ray for this piece type, or if the path is clear."""
    ff, fr = chess.square_file(from_sq), chess.square_rank(from_sq)
    tf, tr = chess.square_file(to_sq), chess.square_rank(to_sq)
    df, dr = tf - ff, tr - fr
    if max(abs(df), abs(dr)) < 2:
        return None  # adjacent or same square — not a slide
    is_orthogonal = (df == 0) ^ (dr == 0)
    is_diagonal = df != 0 and dr != 0 and abs(df) == abs(dr)
    if not (is_orthogonal or is_diagonal):
        return None  # not a straight line — not a slider move at all
    # Filter by piece type.
    if piece_type == chess.ROOK and not is_orthogonal:
        return None
    if piece_type == chess.BISHOP and not is_diagonal:
        return None
    # Queen handles both.
    step_f = (df > 0) - (df < 0)
    step_r = (dr > 0) - (dr < 0)
    f, r = ff + step_f, fr + step_r
    while (f, r) != (tf, tr):
        sq = chess.square(f, r)
        if board.piece_at(sq) is not None:
            return sq
        f += step_f
        r += step_r
    return None


def _castling_reason(board: chess.Board, move: chess.Move) -> str:
    """Diagnose a failed castling attempt."""
    color = board.turn
    kingside = chess.square_file(move.to_square) > chess.square_file(move.from_square)
    side_name = "kingside" if kingside else "queenside"
    if board.is_check():
        return f"cannot castle {side_name}: king is in check"
    if not board.has_castling_rights(color):
        return f"cannot castle {side_name}: castling rights already lost"
    if kingside and not board.has_kingside_castling_rights(color):
        return f"cannot castle kingside: kingside castling rights lost"
    if not kingside and not board.has_queenside_castling_rights(color):
        return f"cannot castle queenside: queenside castling rights lost"
    # Squares between king and rook must be empty.
    rank = 0 if color == chess.WHITE else 7
    if kingside:
        between = [chess.square(f, rank) for f in (5, 6)]  # f1/f8, g1/g8
    else:
        between = [chess.square(f, rank) for f in (1, 2, 3)]  # b1, c1, d1
    for sq in between:
        if board.piece_at(sq) is not None:
            blocker = board.piece_at(sq)
            return (
                f"cannot castle {side_name}: {chess.square_name(sq)} is occupied by "
                f"{_color_name(blocker.color)} {_PIECE_NAMES[blocker.piece_type]}"
            )
    # Otherwise: the king passes through or lands on an attacked square.
    pass_squares = [chess.square(f, rank) for f in (4, 5, 6)] if kingside else [chess.square(f, rank) for f in (2, 3, 4)]
    for sq in pass_squares:
        if board.is_attacked_by(not color, sq):
            return (
                f"cannot castle {side_name}: king would pass through or land on "
                f"{chess.square_name(sq)}, which is attacked"
            )
    return f"cannot castle {side_name}"


class MoveListError(Exception):
    """Raised when a move in --moves can't be applied. Carries the 1-indexed
    move number, the offending UCI string, and a human-readable reason."""

    def __init__(self, index: int, uci: str, reason: str):
        self.index = index
        self.uci = uci
        self.reason = reason
        super().__init__(f"move {index} ({uci}): {reason}")


def parse_moves_arg(raw: str) -> list[str]:
    """Comma-separated UCI list. Empty -> []. Whitespace tolerated."""
    if not raw:
        return []
    return [m.strip() for m in raw.split(",") if m.strip()]


def apply_line(board: chess.Board, ucis: list[str]) -> tuple[chess.Board, list[str]]:
    """Apply the UCI moves to a copy of `board`. Returns (final_board, san_moves).
    Raises MoveListError on the first illegal move."""
    work = board.copy()
    san_moves: list[str] = []
    for i, uci in enumerate(ucis, start=1):
        try:
            move = chess.Move.from_uci(uci)
        except Exception:
            raise MoveListError(i, uci, classify_illegal_move(work, uci))
        if move not in work.legal_moves:
            raise MoveListError(i, uci, classify_illegal_move(work, uci))
        san_moves.append(work.san(move))
        work.push(move)
    return work, san_moves


def format_san_line(starting_board: chess.Board, san_moves: list[str]) -> str:
    """Render an SAN line with move numbers: '1.e4 e5 2.Nf3 Nc6 ...'.
    Respects the starting fullmove number and side-to-move."""
    if not san_moves:
        return ""
    parts: list[str] = []
    move_num = starting_board.fullmove_number
    white_to_move = starting_board.turn == chess.WHITE
    i = 0
    while i < len(san_moves):
        if white_to_move:
            white = san_moves[i]
            black = san_moves[i + 1] if i + 1 < len(san_moves) else None
            if black is not None:
                parts.append(f"{move_num}.{white} {black}")
                i += 2
            else:
                parts.append(f"{move_num}.{white}")
                i += 1
            move_num += 1
        else:
            # Starting from black-to-move: render as "<n>...<black>" then continue.
            black = san_moves[i]
            parts.append(f"{move_num}...{black}")
            i += 1
            move_num += 1
            white_to_move = True
    return " ".join(parts)


def render_evaluation(board: chess.Board, san_moves: list[str] | None = None, ucis: list[str] | None = None, starting_board: chess.Board | None = None) -> str:
    """Render the evaluation. If `san_moves` / `ucis` are supplied (with the
    `starting_board` they were applied from), prepend Line + After headers."""
    ev = evaluate(board)
    score = ev["score"]
    phase, _, _ = detect_phase(board)
    pawns = score / 100.0

    sign = "+" if score >= 0 else "-"
    headline = f"Evaluation: {sign}{abs(pawns):.2f} ({_verdict(score)})"

    mat_diff = ev["white"]["material"] - ev["black"]["material"]
    pst_diff = ev["white"]["pst"] - ev["black"]["pst"]

    lines: list[str] = []
    if ucis:
        assert starting_board is not None and san_moves is not None
        lines.append(f"Line: {format_san_line(starting_board, san_moves)}")
        lines.append(f"After: {', '.join(ucis)}")
    lines.extend([
        f"Side to move: {_color_name(board.turn)}",
        headline,
        f"Material:   white {ev['white']['material']}, black {ev['black']['material']} ({mat_diff:+d})",
        f"PST:        white {ev['white']['pst']:+d}, black {ev['black']['pst']:+d} ({pst_diff:+d})",
        f"Phase:      {phase}",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--moves", type=str, default="")
    parser.add_argument("-h", "--help", action="store_true")
    args = parser.parse_args()

    if args.help:
        print(__doc__)
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

    starting_board = chess.Board(fen)
    ucis = parse_moves_arg(args.moves)

    if not ucis:
        print(render_evaluation(starting_board))
        return

    try:
        final_board, san_moves = apply_line(starting_board, ucis)
    except MoveListError as exc:
        # Hard error per the script contract: agent's candidate line is bad
        # and it needs to revise rather than receive a misleading partial eval.
        print(
            f"error: move {exc.index} of --moves ({exc.uci}) is illegal: {exc.reason}",
            file=sys.stderr,
        )
        print(
            f"hint: --moves takes a comma-separated list of UCI moves to play "
            f"from the live position (e.g. --moves e2e4,e7e5,g1f3)",
            file=sys.stderr,
        )
        sys.exit(1)

    print(render_evaluation(final_board, san_moves=san_moves, ucis=ucis, starting_board=starting_board))


if __name__ == "__main__":
    main()
