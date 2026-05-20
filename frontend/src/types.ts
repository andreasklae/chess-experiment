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
