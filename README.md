# Chess Experiment

Phase 1 scaffold for the chess skill-acquisition experiment. The app is split into:

- `backend/` — FastAPI + python-chess orchestration.
- `frontend/` — React + Vite + chessground inspection UI.
- `diary/` — local testing notes for this experiment.

`progress/` is intentionally reserved for the later experiment-tracking system. Do not add it until the agent phase starts and the tracking schema is defined.

## Backend

```bash
cd experiments/chess/backend
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The backend serves:

- `GET /api/health`
- `GET /api/player-types`
- `POST /api/games`
- `GET /api/game`
- `GET /api/game/events`
- `POST /api/game/moves`
- `GET /api/games/{game_id}`
- `GET /api/games/{game_id}/events`
- `POST /api/games/{game_id}/moves`

The backend intentionally owns one current in-memory game at a time. Creating a game replaces the current game. Refreshing the frontend reloads `GET /api/game`; restarting the backend clears the game.

## Frontend

```bash
cd experiments/chess/frontend
npm install
npm run dev -- --host 127.0.0.1
```

The frontend expects the backend at `http://localhost:8000`. Override with:

```bash
VITE_API_BASE=http://localhost:8001 npm run dev
```

## Maia Setup

Maia is run locally through Lc0 as a UCI engine. Configure:

- `CHESS_LC0_PATH`, default `lc0`
- `CHESS_MAIA_WEIGHTS_DIR`, default `backend/engines/maia/weights` resolved inside this experiment's backend folder

On this machine, Lc0 has been installed with Homebrew and the Maia-1 weights have been downloaded into `backend/engines/maia/weights/`.

Expected weight filenames:

- `maia-1100.pb.gz`
- `maia-1200.pb.gz`
- `maia-1300.pb.gz`
- `maia-1400.pb.gz`
- `maia-1500.pb.gz`
- `maia-1600.pb.gz`
- `maia-1700.pb.gz`
- `maia-1800.pb.gz`
- `maia-1900.pb.gz`

Sources:

- https://github.com/CSSLab/maia-chess
- https://lczero.org/play/quickstart/
