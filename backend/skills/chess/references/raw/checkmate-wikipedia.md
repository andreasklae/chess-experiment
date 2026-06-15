# Checkmate — Wikipedia

Source: https://en.wikipedia.org/wiki/Checkmate

**Checkmate** (shortened to **mate**) is any game position in chess in which a player's king is in check and there is no possible escape. Checkmating the opponent wins the game.

If a player is not in check but has no legal moves, it is *stalemate* — an immediate draw. A checkmating move is recorded with `#`, e.g. `34.Qg7#`.

Boards below use the same format as `chess__show_position`: uppercase = White, lowercase = Black; ranks 8–1 top to bottom, files a–h left to right. FENs are the final mated position (side to move is in checkmate). All verified with python-chess.

---

## Examples

### Fool's mate

FEN: `rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3`

```
8  r n b . k b n r
7  p p p p . p p p
6  . . . . . . . .
5  . . . . p . . .
4  . . . . . . P q
3  . . . . . P . .
2  P P P P P . . P
1  R N B Q K B N R
   a b c d e f g h
```

The quickest possible checkmate (2 moves). White is mated: 1.f3 e5 2.g4 Qh4#. The queen on h4 checks the white king on e1 via the diagonal h4–e1; the pawns on f3 and g4 block all escape. White to move, no legal moves.

### Scholar's mate

FEN: `r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4`

```
8  r . b q k b . r
7  p p p p . Q p p
6  . . n . . n . .
5  . . . . p . . .
4  . . B . P . . .
3  . . . . . . . .
2  P P P P . P P P
1  R N B . K . N R
   a b c d e f g h
```

Four-move checkmate. The queen on f7 checkmates the black king on e8: 1.e4 e5 2.Qh5 Nc6 3.Bc4 Nf6?? 4.Qxf7#. The queen covers e8 (rank), g8 (diagonal), g7 (rank), e7 (rank); the bishop on c4 covers f7 itself.

---

## Two major pieces (ladder mate)

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

Two major pieces (queens or rooks) push the king to the edge using the ladder technique: one piece checks, the other cuts off the rank above. Ra8 checks on rank 8; Rb7 covers rank 7 and protects Ra8. Works with two rooks, two queens, or rook + queen. Checkmate can be forced in at most 7 moves from any position with two queens, or ~16 with two rooks.

---

## Basic mates

### King and queen

FEN: `k7/1Q6/2K5/8/8/8/8/8 b - - 0 1`

```
8  k . . . . . . .
7  . Q . . . . . .
6  . . K . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

The queen on b7 checks the king on a8 via the a8–b7 diagonal; the queen also covers b8 (b-file) and a7 (rank 7); the white king on c6 covers b7 (own queen — irrelevant here). The king on a8 cannot go to b8 (queen's b-file), a7 (queen's rank 7), or b7 (queen). Checkmate can be forced in at most 10 moves from any starting position. **Key danger: avoid stalemate** — if the queen cuts off all squares but the king is not in check, it is stalemate.

### King and rook

FEN: `k6R/8/1K6/8/8/8/8/8 b - - 0 1`

```
8  k . . . . . . R
7  . . . . . . . .
6  . K . . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

The rook on h8 checks the king on a8 along rank 8; the white king on b6 covers a7 and b7. Checkmate can be forced in at most 16 moves. The technique: box the king into a rectangle, shrink the rectangle to the edge, then force the king to the corner with the kings in opposition. **Key danger: two stalemate patterns** — avoid placing the rook such that the king has no moves but is not in check.

### King and two bishops

FEN: `k7/2B5/1KB5/8/8/8/8/8 b - - 0 1`

```
8  k . . . . . . .
7  . . B . . . . .
6  . K B . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

The bishop on c7 covers b8 and d8; the bishop on c6 covers b7 and d7; the white king on b6 covers a7. The king on a8 has no escape. The two bishops must be on opposite-colored squares. Checkmate can be forced in at most 19 moves. The process: centralize the bishops on adjacent diagonals, use the king aggressively to drive the enemy king to a corner.

### King, bishop and knight

The most difficult basic mate. Checkmate can only be forced in the corner that the bishop controls (the corner on the bishop's color), and requires at most 33 moves. The process requires precise technique and is rarely seen in practice. Only two checkmate positions are possible:

- King checkmated by bishop in the bishop-colored corner (king on edge square adjacent to corner, knight cutting off the final square).
- King checkmated by knight with bishop covering the adjacent corner square.

---

## Common checkmates

### Back-rank mate

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

A rook or queen checkmates a king blocked by its own pawns on the back rank. The king on g8 cannot escape because pawns on f7, g7, h7 deny all second-rank escape. Prevention: make *luft* — play ...h6 or ...g6 to give the king an escape square. See [[patterns/mating-patterns/back-rank-mate]].

### Scholar's mate

See above.

### Fool's mate

See above.

### Smothered mate

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

A knight checkmates a king surrounded (smothered) by its own pieces. The knight on f7 checks the king on h8; the rook on g8, and pawns on g7 and h7 deny all escape. Usually seen in the corner. The classic setup is Philidor's legacy: a queen sacrifice drives the king to the corner, then the knight delivers mate.

---

## Rare checkmates

### Stamma's mate

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

King and knight can force mate against king and rook pawn when the defending king is trapped in front of its pawn. The knight on c2 mates the king on a1; white king on c1 covers b2 and b1. Sequence: 1.Nb4+ Ka1 2.Kc1 a2 3.Nc2#. Named after Philipp Stamma. See [[patterns/mating-patterns/stamma-mate]].

---

## King and two knights

Two knights and a king **cannot force** checkmate against a bare king — the defender can always avoid being mated. However, checkmate positions are possible if the defender blunders. If the weaker side has a pawn, checkmate can sometimes be forced: one knight blockades the pawn, the other eventually delivers mate.

---

## Key principles

- **Avoid stalemate**: When checkmating with queen or rook, never leave the enemy king with no moves unless it is also in check. Common stalemate traps: queen alone cornering a king with no checking move available; rook on adjacent file to cornered king.
- **Use the king**: The king is an essential attacking piece in all basic endgame mates. Bring it toward the enemy king early.
- **Drive to the edge, then corner**: Most basic mates require pushing the enemy king to the edge first, then to a corner.
- **Back-rank awareness**: A castled king with no luft is always vulnerable to back-rank tactics. When significantly ahead materially, check for back-rank mate threats before every move.
