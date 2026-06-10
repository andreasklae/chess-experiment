"""Mate & draw radar: mechanical board facts that point the agent at the
right knowledge, without making chess judgements for it.

Everything here is material counting, geometry, and the rules of chess —
mechanics-tool territory under the tool-fairness rulebook
(knowledge-base/decisions/2026-06-02-tool-fairness-rulebook.md):

  * material classes ("you have K+Q vs bare K") and which *wiki page* covers
    the standard technique — retrieval pointers into the agent's own corpus;
  * enemy king geometry (edge/corner, legal-move count);
  * back-rank geometry (king trapped behind own pawns; who defends the rank);
  * passed pawns and their distance from promotion;
  * draw-rule status (repetition, 50-move clock, the experiment's move cap).

None of it evaluates moves or searches; the agent still has to find the
mate. The radar only tells it that one is worth looking for, which a human
player reads off the board at a glance.

Not exposed as a tool (underscore prefix): show_position embeds the output.
"""

from __future__ import annotations

import chess

# Wiki pages the radar may point to. Paths relative to references/.
_PAGE_LADDER = "patterns/mating-patterns/ladder-mate.md"
_PAGE_KQ = "patterns/mating-patterns/king-queen-mate.md"
_PAGE_KR = "patterns/mating-patterns/king-rook-mate.md"
_PAGE_BACK_RANK = "patterns/mating-patterns/back-rank-mate.md"
_PAGE_CONVERT = "strategic-thinking/convert-advantage.md"
_PAGE_KP = "endgames/king-pawn-endings.md"


def _material(board: chess.Board, color: bool) -> dict[int, int]:
    return {
        pt: len(board.pieces(pt, color))
        for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
    }


def _mating_material_lines(board: chess.Board, own: bool) -> list[str]:
    """When the opponent is down to king (+ pawns), name the basic mate the
    agent's material supports and the wiki page that teaches it."""
    opp = not own
    opp_mat = _material(board, opp)
    own_mat = _material(board, own)
    opp_pieces = sum(v for pt, v in opp_mat.items() if pt != chess.PAWN)
    if opp_pieces > 0:
        return []

    opp_desc = "a bare king" if opp_mat[chess.PAWN] == 0 else (
        f"only king and {opp_mat[chess.PAWN]} pawn(s)"
    )
    majors = own_mat[chess.QUEEN] + own_mat[chess.ROOK]
    lines = [f"- Opponent has {opp_desc}."]

    if majors >= 2:
        lines.append(
            f"- You have two or more major pieces: the **ladder mate** is fully "
            f"forced — read `{_PAGE_LADDER}`."
        )
    elif own_mat[chess.QUEEN] == 1:
        lines.append(
            f"- King + queen vs king is a forced mate (under ~10 moves) — "
            f"read `{_PAGE_KQ}`."
        )
    elif own_mat[chess.ROOK] == 1:
        lines.append(
            f"- King + rook vs king is a forced mate — read `{_PAGE_KR}`."
        )
    elif own_mat[chess.BISHOP] >= 2:
        lines.append(
            "- Two bishops + king can force mate, but it is slow technique. "
            f"If you still have a pawn, promoting it first is simpler — "
            f"read `{_PAGE_CONVERT}`."
        )
    elif own_mat[chess.BISHOP] + own_mat[chess.KNIGHT] >= 2:
        lines.append(
            "- Bishop+knight mate is very hard, and two knights cannot force "
            f"mate. If you have a pawn, promote it and mate with the queen — "
            f"read `{_PAGE_KP}`."
        )
    if own_mat[chess.PAWN] > 0 and majors == 0:
        lines.append(
            f"- You have pawn(s): promotion is the most reliable winning plan — "
            f"read `{_PAGE_KP}`."
        )
    if board.has_insufficient_material(own):
        lines = [
            "- **You cannot checkmate with your remaining material** — "
            "the best available result is a draw."
        ]
    return lines


def _king_geometry_lines(board: chess.Board, own: bool) -> list[str]:
    """Edge/corner status and legal-move count of the enemy king. Shown only
    when the king is already restricted or the game is thinning out."""
    opp = not own
    ksq = board.king(opp)
    if ksq is None:
        return []
    f, r = chess.square_file(ksq), chess.square_rank(ksq)
    on_edge = f in (0, 7) or r in (0, 7)
    in_corner = f in (0, 7) and r in (0, 7)

    # Only meaningful once the opponent is thinned out — a fully-defended
    # opening king is "restricted" by its own army, which is noise. Gate on
    # the opponent having at most two non-pawn pieces besides the king.
    opp_mat = _material(board, opp)
    if sum(v for pt, v in opp_mat.items() if pt != chess.PAWN) > 2:
        return []

    # Count the enemy king's legal moves (from a null-moved copy when it is
    # not the opponent's turn).
    b = board.copy(stack=False)
    if b.turn != opp:
        b.push(chess.Move.null())
    king_moves = sum(1 for m in b.legal_moves if m.from_square == ksq)

    if not on_edge and king_moves > 3:
        return []

    where = "in a corner" if in_corner else ("on the edge" if on_edge else "in the open")
    return [
        f"- Enemy king on {chess.square_name(ksq)} is {where} and has "
        f"{king_moves} legal king move(s). Forcing moves that shrink this "
        f"number are how mating nets close."
    ]


def _back_rank_lines(board: chess.Board, own: bool) -> list[str]:
    """Purely geometric back-rank check: enemy king on its back rank, every
    forward escape square blocked by its own pawns; report rank defenders."""
    opp = not own
    ksq = board.king(opp)
    if ksq is None:
        return []
    back = 7 if opp == chess.BLACK else 0
    if chess.square_rank(ksq) != back:
        return []
    forward = -8 if opp == chess.BLACK else 8
    f = chess.square_file(ksq)
    front_files = [x for x in (f - 1, f, f + 1) if 0 <= x <= 7]
    front_squares = [chess.square(x, back) + forward for x in front_files]
    blocked = all(
        (p := board.piece_at(sq)) is not None and p.color == opp and p.piece_type == chess.PAWN
        for sq in front_squares
    )
    if not blocked:
        return []

    # Geometry alone is noise in a closed position (it is "true" at move
    # one). Require a path: at least one fully open file (no pawns of either
    # colour) AND a major piece of ours to use it.
    if not (board.pieces(chess.ROOK, own) | board.pieces(chess.QUEEN, own)):
        return []
    pawns = board.pieces(chess.PAWN, chess.WHITE) | board.pieces(chess.PAWN, chess.BLACK)
    open_file = any(
        all(chess.square(x, r) not in pawns for r in range(8)) for x in range(8)
    )
    if not open_file:
        return []
    defenders = [
        chess.square_name(sq)
        for sq in board.pieces(chess.ROOK, opp) | board.pieces(chess.QUEEN, opp)
        if chess.square_rank(sq) == back
    ]
    guard = (
        f"its back rank is guarded by major piece(s) on {', '.join(defenders)} — "
        f"they must be deflected or outnumbered first"
        if defenders else "no enemy major piece guards that rank"
    )
    return [
        f"- Enemy king is trapped on its back rank behind its own pawns; "
        f"{guard}. Back-rank mate geometry — read `{_PAGE_BACK_RANK}`."
    ]


def _passed_pawn_lines(board: chess.Board, own: bool) -> list[str]:
    """List passed pawns for both sides with distance to promotion."""
    def passed(sq: int, color: bool) -> bool:
        f, r = chess.square_file(sq), chess.square_rank(sq)
        ahead = range(r + 1, 8) if color == chess.WHITE else range(0, r)
        for x in (f - 1, f, f + 1):
            if not 0 <= x <= 7:
                continue
            for rr in ahead:
                p = board.piece_at(chess.square(x, rr))
                if p is not None and p.piece_type == chess.PAWN and p.color != color:
                    return False
        return True

    def describe(color: bool) -> list[str]:
        out = []
        for sq in board.pieces(chess.PAWN, color):
            if passed(sq, color):
                r = chess.square_rank(sq)
                dist = (7 - r) if color == chess.WHITE else r
                out.append(f"{chess.square_name(sq)} ({dist} move(s) from promotion)")
        return out

    mine, theirs = describe(own), describe(not own)
    lines = []
    if mine:
        lines.append(
            f"- Your passed pawn(s): {', '.join(mine)}. A passed pawn escorted "
            f"by its king promotes — read `{_PAGE_KP}`."
        )
    if theirs:
        lines.append(f"- Opponent passed pawn(s): {', '.join(theirs)} — do not let them run.")
    return lines


def _draw_rule_lines(board: chess.Board, move_cap: int | None) -> list[str]:
    """Repetition count, 50-move clock, and the experiment's ply cap."""
    lines = []
    if board.move_stack and board.is_repetition(2):
        lines.append(
            "- **Repetition warning:** this position has already occurred "
            "before — repeating it once more is an automatic draw. Choose a "
            "move that makes progress instead."
        )
    if board.halfmove_clock >= 60:
        lines.append(
            f"- 50-move rule: {board.halfmove_clock}/100 half-moves without a "
            f"capture or pawn move. A capture or pawn advance resets the count."
        )
    if move_cap is not None:
        ply = len(board.move_stack) if board.move_stack else None
        if ply is not None and move_cap - ply <= 30:
            remaining = (move_cap - ply) // 2
            lines.append(
                f"- **Move cap:** the game is declared drawn at ply {move_cap}; "
                f"about {remaining} of your moves remain. If you are winning, "
                f"force matters NOW — read `{_PAGE_CONVERT}`."
            )
    return lines


def render_radar(board: chess.Board, move_cap: int | None = None) -> str | None:
    """Markdown radar section, or None when nothing is worth saying.

    `board` should carry the real move stack when available (repetition and
    cap checks need it); a bare-FEN board degrades gracefully.
    """
    own = board.turn
    lines: list[str] = []
    lines += _mating_material_lines(board, own)
    lines += _king_geometry_lines(board, own)
    lines += _back_rank_lines(board, own)
    lines += _passed_pawn_lines(board, own)
    lines += _draw_rule_lines(board, move_cap)
    if not lines:
        return None
    return "## Mate & draw radar\n\n" + "\n".join(lines)
