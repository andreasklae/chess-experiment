---
category: mates
description: Knight mates a king fully boxed in by its own pieces, usually in the corner. Includes the forced Philidor's legacy sequence (double check, queen sacrifice, knight mate).
triggers: [smothered mate, king in corner behind own pieces, knight near enemy king, philidor]
related_pages: [mates/arabian-mate, tactics/deflection]
tags: [mate, knight, corner, forcing-sequence]
template_pieces: [knight, queen]
template_king_zone: back-rank
template_min_own_blockers: 2
status: draft
updated: 2026-06-11
---

# Smothered mate

## When to use

The enemy king sits in (or near) a corner with its own pieces filling the
escape squares — typically Kg8/h8 with Rf8, g7, h7 — and you have a knight
that can reach f7/h6 (or the mirror squares). With queen + knight this can
often be **forced from a normal-looking position**.

## The idea

A king whose neighbours are all its own pieces needs only a check it
cannot block or capture: a knight ignores the wall entirely. Your other
pieces don't attack the king — they force its own army to imprison it.

## What to do — the forced sequence (Philidor's legacy)

With Q + N against a castled king (king g8, rook f8, pawns g7/h7):

1. Check on the a2–g8 diagonal (e.g. Qe6+). King must go h8 (f8 is its own
   rook).
2. Knight check f7+. King back to g8 (forced).
3. Knight to h6 — **double check** (knight + rediscovered queen). Double
   check cannot be blocked; king to h8 (forced).
4. **Queen sacrifice g8+!** Rook must take (king can't — knight covers g8).
5. Knight f7 — mate. The rook you forced to g8 is the final blocker.

Every black move is forced — verify each step with `chess__imagine_move`
before starting, then play it straight through.

## Watch out for

- Step 1 only forces Kh8 if f8 is blocked by Black's own piece.
- The double check at step 3 is what makes it work — without the queen
  behind the knight, the king just takes or runs.
- If Black can interpose or capture the queen with a *different* piece at
  step 4, recount before sacrificing.

## Examples

`5rk1/6pp/8/6N1/8/8/8/4Q1K1 w - - 0 1` — 1.Qe6+ Kh8 2.Nf7+ Kg8 3.Nh6+ Kh8
4.Qg8+ Rxg8 5.Nf7#. Verified.
Final picture: `6rk/5Npp/8/8/8/8/8/8 b` — knight f7 mates the smothered king.
