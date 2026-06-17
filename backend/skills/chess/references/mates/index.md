# Mates — Index

Every checkmating page: the basic technical drills (your material vs a
**lone** king) and the named attacking nets (against a king that still has
its army). Watch the **Enemy king mobility** line in `chess__imagine_move`
and the **King mvt** column in `chess__list_legal_moves` — a move that
drives that toward zero is the thread that leads here.

**The one question that picks your page: is the enemy down to a bare king
(plus maybe pawns)?**

- **Yes → a BASIC TECHNICAL MATE.** A forced drill you execute; pick by your
  material from the first table.
- **No (the king still has defenders, you spotted a mating motif) → a NAMED
  ATTACKING MATE.** Pick by the motif's geometry from the second table.

**Choose the simplest mate available.** With two major pieces the ladder is
fully forced — look no further. Often the fastest "mate" is to promote a
pawn first and then mate with the queen (see
[`../strategy/convert-advantage.md`](../strategy/convert-advantage.md)).

## Basic technical mates (vs a lone king) — pick by your material

| Read this when you have… | Page | The technique |
|---|---|---|
| **two rooks** (K+2R) | [two-rook-ladder-mate](two-rook-ladder-mate.md) | fence one rank, check with the OTHER rook, leapfrog the king to the edge |
| **king + queen** (K+Q) | [king-queen-mate](king-queen-mate.md) | knight's-move shadow the king to the edge, bring your king, mate |
| **king + rook** (K+R) | [king-rook-mate](king-rook-mate.md) | fence behind the king, take opposition with your king, then check on the edge |

*(Queen+rook and two-queen ladders run on the two-rook rhythm but have
their own traps — pages added when seeded.)*

## Named attacking mates (king still has defenders) — pick by geometry

| Read this when… | Page |
|---|---|
| enemy king on its back rank, escape squares blocked by its own pawns, you have a rook/queen to check along the rank | [back-rank-mate](back-rank-mate.md) |
| enemy king cornered behind its own pieces; you have a knight (Q+N forced sequence) | [smothered-mate](smothered-mate.md) |
| enemy king on the edge file; knight reaches the e7-type square; rook free for the edge file | [anastasia-mate](anastasia-mate.md) |
| enemy king cornered; you have rook + knight | [arabian-mate](arabian-mate.md) |
| enemy king on the edge; rook + knight + pawn on that wing | [hook-mate](hook-mate.md) |
| castled king, open/openable h-file, bishop on the a2–g8 diagonal, queen available | [greco-mate](greco-mate.md) |
| enemy king with 2+ escape squares blocked by its own pieces; queen lands adjacent (epaulette / dovetail / swallow's tail) | [queen-contact-mates](queen-contact-mates.md) |
| uncastled enemy king on an openable central file; rook + bishop coordinate | [opera-mate](opera-mate.md) |
| both your rooks reach the enemy 7th rank against a castled king | [blind-swine-mate](blind-swine-mate.md) |

## Always confirm

Confirm the mate with `chess__imagine_move` (it flags `gives checkmate`) or
by scanning `chess__list_legal_moves` for the `checkmate` flag before
committing. A quiet move that leaves the king zero squares but is **not**
a check is **stalemate** — see [`../principles/avoid-stalemate.md`](../principles/avoid-stalemate.md).
