# Tactics — Index

Concrete, calculable tactical patterns: short forcing ideas you can verify
with `chess__imagine_move`. Read here when something tactical is in the
air — a loose or undefended enemy piece, an exposed king, pieces lined up
on a file/diagonal, an overworked defender.

## Pages

| Read this when… | Page |
|---|---|
| a mate or capture fails only because one enemy piece guards the key square — you want to remove that guard | [deflection](deflection.md) |

*(Forks, pins, skewers, discovered attacks, and overloading are added by
ingestion later.)*

## Routing

- It is forced mate, not just winning material → [`../mates/`](../mates/index.md).
- After spotting a candidate combination, **verify it with
  `chess__imagine_move`** before committing — the pattern tells you what to
  look for; the script confirms it works.
