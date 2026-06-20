---
category: patterns/mating-patterns
description: K+Q vs K as a three-phase drill — knight's-move shadowing to the edge, stop and bring the king, mate with king support. Stalemate is the only way to fail.
triggers: [king and queen versus king, bare king, queen mate, basic mate, K+Q]
related_pages: [patterns/mating-patterns/ladder-mate, patterns/mating-patterns/king-rook-mate, principles/avoid-stalemate]
tags: [mate, endgame, queen, technique, recipe]
status: draft
updated: 2026-06-11
---

# King + Queen vs King — the drill

## When to use

Queen and king against a bare (or nearly bare) king — typically right
after promoting. Forced mate in under ten moves. If you also have a rook,
prefer the even simpler [[patterns/mating-patterns/ladder-mate]].

## What to do — three phases, in order

**Phase 1 — shrink (queen only, NO checks needed):**
1. Place the queen a **knight's-move away** from the enemy king (e.g.
   king d5 → queen c3, e3, b4, or f4 — pick the side toward the centre of
   the board so the king is pushed to the nearer edge).
2. **Mirror means: copy the king's last move direction.** King steps
   toward a1 → queen steps one square toward a1 too, recreating the
   knight's-move shape on the same side. Copying the direction is what
   shrinks the box; restoring knight-distance on a different side undoes
   your progress.
3. **Never move the queen back to a square she just left.** If the king
   dances so that mirroring would repeat your previous square, the queen
   has done all she can: leave her standing and **march YOUR king one
   square toward the enemy king instead** (phase 2 starts early).
   Oscillating queen moves are how this drill draws by repetition.
4. **STOP shadowing the moment the king reaches the edge.** Park the
   queen where it confines the king to two or three edge squares, and do
   not move her again until phase 3. One more shadow step here is the
   classic stalemate.

**Phase 2 — march:** walk your king straight toward the enemy king, one
square a turn, until it stands on the adjacent rank/file (a knight's-move
or one diagonal step away from the enemy king).

**Phase 3 — mate:** queen checks on the edge rank/file (supported by your
king or from distance), or lands directly in front of the king protected
by yours. Confirm `gives checkmate` with `chess__imagine_move`.

## Watch out for

- **Stalemate, the only real risk:** while your king marches (phase 2),
  every quiet move must leave the enemy king at least one square.
  `k7/8/1QK5/8/8/8/8/8 b` is stalemate — queen a knight's-move from a
  *cornered* king with your king close is exactly the trap. If
  `chess__imagine_move` reports `stalemate` on any candidate, pick another.
- Aimless checks make no progress and risk `repeats!` — the drill needs
  no checks until the final move.

## Examples

`7k/8/6K1/8/8/8/8/1Q6 w - - 0 1` — phase 3: 1.Qb8#. Verified.
Full worked mate from the centre: Capablanca Example 4 in
`raw/chess-fundamentals-capablanca.md` (1.Qc6 Kd4 2.Kd2 ... mate on move 8).
