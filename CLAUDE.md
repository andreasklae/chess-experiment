# CLAUDE.md — Chess Experiment

This file gives Claude Code (and any other LLM agent) the operating manual
for the chess experiment. Read it before doing work in this repo.

## What this repo is

A self-contained chess experiment with two active packages and one
reference directory:

- `backend/` — FastAPI + python-chess service that owns one game at a
  time, drives bot turns, persists state to `games/`, runs batch
  experiments, and serves the React frontend over SSE. The
  `chesscom_driver` package lives inside `backend/` as a regular
  subdirectory.
- `frontend/` — React + Vite + chessground UI. Lobby for ad-hoc games,
  a batch page for running calibration sequences, and a per-game board
  page with live Stockfish evaluation.
- `chesscom-driver/` — original standalone package directory; kept for
  reference. The live copy used at runtime is `backend/chesscom_driver/`.

The agent is `pydantic-ai` + the `skillful-agent` SDK running against a
local Gemma 4 31B-it model on eX3 via vLLM. It plays white. After
`use_skill("chess")`, each `scripts/<name>.py` is exposed as a typed tool
`chess__<name>` (the harness no longer has a generic `run_script`):

- `chess__show_position` — ASCII board + material balance + attack/defense map + the **mate & draw radar** (`scripts/_radar.py`: mechanical facts — basic-mate material classes with wiki pointers, enemy-king geometry, back-rank geometry, passed pawns, repetition/50-move/move-cap warnings)
- `chess__imagine_move(move=...)` — one-ply look-ahead with tactical report
- `chess__list_legal_moves` — annotated markdown table of legal moves
- `chess__make_move(move=..., reasoning=..., plan=...)` — commits the move (validation-only HTTP call via `/agent-commit`; the bot loop is the sole writer to `game.board`). `reasoning` is the per-move note; optional `plan` is the standing plan that persists across turns (see `decisions/2026-06-10-structured-turn-memory.md`)
- `chess__search_wiki(args=[...])` — keyword search over the knowledge wiki (returns page paths + frontmatter)

Plus the built-in `read_reference(skill_name="chess", path=...)` for reading
wiki pages. See [`backend/skills/chess/`](backend/skills/chess/) and the wiki
maintenance section below. The material+PST static eval previously exposed as
a separate `evaluate_position.py` script is now folded into `show_position`
and `imagine_move` output (one line each); the eval helpers themselves live
in `backend/skills/chess/scripts/_eval.py` and are not exposed to the agent.

SDK-bundled native tools (`manage_todos`, thread/spawn tools, file
read/write, `list_skill_files`, etc.) and native skills (`web-search-free`)
are explicitly disabled in `AgentConfig` for this experiment — the chess
agent needs only `use_skill`, its `chess__*` script tools, and
`read_reference`; a narrower tool surface prevents the looping behaviour
observed when those were available. See `decisions/2026-05-26-stabilization.md`.

The agent UI panel subscribes to `/api/games/{id}/agent-events` (SSE).
On connect, the endpoint **replays all historical events** for the
current game (completed turns + in-progress turn so far) before
switching to live streaming. Reasoning text from earlier turns is
therefore visible to anyone who opens the board page mid-game; the
queue-only design that preceded this would silently drop those events.

## Workspace layout

This is a **uv workspace**. The root `pyproject.toml` declares `backend`
as the sole member. One shared venv lives at `./.venv/`.

```bash
uv sync                        # install workspace into .venv/ at chess root
uv run uvicorn app.main:app    # start backend (from backend/)
bun run dev                    # start frontend (from frontend/)
```

`bun`, not `npm`, for the frontend. The user explicitly prefers it.

### Recovering from a broken venv

If you see `ImportError` on a known-installed package — most commonly
`chesscom_driver` failing to import or `app` not found — run:

```bash
./scripts/repair-env.sh
```

**Root cause:** the project path contains an em-dash (`Dokumenter – MacBook Air`)
which Python's `.pth` processor silently skips. uv's editable installs write
`.pth` files using this path, so neither `app` nor `chesscom_driver` land on
`sys.path` even though their `.dist-info` entries are present. The repair
script works around this by symlinking both packages directly into
`site-packages`, bypassing the `.pth` mechanism entirely. The symlinks
survive `uv sync` — you only need to re-run `repair-env.sh` if you wipe
`.venv` from scratch.

Note: `chesscom_driver` now lives inside `backend/` (not as a separate
workspace member). The `chesscom-driver/` sibling directory is kept for
reference but is no longer on the import path.

## Where to read first

Before touching anything substantive:

1. [`../../knowledge-base/work/experiment-chess.md`](../../knowledge-base/work/experiment-chess.md)
   — design goal, methodology, opponent pool, logging schema.
2. [`../../knowledge-base/decisions/2026-05-20-elo-and-batch-runner.md`](../../knowledge-base/decisions/2026-05-20-elo-and-batch-runner.md)
   — ELO formula, K-factor, opponent selection, batch persistence,
   methodology choices the thesis depends on.
3. Recent diary entries under `../../knowledge-base/diary/experiment-chess/`.

When you make a methodology-affecting change, **add or update a decision
record** before touching code. Decisions drive the thesis chapter on
methods; the code is downstream of those decisions.

## Conventions specific to this repo

- **Single active game.** `GameService._game` is a single slot. Creating
  a new game closes the prior one's players. This is intentional — no
  parallel games.
- **Only agent games are logged.** They go to one of two CSVs:
  `games/ranked.csv` (when on clean `main` — also updates ELO) or
  `games/experimental.csv` (any other git state — ELO frozen).
  Human-vs-Maia ad-hoc games are not logged at all. See
  [`../../knowledge-base/decisions/2026-05-24-ranked-vs-experimental.md`](../../knowledge-base/decisions/2026-05-24-ranked-vs-experimental.md).
- **Each batch game gets a fresh `Agent` instance.** No conversation
  state carries between games. This is enforced by `PlayerFactory.create`
  building a new `AgentPlayer` each call.
- **chess.com is black-only, agent is white-only.** Schema validators
  enforce this; the frontend's `PlayerSelector` mirrors it.
- **Maia covers 1100–1900; chess.com covers 250–3200 in 25 discrete
  steps.** Each batch picks one pool. See decision record for the
  rationale on not mixing pools mid-batch.
- **Stockfish evaluation is UX-only.** The agent has no access to it;
  it's just the advantage needle next to the board.
- **Puzzle mode.** `POST /api/games` accepts an optional `initial_fen` to
  start from any legal position (refused for chess.com games). Used by
  `scripts/run_puzzles.py` to drop the agent into mating/conversion
  exercises; such games land in `experimental.csv` like any non-main game.
- **Per-PR game folders.** Game JSONs and agent logs live in
  `backend/games/<folder>/` named for the PR's `headRefName` (or branch
  name when no PR exists). Pre-PR baseline games are in
  `backend/games/baseline/` with bare UUIDs. Non-baseline folders
  prefix filenames with a 3-digit chronological sequence
  (`042_<game_id>_agent.json`). The `pr_number` column in `ranked.csv` /
  `experimental.csv` references the GitHub PR number. The destination is
  resolved by `app/folder_resolver.py` via `gh pr view` (with a 60s
  cache) and falls back to the branch name when `gh` is unavailable. The
  one-shot migration that introduced the layout is
  `scripts/reorganize_games.py`.

## Workflow norms

### Git commits

- **Never add yourself (Claude) as a co-author.** No `Co-Authored-By:
  Claude <...>` trailers. The user authors every commit; you're the tool
  that produced the patch.
- Commits should be detailed and include rationale, not just a list of
  files changed. The git history is part of the thesis's reproducibility
  story — `git log` should read like a methods journal.
- The chess experiment is a fresh git repo as of 2026-05-20. Every agent
  game's CSV row carries `branch` + `pr_number` so each game is traceable
  to the agent version that produced it.
  But the unit of "agent configuration version" is the **PR**, not the
  commit: iterate on a branch, merge to `main`, run the official
  calibration batch on `main` post-merge. `git revert` is the recovery
  primitive — it reverses both code and the calibration CSV rows the PR
  produced. See
  [`../../knowledge-base/decisions/2026-05-24-ranked-vs-experimental.md`](../../knowledge-base/decisions/2026-05-24-ranked-vs-experimental.md).

### Knowledge base

The knowledge base at `../../knowledge-base/` has its own operating
manual at [`../../knowledge-base/CLAUDE.md`](../../knowledge-base/CLAUDE.md).
Read it before writing or editing anything there. Diary entries in
`diary/experiment-chess/YYYY-MM-DD.md` are user-authored — propose edits,
don't silently rewrite.

### Verifying changes

Before committing:

```bash
# Run from experiments/chess/ — uses the chess venv directly
.venv/bin/python -c "from chesscom_driver import ChessComPlayer; from app.main import app; print('ok')"
cd backend && uv run pytest tests/ -v
```

For UI changes, start the dev server and exercise the path manually.
Type-checking via tsc isn't currently wired into the workflow.

## The agent's chess wiki — you are the maintainer

The chess agent has its own knowledge wiki at
[`backend/skills/chess/references/`](backend/skills/chess/references/). It
is the agent-curated corpus the [[tool-fairness]] rulebook turns on, and
its growth across batches is a Phase 1 result. The architecture, page
contract, and retrieval mechanism are fixed in
[`../../knowledge-base/decisions/2026-06-02-chess-agent-wiki-architecture.md`](../../knowledge-base/decisions/2026-06-02-chess-agent-wiki-architecture.md)
and the fairness rule in
[`../../knowledge-base/decisions/2026-06-02-tool-fairness-rulebook.md`](../../knowledge-base/decisions/2026-06-02-tool-fairness-rulebook.md).
**Read both before editing the wiki.**

This is the same division of labour as the thesis knowledge base
([[karpathy2025wiki]]): the *agent reads* the wiki during play; *you (the
coding agent, acting as the chess tutor) maintain it*. The agent never
edits the wiki mid-game. All ingest, lint, and maintenance is done here,
by you, under the user's direction.

### Layout

```
references/
├── index.md                         # routing decision-tree — read FIRST
├── log.md                           # append-only maintenance log
├── openings/        principles/     strategic-thinking/{,pawn-structures/}
├── patterns/{,mating-patterns/}     endgames/         game-analyses/
```

Every folder has an `index.md`. The agent reaches pages two ways:
**`read_reference(skill_name="chess", path="<path>")`** reads a page body
(path-based, subfolder-aware, jailed to `references/` — requires
skillful-agent ≥ commit `435fa8d`), and **`chess__search_wiki(args=["<kw>"])`**
(the `scripts/search_wiki.py` tool) finds pages by keyword and returns each
hit's frontmatter plus the exact `read_reference` call to open it — never
the body. `read_reference` is intentionally NOT in `_DISABLED_TOOLS`
(`backend/app/agent_player.py`); it is the wiki page reader. Do not add a
`references:` list to SKILL.md expecting it to gate anything — the harness
ignores that frontmatter and serves any file under `references/` by path.

Note the harness no longer has a generic `run_script` tool: each
`scripts/<name>.py` is exposed as a typed tool `chess__<name>` after
`use_skill`. The backend detects the agent's move by watching for the
`chess__make_move` tool result (`_committed_move_from_result` in
`agent_player.py`), not a `run_script` call.

### Page contract (enforce on every page you write)

Frontmatter (all fields required except `related_pages`):

```yaml
---
category: patterns/mating-patterns        # the folder it lives in
description: One sentence. This is what search_wiki.py shows the agent.
triggers: [board conditions, that make, this page relevant]
related_pages: [patterns/deflection, principles/luft]   # [[wikilink]] targets
tags: [mate, tactic, rook]
status: draft                             # draft → tested
updated: YYYY-MM-DD
---
```

Body sections, in order: **When to use** · **The idea** · **What to do** ·
**Watch out for** · **Examples** (FEN/PGN, optional).

Hard rules:

- **~400 words / ~60 lines max per page.** Progressive disclosure is the
  point; an oversized page defeats it. If a page outgrows the cap, **split
  it** (`page-part-1.md` / `page-part-2.md`, cross-linked) — do not let it
  sprawl. `read_reference` truncates at ~15000 chars as a backstop; a page
  approaching that is far past the soft cap and should already be split.
- **Verify every concrete claim.** Any FEN/PGN/"this is mate" example must
  be checked in python-chess before it goes in the wiki — the agent trusts
  these pages. Use the chess venv:
  `.venv/bin/python -c "import chess; b=chess.Board('<fen>'); b.push_san('<mv>'); print(b.is_checkmate())"`.
- **Link with `[[wikilink]]`** inline and mirror the link in
  `related_pages`. A page pointing the agent to the next relevant page is
  how progressive disclosure chains.
- **Register the page in its folder `index.md`** (add a row) and **append
  to `log.md`** (`## [date] <op> | <path> | <description>`; ops: create,
  update, split, promote, retire). The log + `git diff` between batch SHAs
  is half the experiment's data — keep it faithful.

### Operations (mirror the KB's, adapted for this wiki)

- **Ingest.** The user supplies source material (a chess book, an article,
  an engine analysis) and points you at a topic. Read it, synthesise it
  into one or more pages following the contract, register them, log it.
  This is the fair path under the rulebook — reading-and-noting, not
  dumping a corpus. Start narrow: the user has asked to begin with
  `strategic-thinking/` and `patterns/mating-patterns/`.
- **Post-game maintenance.** After a game (and, later, a Lichess analysis
  pass — see [[experiment-chess]] §"Future work"), write a
  `game-analyses/` post-mortem, and distil any recurring lesson into a
  durable `principles/` or `patterns/` page. Promote a page `draft →
  tested` once a game confirms it helped.
- **Lint.** Periodically check: every `[[wikilink]]` and `related_pages`
  entry resolves; every page is listed in its folder index; no page
  exceeds the cap; `description`/`triggers`/`tags` are present and useful
  (they are the only thing `search_wiki.py` matches); `status` is honest.
  Report; don't silently delete.
- **Validate after editing.** `search_wiki.py` runs standalone; the page
  reader is the harness's `read_reference`, so smoke-test search directly
  and confirm the skill still parses + tools register:
  ```bash
  cd backend/skills/chess/scripts && python3 search_wiki.py "back rank mate"
  cd "$OLDPWD" && .venv/bin/python -c "import sys; sys.path.insert(0,'backend'); \
    from skill_agent.registry import discover_skills; from pathlib import Path; \
    s=discover_skills([Path('backend/skills')])['chess']; \
    print(sorted(t.tool_name for t in s.tool_specs))"
  ```

## Open invariants (don't break these without a decision record)

- python-chess is the single source of truth for game state on the host.
- The bot loop runs serially, one move at a time, with a single
  `Game.lock`.
- Persistent ELO state lives at `games/agent_elo.json`. **It is updated
  only when the live git state is clean `main`.** Branches, dirty trees,
  and ad-hoc lobby games never touch it. Enforced in
  `BatchRunner._handle_game_finished` via `repo_state.is_ranked_context()`.
- All game data (`ranked.csv`, `experimental.csv`, `agent_elo.json`,
  per-game JSONs, batch state) is tracked in git, not gitignored. The
  experiment's history is auditable from `git log` alone.

## Baseline calibration invariants (Phase 1 floor)

The current Phase 1 batches measure the **bare model's** chess strength.
Any change to the items below alters what the baseline ELO means and
must be accompanied by a new decision record.

- **Initial agent ELO is 1200** — the conventional "casual amateur
  novice" anchor, documented as a convention rather than a canonical
  value. See
  [`../../knowledge-base/decisions/2026-05-25-initial-elo-1200.md`](../../knowledge-base/decisions/2026-05-25-initial-elo-1200.md)
  (current), which supersedes the earlier ELO-600 choice at
  [`../../knowledge-base/decisions/2026-05-24-initial-elo-600.md`](../../knowledge-base/decisions/2026-05-24-initial-elo-600.md).
- **Reasoning must precede the move.** The system prompt enforces an
  explicit ordered sequence; text the model produces after `make_move.py`
  is labelled "post-move" in the UI and discarded for analysis (recorded
  but not cited as the move's justification). See
  [`../../knowledge-base/decisions/2026-05-24-reason-before-move.md`](../../knowledge-base/decisions/2026-05-24-reason-before-move.md).
- **Curated turn memory (was: per-turn fresh context).** The agent sees
  system prompt + a synthetic prior exchange carrying exactly: the previous
  turn's prompt, its own reasoning note for the last move, and its standing
  plan (which persists until it writes a new one). Everything else is
  forgotten each turn; the FEN remains the complete game state.
  `clear_conversation()` is still only called between games. History:
  [`2026-05-24-per-turn-fresh-context.md`](../../knowledge-base/decisions/2026-05-24-per-turn-fresh-context.md)
  → [`2026-05-26-agent-turn-memory.md`](../../knowledge-base/decisions/2026-05-26-agent-turn-memory.md)
  → [`2026-06-10-structured-turn-memory.md`](../../knowledge-base/decisions/2026-06-10-structured-turn-memory.md)
  (current; also documents the fixed system-prompt-loss bug).
- **Aborted games are recorded but do not affect ELO.** When a player
  exception fires (context overflow, illegal move, browser crash), the
  game record carries `result=""` and an `aborted_reason`; ELO is
  unchanged; the batch advances. Same ADR as above.
- **Ranked-vs-experimental gating** decides which CSV a game lands in
  and whether ELO updates. Clean `main` → `ranked.csv` + ELO update;
  anything else → `experimental.csv` with ELO frozen. The frontend
  banner shows the current mode. See
  [`../../knowledge-base/decisions/2026-05-24-ranked-vs-experimental.md`](../../knowledge-base/decisions/2026-05-24-ranked-vs-experimental.md).

The full experiment design page lives at
[`../../knowledge-base/work/experiment-chess.md`](../../knowledge-base/work/experiment-chess.md).
The full ADR set for this experiment:

- [`2026-05-20-elo-and-batch-runner.md`](../../knowledge-base/decisions/2026-05-20-elo-and-batch-runner.md) — ELO formula, batch runner, opponent stepping (its §3 opponent-selection rule superseded by single-step, below)
- [`2026-05-23-ex3-llm-inference-server-architecture.md`](../../knowledge-base/decisions/2026-05-23-ex3-llm-inference-server-architecture.md) — self-hosted inference architecture
- [`2026-05-25-initial-elo-1200.md`](../../knowledge-base/decisions/2026-05-25-initial-elo-1200.md) — initial ELO 1200 (supersedes [`2026-05-24-initial-elo-600.md`](../../knowledge-base/decisions/2026-05-24-initial-elo-600.md))
- [`2026-05-24-reason-before-move.md`](../../knowledge-base/decisions/2026-05-24-reason-before-move.md)
- [`2026-05-24-per-turn-fresh-context.md`](../../knowledge-base/decisions/2026-05-24-per-turn-fresh-context.md)
- [`2026-05-26-single-step-matchmaking.md`](../../knowledge-base/decisions/2026-05-26-single-step-matchmaking.md) — single-step opponent selection (current)
