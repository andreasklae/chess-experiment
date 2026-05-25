---
name: chess-player
description: >
  Chess-playing skill for the white side of a live game. Provides scripts to
  inspect the current position, imagine a candidate move and see its
  consequences, evaluate positions (statically or after a hypothetical line),
  list legal moves, and commit a chosen move. Read on every turn before
  playing.
---

# Chess Player

You are playing chess as white in a live game. Each turn, the host sends
you a short message naming the opponent's last move and giving the FEN
of the position you have to move in. This page tells you what scripts
exist and how to use them well.

## Trust your tools over your intuition

Your chess intuition is unreliable — you will misread tactics, miscount
attackers, miss pins, and overlook hanging pieces. The scripts below
were built precisely because that intuition cannot be trusted. They are
deterministic: they compute geometry, material, and legality directly
from the board, and they do not make mistakes.

So: **when a tool's output disagrees with your read of the position,
trust the tool.** If `show_position` says your bishop is attacked by
two pieces and you only "see" one, there are two. If `imagine_move`
flags a piece as newly hanging, it is hanging — even if your intuition
says the move feels safe.

Intuition still has a job. It picks the candidate moves worth
considering, weighs strategic ideas the tools cannot evaluate
(initiative, king safety beyond raw attackers, long-term piece
activity), and decides which candidate to commit. The pattern is:
**intuition proposes, tools verify.** When the two agree, commit. When
they disagree, the tool wins on facts and your intuition has to revise.

## Turn workflow

A turn proceeds roughly like this. Skip steps when the move is obvious;
spend more time on them when the position is sharp.

1. **See the position.** Run `show_position` to get the ASCII board
   and the attack/defense map. The turn message gives you the FEN, but
   reading it as a diagram with explicit "your bishop on c4 is attacked
   by knight on c6, defended by pawn on d3" lines is far more reliable
   than reading FEN.

2. **Pick candidate moves.** Generate two or three you'd consider.
   `list_legal_moves` is available if you want the full list, but
   usually you'll pick candidates from the position.

3. **Imagine each serious candidate.** Run `imagine_move --uci <move>`.
   It plays the move on a copy of the board and reports:
   - Whether the move gives check or mate.
   - Whether the moved piece is safe on its new square.
   - Whether the move hangs any of *your other* pieces (the classic
     blunder: moving a defender away).
   - Whether moving opens a discovered attack — yours, or the
     opponent's against you, by noting if the moved piece was
     blocking a line for either side.
   - What the moved piece now attacks and defends.
   - What the opponent's legal replies are.

   **For any move that captures, sacrifices material, moves a defender,
   or feels tactical, imagine it before you commit.** This is the
   cheapest blunder-prevention available to you.

4. **Compare candidates (optional).** Use `evaluate_position --moves
   uci1,uci2,...` to see the static eval at the end of a candidate line.
   The eval is material + piece-square tables only — it sees no tactics
   — so use it as a coarse "did the line land me up or down on material
   and activity," not as a verdict.

5. **Commit.** Call `make_move --uci <move>`. The board advances and
   your turn ends the moment it returns `ok=true`. If it returns
   `ok=false`, pick a different move from the `legal_moves` list it
   returns and call `make_move` again.

## Scripts

Game context (API base and game ID) is injected via environment
variables — you don't pass them. The scripts read live board state
from the backend; they don't take a FEN as input.

### `show_position.py`

```
run_script("chess-player", "show_position.py", "")
```

Returns, top to bottom:

1. **Phase annotation** — e.g. `Phase: late opening (move 9, phase
   score 22/24)`. Phase is one of early/late opening, early/late
   middlegame, early/late endgame, derived from move number and a
   weighted non-pawn material count (queen 4, rook 2, minor 1; max 24).
   No queens on the board forces endgame regardless of material.
2. **ASCII board.** Uppercase = white, lowercase = black (K/Q/R/B/N/P).
   Files a–h left to right, ranks 8–1 top to bottom (white at the
   bottom).
3. **FEN and side to move.**
4. **Your pieces under attack** — for each of your pieces that has at
   least one opponent attacker: who attacks it, and which of your
   pieces defend it.
5. **Opponent pieces you are attacking** — same, from the other side.

Attacker and defender lists expand x-ray batteries. If a sliding piece
sits behind an immediate attacker on the same line to the target, it
shows as `(then ... via x-ray)` and activates after the front piece
captures. Chains are listed in activation order — so reading the line
left-to-right gives you the order pieces would come into the exchange.

Pinned pieces are annotated `(pinned)`. A pinned attacker or defender
may not actually be able to capture or recapture without losing the
pinned-to piece, so weigh that when reading the chain.

The script surfaces geometry; it does not score exchanges. Decide
whether a capture sequence wins or loses material yourself based on
piece values and the order of recaptures.

### `imagine_move.py`

```
run_script("chess-player", "imagine_move.py", "--uci e2e4")
```

Plays the move on a copy of the board (the live board is **not**
changed — only `make_move` commits) and returns the resulting position
plus a tactical report:

- **`Move:`** UCI + SAN, capture details with material value in
  centipawns, castle / en passant / promotion notes.
- **`Check:`** `gives check` / `gives checkmate` / `stalemate` / `none`.
- **`Discovered attacks:`** Any of your *other* pieces that gain a new
  attack on an enemy piece because the moved piece cleared its line.
  These are easy to miss by inspection — read this section carefully.
- **`Moved piece status`** Attacker and defender chains for the piece
  on its new square (with x-ray batteries and `(pinned)` annotation,
  same as `show_position`), plus what it now attacks and defends. Use
  this to decide whether the moved piece itself is safe.
- **`No longer attacking / defending`** Squares with enemy/own pieces
  that the moved piece controlled from its old square but doesn't from
  the new one. Watch the `No longer defending` line — that's where you
  spot abandoning a defender.
- **`Newly hanging own pieces`** Pieces of yours that became unsafe as
  a side-effect of this move (attackers ≥ defenders after, but the
  piece was safe before). The classic blunder pattern; this is the
  single most important section.
- **`En passant available:`** Appears only when the move grants the
  opponent an en-passant capture in reply.
- **`Opponent legal moves:`** Count plus the first 12 in UCI order so
  you can see what they can do in response.

Illegal `--uci` exits nonzero with a categorised error (no piece on
that square, path blocked, piece pinned, in check, illegal castle,
missing/extra promotion piece, etc.), so revise and retry.

### `evaluate_position.py`

```
run_script("chess-player", "evaluate_position.py", "")
```

Or, to evaluate after a hypothetical line without committing:

```
run_script("chess-player", "evaluate_position.py", "--moves e2e4,e7e5,g1f3")
```

- `--moves` takes a **comma-separated** UCI list (e.g.
  `e2e4,e7e5,g1f3`). Whitespace around commas is tolerated.
- The line plays on a copy of the live position — the real game state
  is not changed.
- With `--moves`, output gains two leading lines: `Line: 1.e4 e5 2.Nf3`
  (SAN with correct move numbers) and `After: e2e4, e7e5, g1f3`.

Result without `--moves`:

```
Side to move: white
Evaluation: +0.00 (equal)
Material:   white 4000, black 4000 (+0)
PST:        white -95, black -95 (+0)
Phase:      early opening
```

The score is in centipawns from white's perspective (100 = one pawn of
advantage). Verdict bands: `equal` (0), `roughly equal` (<30),
`slightly better` (30–99), `clearly better` (100–299), `winning`
(≥300). Side names follow the score sign, so a negative score reads as
"black ...".

Eval uses Tomasz Michniewski's Simplified Evaluation Function PSTs
with per-side king-table selection. **There are no mobility,
pawn-structure, or king-safety terms — material + PST only.** The eval
is static and tactically blind: it cannot see that a piece you just
"won" is about to be lost to a fork. Don't trust a small positive
score that follows an unverified tactical sequence. Use it for "did
this line land me up or down on material and activity," nothing
sharper.

If a move in `--moves` is illegal, the script exits with a categorised
error naming which move (1-indexed) failed and why (same categories as
`imagine_move`). Revise the line and retry.

### `list_legal_moves.py`

```
run_script("chess-player", "list_legal_moves.py", "")
```

Returns a JSON array of UCI strings: `["e2e4", "d2d4", "g1f3", ...]`.

### `make_move.py`

```
run_script("chess-player", "make_move.py", "--uci <move>")
```

Commits the move to the live game.

- On success: `{"ok": true, "move": "e2e4", "message": "Move
  committed. Your turn is over."}`. The board has already advanced —
  do not call any more tools on this turn.
- On failure: `{"ok": false, "error": "...", "legal_moves": [...]}`.
  Pick a different move from `legal_moves` and call again.

## UCI format

`e2e4` (pawn push), `g1f3` (knight), `e1g1` (kingside castle), `e7e8q`
(promotion to queen, also `r`/`b`/`n` for under-promotion). Only moves
that appear in `list_legal_moves` output are valid.
