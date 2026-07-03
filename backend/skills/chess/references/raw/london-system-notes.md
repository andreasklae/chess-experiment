# London System — read-and-note synthesis (for wiki compilation)

**Status:** raw ingest notes. Original synthesis in our own words from the sources
listed in `SOURCES.md` (chessdoctrine.com, chess-teacher.com, modern-chess.com,
365chess, thechessworld, plus Wikipedia). No verbatim copying; facts/mechanics only.
Every concrete line below is to be re-verified in python-chess before it enters a
wiki page. This file is NOT read by the agent — it is the tutor's working corpus.

## Move orders
- **Accelerated (modern main):** 1.d4 d5 2.Bf4 Nf6 3.e3 c5 4.c3 — keeps f3 for the
  knight (Nbd2), which is why ...Qb6/...Bf5 tricks don't bite (Nd2 lets the rook
  escape after ...Qxb2; and Qxf5 is available).
- **Standard:** 1.d4 d5 2.Nf3 Nf6 3.Bf4. Committing Nf3 early lets ...Qb6/...Bf5 be
  more annoying (…c4, …Bf5 forces Qc1).
- Ideal full deployment: 1.d4 d5 2.Bf4 Nf6 3.e3 c5 4.c3 e6 5.Nd2 Nc6 6.Ngf3 Bd6
  7.Bg3 O-O 8.Bd3 b6 9.Qe2 Bb7 10.e4 — fully developed, ready for e4.

## White's three plans (pick by structure)
1. **Ne5 + f4 kingside attack** (the main one). Ne5 → Qf3 (or Qh5, stops ...Ne4) →
   f2-f4 (a "reversed Stonewall") → h4-h5-h6 / Rf3-h3 → Bxh7+. Timing: Ne5 too early
   allows ...Ne4. Model: Short–Susilodinata Bangkok 2019 (8.Ne5! 9.Qf3! threatening
   Qh6 + h-pawn).
2. **Central e4 break** with Qe2 + Re1 then e3-e4. Strong when Black's bishop is on
   d6 opposite our Bg3: e4 threatens e5 winning a piece, and ...Bxg3 hxg3 opens the
   h-file for us. Models: Kamsky–Goganov Moscow 2016 (11.e4!), Carlsen–Kramnik
   Moscow 2019 (knight reroute to d3).
3. **Preventive h3** early — stops ...Bg4 and ...Nh5, gives the king luft and the
   f4-bishop the h2 square.

## Exchange / pawn structures
- **Carlsbad (after ...cxd4 exd4):** knight's ideal square is **d3** (guards b2,
  eyes e5); attack with h4-h5 to open the h-file. (Carlsen–Kramnik 2019.) If all
  minors come off, Black gets ...a5-b4 queenside play (Pihajlic–Djukic 2012).
- **Doubled f-pawns (after Bxd6 exf4):** strengthens the e5 outpost, gives knights
  d4 and e5; but d4 can become isolated after cxd5. Plan Nb3-d4 then f4-f5
  (Gukesh–Kjartansson 2020).

## Meeting Black's defenses
- **...g6 / King's Indian:** 1.d4 Nf6 2.Bf4 g6 3.e3 Bg7 4.Nf3 O-O 5.Be2 (not Bd3!)
  d6 6.h3 (stops ...Nh5/...Bg4). After ...c5 ...Qb6, Qb3 offers a trade (Qxb6 gives
  Black doubled pawns but opens the a-file). Note 7...Nc6? allows 8.dxc5 winning a
  pawn; sound is 7...Qb6 or 7...b6.
- **...c5 early (1.d4 Nf6 2.Bf4 c5):** 3.e3 Qb6 4.Nc3! (gambit — 4...Qxb2 5.Nb5
  gives White problems for Black); Black plays 4...d6/4...a6 to stop Nb5. A line
  5.Bb5 Bd7 6.a4 a6 7.a5 Qc7 8.Bxd7 Nbxd7 9.d5 heads for Benoni structures.
- **...Qb6 (main annoyance):** accelerated London answers with the Nd2 setup;
  Qb3 to trade (only legal AFTER c3). dxc5!? gambit: dxc5 Qxb2 Rb1 Qc3 — double-edged.
  Standard-London problem line: 5.c3 Qb6 6.Qb3 c4 7.Qc2 Bf5 forces 8.Qc1 (passive).
  Miles–Minasian move-order trap: 7.Qxf5 ...Qxb2?? 8.Qxd5.
- **...Bf5 (mirror):** 1.d4 d5 2.Bf4 Nf6 3.e3 Bf5 gives Black a rock-solid setup
  (...e6, ...Bd6, ...O-O). In lines with 4.c3 Nc6 5.Nf3 Bg4 6.Nbd2 e6 7.Qa4 (pins
  the c6-knight): 7...Bd6?? loses to 8.Ba6! winning material.
- **...Nh5 (trade the f4-bishop):** retreat Bg3/Bh2 (if h3 in) or allow ...Nxg3 hxg3
  opening the h-file. Sharp: 5...Nh5 6.dxc5! Nxf4 7.exf4 g6 8.c3 Bh6 gives Black some
  compensation.
- **...b6 / Queen's Indian:** harder to force the pure London; still aim for e4.

## Jobava London (1.d4 Nf6 2.Nc3 d5 3.Bf4) — a sharper sibling
- Prepares Nb5 + queenside castling. vs ...g6: 4.e3 Bg7 5.h4!? 5...O-O 6.h5. vs ...a6:
  4.e3 e6 5.g4!? Aggressive; a *different* opening in spirit — flag but keep separate
  from the quiet London so the agent doesn't confuse plans.
- Line: 3...c5 4.e3 Qxd4 5.exd4 a6 6.Nf3 Nc6 7.Ne5 Bd7 8.Be2 e6 9.O-O Qb6 10.Nxc6
  Bxc6 11.Rb1 — roughly balanced.

## Traps (to verify)
- Ne5+f4 mating trap: ...1.d4 Nf6 2.Bf4 e6 3.c3 c5 4.e3 d5 5.Nd2 Nc6 6.Ngf3 Bd6
  7.Bg3 O-O 8.Bd3 Re8 9.Ne5 Qc7 10.f4 Nd7?? 11.Bxh7! Kxh7 12.Qh5+ Kg8 13.Qxf7+ ...
- Qa4 pin trap: ...5.Nf3 Bg4 6.Nbd2 e6 7.Qa4 Bd6?? 8.Ba6! Bxf4 9.Bxb7.

## Named model games to (optionally) turn into game-analyses pages
Kamsky–Shankland 2014 (Greek gift); Short–Susilodinata 2019 (Ne5/Qf3); Kamsky–Goganov
2016 (e4 break); Carlsen–Kramnik 2019 (Nd3 reroute); Gukesh–Kjartansson 2020 (doubled
f-pawns, Nb3-d4-f5); Blatny–Luchan 2001 (Ne5 squeeze).

## Recommended (copyright — NOT ingested verbatim): Sedlak "The London System: The
Adventure Continues"; Jobava London courses. Consulted only for non-copyrightable
facts (plans, which model games exist), restated here in our own words.
