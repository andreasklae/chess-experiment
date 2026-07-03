# Tactics — Index

Concrete, calculable tactical patterns: short forcing ideas you can verify
with `chess__imagine_move`. Read here when something tactical is in the
air — a loose or undefended enemy piece, an exposed king, pieces lined up
on a file/diagonal, an overworked defender. (**Loose pieces drop off:** an
undefended enemy piece is the usual target that makes a tactic work — spot it
first, in [[positional/evaluate-position]].)

A **combination** strings these motifs into a *forced* sequence (often started by
a sacrifice) that wins by force against **any** defence — so it can be calculated
exactly. That is the whole game: find the motif, then verify the forced line.

## Pages

| Read this when… | Page |
|---|---|
| two enemy pieces (esp. K+Q, K+R) sit where one piece could hit both — a fork; or you must avoid being forked | [forks-and-double-attacks](forks-and-double-attacks.md) |
| pieces are lined up on a rank/file/diagonal — one can be pinned or skewered (for or against you) | [pins-and-skewers](pins-and-skewers.md) |
| a piece sits in front of your (or their) rook/bishop/queen — moving it unveils an attack or check (incl. double check, windmill) | [discovered-attacks](discovered-attacks.md) |
| a target is held by ONE defender — lure it away (deflection), to a bad square (decoy), overload it, or block its line (interference) | [removing-the-defender](removing-the-defender.md) |
| a mate or capture fails only because one enemy piece guards the key square — you want to remove that guard | [deflection](deflection.md) |
| the obvious line doesn't quite win — you need an in-between move (zwischenzug), desperado, clearance, X-ray, or to trap a piece | [more-motifs](more-motifs.md) |
| a pawn or piece looks free in the opening — is it bait? named opening traps and how to avoid them | [traps](traps.md) |

**The one test behind every tactic:** make two threats the opponent can't meet in
one move. When you spot a candidate, ask *"can they answer both?"* and confirm the
forced line with `chess__imagine_line` before committing.

## Routing

- It is forced mate, not just winning material → [`../mates/`](../mates/index.md).
- After spotting a candidate combination, **verify it with
  `chess__imagine_move`** before committing — the pattern tells you what to
  look for; the script confirms it works.
