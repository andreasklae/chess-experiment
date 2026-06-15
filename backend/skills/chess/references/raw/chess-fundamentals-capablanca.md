# Chess Fundamentals — J. R. Capablanca (1921)

Source: Project Gutenberg eBook #33870 (public domain).
https://www.gutenberg.org/ebooks/33870

This file converts the book's instructional examples into FEN + modern
algebraic notation (SAN). The original gives positions as image diagrams and
moves in English descriptive notation; here every starting position was
reconstructed from the diagram and the move text, and **every line below was
replayed move-by-move in python-chess** (mates confirmed as mates, draws
confirmed legal). Boards use the same format as `chess__show_position`:
uppercase = White, lowercase = Black; ranks 8-1 top to bottom.

Scope: Chapter I §1-4 (simple mates, pawn promotion, pawn endings, winning
middle-game positions) and Chapter II §9-13 (cardinal principle, the
classical ending, passed pawns, counting, the opposition), plus two
piece-value facts from §14. The opening sections (§5-8, examples 17-21) are
deliberately omitted — this ingestion focuses on mating and strategy.

---

## Chapter I §1 — Some simple mates

### Example 1 — Rook and King v. King

FEN: `7k/8/8/8/8/8/8/R6K w - - 0 1`

```
8  . . . . . . . k
7  . . . . . . . .
6  . . . . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  R . . . . . . K
   a b c d e f g h
```

The principle: **drive the opposing King to the last line on any side of the
board.** The Rook alone cannot mate; the combined action of King and Rook is
needed. Keep your King as much as possible on the same rank or file as the
opposing King. 1.Ra7 immediately confines the Black King to the last rank.

Main line (mate in 10): 1.Ra7 Kg8 2.Kg2 Kf8 3.Kf3 Ke8 4.Ke4 Kd8 5.Kd5 Kc8 6.Kd6 Kb8 7.Rc7 Ka8 8.Kc6 Kb8 9.Kb6 Ka8 10.Rc8#

At move 6, White plays Kd6 and not Kc6, because the Black King would slip
back to d8 and prolong the mate. If Black runs the other way, the same
squeeze works on the other wing: 1.Ra7 Kg8 2.Kg2 Kf8 3.Kf3 Ke8 4.Ke4 Kd8 5.Kd5 Ke8 6.Kd6 Kf8 7.Ke6 Kg8 8.Kf6 Kh8 9.Kg6 Kg8 10.Ra8#

Capablanca: from any position it should be done in under twenty moves.

### Example 2 — Rook and King v. King (king in the centre)

FEN: `8/8/8/4k3/8/8/8/4K2R w - - 0 1`

```
8  . . . . . . . .
7  . . . . . . . .
6  . . . . . . . .
5  . . . . k . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . K . . R
   a b c d e f g h
```

With the Black King in the centre, advance your own King first, to one side
of (not directly in front of) the enemy King. Use the Rook to fence the King
into ever fewer ranks/files; keep the White King next to the Rook to defend
it and take squares from the enemy King.

Line (mate in 11): 1.Ke2 Kd5 2.Ke3 Kc4 3.Rh5 Kc3 4.Rh4 Kc2 5.Rc4+ Kb3 6.Kd3 Kb2 7.Rb4+ Ka3 8.Kc3 Ka2 9.Ra4+ Kb1 10.Ra5 Kc1 11.Ra1#

Note the repeated pattern: rook check on a rank/file forces the King back one
line; the White King steps up; a waiting rook move (9...Kb1 10.Ra5, any
square on the file does it) forces the Black King in front of the White King,
and the rook mates along the first rank.

### Example 3 — Two Bishops and King v. King

FEN: `7k/8/8/8/8/8/8/2B1KB2 w - - 0 1`

```
8  . . . . . . . k
7  . . . . . . . .
6  . . . . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . B . K B . .
   a b c d e f g h
```

The Black King must be driven not just to the edge but **into a corner**, and
the White King must reach the sixth rank near that corner before mate is
possible. The bishops side by side form a diagonal wall.

Line (mate in 14): 1.Bd3 Kg7 2.Bg5 Kf7 3.Bf5 Kg7 4.Kf2 Kf7 5.Kg3 Kg7 6.Kh4 Kf7 7.Kh5 Kg7 8.Bg6 Kg8 9.Kh6 Kf8 10.Bh5 Kg8 11.Be7 Kh8 12.Bg4 Kg8 13.Be6+ Kh8 14.Bf6#

At move 10 White must "mark time" with a bishop (10.Bh5) to force the King
back into the corner. **In all endings of this kind, care must be taken not
to drift into stalemate.** Should be done in under thirty moves.

### Example 4 — Queen and King v. King

FEN: `8/8/8/4k3/8/8/8/3K3Q w - - 0 1`

```
8  . . . . . . . .
7  . . . . . . . .
6  . . . . . . . .
5  . . . . k . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . K . . . Q
   a b c d e f g h
```

The easiest basic mate — the Queen combines Rook and Bishop power. Begin
with a Queen move that limits the Black King's mobility as much as possible,
then bring the King up; force the enemy King to the edge; mate with the
King's support.

Line: 1.Qc6 Kd4 2.Kd2 Ke5 3.Ke3 Kf5 4.Qd6 Kg5 5.Qe6 Kh4 6.Qg6 Kh3 7.Kf3 and now whatever Black plays, White mates next
move (verified: after 7.Kf3, every legal Black move allows mate in one —
e.g. 7...Kh4 8.Qg4#, 7...Kh2 8.Qg2#).

Should always be done in under ten moves. As with the Rook, the King's
co-operation is essential. **The one danger is stalemate: when the enemy
King has been cornered, every non-checking move must leave it at least one
legal move.**

## Chapter I §2 — Pawn promotion

The gain of a single Pawn is often enough to win even with nothing else left.
The governing rule: **the King must be in front of its own Pawn, with at
least one intervening square.** If the defending King reaches the square
directly in front of the Pawn, the game is a draw.

### Example 5 — The draw: defending King in front of the Pawn

FEN: `8/8/8/8/4k3/8/3KP3/8 w - - 0 1`

```
8  . . . . . . . .
7  . . . . . . . .
6  . . . . . . . .
5  . . . . . . . .
4  . . . . k . . .
3  . . . . . . . .
2  . . . K P . . .
1  . . . . . . . .
   a b c d e f g h
```

Drawn with best play. Black keeps his King directly in front of the Pawn;
when that is impossible (because the White King is there), he keeps his King
directly **in front of the White King**:

1.e3 Ke5 2.Kd3 Kd5 3.e4+ Ke5 4.Ke3 Ke6 5.Kf4 Kf6 6.e5+ Ke6 7.Ke4 Ke7 8.Kd5 Kd7 9.e6+ Ke7 10.Ke5 Ke8 11.Kd6 Kd8

Now if 12.e7+ Ke8 13.Ke6 is stalemate, and anything else lets the Black King
return to e8/blockade. The defender's two rules: stay in front of the pawn;
when pushed off, take the square directly in front of the enemy King.

### Example 6 — The win: attacking King in front of the Pawn

FEN: `8/8/5k2/8/5K2/8/4P3/8 w - - 0 1`

```
8  . . . . . . . .
7  . . . . . . . .
6  . . . . . k . .
5  . . . . . . . .
4  . . . . . K . .
3  . . . . . . . .
2  . . . . P . . .
1  . . . . . . . .
   a b c d e f g h
```

White wins. The method: **advance the King as far as is compatible with the
safety of the Pawn, and never advance the Pawn until it is essential to its
own safety.**

1.Ke4 Ke6 2.e3 Kf6 3.Kd5 Ke7 4.Ke5 Kd7 5.Kf6 Ke8 6.e4 Kd7 7.e5 Ke8 8.Ke6 Kf8 9.Kd7 and the Pawn marches e6-e7-e8=Q, every square protected
by the King.

The key moments: 2.e3! is a *waiting move* — Black held the opposition
(1...Ke6), so White spends a pawn-tempo to force the Black King to give way.
8.Ke6! (not 8.e6?, which draws as in Example 5 — the pawn would outrun its
King). The Pawn stays behind the King the whole way.

## Chapter I §3 — Pawn endings (two v. one, three v. two)

### Example 7 — Two pawns v. one, all on one side

FEN: `5k2/6p1/4K1P1/5P2/8/8/8/8 w - - 0 1`

```
8  . . . . . k . .
7  . . . . . . p .
6  . . . . K . P .
5  . . . . . P . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

The hasty 1.f6? only draws: 1...Kg8! (not 1...gxf6?, which loses) 2.fxg7
Kxg7 (drawn as Example 5), or 2.f7+ Kf8 and the Pawn is lost, or 2.Ke7 gxf6
3.Kxf6 Kf8 with a book draw. White wins by improving the King first:

1.Kd7 Kg8 2.Ke7 Kh8 3.f6 gxf6 4.Kf7 f5 5.g7+ Kh7 6.g8=Q+ Kh6 7.Qg6#

If 3...Kg8 instead of 3...gxf6, then 3.f6 Kg8 4.f7+ Kh8 5.f8=Q# —
a back-corner promotion mate.

### Example 8 — Two pawns v. one: giving one back

FEN: `8/6p1/3k4/8/3K1PP1/8/8/8 w - - 0 1`

```
8  . . . . . . . .
7  . . . . . . p .
6  . . . k . . . .
5  . . . . . . . .
4  . . . K . P P .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

Neither 1.f5? g6! nor 1.g5? g6! wins (the opposition governs). White wins
with the King first, and at the critical moment **gives up one Pawn to win
the enemy Pawn and reach a won single-pawn ending**:

1.Ke4 Ke6 2.f5+ Kf6 3.Kf4 g6 4.g5+ Kf7 5.f6 Ke6 6.Ke4 Kf7 7.Ke5 Kf8 8.f7 Kxf7 9.Kd6 Kf8 10.Ke6 Kg7 11.Ke7 Kg8 12.Kf6 Kh7 13.Kf7 Kh8 14.Kxg6 Kg8 15.Kh6 Kh8 16.g6 Kg8 17.g7 Kf7 18.Kh7 and the Pawn queens.

The instructive moment is 8.f7! Kxf7 9.Kd6 — White sacrifices the
advanced pawn to outflank, walk to g6/h6, win the g6-pawn, and queen the
remaining one. Even "simple" endings demand exact play.

### Example 9 — Three pawns v. two

FEN: `8/6pp/3k4/8/3K1PPP/8/8/8 w - - 0 1`

```
8  . . . . . . . .
7  . . . . . . p p
6  . . . k . . . .
5  . . . . . . . .
4  . . . K . P P P
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

General rule: **advance the Pawn that has no Pawn opposing it** (here the
f-pawn). 1.f5 Ke7 2.Ke5 Kf7 3.g5 Ke7 4.h5 followed by g6, reducing to the endings already
shown. Side lines: 1...g6 2.f6, or 3...g6 4.f6, or 3...h6 4.g6+ — each
transposes to a winning structure from Examples 7-8.

### Example 10 — Pawns on both sides of the board

FEN: `8/p6p/4k3/8/4K3/8/P5PP/8 w - - 0 1`

```
8  . . . . . . . .
7  p . . . . . . p
6  . . . . k . . .
5  . . . . . . . .
4  . . . . K . . .
3  . . . . . . . .
2  P . . . . . P P
1  . . . . . . . .
   a b c d e f g h
```

With pawns on both wings: **act at once on the side where you have the
superior force.** Advance the unopposed Pawn first; stop the enemy's
counter-advance on the other wing when his King is far from it.

1.g4 a5 2.a4 Kf6 3.h4 Ke6 4.g5 Kf7 5.Kf5 Kg7 6.h5 Kf7 7.Ke5 — the kingside pawns are now self-defending (if
...h6 then g6 and they hold each other), so the White King walks to the
queenside, wins the a5-pawn, and queens the a-pawn long before Black gets
counterplay. Decide such races by **counting moves**, not by guessing.

## Chapter I §4 — Winning positions in the middle-game

Four combinations against the castled King. All of them rest on the same
foundation: **several pieces co-ordinated against one weak point** — here
the h7/g7 squares and the back rank.

### Example 11 — Queen sacrifice on h7, rook-lift mate

FEN: `5rk1/1b3p1p/pbq3p1/2p5/8/1P1P1R1Q/PBP3PB/7K b - - 0 1` (Black to move)

```
8  . . . . . r k .
7  . b . . . p . p
6  p b q . . . p .
5  . . p . . . . .
4  . . . . . . . .
3  . P . P . R . Q
2  P B P . . . P B
1  . . . . . . . K
   a b c d e f g h
```

Black, seeing only the slow threat Qh6-followed-by-Qg7#, plays 1...Re8
intending ...Re1+ with a counter-attack. White uncovers the real point —
the b2-Bishop's command of h8:

1...Re8 2.Qxh7+ Kxh7 3.Rh3+ Kg8 4.Rh8#

The mate works because the long-diagonal Bishop defends h8 and covers g7,
so the King has no flight square. The Queen is given away to drag the King
onto the h-file for the rook lift.

### Example 12 — The same mate as a standing threat

FEN: `5rk1/1bq1bp1p/p1n3p1/1p6/3N4/1P1PR2Q/PBP3PB/7K w - - 0 1`

```
8  . . . . . r k .
7  . b q . b p . p
6  p . n . . . p .
5  . p . . . . . .
4  . . . N . . . .
3  . P . P R . . Q
2  P B P . . . P B
1  . . . . . . . K
   a b c d e f g h
```

White is a piece down and must act: 1.Nxc6 Bb4 2.Ne7+ Qxe7 3.Rxe7 Bxe7 4.Qd7 forking b7 and e7 —
White regains the piece with interest (Q+B v. R+B).

Black could never accept the first capture: 1.Nxc6 Bxc6 2.Qxh7+ Kxh7 3.Rh3+ Kg8 4.Rh8# — the
Example-11 mate verbatim. A mating pattern you know is worth material even
when it never lands: here it forces Black's replies for two moves.
These two examples show the danger of advancing the g-pawn one square after
castling on that side.

### Example 13 — Knight sacrifice rips the long diagonal

FEN: `2q2rk1/1b3ppp/pp6/2p5/2P1N3/PP1Q4/1B3PPP/6K1 w - - 0 1`

```
8  . . q . . r k .
7  . b . . . p p p
6  p p . . . . . .
5  . . p . . . . .
4  . . P . N . . .
3  P P . Q . . . .
2  . B . . . P P P
1  . . . . . . K .
   a b c d e f g h
```

Black is the exchange up and should win — unless White gets compensation
immediately. He mates in three:

1.Nf6+ gxf6 2.Qg3+ Kh8 3.Bxf6#

1...gxf6 is forced (1.Nf6+ Kh8 2.Qxh7# otherwise — Qd3-h7 supported by the
knight). The capture opens both the g-file for the Queen check and the long
diagonal for the b2-Bishop. Queen + Bishop battery against a fianchetto-less
castled King is one of the most common mating set-ups.

### Example 14 — The same pattern, one preparation deeper

FEN: `2q1rrk1/1bpn1ppp/pp1p4/1B6/4N3/1P1QR3/PBP2PPP/6K1 w - - 0 1`

```
8  . . q . r r k .
7  . b p n . p p p
6  p p . p . . . .
5  . B . . . . . .
4  . . . . N . . .
3  . P . Q R . . .
2  P B P . . P P P
1  . . . . . . K .
   a b c d e f g h
```

1.Bxd7 Qxd7 2.Nf6+ gxf6 3.Rg3+ Kh8 4.Bxf6#

First 1.Bxd7 removes the defender; the rest is Example 13 with the rook
playing the Queen's role on the g-file. If 1...Bxe4 (declining), then
2.Qc3! threatens
Qxg7# on the long diagonal and wins the c8-Queen, which Bd7 already attacks.
Note 3...Kf8 is impossible in the main line because Black's own rook sits
on f8 — a crowded back rank traps its King.

### Example 15 — The classic Bishop sacrifice on h7 (Greek gift)

FEN: `r3qrk1/1pp2ppp/p1np4/3Q4/8/P2B1N2/1PP2PPP/3R2K1 w - - 0 1`

```
8  r . . . q r k .
7  . p p . . p p p
6  p . n p . . . .
5  . . . Q . . . .
4  . . . . . . . .
3  P . . B . N . .
2  . P P . . P P P
1  . . . R . . K .
   a b c d e f g h
```

White is the exchange and a Pawn behind, but wins:

1.Bxh7+ Kxh7 2.Qh5+ Kg8 3.Ng5 Qe4 4.Nxe4

After 3.Ng5 the threat is Qh7#; Black's only resource is to give back the
Queen with 3...Qe4 covering h7 (4.Nxe4 leaves White a Queen for a Rook up).
Declining doesn't help: 1.Bxh7+ Kh8 2.Qh5 g6 3.Qh6 and mate on g7/h7 follows. The
ingredients of the Greek gift: Bishop reaching h7 with check, Queen able to
reach h5, Knight able to reach g5.

### Example 16 — Greek gift, heavy-piece version

FEN: `2nb1rk1/1pqrnppp/p2p4/2pQ1N2/6P1/1P1B1N1P/P3RP2/3R2K1 w - - 0 1`

```
8  . . n b . r k .
7  . p q r n p p p
6  p . . p . . . .
5  . . p Q . N . .
4  . . . . . . P .
3  . P . B . N . P
2  P . . . R P . .
1  . . . R . . K .
   a b c d e f g h
```

The same type in a more complicated form. White first eliminates the
defenders of h7/g5, then sacrifices:

1.Nxe7+ Bxe7 2.Rxe7 Nxe7 3.Bxh7+ Kxh7 4.Qh5+ Kg8 5.Ng5 Rc8 6.Qh7+ Kf8 7.Qh8+ Ng8 8.Nh7+ Ke7 9.Re1+ Kd8 10.Qxg8#

(5...Rc8 frees f8 for the King but later blocks its own King's last flight
square — 10.Qxg8 is mate partly *because* of it.) If Black declines with
5...Kh8 (after 3.Bxh7+): 1.Nxe7+ Bxe7 2.Rxe7 Nxe7 3.Bxh7+ Kh8 4.Qh5 g6 5.Bxg6 Kg7 6.Qh7+ Kf6 7.g5+ Ke6 8.Bxf7+ Rxf7 9.Qe4# — the King is dragged up the
board and mated in the centre. Capablanca's comment: a beginner cannot
calculate all of this, but **knowing the type of combination** lets you find
it when the ingredients are present.

## Chapter II §9 — A cardinal principle

### Example 22 — A unit that holds two

FEN: `8/p5p1/7p/6k1/8/7K/PP5P/8 w - - 0 1`

```
8  . . . . . . . .
7  p . . . . . p .
6  . . . . . . . p
5  . . . . . . k .
4  . . . . . . . .
3  . . . . . . . K
2  P P . . . . . P
1  . . . . . . . .
   a b c d e f g h
```

White draws with 1.b4! (advance the candidate — the Pawn free from
opposition). Suppose instead 1.a4?. Then 1...a5! applies a cardinal
principle of chess strategy: **one unit that holds two** — the single Black
a-pawn now fixes both White queenside Pawns (b4 can be met by ...axb4 and
the a-pawn is stopped by ...a5xb4... while a4-a5 is permanently impossible).

1.a4 a5 2.Kg2 Kf4 3.b4 axb4 4.a5 b3 5.a6 b2 6.a7 b1=Q 7.a8=Q Qe4+ 8.Qxe4+ Kxe4

Both sides queen, but Black's new Queen checks first and trades itself for
White's — counting decides again — and the resulting K+P ending is won for
Black (next example).

## Chapter II §10 — A classical ending

### Example 23 — Two pawns v. one, the three-part winning plan

FEN: `8/6p1/7p/8/4k3/8/6KP/8 w - - 0 1` (the position Example 22 produces; White to move, Black wins)

```
8  . . . . . . . .
7  . . . . . . p .
6  . . . . . . . p
5  . . . . . . . .
4  . . . . k . . .
3  . . . . . . . .
2  . . . . . . K P
1  . . . . . . . .
   a b c d e f g h
```

Capablanca divides the win into three parts and recommends learning to plan
this way — **a plan with stages, executed in order**:

1. **Part one:** march the King to h3, keeping the Pawns untouched (their
   ability to move one *or* two squares later is the winning tempo-reserve).
2. **Part two:** advance the rear Pawn (the h-pawn) up beside the King.
3. **Part three:** time the g-pawn's advance — one square or two according
   to where the White King stands — so that ...g3 comes with White's King
   in the corner.

1.Kg3 Ke3 2.Kg2 Kf4 3.Kf2 Kg4 4.Kg2 Kh4 5.Kg1 Kh3 6.Kh1 h5 7.Kg1 h4 8.Kh1 g5 9.Kg1 g4 10.Kh1 g3 11.hxg3 hxg3 12.Kg1 g2 13.Kf2 Kh2 and the g-pawn queens.

White's best defence was to keep the Pawn on h2 throughout; any pawn move
loses faster. The defender is put in zugzwang by the tempo-reserve.

## Chapter II §11 — Obtaining a passed pawn

### Example 24 — Three v. three: the centre pawn breaks through

FEN: `8/ppp4k/8/PPP5/8/8/8/7K w - - 0 1`

```
8  . . . . . . . .
7  p p p . . . . k
6  . . . . . . . .
5  P P P . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . K
   a b c d e f g h
```

When three connected Pawns face three, **advance the centre Pawn** to force
a passed pawn: 1.b6 axb6 2.c6 bxc6 3.a6 (or 1...cxb6 2.a6! — same idea mirrored)
and White's outside pawn is closer to queening than any Black pawn.

With Black to move, 1...b6! equalises: 2.cxb6 cxb6 3.axb6 axb6 and the
breakthrough is gone — a draw with correct play. Whoever moves first in
such structures gets the passed pawn.

## Chapter II §12 — Which pawn queens first?

### Example 25 — Counting, and the queening square

FEN: `6k1/p6p/8/1P6/8/1K6/P7/8 w - - 0 1` (whoever moves, wins)

```
8  . . . . . . k .
7  p . . . . . . p
6  . . . . . . . .
5  . P . . . . . .
4  . . . . . . . .
3  . K . . . . . .
2  P . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

Two skills decide pawn races. First, **count whether the enemy King can
catch your runner** (here it cannot — g7 is too far from the a-file).
Second, count which Pawn promotes first, and **check whether the first new
Queen controls the other's queening square**:

1.a4 h5 2.a5 h4 3.b6 axb6 4.a6 h3 5.a7 h2 6.a8=Q

3.b6! deflects the a7-pawn (costing Black a tempo), and White queens on a8 —
which commands h1 along the long diagonal, so Black's h-pawn never promotes.
Make a habit of counting; it converts guesswork into certainty.

## Chapter II §13 — The opposition

Kings face each other with one square between (on a file: `8/8/4k3/1p5p/1P2K2P/8/8/8 w - - 0 1` —
frontal; the same relation exists diagonally and laterally): the player who
has **moved last** "has the opposition" — the other King must give way.
When the Kings are on the same line with an **even** number of squares
between them, the player **to move** can seize the opposition.

### Example 27 — The opposition decides a symmetric position

FEN: `4k3/8/8/1p5p/1P5P/8/8/4K3 w - - 0 1` (whoever moves, wins)

```
8  . . . . k . . .
7  . . . . . . . .
6  . . . . . . . .
5  . p . . . . . p
4  . P . . . . . P
3  . . . . . . . .
2  . . . . . . . .
1  . . . . K . . .
   a b c d e f g h
```

Apparently dead equal; in fact whoever moves wins. March straight up:

1.Ke2 Ke7 2.Ke3 Ke6 3.Ke4 Kf6 4.Kf4 Kg6 5.Ke5 Kg7 and counting shows White wins Black's b-pawn and queens
(4.Kd5? — passing through — only draws; 4.Kf4! keeps the opposition, and
4...Ke6 5.Kg5 wins the h-pawn instead).

Against the waiting defence: 1.Ke2 Kd8 2.Kf3 Ke7 3.Ke3 — when the opponent makes
a waiting move (1...Kd8), **advance leaving a rank or file free between the
Kings** (2.Kf3!); 2.Kd3? Kd7! or 2.Ke3? Ke7! gives Black the opposition.

### Example 28 — Distant opposition as a defence

FEN: `8/8/8/4p1p1/8/5P2/6K1/3k4 w - - 0 1`

```
8  . . . . . . . .
7  . . . . . . . .
6  . . . . . . . .
5  . . . . p . p .
4  . . . . . . . .
3  . . . . . P . .
2  . . . . . . K .
1  . . . k . . . .
   a b c d e f g h
```

White is a Pawn down and apparently lost, yet draws with **1.Kh1!** taking
the *distant* opposition. The close opposition fails: 1.Kf1 Kd2 2.Kf2 Kd3
and White cannot keep the lateral opposition because his own Pawn occupies
f3. After 1.Kh1!: 1.Kh1 Kd2 2.Kh2 Kd3 3.Kh3 Ke2 4.Kg2 Ke3 5.Kg3 Kd4 6.Kg4 Ke3 7.Kg3 — White always regains the
opposition, and 6.Kg4 attacks g5 to force Black back.

If Black tries the pawn race: 1.Kh1 g4 2.Kg2 Kd2 3.fxg4 e4 and counting shows both
sides queen — draw. (But 2.fxg4? e4! would lose; and 2...gxf3+ 3.Kxf3
followed by Ke4 holds.)

Capablanca: go back over every King-and-Pawn example in this book — the
opposition is of paramount importance in nearly all of them.

## Chapter II §14 — Two facts worth remembering

- **Two Knights and King cannot force mate** against a bare King (they can
  only stalemate it; mate can sometimes be forced if the defender still has
  a pawn to move).
- **The wrong rook's pawn:** with King + Bishop + rook's pawn whose queening
  corner is the *opposite* colour to the Bishop, the position is a **draw**
  if the defending King reaches the corner — the Bishop is worthless there.
  When choosing which pawn to keep or promote, avoid this case.
- Endgame piece placement: keep your own Pawns on squares of **opposite**
  colour to your own Bishop; keep them on the **same** colour as the
  *opponent's* Bishop.

---

*Conversion notes: positions were reconstructed from the book's diagrams
(read from the Gutenberg image files) plus the move text; descriptive
notation was translated to SAN (Black's descriptive moves read from Black's
side). Every line replayed cleanly in python-chess; all claimed mates are
genuine checkmates. Example 16's "5...R-B1" is rendered as 5...Rc8 (QB1) —
the only reading under which the printed mate works, confirmed by replay.
Omitted: §5-8 (piece values table, opening strategy, traps — out of scope
for the mating/strategy ingestion), Examples 29-33 diagrams (their two
durable facts are summarised above).*
