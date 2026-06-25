import type { AgentElo, Batch, BatchPool, GameState, GameSummary, PlayerConfig, PlayerTypeInfo } from './types';

// API base resolution, in priority order:
//  1. VITE_API_BASE env (explicit override).
//  2. When the page is served from a non-localhost host (e.g. a phone loading
//     it over the LAN at 192.168.x.y:5173), talk to the backend on the SAME
//     host, port 8000 — so the same build works on the laptop and the phone
//     without rebuilding. This requires the backend to bind 0.0.0.0.
//  3. Fall back to localhost:8000 for the plain desktop dev case.
function resolveApiBase(): string {
  const explicit = import.meta.env.VITE_API_BASE;
  if (explicit) return explicit;
  if (typeof window !== 'undefined') {
    const { hostname, protocol } = window.location;
    if (hostname && hostname !== 'localhost' && hostname !== '127.0.0.1') {
      return `${protocol}//${hostname}:8000`;
    }
  }
  return 'http://localhost:8000';
}

const API_BASE = resolveApiBase();

// ── Global "busy" tracker ───────────────────────────────────────────────────
// Every request flows through request(); we count in-flight calls and, after a
// short debounce, flip a `busy` flag so the UI can show a loading indicator.
// The debounce keeps fast polls (every 1–2s) from flashing the indicator, while
// a slow/blocking call (e.g. the backend launching a chess.com browser, which
// blocks ~30s) reliably surfaces it instead of the UI looking frozen.
const BUSY_DEBOUNCE_MS = 400;
let inflight = 0;
let busy = false;
let busyTimer: ReturnType<typeof setTimeout> | null = null;
const busyListeners = new Set<(b: boolean) => void>();

function emitBusy() {
  for (const l of busyListeners) l(busy);
}
function requestStarted() {
  inflight += 1;
  if (inflight === 1 && busyTimer === null) {
    busyTimer = setTimeout(() => {
      busyTimer = null;
      if (inflight > 0 && !busy) {
        busy = true;
        emitBusy();
      }
    }, BUSY_DEBOUNCE_MS);
  }
}
function requestEnded() {
  inflight = Math.max(0, inflight - 1);
  if (inflight === 0) {
    if (busyTimer !== null) {
      clearTimeout(busyTimer);
      busyTimer = null;
    }
    if (busy) {
      busy = false;
      emitBusy();
    }
  }
}

/** Subscribe to the global busy flag (true once a request has been pending
 *  longer than the debounce). Calls back immediately with the current value;
 *  returns an unsubscribe function. */
export function subscribeBusy(cb: (b: boolean) => void): () => void {
  busyListeners.add(cb);
  cb(busy);
  return () => busyListeners.delete(cb);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  requestStarted();
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...init?.headers,
      },
    });
  } finally {
    requestEnded();
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed: ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function playerTypes(): Promise<PlayerTypeInfo[]> {
  return request<PlayerTypeInfo[]>('/api/player-types');
}

export function createGame(white: PlayerConfig, black: PlayerConfig): Promise<GameState> {
  return request<GameState>('/api/games', {
    method: 'POST',
    body: JSON.stringify({ white, black }),
  });
}

export function currentGame(): Promise<GameState> {
  return request<GameState>('/api/game');
}

export function submitMove(move: string): Promise<GameState> {
  return request<GameState>('/api/game/moves', {
    method: 'POST',
    body: JSON.stringify({ move }),
  });
}

export function gameEventsUrl(gameId?: string): string {
  // Per-game stream when an id is given — watching an old game must not be
  // hijacked by state pushes from a different live game (e.g. a background
  // puzzle run).
  return gameId ? `${API_BASE}/api/games/${gameId}/events` : `${API_BASE}/api/game/events`;
}

export function agentEventsUrl(gameId: string): string {
  return `${API_BASE}/api/games/${gameId}/agent-events`;
}

export function listGames(): Promise<GameSummary[]> {
  return request<GameSummary[]>('/api/games');
}

export function getGame(gameId: string): Promise<GameState> {
  return request<GameState>(`/api/games/${gameId}`);
}

export function loadGame(gameId: string): Promise<GameState> {
  return request<GameState>(`/api/games/${gameId}/load`, { method: 'POST' });
}

export function deleteGame(gameId: string): Promise<void> {
  return request<void>(`/api/games/${gameId}`, { method: 'DELETE' });
}

export function pauseGame(gameId: string): Promise<GameState> {
  return request<GameState>(`/api/games/${gameId}/pause`, { method: 'POST' });
}

export function resumeGame(gameId: string): Promise<GameState> {
  return request<GameState>(`/api/games/${gameId}/resume`, { method: 'POST' });
}

// ── Batches ───────────────────────────────────────────────────────────────

export function listBatches(): Promise<Batch[]> {
  return request<Batch[]>('/api/batches');
}

export function getActiveBatch(): Promise<Batch | null> {
  return request<Batch | null>('/api/batches/active');
}

export function createBatch(label: string, pool: BatchPool, totalGames: number): Promise<Batch> {
  return request<Batch>('/api/batches', {
    method: 'POST',
    body: JSON.stringify({ label, pool, total_games: totalGames }),
  });
}

export function getBatch(batchId: string): Promise<Batch> {
  return request<Batch>(`/api/batches/${batchId}`);
}

export function startBatch(batchId: string): Promise<Batch> {
  return request<Batch>(`/api/batches/${batchId}/start`, { method: 'POST' });
}

export function pauseBatch(batchId: string): Promise<Batch> {
  return request<Batch>(`/api/batches/${batchId}/pause`, { method: 'POST' });
}

export function stopBatch(batchId: string): Promise<Batch> {
  return request<Batch>(`/api/batches/${batchId}/stop`, { method: 'POST' });
}

export function deleteBatch(batchId: string): Promise<void> {
  return request<void>(`/api/batches/${batchId}`, { method: 'DELETE' });
}

export function getAgentElo(): Promise<AgentElo> {
  return request<AgentElo>('/api/agent-elo');
}

export function resetAgentElo(): Promise<AgentElo> {
  return request<AgentElo>('/api/agent-elo/reset', { method: 'POST' });
}

// ── Repo state ────────────────────────────────────────────────────────────
//
// Surfaces whether the next batch will be ranked (clean main) or
// experimental (any other git state). The frontend renders this as a
// banner so the operator knows what mode they're working in.

export interface RepoState {
  phase: 'ranked' | 'experimental';
  reason: string;
  branch: string;
  commit_sha: string;
  short_sha: string;
  dirty: boolean;
  is_repo: boolean;
}

export function getRepoState(): Promise<RepoState> {
  return request<RepoState>('/api/repo-state');
}

// ---- Puzzle benchmark ----

export interface PuzzleInfo {
  id: string; topic: string; rating: number; band: string; themes: string[];
}
export interface PuzzleAttempt {
  ply: number; fen_before: string; expected_uci: string; expected_san: string;
  played_uci: string | null; played_san: string | null; correct: boolean;
  accepted_as: string | null; reasoning?: string;
}
export interface PuzzleResult {
  puzzle_id: string; topic: string; band: string; rating: number; themes: string[];
  agent_color: string; solved: boolean; solved_plies: number; total_plies: number;
  aborted_reason: string | null; attempts: PuzzleAttempt[];
}

export function listPuzzles(): Promise<{ total: number; topics: Record<string, number>; puzzles: PuzzleInfo[] }> {
  return fetch(`${API_BASE}/api/puzzles`).then((r) => r.json());
}

export function startPuzzleRun(body: { mode?: PuzzleRunMode; topics?: string[]; difficulties?: string[]; per_topic?: number; limit?: number; ids?: string[] }): Promise<{ started: boolean; n: number; out_path: string }> {
  return fetch(`${API_BASE}/api/puzzles/run`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  }).then(async (r) => { if (!r.ok) throw new Error((await r.json()).detail || 'failed'); return r.json(); });
}

export function puzzleRunStatus(): Promise<{ running: boolean; idx: number; n: number; completed: number; solved: number; results: PuzzleResult[] }> {
  return fetch(`${API_BASE}/api/puzzles/run`).then((r) => r.json());
}

export function puzzleRunEventsUrl(): string {
  return `${API_BASE}/api/puzzles/run/events`;
}

export type PuzzleRunMode = 'all' | 'unsolved' | 'untested' | 'failed';

export interface PuzzleProgressOverview {
  totals: { solved: number; failed: number; untested: number; total: number };
  by_topic: Record<string, { solved: number; failed: number; untested: number; total: number }>;
  by_difficulty: Record<string, { solved: number; failed: number; untested: number; total: number }>;
  puzzles: { id: string; topic: string; difficulty: string; rating: number; title: string;
             status: 'solved' | 'failed' | 'untested'; solved_plies: number | null;
             total_plies: number; ts: string | null }[];
}

export function puzzleProgress(): Promise<PuzzleProgressOverview> {
  return fetch(`${API_BASE}/api/puzzles/progress`).then((r) => r.json());
}

export function abortPuzzleRun(): Promise<{ aborting: boolean; completed: number }> {
  return fetch(`${API_BASE}/api/puzzles/run/abort`, { method: 'POST' })
    .then(async (r) => { if (!r.ok) throw new Error((await r.json()).detail || 'failed'); return r.json(); });
}
