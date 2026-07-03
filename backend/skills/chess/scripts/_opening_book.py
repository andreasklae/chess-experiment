"""The London System opening book — TUTOR-AUTHORED, prepared in advance.

The chess equivalent of a human memorising opening theory: a finite, static body of
*known* opening knowledge the tutor wrote down, NOT a live engine search. It answers
only for positions it recognises; otherwise it returns nothing (the caller routes the
agent to the theory pages / its own calculation). It NEVER calls an engine.

Fairness (tool-fairness rulebook): a precomputed repertoire is prepared knowledge, the
same class as the wiki — "what we taught the agent to memorise", finite and auditable.
The forbidden thing is a tool that *searches/evaluates to pick a move in an arbitrary
position*; this does neither. Out of book = no move.

TWO LAYERS, because the London is a SETUP, not a line (exact-position matching alone
covers only ~40% of real games — Black reaches the same structures by many move orders):

  1. EXACT LINES — for positions where the specific move matters and a generic rule
     would get it wrong (e.g. the ...Qb6 response is move-order-dependent: Qb3 only
     works once c3 is in). Matched by a move-order-independent position key.
  2. SETUP RULES — "play the London setup unless a trigger fires". Each rule is a
     CONDITION on a few squares (not the whole board) → a move + idea. Broad rules for
     the routine setup moves (Bf4, e3, Nf3, c3, Nbd2, O-O), narrow triggers for the
     exceptions (...Qb6 on b2, ...g6 fianchetto, ...Nh5 hitting the bishop). This is
     how a human actually "knows" the London: the structure, with a few gotchas.

Lookup order: exact line first (most specific), then the first matching setup rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import chess

# ── Layer 1: exact lines ─────────────────────────────────────────────────────────
# (line name, idea behind White's moves, [SAN moves from start, W/B alternating])
LINES: list[tuple[str, str, list[str]]] = [
    ("London main setup",
     "the London setup — bishop OUTSIDE the pawn chain on f4, then e3/Nf3/Bd3/c3/Nbd2, "
     "castle, aim a knight at e5",
     ["d4", "d5", "Bf4", "Nf6", "e3", "e6", "Nf3", "Bd6", "Bg3", "O-O",
      "Bd3", "c5", "c3", "Nc6", "Nbd2", "b6", "O-O"]),
    ("London vs ...Qb6 (no c3 yet)",
     "b2 is loose and Qb3 is NOT available yet (queen blocked) — defend with Qc1",
     ["d4", "d5", "Bf4", "c5", "e3", "Qb6", "Qc1"]),
    ("London vs ...Qb6 (after c3)",
     "c3 is in, so Qb3 IS available — offer the queen trade to end the b2 pressure",
     ["d4", "d5", "Bf4", "Nf6", "e3", "c5", "c3", "Qb6", "Qb3"]),
    ("London vs ...g6 (King's Indian setup)",
     "vs the fianchetto put the light bishop on e2 (NOT d3) and play h3 early so Bf4 "
     "can retreat to h2",
     ["d4", "Nf6", "Bf4", "g6", "e3", "Bg7", "Nf3", "O-O", "Be2", "d6",
      "h3", "c5", "c3", "Nc6", "O-O"]),
]


def position_key(board: chess.Board) -> str:
    """Move-order-independent key: placement + side-to-move + castling + ep (the fields
    a position is genuinely defined by; clocks excluded so transpositions collapse)."""
    return " ".join(board.fen().split(" ")[:4])


@dataclass
class BookEntry:
    moves: list[str] = field(default_factory=list)   # candidate book move SAN(s), best-first
    line: str = ""
    idea: str = ""
    source: str = "line"                             # "line" or "rule"
    assumes: str = ""                                # the condition under which this is book
    exceptions: str = ""                             # when NOT to play it / reason yourself
    wiki: str = ""                                   # the London page to reason from


def _build_exact() -> dict[str, BookEntry]:
    book: dict[str, BookEntry] = {}
    for name, idea, sans in LINES:
        b = chess.Board()
        for san in sans:
            white = b.turn == chess.WHITE
            try:
                mv = b.parse_san(san)
            except Exception as exc:
                raise ValueError(f"illegal book move {san!r} in line {name!r}: {exc}")
            if white:
                e = book.setdefault(position_key(b), BookEntry(source="line"))
                bsan = b.san(mv)
                if bsan not in e.moves:
                    e.moves.append(bsan)
                if not e.line:
                    e.line, e.idea = name, idea
                    e.assumes = ("this is a known main-line London position reached by "
                                 "standard moves")
                    e.exceptions = ("if the opponent has deviated or a tactic is on the "
                                    "board, the theory move may not fit — verify it still "
                                    "makes sense before playing it")
                    e.wiki = "openings/london-system"
            b.push(mv)
    return book


EXACT_BOOK: dict[str, BookEntry] = _build_exact()


# ── Layer 2: setup rules ─────────────────────────────────────────────────────────
# A rule = a predicate on the board (a CONDITION on a few squares) + the book move it
# yields + the line name/idea. Rules are tried in order; the FIRST whose predicate
# holds AND whose move is legal wins. "How specific" is per-rule: triggers (the
# exceptions) check a few squares; setup moves check only that the piece isn't placed
# yet and the move is available. Mechanics only — no search.

def _has(board, piece_type, color, square) -> bool:
    p = board.piece_at(square)
    return p is not None and p.piece_type == piece_type and p.color == color

def _black_pawn(board, square) -> bool:
    return _has(board, chess.PAWN, chess.BLACK, square)


def _legal_san(board: chess.Board, san: str) -> str | None:
    """Return the SAN if it is legal in this position, else None."""
    try:
        mv = board.parse_san(san)
    except Exception:
        return None
    return board.san(mv) if mv in board.legal_moves else None


# Every rule carries, besides the candidate move(s): the ASSUMPTIONS under which it is
# book, and the EXCEPTIONS where the agent should reason for itself (from the London
# pages) rather than reflexively playing the move. The tool presents all of this so the
# AGENT DECIDES — a real repertoire move comes with its conditions, not as an oracle.
@dataclass
class Rule:
    name: str
    idea: str
    predicate: object            # Callable[[chess.Board], bool]
    candidates: list[str]        # reasonable moves, best-first — the agent picks among them
    assumes: str = ""            # the condition under which these are book
    exceptions: str = ""         # when NOT to play them / reason yourself
    wiki: str = ""               # the London page to reason from


W = chess.WHITE
B = chess.BLACK

# Assumptions/exceptions shared by the routine setup moves.
_SETUP_ASSUMES = ("a quiet opening position where you are still completing the London "
                  "structure and nothing forcing is happening")
_SETUP_EXCEPT = ("if a check, a winning capture, a real threat against you, or a clearly "
                 "better developing move is available, play THAT — the setup move is only "
                 "right when the position is genuinely quiet")

SETUP_RULES: list[Rule] = [
    # --- CENTRE RECAPTURE (most fundamental: take back the d4 pawn) ---
    Rule("London — recapture on d4",
         "Black captured your d4-pawn (…cxd4/…exd4); recapture to keep the strong "
         "London centre. This is core theory, not a free choice to develop instead.",
         lambda bd: bool(_sound_d4_recaptures(bd)),
         # candidates are filled dynamically by _rule_lookup from the predicate; we list
         # the usual two here so the rule is self-describing, but the lookup recomputes
         # the actually-legal, sound ones for THIS position.
         ["exd4", "cxd4"],
         assumes=("Black just took on d4 and you can recapture soundly. Recapturing keeps "
                  "your centre — the point of the London. If BOTH exd4 and cxd4 are legal, "
                  "they lead to different structures: exd4 opens the e-file (the Carlsbad "
                  "setup, knight later to d3); cxd4 keeps the c-file. Pick by the structure "
                  "you want"),
         exceptions=("recapture UNLESS a stronger forcing move (a check, or a capture that "
                     "wins more) is available, or the recapture itself loses material to a "
                     "tactic — then calculate. Normally, take back the pawn"),
         wiki="openings/london-central-break"),
    Rule("London — recapture a traded minor",
         "Black captured a developed White minor on its key square — the dark bishop on "
         "f4/g3 (…Bxf4 / …Nxg3) or the light bishop on d3 (…Bxd3). Recapture — it is a "
         "normal trade and how you recapture shapes the structure.",
         lambda bd: _traded_minor_recapture_square(bd) is not None
                    and bool(_sound_recaptures_on(bd, _traded_minor_recapture_square(bd))),
         ["exf4"],  # recomputed dynamically in _rule_lookup
         assumes=("Black traded a developed minor and you retake. A PAWN recapture often "
                  "shapes the game: exf4 gives doubled f-pawns that STRENGTHEN the e5 outpost "
                  "and hand your knights d4/e5; hxg3 (after …Nxg3) opens the h-file. For …Bxd3, "
                  "Qxd3 is the natural retake (keeps the pawns healthy); cxd3 only if you want "
                  "the half-open c-file. Pick by the structure you want"),
         exceptions=("if a different recapture is clearly better (keeps the pawns healthy, or "
                     "a zwischenzug/tactic wins more), take that instead — calculate"),
         wiki="openings/london-central-break"),
    Rule("London — dark bishop hit by a pawn",
         "A Black pawn attacks your f4/g3 dark-squared bishop (…e5, …g5). React now — "
         "challenge the pawn or retreat the bishop; don't play a routine setup move and "
         "lose it.",
         lambda bd: _dark_bishop_pawn_attacked_square(bd) is not None
                    and bool(_dark_bishop_pawn_attack_responses(bd)),
         ["Bg3"],  # recomputed dynamically in _rule_lookup
         assumes=("your dark bishop (the London's best minor) is attacked by a pawn. "
                  "Challenge the attacking pawn with a sound capture (e.g. dxe5), or retreat "
                  "the bishop to a safe diagonal square (Bg3/Bh2 if h3 is in, or Bg5). Do NOT "
                  "capture with the bishop into a pawn recapture (e.g. Bxe5 …dxe5 loses it)"),
         exceptions=("if a check, or a capture/tactic that wins more, is available, take "
                     "THAT instead. And which reply is best depends on the structure — read "
                     "the page (vs a ...g6/…d6 King's-Indian setup, Bh2 after h3 is the "
                     "standard tuck-away)"),
         wiki="openings/london-vs-kings-indian"),
    # --- EXCEPTION TRIGGERS (specific, checked first) ---
    Rule("London vs ...Qb6 — b2 under fire",
         "Black's queen eyes the loose b2-pawn.",
         lambda bd: _has(bd, chess.QUEEN, B, chess.B6)
                    and bool(bd.attackers(B, chess.B2)),
         ["Qb3", "Qc1", "b3"],
         assumes=("Black has just brought the queen to b6 hitting b2 in a still-standard "
                  "London structure. Qb3 (offering the queen trade) needs c3 already "
                  "played — otherwise the queen can't reach b3, so use Qc1 or b3"),
         exceptions=("if the queen has been on b6 for a while and the position has moved "
                     "on (pieces developed, files opened, a tactic in the air), Qb3 is "
                     "OFTEN NO LONGER RIGHT — it can be a positional blunder. Do not play "
                     "it reflexively: weigh Qb3/Qc1/b3 against a better developing move or "
                     "a tactic, using the page. If ...c5 came BEFORE your c3, a sharper "
                     "gambit (Nc3 and if ...Qxb2 then Nb5) or dxc5 is also playable — see "
                     "openings/london-vs-early-c5"),
         wiki="openings/london-vs-qb6"),
    Rule("London vs ...Nh5 — save the dark bishop",
         "Black's ...Nh5 attacks your f4/g3 dark-squared bishop (a key London piece).",
         lambda bd: _has(bd, chess.KNIGHT, B, chess.H5)
                    and (bool(bd.attackers(B, chess.F4)) or bool(bd.attackers(B, chess.G3))),
         ["Bh2", "Bg5", "Bg3"],
         assumes=("your dark bishop is attacked and worth keeping. Bh2 is safest once h3 "
                  "is in; Bg5 keeps it active; allowing ...Nxg3 hxg3 trades it for the "
                  "open h-file"),
         exceptions=("if Bg5 runs into ...f6/...h6 kicking it, or a queen+bishop battery "
                     "eyes g5, prefer Bh2 / the hxg3 trade. And if a tactic is available, "
                     "the bishop's safety is secondary — take the tactic"),
         wiki="openings/london-vs-nh5"),
    Rule("London vs ...g6 — develop with Be2 not Bd3",
         "Black is fianchettoing (...g6, King's Indian setup).",
         lambda bd: _black_pawn(bd, chess.G6)
                    and not _has(bd, chess.BISHOP, W, chess.D3)
                    and not _has(bd, chess.BISHOP, W, chess.E2)
                    and _has(bd, chess.BISHOP, W, chess.F1),
         ["Be2"],
         assumes=("vs the ...g6 wall a bishop on d3 has little scope, so Be2 is the "
                  "developing square; get h3 in too so Bf4 can retreat to h2"),
         exceptions=("this is a preference, not forced — if a concrete tactic or a more "
                     "active developing move fits the position, use it"),
         wiki="openings/london-vs-kings-indian"),
    # --- ROUTINE SETUP MOVES (broad; "play the London structure") ---
    Rule("London setup — bishop out to f4",
         "Get the dark-squared bishop OUTSIDE the pawn chain (f4) before playing e3.",
         lambda bd: _has(bd, chess.PAWN, W, chess.D4)
                    and _has(bd, chess.BISHOP, W, chess.C1)
                    and not _black_pawn_attacks_f4(bd),
         ["Bf4"],
         assumes=_SETUP_ASSUMES, exceptions=_SETUP_EXCEPT, wiki="openings/london-system"),
    Rule("London setup — e3",
         "Support d4 and free the f1-bishop.",
         lambda bd: _bishop_developed_dark(bd)
                    and _has(bd, chess.PAWN, W, chess.E2)
                    and not _has(bd, chess.KNIGHT, W, chess.F3),
         ["e3"],
         assumes=_SETUP_ASSUMES, exceptions=_SETUP_EXCEPT, wiki="openings/london-system"),
    Rule("London setup — Nf3",
         "Develop the king's knight; it heads for e5 later.",
         lambda bd: _bishop_developed_dark(bd)
                    and not _has(bd, chess.PAWN, W, chess.E2)   # e3 played
                    and _has(bd, chess.KNIGHT, W, chess.G1),
         ["Nf3"],
         assumes=_SETUP_ASSUMES, exceptions=_SETUP_EXCEPT, wiki="openings/london-system"),
    Rule("London setup — Bd3",
         "Develop the light bishop to d3 (aims at h7).",
         lambda bd: _has(bd, chess.KNIGHT, W, chess.F3)
                    and _has(bd, chess.BISHOP, W, chess.F1)
                    and not _black_pawn(bd, chess.G6),
         ["Bd3"],
         assumes=_SETUP_ASSUMES,
         exceptions=(_SETUP_EXCEPT + "; and use Be2 instead of Bd3 vs a ...g6 fianchetto"),
         wiki="openings/london-system"),
    Rule("London setup — c3",
         "Support d4 with c3 (the third side of the triangle).",
         lambda bd: _bishop_developed_dark(bd)
                    and not _has(bd, chess.PAWN, W, chess.E2)   # e3 in
                    and _has(bd, chess.PAWN, W, chess.C2)
                    and not _has(bd, chess.KNIGHT, W, chess.C3),
         ["c3"],
         assumes=_SETUP_ASSUMES, exceptions=_SETUP_EXCEPT, wiki="openings/london-system"),
    Rule("London setup — Nbd2",
         "Develop the queen's knight to d2 (supports e4/Ne5, keeps the c-pawn free).",
         lambda bd: _has(bd, chess.KNIGHT, W, chess.B1)
                    and _has(bd, chess.KNIGHT, W, chess.F3)
                    and bd.piece_at(chess.D2) is None,
         ["Nbd2"],
         assumes=_SETUP_ASSUMES, exceptions=_SETUP_EXCEPT, wiki="openings/london-system"),
    Rule("London setup — castle short",
         "Get the king safe — castle kingside once the kingside is developed.",
         lambda bd: bd.has_kingside_castling_rights(W)
                    and _has(bd, chess.KNIGHT, W, chess.F3)
                    and bd.piece_at(chess.F1) is None
                    and bd.piece_at(chess.G1) is None,
         ["O-O"],
         assumes=_SETUP_ASSUMES, exceptions=_SETUP_EXCEPT, wiki="openings/london-system"),
]


def _black_pawn_attacks_f4(board: chess.Board) -> bool:
    return bool(board.attackers(B, chess.F4) & board.pieces(chess.PAWN, B))


def _bishop_developed_dark(board: chess.Board) -> bool:
    """The dark-squared bishop is out of c1 (on f4/g3/h2/e5/d2/g5 — i.e. developed)."""
    return not _has(board, chess.BISHOP, W, chess.C1) and bool(
        board.pieces(chess.BISHOP, W))


def _sound_d4_recaptures(board: chess.Board) -> list[str]:
    """If Black has just captured a White pawn on d4 (…cxd4 / …exd4), return White's
    SOUND pawn recaptures (exd4 and/or cxd4), best-first. Recapturing to keep the strong
    London centre is core theory, not improvisation — so this must be BOOK, not left to
    the agent to find. Sound = a static-exchange recapture that doesn't lose material.
    Empty list if there's no Black pawn on d4 or no sound recapture."""
    p = board.piece_at(chess.D4)
    if not (p and p.piece_type == chess.PAWN and p.color == chess.BLACK):
        return []
    try:
        from _eval import static_exchange_eval
    except Exception:
        static_exchange_eval = None
    outs: list[str] = []
    for mv in board.legal_moves:
        if mv.to_square != chess.D4:
            continue
        mover = board.piece_at(mv.from_square)
        if not mover or mover.piece_type != chess.PAWN:
            continue
        if static_exchange_eval is not None:
            try:
                if static_exchange_eval(board, chess.D4, W) < 0:
                    continue  # recapture loses material — not sound
            except Exception:
                pass
        try:
            outs.append(board.san(mv))
        except Exception:
            pass
    # prefer exd4 (opens the e-file, the common Carlsbad recapture) first when both exist
    outs.sort(key=lambda s: (not s.startswith("exd4"), s))
    return outs


def _traded_minor_recapture_square(board: chess.Board):
    """If Black has just CAPTURED a developed White MINOR on one of its key London
    squares — the dark bishop on f4/g3/h2 (…Bxf4, …Nxg3) or the light bishop on d3
    (…Bxd3) — and a Black piece now sits there attacked by White, return that square;
    else None. (The square holds the Black capturer; White retakes.)"""
    for sq in (chess.F4, chess.G3, chess.H2, chess.D3):
        occ = board.piece_at(sq)
        if occ is None or occ.color != B:
            continue
        if board.attackers(W, sq):
            return sq
    return None


def _sound_recaptures_on(board: chess.Board, sq: int) -> list[str]:
    """White's SOUND recaptures of the Black piece on `sq` (SEE ≥ 0), best-first.
    Ordering is square-aware: on the DARK-bishop squares (f4/g3/h2) a PAWN recapture is
    the point (exf4/hxg3 shape the structure / open a file), so pawns first; on d3 the
    QUEEN retake keeps the pawns healthy, so pieces first."""
    if board.piece_at(sq) is None or board.piece_at(sq).color != B:
        return []
    pawns_first = sq in (chess.F4, chess.G3, chess.H2)
    try:
        from _eval import static_exchange_eval
    except Exception:
        static_exchange_eval = None
    pawns, pieces = [], []
    for mv in board.legal_moves:
        if mv.to_square != sq:
            continue
        if static_exchange_eval is not None:
            try:
                if static_exchange_eval(board, sq, W) < 0:
                    continue
            except Exception:
                pass
        mover = board.piece_at(mv.from_square)
        try:
            san = board.san(mv)
        except Exception:
            continue
        (pawns if mover and mover.piece_type == chess.PAWN else pieces).append(san)
    return (pawns + pieces) if pawns_first else (pieces + pawns)


def _dark_bishop_pawn_attacked_square(board: chess.Board):
    """If Black has a PAWN attacking the London dark-squared bishop (on f4/g3/h2) and the
    bishop is not defended enough to be safe there, return the bishop's square; else None.
    This is the …e5 / …g5 / …e5-hitting-f4 case — White must react (challenge or retreat),
    not play a routine setup move."""
    for sq in (chess.F4, chess.G3, chess.H2):
        p = board.piece_at(sq)
        if not (p and p.piece_type == chess.BISHOP and p.color == W):
            continue
        pawn_attackers = board.attackers(B, sq) & board.pieces(chess.PAWN, B)
        if pawn_attackers:
            return sq
    return None


def _dark_bishop_pawn_attack_responses(board: chess.Board) -> list[str]:
    """Candidate replies when a Black pawn attacks the London dark bishop: a sound pawn
    CHALLENGE of the attacker (e.g. dxe5 breaking the pawn that hits f4), then safe bishop
    RETREATS (Bg3/Bh2/Bg5/Be3/Bd2), best-first. Never a capture that loses the bishop
    (e.g. Bxe5 answered by …dxe5) — those are filtered by SEE. Empty if not applicable."""
    bsq = _dark_bishop_pawn_attacked_square(board)
    if bsq is None:
        return []
    try:
        from _eval import static_exchange_eval
    except Exception:
        static_exchange_eval = None
    challenges, retreats = [], []
    safe_retreat_sqs = {chess.G3, chess.H2, chess.G5, chess.E3, chess.D2}
    for mv in board.legal_moves:
        pc = board.piece_at(mv.from_square)
        if pc is None:
            continue
        # a pawn capture that removes/challenges the attacking pawn structure
        if pc.piece_type == chess.PAWN and board.is_capture(mv):
            if static_exchange_eval is not None:
                try:
                    if static_exchange_eval(board, mv.to_square, W) < 0:
                        continue
                except Exception:
                    pass
            try:
                challenges.append(board.san(mv))
            except Exception:
                pass
        # a safe retreat of the attacked bishop
        elif mv.from_square == bsq and pc.piece_type == chess.BISHOP \
                and mv.to_square in safe_retreat_sqs:
            after = board.copy(stack=False); after.push(mv)
            # the retreat square must not itself be attacked by a pawn / lose the bishop
            if static_exchange_eval is not None:
                try:
                    if static_exchange_eval(after, mv.to_square, not W) >= 150:
                        continue
                except Exception:
                    pass
            try:
                retreats.append(board.san(mv))
            except Exception:
                pass
    # challenges (dxe5…) first, then retreats; de-dup preserving order
    seen, ordered = set(), []
    for s in challenges + retreats:
        if s not in seen:
            seen.add(s); ordered.append(s)
    return ordered


def _strong_tactic_available(board: chess.Board) -> bool:
    """Is there a DECISIVE forcing tactic a player would always take over their opening
    prep? — a mate-in-1, or a capture/sequence winning at least a MINOR PIECE (>= ~300cp
    by static exchange). If so, the SETUP RULES stay silent: a book that says 'play c3'
    while Qh7# (or a free knight) is on the board would mislead. We deliberately do NOT
    defer for a mere 1-pawn grab — in the opening, a small SEE pawn-win (e.g. the f4
    bishop snatching c7) is usually worse than completing development, so the book
    should still give the setup move. Pure mechanics (legal-move scan + SEE), NOT an
    engine search."""
    try:
        from _eval import static_exchange_eval, MATERIAL
    except Exception:
        static_exchange_eval = None; MATERIAL = {}
    mover = board.turn
    for mv in board.legal_moves:
        if board.gives_check(mv):
            c = board.copy(stack=False); c.push(mv)
            if c.is_checkmate():
                return True
        if board.is_capture(mv) and static_exchange_eval is not None:
            # Net material for the MOVER = value captured minus what the opponent wins
            # back on the recapture sequence (SEE from the OPPONENT's seat on that square,
            # after the capture). >0 means a genuine winning capture for us. (The earlier
            # version had the sign wrong: a high opponent-SEE means the capture LOSES.)
            victim = board.piece_at(mv.to_square)
            vval = MATERIAL.get(victim.piece_type, 0) if victim else 100  # ep = pawn
            c = board.copy(stack=False); c.push(mv)
            try:
                recapture = max(0, static_exchange_eval(c, mv.to_square, not mover))
            except Exception:
                recapture = 0
            if vval - recapture >= 300:   # nets at least a minor piece
                return True
    return False


# Rules whose move IS a forced reaction to what Black just did (recapture a piece Black
# took, or answer a pawn attack on the bishop). These must NOT be suppressed by the
# tactic-guard: their "winning capture" SEE is just restoring material / the reaction
# itself — that is exactly the move theory wants, not a bonus tactic to defer for.
_REACTION_RULES = {
    "London — recapture on d4",
    "London — recapture a traded minor",
    "London — dark bishop hit by a pawn",
}


def _rule_candidates(board: chess.Board, r: "Rule") -> list[str]:
    """The rule's legal, sound candidates for THIS position (dynamic for the reaction
    rules that need SAN disambiguation / SEE filtering, static otherwise)."""
    if r.name == "London — recapture on d4":
        return _sound_d4_recaptures(board)
    if r.name == "London — recapture a traded minor":
        sq = _traded_minor_recapture_square(board)
        return _sound_recaptures_on(board, sq) if sq is not None else []
    if r.name == "London — dark bishop hit by a pawn":
        return _dark_bishop_pawn_attack_responses(board)
    legal: list[str] = []
    for san in r.candidates:
        good = _legal_san(board, san)
        if good and good not in legal:
            legal.append(good)
    return legal


def _mate_in_1_available(board: chess.Board) -> bool:
    """A forced mate-in-1 for the side to move — the one thing that beats even a
    recapture. (The reaction rules bypass the material tactic-guard, but a mate still
    wins.)"""
    for mv in board.legal_moves:
        if board.gives_check(mv):
            c = board.copy(stack=False); c.push(mv)
            if c.is_checkmate():
                return True
    return False


def _rule_lookup(board: chess.Board) -> BookEntry | None:
    # 1) REACTION rules first — a recapture / answer to a pawn attack is the forcing move
    #    theory wants; it must not be suppressed by the material tactic-guard (that guard
    #    would misread the recapture itself as a "winning capture"). A MATE-in-1 still wins.
    mate1 = _mate_in_1_available(board)
    for r in SETUP_RULES:
        if r.name not in _REACTION_RULES or mate1:
            continue
        try:
            if not r.predicate(board):
                continue
        except Exception:
            continue
        legal = _rule_candidates(board, r)
        if legal:
            return BookEntry(moves=legal, line=r.name, idea=r.idea, source="rule",
                             assumes=r.assumes, exceptions=r.exceptions, wiki=r.wiki)
    # 2) Everything else is a QUIET setup/trigger move — only right when nothing forcing
    #    is on the board. If a real tactic (mate / winning capture) exists, defer.
    if _strong_tactic_available(board):
        return None
    for r in SETUP_RULES:
        if r.name in _REACTION_RULES:
            continue
        try:
            if not r.predicate(board):
                continue
        except Exception:
            continue
        legal = _rule_candidates(board, r)
        if legal:
            return BookEntry(moves=legal, line=r.name, idea=r.idea, source="rule",
                             assumes=r.assumes, exceptions=r.exceptions, wiki=r.wiki)
    return None


# ── public lookup ────────────────────────────────────────────────────────────────
def lookup(board: chess.Board) -> BookEntry | None:
    """Book entry for this position if recognised AND it is White to move, else None.
    Exact line first (most specific), then the first matching setup rule. Pure table /
    predicate lookup — never an engine."""
    if board.turn != chess.WHITE:
        return None
    exact = EXACT_BOOK.get(position_key(board))
    if exact:
        return exact
    return _rule_lookup(board)
