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
| `GET` | `/api/health` | Health check |

## Architecture

- **Single active game.** `GameService._game` is one slot. Creating a new
  game closes the prior one's players.
- **Agent is white-only.** Enforced by schema validators and the frontend.
- **Only agent games are logged to `games.csv`.** Human-vs-Maia ad-hoc
  testing is not part of the experiment record.
- **Each batch game gets a fresh `Agent` instance.** No conversation state
  carries between games.
- **Stockfish eval is UX-only.** The agent has no access to it.

## Packages

- `app/` — backend application
- `chesscom_driver/` — Playwright driver for chess.com Engine bots (lives
  here rather than as a separate workspace member to avoid Python's `.pth`
  path processor silently skipping the em-dash in the project path)
