const NAMED: Record<string, string> = {
  red: "#e2483d",
  blue: "#3b82f6",
  white: "#e5e7eb",
  orange: "#f59e0b",
  green: "#22c55e",
  brown: "#92400e",
};

const PALETTE = ["#e2483d", "#3b82f6", "#e5e7eb", "#f59e0b", "#22c55e", "#a855f7"];

/** Colors a player may pick at game creation. */
export const COLOR_CHOICES: { name: string; hex: string }[] = [
  { name: "red", hex: "#e2483d" },
  { name: "blue", hex: "#3b82f6" },
  { name: "white", hex: "#e5e7eb" },
  { name: "orange", hex: "#f59e0b" },
  { name: "green", hex: "#22c55e" },
  { name: "purple", hex: "#a855f7" },
  { name: "brown", hex: "#92400e" },
  { name: "teal", hex: "#14b8a6" },
];

// Player → explicit color chosen at creation (kept per open game). Consulted
// first so a custom name like "Alice" can still carry a chosen color.
let overrides: Record<string, string> = {};

export function setColorOverrides(map: Record<string, string>): void {
  overrides = map || {};
}

export function playerColor(pid: string, order: string[]): string {
  if (overrides[pid]) return overrides[pid];
  if (NAMED[pid.toLowerCase()]) return NAMED[pid.toLowerCase()];
  const i = Math.max(0, order.indexOf(pid));
  return PALETTE[i % PALETTE.length];
}

export function saveGameColors(gameId: string, map: Record<string, string>): void {
  try {
    localStorage.setItem(`catan-colors:${gameId}`, JSON.stringify(map));
  } catch {
    /* ignore storage failures */
  }
}

export function loadGameColors(gameId: string): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(`catan-colors:${gameId}`) || "{}");
  } catch {
    return {};
  }
}

export const TERRAIN_FILL: Record<string, string> = {
  hills: "#b45f3c",
  forest: "#2f6b3a",
  pasture: "#7bbf5a",
  fields: "#e3c04a",
  mountains: "#8a8f98",
  desert: "#d8c79a",
};

// Ports are colored by the resource they trade (generic = sea blue) so a glance
// tells you the dock type without reading the label.
export const PORT_FILL: Record<string, string> = {
  generic: "#2f80c7",
  brick: "#b45f3c",
  lumber: "#2f6b3a",
  wool: "#7bbf5a",
  grain: "#e3c04a",
  ore: "#8a8f98",
};

export const PORT_LABEL: Record<string, string> = {
  generic: "3:1",
  brick: "2:1",
  lumber: "2:1",
  wool: "2:1",
  grain: "2:1",
  ore: "2:1",
};

export function portText(type: string): string {
  return type === "generic" ? "3:1" : `${type[0].toUpperCase()} 2:1`;
}
