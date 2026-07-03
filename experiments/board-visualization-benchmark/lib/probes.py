"""Relational probe generation + python-chess ground-truth oracle.

The Stage-2 quiz tests COMPREHENSION of a rendered board, not recall of squares.
Probes target the relations the chess tools' decisions actually depend on
(see chess-perception-action-gap): occupancy, attack, defense, check, hanging.

Each probe is auto-generated from a position with a single, mechanically-verified
answer. We only emit a probe when the answer is unambiguous AND non-degenerate
(e.g. we don't ask "is X defended" unless there's a real attacker making it
interesting; we pick squares that have pieces; we ensure yes/no probes aren't
trivially all-yes for a position).

Probe types (all answers ground-truthed here, never by the model under test):
  occupancy   — "What piece is on <sq>?"  answer: piece name or 'empty'
  defended    — "Is the <piece> on <sq> defended by its own side?" yes/no
  attacked    — "Is the <piece> on <sq> attacked by the enemy?" yes/no
  count_attackers — "How many enemy pieces attack <sq>?" integer
  in_check    — "Is the side to move in check?" yes/no
  hanging     — "Is the <piece> on <sq> hanging (attacked and not defended)?" yes/no

Answers are normalized to lowercase canonical tokens for scoring.
"""
from __future__ import annotations

import chess
from dataclasses import dataclass, asdict

_PIECE_WORD = {
    chess.PAWN: "pawn", chess.KNIGHT: "knight", chess.BISHOP: "bishop",
    chess.ROOK: "rook", chess.QUEEN: "queen", chess.KING: "king",
}


@dataclass(frozen=True)
class Probe:
    position_id: str
    probe_id: str
    kind: str       # occupancy | defended | attacked | count_attackers | in_check | hanging
    question: str
    answer: str     # canonical lowercase token: piece word, 'yes'/'no', or integer-as-string
    answer_type: str  # 'piece' | 'bool' | 'int'

    def to_dict(self) -> dict:
        return asdict(self)


def _piece_word(board: chess.Board, sq: int) -> str:
    p = board.piece_at(sq)
    return _PIECE_WORD[p.piece_type] if p else "empty"


def _is_defended(board: chess.Board, sq: int) -> bool:
    """A piece is defended if one of its own side (excluding itself) attacks its
    square. Computed by asking whether, were the square empty of this piece, a
    friendly attacker bears on it — python-chess attackers() already excludes the
    piece on the square itself for this purpose."""
    p = board.piece_at(sq)
    if p is None:
        return False
    return len(board.attackers(p.color, sq)) > 0


def _enemy_attackers(board: chess.Board, sq: int) -> int:
    p = board.piece_at(sq)
    if p is None:
        return 0
    return len(board.attackers(not p.color, sq))


def _occupied_squares(board: chess.Board, color: bool | None = None) -> list[int]:
    out = []
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p and (color is None or p.color == color):
            out.append(sq)
    return out


def generate_probes(position_id: str, board: chess.Board) -> list[Probe]:
    """Deterministically generate a balanced probe set for one position.

    Determinism matters: the same probes are asked of every rendering format,
    so the format is the only variable. Squares are chosen by fixed rules
    (sorted order, first match), not randomness.
    """
    probes: list[Probe] = []
    stm = board.turn  # side to move
    stm_word = "white" if stm == chess.WHITE else "black"

    def add(kind, q, ans, atype):
        probes.append(Probe(position_id, f"{position_id}_{kind}_{len(probes)}",
                            kind, q, ans, atype))

    # --- occupancy: one occupied square + one empty square ---
    occ = _occupied_squares(board)
    if occ:
        sq = sorted(occ)[len(occ) // 2]  # a middle occupied square, deterministic
        add("occupancy", f"What piece is on {chess.square_name(sq)}? "
            f"Answer with the piece type (pawn/knight/bishop/rook/queen/king) or 'empty'.",
            _piece_word(board, sq), "piece")
    empties = [s for s in chess.SQUARES if board.piece_at(s) is None]
    if empties:
        sq = sorted(empties)[len(empties) // 2]
        add("occupancy", f"What piece is on {chess.square_name(sq)}? "
            f"Answer with the piece type or 'empty'.",
            "empty", "piece")

    # --- in_check ---
    add("in_check", f"Is the side to move ({stm_word}) currently in check? "
        f"Answer yes or no.",
        "yes" if board.is_check() else "no", "bool")

    # --- defended: pick a defended piece and an undefended one (stm side) ---
    stm_pieces = [s for s in _occupied_squares(board, stm)
                  if board.piece_at(s).piece_type != chess.KING]
    defended = [s for s in stm_pieces if _is_defended(board, s)]
    undefended = [s for s in stm_pieces if not _is_defended(board, s)]
    if defended:
        sq = sorted(defended)[0]
        add("defended", f"Is the {stm_word} {_piece_word(board, sq)} on "
            f"{chess.square_name(sq)} defended by another {stm_word} piece? Answer yes or no.",
            "yes", "bool")
    if undefended:
        sq = sorted(undefended)[0]
        add("defended", f"Is the {stm_word} {_piece_word(board, sq)} on "
            f"{chess.square_name(sq)} defended by another {stm_word} piece? Answer yes or no.",
            "no", "bool")

    # --- attacked: pick an attacked stm piece and a non-attacked one ---
    attacked = [s for s in stm_pieces if _enemy_attackers(board, s) > 0]
    not_attacked = [s for s in stm_pieces if _enemy_attackers(board, s) == 0]
    if attacked:
        sq = sorted(attacked)[0]
        add("attacked", f"Is the {stm_word} {_piece_word(board, sq)} on "
            f"{chess.square_name(sq)} attacked by an enemy piece? Answer yes or no.",
            "yes", "bool")
        add("count_attackers", f"How many enemy pieces attack the "
            f"{chess.square_name(sq)} square? Answer with a single integer.",
            str(_enemy_attackers(board, sq)), "int")
    if not_attacked:
        sq = sorted(not_attacked)[0]
        add("attacked", f"Is the {stm_word} {_piece_word(board, sq)} on "
            f"{chess.square_name(sq)} attacked by an enemy piece? Answer yes or no.",
            "no", "bool")

    # --- hanging: attacked AND undefended (the load-bearing relation for blunders) ---
    hanging = [s for s in stm_pieces
               if _enemy_attackers(board, s) > 0 and not _is_defended(board, s)]
    safe = [s for s in stm_pieces
            if _enemy_attackers(board, s) == 0 or _is_defended(board, s)]
    if hanging:
        sq = sorted(hanging)[0]
        add("hanging", f"Is the {stm_word} {_piece_word(board, sq)} on "
            f"{chess.square_name(sq)} hanging (attacked by the enemy and not "
            f"defended by its own side)? Answer yes or no.",
            "yes", "bool")
    if safe:
        sq = sorted(safe)[0]
        add("hanging", f"Is the {stm_word} {_piece_word(board, sq)} on "
            f"{chess.square_name(sq)} hanging (attacked by the enemy and not "
            f"defended by its own side)? Answer yes or no.",
            "no", "bool")

    return probes


# ---- answer normalization / scoring ----

_PIECE_SYNONYMS = {
    "p": "pawn", "n": "knight", "b": "bishop", "r": "rook", "q": "queen", "k": "king",
    "knight": "knight", "pawn": "pawn", "bishop": "bishop", "rook": "rook",
    "queen": "queen", "king": "king", "empty": "empty", "none": "empty", "nothing": "empty",
}
_BOOL_TRUE = {"yes", "y", "true", "1"}
_BOOL_FALSE = {"no", "n", "false", "0"}


def normalize_answer(raw: str, answer_type: str) -> str | None:
    """Map a free-text model answer to a canonical token, or None if unparseable.
    Conservative: extracts the operative token; refuses to guess when ambiguous."""
    if raw is None:
        return None
    t = raw.strip().lower()
    # strip trailing punctuation/quotes/markdown
    t = t.strip(" .,:;!?\"'`*_\n\t()[]{}")
    if not t:
        return None

    if answer_type == "bool":
        # look for the first clear yes/no token anywhere in a short answer
        words = t.replace("/", " ").split()
        for w in words:
            w2 = w.strip(" .,:;!?\"'`*_")
            if w2 in _BOOL_TRUE:
                return "yes"
            if w2 in _BOOL_FALSE:
                return "no"
        return None

    if answer_type == "int":
        import re
        m = re.search(r"-?\d+", t)
        return m.group(0) if m else None

    if answer_type == "piece":
        words = t.replace("/", " ").split()
        for w in words:
            w2 = w.strip(" .,:;!?\"'`*_")
            if w2 in _PIECE_SYNONYMS:
                return _PIECE_SYNONYMS[w2]
        return None

    return None


def score(raw_answer: str, probe: Probe) -> tuple[bool, str | None]:
    """Return (correct, normalized). Unparseable -> (False, None) and is counted
    as wrong (a format whose output the model cannot answer cleanly IS worse)."""
    norm = normalize_answer(raw_answer, probe.answer_type)
    if norm is None:
        return False, None
    return norm == probe.answer, norm


if __name__ == "__main__":
    from positions import load_positions
    total = 0
    kinds: dict[str, int] = {}
    for pos in load_positions():
        ps = generate_probes(pos.id, pos.board)
        total += len(ps)
        for p in ps:
            kinds[p.kind] = kinds.get(p.kind, 0) + 1
    print(f"{total} probes across corpus")
    for k, n in sorted(kinds.items()):
        print(f"  {k}: {n}")
