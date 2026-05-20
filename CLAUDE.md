# CLAUDE.md — Chess Experiment

This file gives Claude Code (and any other LLM agent) the operating manual
for the chess experiment. Read it before doing work in this repo.

## What this repo is

A self-contained chess experiment with three sibling packages:

- `backend/` — FastAPI + python-chess service that owns one game at a time,
  drives bot turns, persists state to `games/`, runs batch experiments,
  and serves the React frontend over SSE.
- `chesscom-driver/` — Playwright-backed Python library that drives a real
  Chrome window to play chess.com Engine bots. Used as an opponent
  provider; loaded as a `Player` ABC adapter from the backend.
- `frontend/` — React + Vite + chessground UI. Lobby for ad-hoc games,
  a batch page for running calibration sequences, and a per-game board
  page with live Stockfish evaluation.

The agent itself is `pydantic-ai` + the `skillful-agent` SDK; it plays
white and only ever invokes two skill scripts (`list_legal_moves.py`,
`make_move.py`) — see [`backend/skills/chess-player/`](backend/skills/chess-player/).

## Workspace layout

This is a **uv workspace**. The root `pyproject.toml` declares `backend`
and `chesscom-driver` as members. One shared venv lives at `./.venv/`.

```bash
uv sync --all-packages         # install everything (run from chess/, backend/, or chesscom-driver/)
uv run uvicorn app.main:app    # start backend (from backend/)
bun run dev                    # start frontend (from frontend/)
```

`bun`, not `npm`, for the frontend. The user explicitly prefers it.

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
uv run python -c "from app.main import app; print('ok')"   # backend imports
uv run pytest tests/ -v                                     # backend tests if applicable
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
