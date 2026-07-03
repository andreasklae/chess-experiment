---
category: fundamentals
description: The checklist to run on EVERY move, in order — check threats, check your safety, then improve. Read this every turn; it is the thinking method, not theory.
triggers: [every move, what do I do, my turn, thinking method, checklist, where do I start, how to choose a move]
related_pages: [fundamentals/opening, fundamentals/middlegame, fundamentals/endgame, strategy/handle-a-threat, positional/evaluate-position]
tags: [fundamentals, checklist, thinking-method, every-move]
status: draft
updated: 2026-06-24
---

# The every-move checklist

Run this **every single move, in this order.** Do not skip to "my plan" before
the safety checks — most games are lost by ignoring the opponent's threat, not by
missing a deep plan. Use your tools (`chess__show_position`,
`chess__imagine_move`, `chess__imagine_line`) to answer each step with facts, not
guesses.

## 1. What did the opponent's last move do? (threats FIRST)
- Does it **attack** one of my pieces? (check the "under attack" list.)
- Does it **threaten mate**, a fork, a pin, a discovered attack next move?
- Did it stop something I was planning?
- If there is a real threat, I must answer it before anything else —
  [[strategy/handle-a-threat]].

## 2. Is my move safe? (don't blunder)
Before committing ANY move, check with `chess__imagine_move`:
- Does it **hang a piece** (leave it attacked and not defended / losing the
  exchange)? If so, don't play it unless it's a sound sacrifice with a forced
  follow-up.
- Does it walk into a **fork, pin, skewer, or discovered attack**?
- Does it expose **my king** or allow a check that wins material / mates?
- Does it let an enemy **pawn promote**?
> If a move fails any of these, find another — unless you've calculated that the
> material comes straight back or it's mate.

## 3. Do I have a tactic / forcing win? (checks, captures, threats)
Scan, in this order, for ME:
- **Checks** — any check that wins material or mates? (Look at every check.)
- **Captures** — any capture that wins material (verify the recapture nets out)?
- **Threats** — fork, pin, skewer, discovered attack, removing a defender,
  a mate threat? See [[tactics/index]]. A loose (undefended) enemy piece is the
  usual target.
- Verify any candidate with `chess__imagine_line`: can the opponent meet **both**
  my threats in one move? If not, it works.

## 4. If nothing forcing: improve the position
- Am I **up material**? → trade pieces, simplify, keep a rook/queen for mating
  ([[principles/material-and-trading]]).
- Is a **king exposed** (mine or theirs)? → defend / attack it
  ([[positional/king-safety]]).
- Otherwise → **improve your worst-placed piece**, fight for the centre, put a
  rook on an open file, a knight on an outpost
  ([[positional/evaluate-position]]).
- Follow your **standing plan** unless the board changed; if you have none, make
  one ([[strategy/make-a-plan]]).

## 5. Match the phase
- Opening → develop, centre, castle ([[fundamentals/opening]]).
- Middlegame → plan around the pawn structure, attack a weakness or the king
  ([[fundamentals/middlegame]]).
- Endgame → activate the king, push passed pawns ([[fundamentals/endgame]]).

**One-line summary to apply every move:** *answer their threat → make sure my
move doesn't blunder → look for my checks/captures/threats → else improve my
worst piece.*
