#!/usr/bin/env python3
"""Show the current position: ASCII board, FEN, eval, and attack/defense map.

Reads CHESS_API_BASE and CHESS_GAME_ID from environment (injected by AgentPlayer).
No arguments needed — fetches the live position from the backend.

Output is markdown so it renders cleanly in the agent UI and is easy for the
model to scan. Sections:

  1. Phase annotation (early/late opening, middlegame, endgame).
  2. Material balance (static eval; tactically blind — see warning).
  3. ASCII board (uppercase = white, lowercase = black; a-h, 8-1).
  4. FEN and side to move.
  5. Your pieces under attack — for each of your pieces with at least one
     opponent attacker, lists the attackers and your defenders.
  6. Opponent pieces you're attacking — same, from the other side.

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
from pathlib import Path

import chess

# Sibling import of _eval helpers. The script is invoked from arbitrary cwd,
# so add this script's directory to sys.path before importing.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from _eval import (  # noqa: E402 — sys.path adjusted above
    EVAL_WARNING,
    MATERIAL,
    PIECE_NAMES,
    color_name,
    detect_phase,
    is_losing_on_square,
    phase_score,
    render_eval_line,
    safe_destination_squares,
    static_exchange_eval,
)
from _live import board_with_history, fetch_state  # noqa: E402
from _radar import render_radar  # noqa: E402

# Re-export phase_score so tests and external callers that previously imported
# it from show_position keep working. `detect_phase` is already imported above.
__all__ = ["detect_phase", "phase_score", "render_position", "compute_attack_chain", "format_chain"]


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
    """Return ordered attackers of `target` by `by_color`. Each element is
    (square_of_attacker, is_xray). is_xray=False for immediate attackers
    (visible to board.attackers()); True for sliders sitting behind an
    immediate attacker on the same ray, which activate after the front piece
    captures.

    Ordering: immediate attackers sorted cheapest-first (pawn < minor < rook
    < queen < king), with each immediate attacker's x-ray battery listed
    *directly after* that immediate attacker — matching the order pieces
    would join the exchange."""
    immediate = list(board.attackers(by_color, target))
    if not immediate:
        return []
    immediate.sort(key=lambda s: _piece_value(board.piece_at(s).piece_type))

    chain: list[tuple[int, bool]] = []
    for attacker_sq in immediate:
        chain.append((attacker_sq, False))
        chain.extend((s, True) for s in _xray_chain(board, by_color, target, attacker_sq))
    return chain


def _ray_kind(a: int, b: int) -> str | None:
    """Return 'orthogonal' if a-b lies on a rank or file, 'diagonal' if on a
    diagonal of equal abs(file_delta) == abs(rank_delta), else None.
    Treats same-square as None."""
    fa, ra = chess.square_file(a), chess.square_rank(a)
    fb, rb = chess.square_file(b), chess.square_rank(b)
    if fa == fb and ra == rb:
        return None
    if fa == fb or ra == rb:
        return "orthogonal"
    if abs(fa - fb) == abs(ra - rb):
        return "diagonal"
    return None


def _step(a: int, b: int) -> int:
    """Signed step from a to b along a straight ray. Assumes ray_kind(a, b)
    is not None."""
    fa, ra = chess.square_file(a), chess.square_rank(a)
    fb, rb = chess.square_file(b), chess.square_rank(b)
    df = (fb - fa) and ((fb - fa) // abs(fb - fa))
    dr = (rb - ra) and ((rb - ra) // abs(rb - ra))
    return df + dr * 8


def _xray_chain(board: chess.Board, by_color: bool, target: int, front_attacker: int) -> list[int]:
    """Walk from target -> front_attacker -> beyond, collecting same-color
    sliders that would activate after front_attacker captures on target.
    Only sliders that move along this ray count (rooks/queens for orthogonal,
    bishops/queens for diagonal)."""
    kind = _ray_kind(target, front_attacker)
    if kind is None:
        return []
    step = _step(target, front_attacker)
    if step == 0:
        return []

    if kind == "orthogonal":
        valid_types = {chess.ROOK, chess.QUEEN}
    else:
        valid_types = {chess.BISHOP, chess.QUEEN}

    # Walk from front_attacker outward (away from target). Stop at first
    # blocker of the wrong colour or wrong piece type.
    chain: list[int] = []
    sq = front_attacker + step
    while 0 <= sq < 64:
        # Bail out if we've left the ray (we cross a file/rank wrap).
        if _ray_kind(target, sq) != kind:
            break
        piece = board.piece_at(sq)
        if piece is None:
            sq += step
            continue
        if piece.color != by_color:
            break
        if piece.piece_type not in valid_types:
            break
        chain.append(sq)
        sq += step
    return chain


def _piece_value(piece_type: int) -> int:
    """Crude material weight for sorting attacker chains: lightest piece
    first (smallest exchange loss to the attacker)."""
    return {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 99}[piece_type]


def format_chain(board: chess.Board, by_color: bool, chain: list[tuple[int, bool]]) -> str:
    """Format an attacker/defender chain into prose:
    `knight on c6, rook on a1, then bishop on b2 via x-ray`."""
    parts: list[str] = []
    for sq, is_xray in chain:
        pinned = board.is_pinned(by_color, sq)
        label = piece_label(board, sq, pinned=pinned)
        if is_xray:
            parts.append(f"then {label} via x-ray")
        else:
            parts.append(label)
    return ", ".join(parts)


def _safe_squares_line(board: chess.Board, sq: int, own_color: bool) -> str | None:
    """One-line 'safe squares' hint for a piece that is currently losing
    material on its square. None when the piece is not actually losing (it is
    defended/trades even) or when there is no safe square to flag.

    SEE helpers are shared from _eval (also used by the ladder advisor)."""
    if not is_losing_on_square(board, sq, own_color):
        return None
    safe = safe_destination_squares(board, sq, own_color)
    if not safe:
        return "  ↳ no safe square to relocate it — consider defending it, "\
               "capturing the attacker, or counter-attacking instead."
    names = ", ".join(chess.square_name(s) for s in safe)
    return f"  ↳ safe squares to move it (not losing material there): {names}"\
           " — verify the full move with imagine_move (this ignores discovered"\
           " attacks)."


def attack_defense_section(
    board: chess.Board,
    own_color: bool,
    opp_color: bool,
    header: str,
    action: str,
    show_safe_squares: bool = False,
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
        # State the counts as explicit integers, not just a prose list the model
        # must tally itself. The board-visualization benchmark (2026-06-24) found
        # the model reads relations well but counts attackers on a square poorly
        # (0.20 from FEN) — so surface the number as a computed fact. Pure
        # mechanics: len() of the chains the tool already built. See
        # decisions/2026-06-23-board-visualization-benchmark.md.
        n_atk = len(attacker_chain)
        n_def = len(defender_chain)
        lines.append(
            f"- {desc}: {action} {n_atk} ({atk_str}); "
            f"defended by {n_def} ({def_str})"
        )
        # For OUR attacked pieces, when the piece is actually losing material
        # on its square, list where it can go without re-hanging it.
        if show_safe_squares:
            hint = _safe_squares_line(board, sq, own_color)
            if hint:
                lines.append(hint)
    if not found_any:
        lines.append("- (none)")
    return "\n".join(lines)


def _piece_list(board: chess.Board, color: bool) -> str:
    """Compact square-level inventory ("Kg1, Ra4, Rb1") — grounds the
    model's reasoning in the actual squares; FEN alone gets misread."""
    order = {chess.KING: 0, chess.QUEEN: 1, chess.ROOK: 2, chess.BISHOP: 3,
             chess.KNIGHT: 4, chess.PAWN: 5}
    pieces = sorted(
        ((order[board.piece_type_at(sq)], board.piece_at(sq).symbol().upper(), sq)
         for sq in chess.SQUARES if (pc := board.piece_at(sq)) and pc.color == color),
        key=lambda t: (t[0], t[2]),
    )
    return ", ".join(f"{sym}{chess.square_name(sq)}" for _, sym, sq in pieces) or "(none)"


def render_position(board: chess.Board, move_cap: int | None = None) -> str:
    """Markdown-formatted position report. Each section is a small heading
    so the agent (and the UI) can scan; the ASCII board sits in a fenced
    code block to preserve monospace alignment in markdown renderers.

    Pass a board carrying the real move stack when available — the radar's
    repetition and move-cap checks need it (a bare-FEN board still works,
    those checks just stay silent)."""
    own_color = board.turn
    opp_color = not own_color
    phase, score, move = detect_phase(board)

    # SITUATION header (adaptive priority) — the first thing the agent reads. It
    # triages the position from mechanical facts (material / threat / forcing / phase)
    # and names what to prioritise, so the same feature below is weighted correctly
    # for THIS position (e.g. a material-losing capture is fine when defending a mate,
    # bad when winning and safe). Informative, never move-selecting.
    situation_lines = []
    try:
        from _features import assess_situation
        situation_lines = assess_situation(board).get("lines", []) + [""]
    except Exception:
        situation_lines = []

    out = [
        *situation_lines,
        f"**Phase:** {phase} (move {move}, phase score {score}/24)",
        "",
        f"**{render_eval_line(board)}**",
        EVAL_WARNING,
        "",
        "```",
        render_ascii(board),
        "```",
        "",
        f"**Pieces:** white: {_piece_list(board, chess.WHITE)} · "
        f"black: {_piece_list(board, chess.BLACK)}",
        f"**FEN:** `{board.fen()}`",
        f"**Side to move:** {color_name(own_color)}",
        "",
        "## Your pieces under attack",
        "",
        attack_defense_section(
            board, own_color, opp_color,
            header="",
            action="attacked by",
            show_safe_squares=True,
        ).lstrip("\n"),
        "",
        "## Opponent pieces you are attacking",
        "",
        attack_defense_section(
            board, opp_color, own_color,
            header="",
            action="attacked by your",
        ).lstrip("\n"),
    ]
    # King-net visualisation: only in a minor-piece basic mate (K+2B / K+B+N
    # vs a lone king), where the whole technique is shrinking the king's free
    # region toward the right corner — seeing the net is the key aid. `*` marks
    # squares the bare king can still roam; `T` the target corner.
    net = _king_net_section(board)
    if net:
        out += ["", net]
    # Positional / tactical / fundamentals assessment (strengths, weaknesses,
    # potentials — both sides, with handling suggestions and wiki pointers).
    try:
        from _features import render_features
        feats = render_features(board)
        if feats:
            out += ["", feats]
    except Exception:
        pass  # features must never take down the position report
    radar = render_radar(board, move_cap=move_cap)
    if radar:
        out += ["", radar]
    return "\n".join(out)


def _king_net_section(board: chess.Board) -> str | None:
    """Render the lone king's free-region 'net' when this is a K+2B / K+B+N
    mate. None otherwise. Pure geometry; see _eval.render_king_net."""
    for own in (chess.WHITE, chess.BLACK):
        defender = not own
        defender_force = sum(
            len(board.pieces(pt, defender))
            for pt in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)
        )
        majors = sum(len(board.pieces(pt, own)) for pt in (chess.QUEEN, chess.ROOK))
        bishops = len(board.pieces(chess.BISHOP, own))
        knights = len(board.pieces(chess.KNIGHT, own))
        is_minor_mate = majors == 0 and (bishops >= 2 or (bishops >= 1 and knights >= 1))
        if defender_force == 0 and is_minor_mate:
            from _eval import bishop_corner_targets, king_free_region, render_king_net
            corners = bishop_corner_targets(board, own)
            ek = board.king(defender)
            target = min(corners, key=lambda c: chess.square_distance(ek, c)) if ek is not None else None
            size = len(king_free_region(board, defender))
            return (
                "## King net (squares the lone king can still reach)\n\n"
                f"```\n{render_king_net(board, defender, target)}\n```\n"
                f"The king's free region is **{size}** squares (`*`). The mate is "
                f"shrinking this net toward the target corner (`T`). A move that "
                f"reduces the `*` count is progress; one that grows it gives the "
                f"king room — reject it."
            )
    return None


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--fen",
        default=None,
        help=(
            "Analyse this position instead of the live game — a hypothetical "
            "board, e.g. the FEN that chess__imagine_move returned. The live "
            "game is not touched."
        ),
    )
    args = parser.parse_args()

    if args.fen:
        try:
            board = chess.Board(args.fen)
        except ValueError as exc:
            # A hallucinated/malformed FEN must NOT block the turn. Fall back
            # to the LIVE position with a clear note so the agent stops
            # reasoning about an imagined board. (Models routinely fabricate
            # FENs — e.g. a rank with 9 columns; never error out on it.)
            data = fetch_state()
            board = board_with_history(data)
            print(
                f"⚠ The FEN you passed (`{args.fen}`) is not a legal position "
                f"({exc}). Showing the LIVE game position instead — do not "
                f"analyse a board you typed by hand; trust this one.\n"
            )
            print(render_position(board, move_cap=data.get("move_cap")))
            return
        # Hypothetical boards have no history or move cap — the radar's
        # repetition/cap lines simply stay silent.
        print(render_position(board))
        return

    data = fetch_state()
    # Board carries the real move history when it replays cleanly (the
    # radar's repetition check needs the stack); _live.board_with_history
    # falls back to a bare-FEN board on any reconstruction problem so the
    # board view can never be taken down by history issues.
    board = board_with_history(data)
    print(render_position(board, move_cap=data.get("move_cap")))


if __name__ == "__main__":
    main()
