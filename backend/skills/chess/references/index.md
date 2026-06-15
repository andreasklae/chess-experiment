# Chess Knowledge Wiki — Index

This is your accumulated chess knowledge. **Read this page to decide where
to look, then read at most one or two pages — don't read everything.** Each
folder has its own `index.md` that routes one level deeper. Pages are short
by design; the cost of reading the wrong one is wasted tokens, so route
deliberately.

## How to navigate

1. You have already run `chess__show_position`. Use what it told you — the
   phase (opening / middlegame / endgame), the material balance, what is
   under attack — to pick a folder below.
2. Read that folder's index with
   `read_reference(skill_name="chess", path="<folder>/index.md")`. It lists
   its pages with a one-line description and the board conditions that make
   each relevant.
3. Read the one page that fits with
   `read_reference(skill_name="chess", path="<path>")`. Follow a
   `[[wikilink]]` only if it is clearly relevant to *this* position.
4. If you know the name of a concept but not where it lives, call
   `chess__search_wiki(args=["<keywords>"])` — it returns matching pages'
   paths, descriptions, and tags (not their bodies), each with the exact
   `read_reference` call to open it.

The wiki is reached two ways: **`chess__search_wiki`** (find pages by
keyword → returns frontmatter + the read_reference call) and
**`read_reference`** (read one page → returns its body). You are reading
this index via `read_reference(skill_name="chess", path="index.md")` now.

## Route by what the position needs

- **Opening unclear, or you're in the first ~10 moves** → [`openings/`](openings/index.md)
- **You need a rule of thumb / sanity check on a move** → [`principles/`](principles/index.md)
- **You need a plan — what should I be trying to do here?** → [`strategic-thinking/`](strategic-thinking/index.md)
  - pawn-structure questions (isolated / passed / doubled pawns, chains) live under [`strategic-thinking/pawn-structures/`](strategic-thinking/pawn-structures/index.md)
- **There's a tactic in the air (loose piece, exposed king, pin, fork)** → [`patterns/`](patterns/index.md)
  - **the enemy king looks exposed and you may be able to mate** → [`patterns/mating-patterns/`](patterns/mating-patterns/index.md)
- **Few pieces left on the board** → [`endgames/`](endgames/index.md)
- **Reviewing a finished game** (post-game only) → [`game-analyses/`](game-analyses/index.md)

## When NOT to look anything up

If the move is obvious (a free capture, a forced mate flagged by
`list_legal_moves`, an only-move), just play it. The wiki is for when you
need a plan or a check, not for every turn.

---
*Folders, page contract, and how this wiki is maintained:
`../../../../../../knowledge-base/decisions/2026-06-02-chess-agent-wiki-architecture.md`.
You read these pages; the tutor maintains them.*
