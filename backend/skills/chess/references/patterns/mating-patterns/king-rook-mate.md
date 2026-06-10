---
category: patterns/mating-patterns
description: Basic mate with king and rook against a bare king — fence with the rook, walk the kings into opposition, check to push the king back, mate on the edge.
triggers: [king and rook versus king, rook mate, bare king, basic mate, K+R]
related_pages: [patterns/mating-patterns/ladder-mate, patterns/mating-patterns/king-queen-mate, endgames/king-pawn-endings]
tags: [mate, endgame, rook, technique, opposition]
status: draft
updated: 2026-06-10
---

# King + Rook vs King

## When to use

You have king and rook against a bare king and no faster mate is available.
Forced win, at most ~16 moves with good technique. Slower and more exacting
than the queen mate — if you can promote to a queen instead, do that.

## The idea

The rook fences the king behind a rank (or file); your king does the real
work. The enemy king is pushed back one rank at a time: when the two kings
stand **directly facing each other** (one square between them — the
opposition), a rook check on that rank forces the enemy king back. Repeat
until it is mated on the edge.

## What to do

1. Rook cuts the king off on one rank; keep it far from the enemy king on
   its rank so it cannot be attacked.
2. Walk your king up the neighbouring file toward the enemy king.
3. **Kings face each other → rook checks → king retreats a rank.**
4. If the enemy king steps aside instead of facing yours, **make a waiting
   move with the rook along its rank** ("losing" one tempo) — the king must
   then face yours, and the check lands.
5. On the last rank, the same check is mate (your king covers the escape
   squares).

## Watch out for

- **Two stalemate traps:** king cornered with the rook sealing it but no
  check — e.g. White Ka6+Rb1 vs Ka8, Black to move, is stalemate
  (`k7/8/K7/8/8/8/8/1R6 b - - 0 1`). Always leave the fenced king a square
  to move to, or give check.
- Checking too early (kings not in opposition) lets the king zigzag and
  wastes many moves. Check only when the kings face each other.

## Examples

`4k3/8/4K3/8/8/8/8/7R w - - 0 1` — kings in opposition: 1.Rh8#. Verified.
Full technique from the centre: Examples 1–2 of the Capablanca notes
(`raw/chess-fundamentals-capablanca.md`) — mate in 10–11 from any start.
