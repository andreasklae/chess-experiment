# Zwischenzug — Wikipedia (text + inline FEN/ASCII diagrams)

Source: https://en.wikipedia.org/wiki/Zwischenzug
License: text CC BY-SA 4.0 (Wikipedia); position diagrams reconstructed losslessly from the article's {{Chess diagram}} wikitext into FEN+ASCII (verified in python-chess); composed images from Wikimedia Commons (CC/PD). Retrieved 2026-06-24.
Diagrams: 9 positions inlined as FEN+grid; 0 images downloaded.

---

The **zwischenzug** (German: , "intermediate move"; also called an **in-between move** or **intermezzo**) is a chess tactic in which a player, instead of playing the expected move (commonly a ), first interposes another move posing an immediate threat that the opponent must answer, and only then plays the expected move. It is a move that has a high degree of "initiative". Ideally, the zwischenzug changes the situation to the player's advantage, such as by gaining  or avoiding what would otherwise be a strong continuation for the opponent. When the intermediate move is a check, it is sometimes called an *in-between check*, *zwischenschach*, or *zwischen-check*.

As with any fairly common chess tactic, it is impossible to pinpoint when the first zwischenzug was played. Three early examples are Lichtenhein–Morphy, New York 1857; Rosenthal–De Vere, Paris 1867; and Tartakower–José Raúl Capablanca, New York 1924. The first known use of the term zwischenzug, however, did not occur until 1933, when the prolific American chess authors Fred Reinfeld and Irving Chernev used it in their book *Chess Strategy and Tactics*.

## History

**Diagram 1** — FEN `1r2qk2/1p1pb1pp/3p4/3bpP2/5B2/8/1PPP2PP/1RNBQK2 w - - 0 1`

```
8  . r . . q k . .
7  . p . p b . p p
6  . . . p . . . .
5  . . . b p P . .
4  . . . . . B . .
3  . . . . . . . .
2  . P P P . . P P
1  . R N B Q K . .
   a b c d e f g h
```

No one knows when the first zwischenzug was played, but the tactic existed long before the term itself was created. One early example was Lichtenhein–Morphy, New York 1857. In the diagram, White has just captured Black's knight on e4 and surely expected the recapture 10...dxe4 11.0-0, when White's king is safe and he has the better pawn structure. Morphy, the strongest player of the day, instead played the zwischenzug 10...Qh4! with the threat 11...Qxf2#, so White cannot save the bishop (11.Bf3?? Qxf2#). Instead, White correctly played 11.Qe2 (forcing Black to weaken his pawns), but then erred with 11...dxe4 12.Be3? (after 12.0-0!, Black has only a slight advantage) Bg4! 13.Qc4? Bxe3!! and Morphy went on to win a .

**Diagram 2** — FEN `3r2rk/1pp1b1pp/2q2p2/4pP2/2B3Pn/4B1N1/1P3Q1P/1RN2KR1 w - - 0 1`

```
8  . . . r . . r k
7  . p p . b . p p
6  . . q . . p . .
5  . . . . p P . .
4  . . B . . . P n
3  . . . . B . N .
2  . P . . . Q . P
1  . R N . . K R .
   a b c d e f g h
```

Rosenthal–De Vere, Paris 1867, is another 19th-century example of a zwischenzug. De Vere had earlier sacrificed a piece for two pawns. White has just played 16.Bxb4. Instead of recapturing with 16...Qxb4+, De Vere first played the zwischenzug (specifically, a zwischenschach) 16...Rc1+! After 17.Kd2 Rxf1 18.Qxf1 Qxb4+ 19.Ke2 Qxf4 20.Qg1 Nxe5, De Vere's zwischenzug had netted him two more pawns, leaving him with the  of four pawns for a knight. White resigned after twelve more moves.

**Diagram 3** — FEN `1rBbqk2/1pp3pp/6n1/8/2bpP3/8/1PP2B1P/1RN1Q1KN w - - 0 1`

```
8  . r B b q k . .
7  . p p . . . p p
6  . . . . . . n .
5  . . . . . . . .
4  . . b p P . . .
3  . . . . . . . .
2  . P P . . B . P
1  . R N . Q . K N
   a b c d e f g h
```

Another prominent example that brought the concept of zwischenzug, albeit not the term itself, to public attention was Tartakower–Capablanca, New York 1924. This was a game won by the reigning World Champion at one of the strongest tournaments of the early 20th century. In the position in the diagram, Tartakower (White) has just played 9.Bxb8, thinking he has caught Capablanca in a trap: if 9...Rxb8, 10.Qa4+ and 11.Qxb4 wins a bishop. However, Capablanca sprang the zwischenzug 9...Nd5!, protecting his bishop and also threatening 10...Ne3+, forking White's king and queen. After Tartakower's 10.Kf2 Rxb8, Capablanca had regained his piece and went on to win in 20 more moves. Note that after 10.Bf4 (instead of 10.Kf2), Black would not play 10...Nxf4??, which would still allow 11.Qa4+, winning a piece. Instead, after 10.Bf4 Black would play a second zwischenzug, 10...Qf6!, attacking the bishop again, and also renewing the threat of 11...Ne3+. After a move like 11.Qc1, Black could either take the bishop or consider yet a third zwischenzug with 11...Bd6.

Alekhine, Reinfeld, and Tartakower and du Mont do not call 9...Nd5! a "zwischenzug" in their books (originally published in 1925, 1942, and 1952, respectively). Instead, they refer to it as, respectively, "a bit of finesse", a "sly interpolation", and an "intermediary manoeuvre".

**Diagram 4** — FEN `3kB3/1p1p4/7r/5pn1/7n/3N4/1PPP3P/6R1 w - - 0 1`  (reconstructed; may be a partial/illustrative position)

```
8  . . . k B . . .
7  . p . p . . . .
6  . . . . . . . r
5  . . . . . p n .
4  . . . . . . . n
3  . . . N . . . .
2  . P P P . . . P
1  . . . . . . R .
   a b c d e f g h
```

The earliest known use of the term zwischenzug did not occur until after all of these games. According to chess historian Edward Winter, the first known use was in 1933. Fred Reinfeld and Irving Chernev, annotating the game Max Euwe–Gyula Breyer, Vienna 1921, called Breyer's 27th move, 27...Nge3!, "an important *Zwischenzug*". The game can be played over [http://www.chessgames.com/perl/chessgame?gid=1033550 here].

## Additional examples

**Diagram 5** — FEN `7k/2q3pp/7p/1p6/4Q3/7r/7P/6BK w - - 0 1`

```
8  . . . . . . . k
7  . . q . . . p p
6  . . . . . . . p
5  . p . . . . . .
4  . . . . Q . . .
3  . . . . . . . r
2  . . . . . . . P
1  . . . . . . B K
   a b c d e f g h
```

The diagram shows another example.  Black, on move, plays
:**1... Rxh4?**
expecting White to play 2.Qxh4, when Black retains a material advantage. However, White has a zwischenzug: 
:**2. Qd8+!**
which is followed by 
:**2... Kh7** 
:**3. Qxh4+ Kg8**
:**4. Qxg3**
and White has won a rook, leaving him with a winning position.

## Mieses vs. Reshevsky

**Diagram 6** — FEN `5r1k/1pp3pb/7p/2P1q3/1P1p4/3P2NP/3Q2P1/3R3K w - - 0 1`

```
8  . . . . . r . k
7  . p p . . . p b
6  . . . . . . . p
5  . . P . q . . .
4  . P . p . . . .
3  . . . P . . N P
2  . . . Q . . P .
1  . . . R . . . K
   a b c d e f g h
```

A zwischenzug occurred in Mieses–Reshevsky, Margate 1935. From the position in the diagram, play continued:
:**29. Nd4 Bxd4**
:**30. cxd4**
White must have expected 30...Qxd4 31.Qxc4 Re1+ and then 32.Kg2 gets him out of trouble, but Black has a zwischenzug:
:**30... Re4!**
Making a  on the d-pawn and preventing the capture of his own pawn.  Now if 31.Qxc4, 31...Re1+ forces 32.Rxe1 and White loses his queen.

## L. Steiner vs. Helling

**Diagram 7** — FEN `1r1b2rk/3p2pp/1p2b3/2p5/4P3/2BP2Q1/1PP3nP/1RNB1R1K w - - 0 1`

```
8  . r . b . . r k
7  . . . p . . p p
6  . p . . b . . .
5  . . p . . . . .
4  . . . . P . . .
3  . . B P . . Q .
2  . P P . . . n P
1  . R N B . R . K
   a b c d e f g h
```

L. Steiner–Helling, Berlin 1928, provides another example of the zwischenschach (in-between check). Black has just captured White's pawn on f2 with his knight (). White responded with 
:**16. Qxf2**
expecting the skewer 16...Bg3??, which he would refute with 17.Qxf7+! Rxf7 18.Re8#. Instead, Black first played the zwischenschach 
:**16... Bh2+!** 
Now 17.Kxh2 Qxf2 loses White's queen. The game continued 
:**17.Kf1 Bg3!** 
Not seeing the point, White blithely continued with his plan: 
:**18. Qxf7+?? Rxf7+** 
Now White realized that he is in check (that was the point of 16...Bh2+!), so his intended 19.Re8# is illegal. The forced 19.Bxf7+ Kxf7 would leave Black with queen for rook, an easily winning material advantage, so White resigned.

## Kerchev vs. Karastoichev

**Diagram 8** — FEN `1r4rk/1pp3pb/4p2q/4p3/3P1nP1/5PR1/1PPQ1B2/1R3B2 w - - 0 1`  (reconstructed; may be a partial/illustrative position)

```
8  . r . . . . r k
7  . p p . . . p b
6  . . . . p . . q
5  . . . . p . . .
4  . . . P . n P .
3  . . . . . P R .
2  . P P Q . B . .
1  . R . . . B . .
   a b c d e f g h
```

In the game Zlatozar Kerchev–Emil Stefanov Karastoichev, 1965 (), Black moved 
:**1... Ng5**
discovering an attack on White's queen.  
:**2. Qxg6**
If White moves the queen to another square, Black's knight captures White's rook on f3, winning the exchange. Instead of immediately recapturing the queen, Black played
:**2... Nxf3+**
and White must get out of check.  After
:**3. Bxf3 hxg6**
Black had won the exchange.

## Carlsen vs. Anand

**Diagram 9** — FEN `1r6/1p2bk1p/2Pp1p2/8/5p2/1P3PB1/2P4P/3KR3 w - - 0 1`

```
8  . r . . . . . .
7  . p . . b k . p
6  . . P p . p . .
5  . . . . . . . .
4  . . . . . p . .
3  . P . . . P B .
2  . . P . . . . P
1  . . . K R . . .
   a b c d e f g h
```

In game 5 of the 2013 World Chess Championship match, Carlsen had captured a bishop with 20.cxb6, and Anand maintained material balance by capturing a knight with 20...fxe4, also attacking White's bishop (). Instead of immediately taking the pawn with 21.Bxe4, which would have given Anand the opportunity to fix his queenside pawn weaknesses with 21...axb6, Carlsen played the zwischenzug 
:**21. b7**
After the necessary 
:**21... Rab8**
:**22. Bxe4 Rxb7**
Anand's a- and c-pawns remained isolated. Black's weaker pawn structure was an important factor to Carlsen's initiative in this first decisive game of the match.

## See also
* Chess tactics
* Combination (chess)
* Sente and Tenuki (from Go)

## Notes
## References
*
*
*
*
*
* 
* 
* 
*
*
*
* 
* 
*
* 
* 

Category:Chess tactics
Category:Chess terminology