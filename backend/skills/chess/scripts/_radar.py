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

from pathlib import Path

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


def _drill_excerpt(page_rel: str) -> list[str]:
    """Inline a technique page's "What to do" rules. Retrieval from the
    agent's own wiki (the fair path): in a basic-mate endgame the drill must
    be in front of the model every turn — relying on it to re-read the page
    under fresh context demonstrably fails (the 2026-06-12 ladder game
    checked aimlessly for 50 plies with the page one tool call away)."""
    try:
        page = Path(__file__).resolve().parent.parent / "references" / page_rel
        text = page.read_text(encoding="utf-8")
        start = text.find("## What to do")
        if start < 0:
            return []
        end = text.find("\n## ", start + 5)
        section = text[start:end if end > 0 else None].strip()
        lines = section.splitlines()[:28]
        return ["  The drill, from that page (follow it literally each turn):"] + [
            f"  > {l}" for l in lines[1:] if l.strip()
        ]
    except Exception:
        return []


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
        lines += _drill_excerpt(_PAGE_LADDER)
    elif own_mat[chess.QUEEN] == 1:
        lines.append(
            f"- King + queen vs king is a forced mate (under ~10 moves) — "
            f"read `{_PAGE_KQ}`."
        )
        lines += _drill_excerpt(_PAGE_KQ)
    elif own_mat[chess.ROOK] == 1:
        lines.append(
            f"- King + rook vs king is a forced mate — read `{_PAGE_KR}`."
        )
        lines += _drill_excerpt(_PAGE_KR)
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
        lines += _drill_excerpt(_PAGE_KP)
    if board.has_insufficient_material(own):
        lines = [
            "- **You cannot checkmate with your remaining material** — "
            "the best available result is a draw."
        ]
    return lines


def _pawn_escort_lines(board: chess.Board, own: bool, psq: int) -> list[str]:
    """Which rule of the K+P escort drill applies now. Pure geometry:
    king-in-front, opposition, and the never-7th-with-check trap that drew
    game 9d2e1e58 (e7+?? Ke8, then the pawn fell)."""
    opp = not own
    my_k, opp_k = board.king(own), board.king(opp)
    pf, pr = chess.square_file(psq), chess.square_rank(psq)
    forward = 1 if own == chess.WHITE else -1
    promo_rank = 7 if own == chess.WHITE else 0
    seventh = promo_rank - forward
    pre = "- **Drill state** (K+P escort): "

    king_ahead = (
        (chess.square_rank(my_k) - pr) * forward > 0
        and abs(chess.square_file(my_k) - pf) <= 1
    )
    opposition = (
        chess.square_file(my_k) == chess.square_file(opp_k)
        and abs(chess.square_rank(my_k) - chess.square_rank(opp_k)) == 2
    )

    if pr == seventh:
        promo_sq = chess.square(pf, promo_rank)
        controlled = board.is_attacked_by(own, promo_sq)
        if controlled:
            return [pre + "your pawn is one step from promotion and your "
                    "king controls the promotion square — push it (verify "
                    "no stalemate with imagine_move), then mate with the "
                    "new queen."]
        return [pre + "your pawn stands on the second-to-last rank but your "
                "king does NOT control the promotion square — do NOT push "
                "yet. Bring your king to control the promotion square "
                "first; if the enemy king blockades, use opposition to "
                "lever it off."]
    if not king_ahead:
        return [pre + "your king is NOT in front of the pawn — RULE: march "
                "the KING (not the pawn) until it stands ahead of the pawn "
                "on its file or an adjacent file. The pawn only moves when "
                "the king already controls the square in front of it. "
                "NEVER push the pawn to the second-to-last rank with check "
                "— that position is a known draw."]
    if opposition:
        return [pre + "king in front ✓ and kings in opposition ✓ (enemy "
                "must give way) — RULE: advance your king diagonally to "
                "the side the enemy king did not go, or push the pawn one "
                "step to keep the king ahead. Re-check opposition next "
                "turn."]
    return [pre + "king in front ✓, kings NOT in opposition — RULE: move "
            "so the enemy king must step aside: take the opposition (same "
            "file, two ranks apart) or, if it refuses to commit, advance "
            "the pawn ONE step (never two) as a waiting move."]


def _drill_state_lines(board: chess.Board, own: bool) -> list[str]:
    """Which numbered rule of the basic-mate drill applies RIGHT NOW.

    Pure geometry matched against the wiki recipes (fence line present?
    piece touchable by the king? kings in opposition?) — the same check a
    human drilling the technique performs at a glance. It names the rule
    and the geometric condition; choosing and verifying the move stays with
    the agent. Only fires vs a bare king (the drills' precondition).
    """
    opp = not own
    opp_mat = _material(board, opp)
    if sum(opp_mat.values()) > 0:
        return []
    own_mat = _material(board, own)
    majors = [
        sq for pt in (chess.QUEEN, chess.ROOK) for sq in board.pieces(pt, own)
    ]
    if not majors:
        # K+P vs K: the escort drill. Fires only for the single-pawn case
        # (the multi-pawn endgame has too many shapes for a one-line rule).
        pawns = list(board.pieces(chess.PAWN, own))
        if len(pawns) == 1:
            return _pawn_escort_lines(board, own, pawns[0])
        return []

    ksq = board.king(opp)
    my_k = board.king(own)
    kf, kr = chess.square_file(ksq), chess.square_rank(ksq)

    # Target edge selection. With TWO majors the ladder is purely
    # rank-driven (fence a rank, check on the next, leapfrog to rank 1/8 —
    # no king march, no file fences), so we LOCK to the nearest back rank
    # and never reconsider: the previous "nearest of any fenced edge" rule
    # thrashed between rank and file targets turn-to-turn as the rooks moved
    # (game a971fff9, 2026-06-13), which is what broke the drill. With one
    # major we keep the original "prefer the edge already fenced toward,
    # else nearest" rule, since K+R/K+Q genuinely need king support and the
    # edge can be either a rank or a file.
    dists = {"rank-top": 7 - kr, "rank-bottom": kr, "file-h": 7 - kf, "file-a": kf}
    if len(majors) >= 2:
        edge = "rank-top" if kr >= 4 else "rank-bottom"
    else:
        fenced = {
            "rank-top": any(chess.square_rank(sq) == kr - 1 for sq in majors),
            "rank-bottom": any(chess.square_rank(sq) == kr + 1 for sq in majors),
            "file-h": any(chess.square_file(sq) == kf - 1 for sq in majors),
            "file-a": any(chess.square_file(sq) == kf + 1 for sq in majors),
        }
        existing = [e for e, ok in fenced.items() if ok]
        edge = min(existing, key=dists.get) if existing else min(dists, key=dists.get)
    if edge.startswith("rank"):
        fence_line = kr - 1 if edge == "rank-top" else kr + 1
        on_fence = [sq for sq in majors if chess.square_rank(sq) == fence_line]
        line_word, line_name = "rank", fence_line + 1
        king_line_name = f"rank {kr + 1}"
        opposition = (
            chess.square_file(my_k) == kf
            and abs(chess.square_rank(my_k) - kr) == 2
        )
    else:
        fence_line = kf - 1 if edge == "file-h" else kf + 1
        on_fence = [sq for sq in majors if chess.square_file(sq) == fence_line]
        line_word, line_name = "file", "abcdefgh"[fence_line]
        king_line_name = f"file {'abcdefgh'[kf]}"
        opposition = (
            chess.square_rank(my_k) == kr
            and abs(chess.square_file(my_k) - kf) == 2
        )

    touchable = [
        sq for sq in majors
        if chess.square_distance(sq, ksq) == 1 and not board.is_attacked_by(own, sq)
    ]

    def _slide_away_text(sq: int) -> str:
        """Name the slide-away move concretely: the piece's fence line and
        the far-side square. 'Slide along its line' alone was ambiguous —
        game 3a787edc slid the fence rook up the FILE (b5-b8) instead of
        along the rank, losing the fence."""
        f, r = chess.square_file(sq), chess.square_rank(sq)
        if edge.startswith("rank"):
            far_file = 7 if kf <= 3 else 0
            tgt = chess.square_name(chess.square(far_file, r))
            return (f"slide it ALONG RANK {r + 1} (sideways, not up the "
                    f"file) to the far side from the king — e.g. {tgt}")
        far_rank = 7 if kr <= 3 else 0
        tgt = chess.square_name(chess.square(f, far_rank))
        return (f"slide it ALONG FILE {'abcdefgh'[f]} (vertically) to the "
                f"far side from the king — e.g. {tgt}")

    out = []
    pre = "- **Drill state** (vs bare king): "
    # Lone queen: the K+Q drill is knight's-move shadowing, NOT a fence.
    if own_mat[chess.QUEEN] == 1 and own_mat[chess.ROOK] == 0:
        qsq = next(iter(board.pieces(chess.QUEEN, own)))
        if touchable:
            return [pre + f"your queen on {chess.square_name(qsq)} is adjacent "
                    f"to the enemy king and UNPROTECTED — it can simply be "
                    f"captured. Move it to safety (a knight's-move from the "
                    f"king) NOW."]
        on_edge = kf in (0, 7) or kr in (0, 7)
        knight_dist = chess.square_distance(qsq, ksq) == 2 and (
            abs(chess.square_file(qsq) - kf), abs(chess.square_rank(qsq) - kr)
        ) in ((1, 2), (2, 1))
        if not on_edge:
            msg = (pre + f"phase 1 (shrink): keep the queen a KNIGHT'S-MOVE "
                   f"from the enemy king and MIRROR its moves — no checks "
                   f"needed. Mirror means copy the king's last move "
                   f"DIRECTION (king went toward a rank/file, queen steps "
                   f"the same way), not just restore the distance on a "
                   f"different side. NEVER place the queen adjacent to the "
                   f"king unless protected (the king just takes it).")
            if not knight_dist:
                msg += (f" The queen on {chess.square_name(qsq)} is not at "
                        f"knight's-move distance now.")
            # Direction of the king's last step, read off the move stack —
            # the concrete fact the mirror rule needs.
            if board.move_stack:
                last = board.move_stack[-1]
                if last.to_square == ksq:
                    df = chess.square_file(ksq) - chess.square_file(last.from_square)
                    dr = chess.square_rank(ksq) - chess.square_rank(last.from_square)
                    ew = "kingside (h)" if df > 0 else ("queenside (a)" if df < 0 else "")
                    ns = "up (rank 8)" if dr > 0 else ("down (rank 1)" if dr < 0 else "")
                    direction = " and ".join(x for x in (ew, ns) if x)
                    if direction:
                        msg += (f" The king's last step went {direction} — "
                                f"shift the queen one square the same way.")
            # Anti-oscillation: returning the queen to the square she just
            # left is the no-progress loop that draws by repetition.
            if len(board.move_stack) >= 2:
                prev_own = board.move_stack[-2]
                if prev_own.to_square == qsq:
                    msg += (f" Your queen just came FROM "
                            f"{chess.square_name(prev_own.from_square)} — do "
                            f"NOT move her back there. If no mirroring square "
                            f"makes progress, leave the queen and march YOUR "
                            f"king one square toward the enemy king instead.")
            return [msg]
        if chess.square_distance(my_k, ksq) > 2:
            return [pre + "phase 2 (march): the enemy king is on the edge — "
                    "STOP moving the queen (one more shadow step risks "
                    "stalemate); walk YOUR king one square toward the enemy "
                    "king instead."]
        return [pre + "phase 3 (mate): your king is close — look for the "
                "queen check along the edge (protected by your king or from "
                "distance). Verify `gives checkmate` with imagine_move and "
                "watch for `stalemate`."]

    if touchable:
        out.append(
            pre + f"the enemy king can capture your piece on "
            f"{chess.square_name(touchable[0])} — RULE: "
            f"{_slide_away_text(touchable[0])}. Nothing else this turn."
        )
    elif not on_fence:
        out.append(
            pre + f"no fence — RULE: put a rook/queen on {line_word} "
            f"{line_name} (one line centre-side of the enemy king), far from "
            f"the king. The king must never cross it."
        )
    elif len(majors) >= 2:
        # Ladder pathologies before the generic check rule. Both are pure
        # geometry: a king touching a rook paralyses it even when the rook
        # is defended (it cannot ladder from there), and two majors stacked
        # on the same cross-line block each other's leapfrog while letting
        # the king chase both at once.
        harassed = [sq for sq in majors if chess.square_distance(sq, ksq) <= 1]
        if edge.startswith("rank"):
            stacked = len({chess.square_file(sq) for sq in majors[:2]}) == 1
            cross_word, own_word = "file", "rank"
        else:
            stacked = len({chess.square_rank(sq) for sq in majors[:2]}) == 1
            cross_word, own_word = "rank", "file"
        if harassed:
            out.append(
                pre + f"the enemy king is touching your piece on "
                f"{chess.square_name(harassed[0])} — even defended it cannot "
                f"ladder from there. RULE: "
                f"{_slide_away_text(harassed[0])}. Nothing else this turn."
            )
        elif stacked:
            out.append(
                pre + f"both your major pieces stand on the same {cross_word} "
                f"— they block each other's ladder and the king can chase "
                f"both. RULE: move one to the OPPOSITE side of the board "
                f"along its {own_word} (keep the fence line), so the rooks "
                f"work from different wings."
            )
        else:
            out.append(
                pre + f"fence on {line_word} {line_name} ✓ — RULE: check with "
                f"your OTHER major piece on {king_line_name} (the enemy "
                f"king's {line_word}), from far away; the king retreats one "
                f"line; the old checker becomes the new fence. Repeat to "
                f"the edge."
            )
    elif opposition:
        out.append(
            pre + f"fence ✓ and kings in opposition ✓ — RULE: CHECK on "
            f"{king_line_name} (the enemy king's {line_word}) now — a rook "
            f"move TO that {line_word}, far from the king; it must retreat. "
            f"Then re-fence. A check on any other line is a wasted move."
        )
    else:
        out.append(
            pre + f"fence on {line_word} {line_name} ✓, kings NOT in "
            f"opposition — RULE: step YOUR king one square toward the enemy "
            f"king (stay on your side of the fence). Do not move the fence "
            f"piece; do not check yet. If the enemy king just stepped aside "
            f"to dodge, make a one-square waiting move along the fence "
            f"instead."
        )
    return out


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
    lines += _drill_state_lines(board, own)
    lines += _king_geometry_lines(board, own)
    lines += _back_rank_lines(board, own)
    # Wiki-driven pattern triggers: geometry-present hints, each tracing to
    # a page the agent owns. See _patterns.py for the fairness contract.
    try:
        from _patterns import match_patterns
        lines += match_patterns(board)
    except Exception:
        pass  # pattern hints are never allowed to take down the radar
    lines += _passed_pawn_lines(board, own)
    lines += _draw_rule_lines(board, move_cap)
    if not lines:
        return None
    return "## Mate & draw radar\n\n" + "\n".join(lines)
