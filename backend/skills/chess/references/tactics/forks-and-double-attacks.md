---
category: tactics
description: Forks and double attacks — one piece hitting two targets at once (knight forks of K+Q, K+R are deadliest). How to spot one you can play and one threatened against you, current vs potential, plus the soundness test.
triggers: [fork, double attack, knight fork, family fork, two pieces attacked, fork square, can be forked, loose pieces, royal fork]
related_pages: [tactics/index, tactics/pins-and-skewers, tactics/discovered-attacks, strategy/handle-a-threat]
tags: [tactics, fork, double-attack, knight, motif]
status: draft
updated: 2026-06-24
---

# Forks and double attacks

## When to use
Two enemy targets sit near each other, or two of *your* pieces a single enemy
move could hit. Check forks **both directions every move** — one you can play, one
threatened against you.

## The idea
A **fork / double attack** is one piece attacking two+ targets at once; only one
can be saved. The **knight fork** is deadliest — a knight can't be blocked and
strikes in two directions; landing on a square that hits **K+Q** (royal fork),
K+R, or two pieces wins material outright. Queens, bishops, rooks and even pawns
fork too (a pawn pushing to hit two pieces is a common, cheap winner).

The fuel is **loose (undefended) pieces** — "loose pieces drop off." Two
undefended pieces, or a piece sitting near its king, invite a double attack.

Distinguish two states (your tools flag both):
- **Currently threatened** — the fork can be played *now*.
- **Potential** — it would be a fork if the piece could reach the square safely
  (the square is defended, or the piece can't get there yet). A potential fork is
  a **warning**: defend the square or move a target before it becomes real.

## What to do
**Finding your fork:**
- Look for a square a knight can reach that attacks two valuable enemy pieces.
- For Q/R/B double attacks: a square from which the piece hits two loose pieces,
  or a piece + a mate threat.

**SOUNDNESS TEST** — a fork wins unless the opponent can, in one move:
1. **capture the forking piece** (is your fork square defended?), or
2. **move one target with tempo** — a check or a bigger counter-threat that saves
   both, or
3. the second "target" is defended/not worth winning.
A fork that **gives check** is almost always sound: the checked side must answer
the check and cannot use the move to save the other piece. Verify with
`chess__imagine_move`.

**Defending against theirs:**
- Spot the fork square *before* they reach it; control it, or move a target off
  the fork lines, or keep your pieces defended (no loose pieces).
- A king + queen (or king + rook) on knight-fork geometry is the classic warning —
  relocate one.

## Watch out for
- Don't leave two pieces undefended on squares a knight can jump to.
- "Winning" a defended piece by a fork only works if the fork also checks or hits
  the king (so they can't recapture) — otherwise count the trade.

## Examples
Black Kg8 + Rf8: a white knight reaching **e7+** or **h6+** forks king and rook —
if the square is safe (or it's check), it wins the exchange. See
[[strategy/handle-a-threat]] for the general "two pieces attacked" response.
