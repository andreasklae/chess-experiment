---
category: patterns/mating-patterns
description: Basic mate with king and queen against a bare king — box the king to the edge with knight-move shadowing, bring your king up, mate. Under ten moves, but beware stalemate.
triggers: [king and queen versus king, bare king, queen mate, basic mate, K+Q]
related_pages: [patterns/mating-patterns/ladder-mate, patterns/mating-patterns/king-rook-mate, principles/avoid-stalemate]
tags: [mate, endgame, queen, technique]
status: draft
updated: 2026-06-10
---

# King + Queen vs King

## When to use

You have queen and king against a bare (or nearly bare) king — typically
right after promoting a pawn. This mate is always forced and should take
under ten moves. If you also have a rook, prefer the even simpler
[[patterns/mating-patterns/ladder-mate]].

## The idea

The queen alone cannot mate — the king must help. Phase 1: the queen shrinks
the enemy king's box and herds it to an edge. Phase 2: your king walks up.
Phase 3: mate on the edge with the king supporting the queen or sealing the
escape squares.

## What to do

1. **Place the queen a knight's-move away from the enemy king**, then mirror
   its moves, keeping that knight's-move distance. The king is pushed
   steadily to an edge — no checks needed.
2. **Stop shadowing when the king reaches the edge** — leave it two or three
   squares to shuffle between (this is where stalemate happens).
3. March your own king straight toward the enemy king.
4. When your king is close (one file/rank away), deliver mate: queen checks
   along the edge rank/file, or lands in front of the king supported by
   yours.

## Watch out for

- **Stalemate is the only way to ruin this.** While your king walks over,
  every quiet queen move must leave the enemy king at least one legal move.
  Example trap: White Qb6+Kc6 vs Ka8 with Black to move is stalemate
  (`k7/8/1QK5/8/8/8/8/8 b - - 0 1`). A cornered king with the queen a
  knight's-move away = danger; check with `chess__imagine_move` (it reports
  `stalemate`).
- Don't chase with aimless checks — each check should shrink the box or
  it is a wasted move. The shadowing method needs no checks at all.

## Examples

`7k/8/6K1/8/8/8/8/1Q6 w - - 0 1` — 1.Qb8# (king supports nothing here;
it seals g7/g8/h7). Verified mate.
Full technique from the centre: see Example 4 of the Capablanca notes
(`raw/chess-fundamentals-capablanca.md`): 1.Qc6 Kd4 2.Kd2 Ke5 3.Ke3 ... and
mates on move 8.
