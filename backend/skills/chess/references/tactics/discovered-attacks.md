---
category: tactics
description: Discovered attacks, discovered check (the free-capture engine), double check, and the windmill. Moving the front piece unveils an attack from behind — and on a discovered check the moving piece can grab almost anything for free. Includes the exact soundness test.
triggers: [discovered attack, discovered check, double check, windmill, see-saw, battery, my piece is between my rook and their king, unveil, piece in front of my rook or bishop]
related_pages: [tactics/index, tactics/forks-and-double-attacks, tactics/pins-and-skewers, tactics/removing-the-defender, mates/smothered-mate]
tags: [tactics, discovered-attack, discovered-check, double-check, windmill, battery]
status: draft
updated: 2026-06-24
---

# Discovered attacks, discovered check & the windmill

## When to use
One of YOUR pieces stands in front of a friendly rook/bishop/queen, on the same
line as an enemy target behind it — or the mirror, against you. Check this every
move: *do I have a piece screening a line-piece aimed at their king or queen?*

## The idea
- **Discovered attack:** moving the front piece unveils the line-piece's attack.
  You make **two threats in one move** — the moving piece does its own thing, the
  unveiled piece hits something else.
- **Discovered CHECK = a free-capture engine.** If the unveiled line gives check,
  the opponent **must answer the check first**, so the **moving piece is free to
  capture the most valuable thing it can reach — for free** (they can't recapture;
  they're busy with the check). *Example to internalise:* your knight sits between
  your rook and the enemy king; moving the knight discovers check from the rook,
  so the knight can capture ANY piece it reaches and keep it — provided the
  opponent can't answer the check and rescue that piece in a single move.
- **Double check:** both the moving piece AND the unveiled piece give check. The
  king **must move** — no block, no capture can answer two checks at once. This is
  the strongest forcing move in chess and the engine of many mates — most famously
  the knight's double check at the heart of the [[mates/smothered-mate]].
- **Windmill (see-saw):** alternate a **direct check** (rook on the 7th/2nd) and a
  **discovered check** (bishop on the long diagonal). The enemy king is boxed and
  returns to the same square each cycle, so the rook swings out (discovered
  check), grabs a piece, swings back (direct check), and **wins material every
  cycle**. (Torre–Lasker, 1925.)

## What to do — and the SOUNDNESS TEST
Before playing a discovery, run the test: **can the opponent meet BOTH threats in
one move?** The discovery FAILS if they can:
1. **block the check with a piece that also defends** the attacked piece, or
2. have the **attacked piece itself capture the checking (unveiled) piece** or
   block the check, or
3. **capture your moving piece** (king or another unit), killing its threat.

If **none** of those single-move escapes exist, the discovery **wins** — take the
most valuable piece (on a discovered check) or carry out the bigger threat.

- Build a **battery** (Q+R on a file, Q+B on a diagonal) screened by one piece,
  then spring the discovery with tempo.
- Verify the whole thing with `chess__imagine_move` / `chess__imagine_line` — it
  shows the opponent's replies so you can confirm they can't address both.

## Watch out for
- **Against you:** before you move, check if an enemy piece screens a line-piece
  aimed at your king/queen — don't put your king or queen on that line, and don't
  give the screening piece a free tempo target.
- A discovered check is worthless if the moving piece's capture can be answered
  *by the same move that deals with the check* — run the soundness test, don't
  assume.

## Examples
Knight on e5 in front of Re1, Black king on e8: **Nxf7** or **Nd7+** moves the
knight *with its own threat* while the rook discovers check down the e-file → the
knight grabs material for free if Black can't both answer the check and save the
piece. See [[tactics/forks-and-double-attacks]] and [[tactics/pins-and-skewers]].
