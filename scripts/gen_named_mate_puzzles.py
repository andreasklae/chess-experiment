#!/usr/bin/env python3
"""Generate verified pre-mate puzzles for the named 'configuration' mates from
their archetypal positions on Wikipedia's "Checkmate pattern" article.

We do NOT invent positions: each archetype's piece placement is taken verbatim
from the Wikipedia chess-diagram template (the same source the wiki pages were
synthesised from), parsed to a FEN, confirmed to be checkmate in python-chess,
then walked back ONE white move to produce a "White to move, mate in 1" puzzle
from the exact pattern geometry. A white king is added on a far square when the
archetype omits it (the diagrams show only the mating pieces).

This tests whether the agent recognises and plays the pattern's defining final
blow — the meaningful unit for a named configuration mate.

Output: JSON list of {name, fen, mate_san} to stdout.
"""

import json
import sys

import chess


# Archetypal final positions, piece lists taken from the Wikipedia diagrams
# (rank 8 → rank 1). Each is (black-king-mated) with only the mating pieces; we
# add a white king far away. Verified to be checkmate below.
ARCHETYPES = {
    # Arabian: kh8, white Rh7, Nf6.
    "arabian": "7k/7R/5N2/8/8/8/8/K7",
    # Anastasia: black king h7, white Ne7 (covers g8/g6), black pawn g7, white
    # rook delivers along the h-file. Verified mate.
    "anastasia": "8/4N1pk/8/7R/8/8/8/K7",
    # Greco: black king h8, black pawn g7, white Qh5 (h-file), white Bc4 on the
    # a2-g8 diagonal covering g8. Parsed verbatim from the Wikipedia diagram.
    "greco": "7k/6p1/8/7Q/2B5/8/8/K7",
}


def find_premate(final_fen: str):
    """Confirm the position is mate (black to move) with exactly one checker,
    then return (pre_fen, mate_san) for a white move that delivers it."""
    fb = chess.Board(final_fen + " w - - 0 1")
    test = fb.copy()
    test.turn = chess.BLACK
    if not test.is_checkmate():
        return None, "archetype is not checkmate"
    bk = test.king(chess.BLACK)
    checkers = list(test.attackers(chess.WHITE, bk))
    if len(checkers) != 1:
        return None, f"expected one checker, got {len(checkers)}"
    dsq = checkers[0]
    piece = fb.piece_at(dsq)
    for from_sq in chess.SQUARES:
        if from_sq == dsq:
            continue
        pre = fb.copy()
        pre.remove_piece_at(dsq)
        pre.set_piece_at(from_sq, piece)
        pre.turn = chess.WHITE
        if not pre.is_valid():
            continue
        mv = chess.Move(from_sq, dsq)
        if mv in pre.legal_moves:
            after = pre.copy()
            after.push(mv)
            if after.is_checkmate():
                return pre.fen(), pre.san(mv)
    return None, "no legal predecessor"


def main() -> None:
    out = []
    for name, archetype in ARCHETYPES.items():
        pre_fen, info = find_premate(archetype)
        if pre_fen is None:
            print(f"  {name}: SKIP — {info}", file=sys.stderr)
            continue
        out.append({"name": name, "fen": pre_fen, "mate_san": info})
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
