---
category: tactics
description: Named opening traps and the universal lesson behind them — a "free" pawn or piece in the opening is often bait. How the Legal, Noah's Ark, Fishing Pole, and Elephant traps work, and how to avoid falling in.
triggers: [trap, opening trap, free pawn, is this a trap, bait, poisoned pawn, Legal trap, Noah's ark, fishing pole, premature pin, dont take]
related_pages: [tactics/index, tactics/discovered-attacks, principles/opening-principles, tactics/forks-and-double-attacks]
tags: [tactics, traps, opening, poisoned-pawn]
status: draft
updated: 2026-06-24
---

# Traps — and how not to fall for them

## When to use
The opponent leaves a pawn or piece apparently free to take, especially in the
opening. **A trap is a move that tempts you into a losing reply.** Before grabbing
material, ask the universal question: **"what does taking this let them do?"**

## The universal lesson
Most traps work because the victim grabs material and ignores a tactical follow-up
(a discovered attack, a fork, a mating net, or their own piece getting trapped).
The defence is always the same: when something looks free in the opening, **run
the soundness test on the opponent's reply before you take.** A real free pawn is
rare; bait is common.

## Named traps (the idea, not just the moves)
- **Légal Trap** (Italian/Philidor): punishes a **premature pin**. After
  1.e4 e5 2.Nf3 Nc6 3.Bc4 d6 4.Nc3 Bg4 5.h3 Bh5, White plays **6.Nxe5!** — the
  pin is *illusory*. If Black grabs the queen **6…Bxd1?? 7.Bxf7+ Ke7 8.Nd5#** is
  mate (verified). Device: a mating net beats the queen-win. **Avoid:** don't take
  the queen — play 6…Nxe5 and you're fine.
- **Noah's Ark Trap** (Ruy Lopez): Black's queenside pawns (…a6, …b5, …c4) roll up
  and **trap White's light-squared bishop**. Device: trapped piece. Avoid: don't
  let the bishop get fenced in by the advancing pawn chain.
- **Fishing Pole Trap** (Ruy Lopez): Black dangles a knight on g4; if White takes
  **hxg4?**, then **…Bxg4** and the opened h-file feeds a mating attack. Device:
  deflection / opening lines to the king. Avoid: don't grab the g4 knight with the
  h-pawn.
- **Elephant / Rubinstein Traps** (Queen's Gambit Declined): exploit a **pinned or
  overloaded defender** to win material when the victim plays a natural-looking
  capture. Device: pin + removing-the-defender.
- **Lasker Trap** (Albin): features an early **underpromotion to a knight** — a
  reminder that promotion isn't always to a queen.

## What to do
- **Setting a trap (fairly):** a trap is only good if it **doesn't weaken your own
  position** — if the opponent sees through it, it should cost you nothing. Don't
  contort your game to bait a weak move.
- **Avoiding a trap:** the moment a capture looks free in the opening, calculate
  the opponent's most forcing reply (check, recapture, discovery) with
  `chess__imagine_line`. If grabbing the material lets them check/fork/trap you,
  decline it and just develop ([[principles/opening-principles]]).

## Watch out for
- The agent's standing weakness is grabbing material that's lost right back — traps
  are the opening version of that. Treat a free central pawn in the opening as
  *suspicious by default*.
- "Poisoned" pawns (e.g. the b2-pawn for the queen) often trap the grabbing piece
  — count the escape squares before taking.

## Examples
See the Légal line above (verified mate). General drill: opponent leaves e5 or a
b-pawn free → before taking, list their checks and captures next move; if one wins,
it's a trap. See [[tactics/discovered-attacks]] and [[tactics/forks-and-double-attacks]].
