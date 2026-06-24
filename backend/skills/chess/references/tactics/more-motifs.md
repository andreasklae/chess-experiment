---
category: tactics
description: The rest of the tactical toolkit — zwischenzug (in-between move), trapped piece, desperado, clearance, X-ray, and the unifying soundness test. Read to recognise the less-common devices that win material.
triggers: [zwischenzug, in-between move, intermezzo, desperado, clearance, x-ray, trapped piece, zugzwang, intermediate move, in between move]
related_pages: [tactics/index, tactics/removing-the-defender, tactics/discovered-attacks, principles/avoid-stalemate]
tags: [tactics, zwischenzug, desperado, clearance, x-ray, trapped-piece]
status: draft
updated: 2026-06-24
---

# More tactical motifs

## When to use
You're calculating and the "obvious" sequence doesn't quite win — one of these
less-common devices is often the missing idea. Also scan for them against you.

## The motifs
- **Zwischenzug (in-between move / intermezzo):** instead of the expected
  recapture/response, insert a MORE forcing move first (a check, or a threat to
  something bigger). The opponent must answer it; *then* you make the original
  move, having gained material or tempo. **Soundness:** the in-between move must be
  more forcing than what you're ignoring — if they can simply ignore it, it fails.
  Before you auto-recapture, always ask: *is there a stronger in-between move?*
- **Trapped piece:** an enemy piece has no safe square — a bishop that grabbed a
  wing pawn (e.g. …Bxh2 / Bxa2 lines), an over-extended queen, a knight on the rim.
  Attack it; it can't escape. **Check it's really trapped** — list its squares
  (none safe) before committing.
- **Desperado:** a piece that is lost anyway should **grab whatever it can** (or
  sell itself as dearly as possible) before it dies — take a pawn, a defender,
  anything, since it's gone regardless.
- **Clearance:** vacate a square or line — often by sacrifice — so a friendly
  piece can use it **with tempo**. (E.g. a pawn or piece steps aside, sometimes
  giving check, to open the path for the decisive piece.)
- **X-ray:** a line-piece's power acts *through* an enemy piece — it defends or
  attacks a square **beyond** an intervening piece, which matters after the
  intervening piece is captured (the defender "sees through" to recapture, or the
  attacker hits the piece behind once the front one moves).

## The one test behind all tactics
Every device above (and forks, pins, discoveries, removing-the-defender) wins by
the **same logic: make two threats the opponent can't meet in one move.** When you
spot a candidate, run the soundness test — *can they answer both?* — and confirm
the forced line with `chess__imagine_line`. If they have a single move that
parries everything (especially a zwischenzug check of their own), the combination
fails.

## Watch out for
- The opponent's **zwischenzug** is the most common reason your combination
  "loses a tempo" and fails — when you calculate a forced line, give them their
  checks and captures first, not just the cooperative reply.
- A "trapped" piece often has one saving resource (a counter-sac, a fork on the way
  out). Verify no escape before you spend moves trapping it.

## Examples
Zwischenzug: instead of recapturing a knight immediately, you play a check that
wins the enemy queen first, *then* recapture — two moves' worth of gain.
Desperado: both sides have a hanging piece; the one to move grabs an extra pawn
with its doomed piece before the mass exchange. See [[tactics/removing-the-defender]].
