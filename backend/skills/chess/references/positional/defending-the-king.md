---
category: positional
description: What to do WHEN YOUR KING IS UNDER ATTACK — the active-defence recipe. Most of the agent's losses are here: it wins on material then gets mated. Trade the attackers (especially the queen), block checks, retreat to your army, distinguish real threats from spite-checks.
triggers: [king under attack, being mated, king hunt, defend my king, exposed king in the open, walked into the open, king marched out, survive the attack, block the check, trade the queen to defend, escape the checks, mating net, kingside attack against me]
related_pages: [positional/king-safety, principles/luft, strategy/handle-a-threat, mates/index]
tags: [positional, king, defense, survival, mating-attack]
status: draft
updated: 2026-07-01
---

# Defending the king under attack

## When to use
`show_position` warns your king is **exposed in the open / boxed with heavy pieces
closing in**, or you are getting checked repeatedly. This is the position that LOSES
games — a material lead is worthless if you get mated. Switch from attacking to
surviving: your #1 job now is your own king, not winning more material.

## The idea
An attack succeeds by piling FORCING moves (checks, threats) faster than you can
answer. You survive by **removing the forcing power**: trade the attackers, block the
lines, and get the king next to its own army. Do the opposite of what wins games with
an exposed king — do NOT keep grabbing material or walking the king forward.

## What to do — the survival recipe (in order)
1. **Is the threat REAL?** A check that just chases the king (a "spite-check") with no
   follow-up costs you nothing; a check that continues a mating net or wins material is
   real. Before every reply, run `chess__imagine_move` and read the opponent's checks —
   answer the real ones, ignore the empty ones.
2. **BLOCK the check with a piece (interpose) rather than running.** A blocked check
   ends the attacker's tempo; a king move usually just invites the next check and walks
   further into the net.
3. **Retreat the king toward your OWN pieces/pawns.** A king is safe among its army,
   deadly alone in the open. Never march it further into open lines.
4. **Trade off the attackers — the QUEEN first.** One queen trade often ends the whole
   attack. Giving back some material to kill the attack is a GOOD deal when you were
   ahead — you convert the rest afterwards.
5. **Make LUFT** vs a back-rank mate (a quiet rook-pawn move); see [[principles/luft]].
6. **Counter only if it's faster.** With opposite-side castling, your own attack can
   force the opponent to defend — but count the race; don't counterattack while you are
   getting mated in one.

## Watch out for
- **Grabbing material with your king exposed is THE way winning games are lost.** The
  radar warning about your king outranks a free pawn — safety first, then convert.
- **A king walk is good in the ENDGAME** (few pieces, no enemy queen — the king is a
  fighting piece); **suicide in the middlegame** with queens/rooks on. Know which you're in.
- **Don't weaken further:** pushing the pawns in front of your king opens more lines. Only
  make luft, don't dismantle the shield.
- **A blocked/pinned defender guards nothing** — check that the piece you're relying on to
  cover a mating square can actually do it (`chess__imagine_move`).

## Examples
- King hunt lost (real agent game): the king marched Kg2→Kf3→Kg4 under Q+R with pieces
  home; instead of retreating toward its army it walked forward and was mated …Rg3#. The
  radar now flags this the move BEFORE — retreat or block instead.
- Trading to survive: with the enemy queen the only real attacker, forcing a queen trade
  (even at the cost of a pawn) usually ends the attack and leaves you to convert a safe game.
