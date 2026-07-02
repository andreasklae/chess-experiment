# Wiki Log

Append-only record of every page created, updated, split, or promoted.
Newest first. One entry per maintenance action. Format:

```
## [YYYY-MM-DD] <op> | <page path> | <short description>
```

Ops: `create`, `update`, `split`, `promote` (draft→tested), `retire`.
This log plus `git diff` between batch SHAs is how the experiment measures
what the agent learned and when — keep it faithful.

---

## [2026-07-01] create+feature | positional/defending-the-king.md + detect_own_king_exposure | Defensive king-safety: tool + wiki, mirroring the offensive mate stack
- Data: EVERY recent ranked loss (12/12) is a CHECKMATE, not a material loss — the agent
  wins on material then gets its king mated (item P, now confirmed at scale). Built the
  DEFENSIVE twin of the offensive boxing/mate signals: `detect_own_king_exposure` in
  _features.py fires PROACTIVELY (before a forced mate) when the side-to-move's king is
  boxed to ≤1-2 flight squares OR marched off its shelter with enemy heavy pieces closing
  in, OR in check off-shelter — with an ENDGAME GUARD (needs an enemy queen or enough
  material) so it never tells the agent to retreat an active king in a won K+P/K+R ending.
  Fires 3.2% of positions; fires on the real loss (game 3e83ce50) the move BEFORE the fatal
  Kg4; 0 endgame over-fires on a 936-position sweep. Surfaces inline in show_position.
- New wiki page `positional/defending-the-king.md` — the "what to do when your king is under
  attack" survival recipe (is the threat real? block don't run; retreat to your army; trade
  the attackers/queen; make luft; counter only if faster), read-and-note synthesis from
  chessfox + chess.com defensive guides (SOURCES.md). Extended `positional/king-safety.md`
  with a survival section pointing to it. Registered in positional/index.md; the radar signal
  routes to it (WIKI key `defending_king`); search_wiki ranks it #1 for "my king is under
  attack". Tool→wiki wired exactly like the London pages. 505 tests; skill parses (9 tools).

## [2026-07-01] fix | openings/london-bxh7-greek-gift.md | Root cause found: the wiki's own "…Kg6 → h4 wins" line was WRONG and the agent parroted it
- The in-game diagnosis traced the agent's false "h4 wins the queen" conclusion straight to
  a TUTOR-SIDE WIKI ERROR: the page said "…Kg6 → h4 (then h5+ wins the queen)" as if it
  always works. It does not. Mechanical discriminator (verified): after Bxh7+ Kxh7 Ng5+
  …Kg6, the sac wins only if the Ng5 is DEFENDED (sound wiki example: c1-bishop guards g5)
  and a queen check arrives with force; in the batch-3 losses the Ng5 was UNDEFENDED and
  …Kg6 simply refuted it. Rewrote the …Kg6 line to say it is usually the REFUTATION unless
  those conditions hold, added a "checklist is necessary NOT sufficient — calculate …Kg6/
  …Kf8 and TRUST the imagine_line leaf verdict, don't talk past the tool" watch-out citing
  the 4 real lost games. This is a fair tutor fix (correcting our own bad synthesis). Re-ran
  the 4 unsound puzzles with the corrected page: still 4/4 declined (no regression). 504 tests.
- Lesson: an agent over-confidence failure can originate in a WRONG WIKI PAGE, not just the
  model — the agent faithfully applied bad theory. Auditing our synthesised lines against the
  board (not just FEN-legality) matters as much as the tools.

## [2026-07-01] diagnose | in-game Bxh7+ reasoning (batch-3 games 11/13/16/20) | The REAL failure: the agent over-calculates and OVERRIDES the correct leaf verdict
- Read the agent's actual in-game reasoning at the 4 batch-3 checking-Greek-gift failures.
  It is NOT a perception gap and NOT momentum: the agent called `imagine_line ×4-6` each
  time and wrote confident, detailed lines — but its CALCULATION IS WRONG. Game 11 misses
  …Kg6 entirely ("…Qxg5 loses the queen"); games 13/16/20 consider …Kg6 but claim "h4 then
  h5+ wins" — which is false (the king escapes, White is down a piece).
- Decisive: `imagine_line` on the agent's OWN claimed line (Bxh7+ Kxh7 Ng5+ Kg6 h4) already
  says "−2 for you, you end down material, this line is bad; backtrack." The agent READ this
  and played the sac anyway, writing "h4 wins" — a flat contradiction of the tool. So the
  info was present and correct; the agent OVERRODE it with its own wrong narrative. This is
  the hard core of [[chess-perception-action-gap]]: not missing information, but a confident
  false conclusion overriding an accurate mechanical verdict.
- Consequence for the fix: "go calculate" nudges (mine) and "more info" CANNOT help here —
  the agent already calculates and already has the correct leaf verdict. The A/B (identical)
  is explained. Kept the nudge ON (harmless, fair, right shape) but do NOT claim it fixes
  this. The genuine lever is the agent-overrides-correct-tools problem itself — a harder,
  model-facing issue, not a tooling gap. Recorded honestly; no further sac-tooling piled on.

## [2026-07-01] measure | greek_gift benchmark A/B (nudge ON vs OFF) | The nudge is HARMLESS but NOT demonstrably necessary — a perception-action-gap data point
- Ran the 10-puzzle greek_gift set on the live agent (eX3 Gemma-4-31B) twice: nudge ON and
  nudge OFF (env toggle CHESS_DISABLE_GREEK_GIFT_NUDGE). Results IDENTICAL: unsound sacs
  4/4 DECLINED both ways; sound sacs 4/6 played both ways. The agent's reasoning on the
  unsound ones shows it CALCULATED and rejected the sac on its own ("Bxh7+ fails because
  …Qxg5", "the line just loses") — WITHOUT needing the nudge.
- Interpretation (honest): the batch-3 unsound sacs ARE in the benchmark, yet the agent
  declines them in a single-move PUZZLE while it PLAYED them in the full GAME. This is the
  [[chess-perception-action-gap]] again at the *context* level: isolated + focused, the
  agent evaluates correctly; mid-game, momentum/a committed "kingside attack" plan carries
  it into the unsound sac. So the puzzle can't reproduce the failure, and the nudge's value
  (if any) is in-game where we can't cheaply A/B it. Kept the nudge ON by default: it is
  SOFT/confirmable, fires only on the exact pattern, costs nothing on sound play, and is the
  right *shape* of fix — but we do NOT claim it moves the metric (no evidence at this scope).
- The 2 "false negatives" on sound sacs were NOT nudge-caused: gg_5149e9 the agent followed
  a London book move (never considered the sac); gg_0dbb76 it was +8 and chose a safe move
  (reasonable, not a loss). Benchmark + toggle retained for future in-game measurement.

## [2026-07-01] fix | make_move.py (blunder gate) + puzzles_greek_gift.json | Commit-time Greek-gift nudge — the batch-3 top accuracy-leak
- Batch-3's dominant "worst move" was Bxh7+ (4×) + Ng5+ (3×): the Greek-gift sacrifice
  played when UNSOUND. Mined all 370 games → 11 unique Bxh7/Bxh2 sacs, Stockfish-classified
  (depth 18): the 4 checking ones where the king can recapture ALL threw a won game away
  (eval ~+1.4 → ~−2.5); the others were sound/non-checking. The failure is a CALCULATION
  gap: after Bxh7+ Kxh7 Ng5+ the king walks to …Kg6/…Kf8 and White has no knockout — which
  needs calculating to a leaf (imagine_line already reports it; the agent skips it).
- Fix: a SOFT commit-time nudge in `_blunder_gate` — when the move is a bishop capturing on
  h7/h2 that GIVES CHECK and the enemy king can recapture (the Greek-gift shape), it says
  "calculate the whole king hunt with imagine_line — every reply incl. …Kg6/…Kf8 — only
  confirm if it wins". Soft/confirmable (a sound sac is legitimate); mechanical pattern +
  "go calculate", never a verdict → tool-fair (same class as the SEE gate). Fires 4/4 on the
  unsound benchmark sacs (and on sound checking sacs too — correct: it forces the calc the
  agent was skipping; the sound ones survive it). 504 tests.
- Built `experiments/puzzle-benchmark/puzzles_greek_gift.json` (10 puzzles: 6 sound = play
  the sac / 4 unsound = decline it, graded by acceptable_uci) and registered a `greek_gift`
  puzzle set in main.py. Measure-first benchmark for whether the nudge changes behavior.

## [2026-07-01] fix | _opening_book.py + opening_guide.py | Generalised the recapture rule to the light bishop (…Bxd3 → Qxd3), surfaced by batch-3
- Batch-3 improvisation scan showed one remaining recurring recapture the book skipped:
  …Bxd3 (Black trades the LIGHT bishop), where the agent improvised Qxd3. Generalised the
  `recapture the traded dark bishop` rule → `recapture a traded minor` (helper renamed to
  `_traded_minor_recapture_square`, now checks f4/g3/h2 AND d3). Recapture ordering is
  square-aware: pawn-first on f4/g3 (exf4/hxg3 shape the structure), piece-first on d3
  (Qxd3 keeps the pawns healthy; cxd3 only for the c-file). opening_guide routes …Bxd3 too.
  Regression test extended; 504 tests. See work/experiment-chess-opening-batches.md for the
  full B1/B2/B3 results (accuracy flat within noise; coverage ~100%).

## [2026-07-01] fix | _opening_book.py + opening_guide.py | Book now covers recapturing a TRADED dark bishop (…Bxf4/…Nxg3) + tactic-guard refined
- Post-batch improvisation scan of all 20 opening games found a THIRD gap in every Maia
  game (move 7): after …Bxf4 trading the London bishop, the book returned NOTHING and the
  agent improvised exf4. Root cause: the material tactic-guard misread the exf4 RECAPTURE
  as a "winning capture ≥ minor" and deferred the whole book. Fix: (a) a `London —
  recapture the traded dark bishop` rule (exf4 → doubled f-pawns/e5 outpost; hxg3 →
  open h-file), routed to london-central-break; (b) restructured `_rule_lookup` so the
  REACTION rules (both recaptures + the pawn-attack-on-bishop) run BEFORE the material
  tactic-guard — a recapture is the forcing move theory wants, not a bonus tactic to
  defer for — while a real MATE-in-1 still suppresses the book. opening_guide routes it
  too. After all three fixes, EVERY White move in the first 8 moves across all 20 games
  is in book (0 early improvisations, was 10). 504 tests pass; no false firings.

## [2026-07-01] fix | _opening_book.py + opening_guide.py | Tools now detect "dark bishop hit by a pawn" (…e5/…g5) — another improvise case
- Systematic pass over ALL London wiki + raw content for every "what to do when…"
  trigger, checking each against opening_book / opening_guide / the show_position radar.
  Found one uncovered case matching a real game (5166674a: 1.d4 d6 2.Bf4 e5): the …e5
  pawn attacks the f4-bishop, but the book offered the routine setup move e3 — the agent
  had to improvise dxe5. Added a `London — dark bishop hit by a pawn` book rule (fires
  before the setup moves): challenge the pawn with a SOUND capture (dxe5) or a safe bishop
  retreat (Bg3/Bh2/Bg5, SEE-filtered so it never offers Bxe5-into-…dxe5 or a hanging
  retreat), routed to `openings/london-vs-kings-indian`. opening_guide also routes this
  case now. Verified every other wiki "what-to-do-when" trigger (…cxd4, …Qb6, …Nh5, …g6,
  …Bf5, …Bg4, early …c5, plan-phase) IS detected by at least one tool. Regression test
  added; 503 pass; no false firings on a clean setup.

## [2026-07-01] fix | _opening_book.py + openings/london-central-break.md | Book now covers the …cxd4 recapture (was an uncovered case the agent had to improvise)
- Real game 1705bcb5: after 1.d4 Nf6 2.Bf4 c5 3.e3 cxd4, the book returned the routine
  developing move **Nf3**, so the agent had to IMPROVISE **exd4** (it found the right
  move, but theory should have supplied it). Recapturing the centre pawn is core London
  theory. Added a `London — recapture on d4` setup rule (fires FIRST, after the
  tactic-guard): if Black has a pawn on d4 and White has a SOUND recapture (SEE ≥ 0), the
  book gives exd4/cxd4 as candidates (exd4 first → Carlsbad), with assumptions
  (which pawn → which structure) + the "unless a bigger forcing move" exception, routed
  to `openings/london-central-break`. That page now opens with a "if Black took on d4,
  RECAPTURE" section. Surfaces inline in show_position. Regression test added; 502 pass.

## [2026-07-01] lint+structure | (whole wiki) + top index + SKILL.md | Full lint pass; routed openings from the top index; made the London instruction permanent
- **Structure fix (important):** the top-level `index.md` routing table had NO
  openings row and still said "openings … have no pages yet" — the agent could not
  reach its own repertoire from the top. Added an OPENING row (route to `openings/`)
  and corrected the stale note. `openings/index.md` Routing now points at the hub +
  the two plan pages; fixed its dead `../strategy/pawn-structures/` link → `../positional/`.
- **Lint:** verified every read_reference path, `[[wikilink]]`, `related_pages` entry,
  inline `folder/page` ref, and markdown relative link across all 97 md files resolves.
  Fixed a PRE-EXISTING broken link in `positional/index.md` (`tactics/index.md` →
  `../tactics/index.md`). All filenames lowercase kebab-case; every `category:` matches
  its folder; every content page has complete frontmatter; every page registered in
  its folder index.
- **New connection:** `london-ne5-attack` ↔ `london-central-break` now cross-link (the
  two sibling plans) in both related_pages and body, so "pick a plan" navigates both ways.
- **Repertoire instruction made permanent + clean:** removed the temporary
  `CHESS_OPENING_INSTRUCTION=london` env toggle from `app/agent_player.py`; the London
  instruction now lives in `SKILL.md` ("In the opening — play the London System"),
  enriched with the setup order, the two plans, and the new situations the guide routes.

## [2026-07-01] create+update | 4 new London pages + raw ingest | Broad London curriculum expansion (central break, structures, ...Bf5/...Bg4, early ...c5/Benoni, Jobava) from a wider source read
- Ingested a wider source set (read-and-note, no verbatim): chessdoctrine, chess-teacher,
  modern-chess, 365chess, thechessworld London guides + Wikipedia. Notes saved to
  `raw/london-system-notes.md`; provenance + licensing in `raw/SOURCES.md`.
- **create** `openings/london-central-break.md` — the London's SECOND main plan (e3–e4
  with Qe2/Re1; the Bd6-vs-Bg3 point where ...Bxg3 hxg3 opens the h-file) + the pawn
  structures that decide plan choice (Carlsbad → Nd3; doubled f-pawns → Nb3-d4-f5).
- **create** `openings/london-vs-bishop-out.md` — Black's early ...Bf5 (mirror) / ...Bg4
  (pin on f3): how to develop, plus the verified Qa4→Ba6 trap (Bxb7 forks Ra8+Nc6).
- **create** `openings/london-vs-early-c5.md` — early ...c5 on d4 before c3: support d4,
  the Nc3–Nb5 gambit vs ...Qxb2, or push d5 into a favourable Benoni.
- **create** `openings/london-jobava.md` — the sharper Jobava (2.Nc3) sibling, clearly
  flagged as a DIFFERENT plan so the agent doesn't mix it with the quiet London.
- **update** `openings/london-system.md` (route to all four + both plans),
  `openings/london-vs-qb6.md` (CORRECTED the dxc5 gambit line — the earlier "Rb1 Qc3+"
  was illegal with the b1-knight home; now Nd2 after dxc5, or the Nc3–Nb5 move order).
- **tools:** `scripts/opening_guide.py` now routes early-...c5, ...Bf5/...Bg4, and (once
  castled) offers BOTH plans (attack / central break). `scripts/_opening_book.py` ...Qb6
  exception now points at the early-c5 gambit. All new lines verified in python-chess;
  501 tests pass; skill parses (9 tools); all related_pages resolve; every page indexed.

## [2026-07-01] update | tactics/pins-and-skewers.md + tactics/forks-and-double-attacks.md | Skewer/fork SOUNDNESS rule (front must be forced) — paired with the _features.py detector fix
- Real game 57fc05ad: the agent played Qd3 thinking it "skewered" a rook (c4) with a
  bishop (a6) behind — but the rook was DEFENDED and worth LESS than the queen, so
  nothing was forced (Qxc4?? dxc4). Added the explicit rule to both pages: a skewer/
  fork only wins if the front/target piece is FORCED — i.e. undefended, or worth more
  than the attacking piece (or the king). Also fixed `scripts/_features.py`
  `detect_skewers` to enforce this (new `_front_is_forced` helper) + drop pawn-only
  prizes + require the skewering piece to be safe on its landing square. Forks already
  enforced this (detect_piece_forks / detect_knight_forks); tightened the wiki wording
  to match. Regression tests added (test_features.py); synthetic sweep = 1.000
  precision / 1.000 recall over ~1950 skewer geometries; full suite 496 passed.

## [2026-07-01] create+update | london-ne5-attack.md (new) + greek-gift/qb6 deepened | Comprehensive London curriculum: the missing attacking PLAN, and stronger Greek-gift / ...Qb6 pages
- **create** `openings/london-ne5-attack.md` — the London's core middlegame PLAN that was
  entirely missing from the wiki: the **Ne5 outpost → f4 → Rf3–h3 lift → h4–h5 storm →
  Bxh7+** recipe, in order. This is "what to do after the setup" — the page the hub and
  the show_position radar can route to once developed. Model games Kamsky–Shankland 2014
  and Blatny–Luchan 2001 (move orders verified in python-chess). Registered in
  openings/index.md; cross-linked from london-system.md (routing + related_pages).
- **update** `openings/london-bxh7-greek-gift.md` — reframed "recognise it, THEN calculate
  it". The Maia review showed the agent now *declines* sound sacs, not just plays unsound
  ones — so added an explicit "recognise the pattern (all present → CALCULATE the sac now)"
  section and a "the opposite error: DECLINING a sound sac" watch-out. Added the
  Kamsky–Shankland 2014 model game (Ne5 → Bxh7+ Kxh7 Qh5+ Kg8 Ne4). Trimmed 77→65 lines.
- **update** `openings/london-vs-qb6.md` — added the deep-position nuance the redesigned
  book now carries as an EXCEPTION: **Qb3 is a move-1-of-...Qb6 answer, not forever** —
  once the queen has sat on b6 for several moves and the position has developed, reflexive
  Qb3 is often a positional blunder; reason it out instead. Added the concrete traps:
  Qc2→...Bf5→...Qxb2 pawn loss, the Miles–Minasian 2001 move-order line (7.Qxf5! …Qxb2??
  8.Qxd5), and the dxc5 gambit (dxc5 Qxb2 Rb1 Qc3+). All FENs verified in python-chess.
- Sources used (all legally usable — synthesised, not copied verbatim): Wikipedia (London
  System, Greek gift — CC-BY-SA), Exeter Chess Club notes (Qb3 exchange line, Miles–Minasian
  trap, Kamsky–Shankland, Blatny–Luchan), modern-chess (Ne5 timing, h4–h5 storm, dxc5 vs
  ...Qb6). thechessworld.com and 365chess.com returned HTTP 403 (blocked) — did not need them.
- Registered/updated openings/index.md; all related_pages targets resolve.

## [2026-06-25] sources+update | lichess-puzzle-themes.md + trigger alignment | Saved Lichess theme curriculum; sharpened motif triggers for the puzzle benchmark
- Saved `raw/lichess-puzzle-themes.md` (25 official Lichess puzzle-theme definitions, AGPL/free, verbatim) — the same theme tags the agent puzzle benchmark selects on. Recorded in `raw/SOURCES.md`.
- Aligned wiki triggers to the Lichess motif vocabulary so search_wiki matches: added "capturing the defender" to `tactics/removing-the-defender`, and "quiet move / no forcing move / improving move" to `positional/prophylaxis-and-blockade`. The motifs themselves were already covered by the deep-tactics pass; this is terminology alignment, not new theory.

## [2026-06-24] consolidate+lint | wiki cleanup pass | Completed the 2026-06-17 flatten; merged duplicate islands; new crosslinks; OCR'd images
Cleanup/strengthening pass (Wikipedia-style scoped single-source pages + crosslinks). **Completed the incomplete 2026-06-17 restructure**: the `strategic-thinking/` and `patterns/` folders that ADR meant to remove had lingered as orphaned, *older* duplicates (self-referencing only, no inbound links from active pages, superseded content — `mates/` was the strict superset with newer pages, `strategy/` newer than `strategic-thinking/`, `tactics/deflection` canonical). Removed both folders (+ the empty `pawn-structures/` stub). Wiki is now **flat: 9 one-level folders**, every folder index verified to list exactly its real pages. Fixed the one dangling ref in `game-analyses/index.md`.
New crosslinks from the source material: `tactics/discovered-attacks` ↔ `mates/smothered-mate` (the smothered mate IS a knight double-check — its marquee example); `strategy/handle-a-threat` → `tactics/more-motifs` (the counter-threat response IS a zwischenzug); `positional/evaluate-position` → `tactics/index` (assessment flags tactical targets — "loose pieces drop off"); added the **combination** concept (forced sequence of motifs, calculable against any defence) to the tactics index as the umbrella over the soundness test. Closed several 0-inbound orphans (more-motifs, smothered).
OCR: the 3 composed images in `raw/images/` (rendered pictures, not templates) transcribed by vision into FEN+grid, validated in python-chess → `raw/images/diagram-images-as-fen.md` (skewer-bishop, pawn-fork, absolute-skewer GIF [low-res, pawns approximate]). Lint: 0 unresolved links in the active wiki (remaining hits are append-only log history + raw-source internal notes); skill loads; search_wiki routes only to canonical pages (0 hits to removed folders).

## [2026-06-24] create | fundamentals/ — 5 always-relevant pages + 2 more PD books + 116 inlined diagrams | Per-phase + every-move fundamentals; verbatim diagrams; provenance
New `fundamentals/` folder: `every-move-checklist` (the always-applicable thinking method: threats→safety→tactics→improve, as imperatives), `opening`/`middlegame`/`endgame` (what to aim for per phase — actionable, grounded in Capablanca + Edward Lasker, not theory dumps). Wired into the wiki `index.md` AND `SKILL.md` (routing-table row + the one-line checklist now surfaced every turn in the turn-workflow section, with a pointer to the full page). The agent gets a phase label from `show_position`, so it can open the matching phase page.
Diagrams: re-extracted all diagram-bearing Wikipedia raws so each position appears INLINE as FEN + ASCII grid (the representation the agent reads), reconstructed losslessly from the article `{{Chess diagram}}` wikitext and verified in python-chess (116 positions, 0 invalid). Composed images downloaded to `raw/images/` (3). Converter: `experiments/board-visualization-benchmark/lib/wiki_diagram_md.py`.
Sources: added two more public-domain books from Wikipedia further-reading — `edward-lasker-chess-and-checkers-GUTENBERG-4913.txt` (#4913) and `blue-book-of-chess-GUTENBERG-16377.txt` (#16377). Rejected the archive.org endgame books (1975–2005, copyrighted) — recorded in SOURCES.md. All links resolve; skill loads; search_wiki routes to the new pages.

## [2026-06-24] sources | raw/ — stored 24 verbatim source files + SOURCES.md provenance | Replaced summaries-only with the actual verbatim sources
Per the KB principle that raw/ holds the source of truth (not just our synthesis), stored the **verbatim** texts everything was built from. Books (public domain, full text via Project Gutenberg): `edward-lasker-chess-strategy-GUTENBERG-5614.txt` (#5614, 13.9k lines, complete) and `capablanca-chess-fundamentals-GUTENBERG-33870.txt` (#33870, complete) — both verified with the Gutenberg end-of-book marker. Encyclopedia (CC BY-SA, verbatim plain-text via the MediaWiki extracts API, retrieved 2026-06-24): 21 Wikipedia articles — pawn-structure, chess-strategy, glossary-of-chess, chess-opening, chess-tactic, combination; motifs fork/pin/skewer/discovered-attack/deflection/decoy/interference/overloading/windmill/zwischenzug/xray/battery/zugzwang; isolated-pawn/passed-pawn/outpost/list-of-chess-traps/legal-trap. Open content: `lichess-practice-curriculum.md` (32 study titles+descriptions; AGPL/free). Added `raw/SOURCES.md` documenting every file + its license (public-domain/CC only; no copyrighted or paywalled text reproduced — facts/mechanics synthesised in our own words). Relabelled the two earlier `*-extract.md` files as paraphrased digests pointing to their verbatim Gutenberg source. Copyright-clean for the thesis.

## [2026-06-24] create+update | deep tactics mechanics + traps + prophylaxis — 5 new pages, 3 rewritten | Second, deeper sourcing pass (Edward Lasker + Lichess + motif taxonomies)
Deepened the tactics layer with real exploitation mechanics + a soundness test on every page. **Rewrote** `tactics/discovered-attacks` (now covers the free-capture engine — moving piece grabs anything on a discovered check — double check, the windmill, and the exact 3-condition soundness test for when a discovery fails), `tactics/pins-and-skewers` (pile-on + "a pinned piece defends nothing" + how a relative pin breaks), `tactics/forks-and-double-attacks` (current vs potential, royal fork, soundness test). **Added** `tactics/removing-the-defender` (the umbrella: capture/deflection/decoy-attraction/overload/interference/undermining, with deflection-vs-decoy distinction), `tactics/more-motifs` (zwischenzug/desperado/clearance/X-ray/trapped-piece + the unifying two-threats test), `tactics/traps` (Légal verified mate, Noah's Ark, Fishing Pole, Elephant/Rubinstein, Lasker; the "free pawn is bait" lesson), and `positional/prophylaxis-and-blockade` (prophylaxis, blockade with a knight, pigs on the 7th, fix-a-weakness). Sourced from new raw files `tactics-mechanics.md` (Wikipedia *Chess tactic/Discovered attack/Deflection/Decoy/Windmill/traps* + Lichess Practice CC curriculum + chessfox/chessworld taxonomies) and `edward-lasker-chess-strategy-extract.md` (Project Gutenberg #5614, public domain — mobility=value, "every pawn a prospective queen", SEE-as-arithmetic, sacrifice needs compensation, pawn formation is permanent). Tactics + positional indexes updated; all wikilinks resolve; search_wiki routes to each. Copyright discipline: only public-domain (Capablanca, E. Lasker) full text in raw/; facts/mechanics synthesised in our words. Status: draft.

## [2026-06-24] create | positional understanding — 11 pages across positional/, tactics/, principles/, strategy/ | Ingested comprehensive positional theory from Capablanca + Wikipedia
New folder `positional/` (assess-the-position layer, previously missing) with `index.md` + 5 pages: `evaluate-position` (the both-sides assessment method), `pawn-weaknesses` (isolated/doubled/backward/holes/hanging), `pawn-strengths` (passed/connected/majority/chains), `piece-activity` (open files/outposts/good-bad bishop/bishop pair/space), `king-safety`. Extended `tactics/` with `forks-and-double-attacks`, `pins-and-skewers`, `discovered-attacks` (current vs potential threats, both sides). Extended `principles/` with `opening-principles` and `material-and-trading` (incl. the keep-mating-material rule). Extended `strategy/` with `handle-a-threat` (the capture/defend/move/counter-threat/check decision procedure — the page the future positional tool will instantiate with concrete legal moves). All indexes updated (top-level, tactics, principles, strategy) so pages are routable; search_wiki finds each; all wikilinks resolve. Sourced from `raw/capablanca-positional-extract.md` (PDF Ch. III-V) + `raw/positional-concepts.md` (Wikipedia pawn-structure / glossary / strategy / opening, fetched 2026-06-24). Status: draft (to be promoted as games confirm them). Part of the board-representation-and-context-fidelity branch.

## [2026-06-19] test | mate-conversion sweep (Maia 1100, puzzle mode) | Tested whether the agent converts each documented mate from a puzzle position. PASS = found mate. CONFIGURATION/TECHNICAL mates all pass: K+2R, K+R (~23p), K+Q (~23p), back-rank (M1 Ra8#), arabian (Rh7#), anastasia (Rh5#), greco (Qh5#), hook (Re8#), opera (Rd8#). The named-mate puzzles were real positions: config mates derived+verified from the Wikipedia "Checkmate pattern" archetypes (scripts/gen_named_mate_puzzles.py), not invented. SACRIFICIAL mates FAIL: smothered (agent reached the Philidor setup Qe6+/Nf7+/Nh6+ and even *stated* "preparing the queen sacrifice on g8" but flinched and repeated the knight check instead of Qg8+); blind-swine (blundered both rooks, never found the forcing Rxg7+/Rxh7+ line). Skipped queen-contact/epaulette/dovetail (no clean mate-in-1 construction; rare). Headline: the agent converts mates that are material+technique (drive/confine/place the final blow) but cannot execute mating COMBINATIONS that require a material sacrifice, even with the forced line in front of it — a capability boundary, not a tooling gap (wiki pages + imagine_move gave it everything). Note: basic mates are stochastic across runs — K+2R mated in 17p one run and drew another; the deterministic confine_state rule improves but does not guarantee them.

## [2026-06-18] rewrite | _radar.py + _eval.py + K+R/K+Q pages (ONE deterministic rule) | After repeated K+R failures (the agent shuffled the king or fled the rook to a corner), reduced the whole single-major advisor to Capablanca's actual algorithm as ONE rule: (1) play a flagged checkmate; (2) if a tighter rook/queen square exists that the king can defend IN TIME, move the major there; (3) else step the king closer. New mechanics helper `confine_state` (pure geometry: current box area, smallest box reachable by a defensible major move, and a can_tighten yes/no) classifies the position's structure WITHOUT naming a move — like 'is there a back-rank weakness' — so it stays mechanics-side of the fairness rulebook; the agent executes the branch with imagine_move. Replaces the brittle fence/opposition machine and the priority-list that produced wrong-way checks and rook-shuffles (games 4a211a2a, f923a018, 1403f9cc, 8063c239). Pages rewritten to the one rule. 311 tests pass.

## [2026-06-18] fix | _radar.py + king-rook-mate.md (mating-phase squeeze) | Stockfish analysis of game 1403f9cc found the agent reached mate-in-2 (W10) then bounced M2–M4 for seven moves: at W13–17 a quiet rook squeeze (Rd4/Re4/Rf4) mated in 2 every move, but the agent played KING moves. Root cause: the mating-phase advisor said "find the rook move that CHECKS" — but the K+R finish usually needs a QUIET rook move to take the king's last sideways squares first, then mate. Finding no mating check, the agent fell back to marching its (already-close) king. Fixed: the on-edge rule now detects a real mate-in-1 mechanically (scan legal moves for checkmate = rules, not search); if none, it instructs the quiet one-line-at-a-time rook squeeze on a king-defended square (never stalemate). Page rule 4 rewritten to match ("no drastic moves, one rank/file at a time, king always defending the rook").

## [2026-06-18] rework | _radar.py + imagine_move.py + show_position.py + K+R/K+Q pages | Replaced the brittle K+R/K+Q fence-and-opposition state machine (it chose the drive direction from the fence regardless of the king's side → wrong-way checks and rook-shuffles, games 4a211a2a/f923a018; the king never marched) with a PRIORITY-based advisor: rook-safe-first; kings>2 → march the king (confine only on a square the king defends in time); kings-close-not-edge → tighten the box; edge+kings≤2 → mate. The per-move CONFINEMENT FACTS moved from show_position to **chess__imagine_move** (where the agent compares candidates): box-area before→after, king-distance before→after, and "is the major defensible in time" — all numbers + words, no ASCII art (the model reads numbers better). New _eval helpers: lone_king_color, piece_defensible_in_time. Pages rewritten to the confine/march/mate method pointing at imagine_move. 308 tests pass.

## [2026-06-17] unify | mates/king-queen-mate.md + king-rook-mate.md + _radar.py | UNIFIED K+Q onto the K+R drill (user insight, verified against Capablanca's Chess Fundamentals mate-in-11 in python-chess): a queen IS a rook for fencing/opposition/edge-mate — it just also cuts diagonals (faster) and stalemates more easily. The lone-queen case now flows through the same single-major advisor as K+R (one `piece_noun` parameter + a stalemate guard up front), replacing the separate box-phase function (now deleted). KEY EFFICIENCY FIX for both: the kings stay within 2-3 the WHOLE mate; when they drift far (>3) with a fence set, the advisor says MARCH YOUR KING, not move the major — this is the cure for the 49-ply K+R grind and the K+Q queen-shuffle stall. K+Q page rewritten to "same as king-and-rook, with a queen; watch stalemate". Examples verified. 301 tests pass.

## [2026-06-17] rewrite | mates/king-queen-mate.md + king-rook-mate.md (box method) | Reframed both basic mates around the CONFINEMENT BOX: shrink the box toward an edge AND march your king in, both must progress every move. Replaces the K+Q "mirror" wording that let the agent shuffle the queen forever without marching (game 34391da0 stalled 26 plies, king never left e1). New live per-turn advisor in _radar.py (`_basic_mate_phase_lines`) detects the phase from box-area + king-distance and emits ONE instruction (shrink / march / mate / stalemate-guard). New mechanics helpers in _eval.py (confinement_box, confinement_box_bounds, kings_distance) and a confinement-box drawing in show_position. All four directions. Pure geometry — fairness-compliant (names the recipe step, not a searched move). 10 new tests; 301 pass.

## [2026-06-17] restructure | (whole wiki) | Flattened to six topic folders, max one subfolder level (ADR 2026-06-17-wiki-basic-mates-restructure). `patterns/mating-patterns/` + the basic-mate pages → single `mates/` folder (split inside its index by bare-king-vs-not). `strategic-thinking/` (+ pawn-structures) → `strategy/`. `patterns/deflection.md` → `tactics/deflection.md`. Empty `openings/`, `pawn-structures/` no longer routed from the top index. All indexes rewritten to carry per-page "read this when…" so navigation needs one hop; all `[[wikilink]]`/related_pages/radar/SKILL paths repointed.

## [2026-06-17] merge+retire | endgames/two-rook-mate.md → mates/two-rook-ladder-mate.md | Consolidated the day-old herding/support page into the older, more thorough ladder-mate page (now `mates/two-rook-ladder-mate.md`); kept all trap coverage, folded herding framing into "the idea", scoped the page to two rooks (Q+R / Q+Q ladders get their own pages when seeded). Resolves the two-pages-one-endgame duplication. status: draft.

## [2026-06-17] create | endgames/two-rook-mate.md | K+2R forced-mate technique: mechanical herding/support rook pattern, stalemate avoidance, edge-mate delivery. Diagnosed after puzzle 49389f2b: agent was moving wrong rook and trapped itself in loops; explicit drill prevents the pattern from repeating. status: tested. (SAME DAY: merged into mates/two-rook-ladder-mate.md, see above.)

## [2026-06-10] create | raw/chess-fundamentals-capablanca.md | Ingested Capablanca's Chess Fundamentals (Gutenberg #33870, public domain): Ch. I §1-4 + Ch. II §9-13 converted to FEN + SAN, every line replayed in python-chess. Source for the simple-mates / promotion / opposition pages.

## [2026-06-10] create | patterns/mating-patterns/ladder-mate.md | Two-major-piece ladder mate, with the slide-away trick. Example line verified mate. status: draft.

## [2026-06-10] create | patterns/mating-patterns/king-queen-mate.md | K+Q basic mate: knight's-move shadowing, king walk, stalemate trap (verified). status: draft.

## [2026-06-10] create | patterns/mating-patterns/king-rook-mate.md | K+R basic mate: fence + opposition + waiting move; stalemate trap (verified). status: draft.

## [2026-06-10] create | patterns/deflection.md | Removing the sole guard of a mating square; Qc8+ example verified mate. Resolves the dead [[patterns/deflection]] link from back-rank-mate. status: draft.

## [2026-06-10] create | principles/luft.md | Escape square for the castled king; with/without-luft FENs verified. Resolves the dead [[principles/luft]] link from back-rank-mate. status: draft.

## [2026-06-10] create | principles/avoid-stalemate.md | Stalemate awareness when far ahead; three verified stalemate traps (Q, R, pawn). status: draft.

## [2026-06-10] create | strategic-thinking/convert-advantage.md | The conversion staircase: trade pieces → passed pawn → promote → basic mate; checks-with-a-purpose; move-budget urgency. status: draft.

## [2026-06-10] create | strategic-thinking/make-a-plan.md | Forming, writing down, keeping, and replacing a standing plan; pairs with the plan field in make_move. status: draft.

## [2026-06-10] create | endgames/king-pawn-endings.md | King-in-front rule, opposition, race counting, passed-pawn creation, wrong rook's pawn. Examples from the Capablanca raw notes. status: draft.

## [2026-06-10] update | (indexes) | Registered all new pages in patterns/, patterns/mating-patterns/, principles/, strategic-thinking/, endgames/ folder indexes; added "choose the simplest mate" routing note to mating-patterns index.

## [2026-06-02] create | patterns/mating-patterns/back-rank-mate.md | First seed page — validates the page contract (frontmatter + When-to-use/Idea/What-to-do/Watch-out/Examples). FEN verified mate in python-chess. status: draft.

## [2026-06-02] create | (scaffold) | Initial wiki skeleton: top index, per-folder indexes, this log. No content pages yet.

## [2026-06-11] create | patterns/mating-patterns/{smothered,anastasia,arabian,hook,greco,queen-contact,opera,blind-swine}-mate.md | Eight named-mate recipe pages distilled from raw/checkmate-patterns-wikipedia.md; all FENs verified; each carries machine-readable template_ frontmatter for the pattern-trigger matcher. status: draft.

## [2026-06-11] update | patterns/mating-patterns/{king-rook-mate,ladder-mate,king-queen-mate}.md | Rewritten as numbered apply-first-matching-rule drills (live sessions showed concepts don't execute; the ladder draw happened at the missing slide-far-then-mate finish, now an explicit two-move template).

## [2026-06-11] update | patterns/mating-patterns/index.md | Registered the eight new pages.

## [2026-06-12] update | patterns/mating-patterns/king-queen-mate.md | Phase 1 mirror rule made operational after game 185afd0b drew by repetition with the queen oscillating d5/e4: mirror = copy the king's last move DIRECTION; never return the queen to the square she just left — march your own king instead (early phase 2). status: draft.

## [2026-06-12] update | patterns/mating-patterns/ladder-mate.md | Rule 2 covers king-touching-defended-rook paralysis; new rule 2b: rooks stacked on one file must split to opposite wings (live ladder game aa1a22ac shuffled checks with both rooks on the h-file). status: draft.

## [2026-06-13] update | patterns/mating-patterns/ladder-mate.md (advisor) | Two-major ladder now locks the target to the nearest back RANK and never reconsiders; previous nearest-fenced-edge rule thrashed between rank and file targets turn-to-turn (game a971fff9), breaking the drill. One-major K+R/K+Q edge logic unchanged.

## [2026-06-13] update | ladder advisor (_radar.py) | Check rule now names the fence rook and the free rook by square and forbids checking with the fence rook — game 43b388f5 played Ra5 (fence) then Ra6+ (abandoning the fence with the same rook), king dropped straight back down. Names the exact far-side check square too.

## [2026-06-13] update | ladder advisor (_radar.py) | ROOT CAUSE of the ladder draws: the check rule named a formula-derived target (e.g. b1->h6) that was not a legal rook move, and forbade the one rook (the fence rook) that COULD legally check via Ra6+. The model received an impossible instruction and thrashed. New _best_ladder_check enumerates legal moves and names a real, non-hanging check on the king s line (mechanics: enumeration+geometry, no search); when none exists it advises a far-file reposition. Invariant test added.

## [2026-06-13] rewrite | ladder-mate.md + ladder advisor (_radar.py) | Reframed as two iron rules: (A) fence before you check, (B) check with the OTHER rook never the fence rook. Advisor pulled back from naming a concrete move to naming the recipe STEP (which rook, the principle for the square). Sticky drive direction (fence decides, no mid-board flip). Verified line 1.Rb5 Ke6 2.Ra6+ Ke7 3.Rb7+ Ke8 4.Ra8#. New test proves a recipe-faithful follower MATES (recipe is sufficient; residual gap is model execution), and that the advisor never names a concrete move.

## [2026-06-13] redesign | ladder-mate.md + ladder advisor (_radar.py) | Shifted from prescriptive per-turn moves to PRINCIPLES + a board self-check. Advisor now states the two ideas (fence before check; keep rooks far from king) and tells the model to verify candidates with imagine_move (Enemy king mobility must go DOWN or be check; UP = broke the fence). No move/square is named — the model reasons over its own board. Same philosophy to apply to all mate pages.

## [2026-06-13] add | ladder-mate.md + advisor (_radar.py) | FINISH EXCEPTION: when the king is on the edge and a rook sits beside it, the natural edge check hangs that rook (Ra8+?? Kxb7, the exact stall in game cc55b0b9). Rule: slide the adjacent rook far along its line first (keep the cut-off), then the next check is mate. General condition, not a computed move. Verified line 2k5/1R6/R7/.../ 1.Rh7 Kd8 2.Ra8#.

## [2026-06-13] update | king-rook-mate.md + king-queen-mate.md | Added the imagine_move "Enemy king mobility" compass to both basic-mate drills: a good move holds/lowers the number, a check drops it, a quiet drop to 0 = stalemate. Same self-check principle as the ladder page — propagated to the drills where the shuffle-without-progress failure mode actually occurs.

## [2026-06-15] update | _radar.py | Added _own_back_rank_lines: defensive mirror of the back-rank check — warns when OUR king is walled on its back rank with an enemy major + open file to reach it (and no luft). Strictly gated to stay quiet in normal middlegames. From game 9b0d7590 (agent mated on its own back rank, never made luft).

## [2026-06-16] update | king-rook-mate.md + K+R drill advisor (_radar.py) | Synthesized the canonical K+R technique from chess.com / Wikibooks / chesscorner: mate is on the EDGE (no corner needed); the finish is fence → march king to OPPOSITION → one rook check. Added rule 5 (FOLLOW a sideways dodge with your king, don't chase with the rook) and rule 6 (rook WAITING move when opposed on the wrong parity). Strengthened the "never check without opposition / never check with the fence rook" warning — the exact "checks that do nothing, king escapes" failure the user reported. Advisor (_radar.py single-major branch) now detects the sideways dodge from the move stack and the on-edge opposition mate. New examples (Rh8# edge mate, the Ke6→Ra8# sideways herd, the Ra7 waiting move) all machine-verified; recipe-follower unit test (TestKingRookRecipe) proves the text is followable to mate from the standard drill starts.

## [2026-06-16] update | back-rank-mate.md | Added a verified worked deflection example with ASCII board: Lichess puzzle #JxR8M, a fully-forced back-rank deflection (1.Qb8+ Rd8 2.Qxd8+ Rxd8 3.Rxd8#, every black reply the only legal move). Sourced online (not invented), line + final mate verified in python-chess. Wired into scripts/run_puzzles.py as the "backrank-deflection" puzzle; also added a Q+R "qr-ladder" puzzle (standard open position) alongside the two-rook ladder.

## [2026-06-16] add | scripts/run_puzzles.py (suite, not wiki) | Replaced the over-complex deflection mate-in-3 with two sourced back-rank mate-in-2 puzzles from wtharvey.com (backrank-d-file 1.Qb8+ Nxb8 2.Rd8#; backrank-e-file 1.Qd8+ Bxd8 2.Re8#) — simpler "spot the trapped king, mate on the open file" test. Added a qr-ladder (Q+R) puzzle. Puzzle default opponent raised to Maia-1900 (forced mates are forced; removes the won-by-luck confound). Source saved at knowledge-base/raw/other/2026-06-wtharvey-mate-puzzles.md.

## [2026-06-16] update | ladder-mate.md + ladder advisor (_radar.py) | Synthesized the two-major ladder FINISH from chesskid/chess.com/oldschoolchess. Added Trap 2 (your own king blocks the rook's check when the enemy king is driven onto your king's rank/file — game 8909ef13 stalled with enemy Kc1 vs our Kg1, every rank-1 check self-blocked): drive the enemy king to the edge AWAY from your own king, and if they share a line, mate from the far side or step your king off it. Generalized the whole drill to "two major pieces" so QUEEN+ROOK reads naturally, and added a QUEEN CAUTION (never put the queen adjacent to the bare king unprotected; watch stalemate). Advisor now: (a) drive-direction default targets the edge away from the friendly king, (b) emits a SELF-BLOCK line when kings share the enemy king's edge line, (c) emits the queen caution when a queen is present. New example lines (1.Rd3 Kb1 2.Rd1# self-block finish; trap-1 slide) machine-verified.

## [2026-06-16] rewrite | ladder-mate.md + ladder advisor (_radar.py) | Per user, restated the ladder as ONE simple invariant covering all 4 directions: two majors on the king's rank + the rank behind it (transpose rank↔file for an a/h-file mate); one checks, one walls; shift both after the king, repeat to the edge. Advisor now reports the FACTUAL state each turn (king's rank; which majors are on the king's rank vs the wall rank) so the model stops losing track. Added, all general: (a) ROOKS-BLOCK-EACH-OTHER warning when two rooks share a file (they can't pass — must be on different files); (b) king-attack handling via SEE — a rook is only "losing" if actually capturable for material (so a queen guarding an adjacent rook makes the king attack harmless), and when it is losing the advisor lists the SEE-SAFE relocation squares (considering ALL enemy pieces, not just the king); (c) drive direction defaults AWAY from our own king to avoid self-block; (d) refined queen caution (protected queen beside the king is fine/often the mate). Shared SEE helpers (is_losing_on_square, safe_destination_squares) moved to _eval.py and now used by both show_position's hanging-piece hint and the ladder advisor.

## [2026-06-16] fix | ladder advisor (_radar.py) + ladder-mate.md | Fairness + correctness pass on the ladder. (1) DIRECTION is now simply the edge the king is CLOSEST to (stable across turns — pushing toward it never flips), replacing the convoluted away-from-our-king rule; the self-block stays a separate FINISH concern. (2) Fixed a geometry bug: the advisor put the wall on the wrong side and printed an out-of-range "rank 9" when the king was on the edge — now the king-on-target-edge case is handled as the FINISH (wall on the rank just inside, check the edge = mate). (3) Added a plan-persistence nudge: record your target edge in `plan` so you keep driving the same way. (4) TOOL-FAIRNESS: a briefly-added "SUGGESTED move: <SAN>" line was REMOVED — under 2026-06-02-tool-fairness-rulebook the tool may give strong board-specific direction but must NOT name the move to play (that is the tool playing). The advisor now states the king's rank, the wall rank, which majors sit where, the direction, and the rooks-block/safe-square facts — the agent chooses and verifies the move with imagine_move.

## [2026-06-16] add | ladder advisor (_radar.py) + ladder-mate.md | Capturable-check / waiting-move finish (Trap 1b) + AVOID-dead-checks fact. (1) When the checking/mating rook would land ADJACENT to the king it is captured (Ra8+?? Kxa8); the advisor now teaches checking from a file ≥2 away, or — when no safe check exists — a WAITING move sliding the wall rook sideways (zugzwang → king to corner → mate). Transposes to all directions. Verified 1k6/7R/R7/8/8/8/8/6K1: 1.Re7 Kc8 2.Ra8#. (2) Added an AVOID-dead-checks line computed from the board: it names the checking squares where the rook would be CAPTURED and undefended (SEE after the move) and the SAFE checking files (≥2 from the king), so the model stops wasting imagine_move calls on obviously-losing checks; if no safe check exists it points to the waiting move. Facts about squares, names no move (fairness preserved, unit-guarded). Motivated live: game 65e0eed5 stalled imagining bad checks at Kb8, then mated (Rc6 Ka8 Rc8#) once the finish rule landed; re-test from the exact stuck FEN mated in 3 (Raa7 Kc8 Ra8#).

## [2026-06-16] rewrite | ladder advisor (_radar.py → new _ladder_lines) | Made the two-major ladder advisor COMPACT and board-ADAPTIVE to stop model drift (too much text per turn made it ladder correctly then play a junk finish move, game b60f731d). It now emits a short header + EXACTLY ONE rule for the current situation (was 5-8 long lines): hanging/blocking rook → slide sideways first to a cross-line the other rook isn't on; no wall → build it quietly; king on edge with safe check → mate; king on edge no safe check → waiting move; else → check from a safe distance. Added the user's explicit rule (if the next move leaves a rook capturable OR two rooks share the drive-cross-line, move that rook sideways to a different file/rank FIRST). Generalised the whole thing over a DRIVE AXIS (rank or file, whichever edge the king is nearest) so file-ladders (king on the a/h-file) are handled natively — the file↔rank transposition is done once. Fixed a wall-direction inversion (king on the top edge was told to drive DOWN). Still fairness-clean: states which line/squares, never the move. All in show_position's radar (a tool), not the turn prompt.

## [2026-06-17] update | convert-advantage.md + ladder advisor (_radar.py) + turn prompt | Two changes. (1) "Eliminate the opponent's threats before mating": the ladder advisor now leads with a PRIORITY-0 interrupt when an enemy pawn is one push from promoting (it would queen a new major and break the mating net — game 912d0f7f tunnel-laddered through ...c2-c1=Q+). Framed as the general principle, triggered on the concrete detectable case; never fires if we can mate this move. Durable principle added to convert-advantage.md "Watch out for". (2) Turn-prompt hygiene: removed _drill_state_for_prompt from agent_player.py's per-turn prompt — the prompt now carries only bare facts (whose move, FEN, legal moves, the agent's own plan/goal), and ALL position analysis (radar, drill state, threats) comes from the agent's TOOLS (chess__show_position). The prompt no longer analyses the position or hints moves.

## [2026-06-19] create | mates/king-two-bishops-mate.md | K+2B forced mate (≤19), drive to ANY corner, opposite-coloured bishop wall + king march; sourced from Capablanca Ex.3 (full mate-in-14 line verified in python-chess) + Wikipedia. Registered in mates/index.md; radar (_radar.py _PAGE_KBB + _minor_mate_lines) points here and supplies the per-turn corner-drive advisor.

## [2026-06-19] create | mates/king-bishop-knight-mate.md | K+B+N forced mate (≤33), the hardest basic mate; mate ONLY in the bishop-coloured corner. Three-phase method + W-manoeuvre, sourced from Wikipedia "Bishop and knight checkmate" (Seirawan method); example mate FENs verified in python-chess. Registered in mates/index.md; radar (_PAGE_KBN + _minor_mate_lines) names the right corner per side.

## [2026-06-19] rewrite | mates/king-bishop-knight-mate.md + king-two-bishops-mate.md | Reframed both minor-piece mates from recipe to PRINCIPLE+VISUALISATION: the mate is shrinking the lone king's "net" (free region) toward the right corner (bishop-colour for K+B+N; any corner for K+2B). Point the agent at the net display in show_position and at chess__imagine_line for multi-move planning. Sourced: Capablanca Ex.3 (K+2B, full line verified) + Wikipedia "Bishop and knight checkmate" (W-manoeuvre / three phases).

## [2026-06-19] tool | _eval.king_free_region + render_king_net, minor_confine_state region metric, show_position net section, NEW chess__imagine_line | Visualisation + sub-goal tooling for minor mates. king_free_region = the squares the bare king can roam (the net); show_position renders it (`*`) in K+2B/K+B+N endings; minor_confine_state now ranks by net size (not the useless enemy-king corner-distance, since our move never moves their king); chess__imagine_line plays a whole agent-supplied line and reports the net trend per move (fair: agent-driven calculation, no search, names no move).

## [2026-07-01] create | openings/london-system + 4 situational pages | London System theory ingested
- Seeded the openings/ folder (was empty) with the London System repertoire, written as "what to do when..." pages so the agent retrieves the right one by situation (triggers-heavy frontmatter; search_wiki verified to land each query on its page). Sources: Wikipedia (London System, Greek gift sacrifice), thechessworld/365chess/modern-chess/chess.com guides; all example lines machine-verified in python-chess.
  - openings/london-system.md — hub: the setup (d4-Bf4-e3-Nf3-Bd3/Be2-c3-Nbd2-O-O) + the core Ne5 plan; routes to the situational pages.
  - openings/london-vs-qb6.md — meeting ...Qb6 on the loose b2-pawn. KEY CORRECTION (verified): the response is MOVE-ORDER DEPENDENT — Qb3 is only legal AFTER c3 is played; without c3, the answer is b3 / Qc1 / Nc3 (the earlier agent system-prompt's generic "Qc1 or Qb3" was wrong half the time).
  - openings/london-vs-kings-indian.md — vs ...g6/...Bg7: bishop to e2 (not d3), h3 early, meet ...e5/...c5.
  - openings/london-vs-nh5.md — vs ...Nh5 trading the f4-bishop: Bh2 (if h3 in) / Bg5 / allow ...Nxg3 hxg3 for the open h-file.
  - openings/london-bxh7-greek-gift.md — the Bxh7+ sac CHECKLIST (no Black Nf6, Ng5+ ready, queen reaches the h-file, control g5) + the main line; directly targets the agent's recurring premature-Bxh7+ blunder found in the Maia London review. WORK and FAIL example FENs verified.
- Registered all 5 in openings/index.md with one-line "when it applies" routing. Skill still parses (7 tools); related_pages links resolve.

## [2026-07-02] create | principles/calculate-against-best-defense.md | The "opponent plays THEIR best move" discipline — how to read imagine_line's new PROVEN/UNPROVEN/COUNT-NOT-SETTLED labels; written after 32/40 replayed blunder-overrides were justified by lines whose opponent replies the agent picked itself (Qxh7+ x6 games).

## [2026-07-02] update | openings/london-ne5-attack.md | Watch-out added: the h7 sac is the BISHOP's (Bxh7+), never Qxh7+?? — the attack-plan page kept being corrupted into a queen-first sac (6 games lost to it); points to principles/calculate-against-best-defense.

## [2026-07-02] update | principles/index.md | Registered calculate-against-best-defense.
