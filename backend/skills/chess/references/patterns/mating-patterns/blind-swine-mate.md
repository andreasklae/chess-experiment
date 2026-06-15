---
category: patterns/mating-patterns
description: Two rooks doubled on the enemy's second rank devour everything and mate the castled king in the corner — the brute-force cousin of the ladder.
triggers: [blind swine, two rooks on seventh, doubled rooks second rank, pigs on the seventh]
related_pages: [patterns/mating-patterns/ladder-mate, patterns/mating-patterns/back-rank-mate]
tags: [mate, rook, seventh-rank, castled-king]
template_pieces: [rook, rook]
template_king_zone: back-rank
template_rook_on_seventh: true
status: draft
updated: 2026-06-11
---

# Blind swine mate (two rooks on the seventh)

## When to use

Both your rooks have reached (or can reach) the enemy's second rank —
"pigs on the seventh" — against a castled king. Even when no immediate
mate exists, doubled rooks there usually win material by force; against a
cornered king they often mate outright.

## The idea

Two rooks side by side on the 7th control everything the king's pawn
shield once did. Against a king on g8 with a rook still on f8, the
sequence is a short forced ladder in miniature: capture-check on g7 drives
the king to the corner, capture-check on h7 drives it back, then the
second rook returns to g7 — mate (the king's own rook blocks f8).

## What to do

1. Double the rooks on the 7th rank (an open file plus one entry square is
   enough — the second rook follows behind the first).
2. If the king is on g8/h8: Rxg7+ → Kh8 → Rxh7+ → Kg8 → Rg7 (back) — mate
   if f8 is blocked by Black's own piece. Each move is a check; the
   opponent never gets a turn.
3. If f8 is free, the same sequence wins the pawns and chases the king —
   convert per [[patterns/mating-patterns/ladder-mate]] afterwards.

## Watch out for

- Keep the rooks defending each other on the rank — a lone rook on the 7th
  can be harassed; the pair cannot.
- Back-rank counterplay: while your rooks feast, confirm your own first
  rank is safe (see [[principles/luft]]).
- Verify the final rook return is `gives checkmate` — if the king's f8
  square is free it's only a repetition-risk check (the table will flag it).

## Examples

`5rk1/pR4pp/8/8/8/8/8/6RK w - - 0 1` — 1.Rgxg7+ Kh8 2.Rxh7+ Kg8 3.Rbg7# —
every black move forced; the f8-rook blocks its own king. Verified.
Final picture: `5rk1/6RR/8/8/8/8/8/8 b` — the swine side by side.
