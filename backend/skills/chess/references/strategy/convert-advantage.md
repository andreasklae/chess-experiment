---
category: strategy
description: The standard plan for winning a won position — trade pieces (not pawns), make a passed pawn, promote it, mate with the queen. Simple beats clever; the game must end before the move cap.
triggers: [material advantage, winning position, up a piece, up a rook, how to convert, opponent has bare king, ahead in material]
related_pages: [mates/two-rook-ladder-mate, mates/king-queen-mate, endgames/king-pawn-endings, principles/avoid-stalemate]
tags: [strategy, conversion, endgame, plan]
status: draft
updated: 2026-06-17
---

# Converting a material advantage

## When to use

The material balance clearly favours you (a piece or more, or a decisive
pawn advantage). Your problem is no longer "how do I get an edge" but **"how
do I end this game"**. Read this page once and adopt its plan; do not
improvise a new idea every turn.

## The idea

A won position wins itself only if you force the end. The reliable path is
always the same staircase:

**trade pieces → push a passed pawn → promote → basic mate.**

Every trade of *pieces* (not pawns) makes your advantage proportionally
bigger and the defence harder. A new queen plus the
[[mates/king-queen-mate]] or
[[mates/two-rook-ladder-mate]] finishes everything. **Prefer the
simple, slow-looking win over the clever mating hunt** — promoting a pawn
in five moves beats searching for a tricky mate you may miscalculate.

## What to do

- **Trade pieces, keep pawns.** Offer exchanges of queens/rooks/minors when
  ahead; avoid trading your last pawns (a bare minor piece cannot win).
- **Create a passed pawn** (see [[endgames/king-pawn-endings]]) and escort
  it with your king — king *in front of* the pawn.
- **Promote, then mate by the book.** Queen + ladder/box technique; no
  improvising.
- **Give every check a job.** A check that doesn't win material, force the
  king toward the edge, or gain a tempo for your plan is a wasted move —
  shuffling checks is how won games become draws.
- **The game has a move budget** (drawn by rule if it drags on). When the
  position is won, every move must make measurable progress: pawn closer to
  promotion, king closer, enemy king's box smaller.

## Watch out for

- **Eliminate the opponent's threats before mating.** A winning position is
  lost by tunnel-visioning on your own mate while the opponent makes a real
  threat. The sharpest case: an enemy pawn one move from **promoting** — let
  it queen and the new major shatters your mating net. Each move, check what
  the opponent threatens *next* move; if it is serious (a promotion, a fork, a
  mate against you), neutralise it FIRST (capture/block the pawn, cover the
  square, escape the fork), then resume the mate. `chess__imagine_move` and
  the `chess__show_position` radar surface these threats — look before you
  push for mate.
- [[principles/avoid-stalemate]] — the standard way to throw away a bare-king
  position.
- Don't grab pawns that open counterplay against your king; the passed pawn
  matters more.
- Threefold repetition: repeating checks repeats positions. If you have
  checked twice to no effect, stop checking and improve a piece.
