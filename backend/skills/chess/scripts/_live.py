"""Shared live-state access for the chess skill's perception scripts.

Centralises the backend fetch and the board-with-history reconstruction so
every script sees the same position the same way. History matters: the
repetition and 50-move checks (pure rules of chess — mechanics-tool
territory) only work on a board that carries the real move stack.

Not exposed as a tool (underscore prefix).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

import chess


def fetch_state() -> dict:
    """GET the live game state, or exit(1) with an error on stderr."""
    api_base = os.environ.get("CHESS_API_BASE", "http://localhost:8000").rstrip("/")
    game_id = os.environ.get("CHESS_GAME_ID", "")
    if not game_id:
        print("error: CHESS_GAME_ID not set", file=sys.stderr)
        sys.exit(1)
    try:
        with urllib.request.urlopen(f"{api_base}/api/games/{game_id}", timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    if not data.get("fen"):
        print("error: backend response missing 'fen'", file=sys.stderr)
        sys.exit(1)
    return data


def board_with_history(data: dict) -> chess.Board:
    """Board for the live position, carrying the real move stack when the
    recorded history replays cleanly from the game's initial_fen (puzzle
    games don't start at the standard setup). Falls back to a bare-FEN
    board on any reconstruction problem — never raises, never blocks the
    caller's board view."""
    fen = data["fen"]
    board = chess.Board(fen)
    uci_moves = data.get("uci_moves") or []
    if uci_moves:
        try:
            replay = chess.Board(data.get("initial_fen") or chess.STARTING_FEN)
            for uci in uci_moves:
                replay.push(chess.Move.from_uci(uci))
            if replay.fen() == fen:
                board = replay
        except Exception:
            pass
    return board


def draw_flag(board: chess.Board, move: chess.Move) -> str:
    """Short draw-risk flag for pushing `move` on `board`, or ''.

    Needs a board with history to be meaningful (bare boards report '').
      'draw:repetition' — the move immediately produces a threefold
                          repetition (auto-claimed: instant draw).
      'draw:50-move'    — the move triggers the 50-move rule.
      'repeats!'        — the move recreates a position seen before
                          (second occurrence; one more repeat draws).
    """
    b = board.copy()  # full copy, stack included
    b.push(move)
    # can_claim_*, not is_repetition(3)/is_fifty_moves: the backend ends
    # non-chesscom games with claim_draw=True, so a claimable draw IS a draw.
    if b.can_claim_threefold_repetition():
        return "draw:repetition"
    if b.can_claim_fifty_moves():
        return "draw:50-move"
    if b.is_repetition(2):
        return "repeats!"
    return ""
