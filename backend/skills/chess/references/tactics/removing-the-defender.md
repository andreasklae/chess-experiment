---
category: tactics
description: Removing the defender — the umbrella for deflection, decoy/attraction, overloading, interference, and undermining. A target is held by one defender; eliminate, lure, block, or overwork it, then win the target.
triggers: [removing the defender, remove the guard, capturing the defender, capture the defender, deflection, decoy, attraction, overloaded, overworked piece, interference, undermining, lure away, only defender]
related_pages: [tactics/index, tactics/deflection, tactics/pins-and-skewers, strategy/handle-a-threat]
tags: [tactics, deflection, decoy, overload, interference, defender]
status: draft
updated: 2026-06-24
---

# Removing the defender

## When to use
A piece you want (or a mating square) is protected by **one** defender. If you can
get rid of that defender's protection, the target falls. Always ask: *what is the
ONE thing defending this — and can I remove it?*

## The idea — five ways to remove a defender
1. **Capture it** — simplest: if you can take the defender favourably, do it, then
   take the target.
2. **Deflection** — force the defender AWAY from its job with a more urgent threat
   (usually a check or a capture it must answer). It leaves; the target is free.
   ([[tactics/deflection]] has the worked detail.)
3. **Decoy (attraction)** — LURE a piece TO a specific bad square, usually by a
   sacrifice on that square, so another tactic works. When the lured piece is the
   **king**, it's called **attraction** (drag the king onto a fork/check square).
   *How to find it:* spot a tactic that WOULD work if a piece stood on square X,
   then find a forcing way to put it on X.
4. **Overloading (overworked piece)** — one defender is doing **two** jobs. Attack
   one job; it can't hold both — whichever it saves, the other falls.
5. **Interference (obstruction)** — drop a piece BETWEEN the defender and what it
   defends, cutting the line. Deadly against rooks/bishops/queens, which rely on
   open lines; often a startling sacrifice on the blocking square.

Related: **undermining** — remove the *support pawn* propping up an enemy piece or
structure, so the thing it held collapses.

> Deflection vs decoy in one line: **deflection lures a piece AWAY** from a square
> it needs to guard; **decoy lures a piece TO** a square where it's vulnerable.

## What to do
- Identify the target and its **sole** defender. Pick the cheapest removal: can you
  capture it? deflect it with a check? overload it? interpose on its line?
- These are usually **forcing** (a check, a capture, a threat that must be met) —
  so calculate the forced sequence with `chess__imagine_line`.

## Soundness check
The removal wins iff the defender truly can't keep doing its job:
- there is **no second defender** of the target, and
- the forcing move **can't be answered by a move that both meets it AND keeps the
  guard** (the same single-move test as every tactic).
Watch for a *zwischenzug* (in-between check) the opponent can throw in to both
parry and re-defend.

## Watch out for
- A defender that is **pinned** already defends nothing — you may not need to
  remove it at all ([[tactics/pins-and-skewers]]).
- Sacrificing to deflect/decoy only works if the follow-up is forced — don't give
  up material on a hope; verify the line.

## Examples
Overload: the enemy queen guards both a back-rank mate square and a hanging
knight. Take the knight with check or threaten the mate — the queen can't do both,
something falls. Interference: a bishop defends a8 along a8–h1; interpose a piece
on the diagonal and a8 is suddenly undefended. See [[tactics/deflection]].
