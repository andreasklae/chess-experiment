---
category: mates
description: Mate on the 8th rank when the enemy king is trapped behind its own unmoved pawns.
triggers: [back rank, back-rank mate, king trapped behind pawns, undefended back rank]
related_pages: [tactics/deflection, principles/luft]
tags: [mate, tactic, rook, queen, endgame, middlegame]
status: draft
updated: 2026-06-16
---

# Back-Rank Mate

## When to use

The enemy king is on its back rank (rank 8 for Black), its escape squares
on rank 7 are blocked by its own pawns (typically f7-g7-h7 still home after
castling), and you have a rook or queen that can reach the back rank with
check. Watch the **Enemy king mobility** line in `imagine_move`: if a
back-rank check drops it to 0, that's mate.

## The idea

A castled king is safe from the front but can be trapped by its own pawn
shield. A major piece delivering check along the undefended back rank is
checkmate because the king has no flight square — the pawns it hid behind
now wall it in.

## What to do

- Look for a rook or queen with a clear (or clearable) path to the enemy
  back rank.
- If a defender guards the mating square, look to **deflect or overload**
  it first (see [[tactics/deflection]]) — a common pattern is sacrificing
  to remove the one piece covering the back rank.
- Confirm with `imagine_move`: the move should report `gives checkmate`.
  If it only gives check, the king has luft (an escape square) — recount.

## Watch out for

- **Luft:** if the enemy has played ...h6 or ...g6, the back-rank idea
  usually fails — the king steps out. Check the king's escape squares
  before committing material to it.
- **Your own back rank:** the same weakness is yours. Before chasing the
  mate, make sure you aren't walking into a back-rank tactic yourself.
  Consider making luft (see [[principles/luft]]) when your back rank is
  loose.
- A defended back rank: a rook or queen already covering rank 8 means you
  need to remove or outnumber it first.

## Examples

`6k1/5ppp/8/8/8/8/8/R6K w - - 0 1` — White plays Ra8#: the rook checks
along the 8th rank and the f7-g7-h7 pawns deny the king any escape.

**Deflection mate (Lichess #JxR8M).** When a defender guards the mating
square, sacrifice to drag it off. `7k/pp1r1ppp/4p3/2P1Q3/3r4/P6P/1q3PP1/3R1RK1 w - - 2 25`:

```
. . . . . . . k     Black: Kh8, Rd7, Rd4, Qb2, pawns a7 b7 e6 f7 g7 h7
p p . r . p p p     White: Kg1, Qe5, Rd1, Rf1, pawns a3 c5 f2 g2 h3
. . . . p . . .
. . P . Q . . .     The d8 mating square is guarded by ...Rd7. Deflect it
. . . r . . . .     twice, sacrificing the queen, then mate:
P . . . . . . P
. q . . . P P .     1.Qb8+  Rd8   (forced — only legal move)
. . . R . R K .     2.Qxd8+ Rxd8  (forced)
                    3.Rxd8#       (back-rank mate; h7-g7-f7 wall the king)
```

Each black reply is the ONLY legal move — a fully forced sequence.
`imagine_move` confirms `gives checkmate` on the final Rxd8. Verified.
