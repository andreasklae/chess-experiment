---
category: patterns/mating-patterns
description: The queen mates from a square adjacent to the enemy king whose remaining escape squares are blocked by its own pieces — epaulette, dovetail, and swallow's-tail are the same idea in three dressings.
triggers: [epaulette, dovetail, swallow tail, guéridon, cozio, queen next to king, king blocked by own pieces]
related_pages: [patterns/mating-patterns/king-queen-mate, principles/avoid-stalemate]
tags: [mate, queen, contact, own-piece-block]
template_pieces: [queen]
template_king_zone: any
template_min_own_blockers: 2
template_max_king_moves: 3
template_exposed_king: true
status: draft
updated: 2026-06-11
---

# Queen contact mates (epaulette · dovetail · swallow's tail)

## When to use

The enemy king has two or more of its escape squares occupied by **its own
pieces**, and your queen can land on a square adjacent to it, protected or
out of the king's reach-with-recapture. Very common right after a king is
forced out of its castle, or when defenders crowd around their king.

## The idea

A queen standing next to the king covers five of its eight neighbouring
squares by herself. If the king's own pieces fill the rest, that single
queen move is mate. Named variants are just which squares the king's own
army blocks:

- **Epaulette:** rooks on both sides of the king (f8 and h8 around g8) —
  queen mates from the front (g6/g7-type square).
- **Dovetail (Cozio):** two own pieces on the diagonal-rear squares —
  queen mates from the adjacent diagonal.
- **Swallow's tail (guéridon):** two own pieces behind the king's
  shoulders — queen mates from directly in front.

## What to do

1. Spot kings whose neighbours are their own pieces — every such piece is
   a wall you don't have to build.
2. Find the adjacent square the queen covers all the *free* neighbours
   from. It usually needs protection (a pawn, knight, or your king) unless
   distance protects it.
3. Force the picture if it's one move away: a check that drives the king
   beside its own rook, or a deflection that fills an escape square, often
   completes it.

## Watch out for

- The queen's landing square must be defended or untouchable — adjacency
  means the king can capture an unprotected queen.
- Don't confuse "many blocked squares" with mate: one free square = check
  only. Count with `chess__imagine_move`.

## Examples

Epaulette: `5rkr/8/6Q1/8/8/8/8/6K1 b` — Qg6 mates between the rooks.
Dovetail: `8/8/8/8/6p1/5qk1/7Q/6K1 b` — Qh2 mates; Black's own queen and
pawn block the tail squares. Both verified.
