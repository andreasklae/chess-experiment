---
category: patterns/mating-patterns
description: Two rooks (or queen+rook) mate a king in the open by two rules — fence before you check, and always check with the OTHER rook — leapfrogging the king to the edge. Fully forced, king not needed.
triggers: [two rooks, queen and rook, two major pieces, enemy king in the open, lawnmower mate, ladder]
related_pages: [patterns/mating-patterns/king-queen-mate, patterns/mating-patterns/king-rook-mate, patterns/mating-patterns/blind-swine-mate, patterns/mating-patterns/back-rank-mate]
tags: [mate, endgame, rook, queen, technique, recipe]
template_pieces: [rook, rook]
template_king_zone: edge
template_exposed_king: true
status: draft
updated: 2026-06-13
---

# Ladder Mate (two rooks, or queen + rook) — the drill

## When to use

You have two rooks, queen + rook, or two queens against a king in the
open. **The first mate to look for** — fully forced, needs no help from
your king, ~5–8 moves from anywhere.

## The idea — two rooks taking turns

One rook is the **fence**: it controls a whole rank so the king cannot
step back across it. The other is the **checker**: it checks along the
king's rank to shove the king one rank toward the edge. Two principles —
break either and the king slips out:

- **Fence before you check.** A check only drives the king forward if it
  has nowhere backward to go, so a rook must hold the rank *behind* the
  king before you check. Making the fence is a quiet move, not a check.
- **Keep both rooks far from the king** (opposite wing) so it can never
  walk over and capture one.

## How to apply it — reason, don't memorise squares

You work out the move yourself and **verify with `chess__imagine_move`**.
Its **Enemy king mobility: before → after** line is your compass: a good
driving move makes that number **go down** or gives check; if it goes
**up**, you broke the fence — reject it. Each turn:

1. King touching a rook? Slide that rook far away first (even if defended).
2. No fence on the rank just behind the king? Make one (a quiet move).
3. Fence held → find where a rook checks the king's rank from far away.
   Imagine candidates; play the one that checks or most cuts king mobility
   without hanging or repeating.
4. The king steps toward the edge and the rooks swap roles (the checker is
   now rearmost — the new fence). Repeat to the last rank, where the check
   is mate. *Advancing the fence rook to check is fine **if** a rook still
   sits behind the king afterwards — the mobility number confirms it.*

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
