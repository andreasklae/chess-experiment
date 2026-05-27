---
name: chess-player
description: >
  Chess-playing skill for the white side of a live game. Provides scripts to
  inspect the current position (with material balance baked in), imagine a
  candidate move and see its consequences, list legal moves with SAN and
  short descriptions, and commit a chosen move. Read on every turn before
  playing.
---
# Chess Player

You are the white player in a live chess game. **Your only job this turn is to call `make_move.py`.** Everything else — reading the position, imagining candidates, reasoning about tactics — is preparation for that call. A turn that ends without calling `make_move.py` is a forfeit.

**This is not a chess analysis task. You are not writing a report. You are making a move.**

The skill name is `chess-player`. Always use that exact name when calling `use_skill` or `run_script`.

Before each tool call, write one sentence on what you are about to do and why. After each result, write one sentence on what it told you. Keep it brief — this is your reasoning trace, not an essay.

## The mandatory closing action

**Every turn must end with:**
```
run_script("chess-player", "make_move.py", ["--uci", "<move>", "--reasoning", "<your note>"])
```
This is non-negotiable. Writing "I will play Nf3" in text does nothing. Only the tool call commits the move. Do not stop before you have made this call.

`args` is a list of strings. Each element becomes one entry in the script's `sys.argv` — no shell quoting, no escaping, no embedded flags. The reasoning text is one element, even if it contains apostrophes, quotes, or punctuation.

**`--reasoning` is required.** The move will not commit without it. Write whatever you want — a sentence, a few lines, anything. This text is injected verbatim as the first message on your *next* turn, so it is the only context you will have about what you just did.

Useful things to include:
- What you played and why (one phrase)
- What you considered but decided against (move + one-word reason)
- One concrete threat the opponent now has that you need to watch
- Any multi-move plan you are executing, or "none"

Example:
```
run_script("chess-player", "make_move.py", ["--uci", "g1f3", "--reasoning", "Developed knight to f3 controlling center. Rejected e2e4 (too passive). Watch: opponent may push c5. Sequence: none."])
```

The reasoning is a single list element. Write it as plain prose — punctuation, apostrophes, and quotes inside the text are all fine, because the list never goes through a shell parser.

This page tells you what scripts exist and how to use them well.

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
(initiative, long-term piece activity, plans), and decides which
candidate to commit. The pattern is: **intuition proposes, tools
verify.** When the two agree, commit. When they disagree, the tool
wins on facts and your intuition has to revise.

## When to stop investigating and commit

The single biggest failure mode of this agent in testing was not
playing bad moves — it was *not committing any move* because it kept
running more tools to "verify". The correct response when you have
enough information is to play. Concretely:

- **If you see an obviously good move, play it.** A free capture (an
  enemy piece undefended), a forced mate, a winning tactical sequence
  with no real downside — these do not need more verification. Calling
  `imagine_move` to confirm a free queen capture is wasted work. Play
  the move. A `checkmate` flag in `list_legal_moves` is the ultimate
  obviously good move — commit it immediately.
- **After imagining 2–3 serious candidates, pick the best and commit.**
  The tools cannot tell you more than you already know once you've seen
  the resulting position for each candidate. Past that point, more
  tool calls are deliberation, not analysis.
- **If you find yourself calling the same tool on the same arguments
  twice in a row, or imagining the same candidate move twice, you are
  looping.** Pick the move you currently believe is best and commit.
  Re-running tools you already ran does not produce new information.
- **The harness will warn you when you have used most of your turn's
  tool budget** — when you see that warning, commit the best
  candidate immediately rather than starting another investigation.

## Turn workflow

A turn proceeds roughly like this. Skip steps when the move is obvious;
spend more time on them when the position is sharp. Most turns finish
well under ten tool calls. Between each tool call/step, do some reasoning, think before you do. write down your thoughts.

0. **Always check for checkmate first.** Before anything else, ask
   yourself: can I deliver checkmate this turn? In endgame positions
   (few pieces, king close to the edge), run `list_legal_moves` and
   scan the Flag column for `checkmate`. If any move is flagged
   `checkmate`, play it immediately — there is nothing to verify.
   **Do not skip this step in any position where you have a material
   advantage** — the goal is to win, not just to maintain an edge.
1. **See the position.** Run `show_position` to get the ASCII board,
   the material balance (with verdict and caveat), and the
   attack/defense map. The turn message gives you the FEN, but reading
   the position with explicit "your bishop on c4 is attacked by knight
   on c6, defended by pawn on d3" lines is far more reliable than
   parsing FEN.
2. **Pick candidate moves.** Generate two or three you'd consider,
   including any moves that check or corner the opponent king. Prefer
   aggressive moves that shrink the opponent king's escape squares —
   the **King mvt** column in `list_legal_moves` and the **Enemy king
   mobility** line in `imagine_move` tell you exactly how many squares
   the enemy king can legally move to before and after your move. A
   negative delta means you restricted the king; zero after means check
   or stalemate. Use this to hunt for forcing sequences: if you can
   cut the king from 4 squares to 1, the next move may be checkmate.
   `list_legal_moves` is available if you want the full annotated
   list, but usually you'll pick candidates from the position itself.
3. **Imagine each serious candidate.** Run `imagine_move --uci <move>`.
   It plays the move on a copy of the board and reports:

   - Whether the move gives check or mate.
   - **Enemy king mobility: before → after (Δ squares).** How many
     squares the enemy king can legally move to before vs. after your
     move. A move that drops this from 5 to 1 is forcing; 0 after
     means check or checkmate. Watch for sequences that progressively
     shrink this number toward zero.
   - The material balance after the move, with the delta from before.
   - Whether the moved piece is safe on its new square (attackers and
     defenders with x-ray and pinned annotations).
   - Whether the move hangs any of *your other* pieces — the classic
     blunder pattern: moving a defender away.
   - Whether moving opens a discovered attack you didn't intend.
   - What the moved piece now attacks and defends, and what it stopped
     attacking and defending compared to its old square.
   - All of the opponent's legal replies, with SAN, short descriptions,
     and the **King mvt** column (enemy king mobility delta per reply),
     so you can see which replies give the opponent king escape routes.

   **For any move that captures, sacrifices material, moves a
   defender, or feels tactical, imagine it before you commit** —
   unless the move is obviously good per the rule above. Cheap
   calculation prevents expensive blunders.
4. **Commit.** Call `make_move.py --uci <move> --reasoning <your note>`. The board
   advances the moment it returns `ok=true`. If it returns `ok=false`, pick
   a different move from the `legal_moves` list and call again. Never commit
   a move before you have imagined it — do not hang a piece unless you are
   certain it is a good sacrifice or trade. The `--reasoning` text is your
   memory for next turn; write something useful.

## Scripts

Game context (API base and game ID) is injected via environment
variables — you don't pass them. The scripts read live board state
from the backend; they don't take a FEN as input. All output is
markdown.

### `show_position.py`

```
run_script("chess-player", "show_position.py", [])
```

Returns, top to bottom:

1. **Phase annotation** — e.g. `Phase: late opening (move 9, phase score 22/24)`. Phase is one of early/late opening, early/late
   middlegame, early/late endgame.
2. **Material balance** — e.g. `+0.30 (slight material lead for white)`.
   The eval is material + Michniewski piece-square tables only. It is
   **tactically blind** — a material lead can be lost in one move if
   the position has unresolved threats. The warning under every
   eval line says so; treat the number as a coarse material check,
   not a verdict on the position.
3. **ASCII board** in a fenced code block. Uppercase = white,
   lowercase = black (K/Q/R/B/N/P). Files a–h left to right, ranks 8–1
   top to bottom (white at the bottom).
4. **FEN and side to move.**
5. **Your pieces under attack** — for each of your pieces that has at
   least one opponent attacker: who attacks it, and which of your
   pieces defend it.
6. **Opponent pieces you are attacking** — same, from the other side.

Attacker and defender lists expand x-ray batteries. If a sliding
piece sits behind an immediate attacker on the same line to the
target, it shows as `(then ... via x-ray)` and activates after the
front piece captures. Chains are listed in activation order, cheapest
piece first — so reading the line left-to-right gives you the order
pieces would come into the exchange.

Pinned pieces are annotated `(pinned)`. A pinned attacker or
defender may not actually be able to capture or recapture without
losing the pinned-to piece, so weigh that when reading the chain.

The script surfaces geometry; it does not score exchanges. Decide
whether a capture sequence wins or loses material yourself based on
piece values and the order of recaptures.

### `imagine_move.py`

```
run_script("chess-player", "imagine_move.py", ["--uci", "e2e4"])
```

Plays the move on a copy of the board (the live board is **not**
changed — only `make_move` commits) and returns the resulting
position plus a tactical report:

- **Move** — UCI + SAN, capture details with material value in
  centipawns, castle / en passant / promotion notes.
- **Check** — `gives check`, `gives checkmate`, `stalemate`, or `none`.
- **Material balance: before → after (Δ delta)** with the same
  verdict band and warning as `show_position`.
- **ASCII board** of the resulting position.
- **Discovered attacks** — your *other* pieces that gain a new
  attack on an enemy piece because the moved piece cleared its line.
  Easy to miss by inspection; read this carefully.
- **Moved piece status** — attacker and defender chains for the
  piece on its new square (x-ray batteries, pinned annotation), plus
  what it now attacks and defends.
- **Side-effects on other own pieces** — squares with enemy/own
  pieces that the moved piece controlled from its old square but
  doesn't from the new one. Watch the "no longer defending" line —
  that's where you spot abandoning a defender.
- **Newly hanging own pieces** — pieces that became unsafe as a
  side-effect of this move (attackers ≥ defenders after, but the
  piece was safe before). The classic blunder pattern; this is the
  single most important section.
- **En passant available** — appears only when the move grants the
  opponent an en-passant capture in reply.
- **Opponent legal replies** — full annotated table with UCI, SAN,
  short description, and check/mate flag for every legal reply.

Illegal `--uci` exits nonzero with a categorised error (no piece on
that square, path blocked, piece pinned, in check, illegal castle,
missing/extra promotion piece, etc.), so revise and retry.

### `list_legal_moves.py`

```
run_script("chess-player", "list_legal_moves.py", [])
```

Returns a markdown table of all legal moves in the current position
with columns:

- **UCI** — the exact string to pass to `make_move --uci` or
  `imagine_move --uci`.
- **SAN** — standard algebraic notation (e.g. `Nf3`, `Bxc4`, `O-O`,
  `e8=Q+`).
- **Description** — short prose (`pawn to e4`, `bishop takes knight on c4`, `kingside castle`).
- **Flag** — `check` / `checkmate` / `stalemate` / blank.
- **King mvt** — enemy king mobility before → after (Δ). Shows how
  many squares the enemy king can legally move to before and after this
  move. Negative delta means the move restricts the king; `0` after
  means check or stalemate. Scan this column to find forcing moves and
  king-cornering sequences.

### `make_move.py`

```
run_script("chess-player", "make_move.py", ["--uci", "<move>", "--reasoning", "<your note>"])
```

Commits the move to the live game. **Both `--uci` and `--reasoning` are required.**

- On success: `{"ok": true, "move": "e2e4", "reasoning": "...", "message": "Move committed. Your turn is over."}`.
  The board has already advanced — do not call any more tools on this turn.
- On failure (illegal move): `{"ok": false, "error": "...", "legal_moves": [...]}`.
  Pick a different move from `legal_moves` and call again.
- On missing `--reasoning`: `{"ok": false, "error": "Missing --reasoning ..."}`.
  Add your reasoning and retry.

## UCI format

`e2e4` (pawn push), `g1f3` (knight), `e1g1` (kingside castle),
`e7e8q` (promotion to queen; also `r`/`b`/`n` for under-promotion).
Only moves that appear in `list_legal_moves` output are valid.
