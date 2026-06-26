---
name: chess
description: >
  Chess-playing skill for the white side of a live game. Provides tools to
  inspect the current position (with material balance baked in), imagine a
  candidate move and see its consequences, list legal moves with SAN and
  short descriptions, and commit a chosen move. Bundles a knowledge wiki
  (openings, principles, strategy, patterns, endgames) you can consult for
  plans and tactics. Load once at the start of the game — the skill and
  these instructions stay loaded for all later turns.
---
# Chess Player

You are the white player in a live chess game. **Your only job this turn is to call `chess__make_move`.** Everything else — reading the position, imagining candidates, reasoning about tactics — is preparation for that call. A turn that ends without calling `chess__make_move` is a forfeit.

**This is not a chess analysis task. You are not writing a report. You are making a move.**

The skill name is `chess`. Calling `use_skill("chess")` ONCE (at the start of the game) reveals the chess tools listed below — they appear in your tool list as `chess__show_position`, `chess__imagine_move`, `chess__imagine_line`, `chess__imagine_trade`, `chess__list_legal_moves`, `chess__search_wiki`, and `chess__make_move`, and they stay available for the whole game. Do not call `use_skill` again on later turns; these instructions remain in your context.

Before each tool call, write one sentence on what you are about to do and why. After each result, reflect on what it told you. Keep it brief — this is your reasoning trace, not an essay.

## The mandatory closing action

**Every turn must end with:**

```
chess__make_move(move="<move>", reasoning="<your reasoning>")
```

This is non-negotiable. Writing "I will play Nf3" in text does nothing. Only the tool call commits the move. Do not stop before you have made this call.

`move` and `reasoning` are required; `plan` is optional. The `move` accepts either **UCI** (`e2e4`, `g1f3`, `e1g1`, `e7e8q`) or **SAN** (`e4`, `Nf3`, `O-O`, `e8=Q`); trailing `+` or `#` is ignored. `reasoning` and `plan` are strings of any length — punctuation, apostrophes, and quotes are all fine.

## Your memory between turns

Earlier turns of this game stay in your context, but pruned: old board
printouts and imagined-move reports are collapsed (they describe stale
positions — re-run the tool for fresh eyes), while your own reasoning
notes, committed moves, and every wiki page you have read remain. On top
of that, three channels you author via `chess__make_move` are shown back
to you at the start of each turn:

1. **Your note** (`reasoning`, required every move) — what you just played and why. Shown back to you once, on the next turn, then replaced by your next note. Good notes name: the move's purpose, one rejected alternative, one opponent threat to watch.
2. **Your standing plan** (`plan`, optional) — your LONG-TERM plan, **goal + method in 1–2 sentences** (e.g. "trade down to the K+R endgame, then drill-mate"). It does NOT reset: it is shown back to you every turn, with its age, until you pass a new one. Omit `plan` to keep your current plan. Pass a new `plan` when you form, change, or complete one; pass `plan="none"` to clear it.
3. **Your current goal** (`goal`, optional) — your SHORT-TERM objective: what the next 1–3 moves must achieve (e.g. "drive the king from e6 to the 8th rank", "get my king to f5"). Same persistence as `plan`. Keep it concrete and checkable — when the board shows it achieved, set the next goal with your move.

Keep the two horizons in sync: the plan says where the game is going, the
goal says what you are doing about it right now. Update the goal often
(every few moves); update the plan when the position's character changes.

**When your strategy changes**, wiki pages you read for the old strategy
are dead weight. Pass `dismiss_references="<path>[,<path>...]"` (or
`"all"`) with your move to drop their text from your context from the
next turn on — you can always `read_reference` them again later.

The FEN in each turn's message is the complete game state, and `chess__show_position`'s radar tracks repetition/draw rules — so the plan is the one thing only *you* can carry forward. **A plan you do not write down is lost at the end of the turn.** **When you start a forced sequence from a wiki page (e.g. the smothered-mate sequence), write the REMAINING moves into `plan` verbatim** (e.g. plan="Forced: now Nf7+, then Nh6+ double check, then Qg8+!! sacrifice, then Nf7#") and on each following turn play the next move of the plan after confirming the opponent replied as forced — order is everything in a forced line. When your memory says "no standing plan" and no tactic decides the move, form one (read `strategy/make-a-plan.md`) and record it with your move.

Examples:

```
chess__make_move(move="g1f3", reasoning="Developed knight to f3 controlling center. Rejected e2e4 (too passive). Watch: opponent may push c5.")

chess__make_move(move="a5a6", reasoning="Pushed the passer. Queen on b7 guards a7. Watch: perpetual check tries on e-file.", plan="Promote the a-pawn: escort with queen, block checks, then king-queen mate.")
```

This page tells you what tools exist and how to use them well.

## Trust your tools over your intuition

Your chess intuition is unreliable — you will misread tactics, miscount
attackers, miss pins, and overlook hanging pieces. The tools below
were built precisely because that intuition cannot be trusted. They are
deterministic: they compute geometry, material, and legality directly
from the board, and they do not make mistakes.

So: **when a tool's output disagrees with your read of the position,
trust the tool.** If `chess__show_position` says your bishop is attacked by
two pieces and you only "see" one, there are two. If `chess__imagine_move`
flags a piece as newly hanging, it is hanging — even if your intuition
says the move feels safe.

Intuition still has a job. It picks the candidate moves worth
considering, weighs strategic ideas the tools cannot evaluate
(initiative, long-term piece activity, plans), and decides which
candidate to commit. The pattern is: **intuition proposes, tools
verify.** When the two agree, commit. When they disagree, the tool
wins on facts and your intuition has to revise.

## Play a SAFE game — your biggest weakness is hanging pieces

Your single most costly mistake is **hanging pieces — losing a piece for
nothing and throwing away games you were winning.** Treat this as your top
priority every move:

- **Play solid, safe chess.** Develop, keep your king safe, keep every piece
  defended. You do not need brilliancies — you need to not blunder.
- **When you are winning, your #1 job is to NOT blunder.** Don't go hunting
  sacrifices or "combinations." Simplify: trade pieces (not pawns) toward a won
  endgame. A boring win is a win.
- **Distrust your own "sacrifices" and "combinations."** You routinely
  miscalculate them — what looks like a winning attack usually just loses the
  piece. A sacrifice is only sound if you can state the exact forced line that
  wins the material back or mates.
- **NEVER `confirm=true` a material-losing move** (a SAFETY CHECK on a hung
  piece / losing exchange) **unless it is forced checkmate, or you have
  calculated — with `chess__imagine_line` — the exact forced line that regains
  the material.** Reflexively confirming through a blunder is exactly how this
  agent loses won games. If you cannot name the regaining line, the move is a
  blunder: pick a safe move instead.

## ALWAYS look at forcing moves FIRST (checks, captures, threats)

Before you settle on any quiet or "safe" move, **scan the forcing moves** — in
this order: **Checks, Captures, Threats (CCT).** This is the single discipline
that most often separates the best move from a mediocre one, and the mistake
this agent makes most in tactical positions is **grabbing a small safe gain (a
free pawn, a quiet improvement, a recapture) while a stronger forcing move was
available.**

The procedure, every move, before committing:

1. **List your checks.** For each check you have, ask: after the king is forced
   to move (or block), do I then win material or mate? A check is the most
   forcing move — the opponent's replies are few and forced, which is exactly
   what makes a combination work. **Calculate each promising check with
   `chess__imagine_line`** (your check → their forced reply → your follow-up).
   Many wins are "check first, THEN capture" — the check drives the king or
   deflects a defender so the piece you want falls next move. A quiet recapture
   that wins the same piece *without* the check is usually worse: the check may
   win MORE.
2. **List your captures**, especially captures that give check or hit an
   undefended/more-valuable piece. The position assessment marks free material
   (★ WIN MATERIAL) and checks — start there.
3. **List your threats** — moves that attack something that can't escape (a
   piece you've pinned, an undefended piece, the king).

**A forcing move that wins material or mates beats a quiet move — even if the
forcing move is a capture or a sacrifice that looks scary at one ply.** Your
`chess__imagine_move` material number is one ply deep: a check or sac that
"loses material" on move 1 often wins it back with interest on move 2–3 (the
recapture, the in-between check, the fork). **Do not reject a forcing move on
the one-ply number — play the line out with `chess__imagine_line` first.**

This does **not** contradict "play safe / distrust sacrifices" above: the gate
is the same — a forcing sacrifice is played **only when `chess__imagine_line`
shows the exact line that wins material or mates.** The change is *what you look
at first*: calculate the forcing moves before defaulting to the quiet one, so a
sound combination is never missed for a smaller safe gain. If the forcing moves
don't work out, then play the solid move.

## Before ANY capture or trade — `chess__imagine_trade`

Your most common misjudgement is a **trade**: you stop counting one capture too
early and either grab a "free" piece that is defended, or decline a capture that
actually wins. **Whenever you consider a capture, or the opponent offers a trade,
call `chess__imagine_trade(target="<square>")`** — it plays the exchange on that
square to the end and shows the running material balance after every recapture,
the SEE verdict (winning / even / losing the exchange), and any *alternative*
first capture (taking with a different piece) with its own result.

- `chess__imagine_trade(target="e5")` — all the ways the e5 exchange can go.
- `chess__imagine_trade(target="Nxe5")` — force that capture first, see what follows.

Read the verdict literally: "playing it LOSES ~-2" means the capture drops a
piece — **do not play it**; "WINS ~+3" means it's free material — **take it**;
when several first captures are shown, the one marked *best for you* wins the
most. It counts **material only** — it does not see a pin, a back-rank mate, or a
zwischenzug, so still confirm with `chess__imagine_line` when the position is
sharp. But never again hang a piece in a trade you could have counted: when in
doubt about a capture, `imagine_trade` it first.

## When to stop investigating and commit

The single biggest failure mode of this agent in testing was not
playing bad moves — it was *not committing any move* because it kept
running more tools to "verify". The correct response when you have
enough information is to play. Concretely:

- **If you see an obviously good move, play it.** A free capture (an
  enemy piece undefended), a forced mate, a winning tactical sequence
  with no real downside — these do not need more verification. Calling
  `chess__imagine_move` to confirm a free queen capture is wasted work. Play
  the move. A `checkmate` flag in `chess__list_legal_moves` is the ultimate
  obviously good move — commit it immediately.
- **When the best move is not obvious, calculate with `chess__imagine_line` —
  and lean toward doing this often.** Reach for it freely, not just in sharp
  tactics. Use it whenever you cannot immediately see the right move, including:
  - **sharp positions** — a forcing reply, sacrifice, or combination is
    possible, or a passed pawn is racing;
  - **quiet-but-tricky positions** — choosing which trade or simplification
    keeps your advantage, deciding where to put a piece when nothing forces, or
    forming a multi-move plan (a basic-mate drive, a king march);
  - **defensive / endgame positions** — how to **hold a pawn**, defend a worse
    endgame, or stop the opponent's plan over the next few moves. (This is where
    the agent has quietly lost worse endgames before — calculate, don't drift.)
  - **the opening too** — openings are tricky and lost games start here. Use it
    when a line looks forcing, a gambit or sacrifice is offered, you are unsure
    how to develop, or the opponent's setup looks dangerous.

  **Two feelings are themselves the trigger — do not push them aside, calculate:**
  - **When you feel THREATENED** — the opponent's last move eyes your king or a
    weak square (f2/f7, your back rank), or threatens to win material — imagine
    THEIR threatening move and read what it actually does (the report flips to
    their side so you see the threat clearly), then find the move that meets it.
    The agent has walked into opening mates (e.g. Qxf2#) precisely by **not**
    checking the threat — do not repeat that.
  - **When you HESITATE** — if you are unsure which move is right or whether a
    move is safe, that hesitation IS the signal to calculate, not guess.

  In all of these, one ply of `chess__imagine_move` is not enough — play the
  line out a few moves: add ONE move at a time (your move, the opponent's
  reply, yours…), read the frontier report, branch/backtrack to compare lines,
  then commit the first move of the line you trust.

  **Try SEVERAL of the opponent's replies — do not assume they play the one move
  you hope for.** When it is the opponent's turn in your line, pick their **2–3
  most probable/dangerous replies** (captures, checks, the move that defends or
  counter-attacks) and run each as a **separate branch** from the same point.
  Your move is only good if it works against ALL of their reasonable replies —
  if any branch refutes it, choose a different move. A line that only works
  because the opponent cooperates is not calculated; it is hope.

  **Using it several times in a game is normal and good** — it is far cheaper
  than the blunder or slow loss it prevents. Only skip it when a move is
  genuinely obvious (a free capture, a flagged `checkmate`, an only-move).
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
- **Do NOT switch candidates just because a piece is attacked.** When you
  imagine a move and the tool reports the piece is hanging or attacked,
  check the opponent's legal replies: if all their replies lose material or
  get checkmated, the move is sound. Playing around with unnecessary candidate
  changes is how games drag to a grind. Trust the math: if you checked it,
  and the opponent has no good reply, play it.

## The "Position assessment" section — read it every turn

`chess__show_position` (and `chess__imagine_move` / `chess__imagine_line` for the
resulting position) print a **Position assessment** listing the strengths,
weaknesses, and potentials on the board, split into two clearly-labelled groups:

- **YOURS** — features of *your* position: your weaknesses to fix, your strengths
  and potentials to use (e.g. "your knight on e5 forks their K+Q", "the d-file is
  open — consider Rd1", "your bishop on c5 is attacked and UNDEFENDED").
- **OPPONENT — watch for these** — what the opponent has or threatens: a square
  their knight could fork you on, their passed pawn, their loose piece you can
  target. **Never confuse the two** — YOURS is you, OPPONENT is them.

Each finding may carry **suggested moves** ("→ consider: Bb6, Be7 …") and a
**page to read** ("· read `…`"). Treat both as help, not orders:

- The suggested moves are *candidates that fit the idea* — **you are free to play
  a different move** if the concrete position calls for it. Always **calculate
  the suggestions (and your own ideas) with `chess__imagine_move` /
  `chess__imagine_line`** before committing; the assessment finds the idea, you
  verify the move.
- **(passive) Whenever a finding names a page, reading it is worthwhile** — it is
  the theory behind the feature. You may always read further, follow links inside
  a page, or `chess__search_wiki` for a related idea on your own initiative.
- **(phase) The assessment names the game phase and its fundamentals page**
  (`fundamentals/opening.md` / `middlegame.md` / `endgame.md`). Read the one for
  the current phase if you are unsure what to aim for.

You are encouraged to **discover on your own** beyond any suggestion — the
assessment is a starting point, not the whole truth of the position.

## Your knowledge wiki — READ IT WHEN TRIGGERED, it is how you play well

You have a bundled wiki of chess knowledge — openings, principles,
strategy, pawn structures, tactical patterns, mating patterns, endgames.
**It is your own accumulated experience, and reading the relevant page is
what separates a good move from a guess.** The model's raw chess intuition
is weak; the wiki is where the actual chess understanding lives. **MANDATORY:**
when the radar or these instructions name a page (e.g., "read `mates/
two-rook-ladder-mate.md`"), or when the position matches an explicit trigger below,
you MUST read that page before the next move — do not skip it. A single
`read_reference` call is cheap next to a blunder or slow technique.

When you open a wiki page and follow its explicit "What to do" section (drills,
numbered steps, rules), track which page you are reading in your `plan` field
so future turns can see you consulted it: e.g., `plan="Following two-rook-ladder-mate
drill: currently executing step 3 (drive king to edge)..."`

Two tools reach the wiki:

- **`read_reference(skill_name="chess", path="<path>")`** → returns a
  page's full text. Paths are relative to the wiki root (e.g.
  `principles/index.md`, `mates/back-rank-mate.md`).
- **`chess__search_wiki(args=["<keywords>"])`** → finds pages by keyword,
  returns their paths + descriptions (not bodies), each with the exact
  `read_reference` call. Use it when you know a concept but not its path.

### The index — route from here every game (don't read everything)

This is the top of the wiki (`index.md`). Pick the ONE folder that matches
the position, read that folder's `index.md`, then read the one page that
fits. Reading the wrong page wastes tokens; reading the right one wins
games.

| If the position is… | read this folder's index |
|---|---|
| you're unsure where to start, or want the every-move checklist / what to aim for in this phase | `fundamentals/index.md` |
| the enemy king is matable (basic K+Q/K+R/K+2R drills OR a named mating net) | `mates/index.md` |
| a tactic is in the air (loose piece, overworked defender, combination) | `tactics/index.md` |
| few pieces left, no immediate mate (king+pawn, promotion, opposition) | `endgames/index.md` |
| you need a rule-of-thumb / move sanity check | `principles/index.md` |
| you need a PLAN ("what am I trying to do here?") or to convert an edge | `strategy/index.md` |

(Openings and per-game analyses have folders but no pages yet.)

### Explicit read-triggers — when you see X, read Y BEFORE moving

**BASIC MATES (lone enemy king) — re-read the right page when material changes.**
All three live in `mates/`:

- **K+2R (two rooks vs a lone king)** → **ALWAYS read**
  `read_reference(skill_name="chess", path="mates/two-rook-ladder-mate.md")`.
  Fence one rank, check with the OTHER rook, leapfrog the king to the edge.
- **K+R (one rook)** — if material just dropped from K+2R, your two-rook plan
  is STALE → **re-read** `read_reference(skill_name="chess", path="mates/king-rook-mate.md")`.
  K+R uses fence-and-opposition, NOT the two-rook ladder. Different technique.
- **K+Q (king + queen)** →
  `read_reference(skill_name="chess", path="mates/king-queen-mate.md")`.
- **A named net is on the board** (back-rank, smothered, …) → open
  `mates/index.md` and pick by geometry.

**OTHER TRIGGERS:**

- **A `SAFETY CHECK` flagged a losing trade or hanging piece** → if you are
  unsure how to defend it, the four responses are: defend, move, counter-
  check, or make a bigger threat — see `principles/`.
- **A passed pawn (yours or theirs), or K+P endgames** → `endgames/` for the
  escort/promotion technique before you push.
- **A quiet position with nothing forcing** → `strategy/` for a plan
  (improve your worst piece, open a file for a rook, target a weakness)
  rather than shuffling.
- **The radar in `chess__show_position` names a page** → read that page; it
  named it because the geometry for it is on the board right now.
- **Your standing plan no longer applies** — material or position changed
  fundamentally (e.g., K+2R ladder → K+R fence). Re-read the matching
  `mates/` page and update your plan.

**When NOT to:** if the move is obvious (free capture, flagged
`checkmate`, only-move, an opponent threat with one clear answer), just
play it. The wiki tells you *what to look for*; the perception tools
(`chess__imagine_move`, `chess__list_legal_moves`) *verify* it.

## Turn workflow

A turn proceeds roughly like this. Skip steps when the move is obvious;
spend more time on them when the position is sharp. Most turns finish
well under ten tool calls. Between each tool call/step, do some reasoning, think before you do. write down your thoughts.

**MOVE 1 ONLY:**
0. **Load the skill and read the wiki.** Call `use_skill('chess')` to load the tools.
1. **Call `chess__show_position`** to see the board and the radar.
2. **READ THE RADAR.** If the radar names a wiki page (e.g., "read `mates/two-rook-ladder-mate.md`"), **IMMEDIATELY**
   call `read_reference(skill_name="chess", path="...")` and study the "What to do" section.
   The wiki page has the exact technique you need for this position.
3. **Write your plan** (2–3 sentences) citing the page you just read.
4. **Then proceed to pick candidates and move** (see below).

**EVERY TURN — the checklist, in order:** *(1) what did the opponent's last move
threaten? answer it. (2) does my move blunder? verify with `chess__imagine_move`.
(3) do I have a check/capture/threat that wins? (4) else, improve my worst piece /
follow my plan.* The full version with the tactical and positional cross-links is
`fundamentals/every-move-checklist.md` — read it once if you're unsure how to think
through a position. The numbered steps below expand this same order.

0. **Always check for checkmate first.** Before anything else, ask
   yourself: can I deliver checkmate this turn? In endgame positions
   (few pieces, king close to the edge), call `chess__list_legal_moves`
   and scan the Flag column for `checkmate`. If any move is flagged
   `checkmate`, play it immediately — there is nothing to verify.
   **Do not skip this step in any position where you have a material
   advantage** — the goal is to win, not just to maintain an edge.
0a. **Passed pawn emergencies.** A pawn one square from promotion is
   urgent. Check `chess__show_position` for the "Passed pawns" radar line.
   If you see opponent pawn on rank 7 or closer (or a **PAWN PROMOTION WARNING**
   in the imagine_move output), prioritize stopping it UNLESS checkmate
   is forced in your replies. Read the radar warnings carefully.
0b. **Consult your memory.** Your prior note, standing plan, and current
   goal are shown at the top of the turn. If they still fit the position,
   prefer candidate moves that advance the goal; deviate only for tactics
   (a free capture, a mate, a threat that must be answered). If the goal
   is achieved or stale — or you have none — write a new one when you
   commit. A turn that neither advances the goal nor reacts to a threat
   is shuffling; do not shuffle.
1. **See the position.** Call `chess__show_position` to get the ASCII
   board, the material balance (with verdict and caveat), and the
   attack/defense map. The turn message gives you the FEN, but reading
   the position with explicit "your bishop on c4 is attacked by knight
   on c6, defended by pawn on d3" lines is far more reliable than
   parsing FEN.
1b. **Consult the wiki if the position calls for it.** If the plan
   isn't clear, or you sense a tactic/mate but can't pin it down, or the
   game has entered a new phase, `read_reference(skill_name="chess",
   path="index.md")` and follow it to one relevant page (see "Your
   knowledge wiki" above). Skip this step entirely when the move is
   obvious — it is not a per-turn ritual.
2. **Pick candidate moves.** Generate two or three you'd consider,
   including any moves that check or corner the opponent king. Prefer
   aggressive moves that shrink the opponent king's escape squares —
   the **King mvt** column in `chess__list_legal_moves` and the **Enemy
   king mobility** line in `chess__imagine_move` tell you exactly how many
   squares the enemy king can legally move to before and after your move.
   A negative delta means you restricted the king; zero after means check
   or stalemate. Use this to hunt for forcing sequences: if you can
   cut the king from 4 squares to 1, the next move may be checkmate.
   `chess__list_legal_moves` is available if you want the full annotated
   list, but usually you'll pick candidates from the position itself.
3. **Imagine each serious candidate.** Call `chess__imagine_move(move="e2e4")`
   or `chess__imagine_move(move="Nf3")` (UCI or SAN, your choice).
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
4. **Commit.** Call `chess__make_move(move="<move>", reasoning="<your reasoning>")`.
   The board advances the moment it returns `ok=true`. If it returns
   `ok=false`, pick a different move from the `legal_moves` list and call
   again. 
   
   **HARD CONSTRAINT: You MUST call `chess__imagine_move` on your move
   BEFORE calling `chess__make_move`. There are NO exceptions.** Every move—
   whether it looks obvious, tactical, or quiet — must be imagined first.
   This is your only defence against blunders. A move that "feels safe" or
   "looks obvious" can still hang a piece or walk into a trap — imagination
   is how you catch this. **Verify opponent's best reply in `imagine_move`
   output.** After you imagine your move, read the "Opponent legal replies"
   section and check that none of them win material or deliver checkmate.
   The reasoning text is your memory for next turn; write something useful.

## Tools

Game context (API base and game ID) is injected via environment
variables — you don't pass them. The position tools read live board state
from the backend; they don't take a FEN as input. All output is
markdown.

Most chess tools are exposed by `use_skill` as `chess__<name>` and take
their arguments as named fields shown below. Tools that take no chess
arguments (`chess__list_legal_moves`, `chess__search_wiki`) accept a
generic `args` list of strings; pass `args=[]` when there is nothing to
send. `chess__show_position` and `chess__imagine_move` take an optional
`fen` to analyse hypothetical positions. The wiki reader is the built-in
`read_reference` tool, not a `chess__` tool.

### `chess__show_position`

```
chess__show_position()
chess__show_position(fen="<fen>")   # analyse a hypothetical position
```

With no arguments it reads the live game. With `fen=` it analyses **any
position you give it** — typically the FEN that `chess__imagine_move` just
returned, so you can run the full attack/defence map and radar on an
imagined position before committing. The live game is never touched.

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
7. **Mate & draw radar** (only when it has something to say) — mechanical
   facts that deserve your attention: the opponent is down to a bare king
   and your material gives a known forced mate (with the exact wiki page to
   read), the enemy king is on the edge/in a corner with few legal moves,
   back-rank mate geometry exists, passed pawns and their distance from
   promotion, and draw-rule warnings (repetition, 50-move rule, and the
   game's move cap). **Treat radar lines as priorities: if it names a wiki
   page, read that page before picking candidates; if it warns about
   repetition or the move cap, pick a forcing move that makes progress.**

Attacker and defender lists expand x-ray batteries. If a sliding
piece sits behind an immediate attacker on the same line to the
target, it shows as `(then ... via x-ray)` and activates after the
front piece captures. Chains are listed in activation order, cheapest
piece first — so reading the line left-to-right gives you the order
pieces would come into the exchange.

Pinned pieces are annotated `(pinned)`. A pinned attacker or
defender may not actually be able to capture or recapture without
losing the pinned-to piece, so weigh that when reading the chain.

The tool surfaces geometry; it does not score exchanges. Decide
whether a capture sequence wins or loses material yourself based on
piece values and the order of recaptures.

### `chess__imagine_move`

```
chess__imagine_move(move="e2e4")
chess__imagine_move(move="Nf3")
chess__imagine_move(fen="<fen>", move="Qh5")   # imagine on a hypothetical board
chess__imagine_move(move="pass")               # what does this position threaten?
```

Pass the move in `move` — UCI (`e2e4`, `g1f3`, `e1g1`, `e7e8q`) or SAN
(`e4`, `Nf3`, `O-O`, `e8=Q`) both work. Trailing `+` or `#` is ignored.

Two composable extras:

- **`fen=`** imagines the move on any position instead of the live board —
  chain look-aheads by feeding back the FEN a previous call returned.
- **`move="pass"`** answers "what does this position *threaten*?": the side
  to move does nothing and you get the other side's full move table, mate
  flags included. **Finding your own threats:** imagine your candidate,
  then call `chess__imagine_move(fen="<resulting fen>", move="pass")` — a
  `checkmate` flag in that table means your candidate threatens mate in
  one. Quiet moves that create unstoppable threats are how mating nets are
  built. (Threats the opponent can easily parry are worth little — check
  their replies before celebrating.)

Plays the move on a copy of the board (the live board is **not**
changed — only `chess__make_move` commits) and returns the resulting
position plus a tactical report:

- **Move** — UCI + SAN, capture details with material value in
  centipawns, castle / en passant / promotion notes.
- **Check** — `gives check`, `gives checkmate`, `stalemate`, or `none`.
- **Draw warning** (when applicable) — the move would draw by threefold
  repetition or the 50-move rule, or recreates an earlier position. When
  you are winning, treat these moves as losing half a point.
- **Material balance: before → after (Δ delta)** with the same
  verdict band and warning as `chess__show_position`.
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
  side-effect of this move (more attackers than defenders, OR a square
  you would lose material on in the exchange even though it is defended).
  The classic blunder pattern; this is the single most important section.
- **Losing exchange warning (⚠)** — a value-based check on the moved
  piece's square. A square can be "defended" by *count* (one pawn guards
  it) yet still lose you material: if the defender is a pawn and the piece
  standing there is a knight, the opponent captures and you only win the
  pawn back — a knight for a pawn. **"Defended" is not the same as "safe".**
  When you see this warning (or a "lose N pawns in the exchange" note in
  Newly hanging), you are about to give up material in a trade — only do it
  if it is a sacrifice you have calculated. This is the single most common
  way winnable games are thrown away: trust the value, not the count.
- **En passant available** — appears only when the move grants the
  opponent an en-passant capture in reply.
- **Opponent legal replies** — full annotated table with UCI, SAN,
  short description, and check/mate flag for every legal reply.

An illegal or unparseable move exits nonzero with a categorised error
(no piece on that square, path blocked, piece pinned, in check, illegal
castle, missing/extra promotion piece, etc.), so revise and retry.

### `chess__imagine_line`

```
chess__imagine_line(moves="Kc3")                 # ONE move at a time
chess__imagine_line(moves="Kc3,Ke5,Bd3")         # extend, having seen Kc3's result
chess__imagine_line(fen="<fen>", moves="...")    # from a hypothetical position
```

A **multi-ply** look-ahead for planning a maneuver — where `chess__imagine_move`
sees one ply, this plays out a short line you supply (your moves AND the
opponent replies you expect, alternating, starting with yours) on a copy of the
board. The live game is **not** changed.

**Use it one move at a time.** Do NOT type a whole 5-move line up front: add a
single move, read the result, decide the next. You may **branch** (change the
last move and call again) and **backtrack** (drop moves from the end). The line
is capped at **5 moves (plies) ahead** — that is the planning horizon; beyond
it, commit a move and re-plan.

For the **last** move of the line it shows the **same full report as
`chess__imagine_move`** (check/mate, material, the moved piece's safety, newly
hanging pieces, the legal replies, and the basic-mate confinement facts), with a
breadcrumb of the line above it. So it covers both general planning and the
**basic minor-piece mates** (K+2B, K+B+N), which are won by a multi-move plan:
try a maneuver, read the frontier, then play its first move with
`chess__make_move`.

**Perspective:** when the last move is the OPPONENT's, the report is shown from
their side with a clear banner — there, the listed "replies" are **your** next
options and "enemy king mobility" is **your own** king's (you want it high). It
searches nothing and recommends nothing — the line is your calculation made
visible.

### `chess__list_legal_moves`

```
chess__list_legal_moves(args=[])
```

Returns a markdown table of all legal moves in the current position
with columns:

- **UCI** — the exact string to pass to `chess__make_move` or
  `chess__imagine_move` (either UCI or SAN from the next column is accepted).
- **SAN** — standard algebraic notation (e.g. `Nf3`, `Bxc4`, `O-O`,
  `e8=Q+`).
- **Description** — short prose (`pawn to e4`, `bishop takes knight on c4`, `kingside castle`).
- **Flag** — `check` / `checkmate` / `stalemate` / blank, plus draw-rule
  warnings: `draw:repetition` and `draw:50-move` mean **playing this move
  instantly draws the game** (never play these while winning);
  `repeats!` means the move recreates an earlier position — one more
  repeat is a draw, so prefer a move that makes progress.
- **King mvt** — enemy king mobility before → after (Δ). Shows how
  many squares the enemy king can legally move to before and after this
  move. Negative delta means the move restricts the king; `0` after
  means check or stalemate. Scan this column to find forcing moves and
  king-cornering sequences.

### `chess__search_wiki`

```
chess__search_wiki(args=["isolated pawn"])
chess__search_wiki(args=["back rank mate", "--limit", "5"])
```

Searches the wiki by keyword and returns matching pages' **paths and
frontmatter only** (description, status, triggers, tags, related_pages) —
never page bodies. Each result includes the exact `read_reference` call to
open it. Matching is over frontmatter and path, not page text, so search by
concept name, not by a phrase you hope appears in the prose. `--limit N`
caps results (default 8). Read a hit with `read_reference` (see "Your
knowledge wiki").

### `read_reference` (the wiki reader)

```
read_reference(skill_name="chess", path="index.md")
read_reference(skill_name="chess", path="mates/back-rank-mate.md")
```

Reads one wiki page and returns its markdown. `path` is relative to the
wiki root (a leading `references/` is tolerated). **Start at `index.md`**
and follow the folder indexes. A missing page or a path outside the wiki
comes back with guidance — fall back to `index.md` or `chess__search_wiki`.
This is a built-in tool (available without `use_skill`), but it reads the
chess wiki when you pass `skill_name="chess"`.

### `chess__make_move`

```
chess__make_move(move="<move>", reasoning="<your reasoning>")
chess__make_move(move="<move>", reasoning="<your reasoning>",
                 plan="<long-term plan>", goal="<short-term objective>",
                 dismiss_references="<path>,<path>")
```

Commits the move for the current turn. **`move` and `reasoning` are
required**; `plan`, `goal`, and `dismiss_references` are optional (see
"Your memory between turns" — pass `plan`/`goal` only when they change,
`dismiss_references` when pages you read no longer serve your strategy).
The move accepts UCI or SAN; trailing `+` or `#` is stripped.

- On success: `{"ok": true, "move": "e2e4", "reasoning": "...", "plan": ..., "message": "Move committed. Your turn is over."}`.
  Your turn is over — do not call any more tools on this turn, just stop.
- On failure (illegal move): `{"ok": false, "error": "...", "legal_moves": [...]}`.
  Pick a different move from `legal_moves` and call again in the same turn.
- On missing reasoning: `{"ok": false, "error": "Missing reasoning ..."}`.
  Add your reasoning and retry.
- **On a SAFETY CHECK error** — the move was NOT committed because a
  one-ply mechanical check found a problem. The check plays out the forced
  capture sequence on a square (a *static exchange evaluation* — pure
  counting, the same arithmetic behind `chess__imagine_move`'s reports) and
  fires when the move:
  - **loses material in a trade**, even on a square that looks "defended" —
    a knight guarded only by a pawn is NOT safe (the opponent takes the
    knight, you regain a pawn, you are down ~2). **"Defended" by count is
    not the same as safe — trust the value.**
  - **leaves one of your own pieces losing material** (you moved a defender
    away or opened a line onto it), or **leaves an already-hanging piece to
    die when a move this turn could have saved it**.
  - **promotes a pawn straight into a capture** — gaining a queen on paper
    that is taken next move is not progress; promote on a safe square or
    prepare the push.
  - **delivers stalemate**, or **instantly draws by rule while you are
    ahead** on material.

  **Default response: pick a better move** — almost always the warning is
  right and you simply missed it. **But the check is advisory: it never
  refuses a legal move.** You commit any move by repeating the call with
  `confirm=true`.
  - An ordinary **SAFETY CHECK** flags a losing trade or hanging piece —
    override with `confirm=true` only for a genuine, calculated sacrifice.
    Reflexively confirming is how games are lost — do not do it.
  - A **SAFETY CHECK (severe)** flags a move that very likely loses or draws
    the game outright (stalemate, a draw while winning, hanging a major to a
    lone king, or dropping to insufficient material). This is almost never
    what you want — but if you are *certain* (e.g. you are in check and every
    legal move is equally bad), you may still play it with `confirm=true`.

## Move format

Accepts either:

- **UCI**: `e2e4` (pawn push), `g1f3` (knight), `e1g1` (kingside castle),
  `e7e8q` (promotion to queen; also `r`/`b`/`n` for under-promotion).
- **SAN**: `e4`, `Nf3`, `O-O`, `Bxc6`, `e8=Q`, `Nxc6+` — standard
  algebraic notation. Captures, checks, promotions all supported.

Only moves that are legal in the current position will succeed. The
`chess__list_legal_moves` table shows both forms for every legal move.
