---
category: mates
description: Two rooks mate a lone king by two rules — fence before you check, and always check with the OTHER rook — leapfrogging the king to the edge. Fully forced, your king not needed.
triggers: [two rooks, K+2R, two major pieces, lone king, enemy king in the open, lawnmower mate, ladder]
related_pages: [mates/king-queen-mate, mates/king-rook-mate, mates/blind-swine-mate, mates/back-rank-mate]
tags: [mate, endgame, rook, technique, recipe, basic-mate]
template_pieces: [rook, rook]
template_king_zone: edge
template_exposed_king: true
status: draft
updated: 2026-06-17
---

# Two-Rook Ladder Mate (K + 2R vs lone king) — the drill

> **Scope:** two rooks vs a bare king. The **queen + rook** and **two-queen**
> ladders run on the same fence/check rhythm but differ in the king-adjacency
> and stalemate traps — they have their own pages (`queen-rook-ladder-mate`,
> `two-queen-ladder-mate`) when seeded. For K+Q or K+R alone, see
> [[mates/king-queen-mate]] / [[mates/king-rook-mate]].

## When to use

You have two rooks against a lone king. **The first mate to look for** —
fully forced, needs no help from your own king, ~5–8 moves from anywhere.

## The idea — two rooks taking turns (a.k.a. herding)

One rook is the **fence** (the *support* rook): it controls a whole rank so
the king cannot step back across it. The other is the **checker** (the
*herding* rook): it checks along the king's rank to shove the king one rank
toward the edge. Each turn the king is herded one rank closer to the edge,
the rooks swapping fence/checker roles. Two principles — break either and the
king slips out:

- **Fence before you check.** A check only drives the king forward if it
  has nowhere backward to go, so a rook must hold the rank *behind* the
  king before you check. Making the fence is a quiet move, not a check.
- **Keep both rooks far from the king** (opposite wing) so it can never
  walk over and capture one.
- **The two majors must be on DIFFERENT files** (one on the king's rank,
  one on the rank behind). Two rooks stacked on the *same file* block each
  other — neither can slide past its partner to check or to re-fence. If
  yours share a file, move one to another file first. (The whole method
  also runs sideways: to mate on the a/h-file instead, swap "rank" for
  "file" everywhere — fence a file, check along the next.)

## What to do — reason, don't memorise squares

**Pick the direction ONCE and keep it.** Drive the king toward the edge it
is **already closest to** (fewest ranks away). Pushing it that way only
brings it closer, so the choice never needs to change — **write your target
edge (e.g. "drive to rank 8") into your `plan`** and keep driving the SAME
way every turn. Flip-flopping direction is the #1 reason the king escapes.

You work out the move yourself and **verify with `chess__imagine_move`**.
Its **Enemy king mobility: before → after** line is your compass: a good
driving move makes that number **go down** or gives check; if it goes
**up**, you broke the fence — reject it. Each turn, in order:

1. King touching a rook? Slide that rook far away first (even if defended).
2. No wall on the rank *behind* the king (the side away from your target
   edge)? Make one — a **quiet** rook move onto that rank, far from the
   king. Not a check.
3. Wall held → **check the king's rank with the OTHER rook**, from as far
   from the king as possible. The king must step one rank toward the edge.
4. The king has stepped toward the edge; the rooks swap roles (the checker
   becomes the new wall). Repeat to the last rank, where the check is mate.
   *Advancing the wall rook to check is fine **if** a rook still sits behind
   the king afterwards — the mobility number confirms it.*

## The finish (and the three traps in it)

When the king is on the **last rank** with your fence holding the
second-to-last, bring the free major to the last rank far from the king —
that check is mate.

**Trap 1 — fence next to the king:** if your *fence* rook sits right next to
the cornered king (e.g. king c8, fence rook b7), the natural edge check lets
the king simply **capture the fence rook** (Ra8+?? Kxb7). When the king is on
the edge and a major is beside it: **first slide that major far away along
its own line** (it keeps cutting off the rank, but now out of the king's
reach), leaving the king trapped on the edge. *Then* the next check on the
edge is mate. Example `2k5/1R6/R7/8/8/8/8/6K1 w - - 0 1`: `1.Rh7 Kd8 2.Ra8#`.

**Trap 1b — the CHECKING rook would land next to the king (waiting move):**
the move that checks (to push the king the last rank, or to mate) may itself
land on a square *adjacent* to the king, where the king captures it
(`Ra8+?? Kxa8` with the king on b8). Two fixes: **(a) check from a file at
least TWO away** from the king's file; or, when no safe check is available
yet, **(b) make a WAITING move** — slide the WALL rook sideways to the far
end of its rank (away from the king, keeping the cut-off). The king is in
zugzwang and must step toward the corner; *then* the check is mate. This
transposes to every direction (file mates too: slide the wall along its
file). Example `1k6/7R/R7/8/8/8/8/6K1 w - - 0 1` (king b8, rooks a6/h7):
`1.Re7` (waiting) `Kc8 2.Ra8#` — Ra8+ at once would hang to Kxa8.

**Trap 2 — your own king blocks the check (drive AWAY from your king):** a
rook checks along a whole rank/file, so if your OWN king stands on that line
between the rook and the enemy king, the "check" is blocked and does nothing.
This stalls the ladder when you drive the enemy king onto the rank your king
is on (e.g. enemy king to rank 1 while your king sits on g1 — every Rank-1
check is self-blocked by g1). Two cures: **(a) drive the king to the edge
AWAY from your own king** from the start (your king low → push the enemy up;
your king high → push it down), and **(b)** if they do share a line, deliver
the mate from the side of the enemy king *away* from your king, or step your
king off the line first. Example `8/8/8/8/8/7R/5R2/2k3K1 w - - 24 13` (enemy
Kc1, your Kg1 both on rank 1, rooks f2/h3): 1.Rd3 (box the king on b1/a1)
Kb1 2.Rd1# — the d-rook mates from the a/b side, where g1 does not block.

## Watch out for

- A `repeats!`/`draw:repetition` flag = you broke the rhythm (probably
  checked with the fence rook, or checked with no fence). Re-read "The idea"
  above and place a fence this turn.
- **The single most common mistake: checking with the fence rook.** It
  feels like progress (it's a check!) but it abandons the cut-off rank and
  the king walks straight back. Always check with the *other* rook.
- Keep both rooks on the **opposite wing from the king** so it can never
  touch them (rule 1). If it does touch one, sliding it away (rule 1)
  always comes before checking.
- **Stalemate check at the finish.** A quiet rook move that leaves the king
  zero legal squares but is *not* a check is **stalemate**, not mate — always
  confirm the final move is `gives checkmate` with `chess__imagine_move`.
- **If the opponent still has a piece** (not yet a bare king — e.g. a knight
  left), it may attack your rooks too. A "safe" square is one not capturable
  by **any** enemy piece, not just the king — `chess__show_position` lists the
  safe squares for an attacked piece, and `imagine_move` confirms a relocation
  does not hang it. Pick your fence/check squares off enemy lines of attack.
- **Doing the queen-ladder instead?** With queen + rook (or two queens) the
  king-adjacency rules change — read [[mates/king-queen-mate]]
  for the queen's stalemate/contact rules, then run the same fence/check
  rhythm.

## Example (verified, king flees toward the centre)

`8/8/3k4/8/8/8/R7/1R4K1 w - - 0 1` — king d6, rooks a2 and b1.

`1.Rb5 Ke6 2.Ra6+ Ke7 3.Rb7+ Ke8 4.Ra8#`

- **1.Rb5** builds the fence on rank 5 (a quiet move — king can't come
  down). **2.Ra6+** checks with the *other* rook. **3.Rb7+** leapfrogs:
  the b-rook checks rank 7 while a6 is now the fence. **4.Ra8#**.
- The rooks alternate a/b files (opposite wing from the king) and **the
  fence rook never gives the check**.
