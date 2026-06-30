---
category: openings
description: The Bxh7+ "Greek gift" bishop sacrifice (common in the London with Bd3). It WINS only under strict conditions; play it otherwise and you just lose a bishop. The exact checklist for when it works.
triggers: [Bxh7, Bxh7+, greek gift, bishop sacrifice h7, sac on h7, Bd3 points at h7, sacrifice bishop for attack, kingside attack sacrifice, should I sacrifice on h7, Ng5 attack, Qh5 mate attack, london attack]
related_pages: [openings/london-system, positional/king-safety, tactics/index, mates/index]
tags: [opening, london, sacrifice, greek-gift, attack, Bxh7, tactics]
status: draft
updated: 2026-07-01
---

# The Bxh7+ Greek-gift sacrifice (when it works)

## When to use
Your bishop is on **d3** (or b1), pointing down the b1–h7 diagonal at Black's **h7**,
and Black has **castled kingside**. The Bxh7+ sacrifice is tempting — but it only wins
when ALL the conditions below hold. **If even one fails, it just loses a bishop. Check
every box first; do not sacrifice on h7 by reflex.**

## The idea — the win is a forced king hunt
The point is **Bxh7+ Kxh7 Ng5+** (the knight comes with check), then your **queen
reaches the h-file** (Qh5/Qd1–h5) for mate. You give a bishop to strip the king and
bring the knight + queen with tempo.

## What to do — the CHECKLIST (all must be true)
1. **Black has NO knight on f6.** A knight on f6 defends h7 and covers g5 — the sac
   fails outright. (A White pawn on e5 is what usually *removes* the f6-knight; that is
   why e5 is the precondition that makes Bxh7+ live.)
2. **Your knight can land on g5 WITH CHECK** immediately after Kxh7 (knight on f3 → g5).
3. **Your queen can reach the h-file fast** (d1→h5 in one move is ideal) to threaten
   Qh7#.
4. **You control g5 more than Black does** — Black cannot safely answer Ng5+ with
   ...Qxg5 (you must be able to recapture, e.g. Bxg5) or ...Bxg5.
5. **No quick Black defender of h7** (no ...Re8/...Nf8/...Bf5 reorganisation that holds).
6. If Black has a bishop on **e7**, you usually also need a **pawn on h4** (to meet
   ...Kg6 with h5+).

Only if 1–5 (and 6 when relevant) hold: **calculate it to the end with imagine_line**
(Bxh7+ Kxh7 Ng5+ and EACH king reply) and confirm mate or a decisive attack before
committing.

## The main line (king's three replies after Bxh7+ Kxh7 Ng5+)
- **...Kg8** → **Qh5**, threatening Qh7#. ...Qxg5 loses to Bxg5; ...Re8 loses to Qxf7+.
- **...Kg6** → **h4** (then h5+ wins the queen) — needs your h-pawn ready.
- **...Kh6** → **Nxf7+** wins the queen at once.

## Watch out for
- **The single commonest mistake: sacrificing when Black HAS a knight on f6.** Then
  Bxh7+ Nxh7 (or Kxh7 and ...Nf6 holds) and you are simply a piece down. ALWAYS check
  f6 first.
- If you cannot get the queen to the h-file quickly, the attack stalls and the bishop
  is gone. Do not start it on hope.
- When in doubt, DON'T sac — keep the bishop on the diagonal and build the attack
  (Ne5, Qf3/Qh5, Rf1–f3–h3) until the conditions actually appear.

## Example (verified — sac WORKS)
`r1bq1rk1/pppn1ppp/3bp3/3pP3/3P4/3B1N2/PPP2PPP/RNBQ1RK1 w` — Black has NO Nf6, h7 is
only king-defended, e5-pawn present, Nf3 ready for g5, Qd1 ready for h5: **Bxh7+ Kxh7
Ng5+ Kg8 Qh5** with a winning attack.
Example (sac FAILS): same position but with a Black **knight on f6** — Bxh7+ is met by
...Nxh7 and White is just down a bishop.
