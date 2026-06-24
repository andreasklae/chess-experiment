# Chess strategy — Wikipedia (text + inline FEN/ASCII diagrams)

Source: https://en.wikipedia.org/wiki/Chess_strategy
License: text CC BY-SA 4.0 (Wikipedia); position diagrams reconstructed losslessly from the article's {{Chess diagram}} wikitext into FEN+ASCII (verified in python-chess); composed images from Wikimedia Commons (CC/PD). Retrieved 2026-06-24.
Diagrams: 1 positions inlined as FEN+grid; 0 images downloaded.

---

**Chess strategy** is the aspect of chess play concerned with evaluation of chess positions and setting goals and long-term plans for future play. While evaluating a position strategically, a player must take into account such factors as the relative value of the pieces on the board, pawn structure, king safety, position of pieces, and control of key squares and groups of squares (e.g. diagonals and open files). Chess strategy is distinguished from chess tactics, which is the aspect of play concerned with move-by-move threats and defenses. Some authors distinguish static strategic imbalances (e.g. having more valuable pieces or better pawn structure), which tend to persist for many moves, from dynamic imbalances (such as one player having an advantage in piece ), which are temporary. Static imbalances—such as superior pawn structure or the bishop pair—tend to persist and shape long‑term plans, while dynamic imbalances, including a lead in development or active piece placement, often require immediate action before the advantage disappears.

This distinction affects the immediacy with which a sought-after plan should take effect. Until players reach Master-level chess skill, chess tactics tend to ultimately decide the outcomes of games more often than strategy. Many chess coaches thus emphasize the study of tactics as the most efficient way to improve one's results in serious chess play.

The most basic way to evaluate one's position is to count the total value of pieces on both sides. The point values used for this purpose are based on experience. Usually pawns are considered to be worth one point, knights and bishops three points each, rooks five points, and queens nine points. The fighting value of the king in the endgame is approximately four points. These basic values are modified by other factors such as the  (e.g. advanced pawns are usually more valuable than those on their starting squares),  (e.g. a  usually coordinates better than a bishop plus a knight), and the  (knights are generally better in  with many pawns, while bishops are more powerful in ).

Another important factor in the evaluation of chess positions is the pawn structure or pawn skeleton. Since pawns are the most immobile and least valuable of the pieces, the pawn structure is relatively static and largely determines the strategic nature of the position. Weaknesses in the pawn structure, such as isolated, doubled, or backward pawns and , once created, are usually permanent. Care must therefore be taken to avoid them unless they are compensated by another valuable asset, such as the possibility to develop an attack.

## Basic concepts of board evaluation
(Main article: Chess piece relative value)

A  advantage applies both strategically and tactically. Generally more pieces or an aggregate of more powerful pieces means greater chances of winning. A fundamental strategic and tactical rule is to capture opponent pieces while preserving one's own.

Bishops and knights are called *minor pieces*. A knight is about as valuable as a bishop, but less valuable than a rook. Rooks and the queen are called *major pieces*. Bishops are usually considered slightly better than knights in open positions, such as toward the end of the game when many of the pieces have been captured, whereas knights have an advantage in closed positions. Having two bishops (the ) is a particularly powerful weapon, especially if the opposing player lacks one or both of their bishops.

Three pawns are likely to be more useful than a knight in the endgame, but in the middlegame, a knight is often more powerful. Two minor pieces are stronger than a single rook, and two rooks are slightly stronger than a queen. The bishop on squares of the same color as the opponent's king is slightly more valuable in the opening as it can attack the vulnerable square f7 (for White) or f2 (for Black). A rook is more valuable when  with another rook or queen; consequently, doubled rooks are worth more than two .

One commonly used simple scoring system is:
:{| class="wikitable"
! Piece !! Value
|-
| Pawn || align="center" | 1
|-
| Knight || align="center" | 3
|-
| Bishop || align="center" | 3
|-
| Rook || align="center" | 5
|-
| Queen || align="center" | 9
|}

Under a system like this, giving up a knight or bishop to win a rook ("winning the exchange") is advantageous and is worth about two pawns. This ignores complications such as the current position and freedom of the pieces involved, but it is a good starting point. In an open position, bishops are more valuable than knights (a bishop pair can easily be worth seven points or more in some situations); conversely, in a closed position, bishops are less valuable than knights. A knight in the center of the board that cannot be taken, however, is known as a knight outpost and threatens several fork instances. In such a case, a knight is worth far more than a bishop. Also, many pieces have a partner. By doubling up two knights, two rooks, rook and queen, or bishop and queen, the pieces can get stronger than the sum of the individual pieces alone. When a piece loses its partner, its value slightly decreases. The king is priceless since its capture results in the defeat of that player and ends that game. However, especially in the endgame, the king can also be a fighting piece, and is sometimes given a fighting value of three-and-a-half points.

## Space
Other things being equal, the side that controls more  on the board has an advantage. More space means more options, which can be exploited both tactically and strategically. A player who has all pieces developed and no tactical tricks or promising long-term plan should try to find a move that enlarges their influence, particularly in the center. In some openings, however, one player accepts less space for a time, to set up a counterattack in the middlegame. This is one of the concepts behind hypermodern play.

The easiest way to gain space is to push the pawn skeleton forward. One must be careful not to over stretch, however. If the opponent succeeds in getting a protected piece behind enemy lines, this piece can become such a serious problem that a piece with a higher value might have to be exchanged for it.

**Diagram 1** — FEN `1r2q1rk/1pbpnbpp/2p1p1n1/4Pp2/3P1P2/1P1N3P/2P2NPB/1R1BQ1RK w - - 0 1`

```
8  . r . . q . r k
7  . p b p n b p p
6  . . p . p . n .
5  . . . . P p . .
4  . . . P . P . .
3  . P . N . . . P
2  . . P . . N P B
1  . R . B Q . R K
   a b c d e f g h
```

Larry Evans gives a method of evaluating space. The method (for each side) is to count the number of squares attacked or occupied on the opponent's side of the board. In this diagram from the Nimzo-Indian Defense, Black attacks four squares on White's side of the board (d4, e4, f4, and g4). White attacks seven squares on Black's side of the board (b5, c6, e6, f5, g5, and h6 – counting b5 twice) and occupies one square (d5). White has a space advantage of eight to four and Black is cramped.

Overextending the pawn structure can create long‑term weaknesses, especially if advanced pawns cannot be adequately supported by pieces. Many strategic errors arise when a player gains space but leaves behind weak squares or targets that the opponent can later exploit.

## Control of the center

The strategy consists of placing pieces so that they attack the central four squares of the board. A piece being placed on a central square, however, does not necessarily mean it controls the center; e.g., a knight on a central square does not attack any central squares. Conversely, a piece does not have to be on a central square to control the center. For example, the bishop can control the center from afar.

Control of the center is generally considered important because tactical battles often take place around the central squares, from where pieces can access most of the board. Center control allows more movement and more possibility for attack and defense.

Chess openings try to control the center while developing pieces. Hypermodern openings are those that control the center with pieces from afar (usually the side, such as with a fianchetto); the older Classical (or Modern) openings control it with pawns.

## Initiative
(Main article: Initiative (chess))

The initiative belongs to the player who can make threats that cannot be ignored, such as checking the opponent's king. They thus put their opponent in the position of having to use their turns responding to threats rather than making their own, hindering the development of their pieces. The player with the initiative is generally attacking and the other player is generally defending.

## Defending pieces
It is important to defend one's pieces even if they are not directly threatened. This helps stop possible future campaigns from the opponent. If a defender must be added at a later time, this may cost a tempo or even be impossible due to a fork or discovered attack. The approach of always defending one's pieces has an antecedent in the theory of Aron Nimzowitsch who referred to it as "overprotection." Similarly, if one spots undefended enemy pieces, one should immediately take advantage of those pieces' weakness.

Even a defended piece can be vulnerable. If the defending piece is also defending something else, it is called an overworked piece, and may not be able to fulfill its task. When there is more than one attacking piece, the number of defenders must also be increased, and their values taken into account. In addition to defending pieces, it is also often necessary to defend key squares, open files, and the . These situations can easily occur if the pawn structure is weak.

## Exchanging pieces
(Main article: Exchange (chess))

To exchange pieces means to capture a hostile piece and then allow a piece of the same value to be captured. As a rule of thumb, exchanging pieces eases the task of the defender who typically has less room to operate in.

Exchanging pieces is usually desirable to a player with an existing advantage in material, since it brings the endgame closer and thereby leaves the opponent with less ability to recover ground. In the endgame even a single pawn advantage may be decisive. Exchanging also benefits the player who is being attacked, the player who controls less space, and the player with the better pawn structure.

When playing against stronger players, many beginners attempt to constantly exchange pieces "to simplify matters". However, stronger players are often relatively stronger in the endgame, whereas errors are more common during the more complicated middlegame.

Note that "the exchange" may also specifically mean a rook exchanged for a bishop or knight. The phrase "up the exchange" means that a player has captured a rook in exchange for a bishop or knight—a materially advantageous trade. Conversely, "down the exchange" means having lost a rook but captured a bishop or knight—a materially disadvantageous trade.

## Specific pieces
## Pawns
(Main article: Pawn (chess)|l1 = Pawn|Pawn structure)

{| class="toccolours" style="float: right; margin: 0 0 1em 1em; border:none; font-size: 95%; clear: right; padding:0"
|+ An example of visualizing pawn structures
|-
|

|

|}
In the endgame, passed pawns, unhindered by enemy pawns from promotion, are strong, especially if advanced or protected by another pawn. A passed pawn on the sixth  is roughly as strong as a knight or bishop and often decides the game. (Also see isolated pawn, doubled pawns, backward pawn, connected pawns.)

## Knights
(Main article: Knight (chess)|l1 = Knight)

Since knights can easily be chased away by pawn moves, it is often advantageous for knights to be placed in '''' in the enemy position as outposts—squares where they cannot be attacked by pawns. Such a knight on the fifth rank is a strong asset. The ideal position for a knight is the opponent's third rank, when it is supported by one or two pawns. A knight at the edge or corner of the board controls fewer squares than one on the board's interior, thus the saying "A knight on the rim is dim!"

A king and one knight are not sufficient material to checkmate an opposing lone king (see Two knights endgame). A king and two knights can checkmate a lone king but cannot force it.

## Bishops
(Main article: Bishop (chess)|l1 = Bishop)

In general, bishops and knights are of roughly equal value. When bishops are blocked in by pawns, as seen in closed positions, knights are typically superior for their ability to hop over pawn chains. In open positions where bishops have good , knights are often inferior— knights are a common exception.

Bishops have superior mobility to knights, but that mobility is restricted to (and thus focused on) colors of a single square. As a result, lacking a bishop weakens one's ability to exert control over and parry threats from the deprived color complex, though there may be compensation in the form of tactical or positional assets, or from possible countermeasures, such as placing one's pawns on the color of the lost bishop. Bishops complement each other well, and a retained  is often a strength, especially in open positions.

*Fianchettoed* bishops can keep a king under them well defended, though if the bishop is traded off, the fianchetto pawn structure is especially vulnerable to infiltration on the squares no longer controlled by the bishop.

Despite their openness, in endgames, bishops are usually considered equal to knights. Endgames in which the two sides have bishops on opposite colors are frequently drawish, even when one side has one or two more pawns than the other.

A king and a bishop are not sufficient material to checkmate an opposing lone king, but two bishops and a king can checkmate an opposing lone king easily. A king, bishop, and knight can also force mate; this is considered the most difficult forcible checkmate against a lone king.

## Rooks
(Main article: Rook (chess)|l1 = Rook)

Rooks have more scope of movement on half-open files (ones with no pawns of one's own color). Rooks on the seventh rank can be very powerful as they attack pawns that can only be defended by other pieces, and they can restrict the enemy king to its back rank. A pair of rooks on the player's seventh rank are often a sign of a winning position.

In middlegames and endgames with a passed pawn, Tarrasch's rule states that rooks, both friend and foe of the pawn, are usually strongest  the pawn rather than in front of it.

A king and a rook are sufficient material to checkmate an opposing lone king, although it's a little harder than checkmating with king and queen; thus the rook's distinction as a major piece above the knight and bishop.

## Queen
(Main article: Queen (chess)|l1 = Queen)

Queens are the most powerful pieces. They have great mobility and can make many threats at once. They can act as a rook and as a bishop at the same time. For these reasons, checkmate attacks involving a queen are easier to achieve than those without one. Although powerful, the queen is also easily harassed. Thus, it is generally wise to wait to  the queen until after the knights and bishops have been developed to prevent the queen from being attacked by minor pieces and losing tempo. When a pawn is promoted, most of the time it is promoted to a queen.

## King
(Main article: King (chess)|l1 = King)

During the middlegame, the king is often best protected in a corner behind its pawns. Such a position for either of the players is often achieved by castling by that player. If the rooks and queen leave the first rank (commonly called that player's *back rank*), however, an enemy rook or queen can checkmate the king by invading the first rank, commonly called a back-rank checkmate. Moving one of the pawns in front of the king (making a luft) can allow it an escape square, but may weaken the king's overall safety otherwise. One must therefore wisely balance between these trade-offs.

Castling is often thought to help protect the king and often "connects" the player's two rooks together so the two rooks may protect each other. This can reduce a threat of a back-rank skewer in which the king can be skewered with capture of a rook behind it.

The king can become a strong piece in the endgame. With reduced material, a quick checkmate becomes less of a concern, and moving the king towards the center of the board gives it more opportunities to make threats and actively influence play.

## Considerations
Chess strategy consists of setting and achieving long-term goals during the game—for example, where to place different pieces—while tactics concentrate on immediate maneuver. These two parts of chess thinking cannot be completely separated, because strategic goals are mostly achieved by the means of tactics, while the tactical opportunities are based on the previous strategy of play.

Because of different strategic and tactical patterns, a game of chess is usually divided into three distinct phases: the opening, usually the first 10 to 25 moves, when players develop their armies and set up the stage for the coming battle; the middlegame, the developed phase of the game; and the endgame, when most of the pieces are gone and kings start to take an active part in the struggle.

## Opening
(Main article: Chess opening)

A chess opening is the group of initial moves of a game (the "opening moves"). Recognized sequences of opening moves are referred to as *openings* and have been given names such as the Ruy Lopez or Sicilian Defence. They are catalogued in reference works such as the *Encyclopaedia of Chess Openings*.

There are dozens of different openings, varying widely in character from quiet positional play (e.g. the Réti Opening) to very aggressive play (e.g. the Latvian Gambit). In some opening lines, the exact sequence considered best for both sides has been worked out to 30–35 moves or more. Professional players spend years studying openings, and continue doing so throughout their careers, as opening theory continues to evolve.

The fundamental strategic aims of most openings are similar:
**Development:* To place (develop) the pieces (particularly bishops and knights) on useful squares where they influence the game.
**Control of the :* Control of the central squares allows pieces to be moved to any part of the board relatively easily, and can also have a cramping effect on the opponent.
**King safety:* Correct timing of castling can enhance this.
**Pawn structure:* Players strive to avoid the creation of pawn weaknesses such as isolated, doubled or backward pawns, and .

During the opening, some pieces have a recognized optimum square they try to reach. Hence, an optimum deployment could be to push the king and queen pawn two squares, followed by moving the knights so they protect the center pawns and give additional control of the center. One can then deploy the bishops, protected by the knights, to pin the opponent's knights and pawns. An opening may end with  castling, which moves the king to safety, creates a stronger , and puts a rook on a .

Apart from these fundamentals, other strategic plans or tactical sequences may be employed in the opening.

Most players and theoreticians consider that White, by virtue of the first move, begins the game with a small advantage. Black usually strives to neutralize White's advantage and achieve , or to develop   in an unbalanced position.

## Middlegame
(Main article: Chess middlegame)

The middlegame is the part of the game when most pieces have been developed. Because the opening theory has ended, players have to assess the position to form plans based on the features of the positions, and at the same time take into account the tactical possibilities in the position.

Typical plans or strategic themes—for example the , that is the attack of  pawns against an opponent who has more pawns on the queenside—are often appropriate just for some pawn structures, resulting from a specific group of openings. The study of openings should therefore be connected with the preparation of plans typical for resulting middlegames.

The middlegame is also the phase when most combinations occur. Middlegame combinations are often connected with the attack against the opponent's king; some typical patterns have their own names, for example the Boden's Mate or the Lasker–Bauer combination.

Another important strategical question in the middlegame is whether and how to reduce material and transform into an endgame (i.e. ). For example, minor material advantages can generally be transformed into victory only in an endgame, and therefore the stronger side must choose an appropriate way to achieve an ending. Not every reduction of material is good for this purpose; for example, if one side keeps a light-squared bishop and the opponent has a dark-squared one, the transformation into a *bishops and pawns ending* is usually advantageous for the weaker side only, because an endgame with bishops on opposite colors is likely to be a draw, even with an advantage of one or two pawns.

## Endgame
(Main article: Chess endgame)

The endgame (or *end game* or *ending*) is the stage of the game when there are few pieces left on the board. There are three main strategic differences between earlier stages of the game and the endgame:
*During the endgame, pawns become more important; endgames often revolve around attempting to promote a pawn by advancing it to the eighth rank.
*The king, which must be protected in the middlegame owing to the threat of checkmate, becomes a strong piece in the endgame and it is often brought to the center of the board where it can protect its own pawns, attack the pawns of opposite color, and hinder movement of the opponent's king.
*Zugzwang, a disadvantage because the player must make a move, is often a factor in endgames and rarely in other stages of the game. For example, in the adjacent diagram, Black on move must play 1...Kb7 and allow white to  after 2.Kd7, while White on move must allow a draw either after 1.Kc6 stalemate or losing the last pawn by moving anywhere else.

Endgames can be classified according to the type of pieces remaining on the board. Basic checkmates are positions where one side has only a king and the other side has one or two pieces and can checkmate the opposing king, with the pieces working together with their king. For example, king and pawn endgames involve only kings and pawns on one or both sides and the task of the stronger side is to promote one of the pawns. Other more complicated endings are classified according to the pieces on the board other than kings, e.g. "rook and pawn versus rook endgame".

## See also
* Outline of chess: Chess strategy
* Chess tactics
* Chess terminology
* School of chess

## References
**Bibliography**
* 
* 
* Josh Waitzkin (2002). Chessmaster 8000 Classroom

## Further reading
*  A comprehensive guide for beginners.
*  An International Grandmaster explains the thinking behind every single move of many world-class games.
*
*  A chess teacher analyzes and corrects the thinking of advanced beginners.
* 

## External links
* [https://web.archive.org/web/20120116113334/http://www.chessplans.com/ *Chess Plans and Strategy*] Evaluate positions from master chess games, vote for which side has the advantage based on 8 strategic themes, see how your opinion compares to others.
* [https://www.gutenberg.org/ebooks/5614 *Chess Strategy*, Second Edition] and [https://www.gutenberg.org/ebooks/4913 *Chess and Checkers: the Way to Mastership*], both by Edward Lasker
* [https://www.gutenberg.org/ebooks/16377 *The Blue Book of Chess*]; "Teaching the Rudiments of the Game, and Giving an Analysis of All the Recognized Openings" by Howard Staunton