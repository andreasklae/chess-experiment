# Positional concepts — weaknesses, strengths, potentials, and how to handle them

Consolidated from Wikipedia *Pawn structure*, *Glossary of chess*, *Chess
strategy*, *Chess opening* (fetched 2026-06-24) and cross-checked against
[[capablanca-positional-extract]]. This is the raw source for the wiki's
positional-understanding pages and for the tool detectors. Organised as: **the
feature → how to detect it mechanically → who it favours → what the side WITH it
does → what the side AGAINST it does.** "Detect mechanically" notes are written
for whoever builds the tools.

General rule (Wikipedia, echoing Capablanca): **structural pawn weaknesses
(isolated, doubled, backward, holes) are usually PERMANENT once created.** A
weakness only matters if it can be attacked; a strength only matters if it can
be used.

---

## PAWN WEAKNESSES

### Isolated pawn (isolani)
- **Detect:** a pawn with no friendly pawn on either adjacent file.
- **Weak because:** no pawn can ever defend it; the square in front is a hole
  the enemy can blockade with a piece. Fixed target.
- **Has it:** use the open/half-open files beside it for active piece play and
  attack; the isolated *queen* pawn (IQP, e.g. White pawn on d4) gives space
  (e5/c5 outposts) and attacking chances — play for the middlegame, avoid mass
  trades.
- **Against it:** blockade the square in front (a knight is ideal), then **trade
  pieces** — the fewer pieces, the more the static weakness tells; win it in the
  endgame.

### Doubled pawns
- **Detect:** two friendly pawns on the same file.
- **Weak because:** they can't defend each other, the front one can't be
  defended by a pawn, reduced mobility, often create an open file for the enemy.
- **Has it:** seek piece activity/counterplay; doubled pawns can grant a
  half-open file for your own rook and extra centre control — use those.
- **Against it:** attack them, fix them, simplify; exploit in the endgame.

### Backward pawn
- **Detect:** a pawn behind its neighbours on adjacent files, whose advance
  square is controlled by an enemy pawn so it can't safely advance and no
  friendly pawn can support it — especially on a half-open file.
- **Weak because:** permanent target down the (half-)open file; the square in
  front is a hole.
- **Has it:** defend with pieces, seek a freeing break or counterplay elsewhere.
- **Against it:** control its advance square, pile pieces on it down the file.

### Holes / weak squares
- **Detect:** a square that can no longer be controlled by any friendly pawn
  (the pawns that would guard it have advanced or been traded), usually in your
  half. A hole on the 3rd–5th rank near the king is most dangerous.
- **Weak because:** an enemy piece (knight) planted there cannot be kicked by a
  pawn and dominates.
- **Has it:** avoid creating them; if one exists, cover it with pieces / trade
  off the piece that occupies it.
- **Against it:** occupy it with a knight (an **outpost** — see strengths).

### Hanging pawns
- **Detect:** two friendly pawns side by side (classically c+d) on a half-open
  file each, with no friendly pawns on the files beside them.
- **Weak because:** can be attacked frontally; if forced to advance, one becomes
  weak/the square in front becomes a hole.
- **Has it:** they control four key central squares and grant piece activity —
  use the space and the attack before they're forced forward.
- **Against it:** pressure them frontally to provoke an advance, then blockade
  and exploit; simplify.

### Pawn islands
- **Detect:** count groups of connected pawns separated by empty files. Fewer
  islands = healthier structure.
- **Rule:** more islands = more potential targets and worse coordination.

---

## PAWN STRENGTHS

### Passed pawn
- **Detect:** a pawn with no enemy pawn on its file OR the two adjacent files
  ahead of it.
- **Strong because:** nothing can stop it with pawns; it can promote.
  Capablanca: a passed pawn is *very weak or very strong*, and **grows stronger
  as it advances and as pieces leave the board.** A protected/connected passer
  is stronger; an **outside** passer (far from the kings) is a decisive endgame
  asset — it decoys the enemy king.
- **Has it:** advance it, support it from behind with a rook, blockade-proof it;
  in the endgame push it / use it to tie down the enemy.
- **Against it:** **blockade the square in front (knight ideal)**, or win it; the
  blockading piece both stops the pawn and is safe there.

### Connected pawns / pawn majority
- **Detect:** friendly pawns on adjacent files (mutually supporting); a majority
  = more pawns than the enemy on one wing (can manufacture a passed pawn).
- **Strong because:** they defend each other and advance as a phalanx.
  Capablanca: **pawns are strongest side by side on the same rank.**
- **Has it:** keep them connected, advance as a unit, convert a majority into a
  passed pawn ("the candidate is the one with no enemy pawn in front").
- **Against it:** blockade, provoke a weakening advance, trade into a structure
  where the majority can't produce a passer.

### Pawn chain
- **Detect:** pawns on a diagonal each defending the one ahead; identify the
  **base** (rearmost, undefended by a pawn) and the **head** (most advanced).
- **Plan:** attack the **base** of the chain (it's the root weakness); the side
  with more space behind the chain attacks on the side its chain points toward.

---

## PIECE STRENGTHS (activity)

### Open file / half-open file
- **Detect:** open = no pawns of either colour on the file; half-open (for you) =
  no friendly pawns but enemy pawns present.
- **Use:** put a **rook** on it; **double rooks** (or rook + queen) to dominate;
  a half-open file aims your rook at the enemy pawn on it (often a backward pawn).
- **Potential:** "your rook can move to an open file" — name the move that does
  it. Contesting the only open file is itself a plan.

### Outpost
- **Detect:** a square (usually rank 4–6 in enemy territory) that no enemy pawn
  can attack, ideally defendable by a friendly pawn.
- **Use:** plant a **knight** there (a knight on a strong outpost is often worth
  more than a bishop); it can't be challenged by a pawn.

### Good bishop vs bad bishop
- **Detect:** a bishop is "bad" when many of its OWN pawns sit on its colour
  (they block it); "good" when its pawns are on the opposite colour.
- **Use:** keep your pawns off your bishop's colour; trade off your bad bishop;
  fix the enemy's pawns on the colour of their remaining bishop to make it bad.

### Bishop pair
- **Detect:** you have both bishops, opponent does not.
- **Strong because:** two bishops cover both colour complexes; worth ~half a
  pawn, more in **open** positions.
- **Use:** open the position (open lines/diagonals) to maximise them; the side
  without the pair keeps the position closed and seeks a knight outpost.

### Color complex / fianchetto
- **Detect:** one side controls many squares of one colour (often because the
  enemy's bishop of that colour is gone or bad).
- **Use:** route pieces and pawns onto the colour you dominate; a fianchettoed
  bishop (g2/b2) is the guardian of its long diagonal and of the castled king —
  trading it off weakens that colour complex badly.

### Space advantage
- **Detect:** you control more squares (pawns further advanced) — count space
  behind your pawn line.
- **Use:** space restricts the enemy's pieces; **avoid trades** (the cramped side
  wants to trade to get room); manoeuvre and switch wings (Capablanca's greater
  mobility → attack both sides).
- **Against (cramped):** **trade pieces** to relieve the cramp; strike at the
  pawn chain to open lines.

---

## KING SAFETY (the dominant weakness)
- **Detect:** uncastled king; king with no pawn shield (pawns in front advanced
  or missing); open file/diagonal pointing at the king; enemy heavy pieces near.
- **Has the weakness:** **castle early**; keep the pawn shield intact; give the
  king luft (a flight square) against back-rank mates; if it's stuck in the
  centre, finish development and get it to safety before opening lines.
- **Against:** open lines toward the enemy king, aim pieces at it, don't trade
  the attackers; Capablanca: no king attack works without central control first.

---

## MATERIAL & TRADING (heuristics — advice, not hard facts)
- **Up material → trade pieces (not pawns)** to simplify toward a won endgame;
  every trade magnifies a material edge.
- **Down material → avoid trades**, keep pieces on, seek complications/counterplay.
- **Capablanca:** the rook's power grows and the knight's shrinks as pieces come
  off. Practical rule for THIS agent (strong at K+Q and K+R mates): **even when
  slightly ahead, prefer to keep at least one rook or the queen** rather than
  trade into a piece endgame — keep the mating material.
- A passed pawn is worth more the closer it is to queening and the fewer pieces
  remain.

---

## TACTICAL MOTIFS (potentials to detect for BOTH sides)
- **Fork:** one piece attacks two+ enemy pieces at once. *Knight forks* of K+Q,
  K+R, or two pieces are the most common — detect a square a knight can reach
  that hits two valuable pieces (and whether that square is defended).
  Distinguish **currently threatened** (enemy can play it now) from **potential**
  (would be a fork if the piece could get there safely).
- **Pin:** a piece can't move without exposing a more valuable piece behind it
  on the same line. Pile attackers on a pinned piece (it can't run).
- **Skewer:** a valuable piece is attacked along a line and must move, exposing a
  lesser piece behind it.
- **Discovered attack:** moving one piece unveils an attack from a piece behind
  it; a discovered *check* is especially strong (the moving piece can grab
  anything).
- **Battery:** two pieces aligned on a file/rank/diagonal (R+R, Q+R, Q+B) for
  combined pressure or a discovery.
- **Overloaded / overworked piece:** a piece doing two defensive jobs; attack
  one job and it can't hold both (deflection/overload).
- **Loose piece:** an undefended enemy piece — "loose pieces drop off"; it's the
  target that makes forks and double attacks work.

---

## SCENARIO RECIPES — "what to do when X" (the tool's job is to fill in the moves)

These are the decision procedures the tools should instantiate with the actual
legal moves on the board. The wiki page states the procedure; the tool lists
the concrete options.

### Your piece is attacked (and would be lost)
Consider, in this order, and calculate the candidate lines (not just the obvious
recapture):
1. **Capture** the attacker (is the attacker itself takeable, favourably?).
2. **Defend** the piece (add a defender so a capture loses material for them) —
   but only if the piece isn't also pinned/forked.
3. **Move** the piece to a safe square (not attacked, or defended) — watch for
   discovered attacks the move might allow.
4. **Counter-attack:** create a **bigger threat** (a check, or a threat to a more
   valuable piece) so they must respond instead of capturing.
5. A **check** that changes everything (interpose tempo, win the attacker).
> Imagine several lines for each non-losing option, evaluate, pick the safest
> and strongest. Don't bother "threatening" a piece that can just step away for
> free — only threats that win something or force a concession count.

### Your king is in danger (open lines / enemy heavy pieces near)
1. If not castled and able — **castle** (or get the king to safety).
2. **Block** the checking line / give **luft** against back-rank ideas.
3. **Trade off** the enemy's attacking pieces (the attacker wants to keep them).
4. Don't open lines near your own king; don't march the king into the open.

### A pawn is about to promote (yours or theirs)
- Yours: clear its path, escort with the king (in the endgame the KING escorts
  the pawn — an extra piece is not what wins), support from behind with a rook.
- Theirs: **blockade** the square in front with a piece; or win the pawn; in
  rook endings, get your rook **behind** the passed pawn.

### You have an advantage and don't know what to do
- Material up → trade pieces, simplify, keep mating material (R/Q).
- Space → manoeuvre, switch wings, don't trade.
- Better structure → fix the enemy weakness, blockade it, attack it down the
  open file, win it in the endgame.
- Nothing obvious → improve your worst-placed piece; improve king safety.
