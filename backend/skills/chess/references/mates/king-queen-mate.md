---
category: mates
description: K+Q vs K — the SAME drill as king-and-rook (fence, keep the kings close, mate in opposition on the edge); the queen is a rook that also cuts diagonals, so it is faster, but watch stalemate.
triggers: [king and queen versus king, bare king, queen mate, basic mate, K+Q]
related_pages: [mates/king-rook-mate, mates/two-rook-ladder-mate, principles/avoid-stalemate]
tags: [mate, endgame, queen, technique, opposition, recipe, basic-mate]
status: draft
updated: 2026-06-17
---

# King + Queen vs King — same as king-and-rook, with a queen

## When to use

Queen + king against a lone king — usually right after promoting. Forced
mate in under ten moves.

## The idea — it is the king-and-rook drill

**A queen mates exactly the way a rook does** ([[mates/king-rook-mate]]):
fence the enemy king onto fewer lines, keep your two kings close (within 2-3),
march to **opposition**, then one queen check along the edge is mate. Read the
K+R page — every rule there applies, because **the queen does everything a
rook does** (fence a rank or file, check to push the king back, mate in
opposition on the edge).

The queen is only *better*: it also cuts off **diagonals**, so it confines the
king into a smaller box faster, and it can fence from more squares. So the
mate is quicker — but the method is identical: **keep the kings together and
walk the enemy king to an edge.** The radar's drill-state line guides you the
same way it does for the rook.

## What to do — the same ONE rule as king-and-rook

Use the **king-and-rook rule** ([[mates/king-rook-mate]] "What to do"), reading
"queen" for "rook" — the queen confines exactly like a rook (it just also cuts
diagonals, so it boxes the king faster). Each move (`chess__imagine_move`
reports the box area and whether the queen is *protectable in time*):

1. **Is a move flagged `checkmate`?** → play it.
2. **Does a tighter queen square exist that your king can still defend in
   time?** → move the queen to the tightest such square. Don't move the king;
   don't loosen the box.
3. **Otherwise** → step your king one square toward the enemy king.

**The one extra danger with a queen is STALEMATE** (it covers so many squares):
never make a quiet move that leaves the lone king zero legal moves without
check — confirm `gives checkmate`, not `stalemate`, in imagine_move.

## Watch out for — STALEMATE (much easier with a queen)

The queen controls so many squares that it is easy to leave the lone king with
**no legal move and no check = stalemate = draw.** This is the one real danger.

- When the enemy king is near an edge or corner with few squares, **do not
  snatch its last square with a quiet queen move** — give a check, or march
  your king instead. (A queen confines so well that the careless move which
  would be fine with a rook can be stalemate with a queen.)
- When the enemy king has **one legal move**, the radar shouts STALEMATE
  DANGER. Heed it: confirm the move says `gives checkmate` (never `stalemate`)
  in `chess__imagine_move` before committing.
- **Never put the queen on a square next to the lone king unless your own king
  defends it** — otherwise the king just captures the queen.

## Examples

`7k/8/6K1/8/8/8/8/1Q6 w - - 0 1` — kings close, **1.Qb8#**. Verified.

`4k3/8/4K3/8/8/8/8/7Q w - - 0 1` — opposition on the edge (Ke6 vs ke8):
**1.Qh8#** — the same edge mate the rook delivers from the same position.
Verified.
