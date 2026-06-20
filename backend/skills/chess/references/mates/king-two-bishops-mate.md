---
category: mates
description: K+2B vs K — FORCED mate (≤19 moves). Two opposite-coloured bishops form a moving wall on ADJACENT diagonals; march the king up and shrink the king's net into ANY corner. Won by a multi-move plan — use chess__imagine_line. Watch stalemate.
triggers: [king and two bishops versus king, two bishops mate, bare king, basic mate, K+2B, bishop pair mate, drive king to corner, net shrinking]
related_pages: [mates/king-bishop-knight-mate, mates/king-rook-mate, strategy/convert-advantage]
tags: [mate, endgame, bishop, technique, corner, basic-mate]
status: draft
updated: 2026-06-19
---

# King + two bishops vs King — wall them into a corner

## When to use

King + two **opposite-coloured** bishops vs a bare king. Forced in ≤19 moves
(Capablanca, Ex. 3). Unlike the rook/queen (which mate on any edge), the bishops
must drive the king into a **corner** — but ANY corner works. Two
**same-coloured** bishops cannot mate (draw). With a pawn, promoting to a queen
first is simpler.

## The idea — a moving wall that shrinks the net

The two bishops, side by side on **adjacent diagonals**, build a wall the king
cannot cross. Picture the king trapped in a **net** — the squares it can still
reach (`chess__show_position` draws it as `*` and gives its size). You advance
the wall with your king right behind it, **shrinking the net into a corner**;
then a bishop mates while your king guards the escape squares. Capablanca: "the
King's co-operation is essential" — your king must lead, not watch.

## What to look for / how to plan

1. **Bishops on ADJACENT diagonals**, side by side — that is the wall. If they
   drift apart the net has a gap and the king leaks through; bring them back
   together.
2. **The net must shrink.** Watch the `*` count in `chess__show_position`: a
   move that lowers it is progress; one that raises it gives the king room —
   reject it. Bring your king toward the corner the king is being pushed to.
3. **Plan maneuvers with `chess__imagine_line`** — type several of your moves
   plus the king's likely replies and read the `net` column falling toward the
   corner. This mate is a multi-move plan, not single best moves.
4. **"Mark time" with a bishop** when the king is nearly cornered but a king
   step or wall push would stalemate: a quiet waiting bishop move along its
   diagonal hands the move back and forces the king deeper (Capablanca's move 10
   below).

## Watch out for

- **Stalemate is the main danger** (the bishops cover many squares). Before any
  quiet move that leaves the king few squares, confirm `gives checkmate` (never
  `stalemate`) in `chess__imagine_move`.
- **Same-coloured bishops** cannot mate — check they sit on different colours.
- **Don't chase with the bishops alone** — without the king the net won't close.

## Examples

Mate pattern (verified): `k7/2B5/1KB5/8/8/8/8/8 b - - 0 1` — bishops c6/c7 seal
b7/b8/d7/d8, Kb6 covers a7, Ka8 mated.

Capablanca's mate-in-14 from `7k/8/8/8/8/8/8/2B1KB2 w - - 0 1`: 1.Bd3 Kg7 2.Bg5
Kf7 3.Bf5 Kg7 4.Kf2 Kf7 5.Kg3 Kg7 6.Kh4 Kf7 7.Kh5 Kg7 8.Bg6 Kg8 9.Kh6 Kf8
10.Bh5 (mark time) Kg8 11.Be7 Kh8 12.Bg4 Kg8 13.Be6+ Kh8 14.Bf6#. Verified.
