"""Validate detectors against the Lichess puzzle DB (ground-truth themes).

Reads a decompressed slice of lichess_db_puzzle.csv (cols: PuzzleId, FEN, Moves,
Rating, ..., Themes, ...). For each themed puzzle we replay the solution and, at
the position right before the motif move is played, check that the corresponding
detector fires. The DB FEN is the position BEFORE the first move; the first move
is the opponent's setup, then solver/opponent alternate.

Honest accounting: we only count a puzzle toward a detector when the motif our
detector targets actually occurs in the solution line (e.g. for 'fork' we look
for a KNIGHT move that lands hitting >=2 K/Q/R — what our detector claims). This
measures precision/recall of the detector against what it is designed to catch,
using real positions rather than crafted ones.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import chess

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _features import (  # noqa: E402
    detect_knight_forks, detect_pins_skewers, detect_loose_pieces,
    detect_pawn_structure, _knight_targets_from,
)

CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/puz_chunk.csv")


def rows(theme: str, limit: int):
    out = []
    with CSV.open() as f:
        r = csv.DictReader(f)
        for row in r:
            if theme in row["Themes"].split():
                out.append(row)
                if len(out) >= limit:
                    break
    return out


def solver_positions(fen: str, moves: list[str]):
    """Yield (board_before_move, move, is_solver) for each move in the line.
    DB FEN is before move[0] (opponent setup); solver moves are indices 1,3,5..."""
    b = chess.Board(fen)
    for i, uci in enumerate(moves):
        is_solver = (i % 2 == 1)
        yield b, chess.Move.from_uci(uci), is_solver
        b.push(chess.Move.from_uci(uci))


def test_knight_forks(limit=400):
    checked = flagged = 0
    misses = []
    for row in rows("fork", limit):
        moves = row["Moves"].split()
        for b, mv, is_solver in solver_positions(row["FEN"], moves):
            pc = b.piece_at(mv.from_square)
            if not (pc and pc.piece_type == chess.KNIGHT and pc.color == b.turn):
                continue
            b2 = b.copy(); b2.push(mv)
            tgts = [s for s in _knight_targets_from(mv.to_square)
                    if b2.piece_at(s) and b2.piece_at(s).color != pc.color
                    and b2.piece_at(s).piece_type in (chess.KING, chess.QUEEN, chess.ROOK)]
            if len(tgts) >= 2:
                checked += 1
                land = chess.square_name(mv.to_square)
                kf = detect_knight_forks(b)
                if any(land in f.text and "fork" in f.text.lower() for f in kf):
                    flagged += 1
                else:
                    misses.append((row["PuzzleId"], mv.uci(), b.fen()))
    return checked, flagged, misses


def test_pins(limit=400):
    """For 'pin' puzzles: at the puzzle start the pin geometry usually exists.
    Check the detector flags a pin at the solver's first position."""
    checked = flagged = 0
    misses = []
    for row in rows("pin", limit):
        moves = row["Moves"].split()
        b = chess.Board(row["FEN"]); b.push(chess.Move.from_uci(moves[0]))  # solver to move
        # a pin somewhere on the board (either side)
        any_pin = False
        for c in (chess.WHITE, chess.BLACK):
            for sq in chess.SQUARES:
                p = b.piece_at(sq)
                if p and p.color == c and p.piece_type != chess.KING and b.is_pinned(c, sq):
                    any_pin = True
        if not any_pin:
            continue  # pin not present at this frame (set up later) — skip
        checked += 1
        fnd = detect_pins_skewers(b) + detect_pins_skewers(b, not b.turn)
        if any("PINNED" in f.text for f in fnd):
            flagged += 1
        else:
            misses.append((row["PuzzleId"], "", b.fen()))
    return checked, flagged, misses


def test_hanging(limit=400):
    """'hangingPiece' puzzles: a piece is hanging at the solver's first move."""
    checked = flagged = 0
    misses = []
    for row in rows("hangingPiece", limit):
        moves = row["Moves"].split()
        b = chess.Board(row["FEN"]); b.push(chess.Move.from_uci(moves[0]))
        # is some enemy piece (from solver's view) actually hanging / loose?
        fnd = detect_loose_pieces(b) + detect_loose_pieces(b, not b.turn)
        checked += 1
        if any("undefended" in f.text.lower() or "loose" in f.text.lower() for f in fnd):
            flagged += 1
        else:
            misses.append((row["PuzzleId"], "", b.fen()))
    return checked, flagged, misses


def test_advanced_pawn(limit=400):
    """'advancedPawn' / 'promotion' puzzles: a passed pawn is usually present."""
    checked = flagged = 0
    misses = []
    for row in rows("advancedPawn", limit):
        moves = row["Moves"].split()
        b = chess.Board(row["FEN"]); b.push(chess.Move.from_uci(moves[0]))
        fnd = detect_pawn_structure(b) + detect_pawn_structure(b, not b.turn)
        checked += 1
        if any("passed" in f.text.lower() for f in fnd):
            flagged += 1
        else:
            misses.append((row["PuzzleId"], "", b.fen()))
    return checked, flagged, misses


if __name__ == "__main__":
    for name, fn in [("knight-fork (K/Q/R)", test_knight_forks),
                     ("pin", test_pins),
                     ("hangingPiece", test_hanging),
                     ("advancedPawn->passed", test_advanced_pawn)]:
        checked, flagged, misses = fn()
        rate = f"{flagged}/{checked}" if checked else "0/0"
        pct = f"{100*flagged/checked:.0f}%" if checked else "—"
        print(f"{name:22} detector fired on {rate}  ({pct})")
        for mid, mv, fen in misses[:3]:
            print(f"    MISS {mid} {mv}: {fen}")
