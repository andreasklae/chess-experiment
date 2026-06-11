---
category: patterns/mating-patterns
description: Two major pieces mate by alternating rank-checks — fence and check, leapfrogging to the edge. Fully forced, king not needed. Includes the exact two-move finish.
triggers: [two rooks, queen and rook, two major pieces, enemy king in the open, lawnmower mate, ladder]
related_pages: [patterns/mating-patterns/king-queen-mate, patterns/mating-patterns/king-rook-mate, patterns/mating-patterns/blind-swine-mate, patterns/mating-patterns/back-rank-mate]
tags: [mate, endgame, rook, queen, technique, recipe]
template_pieces: [rook, rook]
template_king_zone: edge
template_exposed_king: true
status: draft
updated: 2026-06-11
---

# Ladder Mate (two rooks, or queen + rook) — the drill

## When to use

You have two rooks, queen + rook, or two queens against a king in the
open. **The first mate to look for** — fully forced, needs no help from
your king, ~5–8 moves from anywhere.

## What to do — apply the FIRST rule that matches, every turn

1. **Neither piece adjacent (in rank) to the enemy king?** Put piece A on
   the rank directly below the king's rank — the fence. Done.
2. **Enemy king attacks (or next move can attack) either piece?** Slide
   that piece along its own rank to the far edge (a/h-file). Fence
   intact. Done.
3. **Fence in place (piece A one rank below the king)?** Check with piece
   B **on the king's rank**, from far away. The king must retreat one
   rank toward the edge. Done.
4. After the king retreats: the old checking piece is now the new fence —
   go back to rule 3 with the other piece. Repeat: check, fence, check,
   fence — the "ladder".

## The finish (the step most often fumbled)

When the king reaches the **last rank**: your fence piece holds the
second-to-last rank, so the king is trapped on the edge. Make sure the
checking piece is **far from the king on the last rank's file-line**,
then check on the last rank — that check is mate. Two-move template:
fence on rank 7 → slide the other piece far (e.g. to h-file) if the king
is near it → check on rank 8 = mate. **Do not shuffle: each move must
either check (rule 3), re-fence (rule 1), or slide away (rule 2).**

## Watch out for

- A `repeats!`/`draw:repetition` flag = you've broken the drill. Apply
  rule 1 explicitly that turn.
- Never let the king touch a piece: rule 2 ALWAYS beats rule 3 in
  priority.
- With queen + rook the queen ladders the same way; confirm the last
  check is `gives checkmate` (not stalemate) with `chess__imagine_move`.

## Examples

`8/8/8/3k4/R7/8/1R6/7K w - - 0 1` — 1.Rb5+ Kc6 (attacks the rook) 2.Rh5!
(rule 2) Kd6 3.Ra6+ Ke7 4.Rh7+ Kf8 5.Ra8#. Verified.
Final picture: `R5k1/1R6/8/8/8/8/8/8 b` — fence on 7, mate on 8.
