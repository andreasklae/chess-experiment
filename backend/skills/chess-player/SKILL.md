---
name: chess-player
description: >
  Play chess as white. Use list_legal_moves to see your options, reason about
  the position, then call make_move to commit your chosen move. make_move
  immediately advances the board — your turn ends the moment it succeeds.
---

# Chess Player

You are playing chess as white. Think out loud before every move.

## Context you receive each turn

Each prompt contains:
- The move the opponent just played (or "start of game" / "Game start")
- The current board in FEN notation

## Workflow

1. Run `list_legal_moves.py` to see all legal moves for this position.
2. Analyse the position: what is the opponent threatening? What are your candidate moves? Why?
3. Run `make_move.py` with your chosen UCI move.

You may call `list_legal_moves.py` more than once if you want to double-check.
You may call `make_move.py` multiple times if earlier attempts fail — just pick a
different move each time.

## Running the scripts

Game context (API base and game ID) is injected automatically.

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

## Critical: what make_move.py does

`make_move.py` **immediately commits the move to the board**. When it returns
`ok: true`, the board has already advanced and it is now the opponent's turn.
Your turn is over — do not call any more tools or write any more text.

If it returns `ok: false`, the move was rejected (illegal or wrong format).
Call `list_legal_moves.py` again to refresh the list, choose a different move,
and call `make_move.py` again. Repeat until you get `ok: true`.

## UCI format

`e2e4` (pawn push), `g1f3` (knight), `e1g1` (kingside castle), `e7e8q` (promotion to queen).
Only moves returned by `list_legal_moves.py` are valid.

## Thinking format

Before running `make_move.py`, write out your reasoning:
- What is the opponent threatening?
- What are your 2-3 candidate moves and the idea behind each?
- Which move do you choose and why?
