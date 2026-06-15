---
category: patterns/mating-patterns
description: Knight + rook trap the king against the board's edge — the knight seals the two squares beside the king, the rook mates along the edge file or rank.
triggers: [anastasia, knight and rook mate, king on h-file, edge king, knight covers escape]
related_pages: [patterns/mating-patterns/arabian-mate, patterns/mating-patterns/hook-mate, patterns/deflection]
tags: [mate, knight, rook, edge]
template_pieces: [rook, knight]
template_king_zone: edge-file
status: draft
updated: 2026-06-11
---

# Anastasia's mate

## When to use

The enemy king is on the edge (typically the h-file after ...Kh7), you have
a knight that can reach the e7-type square (two files in from the king,
same wing), and a rook or queen that can deliver check along the edge file.

## The idea

A knight on e7 covers **both** g8 and g6 — the two inner escape squares of
a king on h7. With those sealed and the king's own pawn on g7 blocking the
third, a single rook check down the h-file is mate. The knight does the
quiet work; the rook only needs one open line.

## What to do

1. Get the knight to e7 (or the mirror square) **with the enemy king on
   the edge file** — often the knight arrives with check (Ne7+) forcing
   ...Kh7 first.
2. Clear or use the edge file: if a pawn shields the king (h7 at home),
   a sacrifice on that square (Qxh7+!? Kxh7) drags the king onto the file
   — count material vs the forced mate before sacrificing.
3. Rook (or queen) checks down the edge file — mate.

## Watch out for

- The knight must cover *both* inner squares: that only works from the
  e7-type square. A knight one square off covers only one.
- Check the edge file is genuinely clear for the rook and that nothing
  can interpose between rook and king.
- Confirm the final move reports `gives checkmate` in `chess__imagine_move`
  before any sacrifice that sets it up.

## Examples

`8/4N1pk/8/7R/8/8/8/8 b - - 0 1` — final picture: Ne7 covers g8/g6, the
black g7-pawn blocks g7, Rh5 mates on the h-file. Verified.
