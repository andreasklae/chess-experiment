#!/usr/bin/env python3
"""Imagine a single move from the current position. Shows the resulting board,
the static eval before/after, the attack/defense map for the moved piece on
its new square, deltas (attacks/defenses gained and lost), discovered
attacks, newly hanging own pieces, check/mate status, captures, and the
opponent's legal replies.

Reads CHESS_API_BASE and CHESS_GAME_ID from environment (injected by
AgentPlayer). The live board state is **not** mutated; everything is computed
on a copy.

Argument (one, required):
  move    The move to imagine, in UCI (e2e4, g1f3, e7e8q) or SAN (e4, Nf3,
          O-O, e8=Q). Trailing + or # is ignored.

Exposed as the tool chess__imagine_move after use_skill('chess'). Example:
  chess__imagine_move(move="e2e4")
  chess__imagine_move(move="Nf3")

If the move is illegal, the script exits nonzero with a categorised error
(no piece, blocked, pinned, etc.).

Output is markdown so it renders cleanly in the agent UI.
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

import chess


# Sibling imports — `from _eval import ...` and `from show_position import ...`.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from _eval import (  # noqa: E402
    EVAL_WARNING,
    MATERIAL,
    PIECE_NAMES,
    annotate_move,
    classify_illegal_move,
    color_name,
    confinement_box,
    describe_piece,
    enemy_king_mobility,
    kings_distance,
    lone_king_color,
    parse_move,
    piece_defensible_in_time,
    render_eval_delta_line,
    render_moves_table,
    static_exchange_eval,
)
from _live import board_with_history, fetch_state  # noqa: E402
from show_position import (  # noqa: E402
    compute_attack_chain,
    format_chain,
    render_ascii,
)


def _attacks_and_defenses(board: chess.Board, square: int) -> tuple[set[int], set[int]]:
    """Return (squares_attacking_opponent, squares_defending_own) for the
    piece on `square`. Splits board.attacks() by colour of pieces on
    controlled squares."""
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
    return ", ".join(describe_piece(board, s) for s in sorted(squares))


def _move_summary(board_before: chess.Board, move: chess.Move) -> str:
    """One-line description of the move itself."""
    piece = board_before.piece_at(move.from_square)
    piece_name = PIECE_NAMES[piece.piece_type]
    from_name = chess.square_name(move.from_square)
    to_name = chess.square_name(move.to_square)
    san = board_before.san(move)

    is_ep = board_before.is_en_passant(move)
    is_castle = board_before.is_castling(move)

    if is_castle:
        side = "kingside" if chess.square_file(move.to_square) > chess.square_file(move.from_square) else "queenside"
        return f"`{move.uci()}` ({san}) — {side} castle"

    captured = board_before.piece_at(move.to_square)
    if is_ep:
        ep_sq = chess.square(chess.square_file(move.to_square), chess.square_rank(move.from_square))
        captured = board_before.piece_at(ep_sq)
        value = MATERIAL[chess.PAWN]
        return (
            f"`{move.uci()}` ({san}) — {piece_name} {from_name} → {to_name}, "
            f"en passant captures {color_name(captured.color)} pawn on {chess.square_name(ep_sq)} (+{value}cp)"
        )

    promo_extra = f", promotes to {PIECE_NAMES[move.promotion]}" if move.promotion is not None else ""

    if captured is not None:
        value = MATERIAL[captured.piece_type] if captured.piece_type != chess.KING else 0
        return (
            f"`{move.uci()}` ({san}) — {piece_name} {from_name} → {to_name}, "
            f"captures {color_name(captured.color)} {PIECE_NAMES[captured.piece_type]} (+{value}cp){promo_extra}"
        )

    return f"`{move.uci()}` ({san}) — {piece_name} {from_name} → {to_name} (no capture){promo_extra}"


def _confinement_lines(
    board_before: chess.Board, board_after: chess.Board, move: chess.Move
) -> list[str]:
    """Basic-mate confinement facts for the imagined move, in numbers + words
    (no ASCII art — the model reads the numbers better). Only emitted when one
    side is a lone king and the mover has a queen/rook (the basic-mate case).

    Reports, all pure geometry:
      - the lone king's confinement-box area BEFORE → AFTER this move (the
        cage the major + edges trap it in; smaller = tighter), with the change;
      - the distance between the two kings before → after (the 'march your
        king in' progress signal);
      - if the move places/leaves your major where the lone king could attack
        it, whether your king can defend it in time (the safe-to-confine test).
    """
    defender = lone_king_color(board_before)
    if defender is None:
        return []
    mover = board_before.turn
    if defender == mover:               # the lone king is the side to move; skip
        return []

    area_before = confinement_box(board_before, defender)[2]
    area_after = confinement_box(board_after, defender)[2]
    kd_before = kings_distance(board_before)
    kd_after = kings_distance(board_after)

    def trend(before: int, after: int, good_is_down: bool) -> str:
        if after == before:
            return "no change"
        better = (after < before) if good_is_down else (after > before)
        arrow = "smaller" if after < before else "larger"
        if good_is_down:
            return f"{arrow} ({'good — tighter' if better else 'WORSE — looser'})"
        return arrow

    lines = [
        "## Confinement (basic mate)",
        "",
        "**The whole K+R/K+Q method: each move, confine the enemy king's box "
        "TIGHTER while keeping your major on a square your king can protect in "
        "time. Compare candidates by these two numbers.**",
        "",
        f"- Enemy king's box (squares it is trapped in): "
        f"**{area_before} → {area_after}** — {trend(area_before, area_after, True)}.",
        f"- Distance between the kings: **{kd_before} → {kd_after}** "
        f"(bring it to 2 to support the mate; "
        f"{'closer' if kd_after < kd_before else ('further' if kd_after > kd_before else 'no change')}).",
    ]

    # For ANY major move, report whether the major stays protectable in time —
    # the core K+R/K+Q safety test (your king must be able to reach a defending
    # square before the enemy king reaches one attacking it). This is what makes
    # a confining square usable vs. a square where the king just wins the rook.
    piece = board_after.piece_at(move.to_square)
    if piece is not None and piece.piece_type in (chess.QUEEN, chess.ROOK):
        name = PIECE_NAMES[piece.piece_type]
        sq = chess.square_name(move.to_square)
        ek = board_after.king(defender)
        attacked_now = ek is not None and chess.square_distance(ek, move.to_square) == 1
        attacked_now = attacked_now and not board_after.is_attacked_by(mover, move.to_square)
        safe = piece_defensible_in_time(board_after, move.to_square, mover)
        if attacked_now:
            lines.append(
                f"- ⚠ Your {name} on {sq} is attacked by the enemy king right "
                f"now and not yet defended — it will be lost unless your king "
                f"defends it immediately."
            )
        elif safe is True:
            lines.append(
                f"- Your {name} on {sq}: your king can reach a defending square "
                f"no later than the enemy king can attack it — **protectable in "
                f"time**, a usable confining square."
            )
        elif safe is False:
            lines.append(
                f"- ⚠ Your {name} on {sq}: the enemy king can reach a square "
                f"attacking it BEFORE your king can defend it — **not "
                f"protectable in time**. Confine from a square nearer your own "
                f"king instead (do not flee to a far corner — that loosens the "
                f"box; pick the tightest square your king can still protect)."
            )
    lines.append("")
    return lines


def _check_status(board_after: chess.Board) -> str:
    if board_after.is_checkmate():
        return "gives checkmate"
    if board_after.is_stalemate():
        return "stalemate (no legal reply)"
    if board_after.is_check():
        return f"gives check to {color_name(board_after.turn)} king"
    return "none"


def _discovered_attacks(board_before: chess.Board, board_after: chess.Board, move: chess.Move) -> list[str]:
    """Find pieces (other than the moved piece) of the moving side that now
    attack squares they didn't attack before."""
    mover_color = board_before.turn
    discoveries: list[str] = []
    for sq in chess.SQUARES:
        if sq == move.to_square:
            continue
        piece = board_before.piece_at(sq)
        if piece is None or piece.color != mover_color:
            continue
        if board_after.piece_at(sq) is None or board_after.piece_at(sq).color != mover_color:
            continue
        before_atks = set(board_before.attacks(sq))
        after_atks = set(board_after.attacks(sq))
        gained = after_atks - before_atks
        if not gained:
            continue
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
    """List own pieces (other than the moved piece) that became unsafe as a
    side-effect of this move (was safe before, has attackers ≥ defenders now)."""
    mover_color = board_before.turn
    enemy_color = not mover_color
    new_hanging: list[str] = []
    for sq in chess.SQUARES:
        if sq == move.to_square:
            continue
        piece = board_after.piece_at(sq)
        if piece is None or piece.color != mover_color:
            continue
        before_piece = board_before.piece_at(sq)
        if before_piece is None or before_piece.color != mover_color:
            continue

        attackers_after = list(board_after.attackers(enemy_color, sq))
        if not attackers_after:
            continue
        attackers_before = list(board_before.attackers(enemy_color, sq))
        defenders_before = list(board_before.attackers(mover_color, sq))
        defenders_after = [s for s in board_after.attackers(mover_color, sq) if s != sq]

        was_safe_before = not attackers_before or len(defenders_before) >= len(attackers_before)
        # Unsafe now = either outnumbered (count) OR a losing exchange on the
        # square even when defended by count (value). The value test catches
        # leaving a knight defended only by a pawn — game 9b0d7590 9.Nd2??
        # left the c3 knight to bxc3 bxc3, net -2, which the count test misses.
        see_loss = static_exchange_eval(board_after, sq, enemy_color)
        is_unsafe_now = (
            (not defenders_after or len(attackers_after) > len(defenders_after))
            or see_loss >= 150
        )
        if not (was_safe_before and is_unsafe_now):
            continue
        atk_str = ", ".join(describe_piece(board_after, a) for a in sorted(attackers_after))
        def_str = (", ".join(describe_piece(board_after, d) for d in sorted(defenders_after))
                   if defenders_after else "nothing")
        loss_note = (
            f" — you would lose ~{see_loss // 100} pawn(s) of material in the "
            f"exchange here"
            if see_loss >= 150
            else ""
        )
        new_hanging.append(
            f"{describe_piece(board_after, sq)} — attacked by {atk_str}; "
            f"defended by {def_str}{loss_note}"
        )
    return new_hanging


def _en_passant_offered(board_after: chess.Board) -> str | None:
    """If this move grants the opponent an en-passant capture, describe it."""
    if board_after.ep_square is None:
        return None
    ep_sq = board_after.ep_square
    pawn_squares = [s for s in board_after.pieces(chess.PAWN, board_after.turn)
                    if ep_sq in board_after.attacks(s)]
    if not pawn_squares:
        return None
    capturers = ", ".join(chess.square_name(s) for s in sorted(pawn_squares))
    return f"yes — {color_name(board_after.turn)} pawn on {capturers} may capture en passant on {chess.square_name(ep_sq)}"


def _bad_trade_warning(
    board_before: chess.Board, board_after: chess.Board, move: chess.Move
) -> str | None:
    """Warn when the moved piece sits on a square it will LOSE material on
    after the full capture sequence — even if the square is 'defended' by
    count. Counts say balanced (1 pawn defends vs 1 pawn attacks); values say
    you gave a knight for a pawn. The hanging-warning only catches
    defenders<attackers; this catches the defended-but-losing trade that
    decided both 1000-rated games (16.Ne5?? fxe5 dxe5, 9.Nd2?? bxc3 bxc3)."""
    moved_piece = board_after.piece_at(move.to_square)
    if moved_piece is None or moved_piece.piece_type == chess.KING:
        return None
    enemy = not board_before.turn
    # Net for the opponent if they start capturing on the moved piece's square.
    opp_gain = static_exchange_eval(board_after, move.to_square, enemy)
    # Credit anything THIS move just captured (a capture that gets recaptured
    # is a trade, not a fresh loss).
    my_gain = 0
    if board_before.is_capture(move):
        victim = board_before.piece_at(move.to_square)
        if victim is not None:
            my_gain = MATERIAL.get(victim.piece_type, 0)
        else:  # en passant
            my_gain = MATERIAL[chess.PAWN]
    net_loss = opp_gain - my_gain
    if net_loss < 150:
        return None
    return (
        f"⚠ **Losing exchange on {chess.square_name(move.to_square)}** — if "
        f"the opponent captures here and you recapture, you come out about "
        f"{net_loss} centipawns DOWN (roughly {net_loss // 100} pawn(s) of "
        f"material). The square is defended by count, but you lose material "
        f"in the trade — verify this is a sacrifice you intend."
    )


def _moved_piece_hanging_warning(
    board_after: chess.Board,
    move: chess.Move,
    attacker_chain: list,
    defender_chain: list,
) -> str | None:
    """Return a prominent warning when the moved piece is left undefended on
    its new square (more immediate attackers than immediate defenders).

    Skipped when:
    - The piece is a king (illegal king-into-check is rejected by python-chess
      before we ever get here).
    - The opponent is in check AND none of their legal replies captures the
      moved piece. (If the king itself can take it, the piece is still hanging.)
    - There are no opponent attackers, or defenders >= attackers.
    """
    moved_piece = board_after.piece_at(move.to_square)
    if moved_piece is None or moved_piece.piece_type == chess.KING:
        return None
    attackers = [sq for sq, is_xray in attacker_chain if not is_xray]
    defenders = [sq for sq, is_xray in defender_chain if not is_xray]
    if not attackers or len(defenders) >= len(attackers):
        return None
    # When in check, only warn if at least one legal reply actually captures
    # the hanging piece (e.g. king takes the checking rook).
    if board_after.is_check():
        can_capture = any(
            m.to_square == move.to_square for m in board_after.legal_moves
        )
        if not can_capture:
            return None
    atk_str = ", ".join(describe_piece(board_after, s) for s in attackers)
    def_str = ", ".join(describe_piece(board_after, s) for s in defenders) if defenders else "nothing"
    return (
        f"⚠ **{describe_piece(board_after, move.to_square)} is hanging** — "
        f"attacked by {atk_str}; defended by {def_str}. "
        f"The opponent can capture it immediately."
    )


def render_imagine(
    board_before: chess.Board, move: chess.Move, agent_color: bool | None = None
) -> str:
    """Markdown-formatted one-ply look-ahead report for `move` from `board_before`.
    Caller must have already verified the move is legal.

    The report is MOVER-RELATIVE: "Moved piece status" / "Newly hanging own
    pieces" describe the side that just moved, and "Opponent legal replies" /
    "Enemy king mobility" describe the other side. `chess__imagine_move` always
    imagines the agent's OWN move, so that is unambiguous and it passes
    ``agent_color=None``.

    `chess__imagine_line` can imagine the OPPONENT's move too. When
    ``agent_color`` is given and the mover is the opponent (mover ≠
    agent_color), we keep the single mover-relative rendering but PREPEND an
    orientation banner and relabel the two most invertible headers, so the agent
    is never confused about whose pieces are whose."""
    board_after = board_before.copy()
    board_after.push(move)

    mover_color = board_before.turn
    # Opponent-move framing: only when the caller declared the agent's colour
    # AND the move being shown is the opponent's.
    opp_move = agent_color is not None and mover_color != agent_color
    moved_piece = board_after.piece_at(move.to_square)

    attacker_chain = compute_attack_chain(board_after, not mover_color, move.to_square)
    defender_chain = [
        (s, x) for s, x in compute_attack_chain(board_after, mover_color, move.to_square)
        if s != move.to_square
    ]

    now_attacks, now_defends = _attacks_and_defenses(board_after, move.to_square)
    before_attacks_enemy, before_defends_own = _attacks_and_defenses(board_before, move.from_square)
    no_longer_attacking = before_attacks_enemy - now_attacks
    no_longer_defending = before_defends_own - now_defends
    no_longer_defending.discard(move.from_square)

    discoveries = _discovered_attacks(board_before, board_after, move)
    newly_hanging = _newly_hanging_own_pieces(board_before, board_after, move)
    ep_text = _en_passant_offered(board_after)
    check_text = _check_status(board_after)

    moved_pinned = board_after.is_pinned(mover_color, move.to_square)
    moved_label = (
        f"{chess.square_name(move.to_square)}, {PIECE_NAMES[moved_piece.piece_type]}"
        f"{' (pinned)' if moved_pinned else ''}"
    )

    hanging_warning = _moved_piece_hanging_warning(
        board_after, move, attacker_chain, defender_chain
    )
    # Only show the value-based bad-trade warning when the count-based hanging
    # warning did NOT already fire (the hanging case is the obvious one; the
    # bad-trade case is the subtle defended-but-losing one). Skip if this move
    # gives checkmate (nothing after mate matters).
    bad_trade_warning = None
    if hanging_warning is None and not board_after.is_checkmate():
        bad_trade_warning = _bad_trade_warning(board_before, board_after, move)

    king_before = enemy_king_mobility(board_before)
    king_after = sum(
        1 for m in board_after.legal_moves
        if board_after.piece_at(m.from_square) is not None
        and board_after.piece_at(m.from_square).piece_type == chess.KING
    )
    king_delta = king_after - king_before
    king_sign = "−" if king_delta < 0 else ("+" if king_delta > 0 else "")
    king_mobility_line = (
        f"**Enemy king mobility:** {king_before} → {king_after} "
        f"({king_sign}{abs(king_delta)} squares)"
    )

    out: list[str] = []
    if opp_move:
        you = color_name(agent_color)
        them = color_name(mover_color)
        out.append(
            f"> ⟳ **This is the OPPONENT's ({them}) move** — not yours. Read the "
            f"perspective carefully:\n"
            f"> - 'Moved piece status', 'Side-effects', 'Newly hanging' below are "
            f"about {them.upper()}'s pieces (the opponent's).\n"
            f"> - **'Replies' are YOUR ({you}) options** — what you can play after "
            f"this line.\n"
            f"> - **'Enemy king mobility'** counts YOUR ({you}) king's squares — "
            f"after the opponent's move you want this HIGH (your king free), the "
            f"opposite of when imagining your own move."
        )
        out.append("")
    out.append(f"## Move: {_move_summary(board_before, move)}")
    out.append("")
    out.append(f"**Check:** {check_text}")
    if board_before.move_stack and not board_after.is_checkmate():
        if board_after.can_claim_threefold_repetition():
            out.append(
                "**Draw warning:** this move immediately draws by threefold "
                "repetition. Pick a move that makes progress instead."
            )
        elif board_after.can_claim_fifty_moves():
            out.append(
                "**Draw warning:** this move triggers the 50-move rule "
                "(50 moves without a capture or pawn move) — instant draw."
            )
        elif board_after.is_repetition(2):
            out.append(
                "**Draw warning:** this move recreates a position that has "
                "already occurred — one more repetition is an automatic draw."
            )
    out.append(king_mobility_line)
    out.append("")
    if hanging_warning:
        out.append(hanging_warning)
        out.append("")
    if bad_trade_warning:
        out.append(bad_trade_warning)
        out.append("")
    out.append(f"**{render_eval_delta_line(board_before, board_after)}**")
    out.append(EVAL_WARNING)
    out.append("")
    out.append("```")
    out.append(render_ascii(board_after))
    out.append("```")
    out.append("")
    out.append(f"**FEN:** `{board_after.fen()}`")
    out.append(f"**Side to move:** {color_name(board_after.turn)}")
    out.append("")

    # Basic-mate confinement facts (only fires vs a lone king): how this move
    # changes the enemy king's box and the king-distance, and whether a major
    # placed near the king stays defensible. Numbers + words, no ASCII art.
    out.extend(_confinement_lines(board_before, board_after, move))

    out.append("## Discovered attacks")
    out.append("")
    if discoveries:
        for d in discoveries:
            out.append(f"- {d}")
    else:
        out.append("- (none)")
    out.append("")

    out.append(f"## Moved piece status ({moved_label})")
    out.append("")
    out.append(f"- **attacked by:** "
               f"{format_chain(board_after, not mover_color, attacker_chain) if attacker_chain else '(none)'}")
    out.append(f"- **defended by:** "
               f"{format_chain(board_after, mover_color, defender_chain) if defender_chain else '(none)'}")
    out.append(f"- **now attacks:** {_format_squares_with_pieces(board_after, now_attacks)}")
    out.append(f"- **now defends:** {_format_squares_with_pieces(board_after, now_defends)}")
    out.append("")

    out.append("## Side-effects on other own pieces")
    out.append("")
    out.append(f"- **no longer attacking:** {_format_squares_with_pieces(board_before, no_longer_attacking)}")
    out.append(f"- **no longer defending:** {_format_squares_with_pieces(board_before, no_longer_defending)}")
    out.append("")

    out.append(
        f"## {color_name(mover_color).capitalize()}'s newly hanging pieces (opponent's)"
        if opp_move else "## Newly hanging own pieces"
    )
    out.append("")
    if newly_hanging:
        for h in newly_hanging:
            out.append(f"- {h}")
    else:
        out.append("- (none)")
    out.append("")

    if ep_text:
        out.append(f"**En passant available:** {ep_text}")
        out.append("")

    # Check if opponent can promote a pawn after this move
    opp_can_promote = []
    for sq in board_after.pieces(chess.PAWN, board_after.turn):
        rank = chess.square_rank(sq)
        target_rank = 0 if board_after.turn == chess.WHITE else 7
        if rank == target_rank:
            opp_can_promote.append(chess.square_name(sq))

    if opp_can_promote:
        # Build mitigation strategies
        strategies = [
            "**Protect the promotion square:** Place a piece on it (e.g., rook on c8 protects c7-pawn on c8)",
            "**Block the pawn:** Place a piece directly in front (one rank back) to prevent advance",
            "**Place rook/queen behind:** Put a major piece on the pawn's file, behind it (same file, safe distance)",
            "**Give check:** Force opponent's king to move instead of pushing the pawn",
            "**Deliver checkmate:** If opponent has no safe moves, they cannot promote (already losing)",
        ]
        out.append(
            f"**⚠️ CRITICAL: PAWN PROMOTION THREAT on {', '.join(opp_can_promote)}**\n\n"
            f"Opponent can promote next move — this becomes a NEW QUEEN/ROOK. You likely lose unless:\n"
            f"- (1) This move delivers **checkmate in your opponent's forced replies**, OR\n"
            f"- (2) Opponent has **NO LEGAL MOVES** or **ONLY LOSING MOVES** (all replies lose material/mate)\n\n"
            f"**Ways to stop promotion (pick one if you allow it):**\n"
        )
        for strategy in strategies:
            out.append(f"- {strategy}")
        out.append(
            f"\n**SCAN THE LEGAL REPLIES BELOW:** If opponent has even ONE safe reply (not check, not losing), "
            f"they will play {opp_can_promote[0]}=Q (or =R) and win. Do NOT allow this unless checkmate is forced."
        )
        out.append("")

    out.append(
        f"## Your ({color_name(agent_color)}) replies after this line"
        if opp_move else "## Opponent legal replies"
    )
    out.append("")
    legal = list(board_after.legal_moves)
    if not legal:
        out.append(f"_None — game over ({check_text})._")
    else:
        out.append(f"_{len(legal)} legal replies_:")
        out.append("")
        out.append(render_moves_table(board_after, legal))

    # Nudge: if this move is sharp/forcing/material-changing, one ply is not
    # enough — tell the agent to calculate the LINE before committing. Only in
    # the standalone imagine_move tool (agent_color is None); not when
    # imagine_line itself rendered this frontier. Never on mate (obvious win) or
    # a clean free capture (nothing to recapture).
    if agent_color is None and not board_after.is_checkmate() and not board_after.is_stalemate():
        reasons = []
        if board_before.is_capture(move) and attacker_chain:
            reasons.append("a TRADE (your piece can be recaptured here)")
        if hanging_warning or bad_trade_warning or newly_hanging:
            reasons.append("a SACRIFICE / material giveaway")
        if board_after.is_check():
            reasons.append("a CHECK (a forcing line)")
        if discoveries:
            reasons.append("a DISCOVERED ATTACK")
        if reasons:
            out.append("")
            out.append(
                "**⮕ Calculate before committing.** This move is "
                + ", and ".join(reasons)
                + " — a sharp, forcing, or material-changing move where ONE ply "
                "is not enough. Before `chess__make_move`, play it out with "
                "`chess__imagine_line` (this move, the opponent's best reply, your "
                "follow-up — add one move at a time) and confirm the line works."
            )

    return "\n".join(out)


def render_pass(board: chess.Board) -> str:
    """Hypothetical: the side to move passes. Lists the other side's
    follow-up moves (the standard way to see what a position *threatens*).
    Pure rules mechanics — the agent decides which threats matter."""
    if board.is_check():
        return (
            "_Cannot imagine a pass here: the side to move is in check and "
            "must respond. Imagine the actual checks/replies instead._"
        )
    after = board.copy()
    after.push(chess.Move.null())
    mover = color_name(after.turn)
    out = [
        f"## Hypothetical: {color_name(board.turn)} passes (null move)",
        "",
        f"If {color_name(board.turn)} did nothing, **{mover}** could play "
        f"(scan the Flag column — `checkmate` here means the position "
        f"threatens mate in one):",
        "",
        render_moves_table(after, list(after.legal_moves)),
        "",
        "_A real opponent moves — threats they cannot parry are the "
        "valuable ones. Use this to check what YOUR last imagined move "
        "threatens (pass on its FEN), or what the opponent threatens "
        "against you (pass on the live board)._",
    ]
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--fen",
        default=None,
        help=(
            "Imagine the move on this position instead of the live game — "
            "chain hypotheticals by passing the FEN a previous "
            "chess__imagine_move returned."
        ),
    )
    parser.add_argument("move", nargs="?", default="")
    parser.add_argument("-h", "--help", action="store_true")
    args = parser.parse_args()

    if args.help:
        print(__doc__)
        return

    if not args.move:
        print(json.dumps({
            "ok": False,
            "error": (
                "Missing move argument. Call with the move in UCI or SAN form. "
                "Example: chess__imagine_move(move=\"e2e4\") "
                "or chess__imagine_move(move=\"Nf3\")."
            ),
        }))
        sys.exit(1)

    if args.fen:
        try:
            board = chess.Board(args.fen)
        except ValueError as exc:
            # Hallucinated FEN. Unlike show_position we can't silently fall
            # back to the live board (the move must match the position the
            # agent intended), so return an actionable error: drop fen= and
            # imagine on the live board, or fix the FEN.
            print(json.dumps({
                "ok": False,
                "error": (
                    f"The FEN you passed is not a legal position ({exc}). "
                    f"Do NOT type FENs by hand — they are easy to get wrong. "
                    f"To analyse the CURRENT game, call this tool WITHOUT a "
                    f"fen argument (e.g. chess__imagine_move(move=\"{args.move or 'e2e4'}\")). "
                    f"Only pass fen= with a string a previous tool returned."
                ),
            }))
            sys.exit(1)
    else:
        data = fetch_state()
        # Board carries the move stack when possible so the report can flag
        # repetition/50-move draws.
        board = board_with_history(data)

    # "pass": the null move — see what the side to move could do NEXT if
    # the opponent did nothing. The agent composes threat detection from
    # this primitive: imagine a candidate, then imagine "pass" on the
    # resulting FEN and read its own follow-ups (checkmate flags included).
    if args.move.strip().lower() in ("pass", "null", "--"):
        print(render_pass(board))
        return

    try:
        move = parse_move(board, args.move)
    except ValueError:
        cleaned = args.move.strip().rstrip("+#")
        legal = [board.san(m) for m in board.legal_moves]
        print(json.dumps({
            "ok": False,
            "error": (
                f"'{args.move}' is not a legal move in the CURRENT position "
                f"({classify_illegal_move(board, cleaned)}). Do not retry the "
                f"same string — pick a move from legal_moves below."
            ),
            "legal_moves": legal[:90],
        }))
        sys.exit(1)
    if move not in board.legal_moves:
        cleaned = args.move.strip().rstrip("+#")
        print(json.dumps({
            "ok": False,
            "error": f"Illegal move '{args.move}': {classify_illegal_move(board, cleaned)}",
        }))
        sys.exit(1)

    print(render_imagine(board, move))


if __name__ == "__main__":
    main()
