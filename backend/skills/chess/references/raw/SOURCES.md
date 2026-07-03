# Raw sources — provenance & licensing

Every external source the chess wiki is built from, with its license. The wiki
pages (`../*/*.md`) synthesise these in our own words; this folder holds the
**verbatim sources** so every claim is traceable and the ingestion is auditable
for the thesis. **Only public-domain or freely-licensed (CC) full text is stored
verbatim here** — no copyrighted material is reproduced.

## Books (public domain — full verbatim text)

| File | Work | License | Source |
|---|---|---|---|
| `capablanca-chess-fundamentals-GUTENBERG-33870.txt` | Capablanca, *Chess Fundamentals* (1921) | Public domain | Project Gutenberg #33870 |
| `Chess Fundamentals_.pdf` | same, original scanned PDF (diagrams) | Public domain | (same work) |
| `edward-lasker-chess-strategy-GUTENBERG-5614.txt` | Edward Lasker, *Chess Strategy* (1915, tr. Du Mont) | Public domain | Project Gutenberg #5614 |
| `edward-lasker-chess-and-checkers-GUTENBERG-4913.txt` | Edward Lasker, *Chess and Checkers: The Way to Mastership* | Public domain | Project Gutenberg #4913 |
| `blue-book-of-chess-GUTENBERG-16377.txt` | *The Blue Book of Chess* (rudiments + openings) | Public domain | Project Gutenberg #16377 |

## Encyclopedia (CC BY-SA 4.0 — verbatim plain-text extracts via MediaWiki API)

Retrieved 2026-06-24. All under Wikipedia's CC BY-SA 4.0.

- `wikipedia-pawn-structure.md`, `wikipedia-chess-strategy.md`,
  `wikipedia-glossary-of-chess.md`, `wikipedia-chess-opening.md`,
  `wikipedia-chess-tactic.md`, `wikipedia-combination.md`
- Motifs: `wikipedia-fork.md`, `wikipedia-pin.md`, `wikipedia-skewer.md`,
  `wikipedia-discovered-attack.md`, `wikipedia-deflection.md`,
  `wikipedia-decoy.md`, `wikipedia-interference.md`, `wikipedia-overloading.md`,
  `wikipedia-windmill.md`, `wikipedia-zwischenzug.md`, `wikipedia-xray.md`,
  `wikipedia-battery.md`, `wikipedia-zugzwang.md`
- Structure/traps: `wikipedia-isolated-pawn.md`, `wikipedia-passed-pawn.md`,
  `wikipedia-outpost.md`, `wikipedia-list-of-chess-traps.md`,
  `wikipedia-legal-trap.md`
- `checkmate-wikipedia.md`, `checkmate-patterns-wikipedia.md` (earlier pass)

## Open content

| File | Source | License |
|---|---|---|
| `lichess-practice-curriculum.md` | lichess.org/practice study index | Lichess open-source (AGPL); free content |

## Synthesis digests (our own notes, NOT verbatim sources)

These are paraphrased reading notes, kept as quick digests. The verbatim
sources above are authoritative; these are convenience summaries.

- `capablanca-positional-extract.md` — digest of the Capablanca strategy chapters
  (verbatim: the `-GUTENBERG-33870.txt`).
- `edward-lasker-chess-strategy-extract.md` — digest of key Lasker maxims
  (verbatim: the `-GUTENBERG-5614.txt`).
- `positional-concepts.md` — consolidated positional taxonomy (detect → handle),
  drawn from the Wikipedia sources above + the books.
- `tactics-mechanics.md` — consolidated tactical mechanics + soundness tests,
  drawn from the Wikipedia motif articles + Lichess + the books.

## Puzzle benchmark curriculum (open content)

| File | Source | License |
|---|---|---|
| `lichess-puzzle-themes.md` | Lichess puzzle theme definitions (lila i18n `puzzleTheme.xml`) | lichess.org AGPL; free content |

The official one-line definitions Lichess uses to tag puzzles — the same theme
tags the agent puzzle benchmark (`experiments/puzzle-benchmark/`) selects on.
Used to align/sharpen the wiki tactic-page descriptions and `triggers` so the
agent's `search_wiki` matches the motif vocabulary. Retrieved 2026-06-25.

## London System curriculum (read-and-note web synthesis, 2026-07-01)

| File | Sources consulted | License / handling |
|---|---|---|
| `london-system-notes.md` | chessdoctrine.com, chess-teacher.com, modern-chess.com, 365chess.com, thechessworld.com London guides; Wikipedia *London System* | **Copyrighted web guides — read-and-note only.** No verbatim text stored; only non-copyrightable facts (move orders, plans, which model games exist) restated in our own words. Every concrete line re-verified in python-chess before entering a wiki page. |

Named books consulted for *what exists* but **NOT reproduced** (copyright): GM Nikola
Sedlak, *The London System: The Adventure Continues*; GM Baadur Jobava's London
courses. Only the fact of their existence and the plans they teach (uncopyrightable)
informed the notes; no text was copied. This is the readable-and-notable path the
[[tool-fairness]] rulebook allows.

**Correction caught during verification (why re-checking matters):** an early draft of
`openings/london-vs-qb6.md` gave the dxc5 gambit as "dxc5 Qxb2 **Rb1** Qc3+", but Rb1
is *illegal* while the b1-knight is home. Corrected to the real lines (Nd2 after dxc5;
or the Nc3→Nb5 gambit in the ...c5-early move order). Sources state plans loosely; the
board is the authority.


## King-safety / defence curriculum (read-and-note web synthesis, 2026-07-01)

| Wiki page | Sources consulted | Handling |
|---|---|---|
| `positional/defending-the-king.md` (new), `positional/king-safety.md` (extended) | chessfox.com "Keep the king safe", chess.com forums/lessons on defending king attacks, general defensive-technique guides | **Read-and-note only** — non-copyrightable defensive principles (trade the attackers/queen, block checks, retreat to your army, distinguish real vs spite checks, luft) restated in our own words. Paired with the new `detect_own_king_exposure` radar signal so the tool that flags the danger routes to the page that says how to survive it.

## Diagram handling (point made explicit)

The `wikipedia-*.md` files store the article text **with every position diagram
inlined as FEN + ASCII grid** (the representation `chess__show_position` uses),
reconstructed losslessly from the article's `{{Chess diagram}}` wikitext and
**verified in python-chess** (116 positions, 0 invalid). Composed position images
/ photos are downloaded to `images/`. Converter:
`experiments/board-visualization-benchmark/lib/wiki_diagram_md.py`.

The composed images in `images/` (which are rendered pictures, not templates)
were **OCR'd by reading the image into FEN + grid**, validated in python-chess,
in `images/diagram-images-as-fen.md` (3 positions; the low-res GIF's pawn squares
are approximate, piece geometry exact).

## Rejected sources (copyright — checked, NOT included)

Found in Wikipedia "Further reading / External links" but **not public domain**,
so deliberately excluded: the archive.org endgame books `How to Play the Endgame`
(1975), `Six Hundred Endings` (1980), `Winning Chess Endgames` (2005), `Knight
Endings` (1977) — all post-1929, archived-but-copyrighted. Also all modern cited
books (Watson, Seirawan, Silman, Nunn, etc.). Being *on* archive.org does not make
a work public domain; only pre-1929 / PD-flagged works were pulled.

## Note on non-public-domain material

Facts and mechanics (which side a fork favours, how a windmill works) are not
copyrightable and are synthesised freely. Proprietary sites (chess.com lessons,
modern book editions) were **not** reproduced; where consulted, only
non-copyrightable facts were used, restated in our own words. No pirated or
paywalled text is stored in this repository.
