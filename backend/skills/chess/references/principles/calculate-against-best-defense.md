---
category: principles
description: A sacrifice or combination is only sound if it works against the opponent's BEST reply at every step — a line where you picked their replies is hope, not calculation. How to prove a line with imagine_line.
triggers: [sacrifice, sac, calculated line, forced line, combination, confirm, override, safety check, queen sacrifice, unsound, refutation, best defense, forced mate, proven line, i win material]
related_pages: [openings/london-bxh7-greek-gift, fundamentals/every-move-checklist, principles/material-and-trading]
tags: [calculation, sacrifice, discipline, forcing-moves]
status: draft
updated: 2026-07-02
---

# Calculate against the best defense

## When to use
Every time a line you calculated says "I win material" or "I mate" — **especially**
before you override a SAFETY CHECK with `confirm=true`, and always before a
sacrifice (any move that loses material at one ply).

## The idea
Your opponent plays **their** best move, not the reply your plan needs. A
combination that wins after one cooperative reply and loses after the others is
not a combination — it is a blunder wearing one. Most lost games in our history
came from exactly this: a confident line whose opponent replies were hand-picked
(6 games lost to Qxh7+ alone).

## What to do
1. Calculate the line with `chess__imagine_line`, one move at a time.
2. Read the verdict's labels, and believe them:
   - **PROVEN** — every opponent reply was forced and the final position is
     quiet. You may play the line, and `confirm=true` is justified.
   - **UNPROVEN / "you PICKED the opponent's replies"** — the verdict names the
     step and the testing alternatives. Re-run the line with **each**
     alternative. The line is sound only when **every** branch still wins.
   - **COUNT NOT SETTLED** — your last piece can be recaptured; the material
     count is mid-exchange. Extend the line through the recapture first.
3. When a check has several legal replies, test the **most testing** ones first:
   captures of your checking piece, king moves that *attack* your pieces, and
   blocks. A king stepping toward your knight often refutes the whole idea.
4. If even one alternative refutes the line: **backtrack and pick a safe move.**
   Declining an unsound sacrifice costs nothing; playing it costs the game.

## Watch out for
- "The follow-up fork wins the queen back" — only if the king goes where you
  need it. Count the king's legal squares; you must win against **all** of them.
- A one-ply-forced start (only one recapture) does not make the *rest* forced.
- Never let a plan's momentum decide. The plan said "attack h7"; the board
  decides **whether the sac works today**.
