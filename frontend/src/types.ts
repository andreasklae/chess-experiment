export type PlayerKind = 'human' | 'maia' | 'agent' | 'chesscom';
export type Color = 'white' | 'black';

export interface PlayerConfig {
  type: PlayerKind;
  elo?: number | null;
}

export interface PlayerTypeInfo {
  type: PlayerKind;
  elo_required: boolean;
  allowed_elos: number[];
}

export interface GameState {
  game_id: string;
  fen: string;
  turn: Color;
  white: PlayerConfig;
  black: PlayerConfig;
  legal_moves: string[];
  uci_moves: string[];
  san_moves: string[];
  status: 'active' | 'finished';
  result: string | null;
  termination: string | null;
  eval_cp: number | null;
  eval_mate: number | null;
  paused: boolean;
}

export interface GameSummary {
  game_id: string;
  white: PlayerConfig;
  black: PlayerConfig;
  status: 'active' | 'finished';
  result: string | null;
  turn: Color;
  move_count: number;
  last_move_san: string | null;
  created_at: string;
}

export type BatchStatus = 'pending' | 'running' | 'paused' | 'completed' | 'stopped' | 'failed';
export type BatchPool = 'maia' | 'chesscom';
export type BatchResult = 'win' | 'loss' | 'draw' | null;

export interface GameRecord {
  game_id: string;
  opponent_elo: number;
  result: BatchResult;
  agent_elo_before: number;
  agent_elo_after: number;
}

export interface Batch {
  batch_id: string;
  label: string;
  pool: BatchPool;
  total_games: number;
  status: BatchStatus;
  created_at: string;
  games: GameRecord[];
  current_game_id: string | null;
  last_error: string;
}

export interface AgentElo {
  elo: number;
  games_played: number;
  last_result: BatchResult;
  streak: number;
}
