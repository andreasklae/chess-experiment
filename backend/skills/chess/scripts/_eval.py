"""Shared helpers for the chess skill's perception scripts.

This module is underscore-prefixed so the SDK does not expose it as a
typed tool (it skips underscore-prefixed files when listing a skill's
scripts). It is intended for `from _eval import ...` use by sibling
scripts only.

Contents:

- Piece-name + colour-name helpers (PIECE_NAMES, color_name).
- Material values (MATERIAL) — centipawn weights for each piece type.
- Piece-square tables (Michniewski's Simplified Evaluation Function)
  plus the per-side king-table selection rule (use_endgame_king_table).
- `evaluate(board)` — net material+PST score in centipawns, white-positive.
- `verdict(score)` — plain-language band for an eval score. Phrasing
  is deliberately material-focused ("material lead" not "winning"),
  because this eval is tactically blind.
- Phase detection (phase_score, detect_phase) using a weighted non-pawn
  material count.
- Illegal-move classifier (classify_illegal_move) used by imagine_move
  and apply_line — produces a categorised reason why a UCI move is
  illegal in a given position.
- Line-application machinery (parse_moves_arg, apply_line, MoveListError,
  format_san_line) — plays a comma-separated UCI list out on a copy of
  the board, with categorised errors when any move is illegal.
- `eval_lines_for_position` and `eval_lines_for_move` — the small set of
  lines that show_position and imagine_move embed in their output so the
  agent gets the static eval directly in the relevant tool's report
  rather than having to call a separate script.
"""

from __future__ import annotations

import chess


# ── Piece + colour name helpers ────────────────────────────────────────────

PIECE_NAMES: dict[int, str] = {
    chess.PAWN: "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK: "rook",
    chess.QUEEN: "queen",
    chess.KING: "king",
}


def color_name(color: bool) -> str:
    """'white' for chess.WHITE (True), 'black' for chess.BLACK (False)."""
    return "white" if color == chess.WHITE else "black"


def describe_piece(board: chess.Board, square: int) -> str:
    """e.g. 'knight on f3'. Assumes there is a piece on `square`."""
    piece = board.piece_at(square)
    return f"{PIECE_NAMES[piece.piece_type]} on {chess.square_name(square)}"


# ── Material values (centipawns) ───────────────────────────────────────────

MATERIAL: dict[int, int] = {
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


_PST_WHITE: dict[int, list[int]] = {
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
    (in centipawns, white-positive). King material is excluded from totals."""
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


# ── Verdict bands (deliberately material-focused) ──────────────────────────
#
# The eval is material + PST only, so it cannot see that a piece you just
# captured is about to be lost to a fork or that your king is one move from
# mate. Saying "winning" would invite the agent to treat a coarse number as
# a verdict. The bands below all say "lead" instead, and the SKILL.md
# guidance pairs this with a one-line warning under every eval line so the
# agent treats the number as a coarse material check, not a position
# assessment.


def verdict(score: int) -> str:
    """Plain-language band for the score (centipawns, white-positive)."""
    if score == 0:
        return "material balanced"
    abs_score = abs(score)
    side = "white" if score > 0 else "black"
    if abs_score >= 300:
        return f"decisive material lead for {side}"
    if abs_score >= 100:
        return f"clear material lead for {side}"
    if abs_score >= 30:
        return f"slight material lead for {side}"
    return "roughly balanced"


# Backwards-compat alias for code that previously imported the private name.
_verdict = verdict


# One-line warning attached to every eval line shown to the agent.
EVAL_WARNING = (
    "(material + piece-square tables only; does not see tactics — a "
    "material lead can be lost in one move if the position has unresolved threats.)"
)


def render_eval_line(board: chess.Board) -> str:
    """Format the eval as a single line for embedding in show_position output:
    `Material balance: +0.30 (slight material lead for white)`."""
    ev = evaluate(board)
    score = ev["score"]
    pawns = score / 100.0
    sign = "+" if score >= 0 else "-"
    return f"Material balance: {sign}{abs(pawns):.2f} ({verdict(score)})"


def render_eval_delta_line(before: chess.Board, after: chess.Board) -> str:
    """Format the before/after eval with delta for imagine_move output:
    `Material balance: +0.30 → +0.20 (Δ -0.10, slight material lead for white)`.

    The delta is from the mover's perspective only in the sense of which
    side gained or lost material — the signed value is always white-positive,
    same as the eval itself."""
    ev_before = evaluate(before)
    ev_after = evaluate(after)
    s_before = ev_before["score"]
    s_after = ev_after["score"]
    delta = s_after - s_before

    def _fmt(score: int) -> str:
        sign = "+" if score >= 0 else "-"
        return f"{sign}{abs(score) / 100.0:.2f}"

    delta_sign = "+" if delta >= 0 else "-"
    return (
        f"Material balance: {_fmt(s_before)} → {_fmt(s_after)} "
        f"(Δ {delta_sign}{abs(delta) / 100.0:.2f}, {verdict(s_after)})"
    )


# ── Phase detection ────────────────────────────────────────────────────────

_PHASE_PIECE_WEIGHTS = {
    chess.QUEEN: 4,
    chess.ROOK: 2,
    chess.BISHOP: 1,
    chess.KNIGHT: 1,
}


def phase_score(board: chess.Board) -> int:
    """Sum of weighted non-pawn, non-king pieces across both sides.
    Starting position = 24; max possible is also 24."""
    total = 0
    for piece_type, weight in _PHASE_PIECE_WEIGHTS.items():
        total += weight * (
            len(board.pieces(piece_type, chess.WHITE))
            + len(board.pieces(piece_type, chess.BLACK))
        )
    return total


def detect_phase(board: chess.Board) -> tuple[str, int, int]:
    """Return (phase_label, score, fullmove_number).

    Rules:
    - Queen presence takes priority: no queens on either side -> endgame.
    - Otherwise: score >= 14 with move > 6 -> middlegame (early 20-23, late 14-19).
    - score <= 13 -> endgame (early 8-13, late <8).
    - Move <= 15 and score >= 22 -> opening (early move <= 6, late 7-15).
    - If opening-by-move conflicts with score-by-middle/endgame, trust the score.
    """
    score = phase_score(board)
    move = board.fullmove_number
    queens_present = bool(board.pieces(chess.QUEEN, chess.WHITE)) or bool(
        board.pieces(chess.QUEEN, chess.BLACK)
    )

    if not queens_present:
        return ("early endgame" if score >= 8 else "late endgame", score, move)

    if score <= 13:
        return ("early endgame" if score >= 8 else "late endgame", score, move)
    if score <= 19:
        return ("late middlegame", score, move)
    # score in 20-24.
    if move <= 15 and score >= 22:
        return ("early opening" if move <= 6 else "late opening", score, move)
    return ("early middlegame", score, move)


# ── Static exchange evaluation ─────────────────────────────────────────────


def static_exchange_eval(board: chess.Board, square: int, side_to_capture: bool) -> int:
    """Material the side initiating captures on ``square`` nets, in
    centipawns, assuming both sides recapture with their least valuable piece
    each time (standard static-exchange evaluation, SEE).

    ``side_to_capture`` is the colour that moves first (the opponent of the
    piece sitting on ``square``). Returns the net gain for that side: positive
    means the capturing side wins material. Pure rules arithmetic — it plays
    out the legal recapture sequence on one square; no move-tree search, no
    positional judgement. Shared by imagine_move (reporting) and make_move's
    commit gate (enforcement).
    """
    target = board.piece_at(square)
    if target is None:
        return 0

    def least_valuable_attacker(bd: chess.Board, color: bool, sq: int) -> int | None:
        attackers = bd.attackers(color, sq)
        if not attackers:
            return None
        return min(attackers, key=lambda a: MATERIAL.get(bd.piece_at(a).piece_type, 0))

    gains: list[int] = []
    work = board.copy(stack=False)
    on_square_value = MATERIAL.get(target.piece_type, 0)
    color = side_to_capture
    while True:
        frm = least_valuable_attacker(work, color, square)
        if frm is None:
            break
        gains.append(on_square_value)
        on_square_value = MATERIAL.get(work.piece_at(frm).piece_type, 0)
        work.remove_piece_at(square)
        work.set_piece_at(square, work.piece_at(frm))
        work.remove_piece_at(frm)
        color = not color
    net = 0
    for g in reversed(gains):
        net = max(0, g - net)
    return net


def is_losing_on_square(board: chess.Board, square: int, own_color: bool) -> bool:
    """True when the opponent wins material (>= a pawn) by capturing the piece
    on ``square`` — single-square SEE from the opponent's side. Considers ALL
    enemy attackers (king and pieces), not just the king. Pure mechanics."""
    return static_exchange_eval(board, square, not own_color) >= 100


def safe_destination_squares(board: chess.Board, square: int, own_color: bool) -> list[int]:
    """Squares the piece on ``square`` can legally move to where it would NOT
    be losing material on arrival — SEE-safe against EVERY enemy piece, not
    just the enemy king. Mechanics only: enumerate legal moves, filter by the
    single-square SEE on the landing square. It does NOT account for material
    lost by DISCOVERY (a line opened behind the moved piece) — verify the whole
    move with imagine_move. Shared by show_position (hanging-piece hint) and
    the ladder advisor (safe wall/check squares when enemy pieces are around)."""
    out: list[int] = []
    for mv in board.legal_moves:
        if mv.from_square != square:
            continue
        after = board.copy(stack=False)
        after.push(mv)
        if static_exchange_eval(after, mv.to_square, not own_color) < 100:
            out.append(mv.to_square)
    return out


# ── Move parsing ─────────────────────────────────────────────────────────


def _major_attacked_squares(board: chess.Board, color: bool) -> set[int]:
    """Squares attacked by ``color``'s queens and rooks — the cage walls in a
    basic mate. King and minor pieces are excluded: only majors cut a full
    rank/file."""
    walls: set[int] = set()
    for pt in (chess.QUEEN, chess.ROOK):
        for sq in board.pieces(pt, color):
            walls |= set(board.attacks(sq))
    return walls


def confinement_box(board: chess.Board, defender: bool) -> tuple[int, int, int]:
    """Return (width, height, area) of the rectangle the ``defender`` king is
    confined to by the OTHER side's major pieces and the board edges.

    Mechanics only: walk outward from the king along each of the four
    orthogonal directions until hitting a square the attacking side's
    queen/rook controls (a wall) or the board edge. The box is the rectangle
    those four walls (or edges) bound. A smaller area = a tighter cage; the
    basic-mate method is to drive this toward the few squares around the edge
    where mate is delivered. Geometry, not evaluation: it does not consider
    whose move it is or whether a wall is defended."""
    ek = board.king(defender)
    if ek is None:
        return (8, 8, 64)
    ekf, ekr = chess.square_file(ek), chess.square_rank(ek)
    walls = _major_attacked_squares(board, not defender)

    def reach(df: int, dr: int) -> int:
        f, r, steps = ekf + df, ekr + dr, 0
        while 0 <= f <= 7 and 0 <= r <= 7:
            if chess.square(f, r) in walls:
                return steps
            f += df
            r += dr
            steps += 1
        return steps  # ran into the board edge

    left, right = reach(-1, 0), reach(1, 0)
    down, up = reach(0, -1), reach(0, 1)
    width = left + right + 1
    height = down + up + 1
    return (width, height, width * height)


def confinement_box_bounds(board: chess.Board, defender: bool) -> tuple[int, int, int, int] | None:
    """File/rank bounds (min_file, max_file, min_rank, max_rank) of the
    rectangle the ``defender`` king is confined to — the same box
    ``confinement_box`` measures, returned as coordinates so a renderer can
    draw it. None if the defender king is missing. Pure geometry."""
    ek = board.king(defender)
    if ek is None:
        return None
    ekf, ekr = chess.square_file(ek), chess.square_rank(ek)
    walls = _major_attacked_squares(board, not defender)

    def reach(df: int, dr: int) -> int:
        f, r, steps = ekf + df, ekr + dr, 0
        while 0 <= f <= 7 and 0 <= r <= 7:
            if chess.square(f, r) in walls:
                return steps
            f += df
            r += dr
            steps += 1
        return steps

    return (
        ekf - reach(-1, 0), ekf + reach(1, 0),
        ekr - reach(0, -1), ekr + reach(0, 1),
    )


def kings_distance(board: chess.Board) -> int:
    """Chebyshev (king-move) distance between the two kings, or 8 if either is
    missing. The basic-mate 'march your king in' progress signal: pure
    geometry."""
    wk, bk = board.king(chess.WHITE), board.king(chess.BLACK)
    if wk is None or bk is None:
        return 8
    return chess.square_distance(wk, bk)


def lone_king_color(board: chess.Board) -> bool | None:
    """Colour of the side reduced to king (+ pawns), while the other side has a
    queen or rook — the basic-mate precondition. None if neither side qualifies.
    Pure material count."""
    for color in (chess.WHITE, chess.BLACK):
        own_pieces = sum(
            len(board.pieces(pt, color))
            for pt in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)
        )
        opp_majors = len(board.pieces(chess.QUEEN, not color)) + len(
            board.pieces(chess.ROOK, not color)
        )
        if own_pieces == 0 and opp_majors >= 1:
            return color
    return None


def piece_defensible_in_time(board: chess.Board, sq: int, own: bool) -> bool | None:
    """Geometry race: can ``own``'s king reach a square defending ``sq`` no
    later than the enemy king can reach a square attacking ``sq``? Compares the
    Chebyshev distance of each king to the nearest square adjacent to ``sq``.
    Used to judge whether a major parked on ``sq`` (to confine the lone king)
    will stay safe. Pure geometry — does not search. None if a king is missing.

    Note: this is a coarse race (it ignores whose move it is and blocking); it
    is a hint, not a guarantee — the agent still verifies with imagine_move."""
    mk, ek = board.king(own), board.king(not own)
    if mk is None or ek is None:
        return None
    adjacent = [s for s in chess.SQUARES if chess.square_distance(s, sq) == 1]
    if not adjacent:
        return None
    my_d = min(chess.square_distance(mk, s) for s in adjacent)
    opp_d = min(chess.square_distance(ek, s) for s in adjacent)
    return my_d <= opp_d


def confine_state(board: chess.Board, own: bool) -> dict | None:
    """Geometric state of the K+R / K+Q confine-and-defend method, as a
    structural fact about the CURRENT position — not a move recommendation.

    The method (Capablanca): the major confines the lone king into the
    smallest box it can while the king stays able to defend the major in time;
    when the major already sits on the tightest defensible confining line, the
    king steps closer instead. This reports which of those two situations holds
    — like 'is there a back-rank weakness' — leaving the agent to find and play
    the actual square with imagine_move.

    Returns a dict (or None if not a lone-king ending with a single major):
      current_area:    the box area the major confines the king to right now;
      best_area:       the smallest box area reachable by a single major move
                       to a square the king can still defend in time;
      can_tighten:     True  → MOVE THE MAJOR (a defensible major move improves
                       the position more than any king move on the combined
                       'box then kings-closer' measure);
                       False → STEP THE KING closer (no defensible major move
                       beats simply walking the king in — the coordination the
                       enemy king exploits when you squeeze too early).

    The combined measure (box area first, kings-distance second) is what makes
    this match real K+R technique rather than greedy box-shrinking: a rook move
    that shrinks the *measured* box but abandons the cut just lets the enemy
    king walk back (the repetition draw in game f36a4618). Pure geometry — box
    rectangles + the king-distance race; it does NOT search, score positions,
    or name a move; it classifies the current structure so the agent knows
    which branch of the method applies."""
    defender = not own
    majors = [sq for pt in (chess.QUEEN, chess.ROOK) for sq in board.pieces(pt, own)]
    if lone_king_color(board) != defender or len(majors) != 1:
        return None
    msq = majors[0]
    current_area = confinement_box(board, defender)[2]

    # Rank every legal non-stalemate move by the combined measure
    #   (box area, then kings closer, then prefer a KING move on ties)
    # and report whether the best move is the major or the king. This matches
    # real K+R technique: a rook move that shrinks the box but leaves the king
    # behind ties or loses to a king step (verified: this ordering mates a
    # running king in ~29 plies without repetition, whereas pure box-greedy
    # drew by repetition, game f36a4618).
    # Ranking metric is PIECE-SPECIFIC (each verified to mate; the wrong one
    # draws — K+R game f36a4618, K+Q game b2648178):
    #   K+R: (box area, then kings closer) — the rook confines, the king
    #        escorts. A rook move that shrinks the measured box but leaves the
    #        king behind ties/loses to a king step.
    #   K+Q: (kings closer, then enemy-king mobility) — the queen is strong
    #        enough that the KING march is primary; the queen just cuts the
    #        enemy king's legal moves. Box-greedy stalls the queen (it boxes
    #        the king instantly, then never finishes / stalemates).
    is_queen = board.piece_type_at(msq) == chess.QUEEN

    def _enemy_king_moves(bd: chess.Board) -> int:
        eksq = bd.king(defender)
        probe = bd
        if bd.turn != defender:
            probe = bd.copy(stack=False)
            try:
                probe.push(chess.Move.null())
            except (AssertionError, ValueError):
                return 0
        return sum(1 for m in probe.legal_moves if m.from_square == eksq)

    best_key = None
    best_is_major = False
    best_area = current_area
    for mv in board.legal_moves:
        after = board.copy(stack=False)
        after.push(mv)
        if after.is_checkmate():          # a mate is its own signal; ignore here
            continue
        if after.is_stalemate():
            continue
        ek = after.king(defender)
        is_major = mv.from_square == msq
        if is_major:
            if ek is not None and chess.square_distance(ek, mv.to_square) == 1 \
                    and not after.is_attacked_by(own, mv.to_square):
                continue
            if piece_defensible_in_time(after, mv.to_square, own) is False:
                continue
        area = confinement_box(after, defender)[2]
        mk = after.king(own)
        kd = chess.square_distance(mk, ek) if (mk is not None and ek is not None) else 8
        tie = 1 if is_major else 0       # prefer a king move on exact ties
        if is_queen:
            key = (kd, _enemy_king_moves(after), tie)
        else:
            key = (area, kd, tie)
        if best_key is None or key < best_key:
            best_key = key
            best_is_major = is_major
        if area < best_area:
            best_area = area
    return {
        "current_area": current_area,
        "best_area": best_area,
        "can_tighten": best_is_major,
    }


def parse_move(board: chess.Board, raw: str) -> chess.Move:
    """Parse a move string in UCI or SAN form on the given board.

    Accepts:
      - UCI: ``e2e4``, ``g1f3``, ``e1g1``, ``e7e8q``
      - SAN: ``e4``, ``Nf3``, ``O-O``, ``e8=Q``, ``Nxc6``, ``Nxc6+``
      - Either form with a trailing ``+`` (check) or ``#`` (mate) — stripped
        because the check/mate annotation is descriptive, not part of the
        move identity.
      - SAN-style square pairs from the model that look like UCI but with a
        trailing ``+`` (e.g. ``d5f6+``).

    Raises ``ValueError`` if the cleaned string is neither a legal UCI move
    nor parseable as SAN in the given position.
    """
    cleaned = raw.strip().rstrip("+#")
    if not cleaned:
        raise ValueError(f"empty move string (got {raw!r})")
    try:
        move = chess.Move.from_uci(cleaned)
        if move in board.legal_moves:
            return move
        # UCI parse succeeded but illegal — fall through to SAN attempt
        # (rare but possible, e.g. when the model fabricated a UCI that
        # happens to be syntactically valid but not legal here).
    except ValueError:
        pass
    try:
        return board.parse_san(cleaned)
    except (ValueError, chess.IllegalMoveError, chess.InvalidMoveError, chess.AmbiguousMoveError) as exc:
        raise ValueError(
            f"could not parse {raw!r} as UCI (e.g. e2e4) or SAN (e.g. Nf3) "
            f"in the current position: {exc}"
        ) from exc


# ── Illegal-move classification ────────────────────────────────────────────


def classify_illegal_move(board: chess.Board, uci: str) -> str:
    """Return a human-readable reason why `uci` is illegal in `board`.
    Assumes the move is known to be illegal (or malformed); inspects board
    state to categorise the failure. Goes through cases in priority order:
    malformed -> piece presence -> ownership -> destination-own -> castling
    -> promotion mismatch -> blocked path -> geometry -> in-check -> pin ->
    generic."""
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
            f"the piece on {from_name} is {color_name(piece.color)}, "
            f"but it's {color_name(board.turn)}'s turn"
        )

    piece_name = PIECE_NAMES[piece.piece_type]
    dest = board.piece_at(to_sq)

    # 4. Destination occupied by own piece (caught before geometry — a more
    # informative message than "can't move there").
    if dest is not None and dest.color == piece.color:
        return (
            f"destination {to_name} is occupied by your own "
            f"{PIECE_NAMES[dest.piece_type]}"
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
                f"{color_name(blocking_piece.color)} {PIECE_NAMES[blocking_piece.piece_type]} "
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
        direction = 1 if piece.color == chess.WHITE else -1
        ff, fr = chess.square_file(from_sq), chess.square_rank(from_sq)
        tf, tr = chess.square_file(to_sq), chess.square_rank(to_sq)
        if to_sq in board.attacks(from_sq):
            # Diagonal moves are only legal as captures or en passant.
            if board.piece_at(to_sq) is not None or to_sq == board.ep_square:
                return True
            return False
        if ff != tf:
            return False
        if tr - fr == direction:
            return board.piece_at(to_sq) is None
        if tr - fr == 2 * direction and fr == (1 if piece.color == chess.WHITE else 6):
            intermediate = chess.square(ff, fr + direction)
            return board.piece_at(intermediate) is None and board.piece_at(to_sq) is None
        return False
    return to_sq in board.attacks(from_sq)


def _first_blocker_for_piece(board: chess.Board, piece_type: int, from_sq: int, to_sq: int) -> int | None:
    """For a sliding piece, return the first occupied square strictly between
    from_sq and to_sq along a ray the piece can use. Returns None if the move
    is not on a usable ray for this piece type, or if the path is clear."""
    ff, fr = chess.square_file(from_sq), chess.square_rank(from_sq)
    tf, tr = chess.square_file(to_sq), chess.square_rank(to_sq)
    df, dr = tf - ff, tr - fr
    if max(abs(df), abs(dr)) < 2:
        return None
    is_orthogonal = (df == 0) ^ (dr == 0)
    is_diagonal = df != 0 and dr != 0 and abs(df) == abs(dr)
    if not (is_orthogonal or is_diagonal):
        return None
    if piece_type == chess.ROOK and not is_orthogonal:
        return None
    if piece_type == chess.BISHOP and not is_diagonal:
        return None
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
    rank = 0 if color == chess.WHITE else 7
    if kingside:
        between = [chess.square(f, rank) for f in (5, 6)]
    else:
        between = [chess.square(f, rank) for f in (1, 2, 3)]
    for sq in between:
        if board.piece_at(sq) is not None:
            blocker = board.piece_at(sq)
            return (
                f"cannot castle {side_name}: {chess.square_name(sq)} is occupied by "
                f"{color_name(blocker.color)} {PIECE_NAMES[blocker.piece_type]}"
            )
    pass_squares = [chess.square(f, rank) for f in (4, 5, 6)] if kingside else [chess.square(f, rank) for f in (2, 3, 4)]
    for sq in pass_squares:
        if board.is_attacked_by(not color, sq):
            return (
                f"cannot castle {side_name}: king would pass through or land on "
                f"{chess.square_name(sq)}, which is attacked"
            )
    return f"cannot castle {side_name}"


# ── Line application (play out a UCI sequence on a copy of the board) ──────


class MoveListError(Exception):
    """Raised when a move in a UCI list can't be applied. Carries the 1-indexed
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


def enemy_king_mobility(board: chess.Board) -> int:
    """Count how many squares the enemy king (opponent of board.turn) can legally
    move to. Generates moves from a copy with the turn flipped so we see the
    enemy's legal king moves from this position. Returns 0 if no king found."""
    enemy_color = not board.turn
    if not board.pieces(chess.KING, enemy_color):
        return 0
    flipped = board.copy()
    flipped.turn = enemy_color
    return sum(
        1 for m in flipped.legal_moves
        if flipped.piece_at(m.from_square) is not None
        and flipped.piece_at(m.from_square).piece_type == chess.KING
    )


def annotate_move(board: chess.Board, move: chess.Move) -> dict:
    """Return a small annotation dict for `move` on `board`:
      - 'uci': the UCI string.
      - 'san': SAN rendering (e.g. 'Nf3', 'Bxc4', 'O-O', 'e8=Q+').
      - 'description': short prose ('knight to f3', 'bishop takes pawn on c4',
        'kingside castle', 'pawn promotes to queen').
      - 'flag': 'check' / 'checkmate' / 'stalemate' / '' (empty when none).
      - 'king_before': enemy king legal squares before the move.
      - 'king_after': enemy king legal squares after the move.

    The move must be legal in `board`. Used by list_legal_moves and by
    imagine_move's opponent-replies block to give the agent a scannable
    human-readable view alongside the UCI strings.
    """
    san = board.san(move)
    piece = board.piece_at(move.from_square)
    piece_name = PIECE_NAMES[piece.piece_type]
    to_name = chess.square_name(move.to_square)

    # Description.
    if board.is_castling(move):
        side = "kingside" if chess.square_file(move.to_square) > chess.square_file(move.from_square) else "queenside"
        desc = f"{side} castle"
    elif board.is_en_passant(move):
        ep_sq = chess.square(chess.square_file(move.to_square), chess.square_rank(move.from_square))
        desc = f"pawn captures en passant on {to_name} (taking pawn on {chess.square_name(ep_sq)})"
    else:
        captured = board.piece_at(move.to_square)
        if captured is not None:
            captured_name = PIECE_NAMES[captured.piece_type]
            desc = f"{piece_name} takes {captured_name} on {to_name}"
        else:
            desc = f"{piece_name} to {to_name}"
        if move.promotion is not None:
            desc += f", promotes to {PIECE_NAMES[move.promotion]}"

    # Flag + king mobility — apply the move and inspect the resulting board.
    king_before = enemy_king_mobility(board)
    work = board.copy()
    work.push(move)
    if work.is_checkmate():
        flag = "checkmate"
    elif work.is_stalemate():
        flag = "stalemate"
    elif work.is_check():
        flag = "check"
    else:
        flag = ""
    # After the move it's the enemy's turn, so work.legal_moves is already
    # their move set. Count only king moves.
    king_after = sum(
        1 for m in work.legal_moves
        if work.piece_at(m.from_square) is not None
        and work.piece_at(m.from_square).piece_type == chess.KING
    )

    return {
        "uci": move.uci(),
        "san": san,
        "description": desc,
        "flag": flag,
        "king_before": king_before,
        "king_after": king_after,
    }


def render_moves_table(board: chess.Board, moves: list[chess.Move]) -> str:
    """Render a list of legal moves as a markdown table with columns
    `UCI | SAN | Description | Flag | King mvt`. Sorted by UCI for stable ordering.

    The 'King mvt' column shows enemy king legal squares before → after (Δ delta),
    e.g. '6→3 (−3)'. A negative delta means the move restricts the enemy king;
    moves that reduce king mobility to 0 typically give check or checkmate.

    When `board` carries its move stack, the Flag column also warns about
    draw-by-rule moves: 'draw:repetition' / 'draw:50-move' (the move ends the
    game as a draw on the spot) and 'repeats!' (recreates an earlier
    position; one more repeat draws). Pure rules-of-chess bookkeeping."""
    annotated = [annotate_move(board, m) for m in moves]
    if board.move_stack:
        from _live import draw_flag
        for a, m in zip(annotated, moves):
            df = draw_flag(board, m)
            if df and a["flag"] != "checkmate":
                a["flag"] = f"{a['flag']}, {df}" if a["flag"] else df
    annotated.sort(key=lambda a: a["uci"])
    if not annotated:
        return "_(no legal moves)_"
    rows = [
        "| UCI    | SAN    | Description                                | Flag       | King mvt   |",
        "|--------|--------|--------------------------------------------|------------|------------|",
    ]
    for a in annotated:
        kb, ka = a["king_before"], a["king_after"]
        delta = ka - kb
        sign = "−" if delta < 0 else ("+" if delta > 0 else "")
        king_str = f"{kb}→{ka} ({sign}{abs(delta)})"
        rows.append(
            f"| {a['uci']:<6} | {a['san']:<6} | {a['description']:<42} | {a['flag']:<10} | {king_str:<10} |"
        )
    return "\n".join(rows)


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
