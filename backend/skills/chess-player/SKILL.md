---
name: chess-player
description: >
  Play chess as white. Use list_legal_moves to see your options, reason about
  the position, then call make_move to commit your chosen move. make_move
  immediately advances the board — your turn ends the moment it succeeds.
---

# Chess Player

The system prompt describes the turn workflow. This page documents the script
invocation contract you need to know once.

## Context you receive each turn

- The move the opponent just played (or "Game start")
- The current board in FEN notation

## Scripts

Game context (API base and game ID) is injected via environment variables —
no arguments needed beyond what's shown below.

**List legal moves:**
```
run_script("chess-player", "list_legal_moves.py", "")
```
Returns a JSON array: `["e2e4", "d2d4", "g1f3", ...]`

**Make a move:**
```
run_script("chess-player", "make_move.py", "--uci <move>")
```
On success: `{"ok": true, "move": "e2e4", "message": "Move committed. Your turn is over."}`
On failure: `{"ok": false, "error": "...", "legal_moves": [...]}`

## UCI format

`e2e4` (pawn push), `g1f3` (knight), `e1g1` (kingside castle), `e7e8q` (promotion to queen).
Only moves returned by `list_legal_moves.py` are valid.
