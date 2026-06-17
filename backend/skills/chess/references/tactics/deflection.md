---
category: tactics
description: Force the one piece guarding a mating square (or key point) to leave or die — by capturing it, exchanging it, or giving a check it must answer. Sacrifices often pay here.
triggers: [defended mating square, sole defender, overloaded piece, remove the guard, back rank defended]
related_pages: [mates/back-rank-mate, mates/index]
tags: [tactic, deflection, sacrifice, middlegame]
status: draft
updated: 2026-06-10
---

# Deflection — removing the guard

## When to use

You have spotted a mate (or a big capture) that fails only because **one
enemy piece guards the key square**. Typical case: a back-rank mate stopped
by a single rook on the eighth rank.

## The idea

A piece that must guard a square is tied down. Attack it, capture it,
exchange it, or give it a second job it cannot also do (overloading). If it
is the *only* defender, you may sacrifice material to remove it — the mate
that follows outweighs anything you gave up.

## What to do

- Name the mating square and list its defenders with `chess__show_position`
  / `chess__imagine_move` (attacker–defender chains).
- If there is exactly one defender, look for: a capture of it, a check that
  forces it away, or a threat it must answer elsewhere.
- Count the material *after* the whole sequence, not after the first move —
  giving a queen for a forced mate is winning, not losing.
- Verify the final move reports `gives checkmate` in `chess__imagine_move`
  before committing the first sacrifice.

## Watch out for

- The defender may have a *second* defender behind it (x-ray). Re-check the
  chain after each imagined capture.
- If the mate is not forced after the sacrifice, you are just down material.
  No `gives checkmate` at the end of the line → don't start it.
- Your own back rank: while you hunt their king, confirm they have no
  one-move counter-mate (check "Opponent legal replies" for checks).

## Examples

`1r4k1/5ppp/8/8/8/8/2Q2PPP/2R3K1 w - - 0 1` — Black's rook on b8 is the
only piece that can cover c8. 1.Qc8+! Rxc8 2.Rxc8# — the queen deflects by
forcing the recapture; the rook recaptures into the mate. Verified.
A king can be deflected too: see Example 11 in
`raw/chess-fundamentals-capablanca.md` (queen sacrifice on h7 drags the king
onto the h-file for a rook-lift mate).
