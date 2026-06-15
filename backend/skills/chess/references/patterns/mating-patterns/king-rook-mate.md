---
category: patterns/mating-patterns
description: K+R vs K as a six-rule drill — fence with the rook, march the king, check only in opposition, slide away when attacked, waiting move when dodged.
triggers: [king and rook versus king, rook mate, bare king, basic mate, K+R]
related_pages: [patterns/mating-patterns/ladder-mate, patterns/mating-patterns/king-queen-mate, endgames/king-pawn-endings]
tags: [mate, endgame, rook, technique, opposition, recipe]
status: draft
updated: 2026-06-13
---

# King + Rook vs King — the drill

## When to use

King and rook against a bare king. Forced win ≤16 moves — but only by the
drill. Freestyle checking does NOT work (it walks into the 50-move rule).

## The idea

The rook is a fence the king may never cross; your king does the pushing.
The enemy king only retreats a rank when checked **while the kings face
each other** — every other check is a wasted move.

**Your compass:** `chess__imagine_move` prints **Enemy king mobility:
before → after**. Real progress shrinks the king's box, so a good move
holds or lowers that number (a check drops it sharply); a move that raises
it is drifting — pick another. Watch for `stalemate` whenever the king has
few squares left.

## What to do — apply the FIRST rule that matches, every turn

1. **Rook not yet fencing?** Put it on the rank directly below the enemy
   king (its rank minus one, from a file far from both kings). Done for
   the turn.
2. **Enemy king attacks your rook?** Slide the rook to the far end of the
   SAME rank (a- or h-file, whichever is farther). The fence holds. Done.
3. **Kings directly facing each other** (same file, exactly one rank
   between, your king on the fence rank)? **Rook checks on the enemy
   king's rank.** It must retreat. Next turn, move the fence up (rule 1
   onto the new rank). This is the ONLY time you check.
4. **Enemy king moved sideways, not facing you?** If your king can step
   toward it (staying on your side of the fence), do that. If your king
   already mirrors it (same file), the enemy just dodged: make a
   **waiting move — rook one square along the fence rank** (stay far from
   the king). Now it must step into opposition and rule 3 fires.
5. **Enemy king on the edge rank?** Same rules; rule 3's check is mate
   once your king stands one rank away facing it.

## Watch out for

- Never check outside rule 3. Never move the rook off the fence rank
  except rules 2–4.
- Stalemate trap when the king is cornered: `k7/8/K7/8/8/8/8/1R6 b` is
  stalemate — when the enemy king has ≤2 squares, prefer rule-3 checks
  and watch `chess__imagine_move` for `stalemate`.
- A `repeats!`/`draw:repetition` flag means you broke the drill — re-read
  this page and apply rule 1.

## Examples

`4k3/8/4K3/8/8/8/8/7R w - - 0 1` — rule 3 with the enemy king on the edge:
1.Rh8#. Verified. Full worked mate: Capablanca Examples 1–2 in
`raw/chess-fundamentals-capablanca.md` (mate in 10–11 from anywhere).
