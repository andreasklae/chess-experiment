# Checkmate Patterns — Wikipedia

Source: https://en.wikipedia.org/wiki/Checkmate_pattern

In chess literature, certain recognizable arrangements of pieces that deliver checkmate have been given specific names. The boards below show these checkmates with White checkmating Black. Boards use the same format as `chess__show_position`: uppercase = White, lowercase = Black; ranks 8–1 top to bottom, files a–h left to right.

FENs are of the final mated position (Black to move, in checkmate). All verified with python-chess.

---

## Anastasia's mate

FEN: `8/4N1pk/8/7R/8/8/8/8 b - - 0 1`

```
8  . . . . . . . .
7  . . . . N . p k
6  . . . . . . . .
5  . . . . . . . R
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

A knight and rook team up to trap the opposing king between the side of the board and a friendly piece. The knight on e7 covers g8 and g6; the black pawn on g7 and h7 block the king's escape; the rook on h5 delivers check along the h-file. Often a queen or rook is first sacrificed on the a- or h-file to achieve the position.

---

## Anderssen's mate

FEN: `6kR/6P1/5K2/8/8/8/8/8 b - - 0 1`

```
8  . . . . . . k R
7  . . . . . . P .
6  . . . . . K . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

The rook on h8 checks the king on g8, supported by the pawn on g7 (which covers f8 and h8) and the white king on f6 (which cuts off f7 and g7). Sometimes a distinction is drawn between Anderssen's mate (rook supported by a pawn) and Mayet's mate (rook supported by a distant bishop).

---

## Arabian mate

FEN: `7k/7R/5N2/8/8/8/8/8 b - - 0 1`

```
8  . . . . . . . k
7  . . . . . . . R
6  . . . . . N . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

The knight on f6 and the rook on h7 team up to trap the king in the corner on h8. The rook sits adjacent to the king on h7, preventing escape along the rank and delivering check via the h-file, while the knight covers g8 and prevents the king from stepping there.

---

## Back-rank mate

FEN: `3R2k1/5ppp/8/8/8/8/8/8 b - - 0 1`

```
8  . . . R . . k .
7  . . . . . p p p
6  . . . . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

The rook on d8 checkmates the king on g8, which is blocked by its own pawns on f7, g7, and h7. Also known as the corridor mate. The pattern arises when a castled king never created luft (a pawn escape square). See also [[patterns/mating-patterns/back-rank-mate]].

---

## Balestra mate

FEN: `6k1/8/4B2Q/8/8/8/8/8 b - - 0 1`

```
8  . . . . . . k .
7  . . . . . . . .
6  . . . . B . . Q
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

The queen on h6 cuts off the king's escape both along the rank and the diagonal, while the bishop on e6 covers f7 and d7. The queen checks on h6 (covering g7 via diagonal and h7 via file); the bishop covers f7 and the diagonal approach to g8.

---

## Blackburne's mate

FEN: `5rk1/7B/8/6N1/8/8/1B6/8 b - - 0 1`

```
8  . . . . . r k .
7  . . . . . . . B
6  . . . . . . . .
5  . . . . . . N .
4  . . . . . . . .
3  . . . . . . . .
2  . B . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

Named for Joseph Henry Blackburne. The two bishops (b2 and h7) and the knight on g5 cooperate, using the enemy rook on f8 and the edge of the board to confine the king. The bishop on h7 blocks h8; the knight on g5 covers h7 and f7; the bishop on b2 covers the long diagonal. The black rook on f8 blocks f8 itself.

---

## Blind swine mate

FEN: `5rk1/6RR/8/8/8/8/8/8 b - - 0 1`

```
8  . . . . . r k .
7  . . . . . . R R
6  . . . . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

Two white rooks on the 7th rank (named "swine" by Dawid Janowski) deliver checkmate. Both rooks on g7 and h7 control the 7th rank; the black rook on f8 blocks f8; the king on g8 has no escape. A typical sequence reaching this position: 1.Rxg7+ Kh8 2.Rxh7+ Kg8 3.Rbg7#.

---

## Boden's mate

FEN: `2kr4/3p4/B7/8/5B2/8/8/8 b - - 0 1`

```
8  . . k r . . . .
7  . . . p . . . .
6  B . . . . . . .
5  . . . . . . . .
4  . . . . . B . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

Two attacking bishops on criss-crossing diagonals deliver checkmate to a king obstructed by its own pieces (here a rook on d8 and a pawn on d7). The bishop on a6 checks the king via b7–c8; the bishop on f4 controls the other diagonal. The king on c8 cannot escape to b7 (Ba6), d7 (own pawn), d8 (own rook), or b8 (blocked).

---

## Corner mate

FEN: `7k/5N1p/8/8/8/8/8/6R1 b - - 0 1`

```
8  . . . . . . . k
7  . . . . . N . p
6  . . . . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . R .
   a b c d e f g h
```

The rook on g1 delivers check along the g-file (g8 square); the knight on f7 covers h8 and g5; the black pawn on h7 blocks h7 for the king. The king on h8 is trapped in the corner.

---

## Damiano's bishop mate

FEN: `5k2/5Q2/6B1/8/8/8/8/8 b - - 0 1`

```
8  . . . . . k . .
7  . . . . . Q . .
6  . . . . . . B .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

The queen on f7 checkmates the king on f8, supported by the bishop on g6 (which protects the queen and covers h7). The king cannot go to e8 (queen covers e8 via rank), g8 (queen covers g8 via diagonal), g7 (queen covers g7 via rank), or e7 (queen covers e7 via file). Named after Pedro Damiano. A typical 4-move sequence: 1.Bxh7+ Kh8 2.Bg6+ Kg8 3.Qh7+ Kf8 4.Qxf7#.

---

## Damiano's mate

FEN: `5rk1/6pQ/6P1/8/8/8/8/8 b - - 0 1`

```
8  . . . . . r k .
7  . . . . . . p Q
6  . . . . . . P .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

The queen on h7 checks the king on g8; the black rook on f8 blocks f8; the pawn on g7 (black) blocks g7; the white pawn on g6 covers h7 (so the king cannot capture the queen). First published by Pedro Damiano in 1512. Often arrived at by first sacrificing a rook on the h-file.

---

## Double bishop mate

FEN: `7k/7p/8/3B4/8/2B5/8/8 b - - 0 1`

```
8  . . . . . . . k
7  . . . . . . . p
6  . . . . . . . .
5  . . . B . . . .
4  . . . . . . . .
3  . . B . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

Two bishops on parallel (adjacent) diagonals deliver checkmate. The bishop on d5 attacks h1–e8 diagonally and covers g8; the bishop on c3 covers the parallel diagonal and h8. The black pawn on h7 blocks h7. Similar to Boden's mate but the bishops are on parallel diagonals rather than crossing ones.

---

## Dovetail mate (Cozio's mate)

FEN: `8/8/8/8/6p1/5qk1/7Q/6K1 b - - 0 1`

```
8  . . . . . . . .
7  . . . . . . . .
6  . . . . . . . .
5  . . . . . . . .
4  . . . . . . p .
3  . . . . . q k .
2  . . . . . . . Q
1  . . . . . . K .
   a b c d e f g h
```

The queen on h2 checkmates the king on g3, which is hemmed in by its own pieces: black queen on f3 (blocks f3), black pawn on g4 (blocks g4), and the board edge. The white queen covers h3 (via file), g2 (via rank), f2 (via rank), h1 (via diagonal), and g3 (via diagonal). Named after Carlo Cozio (1766). Note: the black pieces here are the mated side's own pieces creating the dovetail pattern.

---

## Epaulette mate

FEN: `5rkr/8/6Q1/8/8/8/8/6K1 b - - 0 1`

```
8  . . . . . r k r
7  . . . . . . . .
6  . . . . . . Q .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . K .
   a b c d e f g h
```

The queen on g6 checkmates the king on g8, which is flanked by its own rooks on f8 and h8 (the "epaulettes"). The queen covers g7 (via file), f7 (via diagonal), h7 (via diagonal), and the rooks block f8 and h8. Named for the visual resemblance to military epaulettes on the shoulder. Example: Carlsen–Ernst, Wijk aan Zee 2004 (29.Qd7#, a sideways variant).

---

## Greco's mate

FEN: `7k/6p1/8/7Q/2B5/8/8/8 b - - 0 1`

```
8  . . . . . . . k
7  . . . . . . p .
6  . . . . . . . .
5  . . . . . . . Q
4  . . B . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

The queen on h5 checks h8 (via the h-file); the bishop on c4 covers g8 (via the long diagonal c4–d5–e6–f7–g8); the black pawn on g7 blocks g7. The queen also covers g6 via diagonal. Named after Gioachino Greco.

---

## Hook mate

FEN: `4R3/4kp2/5N2/4P3/8/8/8/8 b - - 0 1`

```
8  . . . . R . . .
7  . . . . k p . .
6  . . . . . N . .
5  . . . . P . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

The rook on e8 checks the king on e7; the knight on f6 covers d7, d5, g8, g4, h5, h7; the white pawn on e5 covers d6 and f6; the black pawn on f7 blocks f7. The rook, knight, and pawn form a hook shape around the king.

---

## Ladder mate (lawnmower mate)

FEN: `R5k1/1R6/8/8/8/8/8/8 b - - 0 1`

```
8  R . . . . . k .
7  . R . . . . . .
6  . . . . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

Two major pieces (here two rooks) work together to push the king to the edge. The rook on a8 checks on the 8th rank; the rook on b7 covers the 7th rank and protects Ra8. The king on g8 cannot move to f8 (Ra8), g7 or h7 (Rb7 covers), or h8 (Ra8 covers). Can use two rooks, two queens, or a rook and queen.

---

## Légal's mate

FEN: `r2q1bnr/ppp1kBpp/2np4/3NN3/4P3/7P/PPPP1PP1/R1BbK2R b - - 0 1`

```
8  r . . q . b n r
7  p p p . k B p p
6  . . n p . . . .
5  . . . N N . . .
4  . . . . P . . .
3  . . . . . . . P
2  P P P P . P P .
1  R . B b K . . R
   a b c d e f g h
```

Two knights (d5, e5) and a bishop (f7) coordinate to checkmate the king on e7. The bishop on f7 delivers check; both knights cover all escape squares. The black bishop on d1 and other black pieces seal off the queenside. From the game Légal vs. Saint Brie (c. 1750): 1.e4 e5 2.Nf3 d6 3.Bc4 Bg4 4.Nc3 g6 5.Nxe5 Bxd1 6.Bxf7+ Ke7 7.Nd5#.

---

## Lolli's mate

FEN: `6k1/5pQ1/5Pp1/8/8/8/8/8 b - - 0 1`

```
8  . . . . . . k .
7  . . . . . p Q .
6  . . . . . P p .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

The queen on g7 checkmates the king on g8; the white pawn on f6 covers g7 (protects the queen) and e7; the black pawn on g6 blocks g6; the black pawn on f7 blocks f7. Involves infiltrating Black's fianchetto position using pawn and queen. Named after Giambattista Lolli.

---

## Morphy's mate

FEN: `7k/7p/5B2/8/8/8/8/6R1 b - - 0 1`

```
8  . . . . . . . k
7  . . . . . . . p
6  . . . . . B . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . R .
   a b c d e f g h
```

The rook on g1 checks the king on h8 via the g-file (covering g8); the bishop on f6 covers g7 and g5; the black pawn on h7 blocks h7 (and the bishop controls it). Named after Paul Morphy. Very similar to Corner mate; the key difference is using the bishop to confine via a diagonal rather than a knight.

---

## Opera mate

FEN: `1n1Rkb1r/p4ppp/4q3/4p1B1/4P3/8/PPP2PPP/2K5 b - - 0 1`

```
8  . n . R k b . r
7  p . . . . p p p
6  . . . . q . . .
5  . . . . p . B .
4  . . . . P . . .
3  . . . . . . . .
2  P P P . . P P P
1  . . K . . . . .
   a b c d e f g h
```

The rook on d8 checkmates the king on e8, protected by the bishop on g5 (covers d8 via diagonal e7? No — the bishop controls e7 and f6, cutting off king retreats). The black knight on b8, bishop on f8, and pawns block all escapes. From Morphy's Opera Game (Paris 1858): 17.Rd8#. A type of Anderssen's mate with an uncastled king.

---

## Pillsbury's mate

FEN: `5rk1/5p1p/5B2/8/8/8/8/6R1 b - - 0 1`

```
8  . . . . . r k .
7  . . . . . p . p
6  . . . . . B . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . R .
   a b c d e f g h
```

The rook on g1 checks the king on g8 via the g-file; the bishop on f6 covers g7 and g5; the black rook on f8 blocks f8; the black pawn on f7 blocks f7; the black pawn on h7 blocks h7. Named after Harry Nelson Pillsbury. Very similar to Morphy's mate; the bishop can be on h6 in alternative versions.

---

## Smothered mate

FEN: `6rk/5Npp/8/8/8/8/8/8 b - - 0 1`

```
8  . . . . . . r k
7  . . . . . N p p
6  . . . . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

The knight on f7 checks the king on h8; the king is smothered by its own pieces — rook on g8 (blocks g8), pawns on g7 and h7 (block g7 and h7). The classic finishing pattern of Philidor's legacy: a queen sacrifice forces the king into the corner, then the knight delivers smothered mate.

---

## Stamma's mate

FEN: `8/8/8/8/8/8/p1N5/k1K5 b - - 0 1`

```
8  . . . . . . . .
7  . . . . . . . .
6  . . . . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  p . N . . . . .
1  k . K . . . . .
   a b c d e f g h
```

A rare endgame in which king + knight forces mate against king + rook pawn. The knight on c2 checkmates the king on a1; the white king on c1 covers b2 and b1; the pawn on a2 is blocked. Sequence: 1.Nb4+ Ka1 2.Kc1 a2 3.Nc2#. Named after Philipp Stamma.

---

## Réti's mate

FEN: `1nbB4/1pk5/2p5/8/8/8/8/3R4 b - - 0 1`

```
8  . n b B . . . .
7  . p k . . . . .
6  . . p . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . R . . . .
   a b c d e f g h
```

The bishop on d8 checks the king on c7; the rook on d1 covers the d-file (d7); the black knight on b8, bishop on c8, and pawns on b7 and c6 block all escapes. From Réti vs. Tartakower, Vienna 1910 (11 moves). Works by trapping the enemy king with four of its own pieces on flight squares, then attacking with the bishop protected by a rook or queen.

---

## Suffocation mate

A common method using a knight to attack the enemy king with a bishop or queen confining the king's escape routes. Related to the smothered mate but the attacker uses the bishop or queen to cover escape squares rather than relying solely on the king's own pieces.

---

## Swallow's tail mate (guéridon mate)

Similar to the epaulette mate. The queen attacks a king whose retreat squares are occupied by its own rooks (or other pieces), with the queen protected by a rook. The pieces arrange in a swallow's-tail pattern.

---

## Triangle mate

A queen supported by a rook on the same file two squares away delivers checkmate to a king at the edge of the board (or whose escape is blocked). The queen, rook, and king form a triangular shape.

---

## Vuković's mate

A protected rook delivers checkmate to the king at the edge of the board while a knight covers the remaining escape squares. The rook is usually protected by the king or a pawn. Famously used by 13-year-old Bobby Fischer against Donald Byrne in the Game of the Century (1956).
