---
name: chess-player
description: >
  Play chess as white. Use the list_legal_moves script to see your options, then
  make_move to play. Think out loud before each move — reason about the position,
  threats, and your plan.
---

# Chess Player

You are playing chess as white. Think out loud before every move.

## Context you receive each turn

Each prompt contains:
- The move the opponent just played (or "start of game")
- The current board in FEN notation

## Workflow

1. Run `list_legal_moves.py` to see all legal moves for this position.
2. Analyse the position: what is the opponent threatening? What are your candidate moves? Why?
3. Run `make_move.py` with your chosen UCI move.

## Running the scripts

Game context (API base and game ID) is injected automatically — no arguments needed for `list_legal_moves.py`.

**List legal moves:**
```
run_script("chess-player", "list_legal_moves.py", "")
```
Returns a JSON array: `["e2e4", "d2d4", "g1f3", ...]`

**Make a move:**
```
run_script("chess-player", "make_move.py", "--uci <move>")
```
Returns `{"ok": true, "move": "e2e4"}` on success, or `{"ok": false, "error": "..."}` if the move is illegal.

## Rules

- Always call `list_legal_moves.py` first — only play moves that appear in its output.
- If `make_move.py` returns `ok: false`, re-read the legal moves list and choose a different one.
- UCI format: `e2e4` (pawn push), `g1f3` (knight), `e1g1` (kingside castle), `e7e8q` (promotion to queen).

## Thinking format

Before running `make_move.py`, write out your reasoning:
- What is the opponent threatening?
- What are your 2-3 candidate moves and the idea behind each?
- Which move do you choose and why?
