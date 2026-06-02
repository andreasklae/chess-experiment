# Patterns — Index

Concrete, calculable tactical patterns: forks, pins, skewers, discovered
attacks, double attacks, deflection, overloading, trapped pieces, and the
like. These are short forcing ideas you can verify with `imagine_move`.

**Read a page here when:** something tactical is in the air — a loose or
undefended enemy piece, an exposed king, pieces lined up on a file/diagonal,
an overworked defender. If you suspect a tactic but can't name it, call
`chess__search_wiki(args=["<what you see>"])`.

## Pages

_(none yet.)_

| Page | When it applies | Read with |
|------|-----------------|-----------|
| _(none yet)_ | _—_ | _—_ |

## Subfolders

- [`mating-patterns/`](mating-patterns/index.md) — checkmating patterns
  when the enemy king is exposed (back-rank, smothered, ladder/box, common
  mating nets).

## Routing

- It looks like forced mate, not just a tactic → [`mating-patterns/`](mating-patterns/index.md).
- After spotting a candidate combination, **verify it with `imagine_move`**
  before committing — the pattern tells you what to look for; the script
  confirms it works.
