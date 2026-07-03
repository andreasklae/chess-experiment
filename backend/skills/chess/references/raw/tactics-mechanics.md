# Tactical motifs — deep mechanics and soundness conditions

Consolidated from Wikipedia (*Chess tactic*, *Discovered attack*, *Deflection*,
*Decoy*, *Windmill*, *List of chess traps*, *Légal Trap*), the Lichess Practice
curriculum (CC-licensed, freely reusable), and public-domain tactical taxonomies
(chessfox 56-pattern list, chessworld glossary). All facts/mechanics are
non-copyrightable and synthesised here in our own words; concrete example lines
are verified in python-chess before they go into a wiki page.

The unifying principle behind almost every tactic (Wikipedia): **create two
threats the opponent cannot meet with a single move.** The *soundness test* for
any tactic is therefore always the same question — **can the opponent address
both threats in one move?** If yes, the tactic fails; if no, it wins.

---

## Fork / double attack
- **Mechanic:** one piece attacks two+ targets at once. Knight forks (K+Q, K+R,
  two pieces) are deadliest — a knight can't be blocked and hits in two
  directions.
- **Soundness:** wins unless (a) a target can capture the forking piece, (b) a
  target can move *with tempo* (check/bigger threat) saving both, or (c) one
  "target" is defended and not worth winning. A fork that also gives **check**
  is near-always sound (the checked side can't use its move to save the other
  piece).

## Pin
- **Mechanic:** a piece can't (absolute: illegally; relative: at material cost)
  move because a more valuable piece sits behind it on a rook/bishop/queen line.
- **Exploitation:** the pinned piece is **paralysed** — (1) **pile more
  attackers on it** (it can't run), often a pawn; (2) it can't perform its
  defensive job, so whatever it "defends" is effectively **undefended** — attack
  that instead.
- **Soundness:** a *relative* pin can be broken (the pinned piece may legally
  move with a counter-threat/check) — verify it can't wriggle with tempo.

## Skewer
- **Mechanic:** the reverse of a pin — the **more** valuable piece is in front,
  attacked; when it moves, the lesser piece behind falls.
- **Soundness:** fails if the front piece can move *and* defend the rear piece,
  or interpose, in one move.

## Discovered attack & discovered check (the key one)
- **Mechanic:** moving a front piece off a line unveils an attack from a
  rook/bishop/queen behind it. You get **two independent threats at once**: the
  moving piece does its own thing, the unveiled piece attacks something else.
- **Discovered CHECK = free capture engine:** if the unveiled line gives check,
  the opponent MUST answer the check first — so the **moving piece is free to
  capture almost anything** (the most valuable loose enemy piece), and they
  can't recapture because they're busy with the check. State this to the agent
  explicitly: *"your knight sits between your rook and the enemy king; moving the
  knight discovers check, so the knight can capture any piece and it's free —
  provided the opponent can't both answer the check and save that piece in one
  move."*
- **Double check:** both the moving piece and the unveiled piece give check →
  the king **must move**, nothing else (no block, no capture) can answer two
  checks at once. Devastating, often the engine of a mate.
- **Soundness (when it FAILS — verbatim conditions):** the discovery fails iff
  the opponent can, in ONE move, do both jobs:
  1. **block the check with a piece that also defends** the attacked piece, or
  2. have the **attacked piece capture the checking (unveiled) piece** / block
     the check itself, or
  3. **capture the moving piece** (so its threat never lands), or the king
     simply captures it.
  The tactic wins only when **none** of these single-move escapes exists. Always
  run this check before playing a discovery.

## Windmill (see-saw)
- **Mechanic:** alternating **direct check** (usually a rook on the 7th/2nd) and
  **discovered check** (from a bishop on the long diagonal), repeated. Because the
  opponent must answer check every move, the rook can swing back and forth
  **capturing a piece each cycle for free**. Classic: Torre–Lasker 1925 (queen
  sac → windmill → wins three pawns + the queen back).
- **Setup conditions:** a bishop fixing a discovered-check line + a rook that
  shuttles between giving direct check and stepping aside for the discovery, with
  the enemy king boxed so it returns to the same square each cycle.

## Zwischenzug (in-between move)
- **Mechanic:** instead of the "expected" recapture/response, insert a MORE
  forcing move first (usually a check or a bigger threat); after the opponent
  answers it, *then* make the original move — having gained material or tempo.
- **Soundness:** the in-between move must be more forcing than the threat you're
  ignoring (typically a check, or a threat to something more valuable). If the
  opponent can ignore your zwischenzug, it doesn't work.

## Removing the defender (umbrella) — and its forms
The target is protected by one defender; eliminate or neutralise it. Forms:
- **Capture the defender** (simplest — if you can take it favourably).
- **Deflection:** force the defender AWAY from its job by a more urgent threat
  (often a check or a capture it must answer). Then the thing it guarded is free.
- **Decoy (attraction):** LURE a piece TO a specific bad square (usually via a
  sacrifice on that square) so another tactic works — e.g. drag the king onto a
  forking/checking square. When the lured piece is the **king**, it's called
  **attraction**. *Finding it:* spot a tactic that WOULD work if a piece were on
  square X, then find a way to force it to X.
- **Overloading (overworked piece):** one piece is doing **two** defensive jobs;
  attack one job and it can't hold both — whichever it saves, the other falls.
- **Undermining:** remove the *support* (often a pawn) holding an enemy piece/
  structure in place.
- **Soundness (all forms):** wins iff the defender truly can't keep doing its job
  — i.e. there's no *second* defender, and the forcing move can't be met by a
  move that both answers it and keeps the guard.

## Interference (obstruction / screening)
- **Mechanic:** place a piece BETWEEN an enemy defender and the thing it defends,
  cutting the line. Especially strong vs rooks/bishops/queens (they rely on open
  lines). Often a surprising sacrifice on the blocking square.
- **Soundness:** the interposed piece must not be capturable in a way that
  re-opens the line and meets the threat in one move.

## X-ray / battery / desperado / clearance
- **X-ray:** a line-piece's influence "through" an enemy piece — it defends or
  attacks a square *beyond* an intervening piece (relevant after a capture
  sequence).
- **Battery:** two pieces stacked on a line (Q+R, Q+B, R+R) — the loaded setup
  for discoveries and overwhelming pressure.
- **Desperado:** a piece that's lost anyway grabs whatever it can / sells itself
  as dearly as possible before it dies.
- **Clearance:** vacate a square or line (often by sacrifice) so a friendly piece
  can use it with tempo.

## Trapped piece
- **Mechanic:** an enemy piece (often a bishop that grabbed a wing pawn, or an
  over-extended queen) has no safe squares; attack it and win it.

## Back-rank & zugzwang (cross-refs)
- **Back-rank:** the king is boxed by its own pawns; a heavy piece reaching the
  back rank mates. (See mates/back-rank-mate, principles/luft.)
- **Zugzwang:** any move worsens the position; the obligation to move *is* the
  weapon (mostly endgames). (See principles/avoid-stalemate for the opposite
  edge.)

---

## TRAPS (named, public-domain taxonomy from Wikipedia *List of chess traps*)
A **trap** = a move that tempts the opponent into a losing reply; it can backfire
if seen through, so a trap should not weaken your own position much. The
underlying device is always one of the tactics above.

- **Légal Trap** (Philidor/Italian): punishes a premature pin (…Bg4 pinning Nf3).
  White ignores the pin: Nxe5! and if …Bxd1?? then Bxf7+ Ke7, Nd5# (verified
  mate). Device: the pin is *illusory* (a discovered/околo-mating net beats the
  queen-grab). Avoid by **not taking the queen** — play …Nxe5 instead.
  Line: 1.e4 e5 2.Nf3 Nc6 3.Bc4 d6 4.Nc3 Bg4 5.h3 Bh5 6.Nxe5! Bxd1?? 7.Bxf7+ Ke7
  8.Nd5#.
- **Noah's Ark Trap** (Ruy Lopez): Black's a6/b5/c4 pawns **trap White's
  light-squared bishop** on the queenside. Device: trapped piece. White avoids by
  not letting the bishop get rounded up by the pawn chain.
- **Lasker Trap** (Albin Countergambit): features an early **underpromotion** to a
  knight. Device: underpromotion tactic.
- **Fishing Pole Trap** (Ruy Lopez): Black offers a knight on g4; if White grabs
  with hxg4, …Bxg4 and the opened h-file gives a mating attack. Device:
  deflection/opening lines to the king.
- **Elephant / Rubinstein Traps** (QGD): exploit a pinned/overloaded defender to
  win material. Device: pin + removing-the-defender.
- General lesson for the agent: a "free" pawn/piece in the opening is often
  bait — before grabbing, ask *what does taking this let them do?* (the
  soundness test again).
