import type { GameState, GameSummary, PlayerConfig, PlayerTypeInfo } from './types';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });
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

export function gameEventsUrl(): string {
  return `${API_BASE}/api/game/events`;
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
