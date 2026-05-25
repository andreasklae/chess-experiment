#!/usr/bin/env python3
"""Show the current position: ASCII board, FEN, and per-piece attack/defense map.

Reads CHESS_API_BASE and CHESS_GAME_ID from environment (injected by AgentPlayer).
No arguments needed — fetches the live position from the backend.

Output is plain text, meant to be read by the model. Sections:

  1. ASCII board (uppercase = white, lowercase = black; a-h, 8-1).
  2. FEN and side to move.
  3. Your pieces under attack — for each of your pieces with at least one
     opponent attacker, lists the attackers and your defenders.
  4. Opponent pieces you're attacking — for each opponent piece with at
     least one of your attackers, lists your attackers and their defenders.

Attackers and defenders include x-ray batteries: if a sliding piece sits
behind an immediate attacker on the same line to the target, it is listed
as `(then ... via x-ray)` and activates when the piece in front captures.
Chains of x-rays are listed in activation order.

Pinned pieces are annotated `(pinned)`. A pinned attacker may still be
unable to capture if doing so would expose its king; the agent should
account for this when reasoning about exchanges.

This script does not run a static exchange evaluation — it surfaces the
geometry; the agent decides whether the sequence of captures is favourable.
"""

import json
import os
import sys
import urllib.request

import chess


PIECE_NAMES = {
    chess.PAWN: "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK: "rook",
    chess.QUEEN: "queen",
    chess.KING: "king",
}


def render_ascii(board: chess.Board) -> str:
    rows = str(board).split("\n")
    labelled = [f"{8 - i}  {row}" for i, row in enumerate(rows)]
    labelled.append("   a b c d e f g h")
    return "\n".join(labelled)


def piece_label(board: chess.Board, square: int, *, pinned: bool) -> str:
    piece = board.piece_at(square)
    base = f"{PIECE_NAMES[piece.piece_type]} on {chess.square_name(square)}"
    return f"{base} (pinned)" if pinned else base


def compute_attack_chain(board: chess.Board, by_color: bool, target: int) -> list[tuple[int, bool]]:
    """Return attackers of `target` by `by_color` in activation order,
    expanding x-ray batteries. Each entry is (square, is_xray).

    Algorithm: get immediate attackers from the live board. For each
    immediate attacker, walk *outward* along the line from target through
    the attacker (only meaningful for sliders or for any piece behind which
    a slider can attack along the same ray). If the next occupied square
    on that ray is a sliding piece of `by_color` that could attack along
    that ray's direction (rook on rank/file, bishop on diagonal, queen on
    either), add it as an x-ray attacker and continue past it for further
    chained sliders of the same color and ray-compatibility.

    We do NOT remove pieces and re-query, because that would also reveal
    attackers on *other* lines (e.g. a sliding piece that wasn't blocked
    by the captured piece at all). X-ray means: "would attack this square
    if the piece directly in front of it on the same line moved away" —
    which is a per-line property.
    """
    immediate = list(board.attackers(by_color, target))
    # Sort by piece value (cheapest first) to give a natural reading order
    # when there are multiple immediate attackers. Not required for
    # correctness; just makes the output predictable.
    immediate.sort(key=lambda s: _piece_value(board.piece_at(s).piece_type))

    chain: list[tuple[int, bool]] = []
    for attacker_sq in immediate:
        chain.append((attacker_sq, False))
        chain.extend((s, True) for s in _xray_chain(board, by_color, target, attacker_sq))
    return chain


_RAY_PIECE_TYPES = {
    "rank": (chess.ROOK, chess.QUEEN),
    "file": (chess.ROOK, chess.QUEEN),
    "diag": (chess.BISHOP, chess.QUEEN),
}


def _ray_kind(a: int, b: int) -> str | None:
    """Return 'rank', 'file', 'diag', or None for the line from a to b."""
    if a == b:
        return None
    fa, ra = chess.square_file(a), chess.square_rank(a)
    fb, rb = chess.square_file(b), chess.square_rank(b)
    df, dr = fb - fa, rb - ra
    if dr == 0:
        return "rank"
    if df == 0:
        return "file"
    if abs(df) == abs(dr):
        return "diag"
    return None


def _step(a: int, b: int) -> int:
    """Unit step from a toward b along their shared ray (caller ensures one exists)."""
    fa, ra = chess.square_file(a), chess.square_rank(a)
    fb, rb = chess.square_file(b), chess.square_rank(b)
    df = (fb > fa) - (fb < fa)
    dr = (rb > ra) - (rb < ra)
    return chess.square(fa + df, ra + dr) - a  # signed delta in square indices


def _xray_chain(board: chess.Board, by_color: bool, target: int, front_attacker: int) -> list[int]:
    """Walk from `target` outward past `front_attacker` looking for sliders of `by_color`
    that would attack `target` along the same ray if the pieces in front moved away."""
    kind = _ray_kind(target, front_attacker)
    if kind is None:
        return []  # knights, pawns whose attack isn't along an extendable line
    allowed_types = _RAY_PIECE_TYPES[kind]

    # Walk file/rank/diagonal step-by-step from front_attacker away from target.
    fa, ra = chess.square_file(target), chess.square_rank(target)
    fb, rb = chess.square_file(front_attacker), chess.square_rank(front_attacker)
    df = (fb > fa) - (fb < fa)
    dr = (rb > ra) - (rb < ra)

    revealed: list[int] = []
    file, rank = fb + df, rb + dr
    while 0 <= file <= 7 and 0 <= rank <= 7:
        sq = chess.square(file, rank)
        piece = board.piece_at(sq)
        if piece is not None:
            if piece.color == by_color and piece.piece_type in allowed_types:
                revealed.append(sq)
                # keep walking; another slider could be chained behind this one
            else:
                # blocked by a non-matching piece — chain ends
                break
        file += df
        rank += dr
    return revealed


def _piece_value(piece_type: int) -> int:
    return {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
            chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}[piece_type]


def format_chain(board: chess.Board, by_color: bool, chain: list[tuple[int, bool]]) -> str:
    """Render an ordered attacker/defender chain as human-readable text."""
    parts: list[str] = []
    for sq, is_xray in chain:
        pinned = board.is_pinned(by_color, sq)
        label = piece_label(board, sq, pinned=pinned)
        if is_xray:
            parts.append(f"then {label} via x-ray")
        else:
            parts.append(label)
    return ", ".join(parts)


def attack_defense_section(
    board: chess.Board,
    own_color: bool,
    opp_color: bool,
    header: str,
    action: str,
) -> str:
    lines = [header]
    found_any = False
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is None or piece.color != own_color:
            continue
        attacker_chain = compute_attack_chain(board, opp_color, sq)
        if not attacker_chain:
            continue
        found_any = True
        # Defenders: same machinery, but exclude the piece itself.
        defender_chain = [
            (s, is_xray) for (s, is_xray) in compute_attack_chain(board, own_color, sq)
            if s != sq
        ]
        desc = piece_label(board, sq, pinned=board.is_pinned(own_color, sq))
        atk_str = format_chain(board, opp_color, attacker_chain)
        def_str = format_chain(board, own_color, defender_chain) if defender_chain else "nothing"
        lines.append(f"  - {desc}: {action} {atk_str}; defended by {def_str}")
    if not found_any:
        lines.append("  (none)")
    return "\n".join(lines)


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

    # Queen rule wins outright.
    if not queens_present:
        return ("early endgame" if score >= 8 else "late endgame", score, move)

    # Score-driven classification (overrides move-count when they disagree).
    if score <= 13:
        return ("early endgame" if score >= 8 else "late endgame", score, move)
    if score <= 19:
        return ("late middlegame", score, move)
    # score in 20-24.
    if move <= 15 and score >= 22:
        return ("early opening" if move <= 6 else "late opening", score, move)
    return ("early middlegame", score, move)


def render_position(board: chess.Board) -> str:
    own_color = board.turn
    opp_color = not own_color
    own_name = "white" if own_color == chess.WHITE else "black"
    phase, score, move = detect_phase(board)

    out = [
        f"Phase: {phase} (move {move}, phase score {score}/24)",
        "",
        render_ascii(board),
        "",
        f"FEN: {board.fen()}",
        f"Side to move: {own_name}",
        "",
        attack_defense_section(
            board, own_color, opp_color,
            header="Your pieces under attack:",
            action="attacked by",
        ),
        "",
        attack_defense_section(
            board, opp_color, own_color,
            header="Opponent pieces you are attacking:",
            action="attacked by your",
        ),
    ]
    return "\n".join(out)


def main() -> None:
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

    print(render_position(chess.Board(fen)))


if __name__ == "__main__":
    main()
