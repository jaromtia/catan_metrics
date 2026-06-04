// Picture icons for resources and the terrain that produces them.
export const RESOURCE_ICON: Record<string, string> = {
  brick: "🧱",
  lumber: "🪵",
  wool: "🐑",
  grain: "🌾",
  ore: "🪨",
};

export const TERRAIN_ICON: Record<string, string> = {
  hills: "🧱",
  forest: "🪵",
  pasture: "🐑",
  fields: "🌾",
  mountains: "🪨",
  desert: "🏜️",
};

export const RESOURCE_NAME: Record<string, string> = {
  brick: "brick",
  lumber: "lumber",
  wool: "wool",
  grain: "grain",
  ore: "ore",
};

/** Inline resource icon with the resource name as a tooltip. */
export function ResIcon({ r, showName }: { r: string; showName?: boolean }) {
  return (
    <span className="res-ico" title={RESOURCE_NAME[r] ?? r}>
      {RESOURCE_ICON[r] ?? r}
      {showName ? <span className="res-ico-name"> {r}</span> : null}
    </span>
  );
}
