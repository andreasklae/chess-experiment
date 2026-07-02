---
category: endgames
description: Passed pawns — when to push, when to escort with the king, rook behind the passer (Tarrasch rule), blockades, outside/protected/connected passers, and the promotion blunders that throw wins away.
triggers: [passed pawn, passer, promote, promotion, push the pawn, pawn endgame, outside passed pawn, blockade, rook behind, seventh rank, queening, winning endgame, bare king, convert]
related_pages: [endgames/king-pawn-endings, endgames/rook-endings, principles/avoid-stalemate, principles/material-and-trading]
tags: [endgame, passed-pawn, promotion, technique]
status: draft
updated: 2026-07-02
---

# Passed pawns: the winning plan IS promotion

## When to use
Any endgame where you have (or can create) a passed pawn — especially when you
are ahead and wondering "what now?". Against a bare or near-bare king, this
page IS the plan; checks and piece-shuffling achieve nothing and feed the
50-move draw.

## The idea
A passed pawn has no enemy pawn to stop it — **only pieces can**, so it ties
the opponent down or promotes ("a criminal to be kept under lock and key" —
Nimzowitsch). A far-advanced passer is often worth a piece. Promotion converts
a small edge into an unstoppable one: queen = mate soon.

## What to do
1. **Decide the escort before pushing.** A pawn pushed ahead of its support
   gets rounded up. Standard escorts: your **king one step ahead of the pawn**
   (king first, pawn behind — see `endgames/king-pawn-endings`), or your
   **rook BEHIND it** (Tarrasch rule: the rook gains scope as the pawn runs;
   from in front it blocks its own pawn). Then push every move you can.
2. **Against a bare king: march, don't check.** Every move should either push
   the passer or step your king toward its path. A knight/bishop only shields
   the pawn's next square. Checks that don't mate are wasted tempi.
3. **Two ways to win with the outside passer:** push it to DECOY the enemy
   king away, then eat the other wing with your king. You don't always promote
   the passer itself — its job can be to pull the defender off.
4. **Connected passers:** advance them side by side (same rank) — abreast they
   cannot be blockaded.
5. **Facing an enemy passer: blockade it,** ideally with a knight (loses the
   least and can't be chased off the square in front), king in the endgame, or
   your rook BEHIND it (Tarrasch rule works for defense too).

## Watch out for
- **Promoting into a capture** — check the promotion square with
  `chess__imagine_move` first; a new queen that is immediately taken lost you
  a pawn, not gained a queen.
- **Stalemate with the new queen** near a bare king — read
  `principles/avoid-stalemate` before quiet moves in K+Q endings.
- **Wrong rook pawn + bishop:** if your ONLY pawn is a rook pawn and your
  bishop does not control its promotion corner, the defender parks the king
  in the corner and it is a DRAW — keep another pawn alive, or steer the king
  race accordingly.
- **The 50-move rule is ticking.** Shuffling pieces "safely" while winning is
  how won endings drain into draws. Progress = pawn pushed or king advanced.

## Examples
- K+N+P vs K (own game 9eddc039, 2026-07-02): 15 moves of knight checks and
  shuffles with the winning plan being simply e4-e5-e6… with Kd6 escorting.
  The knight's only job: guard the square in front of the pawn.
