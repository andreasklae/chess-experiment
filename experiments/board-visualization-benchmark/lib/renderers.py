"""Board renderers — the formats under test in Stage 2.

Each renderer maps a chess.Board to a string. The FORMAT is the independent
variable; everything else (position, probe questions) is held fixed.

Fixed controls (always benchmarked):
  fen          — the raw FEN, the model's current per-turn input. The format to beat.
  ascii_grid   — python-chess str(board): letters, uppercase=White, lowercase=Black,
                 '.'=empty, with rank/file labels. This is exactly what the live
                 show_position tool draws today (render_ascii in show_position.py).

Candidate formats (Stage 1 may add to / confirm these):
  unicode_grid — same grid but Unicode chess glyphs (♔♕♖♗♘♙ / ♚♛♜♝♞♟).
  piece_list   — coordinate piece list ("White: Ke1, Qd1, Ra1, ...; Black: ...").
                 Close to how imagine_move already talks about the board.

All renderers are pure and deterministic.
"""
from __future__ import annotations

import chess

# Unicode glyphs. White = outline, Black = filled (standard convention).
_UNICODE = {
    (chess.PAWN, chess.WHITE): "♙", (chess.KNIGHT, chess.WHITE): "♘",
    (chess.BISHOP, chess.WHITE): "♗", (chess.ROOK, chess.WHITE): "♖",
    (chess.QUEEN, chess.WHITE): "♕", (chess.KING, chess.WHITE): "♔",
    (chess.PAWN, chess.BLACK): "♟", (chess.KNIGHT, chess.BLACK): "♞",
    (chess.BISHOP, chess.BLACK): "♝", (chess.ROOK, chess.BLACK): "♜",
    (chess.QUEEN, chess.BLACK): "♛", (chess.KING, chess.BLACK): "♚",
}

_PIECE_NAME = {
    chess.PAWN: "P", chess.KNIGHT: "N", chess.BISHOP: "B",
    chess.ROOK: "R", chess.QUEEN: "Q", chess.KING: "K",
}


def render_fen(board: chess.Board) -> str:
    return board.fen()


def render_ascii_grid(board: chess.Board) -> str:
    """Mirrors show_position.render_ascii exactly (letters + rank/file labels)."""
    rows = str(board).split("\n")
    labelled = [f"{8 - i}  {row}" for i, row in enumerate(rows)]
    labelled.append("   a b c d e f g h")
    return "\n".join(labelled)


def render_unicode_grid(board: chess.Board) -> str:
    lines = []
    for rank in range(7, -1, -1):
        cells = []
        for file in range(8):
            sq = chess.square(file, rank)
            piece = board.piece_at(sq)
            cells.append(_UNICODE[(piece.piece_type, piece.color)] if piece else "·")
        lines.append(f"{rank + 1}  " + " ".join(cells))
    lines.append("   a b c d e f g h")
    return "\n".join(lines)


def render_piece_list(board: chess.Board) -> str:
    def side(color: bool) -> str:
        order = [chess.KING, chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN]
        items = []
        for pt in order:
            for sq in sorted(board.pieces(pt, color)):
                items.append(f"{_PIECE_NAME[pt]}{chess.square_name(sq)}")
        return ", ".join(items) if items else "(none)"
    return f"White: {side(chess.WHITE)}\nBlack: {side(chess.BLACK)}"


def render_fen_plus_grid(board: chess.Board) -> str:
    """Combination: both the FEN and the ASCII grid, shown neutrally with no
    guidance about which to use for what. Tests whether complementary encodings
    let the model self-select the right view (relational from FEN, counting from
    the grid) — a PURE perception question, not instruction. Costs ~2x tokens."""
    return f"{render_fen(board)}\n\n{render_ascii_grid(board)}"


# Registry. Keys are stable format ids used throughout results/logging.
RENDERERS = {
    "fen": render_fen,
    "ascii_grid": render_ascii_grid,
    "unicode_grid": render_unicode_grid,
    "piece_list": render_piece_list,
    "fen_plus_grid": render_fen_plus_grid,
}

CONTROLS = ("fen", "ascii_grid")  # always in Stage 2 regardless of Stage 1


if __name__ == "__main__":
    b = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 4")
    for name, fn in RENDERERS.items():
        print(f"===== {name} =====")
        print(fn(b))
        print()
