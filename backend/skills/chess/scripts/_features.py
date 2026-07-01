"""Positional, tactical, and fundamentals feature detection for the chess agent.

Companion to `_radar.py` (which is mate/endgame focused). This module scans a
board and emits **strengths, weaknesses, and potentials** for BOTH colours, each
with a concrete handling suggestion (legal moves the agent can consider) and a
pointer to the wiki page that explains it. The agent still decides — these are
suggestions, not commands; it is free to deviate and to read further.

Design contract (mirrors what the wiki teaches):
- **Both sides, never confused.** Every finding is tagged YOURS (the side to
  move) or OPPONENT. The agent reads "YOUR rook is on an open file" vs "OPPONENT
  has a knight that can fork your K+Q" and never mixes them up.
- **Current AND potential.** "Your rook is on the open d-file" (current strength)
  AND "the d-file is open — consider Rd1" (potential). Same for every feature.
- **Actionable.** A finding that calls for action lists the concrete legal moves
  that serve it ("defend it: d4; move to safety: Bb6, Be7; counter: Qd5+"), then
  tells the agent to calculate them with imagine_move / imagine_line.
- **Fair.** Pure mechanical geometry/structure detection + legal-move listing.
  No evaluation of which move is best; the agent calculates and chooses.

Used by both `show_position` (current board) and `imagine_move` / `imagine_line`
(resulting board). All output is markdown bullet lines.
"""
from __future__ import annotations

import chess
from dataclasses import dataclass, field

# Wiki page pointers (relative paths the agent passes to read_reference).
WIKI = {
    "pawn_weaknesses": "positional/pawn-weaknesses.md",
    "pawn_strengths": "positional/pawn-strengths.md",
    "piece_activity": "positional/piece-activity.md",
    "king_safety": "positional/king-safety.md",
    "prophylaxis": "positional/prophylaxis-and-blockade.md",
    "evaluate": "positional/evaluate-position.md",
    "forks": "tactics/forks-and-double-attacks.md",
    "pins": "tactics/pins-and-skewers.md",
    "discovered": "tactics/discovered-attacks.md",
    "removing": "tactics/removing-the-defender.md",
    "traps": "tactics/traps.md",
    "handle_threat": "strategy/handle-a-threat.md",
    "material": "principles/material-and-trading.md",
    "center": "principles/center-control.md",
    "opening_principles": "principles/opening-principles.md",
    "fund_opening": "fundamentals/opening.md",
    "fund_middlegame": "fundamentals/middlegame.md",
    "fund_endgame": "fundamentals/endgame.md",
    "checklist": "fundamentals/every-move-checklist.md",
}

PIECE_NAME = {chess.PAWN: "pawn", chess.KNIGHT: "knight", chess.BISHOP: "bishop",
              chess.ROOK: "rook", chess.QUEEN: "queen", chess.KING: "king"}
PIECE_VALUE = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
               chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}


@dataclass
class Finding:
    """One detected feature.

    side:    True  -> belongs to the side to move ("YOURS")
             False -> belongs to the opponent ("OPPONENT")
    kind:    'strength' | 'weakness' | 'potential' | 'threat' | 'fundamental'
    text:    the mechanical fact, written from the tagged side's perspective.
    moves:   optional list of concrete SAN suggestions ("Bb6", "d4") to consider.
    wiki:    optional wiki page key (see WIKI) for further reading.
    """
    side: bool
    kind: str
    text: str
    moves: list[str] = field(default_factory=list)
    wiki: str | None = None


def _sq(s: int) -> str:
    return chess.square_name(s)


def _color_word(c: bool) -> str:
    return "White" if c == chess.WHITE else "Black"


# ---- shared geometry helpers (pure mechanics) ----

def _move_san(board: chess.Board, from_sq: int, to_sq: int) -> list[str]:
    """[SAN] of the from→to move if it is legal for the side to move, else [].
    Used to attach the concrete move to a 'could move to X' finding so the agent
    gets the move, not just the square."""
    mv = chess.Move(from_sq, to_sq)
    if mv in board.legal_moves:
        try:
            return [board.san(mv)]
        except Exception:
            return []
    return []


def _legal_sans_for_piece(board: chess.Board, from_sq: int) -> list[str]:
    """SAN of every legal move by the piece on `from_sq` (for the side to move)."""
    out = []
    for m in board.legal_moves:
        if m.from_square == from_sq:
            try:
                out.append(board.san(m))
            except Exception:
                pass
    return out


def _moves_to_square(board: chess.Board, to_sq: int) -> list[str]:
    """SAN of every legal move that lands a (non-pawn-capture) piece on to_sq."""
    out = []
    for m in board.legal_moves:
        if m.to_square == to_sq:
            try:
                out.append(board.san(m))
            except Exception:
                pass
    return out


def _defenders(board: chess.Board, sq: int, color: bool) -> list[int]:
    return [s for s in board.attackers(color, sq) if s != sq]


def _is_hanging(board: chess.Board, sq: int) -> bool:
    p = board.piece_at(sq)
    if not p:
        return False
    attackers = board.attackers(not p.color, sq)
    if not attackers:
        return False
    defenders = board.attackers(p.color, sq)
    return len(defenders) == 0


# ============================================================================
# PAWN STRUCTURE  (positional/pawn-weaknesses, positional/pawn-strengths)
# ============================================================================

def _pawn_files(board: chess.Board, color: bool) -> dict[int, list[int]]:
    """file_index -> sorted list of pawn squares of `color` on that file."""
    out: dict[int, list[int]] = {}
    for sq in board.pieces(chess.PAWN, color):
        out.setdefault(chess.square_file(sq), []).append(sq)
    return out


def _is_passed(board: chess.Board, sq: int, color: bool) -> bool:
    f, r = chess.square_file(sq), chess.square_rank(sq)
    enemy = not color
    direction = 1 if color == chess.WHITE else -1
    # A pawn behind a friendly pawn on the SAME file (rear of a doubled pair) is
    # not meaningfully passed — the front pawn blocks its own path.
    for own in board.pieces(chess.PAWN, color):
        if own != sq and chess.square_file(own) == f and \
           (chess.square_rank(own) - r) * direction > 0:
            return False
    for ef in (f - 1, f, f + 1):
        if not 0 <= ef < 8:
            continue
        for esq in board.pieces(chess.PAWN, enemy):
            if chess.square_file(esq) != ef:
                continue
            er = chess.square_rank(esq)
            # enemy pawn ahead of ours blocks passing
            if (er - r) * direction > 0:
                return False
    return True


def _is_isolated(board: chess.Board, sq: int, color: bool) -> bool:
    f = chess.square_file(sq)
    own_files = {chess.square_file(s) for s in board.pieces(chess.PAWN, color)}
    return (f - 1) not in own_files and (f + 1) not in own_files


def _is_backward(board: chess.Board, sq: int, color: bool) -> bool:
    """Backward: no friendly pawn on adjacent files is level-or-behind to support
    its advance, and the square in front is controlled by an enemy pawn."""
    f, r = chess.square_file(sq), chess.square_rank(sq)
    direction = 1 if color == chess.WHITE else -1
    adj_support = False
    for af in (f - 1, f + 1):
        if not 0 <= af < 8:
            continue
        for s in board.pieces(chess.PAWN, color):
            if chess.square_file(s) == af:
                # support if it's level or behind (can advance to defend the front sq)
                if (chess.square_rank(s) - r) * direction <= 0:
                    adj_support = True
    if adj_support:
        return False
    front = chess.square(f, r + direction)
    if not 0 <= r + direction < 8:
        return False
    return bool(board.attackers(not color, front) &
                board.pieces(chess.PAWN, not color))


def detect_pawn_structure(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Doubled, isolated, backward, passed pawns + open/half-open files, both
    sides. side=True == side to move."""
    findings: list[Finding] = []
    stm = board.turn if perspective is None else perspective
    for color in (chess.WHITE, chess.BLACK):
        mine = (color == stm)
        files = _pawn_files(board, color)
        doubled_files = {f for f, sqs in files.items() if len(sqs) >= 2}
        # --- doubled ---
        for f, sqs in files.items():
            if len(sqs) >= 2:
                fl = chr(ord('a') + f)
                if mine:
                    findings.append(Finding(True, "weakness",
                        f"you have doubled pawns on the {fl}-file ({', '.join(_sq(s) for s in sqs)}) — "
                        f"they can't defend each other; the {fl}-file is a target",
                        wiki="pawn_weaknesses"))
                else:
                    findings.append(Finding(False, "weakness",
                        f"opponent has doubled pawns on the {fl}-file — a target you can attack "
                        f"(use the {fl}-file / pile pieces on them)",
                        wiki="pawn_weaknesses"))
        # --- isolated / backward / passed (per pawn) ---
        for sq in board.pieces(chess.PAWN, color):
            f = chess.square_file(sq)
            # A doubled pawn is already reported via its file; don't also tag it
            # isolated/backward (noise). Passed still matters (rare but real).
            skip_weakness = f in doubled_files
            if _is_passed(board, sq, color):
                if mine:
                    findings.append(Finding(True, "strength",
                        f"you have a PASSED pawn on {_sq(sq)} — push it, support it from behind with a rook; "
                        f"it grows stronger as it advances",
                        moves=_legal_sans_for_piece(board, sq) if mine else [],
                        wiki="pawn_strengths"))
                else:
                    findings.append(Finding(False, "threat",
                        f"opponent has a PASSED pawn on {_sq(sq)} — blockade the square in front (a knight is ideal), "
                        f"or get a rook behind it",
                        wiki="pawn_strengths"))
            if skip_weakness:
                continue
            if _is_isolated(board, sq, color):
                if mine:
                    findings.append(Finding(True, "weakness",
                        f"your pawn on {_sq(sq)} is ISOLATED (no friendly pawn on adjacent files) — "
                        f"a fixed target; support it with pieces and seek activity",
                        wiki="pawn_weaknesses"))
                else:
                    findings.append(Finding(False, "weakness",
                        f"opponent's pawn on {_sq(sq)} is ISOLATED — blockade the square in front, then attack it",
                        wiki="pawn_weaknesses"))
            elif _is_backward(board, sq, color):
                if mine:
                    findings.append(Finding(True, "weakness",
                        f"your pawn on {_sq(sq)} is BACKWARD (can't be supported by a pawn, advance square held) — "
                        f"defend it with pieces or seek a freeing break",
                        wiki="pawn_weaknesses"))
                else:
                    findings.append(Finding(False, "weakness",
                        f"opponent's pawn on {_sq(sq)} is BACKWARD — control its advance square and pile up on it",
                        wiki="pawn_weaknesses"))
    return findings


def detect_files(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Open and half-open files + the potential to use them with a rook."""
    findings: list[Finding] = []
    stm = board.turn if perspective is None else perspective
    white_pf = _pawn_files(board, chess.WHITE)
    black_pf = _pawn_files(board, chess.BLACK)
    for f in range(8):
        fl = chr(ord('a') + f)
        w_has = f in white_pf
        b_has = f in black_pf
        if w_has and b_has:
            continue  # not open in any sense
        for color in (chess.WHITE, chess.BLACK):
            mine = (color == stm)
            own_has = w_has if color == chess.WHITE else b_has
            enemy_has = b_has if color == chess.WHITE else w_has
            if own_has:
                continue  # file isn't open/half-open for this colour's rooks
            kind_txt = "OPEN" if not enemy_has else "half-open"
            # rook already on the file? (current strength) vs potential
            rooks_on = [s for s in board.pieces(chess.ROOK, color)
                        if chess.square_file(s) == f]
            if rooks_on:
                if mine:
                    findings.append(Finding(True, "strength",
                        f"your rook on {_sq(rooks_on[0])} controls the {kind_txt.lower()} {fl}-file",
                        wiki="piece_activity"))
            else:
                # potential: can a rook move to this file?
                target = None
                moves = []
                if mine:
                    for s in board.pieces(chess.ROOK, color):
                        ms = [m for m in _legal_sans_for_piece(board, s)
                              if m and len(m) >= 2]
                        for mv in ms:
                            # crude: SAN landing file == fl
                            dest = mv.replace("+", "").replace("#", "")[-2:]
                            if dest[:1] == fl:
                                moves.append(mv)
                    if moves:
                        findings.append(Finding(True, "potential",
                            f"the {fl}-file is {kind_txt.lower()} — consider putting a rook there",
                            moves=sorted(set(moves)), wiki="piece_activity"))
    return findings


# ============================================================================
# PIECE ACTIVITY & DEVELOPMENT  (positional/piece-activity, principles/opening)
# ============================================================================

_HOME = {
    chess.WHITE: {chess.B1: "knight", chess.G1: "knight", chess.C1: "bishop",
                  chess.F1: "bishop"},
    chess.BLACK: {chess.B8: "knight", chess.G8: "knight", chess.C8: "bishop",
                  chess.F8: "bishop"},
}


def _phase_is_opening(board: chess.Board) -> bool:
    return board.fullmove_number <= 12


def _tactical_sacrifice_squares(board: chess.Board, stm: bool) -> set[int]:
    """Squares where a capture by `stm` removes the SOLE defender of an attacked
    enemy piece (≥ minor) — i.e. a removing-the-defender sacrifice, not a bait.
    Same single-defender logic as detect_removable_defender; factored out so the
    trap detector can exclude these squares. Mechanics only."""
    enemy = not stm
    out: set[int] = set()
    for tsq in chess.SQUARES:
        ep = board.piece_at(tsq)
        if not ep or ep.color != enemy or ep.piece_type in (chess.KING, chess.PAWN):
            continue
        if not board.attackers(stm, tsq):
            continue
        defenders = [d for d in board.attackers(enemy, tsq) if d != tsq]
        if len(defenders) != 1:
            continue
        guard = defenders[0]
        gp = board.piece_at(guard)
        if gp is None or gp.piece_type == chess.KING:
            continue
        # is the guard capturable by stm? if so its square is a tactical sac square
        if board.attackers(stm, guard):
            out.add(guard)
    return out


def detect_traps(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Trap / bait detection (only meaningful for the side to move): a capture
    that LOOKS free — grabbing an enemy piece or pawn — but actually LOSES
    material by static exchange. This is the mechanical heart of most opening
    traps and the agent's documented weakness (grabbing material that's lost
    right back). Pure SEE mechanics; the agent still decides.

    Only runs from the side-to-move's seat (it reasons about *the agent's own*
    tempting captures). Lists the baited capture(s) so the agent can see them
    flagged BEFORE playing one.
    """
    try:
        from _eval import static_exchange_eval
    except Exception:
        return []
    stm = board.turn if perspective is None else perspective
    if board.turn != stm:
        return []  # we only assess the side actually on move
    findings: list[Finding] = []
    baited: list[str] = []
    # A material-losing capture is only a "trap" if it's a NAIVE greedy grab. A
    # capture that GIVES CHECK, or that REMOVES THE SOLE DEFENDER of an attacked
    # enemy piece, is a deliberate tactical sacrifice — the win comes a move later
    # (Qxd8 removes the e7-knight's guard; Bxh7+ is a discovered-attack check).
    # Flagging those as "traps" steers the agent AWAY from the solution (7e5N5,
    # VhRSK). Compute the squares of such tactical captures and exclude them; they
    # are surfaced by the removing-the-defender / discovered-attack detectors with
    # the right "calculate the whole line" framing instead.
    tactical_to_squares = _tactical_sacrifice_squares(board, stm)
    for mv in board.legal_moves:
        victim = board.piece_at(mv.to_square)
        if victim is None or victim.piece_type == chess.KING:
            continue  # not a capture (en-passant handled below is rare; skip)
        after = board.copy(); after.push(mv)
        if after.is_check():
            continue  # a checking capture is forcing — judge it by the line, not SEE
        if mv.to_square in tactical_to_squares:
            continue  # removes a sole defender — a sacrifice, not a bait
        # SEE from the opponent's side on the landing square: how much they win back.
        see_loss = static_exchange_eval(after, mv.to_square, not stm)
        if see_loss >= 150:  # capturing here loses ~1.5+ pawns net → bait
            try:
                san = board.san(mv)
            except Exception:
                continue
            baited.append(f"{san} (looks like it wins the {PIECE_NAME[victim.piece_type]}, "
                          f"but loses ~{see_loss // 100} pawn(s) after recapture)")
    if baited:
        findings.append(Finding(True, "threat",
            "TRAP / bait — a 'free' capture that actually loses material; verify with "
            "imagine_move before grabbing material: " + "; ".join(baited[:4]),
            wiki="traps"))
    return findings


def detect_development(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Undeveloped minor pieces + castling status (opening-relevant)."""
    findings: list[Finding] = []
    if not _phase_is_opening(board):
        return findings
    stm = board.turn if perspective is None else perspective
    for color in (chess.WHITE, chess.BLACK):
        mine = (color == stm)
        undeveloped = [sq for sq, name in _HOME[color].items()
                       if board.piece_at(sq) and
                       board.piece_at(sq).piece_type ==
                       (chess.KNIGHT if name == "knight" else chess.BISHOP) and
                       board.piece_at(sq).color == color]
        if undeveloped:
            names = ", ".join(f"{PIECE_NAME[board.piece_at(s).piece_type]} on {_sq(s)}"
                              for s in undeveloped)
            if mine:
                moves = []
                for s in undeveloped:
                    moves += _legal_sans_for_piece(board, s)
                findings.append(Finding(True, "fundamental",
                    f"you still have undeveloped pieces ({names}) — develop them toward the centre "
                    f"(knights before bishops)",
                    moves=sorted(set(moves))[:8], wiki="fund_opening"))
        # castling status
        if board.king(color) is not None:
            castled = (color == chess.WHITE and board.king(color) in (chess.G1, chess.C1)) or \
                      (color == chess.BLACK and board.king(color) in (chess.G8, chess.C8))
            can_castle = board.has_castling_rights(color)
            if not castled and can_castle and mine:
                cmoves = [m for m in (_legal_sans_for_piece(board, board.king(color)))
                          if m in ("O-O", "O-O-O")]
                findings.append(Finding(True, "fundamental",
                    "you have NOT castled yet — get your king safe",
                    moves=cmoves, wiki="king_safety"))
    return findings


def detect_bishop_pair(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    findings: list[Finding] = []
    stm = board.turn if perspective is None else perspective
    for color in (chess.WHITE, chess.BLACK):
        mine = (color == stm)
        nb = len(board.pieces(chess.BISHOP, color))
        enemy_b = len(board.pieces(chess.BISHOP, not color))
        if nb >= 2 and enemy_b < 2:
            if mine:
                findings.append(Finding(True, "strength",
                    "you have the bishop pair — open the position (open lines/diagonals) to maximise them",
                    wiki="piece_activity"))
            else:
                findings.append(Finding(False, "weakness",
                    "opponent has the bishop pair — keep the position closed, seek a knight outpost",
                    wiki="piece_activity"))
    return findings


def detect_outposts(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """A square in enemy territory (rank 4-6 for White, 3-5 for Black) that no
    enemy pawn can attack, where you have a knight (current) or could land one
    (potential)."""
    findings: list[Finding] = []
    stm = board.turn if perspective is None else perspective
    for color in (chess.WHITE, chess.BLACK):
        mine = (color == stm)
        if not mine:
            continue  # outpost opportunities are most actionable for the mover
        enemy = not color
        good_ranks = range(3, 6) if color == chess.WHITE else range(2, 5)
        knight_sqs = board.pieces(chess.KNIGHT, color)
        for f in range(8):
            for r in good_ranks:
                sq = chess.square(f, r)
                # no enemy pawn can ever attack this square?
                attackable = False
                for ef in (f - 1, f + 1):
                    if not 0 <= ef < 8:
                        continue
                    for ep in board.pieces(chess.PAWN, enemy):
                        if chess.square_file(ep) == ef:
                            er = chess.square_rank(ep)
                            # enemy pawn still behind/level can advance to attack
                            if (er - r) * (1 if enemy == chess.WHITE else -1) <= 0:
                                attackable = True
                if attackable:
                    continue
                # defended by a friendly pawn = a real outpost
                if not (board.attackers(color, sq) & board.pieces(chess.PAWN, color)):
                    continue
                kn_here = sq in knight_sqs
                if kn_here:
                    findings.append(Finding(True, "strength",
                        f"your knight on {_sq(sq)} sits on a strong outpost (no enemy pawn can kick it)",
                        wiki="piece_activity"))
                else:
                    mvs = [m for s in knight_sqs for m in _legal_sans_for_piece(board, s)
                           if m.replace("+", "").replace("#", "")[-2:] == _sq(sq)]
                    if mvs:
                        findings.append(Finding(True, "potential",
                            f"{_sq(sq)} is an outpost (no enemy pawn can attack it) — consider a knight there",
                            moves=sorted(set(mvs)), wiki="piece_activity"))
    return findings


# ============================================================================
# TACTICAL GEOMETRY  (tactics/forks, tactics/pins-and-skewers, tactics/discovered)
# ============================================================================

def _knight_targets_from(sq: int) -> list[int]:
    return list(chess.SquareSet(chess.BB_KNIGHT_ATTACKS[sq]))


def detect_knight_forks(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Knight forks — current (a knight already forks two valuable pieces) and
    potential (a square a knight could reach that would fork them). Both sides.
    Prioritises royal forks (K + Q/R)."""
    findings: list[Finding] = []
    stm = board.turn if perspective is None else perspective
    for color in (chess.WHITE, chess.BLACK):
        mine = (color == stm)
        enemy = not color
        # valuable enemy targets: K, Q, R (and any two minors)
        targets = {s: board.piece_at(s).piece_type
                   for s in chess.SQUARES
                   if board.piece_at(s) and board.piece_at(s).color == enemy
                   and board.piece_at(s).piece_type in
                   (chess.KING, chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)}
        # candidate knight landing squares: where a knight of `color` sits or can go
        knight_sqs = list(board.pieces(chess.KNIGHT, color))
        # current forks: from each knight's current square
        for ksq in knight_sqs:
            hit = [t for t in _knight_targets_from(ksq) if t in targets]
            valuable = [t for t in hit if targets[t] in (chess.KING, chess.QUEEN, chess.ROOK)]
            if len(hit) >= 2 and valuable:
                desc = ", ".join(f"{PIECE_NAME[targets[t]]} on {_sq(t)}" for t in hit)
                if mine:
                    findings.append(Finding(True, "strength",
                        f"your knight on {_sq(ksq)} already forks {desc} — they can only save one, "
                        f"so the other should fall (unless the fork is met by a check/bigger threat)",
                        wiki="forks"))
        # potential forks: empty/safe squares a knight could jump to that fork two targets
        landing_squares = set()
        for ksq in knight_sqs:
            for d in _knight_targets_from(ksq):
                landing_squares.add(d)
        for land in landing_squares:
            occupant = board.piece_at(land)
            if occupant and occupant.color == color:
                continue  # own piece there
            hit = [t for t in _knight_targets_from(land) if t in targets]
            valuable = [t for t in hit if targets[t] in (chess.KING, chess.QUEEN, chess.ROOK)]
            kinds = [targets[t] for t in hit]
            # Flag a potential fork only when it actually WINS material:
            #  - two pieces each worth a rook or more (K+Q, K+R, Q+R, R+R), OR
            #  - the KING or a QUEEN (a piece that MUST flee the fork) alongside another
            #    target the knight can then PROFITABLY take — i.e. that other target is
            #    UNDEFENDED, or is worth more than the knight and its capture nets
            #    material by SEE. (A king/queen fork forces the major to move; whatever
            #    else is hanging then falls. A K/Q + a *defended equal minor* wins
            #    nothing, so it stays suppressed to avoid noise.)
            heavy = [k for k in kinds if k in (chess.QUEEN, chess.ROOK)]
            forcing = chess.KING in kinds or chess.QUEEN in kinds  # a piece that must flee
            fleeing_types = {chess.KING, chess.QUEEN}
            other_targets = [t for t in hit if targets[t] not in fleeing_types
                             or (targets[t] == chess.QUEEN and len(hit) > 1)]
            # a takeable "other" target: undefended, OR a rook/queen (worth more than N)
            takeable = any(
                t for t in hit
                if targets[t] not in ({chess.KING} if chess.KING in kinds else set())
                and (not board.attackers(enemy, t)              # hanging
                     or targets[t] in (chess.ROOK, chess.QUEEN))  # worth > knight
            )
            fork_wins = (len(heavy) >= 2) or (forcing and takeable) \
                or (chess.KING in kinds and len(heavy) >= 1)
            worth_it = fork_wins
            if len(hit) >= 2 and len(valuable) >= 1 and worth_it:
                desc = ", ".join(f"{PIECE_NAME[targets[t]]} on {_sq(t)}" for t in hit)
                # is the landing square safe-ish (not defended by a pawn)?
                guarded = bool(board.attackers(enemy, land))
                if mine:
                    mvs = [m for ksq in knight_sqs for m in _legal_sans_for_piece(board, ksq)
                           if m.replace("+", "").replace("#", "")[-2:] == _sq(land)]
                    if mvs:
                        note = " (landing square is defended — check it's worth it)" if guarded else ""
                        findings.append(Finding(True, "potential",
                            f"a knight on {_sq(land)} would FORK {desc}{note}",
                            moves=sorted(set(mvs)), wiki="forks"))
                else:
                    findings.append(Finding(False, "threat",
                        f"opponent's knight could land on {_sq(land)} and FORK your {desc} — "
                        f"defend {_sq(land)}, move a target, or watch that square",
                        wiki="forks"))
    return findings


def detect_piece_forks(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Forks/double-attacks by a QUEEN, ROOK, BISHOP or PAWN (knight forks are
    handled by detect_knight_forks). A piece that can move to a square from which
    it attacks TWO valuable enemy pieces, at least one a winning target (worth
    more than the mover, or undefended, or the king). Both sides — your own as an
    opportunity, the opponent's as a WARNING (the symmetric defensive signal).
    Only flagged when the landing square is safe (the forker isn't simply lost).
    Pure geometry + SEE; the agent still calculates and decides."""
    from _eval import static_exchange_eval
    findings: list[Finding] = []
    stm = board.turn if perspective is None else perspective
    for color in (chess.WHITE, chess.BLACK):
        mine = (color == stm)
        enemy = not color
        forkers = [(s, board.piece_at(s).piece_type) for s in chess.SQUARES
                   if board.piece_at(s) and board.piece_at(s).color == color
                   and board.piece_at(s).piece_type in
                   (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.PAWN)]
        seen = set()  # (from, to) we've already reported
        for from_sq, pt in forkers:
            # candidate destination squares: where this piece could move. We test
            # on a board with `color` to move so move generation is correct; if it
            # is not color's turn, give it the move via a null (the threat applies
            # next move).
            b = board
            if board.turn != color:
                b = board.copy()
                try:
                    b.push(chess.Move.null())
                except Exception:
                    continue
            for mv in b.legal_moves:
                if mv.from_square != from_sq:
                    continue
                land = mv.to_square
                if (from_sq, land) in seen:
                    continue
                after = b.copy(); after.push(mv)
                # the moved piece must be safe on its new square (not just lost)
                if static_exchange_eval(after, land, enemy) >= 150:
                    continue
                # what valuable enemy pieces does it now attack?
                mover_val = PIECE_VALUE[pt]
                attacked = []  # (sq, piece_type) of all attacked non-pawn enemy pieces
                for tsq in after.attacks(land):
                    ep = after.piece_at(tsq)
                    if not ep or ep.color != enemy or ep.piece_type == chess.PAWN:
                        continue
                    attacked.append((tsq, ep.piece_type))
                # ROYAL fork: if the KING is one of the targets, the move is a
                # CHECK — the opponent must answer it, so any OTHER attacked piece
                # falls even if defended (they can't both move the king and save
                # it). Otherwise a target only counts when it is genuinely
                # winnable (worth more than the mover, or undefended).
                king_hit = any(pt2 == chess.KING for _, pt2 in attacked)
                hit = []
                for tsq, pt2 in attacked:
                    if pt2 == chess.KING:
                        hit.append((tsq, pt2))
                    elif king_hit:
                        hit.append((tsq, pt2))   # royal fork — defended or not
                    elif PIECE_VALUE[pt2] > mover_val or not after.attackers(enemy, tsq):
                        hit.append((tsq, pt2))
                if len(hit) < 2:
                    continue
                seen.add((from_sq, land))
                desc = ", ".join(f"{PIECE_NAME[t]} on {_sq(s)}" for s, t in hit)
                if mine:
                    try:
                        san = board.san(mv) if board.turn == color else b.san(mv)
                    except Exception:
                        san = None
                    findings.append(Finding(True, "potential",
                        f"your {PIECE_NAME[pt]} could move to {_sq(land)} to FORK {desc} — a double "
                        f"attack; they can only save one. Calculate it (and check the forking piece "
                        f"is safe there).",
                        moves=[san] if san else [], wiki="forks"))
                else:
                    findings.append(Finding(False, "threat",
                        f"opponent's {PIECE_NAME[pt]} could move to {_sq(land)} and FORK your {desc} — "
                        f"a double attack you would not meet in one move; prevent it (guard {_sq(land)}, "
                        f"move a target, or defend both).",
                        wiki="forks"))
    return findings


def detect_loose_pieces(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Undefended pieces ('loose pieces drop off') — both sides. Own loose pieces
    are a weakness; enemy loose pieces are targets."""
    findings: list[Finding] = []
    stm = board.turn if perspective is None else perspective
    for color in (chess.WHITE, chess.BLACK):
        mine = (color == stm)
        for sq in chess.SQUARES:
            p = board.piece_at(sq)
            if not p or p.color != color or p.piece_type in (chess.KING, chess.PAWN):
                continue
            defenders = board.attackers(color, sq)
            attackers = board.attackers(not color, sq)
            if not defenders and attackers:
                # actively attacked + undefended = hanging (a threat now)
                if mine:
                    # Symmetric mirror of the enemy "★ WIN MATERIAL": YOUR piece is
                    # the free one. Top-priority "⛔ LOSING MATERIAL" so a hanging
                    # piece is as loud as a free enemy piece — the #1 defensive fact.
                    findings.append(Finding(True, "lose",
                        f"your {PIECE_NAME[p.piece_type]} on {_sq(sq)} is attacked and UNDEFENDED — the "
                        f"opponent can take it for free. SAVE IT: move it to safety, defend it, or answer "
                        f"with a bigger threat (a check or a capture of equal/greater value).",
                        moves=_handle_attacked_piece_moves(board, sq, color),
                        wiki="handle_threat"))
                else:
                    # You attack an UNDEFENDED enemy piece: a free piece on the
                    # board right now. This is the single highest-value fact in
                    # most positions, so it is a top-priority "win" imperative
                    # (rendered first, in YOUR block), NOT a low "potential". The
                    # only caveat is a trap — taking it loses more elsewhere —
                    # which detect_traps flags separately and the wording points at.
                    caps = _winning_captures_of(board, sq, stm)
                    check_caps = _checking_captures_of(board, sq, stm)
                    forcing = ""
                    if check_caps:
                        # Capturing this piece WITH CHECK is more forcing than a
                        # quiet recapture elsewhere — the zwischenzug nudge. If you
                        # have a free piece AND another recapture, take the CHECK
                        # first (you keep the recapture next move). General hint,
                        # not a move order the tool computes for you.
                        forcing = (f" NOTE: {', '.join(check_caps)} captures it WITH CHECK — that is more "
                                   f"forcing; if you also have a quiet recapture available elsewhere, play the "
                                   f"checking capture FIRST (zwischenzug) — you usually still get the other one.")
                    findings.append(Finding(True, "win",
                        f"FREE MATERIAL: opponent's {PIECE_NAME[p.piece_type]} on {_sq(sq)} is UNDEFENDED and you "
                        f"attack it — capturing it wins a piece (this is NOT a trade; it costs you nothing). "
                        f"Take it unless imagine_move shows it is a trap (you lose more material right after).{forcing}",
                        moves=caps, wiki="forks"))
            elif not defenders and not attackers and p.piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT):
                # Loose but not yet attacked — only flag as a *latent* target when
                # it's a real one: an active (developed) piece, not a rook sitting
                # on its home corner in the opening. Filter: the piece is off its
                # starting square OR we can reach it within one knight/slider hop.
                start_rank = 0 if color == chess.WHITE else 7
                on_home = chess.square_rank(sq) == start_rank
                if not mine and not on_home:
                    findings.append(Finding(False, "potential",
                        f"opponent's {PIECE_NAME[p.piece_type]} on {_sq(sq)} is undefended — "
                        f"a loose piece; look for a fork/double-attack hitting it", wiki="forks"))
    return findings


def _winning_captures_of(board: chess.Board, target: int, color: bool) -> list[str]:
    """SAN of every legal capture of `target` by `color` (only when it's color's
    turn). Used to hand the agent the concrete free-material captures so it does
    not have to find them itself."""
    if board.turn != color:
        return []
    out: list[str] = []
    for m in board.legal_moves:
        if m.to_square == target:
            try:
                out.append(board.san(m))
            except Exception:
                pass
    return sorted(set(out))


def _checking_captures_of(board: chess.Board, target: int, color: bool) -> list[str]:
    """SAN of legal captures of `target` by `color` that ALSO give check (only on
    color's turn). A checking capture is more forcing than a quiet one — used to
    nudge the zwischenzug (capture-with-check before a quiet recapture)."""
    if board.turn != color:
        return []
    out: list[str] = []
    for m in board.legal_moves:
        if m.to_square == target:
            b = board.copy(stack=False); b.push(m)
            if b.is_check():
                try:
                    out.append(board.san(m))
                except Exception:
                    pass
    return sorted(set(out))


def _handle_attacked_piece_moves(board: chess.Board, sq: int, color: bool) -> list[str]:
    """The 'handle a threat' move menu for an attacked piece (only when it's the
    side to move): capture the attacker / move the piece to safety / defend it."""
    if board.turn != color:
        return []
    p = board.piece_at(sq)
    moves: list[str] = []
    enemy = not color
    attackers = list(board.attackers(enemy, sq))
    # 1. capture an attacker
    for a in attackers:
        for m in board.legal_moves:
            if m.to_square == a:
                try:
                    moves.append(board.san(m) + " (captures attacker)")
                except Exception:
                    pass
    captured_attacker_sans = {m.split(" ")[0] for m in moves}
    # 2. move the piece to a safe square (skip ones already listed as captures)
    for m in _legal_sans_for_piece(board, sq):
        if m in captured_attacker_sans:
            continue  # already shown as "captures attacker"
        mv = next((x for x in board.legal_moves if x.from_square == sq and
                   board.san(x) == m), None)
        if mv:
            b2 = board.copy(); b2.push(mv)
            if not b2.attackers(enemy, mv.to_square) or \
               b2.attackers(color, mv.to_square):
                moves.append(m + " (moves to safety)")
    return moves[:8]


def detect_pins_skewers(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Absolute pins against the enemy king (current) and own pieces pinned
    (weakness). python-chess gives us pins cheaply."""
    findings: list[Finding] = []
    stm = board.turn if perspective is None else perspective
    for color in (chess.WHITE, chess.BLACK):
        mine = (color == stm)
        for sq in chess.SQUARES:
            p = board.piece_at(sq)
            if not p or p.color != color:
                continue
            if board.is_pinned(color, sq) and p.piece_type != chess.KING:
                if mine:
                    findings.append(Finding(True, "weakness",
                        f"your {PIECE_NAME[p.piece_type]} on {_sq(sq)} is PINNED — it can't move freely "
                        f"and doesn't truly defend; break the pin or don't rely on it",
                        wiki="pins"))
                else:
                    findings.append(Finding(False, "potential",
                        f"opponent's {PIECE_NAME[p.piece_type]} on {_sq(sq)} is PINNED to its king — it "
                        f"literally cannot move, so pile attackers on it (a pawn is ideal) to win it, and "
                        f"treat anything it 'defends' as undefended",
                        wiki="pins"))

    # RELATIVE pins (enemy piece pinned to a more-valuable enemy piece, not the
    # king): python-chess's is_pinned only catches ABSOLUTE pins, so the common
    # "knight pinned to the queen — can't move, pile on it" case was invisible.
    # For each of my line pieces, _pin_from finds an enemy front pinned against a
    # more valuable enemy rear. If I ALREADY attack the front, it's effectively
    # winnable — surface it with the piling move (a fresh attacker).
    seen_pinned = set()
    for from_sq in [s for s in chess.SQUARES
                    if board.piece_at(s) and board.piece_at(s).color == stm
                    and board.piece_at(s).piece_type in (chess.ROOK, chess.BISHOP, chess.QUEEN)]:
        pt = board.piece_at(from_sq).piece_type
        # Check EVERY ray (not just _pin_from's first hit — a queen on a file pin
        # would otherwise shadow a diagonal relative pin, the Wkp7l case).
        for d in _dirs_for(pt):
            res = _pin_on_ray(board, from_sq, d, stm)
            if not res:
                continue
            front, rear = res
            if front in seen_pinned:
                continue
            fp = board.piece_at(front); rp = board.piece_at(rear)
            if rp.piece_type == chess.KING:
                continue  # absolute pin already reported above
            seen_pinned.add(front)
            # A piling move = one that adds an attacker on the pinned `front`
            # (more of my pieces hit it than before), without being the pinning
            # piece itself. That's how you win a piece that can't safely move.
            before_atk = len(board.attackers(stm, front))
            piles = []
            for mv in board.legal_moves:
                if mv.from_square == from_sq or mv.to_square == front:
                    continue
                b2 = board.copy(stack=False); b2.push(mv)
                if len(b2.attackers(stm, front)) > before_atk:
                    try:
                        piles.append(board.san(mv))
                    except Exception:
                        pass
            findings.append(Finding(True, "potential",
                f"opponent's {PIECE_NAME[fp.piece_type]} on {_sq(front)} is RELATIVELY PINNED to its "
                f"{PIECE_NAME[rp.piece_type]} on {_sq(rear)} (your {PIECE_NAME[pt]} on {_sq(from_sq)} is "
                f"behind it) — it can't move without losing the {PIECE_NAME[rp.piece_type]}, so add another "
                f"attacker to win it",
                moves=sorted(set(piles))[:4], wiki="pins"))
    return findings


def _pin_on_ray(board: chess.Board, from_sq: int, d: int, color: bool):
    """On direction `d` from `from_sq`, if a `color` slider there pins an enemy
    front piece against a more-valuable enemy rear, return (front, rear); else
    None. Single-ray version (the caller iterates all rays so no pin is shadowed
    by an earlier-found one on a different ray)."""
    enemy = not color
    front = rear = None
    for sq in _ray_squares(from_sq, d):
        occ = board.piece_at(sq)
        if occ is None:
            continue
        if front is None:
            if occ.color != enemy:
                return None  # own piece blocks
            front = sq
            continue
        rear = sq if occ.color == enemy else None
        break
    if front is None or rear is None:
        return None
    front_pt = board.piece_at(front).piece_type
    rear_pt = board.piece_at(rear).piece_type
    if front_pt == chess.KING:
        return None
    if rear_pt == chess.KING or PIECE_VALUE[rear_pt] > PIECE_VALUE[front_pt]:
        return front, rear
    return None


# ---- skewers ----

# Sliding directions per piece type.
_ROOK_DIRS = [8, -8, 1, -1]
_BISHOP_DIRS = [9, 7, -9, -7]


def _ray_squares(frm: int, direction: int) -> list[int]:
    """Squares along `direction` from `frm` (exclusive), staying on-board."""
    out = []
    sq = frm
    while True:
        f0, r0 = chess.square_file(sq), chess.square_rank(sq)
        sq2 = sq + direction
        if not (0 <= sq2 < 64):
            break
        f1, r1 = chess.square_file(sq2), chess.square_rank(sq2)
        # reject wraparound (file jump > 1)
        if abs(f1 - f0) > 1:
            break
        out.append(sq2)
        sq = sq2
    return out


def _dirs_for(piece_type: int) -> list[int]:
    if piece_type == chess.ROOK:
        return _ROOK_DIRS
    if piece_type == chess.BISHOP:
        return _BISHOP_DIRS
    if piece_type == chess.QUEEN:
        return _ROOK_DIRS + _BISHOP_DIRS
    return []


def _skewer_from(board: chess.Board, from_sq: int, piece_type: int, color: bool):
    """If a line piece of `piece_type`/`color` standing on `from_sq` skewers an
    enemy pair, return (front_sq, rear_sq, direction); else None. Pure geometry,
    independent of whether such a piece is actually there (so it works for both
    current pieces and hypothetical landing squares)."""
    enemy = not color
    for d in _dirs_for(piece_type):
        front = rear = None
        for sq in _ray_squares(from_sq, d):
            occ = board.piece_at(sq)
            if occ is None:
                continue
            if front is None:
                if occ.color != enemy:
                    break  # blocked by own piece — no skewer this ray
                front = sq
                continue
            else:
                rear = sq if occ.color == enemy else None
                break
        if front is None or rear is None:
            continue
        # skewer proper: front at least as valuable as rear (front must move,
        # rear is won). King in front = absolute skewer.
        if PIECE_VALUE[board.piece_at(front).piece_type] >= PIECE_VALUE[board.piece_at(rear).piece_type]:
            return front, rear, d
    return None


def _pin_from(board: chess.Board, from_sq: int, piece_type: int, color: bool):
    """If a line piece of `piece_type`/`color` on `from_sq` would PIN an enemy
    piece (front) against a more valuable enemy piece or the king (rear) on the
    same ray, return (front_sq, rear_sq, direction); else None. Pure geometry, so
    it works for both a piece already there and a hypothetical landing square.

    Pin vs skewer is the value order: pin = front LESS valuable than rear (the
    front can't move without losing the rear, so it's stuck and you win it);
    skewer = front at least as valuable (handled by _skewer_from). King behind =
    absolute pin (front literally cannot move)."""
    enemy = not color
    for d in _dirs_for(piece_type):
        front = rear = None
        for sq in _ray_squares(from_sq, d):
            occ = board.piece_at(sq)
            if occ is None:
                continue
            if front is None:
                if occ.color != enemy:
                    break  # own piece blocks this ray
                front = sq
                continue
            else:
                rear = sq if occ.color == enemy else None
                break
        if front is None or rear is None:
            continue
        front_pt = board.piece_at(front).piece_type
        rear_pt = board.piece_at(rear).piece_type
        if front_pt == chess.KING:
            continue  # king in front is a skewer/check, not a pin
        # Pin proper: the rear is strictly more valuable than the front (or is the
        # king) — moving the front loses the rear, so the front is stuck/winnable.
        if rear_pt == chess.KING or PIECE_VALUE[rear_pt] > PIECE_VALUE[front_pt]:
            return front, rear, d
    return None


def detect_creatable_pins(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Pins you (or the opponent) could CREATE next move: slide a line piece to a
    square where it pins an enemy piece against a more valuable piece/king. The
    high-value case — pinning the enemy QUEEN to its king (you then win the queen
    by piling on) — is the whole `pin` motif and was previously invisible (only
    *already-existing* pins were detected). Mirror of the potential-skewer scan."""
    findings: list[Finding] = []
    stm = board.turn if perspective is None else perspective
    for color in (chess.WHITE, chess.BLACK):
        mine = (color == stm)
        line_pieces = [(s, board.piece_at(s).piece_type) for s in chess.SQUARES
                       if board.piece_at(s) and board.piece_at(s).color == color
                       and board.piece_at(s).piece_type in (chess.ROOK, chess.BISHOP, chess.QUEEN)]
        seen = set()
        for from_sq, pt in line_pieces:
            for d in _dirs_for(pt):
                for land in _ray_squares(from_sq, d):
                    occ = board.piece_at(land)
                    if occ is not None and occ.color == color:
                        break
                    res = _pin_from(board, land, pt, color)
                    if res:
                        front, rear, _dd = res
                        if (front, rear) in seen:
                            if occ is not None:
                                break
                            continue
                        seen.add((front, rear))
                        fp = board.piece_at(front); rp = board.piece_at(rear)
                        # Only surface the strong cases: pin against the king
                        # (absolute) or against the queen — piling on a pinned
                        # queen/rook is a real win. Skip pinning a pawn to a rook.
                        if rp.piece_type == chess.KING or fp.piece_type in (chess.QUEEN, chess.ROOK):
                            if mine:
                                findings.append(Finding(True, "potential",
                                    f"your {PIECE_NAME[pt]} could move to {_sq(land)} to PIN enemy "
                                    f"{PIECE_NAME[fp.piece_type]} on {_sq(front)} against "
                                    f"{'the KING' if rp.piece_type == chess.KING else PIECE_NAME[rp.piece_type]} "
                                    f"on {_sq(rear)} — the pinned {PIECE_NAME[fp.piece_type]} can't move, so "
                                    f"pile attackers on it (a pawn is ideal) to win it. Calculate it; a small "
                                    f"cost elsewhere is worth winning the {PIECE_NAME[fp.piece_type]}.",
                                    moves=[board.san(chess.Move(from_sq, land))]
                                          if chess.Move(from_sq, land) in board.legal_moves else [],
                                    wiki="pins"))
                            else:
                                findings.append(Finding(False, "potential",
                                    f"opponent could move their {PIECE_NAME[pt]} to {_sq(land)} to PIN your "
                                    f"{PIECE_NAME[fp.piece_type]} on {_sq(front)} against your "
                                    f"{'KING' if rp.piece_type == chess.KING else PIECE_NAME[rp.piece_type]} "
                                    f"on {_sq(rear)} — pre-empt it (move a piece off the line or guard "
                                    f"{_sq(land)})", wiki="pins"))
                    if occ is not None:
                        break
    return findings


def _axis_word(d: int) -> str:
    return "file" if d in (8, -8) else ("rank" if d in (1, -1) else "diagonal")


def detect_skewers(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Skewers — CURRENT (a line piece already bears on the front piece) AND
    POTENTIAL/PREEMPTIVE (a line piece could MOVE next turn to a square that
    creates a skewer). Detected for both sides, so the agent sees both its own
    skewer chances and skewers the opponent threatens against it *before* they
    are played.
    """
    findings: list[Finding] = []
    stm = board.turn if perspective is None else perspective
    for color in (chess.WHITE, chess.BLACK):
        mine = (color == stm)
        line_pieces = [(s, board.piece_at(s).piece_type) for s in chess.SQUARES
                       if board.piece_at(s) and board.piece_at(s).color == color
                       and board.piece_at(s).piece_type in (chess.ROOK, chess.BISHOP, chess.QUEEN)]
        seen_pairs = set()  # avoid duplicate (front,rear) across current+potential
        # 1) CURRENT skewers (piece already on a skewering square)
        for from_sq, pt in line_pieces:
            res = _skewer_from(board, from_sq, pt, color)
            if not res:
                continue
            front, rear, d = res
            key = (front, rear)
            seen_pairs.add(key)
            fp, rp = board.piece_at(front), board.piece_at(rear)
            if mine:
                findings.append(Finding(True, "strength",
                    f"your {PIECE_NAME[pt]} on {_sq(from_sq)} SKEWERS {PIECE_NAME[fp.piece_type]} on "
                    f"{_sq(front)} → {PIECE_NAME[rp.piece_type]} on {_sq(rear)} behind it; the front "
                    f"piece is forced to move, so you win the one behind", wiki="pins"))
            else:
                findings.append(Finding(False, "threat",
                    f"opponent's {PIECE_NAME[pt]} on {_sq(from_sq)} SKEWERS your {PIECE_NAME[fp.piece_type]} "
                    f"on {_sq(front)} and {PIECE_NAME[rp.piece_type]} behind it — the front piece must move "
                    f"and you lose the one behind; move one off the {_axis_word(d)} or block", wiki="pins"))
        # 2) POTENTIAL skewers (a line piece could move to a skewering square next).
        # Scan every square each line piece could slide to along its rays (ignoring
        # whether it's that side's turn — a potential threat applies on the next move).
        for from_sq, pt in line_pieces:
            for d in _dirs_for(pt):
                for land in _ray_squares(from_sq, d):
                    occ = board.piece_at(land)
                    if occ is not None and occ.color == color:
                        break  # own piece blocks further sliding
                    # would a piece of this type on `land` skewer something?
                    res = _skewer_from(board, land, pt, color)
                    if res:
                        front, rear, dd = res
                        if (front, rear) in seen_pairs:
                            if occ is not None:
                                break
                            continue
                        seen_pairs.add((front, rear))
                        fp, rp = board.piece_at(front), board.piece_at(rear)
                        if mine:
                            findings.append(Finding(True, "potential",
                                f"your {PIECE_NAME[pt]} could move to {_sq(land)} to SKEWER enemy "
                                f"{PIECE_NAME[fp.piece_type]} on {_sq(front)} → {PIECE_NAME[rp.piece_type]} "
                                f"on {_sq(rear)} behind it (front piece forced to move, you win the one "
                                f"behind) — calculate it",
                                moves=_move_san(board, from_sq, land), wiki="pins"))
                        else:
                            findings.append(Finding(False, "potential",
                                f"opponent could move their {PIECE_NAME[pt]} to {_sq(land)} to SKEWER your "
                                f"{PIECE_NAME[fp.piece_type]} on {_sq(front)} and {PIECE_NAME[rp.piece_type]} "
                                f"behind it — move one off the {_axis_word(dd)} now, or guard {_sq(land)}",
                                wiki="pins"))
                    if occ is not None:
                        break  # enemy piece on `land` — can't slide past it
    return findings


# ---- discovered attacks / checks ----

def detect_discovered_attacks(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Discovered-attack geometry: one of my pieces sits between my own line
    piece (R/B/Q) and an enemy target on the same ray. Moving the front piece
    unveils the attack. If the unveiled line hits the enemy KING, moving the
    front piece is a discovered CHECK — the front piece can then grab almost
    anything (the free-capture engine). Lists the front piece's moves to consider.
    """
    findings: list[Finding] = []
    stm = board.turn if perspective is None else perspective
    for color in (chess.WHITE, chess.BLACK):
        mine = (color == stm)
        enemy = not color
        for back_sq in chess.SQUARES:
            bp = board.piece_at(back_sq)
            if not bp or bp.color != color or bp.piece_type not in (chess.ROOK, chess.BISHOP, chess.QUEEN):
                continue
            for d in _dirs_for(bp.piece_type):
                screen = target = None
                for sq in _ray_squares(back_sq, d):
                    occ = board.piece_at(sq)
                    if occ is None:
                        continue
                    if screen is None:
                        if occ.color != color:
                            break  # first piece is enemy → ordinary attack, not a discovery
                        screen = sq
                        continue
                    else:
                        target = sq if occ.color == enemy else None
                        break
                if screen is None or target is None:
                    continue
                tp = board.piece_at(target)
                is_check_line = (tp.piece_type == chess.KING)
                # Relevance filter: a discovered CHECK is always worth flagging.
                # A non-check discovery is only meaningful if the unveiled target
                # is a real PIECE (knight or better) — unveiling a line onto an
                # enemy pawn (e.g. a-pawn screening a rook from the enemy a-pawn)
                # is noise. Also require the screen has a legal move to make (else
                # there is no discovery available).
                if not is_check_line and tp.piece_type == chess.PAWN:
                    continue
                if board.turn == color and not _legal_sans_for_piece(board, screen):
                    continue
                sp = board.piece_at(screen)
                if mine:
                    movers = _legal_sans_for_piece(board, screen) if board.turn == color else []
                    if is_check_line:
                        desc = (f"your {PIECE_NAME[sp.piece_type]} on {_sq(screen)} sits between your "
                                f"{PIECE_NAME[bp.piece_type]} on {_sq(back_sq)} and the enemy KING on "
                                f"{_sq(target)} — moving it is a DISCOVERED CHECK, so it can capture "
                                f"almost anything for free (check first; verify they can't answer the "
                                f"check AND save the piece in one move)")
                        f = Finding(True, "strength", desc, wiki="discovered")
                        if movers:
                            f.moves = movers[:6]
                        findings.append(f)
                    else:
                        # Among the discovering moves, which ALSO give check? A
                        # discovered attack delivered WITH CHECK is far stronger than
                        # a quiet one: the opponent must answer the check and CANNOT
                        # also save the discovered-attacked piece, so it falls (VhRSK:
                        # Bxh7+ discovers Qd1-vs-Qd6 AND checks → Kxh7, then Qxd6 wins
                        # the queen; the agent otherwise picks a quiet discovering
                        # move that merely "attacks" the well-defended/movable queen).
                        checking_movers = []
                        if board.turn == color:
                            for s in movers:
                                try:
                                    m = board.parse_san(s)
                                except Exception:
                                    continue
                                if board.gives_check(m):
                                    checking_movers.append(s)
                        desc = (f"your {PIECE_NAME[sp.piece_type]} on {_sq(screen)} screens your "
                                f"{PIECE_NAME[bp.piece_type]} on {_sq(back_sq)} from the enemy "
                                f"{PIECE_NAME[tp.piece_type]} on {_sq(target)} — moving it discovers an "
                                f"attack while the mover makes its own threat (two threats at once)")
                        if checking_movers:
                            desc += (f". ⚡ STRONGEST: a discovering move that ALSO gives CHECK "
                                     f"({', '.join(sorted(set(checking_movers)))}) is usually winning — "
                                     f"the opponent must answer the check and CANNOT also save the "
                                     f"{PIECE_NAME[tp.piece_type]} on {_sq(target)}. Calculate it with "
                                     f"`imagine_line` (check → their forced reply → capture the "
                                     f"{PIECE_NAME[tp.piece_type]}) even if the checking move looks like a "
                                     f"sacrifice")
                        f = Finding(True, "potential", desc, wiki="discovered")
                        if movers:
                            # surface the checking discoverers FIRST
                            ordered_m = sorted(set(checking_movers)) + [m for m in movers if m not in checking_movers]
                            f.moves = ordered_m[:6]
                        findings.append(f)
                else:
                    if is_check_line:
                        findings.append(Finding(False, "threat",
                            f"opponent's {PIECE_NAME[sp.piece_type]} on {_sq(screen)} screens their "
                            f"{PIECE_NAME[bp.piece_type]} from your KING on {_sq(target)} — they have a "
                            f"DISCOVERED CHECK available; beware they move it and grab a piece for free",
                            wiki="discovered"))
                    else:
                        # Warn about an opponent piece-discovery only when the
                        # unveiled target (one of YOUR pieces) is valuable AND
                        # undefended — i.e. the discovery would actually win it.
                        # Otherwise it's noise (an unveiled but defended/cheap piece).
                        if tp.piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT) \
                           and not board.attackers(color, target):
                            findings.append(Finding(False, "potential",
                                f"opponent's {PIECE_NAME[sp.piece_type]} on {_sq(screen)} screens their "
                                f"{PIECE_NAME[bp.piece_type]} from your undefended {PIECE_NAME[tp.piece_type]} "
                                f"on {_sq(target)} — if they move it they discover an attack winning it; "
                                f"defend the {PIECE_NAME[tp.piece_type]} or move it", wiki="discovered"))
    return findings


# ============================================================================
# FUNDAMENTALS  (phase pointer — radar names the page; agent reads it)
# ============================================================================

def _phase(board: chess.Board) -> str:
    """'opening' | 'middlegame' | 'endgame'. Material decides endgame first (few
    pieces => endgame regardless of move number, since puzzle/constructed
    positions start at move 1); then development/move-number for opening vs
    middlegame. Shared by phase fundamentals and the (phase-gated) center-control
    and trade-advice detectors."""
    n_pieces = chess.popcount(board.occupied)
    minors_majors = sum(len(board.pieces(pt, c))
                        for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
                        for c in (chess.WHITE, chess.BLACK))
    if n_pieces <= 12 or minors_majors <= 6:
        return "endgame"
    home_minors = sum(1 for c in (chess.WHITE, chess.BLACK)
                      for sq in _HOME[c]
                      if board.piece_at(sq) and board.piece_at(sq).color == c and
                      board.piece_at(sq).piece_type in (chess.KNIGHT, chess.BISHOP))
    if board.fullmove_number <= 10 and home_minors >= 3:
        return "opening"
    return "middlegame"


_CENTER = [chess.D4, chess.E4, chess.D5, chess.E5]            # the 4 central squares
_BIG_CENTER = [chess.square(f, r) for f in range(2, 6) for r in range(2, 6)]  # c3–f6


def detect_center_control(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Center control — OPENING / early-MIDDLEGAME only (it governs piece mobility
    and space then; in the endgame king activity and passed pawns matter instead,
    so this stays silent there). For the four central squares (d4/e4/d5/e5) it
    scores, per side, occupation (a pawn on the square = strong, +2; a piece, +1)
    plus the number of times the side attacks the square (+1 each). Pure
    rules/geometry — a positional fact like material, not a move recommendation.

    Flags a clear central deficit for the agent (the opponent controls the centre)
    and, in the opening, a central square the agent could fight for."""
    findings: list[Finding] = []
    if _phase(board) == "endgame":
        return findings
    stm = board.turn if perspective is None else perspective

    def control(color: bool) -> int:
        score = 0
        for sq in _CENTER:
            p = board.piece_at(sq)
            if p and p.color == color:
                score += 2 if p.piece_type == chess.PAWN else 1
            score += len(board.attackers(color, sq))
        return score

    mine, theirs = control(stm), control(not stm)
    # central pawns are the backbone of center control — count them too
    my_center_pawns = sum(1 for sq in _CENTER if (p := board.piece_at(sq)) and p.color == stm and p.piece_type == chess.PAWN)
    opp_center_pawns = sum(1 for sq in _CENTER if (p := board.piece_at(sq)) and p.color != stm and p.piece_type == chess.PAWN)

    if theirs - mine >= 3:
        findings.append(Finding(True, "weakness",
            f"the OPPONENT controls the centre (their central influence {theirs} vs your {mine}) — "
            f"you are cramped. Fight back: put a pawn on d4/e4/d5/e5, aim a knight at the centre "
            f"(Nf3/Nc3/Nf6/Nc6), or strike with c/f pawns; don't let them keep a free centre",
            wiki="center"))
    elif mine - theirs >= 3:
        findings.append(Finding(True, "strength",
            f"you control the centre (your central influence {mine} vs their {theirs}) — you have more "
            f"space and faster piece access; use it to switch play between wings, but support the centre "
            f"so it isn't undermined by a c/f-pawn break", wiki="center"))

    # In the opening, point at an empty central square the agent can fight for.
    if _phase(board) == "opening" and my_center_pawns <= opp_center_pawns:
        for sq in (chess.E4, chess.D4):
            if board.piece_at(sq) is None:
                # a pawn push or a piece move that would claim/attack it
                pushers = [board.san(m) for m in board.legal_moves
                           if m.to_square == sq and board.piece_at(m.from_square)
                           and board.piece_at(m.from_square).piece_type == chess.PAWN]
                if pushers:
                    findings.append(Finding(True, "potential",
                        f"the centre square {_sq(sq)} is yours to take — a classical central pawn "
                        f"({', '.join(pushers)}) grabs space and opens lines for your pieces",
                        moves=pushers, wiki="center"))
                    break
    return findings


def detect_phase_fundamentals(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Name the phase and point to its fundamentals page. Auto-load by phase is
    the agent reading the page the radar names."""
    phase = _phase(board)
    if phase == "endgame":
        return [Finding(True, "fundamental",
            "ENDGAME phase — activate your king (it is a fighting piece now), push passed pawns "
            "(rook behind them), use opposition; FORCING moves (checks) and king activity decide here",
            wiki="fund_endgame")]
    if phase == "opening":
        return [Finding(True, "fundamental",
            "OPENING phase — control the CENTRE (d4/e4/d5/e5), develop every piece toward it, castle; "
            "don't move the same piece twice or grab pawns while undeveloped",
            wiki="fund_opening")]
    return [Finding(True, "fundamental",
        "MIDDLEGAME phase — assess both sides, attack the king or a weakness, keep pieces active and "
        "safe; this is where most COMBINATIONS occur — calculate trades and tactics fully",
        wiki="fund_middlegame")]


# ============================================================================
# TOP-LEVEL ASSEMBLER
# ============================================================================

def _material_count(board: chess.Board, color: bool) -> int:
    return sum(PIECE_VALUE[pt] * len(board.pieces(pt, color))
               for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN))


def _opponent_threat(board: chess.Board) -> tuple[str, str] | None:
    """What does the opponent threaten on its NEXT move if the side-to-move does
    nothing relevant? Give the opponent a free move (null) and read its strongest
    immediate threat. Returns ('mate', san) | ('material', san) | None. Pure 1-ply
    mechanics — the standard 'pass and see' threat test a human does. (If already in
    check, the threat IS the check; handled by the caller.)"""
    if board.is_check():
        return None
    try:
        from _eval import static_exchange_eval
    except Exception:
        static_exchange_eval = None
    b = board.copy(stack=False)
    try:
        b.push(chess.Move.null())
    except Exception:
        return None
    opp = b.turn
    # mate threat first
    for mv in b.legal_moves:
        c = b.copy(stack=False); c.push(mv)
        if c.is_checkmate():
            try:
                return ("mate", b.san(mv))
            except Exception:
                return ("mate", b.uci(mv))
    # material threat: a capture that nets >= ~2 pawns by SEE, or a fork-ish double
    if static_exchange_eval is not None:
        best = None
        for mv in b.legal_moves:
            if not b.is_capture(mv):
                continue
            try:
                gain = static_exchange_eval(b, mv.to_square, opp)
            except Exception:
                continue
            if gain >= 200 and (best is None or gain > best[1]):
                try:
                    best = (b.san(mv), gain)
                except Exception:
                    best = (b.uci(mv), gain)
        if best:
            return ("material", best[0])
    return None


def _moves_that_prevent_mate(board: chess.Board) -> list[str]:
    """When the opponent threatens mate-in-1 (after the side-to-move passes), return
    the SANs of the side-to-move's moves that stop it — i.e. after the move, the
    opponent no longer has a mate-in-1 (or the move itself mates/ends the game). Pure
    mechanics ('which of my moves defend this mate'); the agent still calculates which
    actually survives deeper. Returns [] if no mate is threatened."""
    def opp_has_mate(bd: chess.Board) -> bool:
        if bd.is_game_over():
            return False
        for m in bd.legal_moves:
            c = bd.copy(stack=False); c.push(m)
            if c.is_checkmate():
                return True
        return False
    # confirm a mate is actually threatened (via null move)
    if board.is_check():
        threatened = True   # being in check, a mate-in-1 may follow any non-escaping move
    else:
        probe = board.copy(stack=False)
        try:
            probe.push(chess.Move.null())
        except Exception:
            return []
        threatened = opp_has_mate(probe)
    if not threatened:
        return []
    savers = []
    for mv in board.legal_moves:
        c = board.copy(stack=False); c.push(mv)
        if c.is_game_over():          # we mated/stalemated — counts as 'not mated'
            if c.is_checkmate():
                savers.append(board.san(mv))
            continue
        if not opp_has_mate(c):
            try:
                savers.append(board.san(mv))
            except Exception:
                pass
    return savers


def assess_situation(board: chess.Board, perspective: bool | None = None) -> dict:
    """Mechanical SITUATION assessment that sets the agent's PRIORITY for this move.

    A strong player triages first — *what does this position demand?* — and that
    decides which features matter. The same fact (e.g. 'this capture loses material')
    means opposite things when you are being mated (a defensive sac may be forced)
    versus when you are winning and safe (don't grab — simplify). This computes the
    triage from mechanical facts only (material count, check/threat via null move,
    forcing-move existence, phase) and names a priority. It NEVER picks a move —
    exactly the context a coach gives ('you're up a piece, just trade').

    Returns a dict with the classification + a 'lines' list rendered at the top of
    show_position. Fair under the rulebook (informative, not move-selecting)."""
    stm = board.turn if perspective is None else perspective
    # _material_count uses PIECE_VALUE in PAWN units (P=1,N=B=3,R=5,Q=9) — already pawns.
    diff = _material_count(board, stm) - _material_count(board, not stm)
    phase = _phase(board)
    in_check = board.is_check() and board.turn == stm
    threat = _opponent_threat(board) if board.turn == stm else None
    # do I have a forcing move (a check or a capture of a real piece)?
    have_forcing = False
    for mv in board.legal_moves:
        if board.gives_check(mv):
            have_forcing = True; break
        if board.is_capture(mv):
            v = board.piece_at(mv.to_square)
            if v and v.piece_type != chess.PAWN:
                have_forcing = True; break

    if diff >= 5:    mat = "winning big"
    elif diff >= 2:  mat = "ahead"
    elif diff >= -1: mat = "roughly equal"
    elif diff > -5:  mat = "behind"
    else:            mat = "losing big"
    mat_str = (f"+{diff}" if diff > 0 else str(diff))

    # priority decision tree (first match wins)
    savers: list[str] = []
    if in_check:
        prio = ("RESPOND TO THE CHECK", "you are in check — you must address it. Among your legal "
                "replies, prefer the one that leaves your king SAFEST (fewest follow-up checks / no "
                "walk into a new attack), not just the first that escapes. A block or a capture of the "
                "checker can be better than running the king — calculate each with imagine_move.")
    elif threat and threat[0] == "mate":
        # Enumerate the moves that actually PREVENT the threatened mate — a fair,
        # mechanical narrowing ('which of my moves stop this mate') that hands the
        # agent the right shortlist (it tends to fixate on the first defence it sees
        # and miss a material-losing one like Rxc8 that also holds). Listing them is
        # mechanics; the agent still calculates which survives.
        savers = _moves_that_prevent_mate(board)
        prio = ("SURVIVAL — you are being mated", f"the opponent threatens MATE ({threat[1]}) next move. "
                "This DOMINATES everything: defend the mate before any other consideration. **Material is "
                "secondary — a move that LOSES material but stops the mate is correct; a 'free' capture "
                "or a quiet improving move that allows the mate is losing.** Ignore the trap/greed "
                "warnings below if the move they flag is what defends the king.")
    elif threat and threat[0] == "material":
        prio = ("MEET THE THREAT", f"the opponent threatens to win material ({threat[1]}) next move. "
                "Address it — defend the target, move it, or make a bigger/forcing threat of your own — "
                "UNLESS a forcing move of yours wins more. Don't play a slow move that lets the threat land.")
    elif diff >= 3 and phase != "opening":
        # 'Consolidate' means different things with vs without pieces on the board.
        has_pieces = any(board.pieces(pt, c)
                         for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
                         for c in (chess.WHITE, chess.BLACK))
        if has_pieces:
            body = ("you are materially ahead and your king is not under immediate threat. The win is "
                    "CONVERSION, not winning more: trade PIECES (not pawns) to simplify toward a won "
                    "endgame, keep your king safe, and avoid unnecessary complications. Do NOT grab more "
                    "material if it loosens your position — a clean simple position wins itself.")
        else:
            body = ("you are ahead in a KING-AND-PAWN endgame (no pieces left). Technique wins this, not "
                    "more material: ACTIVATE YOUR KING toward the key pawns, shepherd your passed pawn "
                    "with the king in front, take the OPPOSITION to force the enemy king back, and create "
                    "an outside passed pawn if you can. Don't shuffle or drift the king away from the action.")
        prio = ("CONSOLIDATE — you are ahead", body)
    elif diff <= -3:
        prio = ("COUNTERPLAY — you are behind", "you are materially behind but not in immediate danger. "
                "Passive defense loses slowly. Seek ACTIVITY and complications: forcing moves, attacks on "
                "the king, pawn breaks, tactical chances. A sharp or speculative move that creates problems "
                "for the opponent is justified here — safe-but-passive play just prolongs a lost game.")
    elif have_forcing:
        prio = ("CALCULATE FORCING MOVES FIRST", "no immediate threat against you, but you have checks/"
                "captures available (see the forcing list). Calculate those FIRST — a forcing move that "
                "wins beats any quiet plan — then, if none works, play positionally.")
    else:
        plan = {"opening": "develop a new piece, fight for the centre, get your king castled — don't grab "
                           "pawns or move the same piece twice without reason",
                "middlegame": "improve your worst-placed piece, target a weakness, control key files/"
                             "diagonals; keep your king safe",
                "endgame": "activate your KING (it is a fighting piece now), push passed pawns with support, "
                          "use opposition — king and pawns decide here"}[phase]
        prio = ("PLAY POSITIONALLY", f"quiet position, no immediate threat or tactic. {plan}.")

    head, body = prio
    lines = [
        f"## Situation — **PRIORITY: {head}**",
        f"- **Material:** {mat} ({mat_str} pawns, from your side).  **Phase:** {phase}.  "
        + (f"**Your king:** IN CHECK." if in_check else
           (f"**Threat against you:** {threat[1]} ({threat[0]})." if threat else "**No immediate threat against you.**")),
        f"- {body}",
    ]
    # The mate-saver shortlist gets its OWN prominent line (delivery location beats
    # burying it in the paragraph — the model otherwise asserts a listed saver
    # 'doesn't address the mate' without checking). One of these IS the move.
    if savers:
        shown = savers[:10]
        lines.append(
            f"- **🛡 ONLY these moves stop the mate — the answer is ONE of them: "
            f"{', '.join(shown)}{'…' if len(savers) > 10 else ''}.** Play EACH out with "
            f"`imagine_line`; anything else loses to {threat[1]}. Do not dismiss a move as "
            f"'irrelevant to the king' — if it is on this list, it provably stops the mate "
            f"(it may cost material and STILL be correct)."
        )
    return dict(material=mat, material_diff=diff, phase=phase, in_check=in_check,
                threat=threat, have_forcing=have_forcing, priority=head,
                mate_savers=savers, lines=lines)


def detect_material(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Material balance → trading advice (principles/material-and-trading).
    Up material: trade pieces (not pawns), keep a rook/queen for mating. Down
    material: avoid trades, seek complications. Advisory heuristic, not a fact."""
    findings: list[Finding] = []
    stm = board.turn if perspective is None else perspective
    diff = _material_count(board, stm) - _material_count(board, not stm)
    if diff >= 2:
        findings.append(Finding(True, "strength",
            f"you are UP ~{diff} points of material — prefer trading PIECES (not pawns) to simplify "
            f"toward a won endgame; keep at least one rook or the queen for mating",
            wiki="material"))
    elif diff <= -2:
        findings.append(Finding(True, "weakness",
            f"you are DOWN ~{-diff} points of material — when given the choice, avoid INITIATING even "
            f"piece trades (keep pieces on for chances) and seek complications/counterplay. "
            f"This does NOT mean refuse free material: ALWAYS capture an undefended enemy piece or win "
            f"a favourable exchange — that is how you climb back, not a trade to avoid.",
            wiki="material"))
    return findings


def detect_king_safety(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """King exposure for BOTH sides (positional/king-safety). Flags an uncastled
    king with the game still open, a king on a (half-)open file, and a missing
    pawn shield — for you (defend) and the opponent (attack)."""
    findings: list[Finding] = []
    stm = board.turn if perspective is None else perspective
    fullmove = board.fullmove_number

    def shield_intact(color: bool, ksq: int) -> bool:
        kf, kr = chess.square_file(ksq), chess.square_rank(ksq)
        home = 1 if color == chess.WHITE else 6
        step = 1 if color == chess.WHITE else -1
        if kr not in (0, 7):
            return True  # king already off the back rank; different question
        cnt = 0
        for f in (kf - 1, kf, kf + 1):
            if 0 <= f <= 7:
                sq = chess.square(f, home)
                p = board.piece_at(sq)
                if p and p.piece_type == chess.PAWN and p.color == color:
                    cnt += 1
        return cnt >= 2

    for color in (chess.WHITE, chess.BLACK):
        mine = (color == stm)
        ksq = board.king(color)
        if ksq is None:
            continue
        kf = chess.square_file(ksq)
        # king on an open / half-open file (no own pawn on it)
        own_pawn_on_file = any(chess.square_file(s) == kf for s in board.pieces(chess.PAWN, color))
        on_back = chess.square_rank(ksq) in (0, 7)
        exposed_file = not own_pawn_on_file
        broken_shield = on_back and not shield_intact(color, ksq)
        # only meaningful while there is attacking material (queens or rooks on)
        heavy_on = bool(board.pieces(chess.QUEEN, not color)) or len(board.pieces(chess.ROOK, not color)) >= 1
        if (exposed_file or broken_shield) and heavy_on:
            if mine:
                findings.append(Finding(True, "weakness",
                    f"your KING on {_sq(ksq)} is exposed ("
                    + ("no pawn on its file" if exposed_file else "broken pawn shield")
                    + ") with enemy heavy pieces on — get it safe (castle if you can), keep the "
                    "pawn shield, trade off the enemy's attackers", wiki="king_safety"))
            else:
                findings.append(Finding(False, "potential",
                    f"opponent's KING on {_sq(ksq)} is exposed ("
                    + ("open file" if exposed_file else "broken shield")
                    + ") — open lines toward it, bring a rook to that file, DON'T trade your "
                    "attackers", wiki="king_safety"))
    return findings


def detect_overloaded_defenders(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """A single defender guarding two (or more) of its own attacked pieces is
    OVERLOADED — attack one and the other falls (tactics/removing-the-defender).
    Reported for both sides. Pure mechanics: a defender that is the sole guard of
    2+ pieces which are themselves attacked by the enemy."""
    findings: list[Finding] = []
    stm = board.turn if perspective is None else perspective
    for color in (chess.WHITE, chess.BLACK):
        mine = (color == stm)
        enemy = not color
        # for each of `color`'s pieces, who is its defender and is it attacked?
        guard_load: dict[int, list[int]] = {}
        for sq in chess.SQUARES:
            p = board.piece_at(sq)
            if not p or p.color != color or p.piece_type == chess.KING:
                continue
            if not board.attackers(enemy, sq):
                continue  # not attacked → not a live duty
            defenders = [d for d in board.attackers(color, sq) if d != sq]
            if len(defenders) == 1:
                guard_load.setdefault(defenders[0], []).append(sq)
        for guard, duties in guard_load.items():
            if len(duties) >= 2:
                gp = board.piece_at(guard)
                duty_str = ", ".join(f"{PIECE_NAME[board.piece_at(d).piece_type]} on {_sq(d)}" for d in duties)
                if not mine:
                    findings.append(Finding(False, "potential",
                        f"opponent's {PIECE_NAME[gp.piece_type]} on {_sq(guard)} is OVERLOADED — it is "
                        f"the only defender of {duty_str}; attack/remove it (or one duty) and another "
                        f"falls", wiki="removing"))
                else:
                    findings.append(Finding(True, "weakness",
                        f"your {PIECE_NAME[gp.piece_type]} on {_sq(guard)} is OVERLOADED — sole defender "
                        f"of {duty_str}; add a defender or relieve it before they exploit it",
                        wiki="removing"))
    return findings


def detect_removable_defender(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """REMOVING THE DEFENDER: you attack an enemy piece (≥ a minor) that is
    defended by exactly ONE piece — if you can CAPTURE or DEFLECT that sole
    defender, the attacked piece falls. This is the capturingDefender / deflection
    motif and it usually STARTS with a sacrifice-looking capture of the defender
    (e.g. the e7 knight is defended only by the d8 rook → Qxd8 removes the guard,
    then Rxe7 wins the knight). Surfaced because the agent, warned its own piece
    hangs, plays safe instead of this winning capture.

    Only the side to move (it has to play the removing move). Pure mechanics; the
    agent still calculates the sequence."""
    findings: list[Finding] = []
    stm = board.turn if perspective is None else perspective
    if board.turn != stm:
        return findings
    enemy = not stm
    seen = set()
    for tsq in chess.SQUARES:
        ep = board.piece_at(tsq)
        if not ep or ep.color != enemy or ep.piece_type in (chess.KING, chess.PAWN):
            continue
        if not board.attackers(stm, tsq):
            continue                                   # I don't attack it
        defenders = [d for d in board.attackers(enemy, tsq) if d != tsq]
        if len(defenders) != 1:
            continue                                   # need a SINGLE defender to remove
        guard = defenders[0]
        gp = board.piece_at(guard)
        if gp is None or gp.piece_type == chess.KING:
            continue                                   # can't capture the king as a "defender"
        # Can I capture that sole defender, or attack it (deflect)? Prefer the
        # concrete capture move(s) of the guard square.
        cap_moves = []
        for mv in board.legal_moves:
            if mv.to_square == guard:
                try:
                    cap_moves.append(board.san(mv))
                except Exception:
                    pass
        if not cap_moves:
            continue
        if (tsq, guard) in seen:
            continue
        seen.add((tsq, guard))
        findings.append(Finding(True, "potential",
            f"REMOVE THE DEFENDER: the {PIECE_NAME[ep.piece_type]} on {_sq(tsq)} is defended ONLY by the "
            f"{PIECE_NAME[gp.piece_type]} on {_sq(guard)}. Capture/deflect that defender "
            f"({', '.join(sorted(set(cap_moves)))}) — even as a sacrifice — and the {PIECE_NAME[ep.piece_type]} "
            f"on {_sq(tsq)} then falls. Calculate the full sequence with `imagine_line` "
            f"(take the defender → their recapture → you take the {PIECE_NAME[ep.piece_type]}).",
            moves=sorted(set(cap_moves))[:4], wiki="removing"))
    return findings


def detect_own_back_rank(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Own king boxed on the back rank with no luft (principles/luft). Flags when
    the king's three forward squares are all blocked by its own pawns and an enemy
    rook/queen could reach the back rank."""
    findings: list[Finding] = []
    stm = board.turn if perspective is None else perspective
    for color in (chess.WHITE, chess.BLACK):
        mine = (color == stm)
        ksq = board.king(color)
        if ksq is None:
            continue
        back = 0 if color == chess.WHITE else 7
        if chess.square_rank(ksq) != back:
            continue
        kf = chess.square_file(ksq)
        fwd = back + (1 if color == chess.WHITE else -1)
        blocked = True
        for f in (kf - 1, kf, kf + 1):
            if 0 <= f <= 7:
                sq = chess.square(f, fwd)
                p = board.piece_at(sq)
                if not (p and p.color == color and p.piece_type == chess.PAWN):
                    blocked = False
                    break
        heavy = bool(board.pieces(chess.QUEEN, not color)) or bool(board.pieces(chess.ROOK, not color))
        if blocked and heavy:
            if mine:
                findings.append(Finding(True, "weakness",
                    f"your king on {_sq(ksq)} has NO LUFT — boxed on the back rank by its own pawns; "
                    f"make an escape square (a quiet rook-pawn move) to avoid a back-rank mate",
                    wiki="luft"))
            else:
                findings.append(Finding(False, "potential",
                    f"opponent's king on {_sq(ksq)} has no luft (back-rank box) — a rook/queen reaching "
                    f"the back rank could be mate; look for it", wiki="forks"))
    return findings


def detect_all(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Run every detector. Returns all findings (side=True == side to move)."""
    findings: list[Finding] = []
    for fn in (detect_phase_fundamentals, detect_center_control,
               detect_pawn_structure, detect_files,
               detect_development, detect_bishop_pair, detect_outposts,
               detect_knight_forks, detect_piece_forks, detect_loose_pieces, detect_pins_skewers,
               detect_creatable_pins,
               detect_skewers, detect_discovered_attacks, detect_traps,
               detect_material, detect_king_safety, detect_overloaded_defenders,
               detect_removable_defender, detect_own_back_rank):
        try:
            findings += fn(board, perspective)
        except Exception:
            pass  # a detector must never crash the tool
    return findings


def why_stronger(board_before: chess.Board, move: chess.Move) -> list[str]:
    """After `move`, surface WHY a threat may be unanswerable — the "attacks the
    queen WHILE giving check, so it can't be defended" insight. Pure mechanics,
    framed as a prompt to verify, never a guarantee.

    Cases detected (resulting board, opponent to move):
      - CHECK + the moving piece also attacks a valuable undefended/▸winnable
        enemy piece → they must answer the check, so the attacked piece likely
        falls (a fork-with-check / discovered-double-threat).
      - The move gives CHECK and is itself safe → forcing; they can't ignore it.
      - The move attacks two pieces where the more valuable is the KING (any
        fork involving check) → only the king can be saved.
    The output is advisory: it tells the agent to confirm the opponent cannot
    meet both the check and the threat in one move (the soundness test).
    """
    out: list[str] = []
    b = board_before.copy()
    mover = b.piece_at(move.from_square)
    if mover is None:
        return out
    color = mover.color
    enemy = not color
    b.push(move)
    gives_check = b.is_check()  # enemy (side to move now) is in check
    if not gives_check:
        return out
    # what does the moved piece now attack? (and any enemy piece newly attacked)
    to_sq = move.to_square
    moved = b.piece_at(to_sq)
    if moved is None:
        return out
    enemy_king = b.king(enemy)
    attacked_valuable = []
    for tsq in b.attacks(to_sq):
        ep = b.piece_at(tsq)
        if ep and ep.color == enemy and ep.piece_type != chess.KING:
            # is it winnable? (undefended, or worth more than the attacker)
            defended = bool(b.attackers(enemy, tsq))
            if not defended or PIECE_VALUE[ep.piece_type] > PIECE_VALUE[moved.piece_type]:
                attacked_valuable.append((tsq, ep.piece_type, defended))
    if attacked_valuable:
        for tsq, pt, defended in attacked_valuable:
            note = "undefended" if not defended else "more valuable than your attacker"
            out.append(
                f"STRONG: this move gives CHECK *and* attacks the {PIECE_NAME[pt]} on {_sq(tsq)} "
                f"({note}) — the opponent must answer the check, so they likely can't save it. "
                f"Verify they can't block the check WITH a piece that also defends, or capture your "
                f"checking piece, in one move (see `tactics/discovered-attacks.md`).")
    else:
        # plain forcing check (no capture threat) — still note it's forcing
        # only if the checking piece is safe (not a free give-away).
        if not b.attackers(enemy, to_sq) or b.attackers(color, to_sq):
            out.append(
                "FORCING: this move gives check and the checking piece is safe — the opponent's reply "
                "is forced (move the king, block, or capture the checker), which can let you follow up "
                "with tempo.")
    return out


def _pawn_capture_opens_attack(board: chess.Board, mv: chess.Move) -> bool:
    """True if this pawn capture has a tactical point beyond winning a pawn: after
    it, the moving side attacks an enemy piece (>= minor) OR a square adjacent to the
    enemy king that it did NOT attack before (a line/diagonal opened by the capture,
    or the captured pawn was a defender). Pure mechanics — used to surface
    combination-starting pawn captures (clearance/attraction/line-opening) in the
    forcing-move list without flooding it with every pawn grab."""
    mover = board.turn
    enemy = not mover
    ek = board.king(enemy)
    def targets(b: chess.Board) -> set[int]:
        # squares the moving side attacks that hold an enemy minor+ OR are next to
        # the enemy king
        hit: set[int] = set()
        for sq in chess.SQUARES:
            p = b.piece_at(sq)
            valuable = p is not None and p.color == enemy and p.piece_type in (
                chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
            near_king = ek is not None and chess.square_distance(sq, ek) <= 1
            if (valuable or near_king) and b.attackers(mover, sq):
                hit.add(sq)
        return hit
    before = targets(board)
    after_b = board.copy(stack=False)
    after_b.push(mv)
    # recompute on the post-capture board but still from the mover's seat
    after_hit: set[int] = set()
    for sq in chess.SQUARES:
        p = after_b.piece_at(sq)
        valuable = p is not None and p.color == enemy and p.piece_type in (
            chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
        near_king = ek is not None and chess.square_distance(sq, ek) <= 1
        if (valuable or near_king) and after_b.attackers(mover, sq):
            after_hit.add(sq)
    return bool(after_hit - before)


def _forcing_moves_line(board: chess.Board) -> str:
    """List the side-to-move's forcing moves — CHECKS and meaningful CAPTURES
    (the C-C of Checks/Captures/Threats) — to calculate FIRST. Pure enumeration
    (board.gives_check / board.is_capture + piece values); no evaluation, no
    best-move pick — the agent still calculates which works. Delivered in the
    tool output at the decision point because SKILL.md prose alone does not move
    the model toward forcing moves; a list in front of it does.

    Captures matter as much as checks: a deflection/removing-the-defender
    combination often STARTS with a capture (e.g. Qxd8 to deflect the defender,
    then win a piece) that is NOT a check — listing only checks misses it."""
    checks, captures = [], []
    for mv in board.legal_moves:
        gives_check = board.gives_check(mv)
        is_cap = board.is_capture(mv)
        if not (gives_check or is_cap):
            continue
        try:
            san = board.san(mv)
        except Exception:
            continue
        if gives_check:
            checks.append(san)
        elif is_cap:
            # Surface captures of a real piece (>= minor). A bare pawn-grab is
            # usually not a "forcing move" — EXCEPT a LINE-OPENING / defender-
            # removing pawn capture that is the start of a combination (BLrYl:
            # exf6 opens the f-file for Rf7+; clearance/attraction motifs often
            # START with such a pawn capture). Include a pawn capture when it gives
            # the moving side a NEW attack on an enemy piece (>= minor) or on a
            # square next to the enemy king that it did not have before — i.e. it
            # has a tactical point, not just a pawn. Mechanics; the agent calculates.
            victim = board.piece_at(mv.to_square)
            vt = victim.piece_type if victim else chess.PAWN  # en-passant = pawn
            if vt != chess.PAWN:
                captures.append(san)
            elif _pawn_capture_opens_attack(board, mv):
                captures.append(san)
    if not checks and not captures:
        return ""
    # Order: capturing-checks (sharpest), other checks, then piece-captures.
    cap_checks = [c for c in checks if "x" in c]
    quiet_checks = [c for c in checks if "x" not in c]
    ordered = cap_checks + quiet_checks + captures
    # MATE-likely signal: if the enemy king has very few squares (it is in a
    # mating net) AND you have a check, a FORCED MATE is often available — the
    # commonest thing the agent misses (it won't enter a checking sac that mates).
    # Pure mechanics: count the enemy king's legal moves and whether it is boxed
    # on its back rank. This says "calculate for mate", never which move mates.
    ek = board.king(not board.turn)
    mate_hint = ""
    if ek is not None and checks:   # the mate hint is about checks; only with a check
        # count the enemy king's escape squares mechanically (give it the move)
        b2 = board.copy(stack=False)
        try:
            b2.push(chess.Move.null())
            esc = sum(1 for m in b2.legal_moves if m.from_square == ek)
        except Exception:
            esc = 9
        back = 7 if (not board.turn) == chess.BLACK else 0
        on_back = chess.square_rank(ek) == back
        if esc <= 2:
            mate_hint = (f" ⚠ The enemy king has only {esc} escape square(s)"
                         + (" and is on its back rank" if on_back else "")
                         + " — a FORCED MATE may be available. Calculate your checks to the END with "
                         "`chess__imagine_line` (a checking SACRIFICE that mates is worth any material — "
                         "read the leaf verdict for 'CHECKMATE'); don't stop because a check 'loses' material.")
    # Per-check BOXING marker: which individual checks trap the enemy king to <=1
    # escape square? The mate_hint above measures the king's CURRENT mobility, but a
    # king with escapes now can be boxed by a SPECIFIC check (1pYEx: the king on e8
    # is free, but Bb5+/Bg4+ box it to <=1 while Bh5+ leaves 2 — the agent picks a
    # non-boxing check and misses the mate). Mark the boxing ones with ↯ so the agent
    # calculates THOSE for mate. Count the king's legal moves after the check
    # directly (it is in check, its turn) — never a null move (illegal in check).
    boxing_checks: set[str] = set()
    for c in checks:
        try:
            mv = board.parse_san(c)
        except Exception:
            continue
        bc = board.copy(stack=False); bc.push(mv)
        ekc = bc.king(bc.turn)
        if ekc is None:
            continue
        esc_c = sum(1 for m in bc.legal_moves if m.from_square == ekc)
        if esc_c <= 1:
            boxing_checks.add(c)
    if boxing_checks and not mate_hint:
        blist = ", ".join(sorted(boxing_checks))
        mate_hint = (f" ↯ These check(s) BOX the enemy king to ≤1 escape square: {blist} — a FORCED "
                     f"MATE may start with one of them. Calculate EACH to the end with "
                     f"`chess__imagine_line` and read the leaf for 'CHECKMATE'; only one may mate, so "
                     f"don't stop after the first. A checking sacrifice that mates is worth any material.")
    def _mark(c):
        box = "↯" if c in boxing_checks else ""
        if c in cap_checks:
            return f"★{box}{c}"      # check that is also a capture (sharpest)
        if c in captures:
            return f"✛{c}"          # a capture (not a check)
        return f"{box}{c}"           # a quiet check (↯ if it boxes the king)
    return (
        "**Forcing moves — calculate these FIRST (★ = capturing check, ✛ = capture, ↯ = boxes the "
        "enemy king, rest = check):** "
        + ", ".join(_mark(c) for c in ordered)
        + ". Checks AND captures force the play — they are how most combinations work (a deflection or "
        "removing-the-defender often STARTS with a capture, not a check). Play each promising one out "
        "with `imagine_line`/`imagine_trade` BEFORE settling on a quiet or defensive move — a forcing "
        "move that wins beats saving a piece. (Listing them is mechanics; whether one wins is for you "
        "to calculate.)" + mate_hint
    )


def _in_check_line(board: chess.Board) -> str:
    """When the side to move is IN CHECK, list ALL its legal replies (escapes,
    blocks, captures of the checker) and tell it to calculate each. Legal moves
    are few in check, so calculating all is cheap — and the right one often is a
    BLOCK that wins material (interpose, get captured, recapture a bigger piece)
    or a specific escape square, both of which the agent routinely misses on
    defence. Pure mechanics (board.legal_moves while in check)."""
    if not board.is_check():
        return ""
    replies = []
    for mv in board.legal_moves:
        try:
            replies.append(board.san(mv))
        except Exception:
            pass
    if not replies:
        return ""
    # mark a block/capture (anything that isn't a king move) — those are the ones
    # the agent under-considers (it tends to just step the king aside).
    nonking = [r for r in replies if not r.startswith("K")]
    extra = (f" Of these, {', '.join(nonking)} are blocks/captures (NOT just running the king) — "
             f"a block that gets captured can WIN material on the recapture, so calculate them with "
             f"imagine_line, do not reflexively move the king." if nonking else "")
    return (
        f"**⚠ YOU ARE IN CHECK — you must answer it this move.** Your only legal replies are: "
        f"{', '.join(replies)}. They are few — calculate EACH (escape / block / capture the checker) "
        f"with imagine_line and pick the one that is best, not just the first safe-looking king move."
        + extra
    )


def render_features(board: chess.Board, *, heading: str = "Position assessment — strengths, weaknesses & ideas") -> str:
    """Full feature section for `board`, from the side-to-move's perspective."""
    findings = detect_all(board)
    body = render_findings(findings, agent_color=board.turn, heading=heading)
    # When in check, that line leads; otherwise the forcing-moves (CCT) line does.
    lead = _in_check_line(board) or _forcing_moves_line(board)
    if not lead:
        return body
    if not body:
        return f"## {heading}\n\n{lead}"
    # Insert the lead line right after the heading + method note so it is the
    # first concrete thing the agent reads.
    lines = body.split("\n")
    insert_at = 1
    for i, ln in enumerate(lines):
        if ln.startswith("_Full method"):
            insert_at = i + 1
            break
    lines.insert(insert_at, f"\n{lead}")
    return "\n".join(lines)


def render_features_for(board: chess.Board, perspective: bool, *, heading: str) -> str:
    """Like render_features but framed from `perspective`'s seat even when it is
    NOT that side's turn (used by imagine_move/line, where the resulting board
    has the opponent to move but findings should read as the agent's own).

    Detection runs with the explicit perspective, so YOURS/OPPONENT and the
    second-person text are already correct. We drop the phase/development
    fundamentals here — those are a current-position (show_position) concern, not
    an after-the-move one; imagine focuses on the tactical/structural change."""
    findings = [f for f in detect_all(board, perspective=perspective)
                if f.kind != "fundamental"]
    # In the resulting position it is the OTHER side to move, so any "consider
    # these moves" list (generated from board.legal_moves) would be the opponent's
    # moves, not the agent's — suppress them here; the agent re-runs the tools on
    # its own turn for move suggestions.
    if perspective != board.turn:
        for f in findings:
            f.moves = []
    return render_findings(findings, agent_color=perspective, heading=heading)


def render_findings(findings: list[Finding], *, agent_color: bool, heading: str) -> str:
    """Render findings to a markdown section, split into YOURS vs OPPONENT.

    `agent_color`: which colour the *reader* is (so "YOURS" is always the agent).
    Findings are tagged by side-to-move at detection time; we re-map to the
    reader here. (When detection ran with board.turn == agent_color, side=True is
    the agent. We pass agent_color so imagine_move — which may show the opponent's
    move — labels correctly.)
    """
    if not findings:
        return ""
    yours = [f for f in findings if f.side]
    theirs = [f for f in findings if not f.side]
    out = [f"## {heading}"]
    # Always point to the assessment-method page and (for quiet positions) the
    # prophylaxis/convert pages — so 'evaluate-position' and 'prophylaxis' are
    # reachable from every assessment, not only when a specific detector fires.
    out.append(
        f"_Full method: read `{WIKI['evaluate']}`. Quiet position with no forcing "
        f"move? read `{WIKI['prophylaxis']}`. These are suggestions — you are free "
        f"to calculate your own ideas and read further on your own._")

    def block(title: str, items: list[Finding]) -> None:
        if not items:
            return
        out.append(f"\n**{title}**")
        # order: free material first (win it now) / losing material first (save
        # it now), then threats, weaknesses, strengths, potentials, fundamentals.
        # `win` (your opportunity) and `lose` (the mirror warning) are the two
        # highest-priority kinds — symmetric: the same logic that finds a free
        # enemy piece for you also warns when YOUR piece is the free one.
        order = {"win": 0, "lose": 0, "threat": 1, "weakness": 2, "strength": 3,
                 "potential": 4, "fundamental": 5}
        for f in sorted(items, key=lambda x: order.get(x.kind, 9)):
            tag = {"win": "★ WIN MATERIAL", "lose": "⛔ LOSING MATERIAL", "threat": "⚠ THREAT",
                   "weakness": "weakness", "strength": "strength", "potential": "potential",
                   "fundamental": "fundamental"}.get(f.kind, f.kind)
            line = f"- [{tag}] {f.text}"
            if f.moves:
                line += f"  → consider: {', '.join(f.moves)} (calculate these with imagine_move/imagine_line)"
            if f.wiki:
                line += f"  · read `{WIKI.get(f.wiki, f.wiki)}`"
            out.append(line)

    block("YOURS (you are " + _color_word(agent_color) + ")", yours)
    block("OPPONENT — watch for these", theirs)
    return "\n".join(out)


if __name__ == "__main__":
    # smoke
    b = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
    fs = [Finding(True, "potential", "the d-file is half-open for you", ["Rd1"], "piece_activity")]
    print(render_findings(fs, agent_color=chess.WHITE, heading="Position features"))
