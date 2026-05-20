# Chess Backend

FastAPI backend for the Phase 1 chess experiment scaffold.

Run locally:

```bash
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run tests:

```bash
uv run pytest
```

The backend owns one current in-memory game. `POST /api/games` creates/replaces it; `GET /api/game`, `GET /api/game/events`, and `POST /api/game/moves` operate on it. ID-based routes remain for compatibility, but the frontend uses the singleton routes.

Persistent game logs and the future progress tracker are intentionally deferred.
