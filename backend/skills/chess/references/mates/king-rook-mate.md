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

**Keep the two KINGS close — within 2-3 squares — the WHOLE time.** This is
the speed secret: in Capablanca's mate-in-11 the kings are never more than 3
apart. The rook and your king work as a unit — the rook fences and checks to
shove the enemy king back one line; your king stays right with it to take
squares and reach opposition. When the kings drift far apart (the radar shows
the distance), **stop moving the rook and march your king** — a fence with a
distant king is the slow, drifting failure. This runs in all four directions
(fence a rank to drive to rank 1/8, or a file to drive to the a/h-file).

## What to do — confine, march, mate (use imagine_move to compare moves)

Each turn, decide between TWO jobs by the numbers `chess__imagine_move` gives
you (it reports, for any move you imagine: the enemy king's **box area**
before→after, the **distance between the kings**, and whether your rook stays
**defensible** on its new square):

1. **Rook can be captured by the king?** Move it to safety first — a square
   the king cannot reach, or one your king defends. imagine_move's confinement
   line flags whether a square is defensible in time.
2. **Kings more than 2 apart?** **MARCH YOUR KING** one square toward the enemy
   king. Move the rook *only* if a rook move makes the box strictly **smaller**
   AND leaves the rook **defensible in time** (imagine_move tells you both).
   Never loosen the box; never park the rook where the king reaches it first.
3. **Kings close (≤2) but the enemy king not yet on an edge?** Tighten the box
   one step toward the nearest edge with the rook (on a defensible square), or
   step your king to keep the squeeze. Pick the move that makes the box
   **smaller** without loosening it.
4. **Enemy king on the EDGE and your kings ≤2 apart?** This is the mate: the
   rook checks along the edge with the king's flight squares covered by your
   king. **You mate on the edge — you do NOT need the corner.** Confirm
   `gives checkmate` in imagine_move.

The whole method in one line: **bring your king in while keeping the enemy
king's box shrinking, then mate on the edge.** Both numbers — box area and
king-distance — must trend down.

## Watch out for

- **Don't check just to check.** A check that pushes the enemy king toward
  open space (away from your king) makes no progress — it slips out and you
  start over. Only check when it drives the king toward its edge with your
  king covering the escape, or when it is mate.
- **Don't loosen the box.** A rook move that makes the box area *bigger*
  (imagine_move shows this) gives the king room — reject it. The box must
  only ever shrink.
- **Don't park the rook where the king reaches it first.** If imagine_move
  says the rook is not defensible in time, confine from a square your king
  supports instead.
- **Stalemate when the king is cornered:** `k7/8/K7/8/8/8/8/1R6 b` is
  stalemate. When the enemy king has ≤2 squares, prefer a check and watch
  `chess__imagine_move` for `stalemate`.
- `repeats!`/`draw:repetition` means you are shuffling without progress —
  march your king (the box-area and king-distance numbers must trend down).

## Examples

Opposition on the edge — `4k3/8/4K3/8/8/8/8/7R w - - 0 1`, kings opposed
(Ke6 vs Ke8) with the king already on the edge: 1.Rh8#. The king is on e8,
NOT a corner. Verified.

Herding a sideways dodge — `4k3/R7/5K2/8/8/8/8/8 w - - 0 1` (rook caps the
7th rank, king one step away): 1.Ke6 Kf8 2.Kf6 Kg8 3.Kg6 Kh8 4.Ra8#. Each
time the king dodges sideways you FOLLOW with YOUR king, keeping the rook on
its rank; the king is herded to the h-file and mated on the edge. Verified.

Waiting move — `4k3/1R6/4K3/8/8/8/8/8 w - - 0 1`: the kings face off but it is
White to move, so 1.Ra7 hands the move to Black; now Black must step aside and
walk into the mate. Verified.

Full worked mate: Capablanca Examples 1–2 in
`raw/chess-fundamentals-capablanca.md` (mate in 10–11 from anywhere).
