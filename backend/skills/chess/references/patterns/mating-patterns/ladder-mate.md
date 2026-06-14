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

## The two rules that make it work

The whole mate is **two rooks taking turns**: one is always the **fence**
(it cuts off a whole rank so the king cannot retreat), the other is the
**checker** (it checks along the king's rank to shove the king one rank
toward the edge). Two iron rules — break either and the king escapes:

- **RULE A — fence before you check.** A check only drives the king
  forward if it has nowhere backward to go. So one rook must sit on the
  rank *behind* the king (between the king and where it came from) BEFORE
  you check. Placing that fence is not a check — it is a quiet move.
- **RULE B — check with the OTHER rook, never the fence rook.** The fence
  rook stays put. The free rook checks along the king's current rank, from
  **as far from the king as possible** (the opposite wing), so the king
  can never step over and capture it.

## What to do — apply the FIRST rule that matches, every turn

1. **King is touching one of your rooks?** It will capture it next move.
   Slide that rook along its rank to the far wing (a- or h-file), away
   from the king. (Do this even if the rook is defended — a touched rook
   can't ladder.) Nothing else this turn.
2. **No rook on the rank directly behind the king?** Build the fence
   (RULE A): put a rook on that rank, on the far wing. **This is a quiet
   move, not a check.** Nothing else this turn.
3. **Fence is in place?** Check with the OTHER rook (RULE B): move it onto
   the king's rank, far from the king. The king is forced one rank toward
   the edge.
4. **After the king steps forward:** the rook that just checked is now
   behind the king — it becomes the new fence. Go back to rule 3 and check
   with the other rook. Check, step, check, step — the "ladder" — until
   the king reaches the last rank, where the check is mate.

## The finish

When the king is on the **8th rank** with your fence holding the 7th, the
king is trapped on the edge. Bring the free rook to the 8th rank far from
the king — that check is mate. **Never check with the fence rook to do
it** (that frees the 7th rank and the king runs back down).

## Watch out for

- A `repeats!`/`draw:repetition` flag = you broke the rhythm (probably
  checked with the fence rook, or checked with no fence). Re-read RULE A/B
  and place a fence this turn.
- **The single most common mistake: checking with the fence rook.** It
  feels like progress (it's a check!) but it abandons the cut-off rank and
  the king walks straight back. Always check with the *other* rook.
- Keep both rooks on the **opposite wing from the king** so it can never
  touch them (rule 1). If it does touch one, sliding it away (rule 1)
  always comes before checking.
- With queen + rook the queen ladders the same way; confirm the last
  check is `gives checkmate` (not stalemate) with `chess__imagine_move`.

## Example (verified, king flees toward the centre)

`8/8/3k4/8/8/8/R7/1R4K1 w - - 0 1` — king d6, rooks a2 and b1.

`1.Rb5 Ke6 2.Ra6+ Ke7 3.Rb7+ Ke8 4.Ra8#`

- **1.Rb5** builds the fence on rank 5 (a quiet move — king can't come
  down). **2.Ra6+** checks with the *other* rook. **3.Rb7+** leapfrogs:
  the b-rook checks rank 7 while a6 is now the fence. **4.Ra8#**.
- The rooks alternate a/b files (opposite wing from the king) and **the
  fence rook never gives the check**.
