---
category: openings
description: The Bxh7+ "Greek gift" bishop sacrifice (the London's main attacking weapon with Bd3). RECOGNISE the pattern — when the checklist is met it is often winning, so calculate it; when it is not, it just loses a bishop.
triggers: [Bxh7, Bxh7+, greek gift, bishop sacrifice h7, sac on h7, Bd3 points at h7, sacrifice bishop for attack, kingside attack sacrifice, should I sacrifice on h7, Ng5 attack, Qh5 mate attack, london attack, attack the castled king, my bishop aims at h7]
related_pages: [openings/london-system, openings/london-ne5-attack, positional/king-safety, tactics/index, mates/index]
tags: [opening, london, sacrifice, greek-gift, attack, Bxh7, tactics]
status: draft
updated: 2026-07-01
---

# The Bxh7+ Greek-gift sacrifice (recognise it, then calculate it)

## When to use
Your bishop is on **d3** (or b1), pointing down the b1–h7 diagonal at Black's **h7**,
and Black has **castled kingside**. This is the London's signature attack — **when the
checklist below is met, Bxh7+ is often WINNING, so you must calculate it, not avoid
it.** The mistake goes both ways: sacrificing when a condition fails loses a bishop, but
**declining it when the conditions ARE met throws away a won game** (a quiet f4/Qg3
lets Black consolidate). So: recognise the pattern → run the checklist → if it passes,
calculate the line to the end and play the sac.

## Recognise the pattern (all present → CALCULATE the sac now)
- your **bishop bears on h7** (Bd3/Bb1, nothing blocking d3–h7),
- Black's king is on **g8** and **h7 is defended only by the king** (no ...g6, no
  piece guarding h7),
- Black has **NO knight on f6** (usually because your **pawn or knight on e5** removed
  or blocked it),
- your **knight is ready to jump to g5 with check** (a knight on f3), and
- your **queen can reach the h-file in one move** (Qd1–h5, or a queen already near).
When you see this, do NOT play a slow move — go straight to `imagine_line`.

## The idea — the win is a forced king hunt
The point is **Bxh7+ Kxh7 Ng5+** (the knight comes with check), then your **queen
reaches the h-file** (Qh5/Qd1–h5) for mate. You give a bishop to strip the king and
bring the knight + queen with tempo.

Extra condition when Black has a bishop on **e7**: you usually also need a **pawn on h4**
(to meet ...Kg6 with h5+). Once the pattern is present, **calculate to the end with
imagine_line** (Bxh7+ Kxh7 Ng5+ and EACH king reply) — confirm mate/decisive attack,
then play it.

## The main line (king's three replies after Bxh7+ Kxh7 Ng5+)
- **...Kg8** → **Qh5**, threatening Qh7#. ...Qxg5 loses to Bxg5; ...Re8 loses to Qxf7+.
- **...Kg6** → the CRITICAL test, and usually the REFUTATION if you're not ready. **h4**
  intends h5+, but this WINS only if (a) your **Ng5 is defended** (e.g. by the f4/g3-bishop
  or a pawn) so Black can't consolidate, AND (b) a **queen check (Qd3+/Qg4/Qh5+) arrives
  with real force**. If Ng5 hangs and your queen check just gets parried by ...f5/...Kf5,
  the king walks out and you are simply **down a piece** — DON'T assume "h4 wins", CALCULATE
  ...Kg6 to a real mate/queen-win with `imagine_line` or the sac fails.
- **...Kh6** → **Nxf7+** wins the queen — but only if it actually forks/checks; verify.

## Watch out for
- **The ...Kg6 escape is how a "sound-looking" sac actually LOSES.** Real games (batch-3,
  4 lost games): the conditions above (no Nf6, Bd3, Nf3, Qd1) were ALL met, so it looked
  sound — but after Bxh7+ Kxh7 Ng5+ **...Kg6** the knight was undefended, "h4" did not win,
  and White was down a bishop for nothing. **The checklist is necessary, NOT sufficient:**
  you MUST calculate ...Kg6 (and ...Kf8) to a forced win, and TRUST the imagine_line leaf
  verdict — if it says "you end down material, not mate", the sac is bad even if the pattern
  looks perfect. Do not talk yourself past the tool.
- **It fails if Black has a knight on f6** (Nf6 guards h7 and g5): Bxh7+ Nxh7 and you are
  down a bishop. Check f6 FIRST — but note e5 (pawn/knight) usually removes it.
- **The opposite error, and the one seen in real games: DECLINING a sound sac.** If the
  pattern is present and you play a quiet f4/Qg3/Qh3 instead, you let Black off. When the
  conditions hold, the sac is the move — calculate it, don't chicken out.
- If the queen can't reach the h-file fast, the attack stalls — then build first (Ne5,
  Qf3/Qh5, Rf1–f3–h3, h4–h5) until the conditions appear (see `openings/london-ne5-attack`).

## Examples (verified)
- **Sac WORKS:** `r1bq1rk1/pppn1ppp/3bp3/3pP3/3P4/3B1N2/PPP2PPP/RNBQ1RK1 w` — no Black
  Nf6, h7 only king-defended, e5-pawn present, Nf3 ready for g5, Qd1 for h5: **Bxh7+
  Kxh7 Ng5+ Kg8 Qh5** with a winning attack.
- **Sac FAILS:** the same position but with a Black **knight on f6** — Bxh7+ Nxh7 and
  White is just down a bishop.
- **Model London game (Kamsky–Shankland 2014):** 1.d4 Nf6 2.Bf4 d5 3.e3 e6 4.Nd2 c5
  5.c3 Nc6 6.Ngf3 Bd6 7.Bg3 O-O 8.Bd3 Qe7 **9.Ne5** (the outpost — see
  `openings/london-ne5-attack`), and later **Bxh7+ Kxh7 Qh5+ Kg8 Ne4** broke through.
  The Ne5 plan is what *creates* the Greek-gift conditions.
