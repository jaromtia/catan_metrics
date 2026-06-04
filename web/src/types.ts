export type Resource = "brick" | "lumber" | "wool" | "grain" | "ore";
export type ResourceMap = Record<string, number>;

export interface PlayerStateDTO {
  resources: ResourceMap;
  dev_cards: Record<string, number>;
  dev_cards_played: Record<string, number>;
  knights_played: number;
  settlements: number[];
  cities: number[];
  roads: number[];
  bonus_vp?: number;
}

export type GameMode = "strict" | "dev";

export interface BoardDTO {
  hexes: number[][];
  terrain: Record<string, string>;
  numbers: Record<string, number>;
  ports: { type: string; vertices: number[] }[];
  robber: number[] | null;
}

export interface GameStateDTO {
  board: BoardDTO;
  player_order: string[];
  players: Record<string, PlayerStateDTO>;
  phase: string;
  current_index: number;
  turn_number: number;
  dice: number[] | null;
  has_rolled: boolean;
  bank: ResourceMap;
  dev_deck: Record<string, number>;
  robber: number[] | null;
  longest_road_holder: string | null;
  largest_army_holder: string | null;
  winner: string | null;
  pending_discards: Record<string, number>;
  robber_pending: boolean;
  dev_played_this_turn: boolean;
  dev_bought_this_turn: Record<string, number>;
  mode?: GameMode;
}

export interface HexLayout {
  coord: number[];
  center: number[];
  terrain: string;
  number: number | null;
  vertices: number[];
}

export interface LayoutDTO {
  hexes: HexLayout[];
  vertices: Record<string, number[]>;
  edges: Record<string, number[]>;
  ports: { type: string; vertices: number[]; pos: number[] }[];
}

export interface PortSlotDTO {
  edge: number;
  vertices: number[];
  pos: number[];
}

export interface PortPlacement {
  type: string;
  edge: number;
}

export interface BoardTemplateDTO {
  hexes: { coord: number[]; center: number[]; vertices: number[] }[];
  vertices: Record<string, number[]>;
  edges: Record<string, number[]>;
  terrain_counts: Record<string, number>;
  number_counts: Record<string, number>;
  port_counts: Record<string, number>;
  perimeter_edges: PortSlotDTO[];
  default_ports: PortPlacement[];
}

export interface CustomLayout {
  terrain: string[];
  numbers: number[];
  ports: PortPlacement[];
}

export interface PlayerMetricsDTO {
  production: Record<string, number>;
  production_total: number;
  expected_production: number;
  luck: number;
  cards_discarded: number;
  steals_made: number;
  cards_stolen_from_me: number;
  robber_blocked: number;
  knights_played: number;
  dev_bought: Record<string, number>;
  dev_played: Record<string, number>;
  trades_domestic: number;
  trades_maritime: number;
  trade_net: Record<string, number>;
  builds: [number, number, string][];
  vp_timeline: [number, number, number][];
  hand_timeline: [number, number][];
  pip_timeline: [number, number][];
  final_vp: number;
  final_pip_equity: number;
}

export interface MetricsDTO {
  player_order: string[];
  num_turns: number;
  winner: string | null;
  dice_histogram: Record<string, number>;
  dice_total: number;
  players: Record<string, PlayerMetricsDTO>;
}

export interface EventDTO {
  seq: number;
  ts: number;
  type: string;
  [k: string]: unknown;
}

export interface GameSummary {
  game_id: string;
  phase: string;
  turn: number;
  winner: string | null;
  players: string[];
  mode?: GameMode;
}
