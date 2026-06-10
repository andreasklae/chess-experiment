---
category: patterns/mating-patterns
description: Mate with two major pieces (two rooks, or queen and rook) by checking on alternating ranks, driving the king to the edge. The simplest forced mate — needs no help from your king.
triggers: [two rooks, queen and rook, two major pieces, enemy king in the open, lawnmower mate, ladder]
related_pages: [patterns/mating-patterns/king-queen-mate, patterns/mating-patterns/king-rook-mate, patterns/mating-patterns/back-rank-mate]
tags: [mate, endgame, rook, queen, technique]
status: draft
updated: 2026-06-10
---

# Ladder Mate (two rooks, or queen + rook)

## When to use

You have two rooks, two queens, or queen + rook, and the enemy king is in
the open. This is the **first mate to look for** — it is fully forced, needs
no support from your own king, and takes only a handful of moves. If you are
about to promote a pawn while you still have a rook, this is the mate you
are promoting *into*.

## The idea

The two pieces take turns: one checks the king along a rank, the other
fences off the next rank so the king cannot come back. Each check pushes the
king one rank closer to the edge — like climbing a ladder. On the last rank
the check is mate.

## What to do

- Put one piece on the rank just behind the king (the fence), the other
  checks on the king's rank.
- After each check, the king retreats a rank; the old fence piece now checks
  on the new rank. Repeat.
- **If the king walks toward a checking or fencing piece, slide that piece
  far away along the same rank** — the fence still holds, and the king
  wastes moves chasing.

## Watch out for

- Don't let a rook get captured — keep them on files far from the enemy
  king (see the example's 2.Rh5).
- With queen + rook, the same ladder works; with a lone queen it does not —
  use [[patterns/mating-patterns/king-queen-mate]] instead.
- Near the end, confirm with `chess__imagine_move` that the final check is
  `gives checkmate`, not stalemate.

## Examples

`8/8/8/3k4/R7/8/1R6/7K w - - 0 1` — 1.Rb5+ Kc6 (the king attacks the
rook) 2.Rh5! (slide away, fence intact) Kd6 3.Ra6+ Ke7 4.Rh7+ Kf8 5.Ra8#.
Verified mate.
