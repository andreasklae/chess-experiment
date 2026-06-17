---
category: mates
description: Rook checks the edge-bound king while a knight protects the rook and a pawn protects the knight — a self-supporting hook of three units.
triggers: [hook mate, rook knight pawn mate, king on back rank with knight nearby]
related_pages: [mates/arabian-mate, mates/anastasia-mate, mates/back-rank-mate]
tags: [mate, rook, knight, pawn, edge]
template_pieces: [rook, knight, pawn]
template_king_zone: edge
template_exposed_king: true
status: draft
updated: 2026-06-11
---

# Hook mate

## When to use

The enemy king sits on the edge (often its back rank), you have rook +
knight + a pawn on that wing, and the king's own pawn blocks one of its
escape squares. Common when converting an endgame where you still have a
pawn chain.

## The idea

Three units form a self-supporting "hook": the **rook** checks the king
from the adjacent square on the edge line; the **knight**, one knight's
move away, protects the rook *and* covers the king's diagonal escape; the
**pawn** protects the knight. Nothing can be captured, nothing blocks —
the king's remaining squares are taken by the knight and its own pawn.

## What to do

1. Fix the enemy king on the edge with the rook (fence one line in front).
2. Plant the knight where it will both guard the rook's mating square and
   cover the king's diagonal flight — with your pawn one step behind,
   guarding the knight.
3. Deliver the rook check on the square next to the king. Mate.

The geometry off the e-file final picture: Re8+ against Ke7, knight f6
(guards e8, covers d7/g8... and is guarded by the e5-pawn), enemy pawn f7
blocking its own king.

## Watch out for

- Each link must hold: unprotected rook → king takes; unprotected knight →
  king takes it next and escapes through the hole.
- Count the king's squares with `chess__imagine_move` — if one is free,
  you have a check, not a mate; tighten the net first.

## Examples

`4R3/4kp2/5N2/4P3/8/8/8/8 b - - 0 1` — final picture: Re8 checks Ke7; Nf6
(protected by Pe5) guards e8 and covers d7/g8; Black's own f7-pawn blocks
the last square. Verified.
