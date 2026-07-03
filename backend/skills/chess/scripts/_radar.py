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

import sys
from pathlib import Path

import chess

# Sibling import of _eval (SEE helpers for the ladder safe-square hints).
# The script may be imported from arbitrary cwd; ensure our dir is on path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _eval  # noqa: E402

# Wiki pages the radar may point to. Paths relative to references/.
_PAGE_LADDER = "mates/two-rook-ladder-mate.md"
_PAGE_KQ = "mates/king-queen-mate.md"
_PAGE_KR = "mates/king-rook-mate.md"
_PAGE_BACK_RANK = "mates/back-rank-mate.md"
_PAGE_CONVERT = "strategy/convert-advantage.md"
_PAGE_KP = "endgames/king-pawn-endings.md"
_PAGE_KBB = "mates/king-two-bishops-mate.md"
_PAGE_KBN = "mates/king-bishop-knight-mate.md"


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


_PIECE_VALUE = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9}


def _winning_safety_lines(board: chess.Board, own: bool) -> list[str]:
    """When ``own`` is clearly ahead on material, lead the radar with a
    don't-blunder reminder. Pure material count. The 2026-06-20 ranked batch
    lost easily-won games by hanging pieces from winning positions; a contextual
    'you are winning, play safe' nudge (which works far better than prose) is the
    cheap counter."""
    own_mat = _material(board, own)
    opp_mat = _material(board, not own)
    lead = sum(_PIECE_VALUE[pt] * (own_mat[pt] - opp_mat[pt]) for pt in own_mat)
    if lead < 3:
        return []
    return [
        f"- **You are winning (+{lead} material). Your #1 job now is to NOT "
        f"blunder.** No sacrifices; keep EVERY piece defended; trade pieces "
        f"(not pawns) to simplify toward a won endgame. Before any non-obvious "
        f"move, imagine it (chess__imagine_move) and confirm it does not hang "
        f"material — a single hung piece throws the win away."
    ]


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
        # The live per-turn drill advisor is emitted by _drill_state_lines.
    elif own_mat[chess.ROOK] == 1:
        lines.append(
            f"- King + rook vs king is a forced mate — read `{_PAGE_KR}`."
        )
        # The live per-turn drill advisor is emitted by _drill_state_lines.
    elif own_mat[chess.BISHOP] >= 2:
        if own_mat[chess.PAWN] > 0:
            lines.append(
                "- Two bishops can force mate, but promoting a pawn to a queen "
                f"first is simpler and faster — read `{_PAGE_CONVERT}`."
            )
        else:
            lines.append(
                "- King + two bishops is a FORCED mate (≤19 moves): drive the "
                "king into a CORNER with the bishops side by side on adjacent "
                f"diagonals, king marching up — read `{_PAGE_KBB}`."
            )
    elif own_mat[chess.BISHOP] >= 1 and own_mat[chess.KNIGHT] >= 1:
        if own_mat[chess.PAWN] > 0:
            lines.append(
                "- Bishop+knight can force mate but it is the hardest basic mate; "
                f"if you have a pawn, promote it and mate with the queen instead — "
                f"read `{_PAGE_KP}`."
            )
        else:
            lines.append(
                "- King + bishop + knight is a FORCED mate (≤33 moves) but the "
                "HARDEST one: the king can only be mated in the corner matching "
                f"your BISHOP's colour — read `{_PAGE_KBN}`."
            )
    elif own_mat[chess.KNIGHT] >= 2 and own_mat[chess.BISHOP] == 0:
        lines.append(
            "- Two knights + king CANNOT force mate against a bare king (it is a "
            "draw with best defence). If the opponent has a pawn, different rules "
            f"apply; otherwise the best result is a draw."
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


def _ladder_lines(board, own, opp, majors, own_mat, ksq, opp_bare):
    """The two-major (R+R / Q+R) ladder advisor — board-ADAPTIVE and minimal.

    Earlier this emitted the whole method plus 6-8 caveats every turn, which
    drowned the model and caused drift (it laddered correctly then played a
    junk move at the finish, game b60f731d). Now it picks the ONE rule that
    applies right now and prints a short header + that rule. Tool-fair: it
    states which line to wall/check and which squares are dead — facts about
    the board — and never names the move to play.

    The drive axis is RANK or FILE, whichever edge the king is nearest; all
    the geometry below is written in terms of that axis (k = the king's coord
    on the driving axis, the wall sits one step behind it). This is the
    file↔rank transposition done once, not duplicated.
    """
    has_q = own_mat[chess.QUEEN] >= 1
    kf, kr = chess.square_file(ksq), chess.square_rank(ksq)
    my_k = board.king(own)

    # ── PRIORITY 0: eliminate the opponent's threats before going for the
    # mate. Tunnel-visioning on a mating drill loses won positions to enemy
    # counterplay. The sharpest, most ladder-specific case is a pawn about to
    # promote: laddering lets it queen and the new MAJOR breaks the mate (game
    # 912d0f7f: the agent laddered through ...c2-c1=Q+). We trigger on that
    # concrete, detectable threat but state the GENERAL principle. (Other
    # threats — a hanging rook, a check — are handled by the SEE/safe-square
    # logic and the rules of the game.) We never fire if we can mate THIS move
    # (mate ends it before any threat matters). Fact, not a move.
    have_mate_now = any(
        (lambda a: (a.push(m), a.is_checkmate())[1])(board.copy(stack=False))
        for m in board.legal_moves
    )
    if not have_mate_now:
        # The enemy promotes on its FAR rank: White on rank 8 (idx 7), Black on
        # rank 1 (idx 0). One push away is that rank ∓1.
        promo_rank = 7 if opp == chess.WHITE else 0
        step_rank = 6 if opp == chess.WHITE else 1
        threats = []
        for psq in board.pieces(chess.PAWN, opp):
            if chess.square_rank(psq) == step_rank:
                # can it actually advance or capture to the back rank next move?
                pf = chess.square_file(psq)
                targets = [chess.square(pf, promo_rank)]
                for df in (-1, 1):
                    if 0 <= pf + df <= 7:
                        targets.append(chess.square(pf + df, promo_rank))
                if any(board.piece_at(t) is None or
                       (board.piece_at(t) and board.piece_at(t).color == own)
                       for t in targets):
                    threats.append(psq)
        if threats:
            names = ", ".join(chess.square_name(s) for s in threats)
            return ["- **Eliminate the opponent's threat before mating.** The "
                    f"enemy pawn(s) on {names} promote next move — a new major "
                    "would break your mating net. Handle it FIRST (capture the "
                    "pawn, block/cover its promotion square, or play a faster "
                    "forcing mate), then resume the mate. Verify with "
                    "imagine_move."]

        # A pawn that isn't promoting NEXT move can still be a runner: it may
        # capture an UNDEFENDED winning-side pawn and break free toward
        # promotion (game 7d4b666a, 2026-06-22: ...cxb3 then b2/b1=Q while the
        # agent mated elsewhere). Flag an enemy pawn that can capture an
        # undefended own pawn — deal with the source before mating.
        runner_threats = []
        for psq in board.pieces(chess.PAWN, opp):
            pf, pr = chess.square_file(psq), chess.square_rank(psq)
            cap_rank = pr - 1 if opp == chess.BLACK else pr + 1
            if not 0 <= cap_rank <= 7:
                continue
            for df in (-1, 1):
                cf = pf + df
                if not 0 <= cf <= 7:
                    continue
                tgt = chess.square(cf, cap_rank)
                victim = board.piece_at(tgt)
                if (victim is not None and victim.color == own
                        and victim.piece_type == chess.PAWN
                        and not board.attackers(own, tgt)):
                    runner_threats.append((psq, tgt))
        if runner_threats:
            pawn_names = ", ".join(
                f"{chess.square_name(p)}x{chess.square_name(t)}"
                for p, t in runner_threats)
            return ["- **Stop the enemy runner before mating.** The enemy pawn "
                    f"can capture your undefended pawn ({pawn_names}) and run "
                    "toward promotion — a new queen would wreck the win. Handle "
                    "it FIRST: capture that enemy pawn, defend/advance your "
                    "attacked pawn, or trade the pair off. Verify with "
                    "imagine_move, then resume the mate."]

        # An already-advanced enemy pawn (within 2 of promotion) that nothing of
        # ours blockades/attacks is a runner in motion — flag it before mating
        # (game 7d4b666a: a black b-pawn ran from b3 to b1=Q while the agent
        # mated elsewhere). A rook on the promotion FILE counts as control.
        adv_runners = []
        for psq in board.pieces(chess.PAWN, opp):
            pr = chess.square_rank(psq)
            steps = pr if opp == chess.BLACK else 7 - pr
            if steps > 2:
                continue
            pf = chess.square_file(psq)
            psq_promo = chess.square(pf, promo_rank)
            controls_file = any(
                chess.square_file(s) == pf
                for s in board.pieces(chess.ROOK, own)
            ) or board.attackers(own, psq_promo)
            if not controls_file and not board.attackers(own, psq):
                adv_runners.append(psq)
        if adv_runners:
            rn = ", ".join(chess.square_name(s) for s in adv_runners)
            return ["- **Stop the advanced enemy pawn before mating.** The pawn "
                    f"on {rn} is close to promoting and nothing of yours blocks "
                    "or attacks it — a new queen would wreck the win. Deal with "
                    "it FIRST: put a rook on its file/promotion square or capture "
                    "it, verify with imagine_move, then resume the mate."]

    # Pick the driving axis+direction. Capablanca's rule for the lone king is
    # "drive it to the LAST LINE ON ANY SIDE" — i.e. the NEAREST edge, not a
    # fixed far one (Chess Fundamentals Ex.1/2: a centre king is herded to
    # whichever side it runs to, mating on a rank OR a file). The old code let a
    # rook on the rank just behind a near-edge king "lock" the drive toward the
    # FAR edge, so a king already one step from rank 1 got laddered all the way
    # to rank 8 — the long way (game 362c4292, 2026-06-22). Fix: choose by
    # nearest edge first; only when the king is mid-board (≥2 from every edge,
    # no edge is clearly nearest) does an existing wall persist the direction
    # to avoid turn-to-turn thrash.
    def coord(sq, axis):
        return chess.square_rank(sq) if axis == "rank" else chess.square_file(sq)
    dtop, dbot, dright, dleft = 7 - kr, kr, 7 - kf, kf
    nearest = min(dtop, dbot, dright, dleft)
    if nearest <= 1:
        # King is on or one step from an edge — mate it against THAT edge.
        if nearest in (dbot, dtop) and nearest == min(dbot, dtop):
            axis, to_high = "rank", (dtop < dbot)
        elif nearest == min(dleft, dright):
            axis, to_high = "file", (dright < dleft)
        else:
            axis, to_high = "rank", (dtop < dbot)
        # Resolve exact ties (king in a corner / equidistant) deterministically.
        if dbot == dtop and nearest in (dbot, dtop):
            to_high = (dtop <= dbot)
    else:
        # Mid-board: let an existing wall persist the committed direction so the
        # drive doesn't thrash; otherwise fall back to nearest edge.
        wall_locks = []
        for axis_ in ("rank", "file"):
            k_ = kr if axis_ == "rank" else kf
            below = any(coord(sq, axis_) == k_ - 1 for sq in majors)
            above = any(coord(sq, axis_) == k_ + 1 for sq in majors)
            if below ^ above:
                wall_locks.append((axis_, below))
        if wall_locks:
            axis, to_high = wall_locks[0]
        else:
            if nearest in (dtop, dbot):
                axis, to_high = "rank", (dtop <= dbot)
            else:
                axis, to_high = "file", (dright <= dleft)

    k = kr if axis == "rank" else kf          # king's coord on the drive axis
    line_word = "rank" if axis == "rank" else "file"
    cross_word = "file" if axis == "rank" else "rank"
    def name_of(c):                            # 1-indexed rank, or file letter
        return str(c + 1) if axis == "rank" else "abcdefgh"[c]
    king_line = name_of(k)
    edge_c = 7 if to_high else 0
    edge_name = name_of(edge_c)
    wall_c = k - 1 if to_high else k + 1
    on_edge = (k == edge_c)

    def on_line(sq, c):                         # rook on the drive-axis line c
        return coord(sq, axis) == c
    king_line_majors = [s for s in majors if on_line(s, k)]
    wall_majors = [s for s in majors if 0 <= wall_c <= 7 and on_line(s, wall_c)]
    names = lambda sqs: ", ".join(chess.square_name(s) for s in sqs) or "none"

    pre = "- **Ladder** "
    if not opp_bare:
        pre += "(opp has no major — run the king down, watch its minors/pawns can't grab a rook) "

    # ── PRIORITY 0.5: win a FREE enemy pawn. When the opponent is down to
    # king + pawns, a pawn you can capture safely (the king can't recapture and
    # SEE says it doesn't hang) is free material AND removes a piece that
    # clutters the mating net — those very pawns sit on the king's rank and
    # block the ladder check (game 57d05c1f, 2026-06-22: the agent had Rxc7
    # free for several moves and instead shuffled rooks / played idle checks).
    # Reducing to a truly bare king makes the drill clean. State it as a fact
    # (this pawn is capturable for free); the agent picks and verifies.
    free_pawn_caps = []
    for mv in board.legal_moves:
        if board.piece_type_at(mv.from_square) not in (chess.ROOK, chess.QUEEN):
            continue
        tgt = board.piece_at(mv.to_square)
        if tgt is None or tgt.color != opp or tgt.piece_type != chess.PAWN:
            continue
        a = board.copy(stack=False); a.push(mv)
        if not _eval.is_losing_on_square(a, mv.to_square, own):
            free_pawn_caps.append((mv.to_square, chess.square_name(mv.to_square)))
    if free_pawn_caps:
        sqs = ", ".join(sorted({n for _, n in free_pawn_caps}))
        return [pre + f"**win the free pawn on {sqs}** — a rook can capture it "
                f"safely (the king cannot recapture; verify with imagine_move). "
                f"Take it: it is free material and it clears the enemy pawn off "
                f"the board so the ladder check is no longer blocked. Reduce to a "
                f"bare king, then mate."]

    # ── PRIORITY 1: a rook is hanging / would self-block. The user's rule:
    # if a rook is capturable, OR two rooks share the drive line so they block,
    # slide that rook sideways FIRST — to a CROSS-line the other rook is NOT on.
    # SEE considers all enemy pieces, so this also covers minors/pawns.
    losing = [s for s in majors if _eval.is_losing_on_square(board, s, own)]
    # A rook is only "hanging, retreat it" if it can't instead give a SAFE
    # CHECK this move: a check is its own protection (the opponent must answer
    # it and cannot just capture the checker), and a driving check is exactly
    # the ladder move. Telling the agent to retreat a rook that can deliver a
    # safe check sent it into an endless shuffle (game 08e916ca, 2026-06-23:
    # Rd1 was "capturable" by the c2 king, but Rd2+ was a safe driving check —
    # the radar said "slide to safety" and it shuffled for 30+ moves). Drop any
    # rook from `losing` that has a safe check available.
    def _has_safe_driving_check(rsq: int) -> bool:
        # A rook that can give a safe check ON THE KING'S OWN LINE (the rank or
        # file the king stands on) isn't "hanging" — that check IS the ladder
        # driving move: the king must step off its line toward the edge, and it
        # cannot capture the checker (the check was verified safe). Retreating
        # such a rook wastes the tempo and loops (game 08e916ca, 2026-06-23:
        # Rd2+ along the king's rank was a safe driving check, but the radar
        # said "slide the hanging rook to safety", causing a 30-move shuffle).
        # Mate also counts. A safe check that is NOT on the king's line (a spite
        # check) does not excuse leaving the rook en prise.
        for mv in board.legal_moves:
            if mv.from_square != rsq or not board.gives_check(mv):
                continue
            a = board.copy(stack=False); a.push(mv)
            if _eval.is_losing_on_square(a, mv.to_square, own):
                continue
            on_king_line = (chess.square_rank(mv.to_square) == kr
                            or chess.square_file(mv.to_square) == kf)
            if a.is_checkmate() or on_king_line:
                return True
        return False
    losing = [s for s in losing if not _has_safe_driving_check(s)]
    # Two rooks blocking: they sit on the same CROSS line (e.g. same file while
    # we drive along ranks) so one can't pass the other to reach the next line.
    cross = lambda sq: coord(sq, "file" if axis == "rank" else "rank")
    block_pair = None
    for i in range(len(majors)):
        for j in range(i + 1, len(majors)):
            if cross(majors[i]) == cross(majors[j]):
                block_pair = (majors[i], majors[j]); break
        if block_pair:
            break

    if losing:
        hsq = losing[0]
        safe = _eval.safe_destination_squares(board, hsq, own)
        # prefer squares that KEEP the line this rook cuts off, AND are on a
        # cross-line the OTHER rook is not on (so they don't block each other).
        other_cross = {cross(s) for s in majors if s != hsq}
        keep = [s for s in safe if (on_line(s, coord(hsq, axis)) or cross(s) == cross(hsq))
                and cross(s) not in other_cross]
        chosen = keep or [s for s in safe if cross(s) not in other_cross] or safe
        chosen = sorted(chosen, key=lambda s: -chess.square_distance(s, ksq))[:6]
        return [pre + f"your rook on {chess.square_name(hsq)} can be captured — "
                f"slide it to safety FIRST, to a {cross_word} the other rook is "
                f"NOT on so they don't block each other. Safe squares: "
                f"{names(chosen)}. (A queen beside a rook already guards it — "
                f"then no need; verify with imagine_move.)"]

    if block_pair:
        a, b = block_pair
        return [pre + f"your rooks on {chess.square_name(a)} and "
                f"{chess.square_name(b)} share a {cross_word}, so they block "
                f"each other. Move one to a DIFFERENT {cross_word} (keep one on "
                f"the king's {line_word} {king_line}, one on the {line_word} "
                f"behind) so each can slide freely."]

    # ── Self-block: our own king on the king's drive line blocks the check.
    if my_k is not None and on_edge and coord(my_k, axis) == k:
        return [pre + f"your OWN king is on {line_word} {king_line} with the "
                f"enemy king, so a check along it is blocked by your king. Mate "
                f"from the side AWAY from your king, or step your king off "
                f"{line_word} {king_line} first."]

    # ── Compute the safe vs dead CHECK squares along the king's drive line.
    # (Done here, before the blocked-line check, because "is the ladder check
    # blocked?" means "is there no SAFE check along the king's line?" — a
    # check that just captures a blocker the king recaptures does NOT count.)
    bad, safe_ch = [], []
    wall_set = set(wall_majors)
    for mv in board.legal_moves:
        if board.piece_type_at(mv.from_square) not in (chess.ROOK, chess.QUEEN):
            continue
        if mv.from_square in wall_set:
            continue
        if coord(mv.to_square, axis) != k or not board.gives_check(mv):
            continue
        a = board.copy(stack=False); a.push(mv)
        (safe_ch if not _eval.is_losing_on_square(a, mv.to_square, own) else bad)\
            .append(mv.to_square)
    safe_cross = sorted({name_of(cross(s)) for s in safe_ch})

    # ── PRIORITY 1.5: the ladder check along the king's line is BLOCKED.
    # The drill says "check along the king's line with the other rook", but a
    # piece sitting ON that line between a rook and the king leaves no SAFE
    # check there — the agent then loops trying an impossible/hanging move
    # (game 57d05c1f, 2026-06-22: enemy c-pawn on the king's rank blocked every
    # rank check, and the only checking move Rxc6+ hung the rook to the king,
    # so the agent shuffled rooks for dozens of moves). Detect "no SAFE check
    # along the king's line AND something is on that line", and surface the
    # GENERAL set of fixes — don't name the move. Point at imagine_line so the
    # agent plans the (still forced) sequence instead of re-asserting the
    # blocked drill step.
    no_line_check = not safe_ch
    # The OBSTRUCTIONS on the king's drive line that actually block a ladder
    # check: a piece on that line CLOSE to the king (within 2 squares along the
    # line). A far-away piece on the same line — e.g. our own b2 pawn when the
    # king is on b6 — does NOT obstruct a check delivered between a rook and the
    # king, so it must not count (it caused a false "blocked" on position A,
    # 2026-06-22). Our own rooks/queen on the line are the *checkers*, never
    # obstructions.
    line_blockers = [
        sq for sq in chess.SQUARES
        if sq != ksq and board.piece_at(sq) is not None
        and coord(sq, axis) == k
        and chess.square_distance(sq, ksq) <= 2
        and board.piece_type_at(sq) != chess.KING
        and not (board.color_at(sq) == own
                 and board.piece_type_at(sq) in (chess.ROOK, chess.QUEEN))
    ]
    if no_line_check and line_blockers:
        own_block = [s for s in line_blockers if board.color_at(s) == own]
        enemy_block = [s for s in line_blockers if board.color_at(s) == opp]
        opts = []
        if enemy_block:
            opts.append(
                f"**capture the enemy piece(s) on {names(enemy_block)}** that "
                f"block the {line_word} — but only with a rook the king CANNOT "
                f"recapture (double your rooks / support the capture first, else "
                f"you just hang the rook)")
        if own_block:
            opts.append(
                f"**move your own piece(s) on {names(own_block)}** off "
                f"{line_word} {king_line} so the check has a clear line")
        # Switching the drive axis is viable iff a SAFE check exists along the
        # perpendicular line through the king (same test as the drive line).
        perp_axis = "file" if axis == "rank" else "rank"
        perp_k = kf if perp_axis == "file" else kr
        perp_safe = []
        for mv in board.legal_moves:
            if board.piece_type_at(mv.from_square) not in (chess.ROOK, chess.QUEEN):
                continue
            if coord(mv.to_square, perp_axis) != perp_k or not board.gives_check(mv):
                continue
            a = board.copy(stack=False); a.push(mv)
            if not _eval.is_losing_on_square(a, mv.to_square, own):
                perp_safe.append(mv.to_square)
        if perp_safe:
            opts.append(
                f"**switch the drive to the {perp_axis}** — the king's {perp_axis} "
                f"is open, so fence and check along it toward the nearer "
                f"{perp_axis} edge instead")
        menu = "; or ".join(opts) if opts else (
            "clear the line, switch the drive axis, or capture the blocker safely")
        return [pre + f"the ladder check along the king's {line_word} "
                f"{king_line} is **BLOCKED** by {names(line_blockers)} on that "
                f"{line_word} — you cannot check there as the drill says, so act "
                f"accordingly: {menu}. Plan the forced sequence with "
                f"`chess__imagine_line` and verify each move with "
                f"`chess__imagine_move`."]

    # ── PRIORITY 2: no wall yet → build it (a QUIET move, not a check).
    if not wall_majors and 0 <= wall_c <= 7:
        return [pre + f"king on {line_word} {king_line}, driving to {line_word} "
                f"{edge_name}. No WALL yet — make a quiet rook move onto "
                f"{line_word} {name_of(wall_c)} (the {line_word} just behind the "
                f"king, away from {line_word} {edge_name}), far from the king. "
                f"Not a check. Your other rook then checks along {line_word} "
                f"{king_line}."]

    # ── PRIORITY 3: king already on the edge → FINISH.
    if on_edge:
        if safe_cross:
            return [pre + f"king on the edge ({line_word} {king_line}), wall on "
                    f"{line_word} {name_of(wall_c)} ✓. CHECK along {line_word} "
                    f"{king_line} from a {cross_word} ≥2 from the king "
                    f"({cross_word}s {', '.join(safe_cross)} are safe) — that "
                    f"check is mate. Confirm `gives checkmate` with imagine_move."]
        return [pre + f"king on the edge ({line_word} {king_line}) but every "
                f"check would land next to it (captured). Make a WAITING move: "
                f"slide the WALL rook sideways along {line_word} "
                f"{name_of(wall_c)}, far from the king. The king must step "
                f"toward the corner, then the check is mate. Verify with "
                f"imagine_move (watch for stalemate)."]

    # ── PRIORITY 4: wall is up, king not on edge → CHECK to push it one line.
    msg = (pre + f"wall on {line_word} {name_of(wall_c)} ✓. CHECK along the "
           f"king's {line_word} {king_line} with the OTHER rook, from a "
           f"{cross_word} far from the king, to push it toward {line_word} "
           f"{edge_name}.")
    if safe_cross:
        msg += f" Safe checking {cross_word}s (rook stays uncapturable): {', '.join(safe_cross)}."
    if bad:
        msg += (f" A check on {', '.join(chess.square_name(s) for s in sorted(set(bad)))}"
                f" hangs the rook — avoid it.")
    if has_q:
        msg += (" QUEEN: keep it ≥2 from the king unless a rook guards it; a "
                "quiet move to 0 king-squares is stalemate.")
    return [msg]


def _minor_mate_lines(board: chess.Board, own: bool) -> list[str]:
    """Advisor for the two minor-piece forced mates (K+2B, K+B+N) vs a bare king.

    Both drive the king to a CORNER (K+2B: any corner; K+B+N: only the corner of
    the bishop's colour). The state comes from `_eval.minor_confine_state` — pure
    geometry that classifies 'reposition a piece' vs 'march the king' without
    naming a move (tool-fairness: facts about the board, not the move to play).
    The agent picks and verifies with imagine_move."""
    bishops = list(board.pieces(chess.BISHOP, own))
    knights = list(board.pieces(chess.KNIGHT, own))
    is_kbb = len(bishops) >= 2
    page = _PAGE_KBB if is_kbb else _PAGE_KBN

    # Same-coloured two bishops cannot force mate — rare (double promotion), but
    # state it honestly rather than send the agent on an impossible drill.
    if is_kbb and len({(chess.square_file(b) + chess.square_rank(b)) % 2 for b in bishops}) == 1:
        return ["- Your two bishops are on the SAME colour — they cannot force "
                "mate against a bare king (it is a draw). Aim only to avoid "
                "losing; promote a pawn if you have one."]

    corners = _eval.bishop_corner_targets(board, own)
    cs = _eval.minor_confine_state(board, own, corners)
    ksq = board.king(not own)
    kd = _eval.kings_distance(board)

    # mate available now?
    has_mate = any(
        (board.push(mv), board.is_checkmate(), board.pop())[1]
        for mv in list(board.legal_moves)
    )
    out = []
    name = "K+2B" if is_kbb else "K+B+N"
    if has_mate:
        return [f"- {name}: there is a CHECKMATE this move — scan "
                f"chess__list_legal_moves for the `checkmate` flag and play it."]

    if cs is None:
        return [f"- {name} is a forced mate — read `{page}` and drive the king "
                f"to the corner."]

    corner = cs["target_corner"]
    ekm = cs["enemy_king_moves"]
    region = cs["region_size"]
    best_region = cs["best_region"]
    if is_kbb:
        corner_clause = f"any corner (nearest: **{corner}**)"
        piece_clause = ("the two bishops as a moving wall on ADJACENT diagonals "
                        "(side by side) — together they cut a barrier the king "
                        "cannot cross")
    else:
        corner_clause = (f"the **{corner}** corner (ONLY a corner of your "
                         "BISHOP's colour can mate — the other two corners can't, "
                         "do not waste moves driving there)")
        piece_clause = ("the bishop on the long diagonal and the knight to seal "
                        "the OTHER-coloured squares the bishop can't cover")
    out.append(
        f"- {name} method (read `{page}`): drive the enemy king to {corner_clause}. "
        f"The king's **free region is {region} squares** (the `*` net in the board "
        f"above); your kings are **{kd}** apart. The whole mate is SHRINKING that "
        f"net toward the corner: keep your king close to lead, and use "
        f"{piece_clause}."
    )

    # Stalemate guard — minors near a cornered king stalemate easily.
    if ekm <= 1:
        out.append(
            "- **STALEMATE DANGER:** the enemy king has "
            f"{ekm} legal move(s). Do NOT make a quiet move that leaves it zero "
            "moves without check — give a check, or march your king. Confirm "
            "`gives checkmate` (never `stalemate`) in imagine_move."
        )
        return out

    if cs["can_tighten"] and best_region < region:
        out.append(
            f"- A piece move SHRINKS the net (from {region} to {best_region} "
            "squares) without hanging — find it with imagine_move (try bishop/"
            "knight moves; pick the one that most reduces the king's free region "
            "toward the target corner and is not stalemate). Keep pieces defended "
            "and coordinated; never park a bishop next to the king undefended."
        )
    else:
        out.append(
            "- No piece move shrinks the net right now — STEP YOUR KING one "
            "square toward the enemy king (toward the target corner). The king "
            "must lead; the pieces hold the wall and seal the next line after."
        )
    out.append(
        "- To plan the maneuver, use chess__imagine_line to play several of your "
        "own moves ahead and watch the net shrink (it reports the king's region "
        "after each move) — these mates are won by a multi-move plan, not one move."
    )
    return out


def _promotion_threat_squares(board: chess.Board, opp: bool, own: bool) -> list[int]:
    """Enemy pawn squares that can promote on the opponent's NEXT move — by
    advancing to, or capturing onto, their back rank. Pure rules-of-chess
    geometry. Used to make the basic-mate advisors defer to a queening pawn
    (a new enemy piece would break the mating net)."""
    promo_rank = 7 if opp == chess.WHITE else 0
    step_rank = 6 if opp == chess.WHITE else 1
    out: list[int] = []
    for psq in board.pieces(chess.PAWN, opp):
        if chess.square_rank(psq) != step_rank:
            continue
        pf = chess.square_file(psq)
        targets = [chess.square(pf, promo_rank)]
        for df in (-1, 1):
            if 0 <= pf + df <= 7:
                targets.append(chess.square(pf + df, promo_rank))
        for t in targets:
            tp = board.piece_at(t)
            # advance to an empty square, or capture an own (winning-side) piece
            if (t == chess.square(pf, promo_rank) and tp is None) or \
               (t != chess.square(pf, promo_rank) and tp is not None and tp.color == own):
                out.append(psq)
                break
    return out


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
    own_mat = _material(board, own)
    majors = [
        sq for pt in (chess.QUEEN, chess.ROOK) for sq in board.pieces(pt, own)
    ]
    opp_has_major = opp_mat[chess.QUEEN] > 0 or opp_mat[chess.ROOK] > 0
    opp_bare = sum(opp_mat.values()) == 0

    # The TWO-MAJOR ladder is a real winning plan even when the opponent still
    # has MINOR pieces / pawns (we run the king down with the rooks; stray
    # enemy pieces are handled by the SEE safe-square logic below). So it fires
    # whenever we have 2+ majors and the opponent has NO major of its own —
    # not only against a bare king. The single-major (K+R / K+Q) and K+P
    # escort drills are precise techniques that DO require a bare king (enemy
    # pieces change them), so those keep the strict gate.
    if len(majors) >= 2:
        if opp_has_major:
            return []
    else:
        if not majors:
            # No major piece. The minor-piece mates (K+2B / K+B+N) and the K+P
            # escort drill are precise techniques that assume a BARE king (an
            # enemy pawn changes them), so they keep the strict gate.
            if not opp_bare:
                return []
            bishops = len(board.pieces(chess.BISHOP, own))
            knights = len(board.pieces(chess.KNIGHT, own))
            if bishops >= 2 or (bishops >= 1 and knights >= 1):
                return _minor_mate_lines(board, own)
            pawns = list(board.pieces(chess.PAWN, own))
            if len(pawns) == 1:
                return _pawn_escort_lines(board, own, pawns[0])
            return []
        # Exactly one major (K+R / K+Q). The confine drill fires whenever the
        # opponent is reduced to KING + PAWNS ONLY (no piece) — not just a bare
        # king. Most realistic conversions leave the loser a pawn; gating on
        # 'bare' silently dropped the drill exactly when the agent was mopping
        # up, so it flailed — moving its king when the rook should confine
        # (game 541b95da). confine_state already tolerates enemy pawns; an
        # enemy pawn near promotion is handled by the promotion-threat note in
        # the single-major renderer below. An enemy PIECE changes the technique,
        # so that stays gated out.
        opp_nonpawn = (opp_mat[chess.QUEEN] + opp_mat[chess.ROOK]
                       + opp_mat[chess.BISHOP] + opp_mat[chess.KNIGHT])
        if opp_nonpawn > 0:
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
        # Two-rook ladder drives the king to a RANK edge. The direction must
        # be STICKY: a `kr>=4 ? top : bottom` test flips the moment a check
        # pushes the king across the middle, reversing the whole drive
        # (game dafe6b95, 2026-06-13). So the FENCE decides the direction —
        # a rook on the rank just below the king means "drive up", a rook on
        # the rank just above means "drive down". Only when no fence exists
        # yet do we choose by nearest rank (and commit to it thereafter by
        # placing the fence on that side).
        fence_below = any(chess.square_rank(sq) == kr - 1 for sq in majors)
        fence_above = any(chess.square_rank(sq) == kr + 1 for sq in majors)
        if fence_below and not fence_above:
            edge = "rank-top"
        elif fence_above and not fence_below:
            edge = "rank-bottom"
        else:
            # No fence committed yet: drive toward the rank edge AWAY from our
            # own king, so the friendly king never blocks the mating check on
            # the final rank (the self-block that stalled game 8909ef13 when
            # the king was driven onto White's own back rank). Fall back to the
            # nearest edge only when our king is mid-board (no clear far side).
            my_k = board.king(own)
            my_kr = chess.square_rank(my_k) if my_k is not None else None
            if my_kr is not None and my_kr <= 2:
                edge = "rank-top"        # our king is low → drive the enemy up
            elif my_kr is not None and my_kr >= 5:
                edge = "rank-bottom"     # our king is high → drive it down
            else:
                edge = "rank-top" if (7 - kr) <= kr else "rank-bottom"
    else:
        # Single major (K+R / K+Q): the drive direction MUST be consistent with
        # the white king's side, or the rook check pushes the enemy king the
        # WRONG way and the mate thrashes (game 4a211a2a, 2026-06-17: fence on
        # rank 5 above the king while the white king sat below, so Rh4+ shoved
        # the king UP through the vacated rank). The enemy king must be driven
        # to the edge the WHITE KING is NOT blocking — i.e. the white king ends
        # on the centre side, shouldering the king toward the edge.
        mf = chess.square_file(my_k) if my_k is not None else 4
        mr = chess.square_rank(my_k) if my_k is not None else 4
        # For each candidate edge, the white king is "on the centre side" (good)
        # when it sits between the enemy king and the board centre along that
        # axis — i.e. NOT beyond the enemy king toward that edge.
        def king_blocks(e: str) -> bool:
            if e == "rank-bottom":   # driving toward rank 1: king must be above
                return mr < kr
            if e == "rank-top":      # driving toward rank 8: king must be below
                return mr > kr
            if e == "file-a":        # driving toward a-file: king must be right
                return mf < kf
            return mf > kf            # file-h: king must be left
        # Prefer the nearest edge whose drive the king supports; fall back to
        # nearest overall if the king blocks them all (it will reposition).
        ordered = sorted(dists, key=dists.get)
        supported = [e for e in ordered if not king_blocks(e)]
        edge = supported[0] if supported else ordered[0]
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
    pre = ("- **Drill state** (vs bare king): " if opp_bare
           else "- **Drill state** (opponent has no major piece — run the king "
                "down with the ladder): ")
    if len(majors) >= 2:
        out += _ladder_lines(board, own, opp, majors, own_mat, ksq, opp_bare)
        return out

    # ── Single major: K+R AND K+Q share ONE drill. The queen IS a rook for the
    #    purposes of fencing, opposition, and the edge mate — it just also cuts
    #    diagonals (so it confines faster) and is easier to stalemate with.
    #    Verified against Capablanca: both keep the kings within ~3 the whole
    #    mate, fence the king onto fewer lines, and mate in opposition on the
    #    edge. So the queen flows through the same rules below, with "queen"
    #    wording and a stalemate guard up front.
    lone_queen = own_mat[chess.QUEEN] == 1 and own_mat[chess.ROOK] == 0
    piece_noun = "queen" if lone_queen else "rook"

    # Stalemate guard (mechanics: enemy-king legal-move count). The queen
    # controls many squares, so a careless quiet move can leave the lone king
    # with zero moves and no check = draw. Fires before any rule that might
    # suggest such a move.
    _probe = board.copy(stack=False)
    if _probe.turn == own:
        try:
            _probe.push(chess.Move.null())
        except (AssertionError, ValueError):
            pass
    _ek_moves = sum(1 for m in _probe.legal_moves if m.from_square == ksq)
    if lone_queen and _ek_moves <= 1:
        return [
            pre + f"the enemy king has only {_ek_moves} legal move(s) — "
            "STALEMATE DANGER. Do NOT play a quiet queen move that removes its "
            "last square; give check, or march your king. Confirm the move "
            "says `gives checkmate` (never `stalemate`) in imagine_move."
        ]
    # ── Single major (K+R): needs king support, so the rules stay
    #    position-specific but are still applied by the model. Lead with the
    #    box + king-distance fact (pure geometry): K+R is a forced mate but the
    #    agent plays it slowly when it does not bring its king in (game
    #    efbdd8ce, 2026-06-17: 49 plies). The box must shrink AND the king must
    #    close to ~2 squares before the edge check mates.
    # ── The K+R / K+Q method as Capablanca states it, encoded as ONE
    #    deterministic rule (replaces the brittle fence/opposition machine and
    #    the priority-list that both produced shuffles and wrong-way checks —
    #    games 4a211a2a, f923a018, 1403f9cc, 8063c239). The geometry is computed
    #    by `confine_state` (a structural fact, like "is there a back-rank
    #    weakness" — it does NOT name a move); the agent executes the branch
    #    with chess__imagine_move, which reports each candidate's box + whether
    #    the major stays defensible.
    _w, _h, _area = _eval.confinement_box(board, opp)
    _kd = _eval.kings_distance(board)
    on_edge = kf in (0, 7) or kr in (0, 7)

    # 0) A mate this move? (scanning legal moves for checkmate is rules.)
    has_mate_in_1 = any(
        (board.push(mv), board.is_checkmate(), board.pop())[1]
        for mv in list(board.legal_moves)
    )
    if has_mate_in_1:
        out.append(
            pre + f"there is a CHECKMATE available this move — scan "
            f"chess__list_legal_moves for the `checkmate` flag and play it."
        )
        return out

    # Balance vs the squeeze: if an enemy pawn can promote next move, a new
    # piece would break the mating net — flag it as the priority BEFORE the
    # confine guidance (we already returned above if we can mate now). The
    # general passed-pawn radar also warns; putting it inside the drill keeps
    # 'tighten with the rook' from drowning out a queening pawn.
    promo = _promotion_threat_squares(board, opp, own)
    if promo:
        out.append(
            "- **Deal with the promotion threat FIRST.** Enemy pawn(s) on "
            f"{', '.join(chess.square_name(s) for s in promo)} can promote next "
            "move; a new queen wrecks your mating net. Capture it, cover/block "
            "its promotion square, or play a check that also stops it (verify "
            "with imagine_move) — then resume the squeeze below."
        )

    # The single rule: confine tighter with the major on a square the king can
    # defend in time; if the major is already on its tightest defensible
    # confining square, step the king closer instead.
    cs = _eval.confine_state(board, own)
    out.append(
        f"- K+{piece_noun[0].upper()} method: the enemy king is boxed in "
        f"**{_w}x{_h} = {_area} squares**; your kings are **{_kd}** apart. "
        f"Each move, confine the box TIGHTER with the {piece_noun} on a square "
        f"your king can defend IN TIME; when the {piece_noun} is already on its "
        f"tightest defensible square, step the king closer instead. Keep king "
        f"and {piece_noun} together."
    )
    if cs is not None and cs["can_tighten"]:
        out.append(
            pre + f"a tighter {piece_noun} square EXISTS that your king can "
            f"still defend in time — it shrinks the box from {cs['current_area']} "
            f"to {cs['best_area']}. MOVE THE {piece_noun.upper()} there (find it "
            f"with imagine_move: try {piece_noun} moves, pick the one with the "
            f"SMALLEST box whose confinement line says 'protectable in time' and "
            f"is not stalemate). Do NOT move the king, do NOT check for its own "
            f"sake, do NOT loosen the box."
        )
    else:
        out.append(
            pre + f"your {piece_noun} is already on its tightest defensible "
            f"confining square (box {_area}; no tighter defensible square "
            f"exists yet). STEP YOUR KING one square toward the enemy king to "
            f"take more squares and let the {piece_noun} confine tighter next "
            f"move. Do NOT move the {piece_noun}."
        )
    if opp_mat[chess.PAWN] > 0:
        out.append(
            "- **The box/region above counts only piece lines — NOT the enemy "
            "pawn(s).** A pawn can block your "
            f"{piece_noun}'s cut or shield the king, so the real confinement may "
            "differ — verify the actual squares with imagine_move. Simplest plan: "
            f"win or trade off the enemy pawn(s) (use your {piece_noun} and king "
            "to round them up; trade pieces, not pawns) to reduce to a clean "
            f"K+{piece_noun[0].upper()} vs K mate."
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
    # The king has no forward luft if every forward square is occupied by one of
    # its OWN pieces (a pawn is the classic case, but a friendly rook/bishop on
    # f7 boxes the king just the same — m3xxZ) OR is covered by one of our
    # pieces (it can't flee onto a guarded square). Either way the escape is
    # denied; both make a back-rank mate real.
    def _forward_blocked(sq: int) -> bool:
        p = board.piece_at(sq)
        if p is not None and p.color == opp:
            return True                      # own piece boxes the king
        return board.is_attacked_by(own, sq)  # or we cover the flight square
    blocked = all(_forward_blocked(sq) for sq in front_squares)
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


def _own_back_rank_lines(board: chess.Board, own: bool) -> list[str]:
    """Defensive mirror of _back_rank_lines: warn when OUR king is the one
    walled in on its back rank with an enemy major able to reach it. Pure
    geometry (same checks, our side). Strictly gated to avoid noise — fires
    only when the enemy actually has a rook/queen and an open file to use,
    so it stays quiet in normal middlegames. Added after game 9b0d7590,
    where the agent was mated on its own back rank (Kh1 behind g2/h2) having
    never made luft."""
    ksq = board.king(own)
    if ksq is None:
        return []
    back = 0 if own == chess.WHITE else 7
    if chess.square_rank(ksq) != back:
        return []
    forward = 8 if own == chess.WHITE else -8
    f = chess.square_file(ksq)
    front_files = [x for x in (f - 1, f, f + 1) if 0 <= x <= 7]
    front_squares = [chess.square(x, back) + forward for x in front_files]
    walled = all(
        (p := board.piece_at(sq)) is not None and p.color == own and p.piece_type == chess.PAWN
        for sq in front_squares
    )
    if not walled:
        return []  # the king has at least one luft square already
    opp = not own
    enemy_majors = board.pieces(chess.ROOK, opp) | board.pieces(chess.QUEEN, opp)
    if not enemy_majors:
        return []
    pawns = board.pieces(chess.PAWN, chess.WHITE) | board.pieces(chess.PAWN, chess.BLACK)
    open_file = any(
        all(chess.square(x, r) not in pawns for r in range(8)) for x in range(8)
    )
    if not open_file:
        return []
    # Do our own majors defend the back rank? If none do, the threat is real.
    own_defenders = [
        sq for sq in board.pieces(chess.ROOK, own) | board.pieces(chess.QUEEN, own)
        if chess.square_rank(sq) == back
    ]
    defence = (
        f"your rook/queen on {', '.join(chess.square_name(s) for s in own_defenders)} "
        f"guards it for now — keep it there or make luft"
        if own_defenders
        else "NOTHING of yours guards that rank"
    )
    return [
        f"- **Your OWN king is walled on its back rank** behind its pawns, "
        f"and the opponent has a major piece plus an open file to reach it; "
        f"{defence}. Consider making luft (a pawn step) before it becomes a "
        f"mate threat — read `{_PAGE_BACK_RANK}`."
    ]


def _nearest_passer_distance(board: chess.Board, color: bool) -> int | None:
    """Min promotion distance (in pawn pushes) over `color`'s pawns that are passed
    NOW or become passed after ONE legal pawn move (a breakthrough — WRHef: c5 isn't
    the runner, but after c6 bxc6 the b6-pawn is a passer 2 from queening). Returns
    None if no such pawn. Used only to decide whether the agent is in a real pawn
    RACE (so the opponent-promotion warning offers 'race, don't reflexively defend'
    instead of prescribing defence). Heuristic distance, not a proof; the agent
    still calculates the race with imagine_line."""
    def passed_on(b: chess.Board, sq: int, c: bool) -> bool:
        f, r = chess.square_file(sq), chess.square_rank(sq)
        ahead = range(r + 1, 8) if c == chess.WHITE else range(0, r)
        for x in (f - 1, f, f + 1):
            if not 0 <= x <= 7:
                continue
            for rr in ahead:
                p = b.piece_at(chess.square(x, rr))
                if p is not None and p.piece_type == chess.PAWN and p.color != c:
                    return False
        return True

    def dist(sq: int, c: bool) -> int:
        r = chess.square_rank(sq)
        return (7 - r) if c == chess.WHITE else r

    best: int | None = None
    # passed now
    for sq in board.pieces(chess.PAWN, color):
        if passed_on(board, sq, color):
            d = dist(sq, color)
            best = d if best is None else min(best, d)
    # passed after one of the agent's legal pawn moves (push or capture), AND the
    # classic 2-ply BREAKTHROUGH: agent pushes a pawn that the opponent captures,
    # and after that capture an agent pawn is passed (WRHef: c6 bxc6 leaves b6 a
    # passer). We look one opponent pawn-capture deep for this.
    if board.turn == color:
        for mv in board.legal_moves:
            pc = board.piece_at(mv.from_square)
            if pc is None or pc.piece_type != chess.PAWN:
                continue
            b2 = board.copy(stack=False)
            b2.push(mv)
            for sq in b2.pieces(chess.PAWN, color):
                if passed_on(b2, sq, color):
                    d = dist(sq, color) + 1  # +1 tempo to make the breakthrough
                    best = d if best is None else min(best, d)
            # 2-ply breakthrough: opponent pawn-capture in reply, then agent passed
            for rep in b2.legal_moves:
                if not b2.is_capture(rep):
                    continue
                rpc = b2.piece_at(rep.from_square)
                if rpc is None or rpc.piece_type != chess.PAWN:
                    continue
                b3 = b2.copy(stack=False)
                b3.push(rep)
                for sq in b3.pieces(chess.PAWN, color):
                    if passed_on(b3, sq, color):
                        d = dist(sq, color) + 2  # +2 tempi (push + their capture)
                        best = d if best is None else min(best, d)
    return best


def _breakthrough_pushes(board: chess.Board, color: bool) -> list[str]:
    """Pawn PUSH moves by `color` that, after a forced/likely opponent pawn capture,
    leave `color` with a passed pawn (the classic breakthrough sacrifice). Returns
    their SANs. Requires that the push is itself a non-capturing pawn advance the
    opponent CAN capture with a pawn. Mechanics; the agent calculates whether the
    resulting passer actually queens in time."""
    def passed_on(b: chess.Board, sq: int, c: bool) -> bool:
        f, r = chess.square_file(sq), chess.square_rank(sq)
        ahead = range(r + 1, 8) if c == chess.WHITE else range(0, r)
        for x in (f - 1, f, f + 1):
            if not 0 <= x <= 7:
                continue
            for rr in ahead:
                p = b.piece_at(chess.square(x, rr))
                if p is not None and p.piece_type == chess.PAWN and p.color != c:
                    return False
        return True

    if board.turn != color:
        return []
    out: set[str] = set()
    for mv in board.legal_moves:
        pc = board.piece_at(mv.from_square)
        if pc is None or pc.piece_type != chess.PAWN or board.is_capture(mv):
            continue
        b2 = board.copy(stack=False)
        try:
            san = board.san(mv)
        except Exception:
            continue
        b2.push(mv)
        # opponent must have a pawn capture; after it, do we get a passer?
        for rep in b2.legal_moves:
            if not b2.is_capture(rep):
                continue
            rpc = b2.piece_at(rep.from_square)
            if rpc is None or rpc.piece_type != chess.PAWN:
                continue
            b3 = b2.copy(stack=False)
            b3.push(rep)
            if any(passed_on(b3, sq, color) for sq in b3.pieces(chess.PAWN, color)):
                out.add(san)
                break
    return sorted(out)


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

    def safe_pushes(color: bool) -> list[str]:
        """SAN of a passed pawn's single-step advance when the pawn is close
        (≤3 from promotion) and the advance square is safe (empty and not lost to
        SEE) — the concrete 'push the passer' move so the agent acts, not just
        notes the pawn. Only when it's `color`'s turn.

        King-safety guard: do NOT recommend pushing while your OWN king is in
        danger — if you are in check, or if after the push the opponent has a
        CHECK or a material-winning reply, the push ignores a threat and the
        advice is bad (pushing a pawn while getting mated). A human pushes a
        passer when it's quiet, not under fire."""
        if board.turn != color:
            return []
        if board.is_check():
            return []  # deal with the check first; never advise a pawn push in check
        out = []
        for sq in board.pieces(chess.PAWN, color):
            if not passed(sq, color):
                continue
            r = chess.square_rank(sq)
            dist = (7 - r) if color == chess.WHITE else r
            if dist > 3:
                continue
            fwd = sq + 8 if color == chess.WHITE else sq - 8
            if not (0 <= fwd < 64) or board.piece_at(fwd) is not None:
                continue
            mv = chess.Move(sq, fwd)
            # promotion move needs a promotion piece to be legal
            if dist == 1:
                mv = chess.Move(sq, fwd, promotion=chess.QUEEN)
            if mv not in board.legal_moves:
                continue
            after = board.copy(stack=False)
            after.push(mv)
            # advance is unsafe if the pawn/queen is simply lost on the new sq …
            if _eval.static_exchange_eval(after, fwd, not color) >= 150:
                continue
            # … OR if it ignores a real threat: after the push the opponent has a
            # reply that WINS MATERIAL (≥ a minor) by SEE — including a
            # capture-with-check. (A bare check that wins nothing is a harmless
            # spite check and must NOT suppress the push — pWCJd promotes through
            # Rxe3+/Rg2+.) A material-winning reply means pushing was reckless;
            # the agent should deal with the threat, so don't prompt the push.
            danger = False
            for opp_mv in after.legal_moves:
                if after.is_capture(opp_mv):
                    a2 = after.copy(stack=False); a2.push(opp_mv)
                    if _eval.static_exchange_eval(a2, opp_mv.to_square, color) >= 300:
                        danger = True; break
            if danger:
                continue
            try:
                out.append(board.san(mv))
            except Exception:
                pass
        return sorted(set(out))

    mine, theirs = describe(own), describe(not own)
    lines = []
    if mine:
        pushes = safe_pushes(own)
        push_note = (f" **Push it now: {', '.join(pushes)}** (the advance is safe) — a passer "
                     f"that runs is decisive; every tempo counts in a pawn race."
                     if pushes else "")
        lines.append(
            f"- Your passed pawn(s): {', '.join(mine)}. A passed pawn escorted "
            f"by its king promotes — read `{_PAGE_KP}`.{push_note}"
        )
    # BREAKTHROUGH: even with NO current passer, a pawn push the opponent must
    # capture can leave you a passed pawn (WRHef: c6! bxc6 b7→b8=Q). The agent, faced
    # with the opponent's own promotion threat, never spots its own breakthrough.
    # Surface the push move(s) that create a passer as candidates to calculate.
    if not mine and board.turn == own:
        bt = _breakthrough_pushes(board, own)
        if bt:
            lines.append(
                f"- **POSSIBLE BREAKTHROUGH: {', '.join(bt)}.** You have no passed pawn YET, but "
                f"this pawn push forces the enemy to capture and leaves you a passed pawn that runs "
                f"to promotion. In a pawn race a breakthrough (even sacrificing a pawn) can queen "
                f"first or with tempo — calculate it with `imagine_line` before defending."
            )
    if theirs:
        # Categorize opponent pawns by urgency: 2 moves away, 1 move away, or already promoting
        critical = []
        warning = []
        for pawn_desc in theirs:
            if "0 move(s)" in pawn_desc:
                critical.append(pawn_desc)
            elif "1 move(s)" in pawn_desc:
                warning.append(pawn_desc)

        if critical:
            lines.append(
                f"- **CRITICAL: Opponent pawn(s) {', '.join(critical)} promote THIS TURN.** "
                f"You MUST block/capture the promotion square or give check NOW, or they win."
            )
        elif warning:
            # Is the agent ALSO in the race? If it has a passed pawn just as close
            # to promoting (and especially one whose promotion gives check), the
            # right call may be to PUSH OWN PAWN / break through rather than defend
            # — a panic "stop the pawns first" loses won races (WRHef: c6! bxc6 b7
            # queens with the agent's own passer while the agent instead defended
            # the g2-pawn with Kh2). Surface the race instead of prescribing defence.
            own_dist = _nearest_passer_distance(board, own)
            race = own_dist is not None and own_dist <= 3
            if race:
                lines.append(
                    f"- **PAWN RACE: opponent pawn(s) {', '.join(warning)} promote in 1 move — but "
                    f"you have a passed pawn ~{own_dist} move(s) from queening too.** Do NOT reflexively "
                    f"defend: calculate whether PUSHING your own pawn (or a breakthrough pawn sacrifice "
                    f"that clears its path) queens first or WITH CHECK — if so, race, don't defend. Use "
                    f"`imagine_line` to play the race out to both queens. Defend only if your pawn is "
                    f"genuinely slower."
                )
            else:
                lines.append(
                    f"- **WARNING: Opponent pawn(s) {', '.join(warning)} promote in 1 move.** "
                    f"Your next move should deal with this threat (block, capture, check, or queen "
                    f"your own pawn first with check) or you will face a new queen. If you can deliver "
                    f"checkmate in 1, do it. Before defending, check whether a faster counter-promotion "
                    f"or a forcing move wins the race."
                )
        else:
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
    lines += _winning_safety_lines(board, own)
    lines += _mating_material_lines(board, own)
    lines += _drill_state_lines(board, own)
    lines += _king_geometry_lines(board, own)
    lines += _back_rank_lines(board, own)
    lines += _own_back_rank_lines(board, own)
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
