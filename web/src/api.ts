import { getClientId } from "./session";
import type {
  BoardTemplateDTO,
  CustomLayout,
  EventDTO,
  GameStateDTO,
  GameSummary,
  LayoutDTO,
  MetricsDTO,
} from "./types";

/** fetch wrapper that tags every request with this browser's client id, so
 * the server can scope the lobby to "my games" (see session.ts). */
function call(url: string, init: RequestInit = {}): Promise<Response> {
  return fetch(url, {
    ...init,
    headers: { "X-Catan-Client": getClientId(), ...(init.headers || {}) },
  });
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      detail = (await res.json()).detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
}

export const api = {
  listGames: () => call("/api/games").then(json<GameSummary[]>),

  createGame: (
    players: string[],
    board: string,
    seed: number | null,
    layout?: CustomLayout,
    mode: string = "strict",
  ) =>
    call("/api/games", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ players, board, seed, layout, mode }),
    }).then(json<{ game_id: string; mode: string; state: GameStateDTO }>),

  setMode: (id: string, mode: string) =>
    call(`/api/games/${id}/mode`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ mode }),
    }).then(json<{ ok: boolean; mode: string }>),

  getBoardTemplate: () =>
    call("/api/board_template").then(json<BoardTemplateDTO>),

  getState: (id: string, at?: number) =>
    call(`/api/games/${id}/state${at != null ? `?at=${at}` : ""}`).then(json<GameStateDTO>),

  getLayout: (id: string) => call(`/api/games/${id}/layout`).then(json<LayoutDTO>),

  getEvents: (id: string) => call(`/api/games/${id}/events`).then(json<EventDTO[]>),

  getMetrics: (id: string) => call(`/api/games/${id}/metrics`).then(json<MetricsDTO>),

  deleteGame: (id: string) =>
    call(`/api/games/${id}`, { method: "DELETE" }).then(json<{ ok: boolean }>),

  sendCommandText: (id: string, line: string) =>
    call(`/api/games/${id}/command_text`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ line }),
    }).then(json<{ ok: boolean; events: string[]; state: GameStateDTO }>),

  sendCommand: (id: string, command: Record<string, unknown>) =>
    call(`/api/games/${id}/commands`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(command),
    }).then(json<{ ok: boolean; events: string[]; state: GameStateDTO }>),
};
