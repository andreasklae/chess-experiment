---
category: patterns/mating-patterns
description: Rook checks the cornered king from the adjacent diagonal square while a knight protects the rook and covers the corner's escape square.
triggers: [arabian, rook and knight corner mate, cornered king, knight protects rook]
related_pages: [patterns/mating-patterns/anastasia-mate, patterns/mating-patterns/hook-mate]
tags: [mate, knight, rook, corner]
template_pieces: [rook, knight]
template_king_zone: corner
status: draft
updated: 2026-06-11
---

# Arabian mate

## When to use

The enemy king is in (or being driven to) a corner, and you have rook +
knight working on that wing. One of the oldest recorded mates — and one of
the few where rook and knight need no other help at all.

## The idea

A knight placed two squares diagonally from the corner (f6 against h8)
does two jobs at once: it covers the corner's diagonal escape square (g8)
**and** protects a rook standing on the square diagonally adjacent to the
king (h7 or g7). The rook gives check; the king has nowhere to go and
cannot take the protected rook.

## What to do

1. Drive the king toward the corner with rook checks (see
   [[patterns/mating-patterns/king-rook-mate]] for the fence technique).
2. Post the knight on the f6-type square (two diagonal steps from the
   corner). It is safe there from the bare king.
3. Land the rook on h7 or g7 — adjacent to the king, protected by the
   knight. Check; mate.

## Watch out for

- The rook must be **protected by the knight** when it touches the king —
  on the wrong square the king simply captures it.
- If the king escapes along the rank/file instead, your rook fence was
  missing — re-establish it before posting the knight.
- As always: only commit when `chess__imagine_move` reports
  `gives checkmate`.

## Examples

`7k/7R/5N2/8/8/8/8/8 b - - 0 1` — final picture: Nf6 covers g8 and protects
Rh7; the king on h8 is mated. Verified.
