# Chess Frontend

React + Vite inspection UI for the Phase 1 chess experiment scaffold.

Run locally:

```bash
npm install
npm run dev -- --host 127.0.0.1
```

The board uses chessground. The backend remains the rules authority and orchestrator; the frontend only creates games, loads the current backend-owned game on refresh, streams state, and submits human moves.
