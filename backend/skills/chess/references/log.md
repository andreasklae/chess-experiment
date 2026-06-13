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
