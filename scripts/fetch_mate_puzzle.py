#!/usr/bin/env python3
"""Fetch a REAL mate puzzle from the Lichess puzzle API by theme, and emit the
position where the solver is to move (plus the verified solution).

These are real positions from real games, tagged by Lichess with the mating
pattern (arabianMate, anastasiaMate, hookMate, …) and a mateInN theme. We do
NOT invent positions — we pull them from Lichess and verify the solution mates
in python-chess before using it as a puzzle.

Lichess puzzle convention: the game PGN runs to ``initialPly``; the position
right after that ply is the puzzle, and ``solution[0]`` is the SOLVER's first
move (the side to move in that position is the side that must mate). We replay
to the puzzle position, confirm the full solution is legal and ends in
checkmate, and print the puzzle FEN + solution.

Usage:
    .venv/bin/python scripts/fetch_mate_puzzle.py <lichessTheme> [tries]
e.g. scripts/fetch_mate_puzzle.py arabianMate
Themes: arabianMate anastasiaMate hookMate bodenMate dovetailMate
        doubleBishopMate smotheredMate backRankMate (Lichess camelCase names).
"""

import io
import json
import sys
import urllib.request

import chess
import chess.pgn


def fetch(theme: str) -> dict | None:
    url = f"https://lichess.org/api/puzzle/next?angle={theme}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)
    except Exception as exc:  # network/throttle
        print(f"  fetch error: {exc}", file=sys.stderr)
        return None


def puzzle_position(data: dict) -> tuple[chess.Board, list[str]] | None:
    """Replay the PGN to initialPly and return (board_at_puzzle, solution)."""
    pgn = data["game"]["pgn"]
    initial_ply = data["puzzle"]["initialPly"]
    solution = data["puzzle"]["solution"]
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        return None
    board = game.board()
    for i, move in enumerate(game.mainline_moves()):
        board.push(move)
        if i + 1 == initial_ply:
            break
    return board, solution


def _mirror_uci(uci: str) -> str:
    """Vertically mirror a UCI move (a1<->a8 …) to match board.mirror()."""
    mv = chess.Move.from_uci(uci)
    fr = chess.square_mirror(mv.from_square)
    to = chess.square_mirror(mv.to_square)
    return chess.Move(fr, to, promotion=mv.promotion).uci()


def verify_solution(board: chess.Board, solution: list[str]) -> bool:
    """Play the solution out; it must be legal and end in checkmate."""
    b = board.copy()
    try:
        for uci in solution:
            b.push(chess.Move.from_uci(uci))
    except (ValueError, AssertionError):
        return False
    return b.is_checkmate()


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    theme = sys.argv[1]
    tries = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    # Optional: max mate-in depth (default 3) and require white-to-move so our
    # white-only agent can solve it directly.
    max_mate_in = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    want_white = "--any-side" not in sys.argv

    best = None  # keep the shortest acceptable puzzle seen
    for attempt in range(tries):
        data = fetch(theme)
        if data is None:
            continue
        pp = puzzle_position(data)
        if pp is None:
            continue
        board, solution = pp
        if not verify_solution(board, solution):
            continue
        mate_in = (len(solution) + 1) // 2
        if mate_in > max_mate_in:
            continue
        # Our agent plays WHITE only. If the solver is black, MIRROR the whole
        # position vertically + swap colours so white is to move and must mate
        # — a legal, equivalent puzzle (chess is colour-symmetric). The mirrored
        # solution is re-verified to still mate.
        if board.turn == chess.BLACK and want_white:
            board = board.mirror()
            solution = [_mirror_uci(u) for u in solution]
            if not verify_solution(board, solution):
                continue
        is_white = board.turn == chess.WHITE
        if want_white and not is_white:
            continue
        rec = {
            "theme": theme,
            "lichess_id": data["puzzle"]["id"],
            "themes": data["puzzle"]["themes"],
            "fen": board.fen(),
            "solver_to_move": "white" if is_white else "black",
            "solution": solution,
            "mate_in": mate_in,
        }
        if best is None or mate_in < best["mate_in"]:
            best = rec
        if mate_in == 1:               # can't do better than mate-in-1
            break
    if best is not None:
        print(json.dumps(best, indent=2))
        return
    print(f"No verified {theme} puzzle found in {tries} tries (throttled or "
          f"none mated cleanly).", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
