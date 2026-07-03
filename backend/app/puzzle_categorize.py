"""Structural categorization of a puzzle, computed up-front from its first
correct move. Surfaces the features that make agent weaknesses easy to spot in
analysis — e.g. "fails BISHOP forks but not KNIGHT forks", "fails high-branching
positions", "fails quiet (non-check, non-capture) defensive moves".

Pure python-chess mechanics; no engine, no model. Computed once at puzzle-set
build time (baked into puzzles.json) and echoed into each run result so a run
can be sliced by any of these axes.
"""
from __future__ import annotations

import chess

_PN = {chess.PAWN: "pawn", chess.KNIGHT: "knight", chess.BISHOP: "bishop",
       chess.ROOK: "rook", chess.QUEEN: "queen", chess.KING: "king"}
_VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
        chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}


def _material(board: chess.Board, color: bool) -> int:
    return sum(_VAL[pt] * len(board.pieces(pt, color))
               for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN))


def categorize(fen: str, moves: list[str]) -> dict:
    """Return a dict of structural features for the puzzle.

    `fen` is the position BEFORE the opponent's setup move; `moves[0]` is that
    setup, `moves[1]` is the solver's first correct move (the one we categorize).
    """
    out: dict = {}
    try:
        board = chess.Board(fen)
        board.push(chess.Move.from_uci(moves[0]))      # position the solver faces
    except Exception:
        return {"categorize_error": "bad fen/setup"}

    # branching factor the solver faces (how many candidate moves to sift)
    legal = list(board.legal_moves)
    out["legal_moves_count"] = len(legal)
    out["in_check"] = board.is_check()                 # solver starts in check?
    out["solver_color"] = "white" if board.turn == chess.WHITE else "black"
    out["solution_plies"] = len(moves) - 1             # solver+opponent plies after setup
    out["solver_moves"] = (len(moves) - 1 + 1) // 2    # how many moves the agent must find
    out["material_before"] = _material(board, board.turn) - _material(board, not board.turn)

    try:
        first = chess.Move.from_uci(moves[1])
    except Exception:
        return out

    mover = board.piece_at(first.from_square)
    if mover is None:
        return out
    out["mover_piece"] = _PN[mover.piece_type]
    out["first_move_is_capture"] = board.is_capture(first)
    out["first_move_is_check"] = board.gives_check(first)
    out["first_move_is_promotion"] = first.promotion is not None
    out["first_move_is_quiet"] = not board.is_capture(first) and not board.gives_check(first)
    out["first_move_san"] = board.san(first)

    # what the moving piece TARGETS after the move (the tactic's victims): the
    # enemy non-pawn pieces it attacks from its new square, with their types.
    after = board.copy(stack=False)
    after.push(first)
    targets = []
    for tsq in after.attacks(first.to_square):
        ep = after.piece_at(tsq)
        if ep and ep.color != mover.color and ep.piece_type != chess.PAWN:
            targets.append(_PN[ep.piece_type])
    out["targets"] = sorted(set(targets))
    out["n_targets"] = len(targets)
    out["targets_king"] = "king" in targets

    # captured value (if a capture) and the net material swing of the FULL
    # solution line (a quick "how decisive" proxy).
    if board.is_capture(first):
        if board.is_en_passant(first):
            out["captured_value"] = 1
        else:
            v = board.piece_at(first.to_square)
            out["captured_value"] = _VAL[v.piece_type] if v else 0
    else:
        out["captured_value"] = 0
    try:
        line = chess.Board(fen)
        for u in moves:
            line.push(chess.Move.from_uci(u))
        pov = board.turn
        out["material_after_line"] = _material(line, pov) - _material(line, not pov)
        out["ends_in_mate"] = line.is_checkmate()
    except Exception:
        pass

    # a compact human-readable signature, e.g. "knight fork → king,rook" or
    # "quiet rook move", for quick eyeballing.
    if out.get("n_targets", 0) >= 2:
        shape = f"{out['mover_piece']} double-attack → {','.join(out['targets'])}"
    elif out["first_move_is_quiet"]:
        shape = f"quiet {out['mover_piece']} move"
    elif out["first_move_is_capture"]:
        shape = f"{out['mover_piece']} captures"
    else:
        shape = f"{out['mover_piece']} {'check' if out['first_move_is_check'] else 'move'}"
    out["signature"] = shape
    return out
