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
local Gemma 4 31B-it model on eX3 via vLLM. It plays white and invokes
four skill scripts:

- `show_position.py` — ASCII board + material balance + attack/defense map
- `imagine_move.py --uci <move>` — one-ply look-ahead with tactical report
- `list_legal_moves.py` — annotated markdown table of legal moves
- `make_move.py --uci <move>` — commits the move

See [`backend/skills/chess-player/`](backend/skills/chess-player/). The
material+PST static eval previously exposed as a separate
`evaluate_position.py` script is now folded into `show_position` and
`imagine_move` output (one line each); the eval helpers themselves live
in `backend/skills/chess-player/scripts/_eval.py` and are not exposed
to the agent.

SDK-bundled native tools (`manage_todos`, thread/spawn tools, file
read/write, etc.) and native skills (`web-search-free`) are explicitly
disabled in `AgentConfig` for this experiment — the chess agent only
needs `use_skill` and `run_script`, and a narrower tool surface
prevents the looping behaviour observed when those were available.
See `decisions/2026-05-26-stabilization.md`.

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

- **Initial agent ELO is 600.** Informed prior from observation, not the
  conventional 1200. See
  [`../../knowledge-base/decisions/2026-05-24-initial-elo-600.md`](../../knowledge-base/decisions/2026-05-24-initial-elo-600.md).
- **Reasoning must precede the move.** The system prompt enforces an
  explicit ordered sequence; text the model produces after `make_move.py`
  is labelled "post-move" in the UI and discarded for analysis (recorded
  but not cited as the move's justification). See
  [`../../knowledge-base/decisions/2026-05-24-reason-before-move.md`](../../knowledge-base/decisions/2026-05-24-reason-before-move.md).
- **Per-turn fresh context.** `AgentPlayer.get_move()` calls
  `self._agent.clear_conversation()` at the start of every turn. The
  agent sees only system prompt + skill list + one user message (opponent
  move + FEN). No cross-turn memory. The FEN is the complete game state.
  See
  [`../../knowledge-base/decisions/2026-05-24-per-turn-fresh-context.md`](../../knowledge-base/decisions/2026-05-24-per-turn-fresh-context.md).
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

- [`2026-05-20-elo-and-batch-runner.md`](../../knowledge-base/decisions/2026-05-20-elo-and-batch-runner.md) — ELO formula, batch runner, opponent stepping
- [`2026-05-23-ex3-llm-inference-server-architecture.md`](../../knowledge-base/decisions/2026-05-23-ex3-llm-inference-server-architecture.md) — self-hosted inference architecture
- [`2026-05-24-initial-elo-600.md`](../../knowledge-base/decisions/2026-05-24-initial-elo-600.md)
- [`2026-05-24-reason-before-move.md`](../../knowledge-base/decisions/2026-05-24-reason-before-move.md)
- [`2026-05-24-per-turn-fresh-context.md`](../../knowledge-base/decisions/2026-05-24-per-turn-fresh-context.md)
