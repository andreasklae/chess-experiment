# Passed pawns & promotion technique — source notes (read-and-note, 2026-07-02)

Read for the passed-pawns / rook-endings wiki pages. Distilled by the tutor
(Claude) from the sources below; every claim in the wiki pages traces here.

## Wikipedia — "Passed pawn" (en.wikipedia.org/wiki/Passed_pawn)
- Definition: no opposing pawns prevent advancing to the 8th (own file + adjacent files).
- Only PIECES can stop a passer; far-advanced passer/pawn group value ≈ a piece or more.
- Protected passer (defended by own pawn) and connected passers ("steamroller") are
  strongest; connected passers should advance ABREAST (same rank) — harder to blockade.
- Outside passer: decoys the defending king away from the main theatre; its job is
  often NOT to promote but to win the other wing.
- Knights are awkward blockaders of ROOK pawns specifically; generally the blockade
  is the standard anti-passer plan (Nimzowitsch: "a criminal … under lock and key").
- Tarrasch rule referenced: rook behind the pawn (attacking or defending).

## Wikipedia — "Rook and pawn versus rook endgame"
- Tarrasch rule: rook BEHIND the passer is the ideal attacking setup (scope grows as
  the pawn advances; supports the push; shields from checks).
- Lucena: attacking king on the promotion square, cut off by file → rook to the 4th
  rank, king steps out, interpose the rook against lateral checks ("the bridge") → win.
- Philidor: defending rook on its 3rd rank stops the king; when the pawn hits its 6th,
  swing to the back rank and check from behind → draw.
- Cutting off the defending king by file decides: if the defending king can reach the
  queening square → draw; otherwise generally winning, EXCEPT rook pawns (a/h) which
  draw far more often. Short-side defense: rook needs 3-4 files of checking distance.

## Wikipedia — "Wrong rook pawn"
- Bishop + rook pawn whose promotion corner the bishop does NOT control = fortress
  draw if the defending king reaches the corner. Practical rule: keep a second pawn,
  or race the king accordingly. Knight also struggles to contain rook pawns
  (Fischer–Taimanov 1971 example).

## Own-game evidence (2026-07-02)
- Game 9eddc039 (K+N+P vs K): 15 consecutive knight checks/shuffles instead of the
  e-pawn march; halfmove clock climbing toward the 50-move rule. The priority header
  said "CONSOLIDATE — trade pieces"; nothing said "PROMOTE".
- Puzzle mining: 141 games scanned → 22 real positions (passers on ranks 2-6, all
  Stockfish-graded winning ≥ +250cp) where the agent neither pushed the passer nor
  brought the king closer for 3+ consecutive moves.
