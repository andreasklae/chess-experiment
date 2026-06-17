---
category: mates
description: K+R vs K — fence on the rank behind the king, march your king to OPPOSITION, then one rook check mates ON THE EDGE; follow the king sideways, never check without opposition.
triggers: [king and rook versus king, rook mate, bare king, basic mate, K+R, cannot finish mate, king escapes on edge]
related_pages: [mates/two-rook-ladder-mate, mates/king-queen-mate, endgames/king-pawn-endings]
tags: [mate, endgame, rook, technique, opposition, recipe]
status: draft
updated: 2026-06-16
---

# King + Rook vs King — the drill

## When to use

King and rook against a bare king. Forced win. **You mate on the EDGE —
you do NOT need the corner.** The king escapes only when you check without
opposition or check with the fence rook. Both are avoidable.

## The idea

The lone king lives in a **confinement box** (the rectangle your rook and the
edges trap it in — `chess__show_position` draws it, marked `·`, and the radar
reports its area). You win by shrinking the box to the edge while marching
your king in. Concretely, three jobs, in order: (1) the rook is a **fence** on
the rank (or file) directly behind the enemy king — it may never cross it,
and it caps one side of the box; (2) your king marches up to stand **in
opposition** (same file as the enemy king, exactly two ranks away, e.g. yours
e6 vs his e8); (3) THEN one rook check along his edge is mate. Until
opposition exists, a check only shoves the king sideways and wastes the fence.

**Both must progress every move: the box area must shrink AND your king must
close in.** A rook that fences but a king that never marches is the slow,
drifting failure — watch the box and the king-distance the radar reports.
This runs in all four directions (fence a rank to drive to rank 1/8, or a
file to drive to the a/h-file) — drive toward whichever edge is nearest.

## What to do — apply the FIRST rule that matches, every turn

1. **Rook not fencing?** Put it on the rank just behind the enemy king
   (his rank ∓1), from a file far from both kings. Quiet move, not a check.
2. **Enemy king attacks the rook?** Slide it along the fence rank to the far
   end (a- or h-file, whichever is farther). Fence holds. Done.
3. **Kings in opposition** (same file, your king two ranks from his, on the
   centre side)? **Check along his edge rank, far from his king** — it mates
   if he is already on the edge, else he retreats a rank and you re-fence.
   This is the ONLY time you check.
4. **Not in opposition, and your king can step toward his?** March your king
   one square toward opposition (stay on your side of the fence). Do NOT
   check.
5. **Enemy king dodged SIDEWAYS along the edge** (e.g. e8→f8)? **Follow it
   sideways with YOUR king** (e6→f6) to re-take opposition. Do NOT check and
   do NOT chase with the rook — the fence stays put. He runs out of room at
   the a/h-file, where rule 3 mates.
6. **Kings opposed but it's YOUR move (wrong side to be on move)?** Make a
   **rook waiting move**: slide the fence rook along its rank to the far side
   from the king. Now HE must move out of opposition, and rule 3 or 5 fires.

## Watch out for

- **Never check without opposition** (rule 3 only). A check from rule-4/5
  positions just lets the king slip out — this is the #1 way the win is
  thrown away.
- **Never check with the fence rook if it abandons the fence rank.** If
  Ra7 is your fence and you play Ra8+, you vacate the 7th and the king
  escapes forward (…Kg7). Keep the fence; mate with opposition instead.
- Stalemate when the king is cornered: `k7/8/K7/8/8/8/8/1R6 b` is stalemate.
  When the enemy king has ≤2 squares, prefer a rule-3 check and watch
  `chess__imagine_move` for `stalemate`.
- `repeats!`/`draw:repetition` means you broke the drill — re-read and apply
  rules 1→6 in order.

## Examples

Opposition on the edge — `4k3/8/4K3/8/8/8/8/7R w - - 0 1`, kings opposed
(Ke6 vs Ke8) with the king already on the edge: 1.Rh8#. The king is on e8,
NOT a corner. Verified.

Herding a sideways dodge — `4k3/R7/5K2/8/8/8/8/8 w - - 0 1` (fence on the
7th rank, king one step from opposition): 1.Ke6 Kf8 2.Kf6 Kg8 3.Kg6 Kh8
4.Ra8#. Each time the king dodges sideways you FOLLOW with YOUR king (rule
5), keeping the rook on the fence; the king is herded to the h-file and
mated on the edge. Verified.

Waiting move — `4k3/1R6/4K3/8/8/8/8/8 w - - 0 1`: kings opposed but it is
White to move (the wrong side), so 1.Ra7 hands the move to Black (rule 6);
now Black must break the opposition and walk into the mate. Verified.

Full worked mate: Capablanca Examples 1–2 in
`raw/chess-fundamentals-capablanca.md` (mate in 10–11 from anywhere).
