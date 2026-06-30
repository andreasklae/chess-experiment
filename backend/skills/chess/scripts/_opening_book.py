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
    moves: list[str] = field(default_factory=list)   # book move SAN(s) for this position
    line: str = ""
    idea: str = ""
    source: str = "line"                             # "line" or "rule"


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


# Each rule: (name, idea, predicate(board) -> bool, candidate SANs in priority order)
@dataclass
class Rule:
    name: str
    idea: str
    predicate: object            # Callable[[chess.Board], bool]
    candidates: list[str]


W = chess.WHITE
B = chess.BLACK

SETUP_RULES: list[Rule] = [
    # --- EXCEPTION TRIGGERS (specific, checked first) ---
    Rule("London vs ...Qb6 — b2 under fire",
         "Black's queen hits the loose b2-pawn. If c3 is already in, Qb3 offers the "
         "trade; otherwise the queen can't reach b3 — defend with Qc1 (or b3). "
         "Read openings/london-vs-qb6.",
         lambda bd: _has(bd, chess.QUEEN, B, chess.B6)
                    and bool(bd.attackers(B, chess.B2)),
         ["Qb3", "Qc1", "b3"]),   # Qb3 tried first but only used if LEGAL (needs c3 in)
    Rule("London vs ...Nh5 — save the dark bishop",
         "Black's ...Nh5 attacks your f4/g3 bishop (a key London piece). Retreat: Bh2 "
         "if h3 is in, else Bg5; or allow ...Nxg3 hxg3 for the open h-file. "
         "Read openings/london-vs-nh5.",
         lambda bd: _has(bd, chess.KNIGHT, B, chess.H5)
                    and (bool(bd.attackers(B, chess.F4)) or bool(bd.attackers(B, chess.G3))),
         ["Bh2", "Bg5", "Bg3"]),
    Rule("London vs ...g6 — use Be2 not Bd3",
         "Black is fianchettoing (...g6). Develop the light bishop to e2 (Bd3 has little "
         "scope vs the wall) and get h3 in. Read openings/london-vs-kings-indian.",
         lambda bd: _black_pawn(bd, chess.G6)
                    and not _has(bd, chess.BISHOP, W, chess.D3)
                    and not _has(bd, chess.BISHOP, W, chess.E2)
                    and _has(bd, chess.BISHOP, W, chess.F1),
         ["Be2"]),
    # --- ROUTINE SETUP MOVES (broad; "play the London structure") ---
    # Each fires when its London piece/pawn is not yet placed and the earlier setup
    # pieces are in (so the move order stays sane). The candidate is only USED if legal,
    # so these never override a position where the move is actually impossible/illegal.
    Rule("London setup — bishop out to f4",
         "Get the dark-squared bishop OUTSIDE the pawn chain (f4) before playing e3 — "
         "the whole point of the London.",
         lambda bd: _has(bd, chess.PAWN, W, chess.D4)
                    and _has(bd, chess.BISHOP, W, chess.C1)
                    and not _black_pawn_attacks_f4(bd),
         ["Bf4"]),
    Rule("London setup — e3",
         "Support d4 and free the f1-bishop.",
         lambda bd: _bishop_developed_dark(bd)
                    and _has(bd, chess.PAWN, W, chess.E2)
                    and not _has(bd, chess.KNIGHT, W, chess.F3),
         ["e3"]),
    Rule("London setup — Nf3",
         "Develop the king's knight; it heads for e5 later.",
         lambda bd: _bishop_developed_dark(bd)
                    and not _has(bd, chess.PAWN, W, chess.E2)   # e3 played
                    and _has(bd, chess.KNIGHT, W, chess.G1),
         ["Nf3"]),
    Rule("London setup — Bd3",
         "Develop the light bishop to d3 (aims at h7). (Use Be2 instead vs a ...g6 "
         "fianchetto — handled above.)",
         lambda bd: _has(bd, chess.KNIGHT, W, chess.F3)
                    and _has(bd, chess.BISHOP, W, chess.F1)
                    and not _black_pawn(bd, chess.G6),
         ["Bd3"]),
    Rule("London setup — c3",
         "Support d4 with c3 (the third side of the triangle).",
         lambda bd: _bishop_developed_dark(bd)
                    and not _has(bd, chess.PAWN, W, chess.E2)   # e3 in
                    and _has(bd, chess.PAWN, W, chess.C2)
                    and not _has(bd, chess.KNIGHT, W, chess.C3),
         ["c3"]),
    Rule("London setup — Nbd2",
         "Develop the queen's knight to d2 (supports e4/Ne5, keeps c-pawn free).",
         lambda bd: _has(bd, chess.KNIGHT, W, chess.B1)
                    and _has(bd, chess.KNIGHT, W, chess.F3)
                    and bd.piece_at(chess.D2) is None,
         ["Nbd2"]),
    Rule("London setup — castle short",
         "Get the king safe — castle kingside once the kingside is developed.",
         lambda bd: bd.has_kingside_castling_rights(W)
                    and _has(bd, chess.KNIGHT, W, chess.F3)
                    and bd.piece_at(chess.F1) is None
                    and bd.piece_at(chess.G1) is None,
         ["O-O"]),
]


def _black_pawn_attacks_f4(board: chess.Board) -> bool:
    return bool(board.attackers(B, chess.F4) & board.pieces(chess.PAWN, B))


def _bishop_developed_dark(board: chess.Board) -> bool:
    """The dark-squared bishop is out of c1 (on f4/g3/h2/e5/d2/g5 — i.e. developed)."""
    return not _has(board, chess.BISHOP, W, chess.C1) and bool(
        board.pieces(chess.BISHOP, W))


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


def _rule_lookup(board: chess.Board) -> BookEntry | None:
    # A setup move is only the right answer in a QUIET book position. If an obvious
    # forcing tactic exists, defer — do not tell the agent to play a developing move
    # when a mate or a winning capture is on the board.
    if _strong_tactic_available(board):
        return None
    for r in SETUP_RULES:
        try:
            if not r.predicate(board):
                continue
        except Exception:
            continue
        for san in r.candidates:
            good = _legal_san(board, san)
            if good:
                return BookEntry(moves=[good], line=r.name, idea=r.idea, source="rule")
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
