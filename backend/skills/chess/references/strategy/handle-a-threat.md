---
category: strategy
description: A decision procedure for when one of your pieces is attacked or under threat — capture, defend, move, counter-threat, or check. Calculate the candidate lines; don't just recapture on reflex.
triggers: [piece attacked, under attack, hanging, threatened, my bishop is attacked, my knight is attacked, save my piece, defend, threat, what do I do about the threat]
related_pages: [positional/king-safety, tactics/index, tactics/more-motifs, strategy/make-a-plan, positional/evaluate-position]
tags: [strategy, defense, threats, calculation, thinking-method]
status: draft
updated: 2026-06-24
---

# Handle a threat — your piece is attacked

## When to use
The opponent's last move attacks one of your pieces (or threatens something
worse). `show_position` / `imagine_move` will tell you *what* is attacked and by
how many; this page is *how to respond*. Don't reflex-recapture or reflex-retreat
— run the options.

## The idea
When a piece of yours is attacked and would be lost, there are **five** kinds of
reply. Consider them in this order and calculate the lines:

1. **Capture the attacker** — can you take the attacking piece favourably?
2. **Defend it** — add a defender so capturing loses *them* material. (Not if the
   piece is pinned or also forked — then defending doesn't save it.)
3. **Move it** — to a square that is safe (not attacked, or defended). Check the
   move doesn't open a **discovered attack** on something else of yours.
4. **Counter-threat** — make a **bigger** threat (attack a more valuable piece,
   or threaten mate) so they must deal with that instead of capturing. When you
   were "supposed" to recapture but insert a more forcing move first, that is a
   **zwischenzug** (in-between move) — see [[tactics/more-motifs]].
5. **Check** — a check forces their reply and can win a tempo to save the piece
   or grab the attacker.

## What to do
- For each viable option, **imagine the line a few moves deep** — especially that
  the opponent's *best* reply, not the one you hope for. Use `imagine_move` /
  `imagine_line`.
- **Evaluate and pick the safest strong move.** Saving the piece while keeping the
  initiative beats saving it passively.
- **Don't bother "threatening" a piece that can just step away for free** — only
  threats that win material or force a real concession count.
- If multiple of your pieces are attacked at once, prioritise saving the most
  valuable, or find the one move (a fork-escape, a counter-check) that saves both.

## Watch out for
- A "safe" retreat square can lose to a **discovered attack** or a follow-up
  fork — verify the whole move with `imagine_move`, which flags newly-hanging
  pieces.
- Defending a pinned piece doesn't help — the pin means it can't be the defender
  that matters. Break the pin instead (block, or move the pinned-to piece).
- Don't give up the initiative to save a pawn; sometimes the best answer is to
  ignore a small threat and make a bigger one.

## Examples
Bishop attacked and undefended → (1) is the attacker takeable? (2) any check that
wins it? (3) safe squares where the bishop is defended or unattacked? (4) a
bigger counter-threat? Calculate each non-losing option, pick the safest and
strongest. King in trouble instead of a single piece → [[positional/king-safety]].
