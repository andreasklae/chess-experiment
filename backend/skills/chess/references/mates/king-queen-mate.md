---
category: mates
description: K+Q vs lone king by the BOX METHOD — shrink the confinement box toward an edge, march your king in, then mate. Stalemate is the only way to fail.
triggers: [king and queen versus king, bare king, queen mate, basic mate, K+Q]
related_pages: [mates/two-rook-ladder-mate, mates/king-rook-mate, principles/avoid-stalemate]
tags: [mate, endgame, queen, technique, recipe, basic-mate]
status: draft
updated: 2026-06-17
---

# King + Queen vs King — the box method

## When to use

Queen + king against a lone king — usually right after promoting. Forced
mate in under ten moves. If you also have a rook, the
[[mates/two-rook-ladder-mate]] is even simpler.

## The idea — the confinement box

The lone king lives in a **box**: the rectangle bounded by the board edges
and the ranks/files your queen cuts off. `chess__show_position` draws this
box (cells marked `·`) and the radar reports its area. **Two jobs, alternating,
win the game:**

1. **Shrink the box** — push the king toward the nearest edge with the queen.
2. **March your king in** — the queen alone cannot mate; your king must arrive
   to support the final blow.

The single biggest failure is shuffling the queen forever and never bringing
the king. **Watch the box area and the king-distance every move: both must
keep dropping.**

## What to do — three phases; read the radar to know which you are in

**Phase 1 — shrink (queen only):** put the queen a **knight's-move** from the
enemy king, on the side toward the nearest edge, so the box gets smaller. A
knight's-move is the magic distance: close enough to confine, never adjacent
(adjacent and unprotected = the king captures it; adjacent with no escape =
stalemate). No checks needed — checks just shove the king around without
shrinking the box. Each queen move the box area must go DOWN.

**Phase 2 — march (king walks, queen waits):** the moment the king is boxed
on an edge, **STOP moving the queen** and walk your own king one square toward
the enemy king every turn until it is **2 squares away**. Moving the queen now
just lets the king shuffle and risks stalemate — the radar will tell you to
march.

**Phase 3 — mate:** with your king close, deliver the mate — queen to the edge
line beside the king, protected by your king, so the king has no square.
Confirm `gives checkmate` with `chess__imagine_move`.

This works in **all four directions** — drive to whichever edge (rank 1, rank
8, the a-file, or the h-file) the king is already nearest; the box and the
radar name it for you.

## Watch out for

- **Stalemate is the ONLY way to fail.** A quiet queen move that leaves the
  king zero legal squares but no check is a draw. When the enemy king is down
  to one square, do NOT take it with a quiet move — give check, or march your
  king. The radar warns you; always confirm the final move says
  `gives checkmate`, never `stalemate`, in `chess__imagine_move`.
- **Never put the queen adjacent to the lone king unless your king defends
  that square** — the king just captures it.
- **Don't shuffle the queen when the king is already on an edge.** That is the
  no-progress loop that draws by repetition. March your king.

## Examples

`7k/8/6K1/8/8/8/8/1Q6 w - - 0 1` — phase 3: kings close, **1.Qb8#**. Verified.

`8/8/8/4k3/8/8/8/3QK3 w - - 0 1` — full mate from the centre: shrink the box
driving the king to an edge, march your king up behind it, then mate on the
edge. The radar names the phase each move.
