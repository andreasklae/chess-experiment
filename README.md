# Chess Experiment

Phase 1 of the chess skill-acquisition experiment. The agent (Gemma 4 31B-it
via eX3 vLLM) plays white against bots from two opponent pools: Maia (1100–1900
ELO) and chess.com Engine bots (250–3200 ELO). Games run in batches with
adaptive ELO matchmaking. Results are logged to `backend/games/games.csv`.

**Read first:**
- [`CLAUDE.md`](CLAUDE.md) — operating manual for working in this repo (conventions, invariants, baseline calibration rules, ADR list)
- [`backend/README.md`](backend/README.md) — backend API surface, architecture, context management
- [`knowledge-base/work/experiment-chess.md`](../../knowledge-base/work/experiment-chess.md) — full experiment design page (methodology, opponent pool, logging schema)

## Layout

```
backend/          FastAPI + python-chess orchestration + agent harness
backend/app/      Backend application code
backend/chesscom_driver/  Playwright driver for chess.com Engine bots
backend/skills/   Skill scripts used by the agent (list_legal_moves, make_move)
backend/games/    Persisted game state + CSV log
backend/batches/  Batch state files
chesscom-driver/  Original standalone package — kept for reference, not on import path
frontend/         React + Vite + chessground UI
scripts/          Maintenance scripts (repair-env.sh)
```

## Running

```bash
# First time / after wiping .venv:
./scripts/repair-env.sh

# Start eX3 vLLM server (required for agent games):
python3 ../../software/ex3/serve.py

# Start backend (from experiments/chess/backend/):
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000

# Start frontend (from experiments/chess/frontend/):
bun run dev
```

The frontend opens at `http://localhost:5173`. The backend API is at
`http://localhost:8000`.

## Opponent pools

| Pool | ELO range | Notes |
|---|---|---|
| Maia | 1100–1900 | Local lc0 + Maia-1 weights in `backend/engines/maia/weights/` |
| chess.com | 250–3200 | 25 discrete steps; driven via Playwright (requires Chrome) |

## Agent

The agent is `pydantic-ai` + `skillful-agent` SDK. Backend selection is
controlled by `backend/.env`:

- `SKILL_AGENT_EX3_BASE_URL` set → local Gemma 4 31B-it on eX3 (active)
- `SKILL_AGENT_AZURE_ENDPOINT` set → Azure OpenAI (inactive)
- Neither → OpenAI public API

Current model: `google/gemma-4-31B-it` at `http://localhost:11500/v1`.

Baseline calibration invariants (see [`CLAUDE.md`](CLAUDE.md) for the full list and ADR links):
- Initial ELO **600** — [`2026-05-24-initial-elo-600.md`](../../knowledge-base/decisions/2026-05-24-initial-elo-600.md)
- Reasoning must precede the move — [`2026-05-24-reason-before-move.md`](../../knowledge-base/decisions/2026-05-24-reason-before-move.md)
- Per-turn fresh context — [`2026-05-24-per-turn-fresh-context.md`](../../knowledge-base/decisions/2026-05-24-per-turn-fresh-context.md)
- Ranked vs experimental logging (PR-as-version) — [`2026-05-24-ranked-vs-experimental.md`](../../knowledge-base/decisions/2026-05-24-ranked-vs-experimental.md)

## Maia setup

Lc0 installed via Homebrew. Maia-1 weights in `backend/engines/maia/weights/`:
`maia-1100.pb.gz` through `maia-1900.pb.gz`.

Sources: https://github.com/CSSLab/maia-chess · https://lczero.org/play/quickstart/

## Broken venv

If imports fail after `uv sync`, run `./scripts/repair-env.sh`. See
[`CLAUDE.md`](CLAUDE.md) for the root cause (em-dash in project path bypasses
Python's `.pth` processor).
