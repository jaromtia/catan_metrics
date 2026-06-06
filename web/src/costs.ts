import type { ResourceMap } from "./types";
import type { Piece } from "./guide";

export const BUILD_COSTS: Record<"road" | "settlement" | "city", Partial<Record<string, number>>> = {
  road: { brick: 1, lumber: 1 },
  settlement: { brick: 1, lumber: 1, wool: 1, grain: 1 },
  city: { ore: 3, grain: 2 },
};

const LIMITS = { settlement: 5, city: 4, road: 15 } as const;

export function canAffordCost(resources: ResourceMap, cost: Partial<Record<string, number>>) {
  return Object.entries(cost).every(([r, n]) => (resources[r] ?? 0) >= (n ?? 0));
}

/** Whether the player has resources and spare pieces to build (ignores board placement). */
export function canAffordBuild(
  resources: ResourceMap,
  piece: Piece,
  built: { settlements: number; cities: number; roads: number },
): boolean {
  if (piece === "robber") return true;
  const cost = BUILD_COSTS[piece];
  if (!canAffordCost(resources, cost)) return false;
  if (piece === "road") return built.roads < LIMITS.road;
  if (piece === "settlement") return built.settlements < LIMITS.settlement;
  return built.cities < LIMITS.city && built.settlements > 0;
}
