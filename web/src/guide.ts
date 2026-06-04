import type { GameStateDTO } from "./types";

/** Mirror of the backend's setup snake-draft expectation. During setup the
 *  engine's current_index stays at 0, so this is how we know who places next. */
export function setupExpected(
  state: GameStateDTO,
): { kind: string; player: string } | null {
  const order = state.player_order;
  const snake = [...order, ...[...order].reverse()];
  const n = order.length;
  const settlements = order.reduce((a, p) => a + state.players[p].settlements.length, 0);
  const roads = order.reduce((a, p) => a + state.players[p].roads.length, 0);
  if (settlements >= 2 * n && roads >= 2 * n) return null;
  if (settlements === roads) return { kind: "settlement", player: snake[settlements] };
  return { kind: "road", player: snake[roads] };
}

export function expectedActor(state: GameStateDTO): string {
  if (state.phase === "setup") {
    const exp = setupExpected(state);
    if (exp) return exp.player;
  }
  return state.player_order[state.current_index];
}

export type Piece = "settlement" | "city" | "road" | "robber";

export interface GuidedStep {
  key: "setup-settlement" | "setup-road" | "discard" | "robber" | "roll" | "build" | "done";
  player: string | null;
  title: string;
  hint: string;
  pieces: Piece[];          // pieces the player may place in this step
}

/** The single thing the guided (strict) UI should let the player do right now. */
export function guidedStep(state: GameStateDTO): GuidedStep {
  if (state.winner) {
    return { key: "done", player: state.winner, title: `🏆 ${state.winner} wins!`, hint: "Game over — review the metrics.", pieces: [] };
  }
  if (state.phase === "setup") {
    const exp = setupExpected(state);
    if (exp?.kind === "settlement") {
      return { key: "setup-settlement", player: exp.player, title: `Setup · ${exp.player}: place a settlement`, hint: "Click any open intersection (distance rule enforced).", pieces: ["settlement"] };
    }
    if (exp?.kind === "road") {
      return { key: "setup-road", player: exp.player, title: `Setup · ${exp.player}: place a road`, hint: "Place a road touching the settlement you just placed.", pieces: ["road"] };
    }
  }
  const cur = state.player_order[state.current_index];
  if (Object.keys(state.pending_discards).length > 0) {
    return { key: "discard", player: null, title: "A 7 was rolled · discards required", hint: "Each listed player discards half (rounded down) of their hand.", pieces: [] };
  }
  if (state.robber_pending) {
    return { key: "robber", player: cur, title: `${cur}: move the robber`, hint: "Pick a hex with the Robber, then choose who to steal from.", pieces: ["robber"] };
  }
  if (!state.has_rolled) {
    return { key: "roll", player: cur, title: `${cur}: roll the dice`, hint: "Enter the two dice values you rolled to produce resources.", pieces: [] };
  }
  return { key: "build", player: cur, title: `${cur}: build, trade, or end turn`, hint: "Place pieces, trade, play development cards, then end your turn.", pieces: ["settlement", "city", "road"] };
}
