"""Position corpus for the board-visualization benchmark.

A fixed, reproducible set of legal positions stratified by game phase and
piece density. Positions are hand-curated FENs (not random) so that:
  - every position is legal and reached by plausible play,
  - the relational probes have non-trivial, unambiguous answers
    (there IS a defended piece to ask about, there IS a hanging piece, etc.),
  - the set is small enough to run many model samples per cell affordably,
  - the same positions are reused verbatim across every rendering format
    (the variable under test is the FORMAT, not the position).

Strata:
  opening   — many pieces, near the starting structure
  middlegame— dense, tactical, kings castled or central
  endgame   — sparse, few pieces

Each entry: id, fen, phase. The FENs are validated at import time.
"""
from __future__ import annotations

import chess
from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    id: str
    fen: str
    phase: str  # opening | middlegame | endgame

    @property
    def board(self) -> chess.Board:
        return chess.Board(self.fen)


# Curated positions. Side-to-move varies on purpose (both colours appear) so
# the formats are tested for both perspectives. All verified legal at import.
_RAW: list[tuple[str, str, str]] = [
    # ---- OPENING (dense, near-start structures) ----
    ("op1", "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 4", "opening"),   # Italian
    ("op2", "rnbqkb1r/pp2pppp/3p1n2/2pP4/4P3/2N5/PPP2PPP/R1BQKBNR b KQkq - 0 4", "opening"),   # Benoni-ish
    ("op3", "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQK2R b KQkq - 0 5", "opening"),  # Italian, both developed
    ("op4", "rnbqkbnr/pp3ppp/4p3/2pp4/3P1B2/4P3/PPP2PPP/RN1QKBNR b KQkq - 0 4", "opening"),    # London
    ("op5", "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQ1RK1 b kq - 5 4", "opening"),  # Italian, White castled

    # ---- MIDDLEGAME (dense, tactical) ----
    ("mg1", "r2q1rk1/ppp2ppp/2np1n2/2b1p1B1/2B1P3/2NP1N2/PPP2PPP/R2Q1RK1 w - - 0 9", "middlegame"),
    ("mg2", "r1bq1rk1/pp2bppp/2n1pn2/2pp4/3P1B2/2P1PN2/PP1N1PPP/R2QKB1R w KQ - 0 8", "middlegame"),
    ("mg3", "2rq1rk1/pp1bppbp/3p1np1/8/3NP3/1BN1BP2/PPPQ2PP/2KR3R w - - 0 12", "middlegame"),  # Sicilian-type
    ("mg4", "r4rk1/1bqnbppp/pp2pn2/2pp4/3P4/1PN1PN2/PBP1BPPP/R2Q1RK1 w - - 0 12", "middlegame"),
    ("mg5", "r1b2rk1/2q1bppp/p1nppn2/1p4B1/3NPP2/2N2Q2/PPP3PP/2KR1B1R w - - 0 12", "middlegame"),  # sharp, opposite plans

    # ---- ENDGAME (sparse) ----
    ("eg1", "8/5pk1/6p1/7p/7P/6P1/5PK1/8 w - - 0 1", "endgame"),          # K+3P each
    ("eg2", "8/8/4k3/8/8/4K3/4P3/8 w - - 0 1", "endgame"),                 # K+P vs K
    ("eg3", "8/8/3k4/8/3K4/8/4R3/8 w - - 0 1", "endgame"),                 # K+R vs K
    ("eg4", "6k1/5ppp/8/8/8/8/3R1PPP/6K1 w - - 0 1", "endgame"),           # R endgame
    ("eg5", "8/8/4k3/2b5/8/4K3/2B5/8 w - - 0 1", "endgame"),               # opp-coloured bishops
    ("eg6", "8/2k5/8/3n4/8/2N5/6K1/8 b - - 0 1", "endgame"),               # K+N each, Black to move
]


def load_positions() -> list[Position]:
    out: list[Position] = []
    for pid, fen, phase in _RAW:
        b = chess.Board(fen)  # raises on illegal FEN structure
        if not b.is_valid():
            raise ValueError(f"position {pid} is not a valid chess position: {fen}")
        out.append(Position(id=pid, fen=fen, phase=phase))
    return out


if __name__ == "__main__":
    ps = load_positions()
    by_phase: dict[str, int] = {}
    for p in ps:
        by_phase[p.phase] = by_phase.get(p.phase, 0) + 1
    print(f"{len(ps)} positions, all valid")
    for ph, n in sorted(by_phase.items()):
        print(f"  {ph}: {n}")
