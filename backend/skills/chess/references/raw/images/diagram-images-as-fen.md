# Raw diagram images → FEN + grid (OCR)

The composed PNG/GIF position diagrams downloaded from Wikimedia Commons,
transcribed by reading the image (vision OCR) into the FEN + ASCII grid the agent
reads. Each placement was **validated in python-chess** (legal board). This is the
same lossless target as the `{{Chess diagram}}` wikitext extraction — done by eye
here because these are rendered images, not templates.

Boards: uppercase = White, lowercase = Black, `.` = empty; ranks 8 (top) → 1
(bottom), files a–h.

---

## Chess_skewer_bishop.png — bishop skewers queen and rook

A White bishop on c4 skewers Black's queen (f7) and the rook behind it (g8): the
queen must move, losing the rook. (Skewer = the more valuable piece is in front.)

FEN: `6r1/p1k2q2/1pb3n1/5pB1/2BR3P/P3P3/6P1/3QK3 w - - 0 1`

```
8  . . . . . . r .
7  p . k . . q . .
6  . p b . . . n .
5  . . . . . p B .
4  . . B R . . . P
3  P . . . P . . .
2  . . . . . . P .
1  . . . Q K . . .
   a b c d e f g h
```
See [[tactics/pins-and-skewers]].

---

## Chess_fork_pawn_chessbase.png — pawn fork

A White pawn on e4 forks Black's bishop (d5) and knight (f5) at once — only one
can be saved. The cheapest forking piece (a pawn) wins a minor piece.

FEN: `r1bqk1nr/pppp1ppp/8/3b1n2/4PP2/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 1`

```
8  r . b q k . n r
7  p p p p . p p p
6  . . . . . . . .
5  . . . b . n . .
4  . . . . P P . .
3  . . N . . . . .
2  P P P . . P P P
1  R . B Q K B . R
   a b c d e f g h
```
See [[tactics/forks-and-double-attacks]].

---

## Chess-tactics-image_skewer-attack_absolute.gif — absolute skewer (approximate)

An *absolute* skewer: a check forces the king to move, exposing the piece behind
it. White queen vs Black king (c6) and rook (g8). **Low-resolution GIF — pawn
squares read approximately; the piece geometry (Q vs K+R skewer) is the point.**

FEN: `6r1/8/2k5/2p3P1/8/5PK1/8/1Q6 w - - 0 1`

```
8  . . . . . . r .
7  . . . . . . . .
6  . . k . . . . .
5  . . p . . . P .
4  . . . . . . . .
3  . . . . . P K .
2  . . . . . . . .
1  . Q . . . . . .
   a b c d e f g h
```
See [[tactics/pins-and-skewers]] (the absolute skewer, king in front).
