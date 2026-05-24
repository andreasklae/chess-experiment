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
two skill scripts (`list_legal_moves.py`, `make_move.py`) — see
[`backend/skills/chess-player/`](backend/skills/chess-player/).

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
- **Only agent games are logged to `games.csv`.** Human-vs-Maia ad-hoc
  testing is not part of the experiment record.
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

## Workflow norms

### Git commits

- **Never add yourself (Claude) as a co-author.** No `Co-Authored-By:
  Claude <...>` trailers. The user authors every commit; you're the tool
  that produced the patch.
- Commits should be detailed and include rationale, not just a list of
  files changed. The git history is part of the thesis's reproducibility
  story — `git log` should read like a methods journal.
- The chess experiment is a fresh git repo as of 2026-05-20; the HEAD SHA
  is stamped into every agent game's CSV row (`skill_repo_sha`). Commits
  that change agent behaviour (skills, prompts, model config, driver)
  should be a single coherent change so the SHA boundary is meaningful.

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
- Persistent ELO state lives at `games/agent_elo.json` and is written
  only by `BatchRunner`. Ad-hoc games never touch it.
- `skill_repo_sha` is the chess repo HEAD; if you change what counts as
  "the agent configuration", update the rationale in the decision record.
