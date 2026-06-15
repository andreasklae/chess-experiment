---
category: principles
description: When far ahead, every quiet move must leave the opponent a legal reply — stalemate turns a won game into a draw in one move.
triggers: [bare king, cornered king, huge material lead, quiet move when winning, stalemate]
related_pages: [patterns/mating-patterns/king-queen-mate, patterns/mating-patterns/king-rook-mate, strategic-thinking/convert-advantage]
tags: [principle, stalemate, endgame, safety]
status: draft
updated: 2026-06-10
---

# Avoid stalemate

## When to use

You are massively ahead — enemy king bare or nearly bare, especially when it
sits on an edge or in a corner. This is exactly when stalemate happens.

## The idea

If the opponent has **no legal move and is not in check**, the game is
instantly drawn — the single cheapest way to lose half a point from a
completely won position. The fewer pieces and squares the enemy has, the
more suspicious you must be of "harmless" quiet moves.

## What to do

- Before any **non-checking** move in a winning endgame, count the enemy
  king's legal moves. If the answer might be zero, run
  `chess__imagine_move` — it reports `stalemate` explicitly.
- Prefer moves that give **check** or leave the enemy king an obvious free
  square.
- When boxing a king (queen or rook mates), stop shrinking the box once the
  king is on the edge with two squares left, and bring your own king up
  instead.

## Watch out for

- The classic queen trap: queen a knight's-move from a cornered king —
  `k7/8/1QK5/8/8/8/8/8 b` is stalemate.
- The rook seal: `k7/8/K7/8/8/8/8/1R6 b` is stalemate.
- Pawn endings too: `4k3/4P3/4K3/8/8/8/8/8 b` is stalemate. Rule of thumb:
  **a pawn that arrives on the seventh rank giving check only draws** — get
  your king to the sixth rank *beside* the promotion path first, then push.

## Examples

All three positions above were verified as stalemate with python-chess.
The fix is always the same: give the king one square, or give check.
