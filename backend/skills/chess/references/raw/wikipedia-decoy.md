# Decoy (chess) — Wikipedia (text + inline FEN/ASCII diagrams)

Source: https://en.wikipedia.org/wiki/Decoy_(chess)
License: text CC BY-SA 4.0 (Wikipedia); position diagrams reconstructed losslessly from the article's {{Chess diagram}} wikitext into FEN+ASCII (verified in python-chess); composed images from Wikimedia Commons (CC/PD). Retrieved 2026-06-24.
Diagrams: 7 positions inlined as FEN+grid; 0 images downloaded.

---

In chess, a **decoy** is a tactic that lures an enemy  off its square and away from its defensive role. Typically this means away from a square on which it defends another piece or threat. The tactic is also called a *deflection*. Usually the piece is decoyed to a particular square via the sacrifice of a piece on that square. A piece so sacrificed is called a *decoy*. When the piece decoyed or deflected is the king, the tactic is known as **attraction**.  In general in the middlegame, the sacrifice of a decoy piece is called a *diversionary sacrifice*. 

## Examples

**Diagram 1** — FEN `3r1r1k/2p4b/1p2p1qp/2n1P3/3P1B2/2N1Q3/1PP2R2/2K5 w - - 0 1`

```
8  . . . r . r . k
7  . . p . . . . b
6  . p . . p . q p
5  . . n . P . . .
4  . . . P . B . .
3  . . N . Q . . .
2  . P P . . R . .
1  . . K . . . . .
   a b c d e f g h
```

The game Honfi–Barczay, Kecskemet 1977, with Black to play, illustrates two separate decoys. First, the white queen is set up on c4 for a knight fork: 
:**1... Rxc4! 2. Qxc4**
Next, the fork is executed by removing the sole defender of the a3-square: 
:**2... Qxb2+ 3. Rxb2 Na3+ 4. Kc1**
Finally, a zwischenzug decoys (attracts) the king to b2: 
:**4... Bxb2+**
After either 5.Kxb2 Nxc4+ 6.Kc3 Rxe4, or 5.Kd1 Nxc4, Black is two pawns ahead and should win comfortably.

**Diagram 2** — FEN `7k/7p/2q5/1p1N4/4P3/8/7P/6RK w - - 0 1`

```
8  . . . . . . . k
7  . . . . . . . p
6  . . q . . . . .
5  . p . N . . . .
4  . . . . P . . .
3  . . . . . . . .
2  . . . . . . . P
1  . . . . . . R K
   a b c d e f g h
```

In this position, after the moves 1.Rf8+ Kxf8 () 2.Nd7+ Ke7 3.Nxb6, White wins the queen and the game. A similar, but more complex position is described by Huczek.

**Diagram 3** — FEN `7k/6pb/2p1N3/1p5p/6q1/1Q6/1Pr5/4RR2 w - - 0 1`  (reconstructed; may be a partial/illustrative position)

```
8  . . . . . . . k
7  . . . . . . p b
6  . . p . N . . .
5  . p . . . . . p
4  . . . . . . q .
3  . Q . . . . . .
2  . P r . . . . .
1  . . . . R R . .
   a b c d e f g h
```

In the diagrammed position from Vidmar–Euwe, Carlsbad 1929, Black had just played 33...Qf4, threatening mate on h2. White now uncorks the elegant combination 34.Re8+ Bf8 (forced) 35.Rxf8+ (attraction) Kxf8 (forced) 36.Nf5+ (discovered check) Kg8 (36...Ke8 37.Qe7) 37.Qf8+ (attraction)  Black resigns. (If 37...Kxf8 then 38.Rd8#. If 37...Kh7 then 38.Qg7#.) The combination after 33...Qf4 features two separate examples of the attraction motif.

**Diagram 4** — FEN `7k/7p/3q1p1P/5Pn1/8/6RB/8/3r4 w - - 0 1`  (reconstructed; may be a partial/illustrative position)

```
8  . . . . . . . k
7  . . . . . . . p
6  . . . q . p . P
5  . . . . . P n .
4  . . . . . . . .
3  . . . . . . R B
2  . . . . . . . .
1  . . . r . . . .
   a b c d e f g h
```

This example shows a position from the game Dementiev–Dzindzichashvili, URS 1972. White had just played 61.g6 (with the threat 62.Qh7+ Kf8 63.Qh8+ (63.Rxf5+ =) Ke7 64.Bh4+ and mate in one). However, Black continued with the crushing 61...Rh1+ (attraction) 62. Kxh1 (best) Nxg3+ (the white rook is pinned) 63.Kh2 Nxh5 and White has dropped his queen to the knight fork. In the game, White resigned after 61...Rh1+.

**Diagram 5** — FEN `1r1br3/2p2npk/4Bpbp/1pqp4/3N1R2/2P1P1QP/2PP2PB/1R5K w - - 0 1`

```
8  . r . b r . . .
7  . . p . . n p k
6  . . . . B p b p
5  . p q p . . . .
4  . . . N . R . .
3  . . P . P . Q P
2  . . P P . . P B
1  . R . . . . . K
   a b c d e f g h
```

Perhaps the most celebrated game featuring a decoy theme is Petrosian–Pachman, Bled 1961, which also involved a queen sacrifice. Pachman resigned after 19.Qxf6+ (attraction) Kxf6 20.Be5+ Kg5 21.Bg7 setting a .

**Diagram 6** — FEN `1r4rk/1pbq1bp1/2p2p1p/7N/3P3n/3B4/1PPB2PP/4R1RK w - - 0 1`

```
8  . r . . . . r k
7  . p b q . b p .
6  . . p . . p . p
5  . . . . . . . N
4  . . . P . . . n
3  . . . B . . . .
2  . P P B . . P P
1  . . . . R . R K
   a b c d e f g h
```

In the game Menchik–Graf, Semmering 1937, Graf resigned after 21.Rd7, deflecting Black's queen. (If 21...Qxd7, then 22.Qxh5 with mate to follow; 21.Qxh5 immediately wins only a pawn after 21...Qxh2+.)

**Diagram 7** — FEN `8/8/6p1/4k1Nn/5p1P/8/1P3K2/8 w - - 0 1`

```
8  . . . . . . . .
7  . . . . . . . .
6  . . . . . . p .
5  . . . . k . N n
4  . . . . . p . P
3  . . . . . . . .
2  . P . . . K . .
1  . . . . . . . .
   a b c d e f g h
```

Often a  pawn serves as a decoy in endgames. In the game Ivkov–Taimanov, Belgrade 1956, Black resigned in the position shown because White has an easy win by using his passed a2-pawn as a decoy to  Black's king away from the  and to the , allowing easy promotion of the h6-pawn.

## See also
*Overloading

## References
**Bibliography**
* 

Category:Chess tactics
Category:Chess theory