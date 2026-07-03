# Pin (chess) — Wikipedia (text + inline FEN/ASCII diagrams)

Source: https://en.wikipedia.org/wiki/Pin_(chess)
License: text CC BY-SA 4.0 (Wikipedia); position diagrams reconstructed losslessly from the article's {{Chess diagram}} wikitext into FEN+ASCII (verified in python-chess); composed images from Wikimedia Commons (CC/PD). Retrieved 2026-06-24.
Diagrams: 4 positions inlined as FEN+grid; 0 images downloaded.

---

In chess, a **pin** is a tactic in which a defending piece cannot move out of an attacking piece's line of attack without exposing a more valuable defending piece. Moving the attacking piece to effect the pin is called *pinning*; the defending piece restricted by the pin is described as *pinned*. Only a piece that can move any number of squares along a horizontal, vertical, or diagonal line (i.e. a bishop, rook, or queen) can pin. Any piece can be pinned except the king. The pin is one of the most powerful chess tactics.  

The inverse of a pin is a *skewer*, in which a more valuable piece under direct attack may move to expose a less valuable piece to an attack.

## Types

**Diagram 1** — FEN `2rk4/8/5n2/6B1/2N5/8/8/2Q1K3 w - - 0 1`

```
8  . . r k . . . .
7  . . . . . . . .
6  . . . . . n . .
5  . . . . . . B .
4  . . N . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . Q . K . . .
   a b c d e f g h
```

## Absolute pin
An *absolute pin* is one where the piece shielded by the pinned piece is the king. In this case it is illegal to move the pinned piece out of the line of attack, as that would place one's king in check (see diagram). A piece pinned in this way can still give check or defend another piece from capture by the opposing king.

## Relative pin
A *relative pin* is one where the piece shielded by the pinned piece is a piece other than the king, but typically is more valuable than the pinned piece. Moving such a pinned piece is legal but may not be prudent, as the shielded piece would then be vulnerable to capture if the pinned piece moving does not put the opponent’s king in check.

## Partial pin

**Diagram 2** — FEN `5k2/2p5/8/8/3b1q2/4P3/2B5/5RK1 w - - 0 1`
*{{Chess diagram*

```
8  . . . . . k . .
7  . . p . . . . .
6  . . . . . . . .
5  . . . . . . . .
4  . . . b . q . .
3  . . . . P . . .
2  . . B . . . . .
1  . . . . . R K .
   a b c d e f g h
```

Sometimes a piece may be considered to be in a *situational pin*. Like a relative pin, a situational pin does not legally restrict the piece from moving, but moving the pinned piece out of the line of attack can result in some detriment to the player (e.g. checkmate, immediate loss of the game, occupation of a critical square by the opponent, etc.).

Consider the diagrammed position with White to move. The black bishop on d5 is unprotected and White can capture it with 1.Nxd5; however, White should not play the capture or otherwise move the knight, due to the skewer attack 1...Rb1+ winning White's rook (the king is forced to move, then 2...Rxh1). It can be said that the white knight is "pinned to the b1-square" rather than pinned to a piece.

## Cross-pin
A *cross-pin* consists of two or more pins, of any type, on the same piece. As there is only one king per side, only one of the pins can be absolute, but there are otherwise no restrictions on the types of pins involved.

## Pin combinations
Pinning can also be used in combination with other tactics.  For example, a piece can be pinned to prevent it from moving to attack, or a defending piece can be pinned as part of tactic undermining an opponent's defense. Another tactic which takes advantage of a pin can be called *working the pin*.  In this tactic, other pieces from the pinning piece's side attack the opposing pinned piece.  Since the pinned piece cannot move out of the line of attack, the player whose piece is pinned may move other pieces to defend the pinned piece, but the pinning player may yet attack with even more pieces, etc. Using a battery of doubled rooks with a queen behind them to this end is known as Alekhine's gun.

A pinned piece can usually no longer be counted on as a defender of another friendly piece or as an attacker of an opposing piece (unless the subject piece is in the pinning line). A pinned piece can still give check to the opposing king, however, and therefore can still defend friendly pieces against captures made by the enemy king.

## Unpinning
Breaking a pin is called *unpinning*. This can be done in a number of ways: the piece creating the pin can be captured or chased away; another unit can be moved to block the line of the pin; the unit to which a piece is pinned can be moved; or, a relatively pinned piece can move despite the pin, such as in the Légal Trap and the Elephant Trap.

## Pins commonly seen in gameplay

**Diagram 3** — FEN `1rn1qkbn/1ppp1pp1/4p2p/8/4PP1b/6N1/1PPP2PP/1RNBQKB1 w - - 0 1`

```
8  . r n . q k b n
7  . p p p . p p .
6  . . . . p . . p
5  . . . . . . . .
4  . . . . P P . b
3  . . . . . . N .
2  . P P P . . P P
1  . R N B Q K B .
   a b c d e f g h
```

A pinning move that often occurs in openings is Bb5 which, if Black has moved ...Nc6 and ...d6 or ...d5, pins the knight on c6, since moving the knight would expose the king on e8 to check. The same may occur on the other , with a bishop on g5; or by Black on White, with a bishop on b4 or g4.

## Examples from games

**Diagram 4** — FEN `7k/1pp1n2p/4bN2/4P1p1/2PP4/5rBq/1P2Q2P/1R4RK w - - 0 1`

```
8  . . . . . . . k
7  . p p . n . . p
6  . . . . b N . .
5  . . . . P . p .
4  . . P P . . . .
3  . . . . . r B q
2  . P . . Q . . P
1  . R . . . . R K
   a b c d e f g h
```

The diagram shows Vladimir Lenin–Maxim Gorky, Capri 1908, with White to move. Black is threatening the following rook sacrifice and : 27...Rh1+ 28.Kxh1 Qh2. White cannot play 27.gxh3, because the queen on g3 is pinning the pawn to the g-file. The only move that postpones the mate is 27.Nf4, which temporarily blocks Black's bishop from protecting his queen, but to no avail as Black can simply play 27...Bxf4 renewing the mate threat. Or, Black can respond by mating a different way: 27.Nf4 Qh2+ 28.Kf2 Rhxf3#. In this case, White cannot capture 29.gxf3 because the queen now on h2 pins the pawn to the 2nd rank. With mate being inevitable, White resigned after move 26.

## See also
*Chess tactics

## References
## Sources
* 
*
*

Category:Chess tactics
Category:Chess terminology