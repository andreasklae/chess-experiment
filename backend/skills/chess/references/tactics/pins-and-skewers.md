---
category: tactics
description: Pins and skewers — line attacks that freeze or win a piece. Pile attackers on a pinned piece (it can't run), and remember a pinned defender defends NOTHING. Includes how a pin breaks and the soundness check.
triggers: [pin, pinned, absolute pin, relative pin, skewer, x-ray, piece cant move, pile on pinned piece, pinned defender, break the pin]
related_pages: [tactics/index, tactics/forks-and-double-attacks, tactics/discovered-attacks, tactics/removing-the-defender]
tags: [tactics, pin, skewer, motif, line-piece]
status: draft
updated: 2026-06-24
---

# Pins and skewers

## When to use
A rook/bishop/queen lines up against two enemy pieces on one rank, file, or
diagonal — or the opponent lines up against two of yours. Scan for these every
move, both directions.

## The idea
- **Pin:** a piece can't (or shouldn't) move because a more valuable piece sits
  behind it on the line. **Absolute pin** = pinned against the king (moving is
  *illegal*). **Relative pin** = against a more valuable piece (legal to move, but
  loses material).
- **Skewer:** the reverse — the **more** valuable piece is in front, attacked;
  when it moves, the lesser piece behind falls.

## What to do
**Exploiting a pin (the two real weapons):**
1. **Pile MORE attackers onto the pinned piece.** It can't run, so add a pawn or
   another piece and win it outright — attacking a pinned piece with a pawn is the
   classic way to win it.
2. **A pinned piece defends NOTHING.** Whatever it was guarding is effectively
   undefended — so attack *that* target, or play the tactic the pinned piece was
   preventing. (A pinned knight that "covers" a mating square doesn't really cover
   it.) This is one of the most-missed ideas in chess; check it every time you
   see a pin.

**Exploiting a skewer:** line up against the valuable piece; when it moves off
the line, capture the lesser piece behind it.

**Defending against a pin/skewer on you:**
- **Break the pin:** block the line with another piece, move the *rear* (pinned-to)
  piece off the line, or challenge/trade the pinning piece.
- Don't rely on a **pinned piece as a defender** — see above, it isn't really
  defending. Add a *different* defender instead ([[tactics/removing-the-defender]]).

## Soundness check
- **A skewer only wins if the FRONT piece is actually FORCED to move.** It is
  forced only when leaving it there costs its owner material — i.e. the front piece
  is **undefended (loose)**, or **worth MORE than your attacking piece**. If the
  front piece is **defended AND worth ≤ your attacker, it is NOT forced**: your
  "skewer" wins nothing, because capturing it would just lose you material. Example
  of the trap: your **queen** "skewers" a **defended rook** with a bishop behind it
  — but Q(9)-takes-R(5) is met by a recapture, so the rook is happy to sit; the
  bishop behind is never exposed. The same rule applies to **forks** and any
  attack: hitting a defended piece worth less than the attacker is not a real
  threat. Check the front piece's defenders and value BEFORE playing the "skewer".
- A **relative** pin can break: the pinned piece may legally move *with a
  counter-threat or check* that saves it. Before counting a relative pin as a win,
  confirm the pinned piece can't wriggle out with tempo (`chess__imagine_move`).
- An **absolute** pin (against the king) is rock-solid — that piece truly cannot
  move — so piling on it, or exploiting that it guards nothing, always works if you
  have a free attacker.

## Watch out for
- The "pinned defender defends nothing" idea cuts BOTH ways — if one of YOUR
  defenders is pinned, the thing it guards is hanging. The blunder gate may not
  see this; check it yourself.
- Adding an attacker to a relatively-pinned piece backfires if the pin breaks with
  a check — calculate the line.

## Examples
Bishop g5 pins Black's Nf6 to the queen on d8 → play **e5** or **h4-h5** to pile
on the knight (it can't move); meanwhile the pinned Nf6 no longer guards e4/d5/h5,
so tactics on those squares are open. See [[tactics/discovered-attacks]] and
[[tactics/removing-the-defender]].
