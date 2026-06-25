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
    for mv in board.legal_moves:
        victim = board.piece_at(mv.to_square)
        if victim is None or victim.piece_type == chess.KING:
            continue  # not a capture (en-passant handled below is rare; skip)
        after = board.copy(); after.push(mv)
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
            #  - the king plus a piece the knight can then PROFITABLY take, i.e.
            #    the other target is undefended (else the king moves and the
            #    defended piece survives — a K+minor "fork" that wins nothing).
            heavy = [k for k in kinds if k in (chess.QUEEN, chess.ROOK)]
            king_plus_loose = (
                chess.KING in kinds and
                any(t for t in hit if targets[t] != chess.KING and
                    not board.attackers(enemy, t))   # the other target is undefended
            )
            worth_it = len(heavy) >= 2 or (chess.KING in kinds and len(heavy) >= 1) \
                or king_plus_loose
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
                    findings.append(Finding(True, "threat",
                        f"your {PIECE_NAME[p.piece_type]} on {_sq(sq)} is attacked and UNDEFENDED — "
                        f"defend it, move it to safety, or counter with a bigger threat",
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
                                f"behind) — calculate it", wiki="pins"))
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
                        desc = (f"your {PIECE_NAME[sp.piece_type]} on {_sq(screen)} screens your "
                                f"{PIECE_NAME[bp.piece_type]} on {_sq(back_sq)} from the enemy "
                                f"{PIECE_NAME[tp.piece_type]} on {_sq(target)} — moving it discovers an "
                                f"attack while the mover makes its own threat (two threats at once)")
                        f = Finding(True, "potential", desc, wiki="discovered")
                        if movers:
                            f.moves = movers[:6]
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

def detect_phase_fundamentals(board: chess.Board, perspective: bool | None = None) -> list[Finding]:
    """Name the phase and point to its fundamentals page. Auto-load by phase is
    the agent reading the page the radar names.

    Phase is decided by MATERIAL first (few pieces => endgame regardless of move
    number, since puzzle/constructed positions start at move 1), then by
    development/move-number for opening vs middlegame."""
    n_pieces = chess.popcount(board.occupied)
    queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
    minors_majors = sum(len(board.pieces(pt, c))
                        for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
                        for c in (chess.WHITE, chess.BLACK))
    # Endgame: few pieces, or queens off with little else.
    if n_pieces <= 12 or minors_majors <= 6:
        return [Finding(True, "fundamental",
            "ENDGAME phase — activate your king, push passed pawns (rook behind them), keep your mating piece",
            wiki="fund_endgame")]
    # Opening: still early AND back rank not yet cleared (pieces undeveloped).
    home_minors = sum(1 for c in (chess.WHITE, chess.BLACK)
                      for sq in _HOME[c]
                      if board.piece_at(sq) and board.piece_at(sq).color == c and
                      board.piece_at(sq).piece_type in (chess.KNIGHT, chess.BISHOP))
    if board.fullmove_number <= 10 and home_minors >= 3:
        return [Finding(True, "fundamental",
            "OPENING phase — develop every piece toward the centre, control the centre, castle",
            wiki="fund_opening")]
    return [Finding(True, "fundamental",
        "MIDDLEGAME phase — assess both sides, attack the king or a weakness, keep pieces active and safe",
        wiki="fund_middlegame")]


# ============================================================================
# TOP-LEVEL ASSEMBLER
# ============================================================================

def _material_count(board: chess.Board, color: bool) -> int:
    return sum(PIECE_VALUE[pt] * len(board.pieces(pt, color))
               for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN))


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
    for fn in (detect_phase_fundamentals, detect_pawn_structure, detect_files,
               detect_development, detect_bishop_pair, detect_outposts,
               detect_knight_forks, detect_loose_pieces, detect_pins_skewers,
               detect_creatable_pins,
               detect_skewers, detect_discovered_attacks, detect_traps,
               detect_material, detect_king_safety, detect_overloaded_defenders,
               detect_own_back_rank):
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


def _forcing_moves_line(board: chess.Board) -> str:
    """List the side-to-move's CHECKS (and which are also captures) as the
    forcing moves to calculate FIRST. Pure enumeration of legal checks — no
    evaluation, no best-move pick (usually several; the agent still calculates
    which works). Delivered in the tool output, at the decision point, because
    SKILL.md prose alone does not move the model toward forcing moves; a list in
    front of it does. Tool-fair mechanics (board.gives_check)."""
    checks = []
    for mv in board.legal_moves:
        if board.gives_check(mv):
            try:
                san = board.san(mv)
            except Exception:
                continue
            checks.append(san)
    if not checks:
        return ""
    # Captures-that-check are the sharpest — surface them, then the rest.
    cap_checks = [c for c in checks if "x" in c]
    quiet_checks = [c for c in checks if "x" not in c]
    ordered = cap_checks + quiet_checks
    return (
        "**Forcing moves — calculate these FIRST (checks; ★ = also a capture):** "
        + ", ".join((f"★{c}" if c in cap_checks else c) for c in ordered)
        + ". A check forces the reply, so it is how most combinations work — play "
        "each promising one out with `imagine_line` (check → forced reply → your "
        "follow-up) BEFORE settling on a quiet move. Many wins are 'check first, "
        "then win material'. (Listing the checks is mechanics; whether one wins is "
        "for you to calculate.)"
    )


def render_features(board: chess.Board, *, heading: str = "Position assessment — strengths, weaknesses & ideas") -> str:
    """Full feature section for `board`, from the side-to-move's perspective."""
    findings = detect_all(board)
    body = render_findings(findings, agent_color=board.turn, heading=heading)
    forcing = _forcing_moves_line(board)
    if not forcing:
        return body
    if not body:
        return f"## {heading}\n\n{forcing}"
    # Insert the forcing-moves line right after the heading + method note so it is
    # the first concrete thing the agent reads.
    lines = body.split("\n")
    # find the method-note paragraph (starts with "_Full method"); insert after it
    insert_at = 1
    for i, ln in enumerate(lines):
        if ln.startswith("_Full method"):
            insert_at = i + 1
            break
    lines.insert(insert_at, f"\n{forcing}")
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
        # order: free material first (win it now), then threats, weaknesses,
        # strengths, potentials, fundamentals.
        order = {"win": 0, "threat": 1, "weakness": 2, "strength": 3, "potential": 4, "fundamental": 5}
        for f in sorted(items, key=lambda x: order.get(x.kind, 9)):
            tag = {"win": "★ WIN MATERIAL", "threat": "⚠ THREAT", "weakness": "weakness",
                   "strength": "strength", "potential": "potential",
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
