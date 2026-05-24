# Chess Backend

FastAPI + python-chess backend for the Phase 1 chess experiment.

## Running

Run from `experiments/chess/` (workspace root), not from inside `backend/`:

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If imports fail, run `../scripts/repair-env.sh` first.

## Tests

```bash
uv run pytest
```

## Environment

Copy or edit `backend/.env`. Key variables:

| Variable | Purpose |
|---|---|
| `SKILL_AGENT_EX3_BASE_URL` | vLLM base URL (e.g. `http://localhost:11500/v1`); takes priority when set |
| `SKILL_AGENT_OPENAI_MODEL` | Model name (e.g. `google/gemma-4-31B-it`) |
| `SKILL_AGENT_AZURE_ENDPOINT` | Azure OpenAI endpoint (inactive when EX3 is set) |
| `CHESS_LC0_PATH` | Path to lc0 binary |
| `CHESS_STOCKFISH_PATH` | Path to Stockfish binary (UX eval needle only) |

## API surface

### Games

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/games` | Create a new game (replaces active game) |
| `GET` | `/api/games` | List all game summaries |
| `GET` | `/api/games/{id}` | Get game state |
| `GET` | `/api/games/{id}/events` | SSE stream of game state updates |
| `POST` | `/api/games/{id}/moves` | Submit a human move |
| `DELETE` | `/api/games/{id}` | Delete a game |
| `POST` | `/api/games/{id}/load` | Load a saved game as the active game |
| `GET` | `/api/game` | Shorthand: current active game state |
| `GET` | `/api/game/events` | Shorthand: current active game SSE stream |
| `POST` | `/api/game/moves` | Shorthand: submit human move to active game |

### Batches

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/batches` | Create a new batch |
| `GET` | `/api/batches` | List all batches |
| `GET` | `/api/batches/{id}` | Get batch state |
| `POST` | `/api/batches/{id}/start` | Start or resume a batch |
| `POST` | `/api/batches/{id}/stop` | Stop a running batch |
| `DELETE` | `/api/batches/{id}` | Delete a batch |
| `GET` | `/api/batches/{id}/events` | SSE stream of batch progress |

### ELO / misc

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/elo` | Current agent ELO state |
| `POST` | `/api/elo/reset` | Reset ELO to initial value (600) |
| `GET` | `/api/player-types` | Available player types and ELO ranges |
| `GET` | `/api/repo-state` | Live git state + ranked/experimental phase (drives the frontend banner) |
| `GET` | `/api/health` | Health check |

## Architecture

- **Single active game.** `GameService._game` is one slot. Creating a new
  game closes the prior one's players.
- **Agent is white-only.** Enforced by schema validators and the frontend.
- **Only agent games are logged.** They go to `games/ranked.csv` (when
  on clean `main`, also updates ELO) or `games/experimental.csv` (any
  other git state, ELO frozen). Human-vs-Maia ad-hoc games are not
  logged. See `Ranked vs experimental` below.
- **Each batch game gets a fresh `Agent` instance.** No conversation state
  carries between games.
- **Each turn within a game gets fresh context too.** `AgentPlayer.get_move()`
  calls `self._agent.clear_conversation()` at the top of every turn. See
  Context management below.
- **Stockfish eval is UX-only.** The agent has no access to it.

## Context management

Baseline calibration runs with **per-turn fresh context**: the agent enters
each turn seeing only the system prompt, skill list, and one user message
(opponent's last move + FEN). No accumulated history from prior turns.
The FEN encodes complete game state; cross-turn memory is a separate
experimental variable that future configurations will introduce and measure
against this baseline.

Implementation: `AgentPlayer.get_move()` calls
`self._agent.clear_conversation()` before building the prompt
([`app/agent_player.py`](app/agent_player.py)).

Error handling: when a model rejects a request for context overflow (or any
other reason), `skill_agent` raises `AgentContextOverflowError`, the chess
backend converts it to a `PlayerError`, and the game is aborted with the
reason recorded in `ranked.csv` or `experimental.csv` under the
`aborted_reason` column. ELO is unchanged for aborted games; the batch
advances to the next opponent.

Full rationale and consequences:
[`knowledge-base/decisions/2026-05-24-per-turn-fresh-context.md`](../../../knowledge-base/decisions/2026-05-24-per-turn-fresh-context.md).

## Ranked vs experimental

Every agent game lands in one of two CSVs based on the **live git state**
at game-record time:

| State | CSV | Updates `agent_elo.json`? |
|---|---|---|
| On `main` with a clean working tree | `games/ranked.csv` | yes |
| Anything else (branch, dirty tree, no repo) | `games/experimental.csv` | no |

Policy lives in [`app/repo_state.py`](app/repo_state.py)
(`is_ranked_context()` / `current_phase()`). Enforcement is in two places:

1. [`app/logging_service.py`](app/logging_service.py) — `record_game`
   routes the row to the correct CSV.
2. [`app/batch_runner.py`](app/batch_runner.py) — `_handle_game_finished`
   refuses to update ELO unless `is_ranked_context()` is true.

The frontend polls [`/api/repo-state`](app/main.py) every 5 seconds and
shows a coloured banner on the lobby and batch pages so the operator
knows which mode the next batch will run in.

**All game data is tracked in git** — both CSVs, `agent_elo.json`, every
per-game board JSON and reasoning JSON, and the batch state files. The
intent is that `git revert` on a PR reverses both the code change and
its calibration rows together. See:
[`knowledge-base/decisions/2026-05-24-ranked-vs-experimental.md`](../../../knowledge-base/decisions/2026-05-24-ranked-vs-experimental.md).

## Packages

- `app/` — backend application
- `chesscom_driver/` — Playwright driver for chess.com Engine bots (lives
  here rather than as a separate workspace member to avoid Python's `.pth`
  path processor silently skipping the em-dash in the project path)
