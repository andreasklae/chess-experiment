---
category: endgames
description: Coordinating two rooks to force checkmate against a lone king — the mechanical pattern every beginner must know.
triggers: [king and two rooks vs lone king, only rooks remain, need to mate with material advantage, enemy king isolated]
related_pages: [king-pawn-endings, patterns/mating-patterns/index]
tags: [mate, rook, endgame, drill, checkmate]
status: tested
updated: 2026-06-17
---

# Two Rooks vs King (K+2R Mate)

## When to use

You have two rooks and the opponent has only a king. **This is forced checkmate** — there is no draw, the king cannot escape forever. Your only job is **not to stalemate** (give checkmate, never a position where the king has no moves and is not in check). The technique is mechanical and takes 10–30 moves depending on the starting position.

## The idea

A single rook can herd a king toward the edge (rook moves cut off ranks and files). A second rook **delivers the final blow when the king has no escape**. The pattern:

1. **Drive the king toward a boundary** (edge or corner) — use one rook to cut off files/ranks, narrowing the king's space.
2. **Advance the second rook** once the first rook has trapped the king into a shrinking region.
3. **Deliver checkmate** on the edge or in a corner.

The key insight: **each rook cuts the board in half**. One rook on the 5th rank cuts off ranks 1–4 from the king. The second rook on the g-file cuts off files h. Move them in lockstep to shrink the escape zone.

## What to do

### The basic algorithm

Use **one active rook** (the "herding rook") to push the king toward an edge. The second rook (the "support rook") follows behind it, cutting off retreat routes.

**Step 1: Herd toward an edge or corner**

- Move your active rook to check the king or restrict its movement.
- After the king moves, advance the support rook closer.
- Alternate: herd rook moves → king moves → support rook closes.

**Step 2: Recognize when the king is trapped**

- If the king is on the edge (rank 1, 8, or file a/h) with few escape squares (2 or fewer), you are near mate.
- Place your rooks so the king has exactly one square. Check on the next move — that is checkmate.

**Step 3: Deliver mate**

- Move a rook to give check so the king cannot escape. If there is only one legal square left for the king after your herd rook moves, the final rook move delivers mate.

### Concrete pattern: edge mate

If the king reaches the 8th rank (top edge):

1. Place one rook on the 7th rank (cutting off retreat to rank 6).
2. Place the second rook to check from above on rank 8 → **Checkmate** (king trapped on rank 8, cannot go to rank 7 or escape laterally).

**Example:** King on e8, your rooks on e7 + a1. Move Ra8# → **Checkmate** (king on e8 cannot go to d8/f8 — blocked by the rook, cannot go to d7/e7/f7 — blocked by the rook on e7).

## Watch out for

### Stalemate (the only danger)

A position where the opponent's king is **not in check BUT has no legal moves** is stalemate (automatic draw). This kills K+2R if you are careless.

**How to avoid it:**

- Always give check to end the position. Never move a rook to a square from which you could be stalemated next.
- After you have cornered the king on an edge: **double-check the position is mate, not stalemate**. The king must be in check.

**Example to avoid:** King on h1, rooks on h2 + a1. If you play Ra1–a2 without checking, the king on h1 has no legal moves but is NOT in check → **Stalemate!** Instead, play Rh2–g1# or Rh2–h1+ (check) to win.

### Moving the wrong rook

When your king is in a tight corner, **moving the support rook by mistake can open an escape route**. Before each move: visually confirm which rook should move (the herding rook advances, the support rook stays put blocking escape). After you move, verify the king still has fewer escape squares than before.

### Moving too slowly

K+2R is forced mate in a finite number of moves. If you've herded the king to an edge and you're moving rooks around without progress, you may be looping. Commit to driving the king to a corner (e.g., always toward h8), and deliver mate when it gets there.

## Examples

### Starting position (FEN)

```
8/8/8/8/3k4/4R3/5K2/R7 w - - 0 1
```

King on d4 (center), White rooks on e3 and a1. White to move.

**Plan:** Drive Black king toward h8.

1. Re4 (herding rook pushes king away, cutting off rank 4)
   → Black king moves, e.g., Kc5, Kd5, Kc3, or Kd3
2. If Kc5, play Ra2 (support rook advances, cutting off rank 2)
   → King continues to edge, e.g., Kb5, Kc4, etc.
3. Continue the pattern: advance herding rook, then support rook, squeezing the king toward h8.
4. When the king reaches e8 or nearby, deliver mate: place rooks on e7 + a8 (or h8), then check on the back rank.

**Expected mate:** ~15–20 moves from this position.

---

**Read next:** If the enemy king is on the back rank and you have a rook, consult [[patterns/mating-patterns/back-rank-mate]].
