import { useMemo, useRef, useState } from "react";
import { playerColor, PORT_FILL, TERRAIN_FILL } from "../colors";
import { TERRAIN_ICON } from "../icons";
import type { GameStateDTO, LayoutDTO } from "../types";
import type { Piece } from "./Palette";

const S = 60; // pixels per board unit

/** Bounds that include terrain icons, number tokens, and port labels — not just vertices. */
function boardBounds(layout: LayoutDTO) {
  const pts: [number, number][] = [];

  for (const hx of layout.hexes) {
    const cx = hx.center[0] * S;
    const cy = hx.center[1] * S;
    for (const v of hx.vertices) {
      const p = layout.vertices[String(v)];
      pts.push([p[0] * S, p[1] * S]);
    }
    // resource icon sits above the number token
    pts.push([cx, cy - 38], [cx, cy + 20]);
  }

  for (const p of layout.ports) {
    const px = p.pos[0] * S;
    const py = p.pos[1] * S;
    pts.push([px - 20, py - 20], [px + 20, py + 24]);
  }

  const xs = pts.map((p) => p[0]);
  const ys = pts.map((p) => p[1]);
  const pad = 8;
  const minX = Math.min(...xs) - pad;
  const minY = Math.min(...ys) - pad;
  const maxX = Math.max(...xs) + pad;
  const maxY = Math.max(...ys) + pad;
  return { ox: minX, oy: minY, w: maxX - minX, h: maxY - minY };
}

interface Props {
  layout: LayoutDTO;
  state: GameStateDTO;
  showVertexIds: boolean;
  showEdgeIds: boolean;
  showResIcons: boolean;
  actor: string;            // player placements are attributed to
  tool: Piece | null;       // click-to-place selection
  dragKind: Piece | null;   // active drag
  disabled: boolean;
  onPlace: (kind: Piece, id: number) => void;
  onRobberHex: (coord: number[]) => void;
}

export function Board({ layout, state, showVertexIds, showEdgeIds, showResIcons, actor, tool, dragKind, disabled, onPlace, onRobberHex }: Props) {
  const order = state.player_order;
  const frameRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [hover, setHover] = useState<{ kind: Piece; x: number; y: number } | null>(null);

  const bounds = useMemo(() => boardBounds(layout), [layout]);
  const { ox, oy, w, h } = bounds;

  const activeKind: Piece | null = disabled ? null : dragKind ?? tool;

  const vpos = (id: number | string) => {
    const p = layout.vertices[String(id)];
    return [p[0] * S, p[1] * S] as const;
  };
  const edgeMid = (id: number) => {
    const [a, b] = layout.edges[String(id)];
    const [x1, y1] = vpos(a);
    const [x2, y2] = vpos(b);
    return [(x1 + x2) / 2, (y1 + y2) / 2] as const;
  };

  // owner lookups
  const roadOwner: Record<string, string> = {};
  const settlementOwner: Record<number, string> = {};
  const cityOwner: Record<number, string> = {};
  for (const pid of order) {
    for (const e of state.players[pid].roads) roadOwner[e] = pid;
    for (const v of state.players[pid].settlements) settlementOwner[v] = pid;
    for (const v of state.players[pid].cities) cityOwner[v] = pid;
  }

  const actorColor = playerColor(actor, order);
  const showVertexLabels = showVertexIds && !dragKind;
  const showEdgeLabels = showEdgeIds && !dragKind;
  const robberKey = state.robber ? state.robber.join(",") : null;

  // --- hit testing -------------------------------------------------------
  const toSvg = (clientX: number, clientY: number) => {
    const svg = svgRef.current;
    if (!svg) return null;
    const pt = svg.createSVGPoint();
    pt.x = clientX;
    pt.y = clientY;
    const m = svg.getScreenCTM();
    if (!m) return null;
    const p = pt.matrixTransform(m.inverse());
    return { x: p.x, y: p.y };
  };
  const nearestVertex = (p: { x: number; y: number }) => {
    let best: number | null = null, bd = Infinity;
    for (const vid of Object.keys(layout.vertices)) {
      const [vx, vy] = vpos(Number(vid));
      const d = Math.hypot(vx - p.x, vy - p.y);
      if (d < bd) { bd = d; best = Number(vid); }
    }
    return bd <= 0.55 * S ? best : null;
  };
  const nearestEdge = (p: { x: number; y: number }) => {
    let best: number | null = null, bd = Infinity;
    for (const eid of Object.keys(layout.edges)) {
      const [mx, my] = edgeMid(Number(eid));
      const d = Math.hypot(mx - p.x, my - p.y);
      if (d < bd) { bd = d; best = Number(eid); }
    }
    return bd <= 0.5 * S ? best : null;
  };
  const nearestHex = (clientX: number, clientY: number) => {
    const p = toSvg(clientX, clientY);
    if (!p) return null;
    let best: (typeof layout.hexes)[number] | null = null, bd = Infinity;
    for (const hx of layout.hexes) {
      const d = Math.hypot(hx.center[0] * S - p.x, hx.center[1] * S - p.y);
      if (d < bd) { bd = d; best = hx; }
    }
    return best && bd <= 0.95 * S ? best : null;
  };
  const hit = (clientX: number, clientY: number, kind: Piece) => {
    const p = toSvg(clientX, clientY);
    if (!p) return null;
    return kind === "road" ? nearestEdge(p) : nearestVertex(p);
  };

  const updateHover = (clientX: number, clientY: number, kind: Piece | null) => {
    if (!kind) { setHover(null); return; }
    if (kind === "robber") {
      const hx = nearestHex(clientX, clientY);
      if (!hx) { setHover(null); return; }
      setHover({ kind, x: hx.center[0] * S, y: hx.center[1] * S });
      return;
    }
    const id = hit(clientX, clientY, kind);
    if (id == null) { setHover(null); return; }
    const [x, y] = kind === "road" ? edgeMid(id) : vpos(id);
    setHover({ kind, x, y });
  };

  const place = (clientX: number, clientY: number, kind: Piece) => {
    if (kind === "robber") {
      const hx = nearestHex(clientX, clientY);
      if (hx) onRobberHex(hx.coord);
      return;
    }
    const id = hit(clientX, clientY, kind);
    if (id != null) onPlace(kind, id);
  };

  const pointerPlace = (clientX: number, clientY: number) => {
    const kind = dragKind ?? tool;
    if (!kind) return;
    place(clientX, clientY, kind);
  };

  const handlers = disabled
    ? {}
    : {
        onMouseMove: (e: React.MouseEvent) => updateHover(e.clientX, e.clientY, tool),
        onMouseLeave: () => setHover(null),
        onClick: (e: React.MouseEvent) => {
          if (tool) place(e.clientX, e.clientY, tool);
        },
        onTouchStart: (e: React.TouchEvent) => {
          const t = e.touches[0];
          if (t) updateHover(t.clientX, t.clientY, tool);
        },
        onTouchMove: (e: React.TouchEvent) => {
          const t = e.touches[0];
          if (t) updateHover(t.clientX, t.clientY, tool);
        },
        onTouchEnd: (e: React.TouchEvent) => {
          const t = e.changedTouches[0];
          if (t) pointerPlace(t.clientX, t.clientY);
          setHover(null);
        },
        onDragOver: (e: React.DragEvent) => {
          if (!dragKind) return;
          e.preventDefault();
          updateHover(e.clientX, e.clientY, dragKind);
        },
        onDrop: (e: React.DragEvent) => {
          if (!dragKind) return;
          e.preventDefault();
          setHover(null);
          place(e.clientX, e.clientY, dragKind);
        },
      };

  return (
    <div
      ref={frameRef}
      className={`board-frame ${activeKind ? "placing" : ""}`}
      style={{ "--board-ar": `${w} / ${h}` } as React.CSSProperties}
    >
      <svg
        ref={svgRef}
        className={`board ${activeKind ? "placing" : ""}`}
        viewBox={`${ox} ${oy} ${w} ${h}`}
        width="100%"
        height="100%"
        preserveAspectRatio="xMidYMid meet"
        {...handlers}
      >
          {/* hex tiles */}
          {layout.hexes.map((hx) => {
            const pts = hx.vertices.map((v) => vpos(v).join(",")).join(" ");
            const isRobber = robberKey === hx.coord.join(",");
            const [cx, cy] = [hx.center[0] * S, hx.center[1] * S];
            const red = hx.number === 6 || hx.number === 8;
            return (
              <g key={hx.coord.join(",")}>
                <polygon points={pts} fill={TERRAIN_FILL[hx.terrain]} stroke="#1b2330" strokeWidth={2} />
                {showResIcons && (
                  <text x={cx} y={cy - 19} textAnchor="middle" className="hex-ico">
                    {TERRAIN_ICON[hx.terrain]}
                  </text>
                )}
                {hx.number != null && (
                  <>
                    <circle cx={cx} cy={cy} r={14} fill="#f5efe0" stroke="#1b2330" />
                    <text x={cx} y={cy + 4} textAnchor="middle" className={red ? "num red" : "num"}>
                      {hx.number}
                    </text>
                  </>
                )}
                {isRobber && <circle cx={cx} cy={cy} r={10} fill="#111" opacity={0.85} />}
              </g>
            );
          })}

          {/* edges: faint base, owned roads, and highlight when placing a road */}
          {Object.entries(layout.edges).map(([eid, [a, b]]) => {
            const [x1, y1] = vpos(a);
            const [x2, y2] = vpos(b);
            const owner = roadOwner[eid];
            return (
              <line key={eid} x1={x1} y1={y1} x2={x2} y2={y2}
                stroke={owner ? playerColor(owner, order) : "#33415533"}
                strokeWidth={owner ? 6 : 2} strokeLinecap="round" />
            );
          })}
          {activeKind === "road" &&
            Object.entries(layout.edges).map(([eid, [a, b]]) =>
              roadOwner[eid] ? null : (
                (() => {
                  const [x1, y1] = vpos(a);
                  const [x2, y2] = vpos(b);
                  return (
                    <line key={`hl${eid}`} x1={x1} y1={y1} x2={x2} y2={y2}
                      stroke="#0ea5e9" strokeWidth={5} strokeLinecap="round"
                      opacity={0.35} className="target" />
                  );
                })()
              ),
            )}

          {/* ports: offset into the sea with docks pointing to their two vertices */}
          {layout.ports.map((p, i) => {
            const [px, py] = [p.pos[0] * S, p.pos[1] * S];
            const generic = p.type === "generic";
            return (
              <g key={i} className="port-mark">
                <title>{`${p.type} port (${generic ? "3:1 any" : "2:1"})`}</title>
                {p.vertices.map((v) => {
                  const [vx, vy] = vpos(v);
                  return <line key={v} className="port-dock" x1={px} y1={py} x2={vx} y2={vy} />;
                })}
                <circle cx={px} cy={py} r={16} fill={PORT_FILL[p.type] ?? "#2f80c7"} stroke="#0b1018" strokeWidth={2} />
                <text x={px} y={py - 2.5} textAnchor="middle" className="port-res">
                  {generic ? "3:1" : p.type[0].toUpperCase()}
                </text>
                <text x={px} y={py + 8} textAnchor="middle" className="port-ratio">
                  {generic ? "any" : "2:1"}
                </text>
              </g>
            );
          })}

          {/* vertices: buildings, ids, and placement targets */}
          {Object.keys(layout.vertices).map((vid) => {
            const id = Number(vid);
            const [x, y] = vpos(id);
            const sOwner = settlementOwner[id];
            const cOwner = cityOwner[id];
            if (cOwner) {
              return <rect key={vid} x={x - 9} y={y - 9} width={18} height={18}
                fill={playerColor(cOwner, order)} stroke="#111" strokeWidth={2} rx={2} />;
            }
            if (sOwner) {
              const upgradeTarget = activeKind === "city" && sOwner === actor;
              return (
                <circle key={vid} cx={x} cy={y} r={8}
                  fill={playerColor(sOwner, order)} stroke={upgradeTarget ? "#0ea5e9" : "#111"}
                  strokeWidth={upgradeTarget ? 3 : 2} className={upgradeTarget ? "target" : ""} />
              );
            }
            const isSettleTarget = activeKind === "settlement";
            return (
              <g key={vid}>
                <circle cx={x} cy={y} r={isSettleTarget ? 7 : 3}
                  fill={isSettleTarget ? "#0ea5e9" : "#64748b"}
                  opacity={isSettleTarget ? 0.4 : 1}
                  className={isSettleTarget ? "target" : ""} />
                {showVertexLabels && <text x={x} y={y - 6} textAnchor="middle" className="vid">{vid}</text>}
              </g>
            );
          })}

          {/* edge ids */}
          {showEdgeLabels &&
            Object.entries(layout.edges).map(([eid, [a, b]]) => {
              const [x1, y1] = vpos(a);
              const [x2, y2] = vpos(b);
              return (
                <text key={`e${eid}`} x={(x1 + x2) / 2} y={(y1 + y2) / 2} textAnchor="middle" className="eid">
                  {eid}
                </text>
              );
            })}

          {/* hover preview (colored for the acting player) */}
          {hover && hover.kind === "settlement" && (
            <circle cx={hover.x} cy={hover.y} r={8} fill={actorColor} opacity={0.6} stroke="#fff" strokeDasharray="2 2" />
          )}
          {hover && hover.kind === "city" && (
            <rect x={hover.x - 9} y={hover.y - 9} width={18} height={18} rx={2} fill={actorColor} opacity={0.6} stroke="#fff" strokeDasharray="2 2" />
          )}
          {hover && hover.kind === "road" && (
            <circle cx={hover.x} cy={hover.y} r={7} fill={actorColor} opacity={0.6} stroke="#fff" strokeDasharray="2 2" />
          )}
          {hover && hover.kind === "robber" && (
            <circle cx={hover.x} cy={hover.y} r={12} fill="#111" opacity={0.55} stroke="#0ea5e9" strokeWidth={2} strokeDasharray="3 2" />
          )}
        </svg>
    </div>
  );
}
