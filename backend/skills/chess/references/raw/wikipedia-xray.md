# X-ray (chess) — Wikipedia (text + inline FEN/ASCII diagrams)

Source: https://en.wikipedia.org/wiki/X-ray_(chess)
License: text CC BY-SA 4.0 (Wikipedia); position diagrams reconstructed losslessly from the article's {{Chess diagram}} wikitext into FEN+ASCII (verified in python-chess); composed images from Wikimedia Commons (CC/PD). Retrieved 2026-06-24.
Diagrams: 10 positions inlined as FEN+grid; 0 images downloaded.

---

In chess, an **X-ray** or **X-ray attack** is a tactic where a  indirectly controls a square from the other side of an intervening piece. Generally, a piece performing an X-ray either:
* effects a skewer,
* indirectly attacks an enemy piece through another piece or pieces, or
* defends a friendly piece through an enemy piece.

## Examples

**Diagram 1** — FEN `1r1bqr1k/1ppp2pb/4p1np/4Pp2/3PnP2/1P1N1BN1/2P2BPP/1R2Q1RK w - - 0 1`

```
8  . r . b q r . k
7  . p p p . . p b
6  . . . . p . n p
5  . . . . P p . .
4  . . . P n P . .
3  . P . N . B N .
2  . . P . . B P P
1  . R . . Q . R K
   a b c d e f g h
```

**Diagram 2** — FEN `2rbq1r1/6p1/3np2p/1p2N3/1R1B1PP1/2PP1N2/8/4Q1K1 w - - 0 1`  (reconstructed; may be a partial/illustrative position)

```
8  . . r b q . r .
7  . . . . . . p .
6  . . . n p . . p
5  . p . . N . . .
4  . R . B . P P .
3  . . P P . N . .
2  . . . . . . . .
1  . . . . Q . K .
   a b c d e f g h
```

The second usage is seen in the first diagram position, which arises from the Black Knights' Tango opening after 1.d4 Nf6 2.c4 Nc6 3.Nf3 e6 4.a3 d6 5.Nc3 g6 6.e4 Bg7 7.Be2 0-0 8.0-0 Re8 9.Be3 e5 10.d5 Nd4 Authors Richard Palliser and Georgi Orlov, in their respective books on that opening, both note that Black's rook on e8 "X-rays" White's e-pawn through Black's own pawn on e5. If 11.Nxd4 exd4 12.Bxd4 Nxe4 13.Nxe4 Rxe4. The identical position is reached, except that White has not played a2–a3, in the King's Indian Defense after 1.d4 Nf6 2.c4 g6 3.Nc3 Bg7 4.e4 d6 5.Nf3 0-0 6. Be2 e5 7.0-0 Nc6 8.Be3 Re8 9.d5 Nd4!

Of the second diagram position, arising from the Sveshnikov Variation of the Sicilian Defense, Atanas Kolev and Trajko Nedev observe, "On f1 the king is X-rayed by the f8-rook". They analyze the possible continuation 22...f5 23.exf5 Bxf5 24.Nxf5 Rxf5 25.Qg4 Bg5 (exploiting the pin along the f-file) 26.Kg2 Bxf4 27.Nxf4 Rg5 28.Nxg6+ Kg7 and White resigned in Delchev–Kotanjian, Kusadasi 2006.

**Diagram 3** — FEN `1r1n1r1k/2p1n1pp/1p1pb3/1P2p1P1/2P1PP2/3NB3/3QB2P/2R2R1K w - - 0 1`

```
8  . r . n . r . k
7  . . p . n . p p
6  . p . p b . . .
5  . P . . p . P .
4  . . P . P P . .
3  . . . N B . . .
2  . . . Q B . . P
1  . . R . . R . K
   a b c d e f g h
```

**Diagram 4** — FEN `1r2r2k/1ppq1ppb/4p1np/8/3b1PP1/3N1BB1/1PPPQ2P/1R3R1K w - - 0 1`

```
8  . r . . r . . k
7  . p p q . p p b
6  . . . . p . n p
5  . . . . . . . .
4  . . . b . P P .
3  . . . N . B B .
2  . P P P Q . . P
1  . R . . . R . K
   a b c d e f g h
```

The first diagram position arose after 23...Qd8–h4! in Krasenkow&ndash;Seirawan, 34th Chess Olympiad, Istanbul 2000. Michael Rohde writes of Seirawan's 23rd move, "Holding things up through an x-ray on the pawn on d4." Black would respond to either 24.e5 or 24.exd5 with 24...Qxd4+.

Gerald Abrahams alludes to the X-ray concept, without using that term, when he cites the aphorism, "Put your rook on the line of his queen, no matter how many other pieces intervene." He writes, "That doggerel jingle incorporates some experience". A future world champion played in that manner in Rauzer&ndash;Botvinnik, USSR Championship 1933. Two moves before the second diagram position arose, Botvinnik had played 13...Rfd8, X-raying the white queen through the pawn on d6. Now Bernard Cafferty and Mark Taimanov suggest "15.Qf2 to get away from the 'X-ray' attack from the d8 rook". Instead, the game continued 15.Rac1 e5! 16.b3 d5, exploiting the queen's position on the same file as the rook and leading to a win for Botvinnik 13 moves later.

**Diagram 5** — FEN `1r1bqk2/1pppp1pp/3P4/8/2b5/2Q3pP/1PP1PPP1/1R1B1KB1 w - - 0 1`

```
8  . r . b q k . .
7  . p p p p . p p
6  . . . P . . . .
5  . . . . . . . .
4  . . b . . . . .
3  . . Q . . . p P
2  . P P . P P P .
1  . R . B . K B .
   a b c d e f g h
```

**Diagram 6** — FEN `8/1Q4nk/7p/5qp1/6R1/2r4P/7B/8 w - - 0 1`  (reconstructed; may be a partial/illustrative position)

```
8  . . . . . . . .
7  . Q . . . . n k
6  . . . . . . . p
5  . . . . . q p .
4  . . . . . . R .
3  . . r . . . . P
2  . . . . . . . B
1  . . . . . . . .
   a b c d e f g h
```

The first diagram position arose from the English Opening in the famous  Petrosian&ndash;Ree, Wijk aan Zee 1971 after 1.c4 e5 2.Nc3 Nf6 3.Nf3 Nc6 4.g3 Bb4 5.Nd5 Nxd5 6.cxd5 e4 7.dxc6 exf3 8.Qb3! Author Iakov Neishtadt cites the game as an example of an "X-ray". Black resigned because the white queen's X-ray of his pawn on b7, through Black's bishop on b4, wins a piece after, e.g., 8...a5 (or 8...Qe7) 9.a3 Bc5 10.cxb7.

The above examples all involve a latent attack along a  or . A latent attack along a diagonal has also been called an X-ray. The second diagram position arose in Dorfman&ndash;Tseshkovsky, 46th USSR Championship Tbilisi 1978. Cafferty and Taimanov write, "Black can use the 'X-ray' attack of his queen on the enemy king to break up the white bastions". Black exploited the X-ray along the b8–h2 diagonal and won quickly after 48...g5! 49.hxg5 h4! with a decisive attack. The game concluded 50.g6 Kxg6 51.Qa6+ Kg5 52.gxh4+ Kxf4 53.Qc4+ Ke3+ 54.Kh3 Kf2+ 55.Qxb3 Nxg5+! and White resigned in light of 56.hxg5 Qh8#.

**Diagram 7** — FEN `1q2r2k/6pp/8/1p2r3/8/8/4R1PP/4R2K w - - 0 1`

```
8  . q . . r . . k
7  . . . . . . p p
6  . . . . . . . .
5  . p . . r . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . R . P P
1  . . . . R . . K
   a b c d e f g h
```

**Diagram 8** — FEN `7k/2p3pp/5pn1/3Nb3/7P/3P1PBK/6P1/8 w - - 0 1`

```
8  . . . . . . . k
7  . . p . . . p p
6  . . . . . p n .
5  . . . N b . . .
4  . . . . . . . P
3  . . . P . P B K
2  . . . . . . P .
1  . . . . . . . .
   a b c d e f g h
```

The third usage is given by the American master and writer Bruce Pandolfini, who states that one usage of "X-Ray" is "a skewer defense along a rank, file, or diagonal" that "protects a friendly man through an enemy man in the middle along the same line of power". Jeremy Silman uses the term in the same way, illustrating "X-ray" with the two diagrams. In the first diagram position, White wins with the X-ray 1.Qxd8+! followed by 1...Rxd8 2.Rxd8+ (note how White's rook defended his queen through the black rook on d5) Qxd8 3.Rxd8# or 1...Qxd8 2.Rxd5 Qf8 3.Rd8 and wins. In the second diagram position, White wins a pawn with 1.Nxb7!, when White's bishop on f3 defends the white knight on b7 through Black's bishop on d5. Silman states that the X-ray "takes advantage of pieces that appear to be adequately defended but really aren't".

**Diagram 9** — FEN `1r6/2kn1Q2/2pp1p2/5P1p/3PP2q/3N2p1/4B1PP/6RK w - - 0 1`

```
8  . r . . . . . .
7  . . k n . Q . .
6  . . p p . p . .
5  . . . . . P . p
4  . . . P P . . q
3  . . . N . . p .
2  . . . . B . P P
1  . . . . . . R K
   a b c d e f g h
```

**Diagram 10** — FEN `1rn1qr1k/2p2np1/3p3p/8/2pPb3/8/1PB1P1PP/3KR1B1 w - - 0 1`

```
8  . r n . q r . k
7  . . p . . n p .
6  . . . p . . . p
5  . . . . . . . .
4  . . p P b . . .
3  . . . . . . . .
2  . P B . P . P P
1  . . . K R . B .
   a b c d e f g h
```

Raymond Keene also uses the term in this way in analyzing Fischer&ndash;Bisguier, New York 1957. Discussing a possible variation that could have arisen in that game (see first diagram position), Keene writes that 28.Qxg5 (when the white queen defends against 28...Qxg2# through Black's queen on g4) "defends the mate&mdash;an 'X-ray motif', as Fischer once described it".

In Euwe–Loman, Rotterdam 1923 (second diagram position), White forced mate with 17.Qh8+! Bxh8 18.Rxh8#. Neishtadt writes of 17.Qh8+, "The X-ray! The bishop at b2 attacks the square h8 'through' the enemy bishop."

## See also
*Chess tactics

## References
Category:Chess tactics
Category:Chess terminology