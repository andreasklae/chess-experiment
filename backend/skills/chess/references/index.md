# Chess Knowledge Wiki — Index

Your accumulated chess knowledge, in topic folders. **Pick the ONE folder
that matches the position, open its index, then read the one page that
fits.** Reading the wrong page wastes tokens; the indexes below tell you
exactly what each folder holds so you can route in one hop.

## How to navigate

1. You have already run `chess__show_position` — use its phase, material,
   and what-is-attacked to pick a folder below.
2. Open that folder's index:
   `read_reference(skill_name="chess", path="<folder>/index.md")`. Each
   index lists its pages with a one-line "read this when…" so you can pick
   the right page without opening several.
3. Read the one page that fits:
   `read_reference(skill_name="chess", path="<folder>/<page>.md")`.
4. If you know a concept's name but not its folder, call
   `chess__search_wiki(args=["<keywords>"])` — it returns matching pages
   with the exact `read_reference` call.

## The folders — route by what the position needs

| If the position is… | open this folder |
|---|---|
| **the enemy king is matable** — you can force or are hunting checkmate (basic K+Q / K+R / K+2R drills AND named mating nets like back-rank, smothered) | [`mates/`](mates/index.md) |
| **a tactic is in the air** — a loose piece, an overworked defender, a combination to win material | [`tactics/`](tactics/index.md) |
| **few pieces left, no immediate mate** — king-and-pawn play, promotion, opposition | [`endgames/`](endgames/index.md) |
| **you need a rule-of-thumb / sanity check** on a move | [`principles/`](principles/index.md) |
| **you need a PLAN** — quiet position, "what am I trying to do here?", converting an advantage | [`strategy/`](strategy/index.md) |

*(Folders for openings and per-game analyses exist but have no pages yet —
they are added by ingestion and post-game review.)*

## When NOT to look anything up

If the move is obvious — a free capture, a `checkmate` flagged by
`chess__list_legal_moves`, an only-move, a single clear answer to a
threat — just play it. The wiki is for when you need a plan or a technique,
not for every turn.

---
*Structure and maintenance: this wiki has at most one level of subfolders;
each folder index lists its own pages. You read these pages; the tutor
maintains them. See
`../../../../../../knowledge-base/decisions/2026-06-17-wiki-basic-mates-restructure.md`.*
