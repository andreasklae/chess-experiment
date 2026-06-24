# Zugzwang — Wikipedia (text + inline FEN/ASCII diagrams)

Source: https://en.wikipedia.org/wiki/Zugzwang
License: text CC BY-SA 4.0 (Wikipedia); position diagrams reconstructed losslessly from the article's {{Chess diagram}} wikitext into FEN+ASCII (verified in python-chess); composed images from Wikimedia Commons (CC/PD). Retrieved 2026-06-24.
Diagrams: 20 positions inlined as FEN+grid; 0 images downloaded.

---

**Zugzwang** (; ) is a situation found in chess and other turn-based games wherein one player is put at a disadvantage because of their obligation to make a move; a player is said to be "in zugzwang" when any legal move will worsen their position.

Although the term is used less precisely in games such as chess, it is used specifically in combinatorial game theory to denote a move that directly changes the outcome of the game from a win to a loss. Putting the opponent in zugzwang is a common way to help the superior side win a game, and in some cases it is necessary in order to make the win possible. More generally, the term can also be used to describe a situation where passing the turn, if this were allowed, would be the best move.

The term *zugzwang* was used in German chess literature in 1858 or earlier,

## Etymology
The word comes from German  'move' +  'compulsion', so that  means 'being forced to make a move'. Originally the term was used interchangeably with the term  'obligation to make a move' as a general game rule. Games like chess and checkers have "zugzwang" (or "zugpflicht"): a player  always make a move on their turn even if this is to their disadvantage. Over time, the term became especially associated with chess.

According to chess historian Edward Winter, the term had been in use in German chess circles in the 19th century.

 had an unsigned article . Friedrich Amelung employed the terms ,  and  on pages 257–259 of the September 1896 issue of the same magazine. When a perceived example of zugzwang occurred in the third game of the 1896–97 world championship match between Steinitz and Lasker, after 34...Rg8, the  (December 1896, page 368) reported that "White has died of zugzwang".}}

The earliest known use of the term zugzwang in English was on page 166 of the February 1905 issue of *Lasker's Chess Magazine*. The term did not become common in English-language chess sources until the 1930s, after the publication of the English translation of Nimzowitsch's *My System* in 1929.

## History

**Diagram 1** — FEN `8/8/8/3k1K2/8/4R3/5n2/8 w - - 0 1`

```
8  . . . . . . . .
7  . . . . . . . .
6  . . . . . . . .
5  . . . k . K . .
4  . . . . . . . .
3  . . . . R . . .
2  . . . . . n . .
1  . . . . . . . .
   a b c d e f g h
```

The concept of zugzwang, if not the term, must have been known to players for many centuries. Zugzwang is required to win the elementary (and common) king and rook versus king endgame, and the king and rook (or differently named pieces with the same abilities) have been chess pieces since the earliest versions of the game.

Other than basic checkmates, the earliest published use of zugzwang may be in this study by Zairab Katai, which was published sometime between 813 and 833, discussing shatranj. After
:**1. Re3 Ng1**
:**2. Kf5 Kd4**
:**3. Kf4**
puts Black in zugzwang, since the black king must abandon its attack on the white rook and thus allow the white king to trap the knight: 3...Kc4 4.Kg3 (or Kg4) Kd4 5.Re1 and White wins.

**Diagram 2** — FEN `8/8/7p/8/8/8/1pk1K3/3R4 w - - 0 1`

```
8  . . . . . . . .
7  . . . . . . . .
6  . . . . . . . p
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . p k . K . . .
1  . . . R . . . .
   a b c d e f g h
```

**Diagram 3** — FEN `8/8/8/8/1Q6/4K3/2r5/2k5 w - - 0 1`

```
8  . . . . . . . .
7  . . . . . . . .
6  . . . . . . . .
5  . . . . . . . .
4  . Q . . . . . .
3  . . . . K . . .
2  . . r . . . . .
1  . . k . . . . .
   a b c d e f g h
```

The concept of zugzwang is also seen in the 1585 endgame study by Giulio Cesare Polerio, published in 1604 by Alessandro Salvio, one of the earliest writers on the game. The only way for White to win is 1.Ra1 Kxa1 2.Kc2, placing Black in zugzwang. The only legal move is 2...g5, whereupon White promotes a pawn first and then checkmates with 3.hxg5 h4 4.g6 h3 5.g7 h2 6.g8=Q h1=Q 7.Qg7.

Joseph Bertin refers to zugzwang in *The Noble Game of Chess* (1735), wherein he documents 19 rules about chess play. His 18th rule is: "To play well the latter end of a game, you must calculate who has the move, on which the game always depends."

François-André Danican Philidor wrote in 1777 of the position illustrated that after White plays 36.Kc3, Black "is obliged to move his rook from his king, which gives you an opportunity of taking his rook by a double check , or making him mate". Lasker explicitly cited a mirror image of this position (White: king on f3, queen on h4; Black: king on g1, rook on g2) as an example of zugzwang in *Lasker's Manual of Chess*. The British master George Walker analyzed a similar position in the same endgame, giving a maneuver (triangulation) that resulted in the superior side reaching the initial position, but now with the inferior side on move and in zugzwang. Walker wrote of the superior side's decisive move: "throwing the move upon Black, in the initial position, and thereby winning".

**Diagram 4** — FEN `1kbK4/1pp5/2P5/8/8/8/1R6/8 w - - 0 1`

```
8  . k b K . . . .
7  . p p . . . . .
6  . . P . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . R . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

Paul Morphy is credited with composing the position illustrated "while still a young boy". After 1.Ra6, Black is in zugzwang and must allow mate on the next move with 1...bxa6 2.b7# or 1...B (moves) 2.Rxa7#.

## Zugzwang in chess
There are three types of chess positions: either none, one, or both of the players would be at a disadvantage if it were their turn to move. The great majority of positions are of the first type.  In chess literature, most writers call positions of the second type *zugzwang*, and the third type *reciprocal zugzwang* or *mutual zugzwang*.  Some writers call the second type a *squeeze* and the third type *zugzwang*.

Normally in chess, having tempo is desirable because the player who is to move has the advantage of being able to choose a move that improves their situation. Zugzwang typically occurs when "the player to move cannot do anything without making an important concession".

**Diagram 5** — FEN `3k4/3P4/4K3/8/8/8/8/8 w - - 0 1`

```
8  . . . k . . . .
7  . . . P . . . .
6  . . . . K . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

**Diagram 6** — FEN `8/8/4k3/2p1p1p1/2P1K1P1/3P4/8/8 w - - 0 1`

```
8  . . . . . . . .
7  . . . . . . . .
6  . . . . k . . .
5  . . p . p . p .
4  . . P . K . P .
3  . . . P . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

Zugzwang most often occurs in the endgame when the number of pieces, and so the number of possible moves, is reduced, and the exact move chosen is often critical. The first diagram shows the simplest possible example of zugzwang. If it is White's move, they must either stalemate Black with 1.Kc6 or abandon the pawn, allowing 1...Kxc7 with a draw. If it is Black's move, the only legal move is 1...Kb7, which allows White to win with 2.Kd7 followed by queening the pawn on the next move.

The second diagram is another simple example. Black, on move, must allow White to play Kc5 or Ke5, when White wins one or more pawns and can advance their own pawn toward promotion. White, on move, must retreat their king, when Black is out of danger. The squares d4 and d6 are *corresponding squares*. Whenever the white king is on d4 with White to move, the black king must be on d6 to prevent the advance of the white king.

In many cases, the player having the move can put the other player in zugzwang by using *triangulation*. This often occurs in king and pawn endgames. Pieces other than the king can also triangulate to achieve zugzwang, such as in the KQ vs. KR Philidor position. Zugzwang is a mainstay of chess compositions and occurs frequently in endgame studies.

## Examples from games
## Fischer vs. Taimanov, second match game

**Diagram 7** — FEN `8/8/6K1/6Bn/6k1/8/8/8 w - - 0 1`

```
8  . . . . . . . .
7  . . . . . . . .
6  . . . . . . K .
5  . . . . . . B n
4  . . . . . . k .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

Some zugzwang positions occurred in the second game of the 1971 candidates match between Bobby Fischer and Mark Taimanov.  In the position in the diagram, Black is in zugzwang because he would rather not move, but he must: a king move would lose the knight, while a knight move would allow the passed pawn to advance.  The game continued:
: **85... Nf3**
: **86. h6 Ng5**
: **87. Kg6**
and Black is again in zugzwang.  The game ended shortly (because the pawn will slip through and promote):
: **87... Nf3**
: **88. h7 Ne5+**
: **89. Kf6 **

## Fischer vs. Taimanov, fourth match game

**Diagram 8** — FEN `8/3k1n2/1Kp4p/1p1p2p1/1P4P1/3P2BP/2P5/8 w - - 0 1`

```
8  . . . . . . . .
7  . . . k . n . .
6  . K p . . . . p
5  . p . p . . p .
4  . P . . . . P .
3  . . . P . . B P
2  . . P . . . . .
1  . . . . . . . .
   a b c d e f g h
```

In the position shown, White has just gotten his king to a6, where it attacks the black pawn on b6, tying down the black king to defend it.  White now needs to get his bishop to f7 or e8 to attack the pawn on g6.  Play continued:
: **57... Nc8**
: **58. Bd5 Ne7**
Now the bishop is able to make a waiting move. It is able to do so while maintaining access to f7, so that it can reach e8 safely, where it attacks the pawn on g6 and restricts the black king from c6.
: **59. Bc4 Nc6**
: **60. Bf7 Ne7**
: **61. Be8**
and Black is in zugzwang.  Knights are unable to lose a tempo, so moving the knight would allow the bishop to capture the  pawns.  The black king must give way.
: **61... Kd8**
: **62. Bxg6! Nxg6**
: **63. Kxb6 Kd7**
: **64. Kxc5**
and White has a winning position.  Either one of White's  pawns will promote or the white king will attack and win the black kingside pawns and a kingside pawn will promote.  Black resigned seven moves later.  Andy Soltis says that this is "perhaps Fischer's most famous endgame".

## Tseshkovsky vs. Flear, 1988

**Diagram 9** — FEN `8/4b1r1/4P3/5K1Q/8/8/8/8 w - - 0 1`  (reconstructed; may be a partial/illustrative position)

```
8  . . . . . . . .
7  . . . . b . r .
6  . . . . P . . .
5  . . . . . K . Q
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

This position from a 1988 game between Vitaly Tseshkovsky and Glenn Flear at Wijk aan Zee shows an instance of "zugzwang" where the obligation to move makes the defense more difficult, but it does not mean the loss of the game.  A draw by agreement was reached eleven moves later.

## Reciprocal zugzwang

**Diagram 10** — FEN `3k4/3P4/2K5/8/8/8/8/8 w - - 0 1`

```
8  . . . k . . . .
7  . . . P . . . .
6  . . K . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

A special case of zugzwang is *reciprocal zugzwang* (also known as *mutual zugzwang*): a position that is in zugzwang regardless of which player's turn it is to move. The study of reciprocal zugzwang positions is considered part of endgame theory.

In practice, a reciprocal zugzwang position must have been reached by a previous move by one of the players, so only the player to move is actually in zugzwang. However, the other player must play carefully because one inaccurate move can often result in zugzwang themselves, for example by returning to the same position but on the other player's turn. That is unlike regular zugzwang, in which the superior side usually has a  or can triangulate to put the opponent in zugzwang.

## Trébuchet

**Diagram 11** — FEN `8/8/8/4pK2/3kP3/8/8/8 w - - 0 1`

```
8  . . . . . . . .
7  . . . . . . . .
6  . . . . . . . .
5  . . . . p K . .
4  . . . k P . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

An extreme type of reciprocal zugzwang, called *trébuchet*, is shown in the diagram. It is also called a *full-point mutual zugzwang* because it will result in a loss for the player in zugzwang, resulting in a full point for the opponent. Whoever is to move in this position must abandon their own pawn, thus allowing the opponent to capture it and proceed to promote their own pawn, resulting in an easily winnable position.

## Mined squares

**Diagram 12** — FEN `8/8/2k1p3/3P1K2/8/8/8/8 w - - 0 1`

```
8  . . . . . . . .
7  . . . . . . . .
6  . . k . p . . .
5  . . . P . K . .
4  . . . . . . . .
3  . . . . . . . .
2  . . . . . . . .
1  . . . . . . . .
   a b c d e f g h
```

Corresponding squares are squares of mutual zugzwang.  When there is only one pair of corresponding squares, they are called *mined squares*.  A player will fall into zugzwang if they move their king onto the square and their opponent is able to move onto the corresponding square.  In the diagram here, if either king moves onto the square marked with the dot of the same color, it falls into zugzwang if the other king moves into the mined square near them.

## Zugzwang helps the defense

**Diagram 13** — FEN `8/8/8/2Nk4/1P6/8/3K4/8 w - - 0 1`

```
8  . . . . . . . .
7  . . . . . . . .
6  . . . . . . . .
5  . . N k . . . .
4  . P . . . . . .
3  . . . . . . . .
2  . . . K . . . .
1  . . . . . . . .
   a b c d e f g h
```

Zugzwang usually works in favor of the stronger side, but sometimes it aids the defense.  In this position based on a game between Zoltán Varga and Péter Ács, it saves the game for the defense:
: **1... Kc4**
Reciprocal zugzwang.
: **2. Nc3 Kb4**
Reciprocal zugzwang again.
: **3. Kd3 Bg7**
Reciprocal zugzwang again.
: **4. Kc2 Bh6 5. Kd3 Bg7 6. Nd5+ Kxa4 7. Ke4 Kb5 8. Kf5 Kc5 9. Kg6 Bd4 10. Nf4 Kd6 11. h6 Ke7 12. h7 Bb2**
This position is a draw and the players agreed to a draw a few moves later.

## Zugzwang in middlegames and complex endgames
Alex Angos notes that, "As the number of pieces on the board increases, the probability for *zugzwang* to occur decreases." As such, zugzwang is very rarely seen in the middlegame.

## Sämisch vs. Nimzowitsch
(Main article: Immortal Zugzwang Game)

**Diagram 14** — FEN `7k/4q2p/1p2bp2/4p1r1/2p1Pp2/4bQ1P/1PP1B1rB/2N2R1R w - - 0 1`  (reconstructed; may be a partial/illustrative position)

```
8  . . . . . . . k
7  . . . . q . . p
6  . p . . b p . .
5  . . . . p . r .
4  . . p . P p . .
3  . . . . b Q . P
2  . P P . B . r B
1  . . N . . R . R
   a b c d e f g h
```

The game Fritz Sämisch–Aron Nimzowitsch, Copenhagen 1923, is often called the "Immortal Zugzwang Game". According to Nimzowitsch, writing in the *Wiener Schachzeitung* in 1925, this term originated in "Danish chess circles". It ended with White resigning in the position in the diagram.

White has a few pawn moves which do not lose material, but eventually he will have to move one of his pieces. If he plays 1.Rc1 or Rd1, then 1...Re2 traps White's queen; 1.Kh2 fails to 1...R5f3, also trapping the queen, since White cannot play 2.Bxf3 because the bishop is pinned to the king; 1.g4 runs into 1...R5f3 2.Bxf3 Rh2 mate. Angos analyzes 1.a3 a5 2.axb4 axb4 3.h4 Kh8 (waiting) 4.b3 Kg8 and White has run out of waiting moves and must lose material. Best in this line is 5.Nc3 bxc3 6.Bxc3, which just leaves Black with a serious positional advantage and an extra pawn. Other moves lose material in more obvious ways.

However, since Black would win even without the zugzwang, it is debatable whether the position is true zugzwang. Even if White could pass his move he would still lose, albeit more slowly, after 1...R5f3 2.Bxf3 Rxf3, trapping the queen and thus winning queen and bishop for two rooks. Wolfgang Heidenfeld thus considers it a misnomer to call this a true zugzwang position. See also .

## Steinitz vs. Lasker

**Diagram 15** — FEN `7r/2kp4/2pb4/1p2q1PB/1P1pP3/3P4/4Q3/6R1 w - - 0 1`  (reconstructed; may be a partial/illustrative position)

```
8  . . . . . . . r
7  . . k p . . . .
6  . . p b . . . .
5  . p . . q . P B
4  . P . p P . . .
3  . . . P . . . .
2  . . . . Q . . .
1  . . . . . . R .
   a b c d e f g h
```

This game between Wilhelm Steinitz and Emanuel Lasker in the 1896–97 World Chess Championship, is an early example of zugzwang in the middlegame. After Lasker's 34...Re8–g8!, Steinitz had no  moves, and resigned. White's bishop cannot move because that would allow the crushing ...Rg2+. The queen cannot move without abandoning either its defense of the bishop on g5 or of the g2 square, where it is preventing ...Qg2#. Attempting to push the f-pawn to promotion with 35.f6 loses the bishop: 35...Rxg5 36. f7 Rg2+, forcing mate. The move 35.Kg1 allows 35...Qh1+ 36.Kf2 Qg2+ followed by capturing the bishop. The rook cannot leave the first , as that would allow 35...Qh1#. Rook moves along the first rank other than 35.Rg1 allow 35...Qxf5, when 36.Bxh4 is impossible because of 36...Rg2+; for example, 35.Rd1 Qxf5 36.d5 Bd7, winning. That leaves only 35.Rg1, when Black wins with 35...Rxg5! 36.Qxg5 (36.Rxg5? Qh1#) Qd6+ 37.Rg3 hxg3+ 38.Qxg3 Be8 39.h4 Qxg3+ 40.Kxg3 b5! 41.axb5 a4! and Black queens first.

## Podgaets vs. Dvoretsky
{|align="right" border="0" cellpadding="1" cellspacing="0"
|-valign="top"
|+ Podgaets vs. Dvoretsky, USSR 1974
|

**Diagram 16** — FEN `6r1/1p5k/1Pp1p2p/3pP3/7n/8/2PP2PQ/6RK w - - 0 1`

```
8  . . . . . . r .
7  . p . . . . . k
6  . P p . p . . p
5  . . . p P . . .
4  . . . . . . . n
3  . . . . . . . .
2  . . P P . . P Q
1  . . . . . . R K
   a b c d e f g h
```

**Diagram 17** — FEN `8/1p6/1Pp1p2p/3pP3/3P3n/6r1/2P3PQ/6RK w - - 0 1`  (reconstructed; may be a partial/illustrative position)

```
8  . . . . . . . .
7  . p . . . . . .
6  . P p . p . . p
5  . . . p P . . .
4  . . . P . . . n
3  . . . . . . r .
2  . . P . . . P Q
1  . . . . . . R K
   a b c d e f g h
```

|}

Soltis writes that his "candidate for the ideal zugzwang game" is the following game , Podgaets–Dvoretsky, USSR 1974: **1. d4 c5 2. d5 e5 3. e4 d6 4. Nc3 Be7 5. Nf3 Bg4 6. h3 Bxf3 7. Qxf3 Bg5! 8. Bb5+ Kf8!** Black exchanges off his , but does not allow White to do the same. **9. Bxg5 Qxg5 10. h4 Qe7 11. Be2 h5 12. a4 g6 13. g3 Kg7 14. 0-0 Nh6 15. Nd1 Nd7 16. Ne3 Rhf8 17. a5 f5 18. exf5 e4! 19. Qg2 Nxf5 20. Nxf5+ Rxf5 21. a6 b6 22. g4? hxg4 23. Bxg4 Rf4 24. Rae1 Ne5! 25. Rxe4 Rxe4 26. Qxe4 Qxh4 27. Bf3 Rf8!! 28. Bh1** If instead 28.Qxh4 then 28...Nxf3+ followed by 29...Nxh4 leaves Black a piece ahead. **28... Ng4 29. Qg2** (first diagram) **Rf3!! 30. c4 Kh6!!** (second diagram) Now all of White's piece moves allow checkmate or ...Rxf2 with a crushing attack (e.g. 31.Qxf3 Qh2#; 31.Rb1 Rxf2 32.Qxg4 Qh2#). That leaves only moves of White's b-pawn, which Black can ignore, e.g. 31.b3 Kg7 32.b4 Kh6 33.bxc5 bxc5 and White has run out of moves. *'*'

## Fischer vs. Rossetto

**Diagram 18** — FEN `3r2n1/2RP3k/1p5p/5pp1/8/2B3P1/1P5P/7K w - - 0 1`

```
8  . . . r . . n .
7  . . R P . . . k
6  . p . . . . . p
5  . . . . . p p .
4  . . . . . . . .
3  . . B . . . P .
2  . P . . . . . P
1  . . . . . . . K
   a b c d e f g h
```

In this 1959 game between future World Champion Bobby Fischer and Héctor Rossetto, 33.Bb3! puts Black in zugzwang.   If Black moves the king, White plays Rb8, winning a piece (...Rxc7 Rxf8); if Black moves the rook, 33...Ra8 or Re8, then not only does White gain a queen with 34.c8=Q+, but the black rook will also be lost after 35.Qxa8, 35.Qxe8 or 35.Rxe7+ (depending on Black's move); if Black moves the knight, Be6 will win Black's rook. That leaves only pawn moves, and they quickly run out. The game concluded:
: **33... a5**
: **34. a4 h6**
: **35. h3 g5**
: **36. g4 fxg4**
: **37. hxg4 1–0**

## Zugzwang Lite

**Diagram 19** — FEN `2rbqk1n/4pppb/3n3p/2p5/2P5/3N3P/4PPPB/2RBQK1N w - - 0 1`

```
8  . . r b q k . n
7  . . . . p p p b
6  . . . n . . . p
5  . . p . . . . .
4  . . P . . . . .
3  . . . N . . . P
2  . . . . P P P B
1  . . R B Q K . N
   a b c d e f g h
```

Jonathan Rowson coined the term *Zugzwang Lite* to describe a situation, sometimes arising in symmetrical opening variations, where White's "extra move" is a burden. He cites as an example of this phenomenon in Hodgson versus Arkell at Newcastle 2001. The position diagrammed arose after **1. c4 c5 2. g3 g6 3. Bg2 Bg7 4. Nc3 Nc6 5. a3 a6 6. Rb1 Rb8 7. b4 cxb4 8. axb4 b5 9. cxb5 axb5** (see diagram). Here Rowson remarks, <blockquote>Both sides want to push their d-pawn and play Bf4/...Bf5, but White has to go first so Black gets to play ...d5 before White can play d4. This doesn't matter much, but it already points to the challenge that White faces here; his most natural continuations allow Black to play the moves he wants to. I would therefore say that White is in 'Zugzwang Lite' and that he remains in this state for several moves.</blockquote> The game continued **10. Nf3 d5 11. d4 Nf6 12. Bf4 Rb6 13. 0-0 Bf5 14. Rb3 0-0 15. Ne5 Ne4 16. h3 h5!? 17. Kh2**. The position is still almost symmetrical, and White can find nothing useful to do with his extra move. Rowson whimsically suggests 17.h4!?, forcing Black to be the one to break the symmetry. **17... Re8!** Rowson notes that this is a useful waiting move, covering e7, which needs protection in some lines, and possibly supporting an eventual ...e5 (as Black in fact played on his 22nd move). White cannot copy it, since after 18.Re1? Nxf2 Black would win a pawn. After **18. Be3 Nxe5! 19. dxe5 Rc6!** Black seized the initiative and went on to win in 14 more moves.

**Diagram 20** — FEN `2r1q1rk/4bppb/3np1np/2p5/2P5/3NP1NP/4BPPB/2R1Q1RK w - - 0 1`

```
8  . . r . q . r k
7  . . . . b p p b
6  . . . n p . n p
5  . . p . . . . .
4  . . P . . . . .
3  . . . N P . N P
2  . . . . B P P B
1  . . R . Q . R K
   a b c d e f g h
```

Another instance of Zugzwang Lite occurred in Lajos Portisch–Mikhail Tal, Candidates Match 1965, again from the Symmetrical Variation of the English Opening, after **1. Nf3 c5 2. c4 Nc6 3. Nc3 Nf6 4. g3 g6 5. Bg2 Bg7 6. 0-0 0-0 7. d3 a6 8. a3 Rb8 9. Rb1 b5 10. cxb5 axb5 11. b4 cxb4 12. axb4 d6 13. Bd2 Bd7** (see diagram). Soltis wrote, "It's ridiculous to think Black's position is better. But Mikhail Tal said it is easier to play. By moving second he gets to see White's move and then decide whether to match it." **14. Qc1** Here, Soltis wrote that Black could maintain equality by keeping the symmetry: 14...Qc8 15.Bh6 Bh3. Instead, he plays to prove that White's queen is misplaced by breaking the symmetry. **14... Rc8! 15. Bh6 Nd4!** Threatening 15...Nxe2+. **16. Nxd4 Bxh6 17. Qxh6 Rxc3 18. Qd2 Qc7 19. Rfc1 Rc8** Although the pawn structure is still symmetrical, Black's control of the c- gives him the advantage.

## Zugzwang required to win
Soltis listed some endgames in which zugzwang is required to win:
* King and rook versus king
* King and two bishops versus king
* King, bishop, and knight versus king
* Queen versus rook
* Queen versus knight
* Queen versus two bishops
* Queen versus two knights.
Positions where the stronger side can win in the ending of king and pawn versus king also generally require zugzwang to win.

## See also
* Black swan theory
* Corresponding squares
* Decision theory
* 
* Key square
* Null-move heuristic
* Opposition — a special type of zugzwang 
* Seki – a situation in Go where neither player can add a stone without disadvantage

## Notes
## References
**Bibliography**

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
* 
* 
* 

## Further reading
* 
* 

## External links
* [http://www.chessgames.com/perl/chessgame?gid=1094915 Levitsky vs. Frank James Marshall 1912]

Category:Chess terminology
Category:Chess tactics
Category:Chess theory
Category:Game theory
Category:German words and phrases
Category:Dilemmas
Category:Combinatorial game theory