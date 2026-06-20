---
category: mates
description: K+B+N vs K — the HARDEST basic mate (forced, ≤33 moves). Mate ONLY in the corner of the bishop's colour. Won by a MULTI-MOVE plan, not single moves — shrink the king's net toward the right corner. Use chess__imagine_line to see maneuvers; watch the 50-move rule and stalemate.
triggers: [king bishop knight versus king, bishop and knight mate, bare king, basic mate, K+B+N, wrong corner, right corner, W manoeuvre, net shrinking]
related_pages: [mates/king-two-bishops-mate, mates/king-rook-mate, strategy/convert-advantage]
tags: [mate, endgame, bishop, knight, technique, corner, basic-mate]
status: draft
updated: 2026-06-19
---

# King + bishop + knight vs King — drive to the bishop's corner

## When to use

K + bishop + knight vs a bare king. Forced (≤33 moves) but the hardest basic
mate. **Mate is possible ONLY in a corner of your BISHOP's colour** ("right"
corner): light bishop → a8/h1; dark bishop → a1/h8. The other two corners are
"wrong" — you cannot mate there, so never herd the king toward them. If you
have a pawn, promote it and mate with the queen instead.

## The idea — shrink the net toward the right corner

There is no short recipe; this mate is a **multi-move plan**, not a sequence of
single best moves. Think of the bare king as trapped in a **net** — the squares
it can still reach (`chess__show_position` draws it as `*`, and reports its
size). Your three pieces cooperate to **shrink that net toward the right
corner**: the bishop cuts a long diagonal, the **knight covers the
opposite-coloured squares the bishop can't**, and your king does the pushing.
The king cannot escape across the bishop's diagonal, so you walk that wall up
the board with your king alongside.

## What to look for / how to plan

1. **The target corner** — the radar names it (your bishop's colour). Keep
   every move pointed there; ignore the wrong corners.
2. **The net size** — it must trend DOWN. A move that grows the `*` net gave the
   king room; reject it. A move that shrinks it is progress.
3. **Plan several moves at once with `chess__imagine_line`.** Type a maneuver
   (your moves + the king's likely replies) and read the `net` column: does it
   fall toward the corner? These mates are won by finding a *maneuver*, not one
   move. The knight especially moves in a looping "W" path along the edge to
   herd the king down — try it in imagine_line and watch the net.
3. **Three phases:** (1) drive the king to ANY edge; (2) walk it ALONG the edge
   to the right corner (the hard part — the knight does the shepherding, the
   bishop seals the diagonal, the king blocks); (3) deliver mate in the corner.

## Watch out for

- **Wrong corner = no progress.** Driving toward a corner of the bishop's
  opposite colour can never mate. Re-check the named target.
- **The 50-move rule** — this mate is long; make steady progress (net shrinking),
  never shuffle. A capture/pawn move resets the clock but you have none.
- **Stalemate** — near the corner, confirm `gives checkmate` (never
  `stalemate`) in `chess__imagine_move` before any quiet move.
- **Never hang the bishop or knight** to the king; don't leave a bishop next to
  the king undefended.

## Examples

Right-corner mates (light bishop, a8 — verified): `k7/2K5/8/1N6/8/8/8/7B b - - 0 1`
(Bh1 mates a8, Nb5 covers a7, Kc7 covers b7/b8) and `k7/3N4/K7/8/4B3/8/8/8 b`
(Be4 mates a8). Dark bishop mirrors into a1 / h8.
