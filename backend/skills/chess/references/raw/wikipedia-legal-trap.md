# Legal Trap — Wikipedia (text + inline FEN/ASCII diagrams)

Source: https://en.wikipedia.org/wiki/Legal_Trap
License: text CC BY-SA 4.0 (Wikipedia); position diagrams reconstructed losslessly from the article's {{Chess diagram}} wikitext into FEN+ASCII (verified in python-chess); composed images from Wikimedia Commons (CC/PD). Retrieved 2026-06-24.
Diagrams: 5 positions inlined as FEN+grid; 0 images downloaded.

---

The **Legal Trap** or **Blackburne Trap** (also known as **Legal Mate**) is a chess opening , characterized by a queen sacrifice followed by checkmate involving three minor pieces if Black accepts the sacrifice. The trap is named after the French player Sire de Legall. Joseph Henry Blackburne, a British master and one of the world's top five players in the latter part of the 19th century, set the trap on many occasions.

## Natural move sequence
There are a number of ways the trap can arise; the one below shows a natural move sequence from a simultaneous exhibition in Paris. André Cheron, one of France's leading players, won with the trap as White against Jeanlose:

**1. e4 e5 2. Nf3 Nc6 3. Bc4 d6** 
:The Semi-Italian Opening.

**4. Nc3 Bg4**
:Black pins the knight in the fight over the center. Strategically this is a sound idea, but there is a tactical flaw with the move.

**5. h3** 
:In this position 5.Nxe5 would be . While the white queen still cannot be taken (5...Bxd1) without succumbing to a checkmate in two moves, 5...Nxe5 would win the white knight (for the pawn) and protect the bishop on g4. Instead, with 5.h3, White "puts the question" to the bishop which must either retreat on the c8–h3 diagonal, capture the knight, be captured, or as in this game, move to an insecure square.

**Diagram 1** — FEN `1r2qkbn/1ppp2pp/3np3/5p2/3B1P2/3N2N1/1PPPP1PP/1R1BQK2 w - - 0 1`

```
8  . r . . q k b n
7  . p p p . . p p
6  . . . n p . . .
5  . . . . . p . .
4  . . . B . P . .
3  . . . N . . N .
2  . P P P P . P P
1  . R . B Q K . .
   a b c d e f g h
```

**5... Bh5** (diagram)
:Black apparently maintains the pin, but this is a tactical mistake which loses at least a pawn (see below). Relatively best is 5...Bxf3 (or 5...Bd7), surrendering the  and giving White a comfortable lead in , but maintaining  equality. 5...Be6 is also possible.

**6. Nxe5**
:The tactical refutation. White seemingly ignores the pin and surrenders the queen. Black's best course now is to play 6...Nxe5, where with 7.Qxh5 Nxc4 8.Qb5+ followed by 9.Qxc4, White remains a pawn ahead, but Black can at least play on. Instead, if Black takes the queen, White has checkmate in two moves:

**6... Bxd1**
: A blunder, winning the queen but losing the game. Black should have played 6...Nxe5 or 6...dxe5 as mentioned in the previous note.

**7. Bxf7+ Ke7 8. Nd5**
:The final position is a pure mate, meaning that for each of the eight squares around the black king, there is exactly one reason the king cannot move there, and exactly one reason why the king cannot remain on its current square.

**Diagram 2** — FEN `1r2q1bn/1ppp1kBp/3np3/4NN2/5P2/8/1PPPP1PP/1R1BbK2 w - - 0 1`

```
8  . r . . q . b n
7  . p p p . k B p
6  . . . n p . . .
5  . . . . N N . .
4  . . . . . P . .
3  . . . . . . . .
2  . P P P P . P P
1  . R . B b K . .
   a b c d e f g h
```

## Legal versus Saint Brie
The original game featured Legal playing at rook odds (without Ra1) against Saint Brie in Paris 1750:

**1. e4 e5 2. Nf3 d6 3. Bc4 Bg4?! 4. Nc3 g6? 5. Nxe5 Bxd1?? 6. Bxf7+ Ke7 7. Nd5# **

:The above version is cited in most publications, sometimes with the move 4... h6 instead of 4... g6. However, research suggests that the  of the game had been altered retrospectively in order to remove a flaw in the original game. Also the year 1750 is assumed to be wrong; it is more likely that the game was played in 1787, and that the original move order was:

**1. e4 e5 2. Bc4 d6 3. Nf3 Nc6 4. Nc3 Bg4 5. Nxe5? Bxd1?? 6. Bxf7+ Ke7 7. Nd5# 1–0**
:Here the combination is flawed, as with 5... Nxe5 Black could have gained a piece. It is reported that Legal disguised his trap with a psychological trick: he first touched the knight on f3 and then retreated his hand as if realizing only now that the knight was pinned. Then, after his opponent reminded him of the touch-move rule, he played Nxe5, and the opponent grabbed the queen without thinking twice.

## Other variations
{| align="left" border="0" cellpadding="1" cellspacing="0"
|-valign="top"
|

**Diagram 3** — FEN `1r2Bk2/1ppp2pp/3p4/8/5n1b/4P3/1PPP1KbP/1RN1Q1B1 w - - 0 1`
*:1.e4 e5 2.Nf3 Nf6 3.Nxe5 Nc6?! 4.Nxc6 dxc6 5.d3 Bc5 6.Bg5? Nxe4 7.Bxd8?? Bxf2+ 8.Ke2 Bg4#*

```
8  . r . . B k . .
7  . p p p . . p p
6  . . . p . . . .
5  . . . . . . . .
4  . . . . . n . b
3  . . . . P . . .
2  . P P P . K b P
1  . R N . Q . B .
   a b c d e f g h
```

|

**Diagram 4** — FEN `1r4k1/1p1p1npp/2b1p1q1/5p2/1B3P1b/3PPBN1/2P3PP/1R2QK2 w - - 0 1`

```
8  . r . . . . k .
7  . p . p . n p p
6  . . b . p . q .
5  . . . . . p . .
4  . B . . . P . b
3  . . . P P B N .
2  . . P . . . P P
1  . R . . Q K . .
   a b c d e f g h
```

|

**Diagram 5** — FEN `1r2qkbn/1ppp2pp/4p3/5n2/3B1P1b/3N2N1/1PP3PP/1R1BQ1RK w - - 0 1`
*:1.e4 e5 2.Nf3 Nc6 3.d4 exd4 4.c3 (the Göring Gambit) dxc3 5.Nxc3 d6 6.Bc4 Bg4 7.0-0 Ne5 8.Nxe5 Bxd1 9.Bxf7+ Ke7 10.Nd5# 1–0*

```
8  . r . . q k b n
7  . p p p . . p p
6  . . . . p . . .
5  . . . . . n . .
4  . . . B . P . b
3  . . . N . . N .
2  . P P . . . P P
1  . R . B Q . R K
   a b c d e f g h
```

|}

## Considerations
A mating pattern where a pinned knight moves, allowing the capture of the player's queen but leading to a checkmate with three minor pieces, occasionally occurs at lower levels of play, though masters would not normally fall for it. According to Bjerke (*Spillet i mitt liv*), the Legal Trap has ensnared countless unwary players. One author writes that "Blackburne sprang it several hundreds of times during his annual tours."

## See also
* Checkmate pattern
* Elephant Trap

## References
**Bibliography**
*
*

## External links
* [http://www.chessgames.com/perl/chessgame?gid=1251892 Kermur Sire De Legal vs Saint Brie, Paris, 1750] at Chessgames.com

Category:Chess traps
Category:Chess checkmates
Category:18th century in chess