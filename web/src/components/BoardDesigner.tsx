import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api";
import { PORT_FILL, saveGameColors, setColorOverrides, TERRAIN_FILL } from "../colors";
import type { BoardTemplateDTO } from "../types";

const S = 60; // pixels per board unit (matches the in-game Board)
const PAD = 44;

const TERRAINS = ["forest", "fields", "pasture", "hills", "mountains", "desert"] as const;
const TERRAIN_LABEL: Record<string, string> = {
  forest: "Forest",
  fields: "Fields",
  pasture: "Pasture",
  hills: "Hills",
  mountains: "Mountains",
  desert: "Desert",
};
const NUMBERS = [2, 3, 4, 5, 6, 8, 9, 10, 11, 12];

const PORTS = ["generic", "brick", "lumber", "wool", "grain", "ore"] as const;
const PORT_TOOL_LABEL: Record<string, string> = {
  generic: "Generic 3:1",
  brick: "Brick 2:1",
  lumber: "Lumber 2:1",
  wool: "Wool 2:1",
  grain: "Grain 2:1",
  ore: "Ore 2:1",
};

type Tool =
  | { kind: "terrain"; value: string }
  | { kind: "number"; value: number }
  | { kind: "port"; value: string };

function sameTool(a: Tool | null, b: Tool | null): boolean {
  return !!a && !!b && a.kind === b.kind && a.value === b.value;
}

interface Props {
  players: string[];
  colors: Record<string, string>;
  mode: string;
  onCancel: () => void;
  onCreated: (gameId: string) => void;
}

export function BoardDesigner({ players, colors, mode, onCancel, onCreated }: Props) {
  const [tpl, setTpl] = useState<BoardTemplateDTO | null>(null);
  const [terrains, setTerrains] = useState<(string | null)[]>([]);
  const [numbers, setNumbers] = useState<(number | null)[]>([]);
  const [portByEdge, setPortByEdge] = useState<Record<number, string>>({});
  const [tool, setTool] = useState<Tool | null>(null);
  const [drag, setDrag] = useState<Tool | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.getBoardTemplate().then((t) => {
      setTpl(t);
      setTerrains(Array(t.hexes.length).fill(null));
      setNumbers(Array(t.hexes.length).fill(null));
      setPortByEdge(Object.fromEntries(t.default_ports.map((p) => [p.edge, p.type])));
    }).catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTool(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const terrainUsed = useMemo(() => {
    const m: Record<string, number> = {};
    for (const t of terrains) if (t) m[t] = (m[t] ?? 0) + 1;
    return m;
  }, [terrains]);

  const numberUsed = useMemo(() => {
    const m: Record<number, number> = {};
    for (const n of numbers) if (n != null) m[n] = (m[n] ?? 0) + 1;
    return m;
  }, [numbers]);

  const portUsed = useMemo(() => {
    const m: Record<string, number> = {};
    for (const t of Object.values(portByEdge)) m[t] = (m[t] ?? 0) + 1;
    return m;
  }, [portByEdge]);

  const { ox, oy, w, h } = useMemo(() => {
    if (!tpl) return { ox: 0, oy: 0, w: 0, h: 0 };
    const pts = [
      ...Object.values(tpl.vertices),
      ...tpl.perimeter_edges.map((s) => s.pos),
    ];
    const xs = pts.map((p) => p[0] * S);
    const ys = pts.map((p) => p[1] * S);
    const minX = Math.min(...xs), minY = Math.min(...ys);
    return {
      ox: minX - PAD, oy: minY - PAD,
      w: Math.max(...xs) - minX + PAD * 2,
      h: Math.max(...ys) - minY + PAD * 2,
    };
  }, [tpl]);

  if (error) return <div className="loading">Failed to load board: {error}</div>;
  if (!tpl) return <div className="loading">Loading…</div>;

  const terrainLeft = (t: string) => (tpl.terrain_counts[t] ?? 0) - (terrainUsed[t] ?? 0);
  const numberLeft = (n: number) => (tpl.number_counts[String(n)] ?? 0) - (numberUsed[n] ?? 0);
  const portLeft = (t: string) => (tpl.port_counts[t] ?? 0) - (portUsed[t] ?? 0);

  const applyPort = (edge: number, active: Tool | null) => {
    if (!active || active.kind !== "port") return;
    setPortByEdge((prev) => {
      const next = { ...prev };
      if (next[edge] === active.value) {
        delete next[edge]; // toggle off
      } else {
        if (portLeft(active.value) <= 0) return prev; // distribution limit reached
        next[edge] = active.value;
      }
      return next;
    });
  };

  const apply = (idx: number, active: Tool | null) => {
    if (!active || active.kind === "port") return;
    if (active.kind === "terrain") {
      setTerrains((prev) => {
        const next = [...prev];
        if (next[idx] === active.value) {
          next[idx] = null; // toggle off
        } else {
          if (terrainLeft(active.value) <= 0) return prev; // count limit reached
          next[idx] = active.value;
        }
        return next;
      });
      // A hex with no terrain (or a desert) cannot carry a number token.
      setNumbers((prev) => {
        if (active.value === "desert" || terrains[idx] === active.value) {
          if (prev[idx] == null) return prev;
          const next = [...prev];
          next[idx] = null;
          return next;
        }
        return prev;
      });
    } else {
      if (!terrains[idx] || terrains[idx] === "desert") return; // only producing hexes
      setNumbers((prev) => {
        const next = [...prev];
        if (next[idx] === active.value) {
          next[idx] = null;
        } else {
          if (numberLeft(active.value) <= 0) return prev;
          next[idx] = active.value;
        }
        return next;
      });
    }
  };

  const reset = () => {
    setTerrains(Array(tpl.hexes.length).fill(null));
    setNumbers(Array(tpl.hexes.length).fill(null));
  };

  const resetPorts = () =>
    setPortByEdge(Object.fromEntries(tpl.default_ports.map((p) => [p.edge, p.type])));

  const placedTerrains = terrains.filter(Boolean).length;
  const missingNumbers = terrains.reduce(
    (a, t, i) => a + (t && t !== "desert" && numbers[i] == null ? 1 : 0),
    0,
  );
  const portsPlaced = Object.keys(portByEdge).length;
  const totalPorts = Object.values(tpl.port_counts).reduce((a, b) => a + b, 0);
  const portsComplete = portsPlaced === totalPorts;
  const complete =
    placedTerrains === tpl.hexes.length && missingNumbers === 0 && portsComplete;

  const create = async () => {
    if (!complete) return;
    const layout = {
      terrain: terrains as string[],
      numbers: terrains
        .map((t, i) => (t !== "desert" ? numbers[i] : null))
        .filter((n): n is number => n != null),
      ports: Object.entries(portByEdge).map(([edge, type]) => ({
        type,
        edge: Number(edge),
      })),
    };
    setBusy(true);
    setError(null);
    try {
      const res = await api.createGame(players, "custom", null, layout, mode);
      saveGameColors(res.game_id, colors);
      setColorOverrides(colors);
      onCreated(res.game_id);
    } catch (e) {
      const detail = e instanceof ApiError ? e.detail : String(e);
      setError(typeof detail === "string" ? detail : JSON.stringify(detail));
      setBusy(false);
    }
  };

  const vpos = (id: number) => {
    const p = tpl.vertices[String(id)];
    return [p[0] * S, p[1] * S] as const;
  };

  return (
    <div className="designer">
      <header>
        <button className="link" onClick={onCancel}>← cancel</button>
        <h1>Design board</h1>
        <span className="muted">{players.join(", ")}</span>
        <button className="create-btn" disabled={!complete || busy} onClick={create}>
          {busy ? "Creating…" : complete ? "Create game →" : "Finish the board"}
        </button>
      </header>

      <div className="designer-body">
        <svg
          className="board"
          viewBox={`${ox} ${oy} ${w} ${h}`}
          onDragOver={(e) => e.preventDefault()}
        >
          {tpl.hexes.map((hx, i) => {
            const pts = hx.vertices.map((v) => vpos(v).join(",")).join(" ");
            const t = terrains[i];
            const [cx, cy] = [hx.center[0] * S, hx.center[1] * S];
            const num = numbers[i];
            const red = num === 6 || num === 8;
            return (
              <g
                key={i}
                className="design-hex"
                onClick={() => apply(i, tool)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  apply(i, drag);
                }}
              >
                <polygon
                  points={pts}
                  fill={t ? TERRAIN_FILL[t] : "#1b2330"}
                  stroke="#1b2330"
                  strokeWidth={2}
                />
                {!t && (
                  <text x={cx} y={cy + 5} textAnchor="middle" className="hex-empty">+</text>
                )}
                {num != null && (
                  <>
                    <circle cx={cx} cy={cy} r={14} fill="#f5efe0" stroke="#1b2330" />
                    <text x={cx} y={cy + 4} textAnchor="middle" className={red ? "num red" : "num"}>
                      {num}
                    </text>
                  </>
                )}
              </g>
            );
          })}

          {/* perimeter port slots: filled badges + faint empty docks */}
          {tpl.perimeter_edges.map((slot) => {
            const t = portByEdge[slot.edge];
            const [px, py] = [slot.pos[0] * S, slot.pos[1] * S];
            const generic = t === "generic";
            return (
              <g
                key={slot.edge}
                className="port-slot"
                onClick={() => applyPort(slot.edge, tool)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  applyPort(slot.edge, drag);
                }}
              >
                {t ? (
                  <>
                    {slot.vertices.map((v) => {
                      const [vx, vy] = vpos(v);
                      return <line key={v} className="port-dock" x1={px} y1={py} x2={vx} y2={vy} />;
                    })}
                    <circle cx={px} cy={py} r={15} fill={PORT_FILL[t]} stroke="#0b1018" strokeWidth={2} />
                    <text x={px} y={py - 2.5} textAnchor="middle" className="port-res">
                      {generic ? "3:1" : t[0].toUpperCase()}
                    </text>
                    <text x={px} y={py + 8} textAnchor="middle" className="port-ratio">
                      {generic ? "any" : "2:1"}
                    </text>
                  </>
                ) : (
                  <circle cx={px} cy={py} r={6} className="port-empty" />
                )}
              </g>
            );
          })}
        </svg>

        <div className="designer-tools">
          <div className="panel">
            <h3>Tiles</h3>
            <div className="tool-grid">
              {TERRAINS.map((t) => {
                const left = terrainLeft(t);
                const active = sameTool(tool, { kind: "terrain", value: t });
                return (
                  <button
                    key={t}
                    className={`tool-chip ${active ? "active" : ""} ${left === 0 ? "done" : ""}`}
                    draggable
                    onDragStart={() => setDrag({ kind: "terrain", value: t })}
                    onDragEnd={() => setDrag(null)}
                    onClick={() => setTool(active ? null : { kind: "terrain", value: t })}
                  >
                    <span className="swatch" style={{ background: TERRAIN_FILL[t] }} />
                    {TERRAIN_LABEL[t]}
                    <span className="left">{left}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="panel">
            <h3>Number tokens</h3>
            <div className="tool-grid nums">
              {NUMBERS.map((n) => {
                const left = numberLeft(n);
                const active = sameTool(tool, { kind: "number", value: n });
                const red = n === 6 || n === 8;
                return (
                  <button
                    key={n}
                    className={`tool-chip num-chip ${active ? "active" : ""} ${left === 0 ? "done" : ""}`}
                    draggable
                    onDragStart={() => setDrag({ kind: "number", value: n })}
                    onDragEnd={() => setDrag(null)}
                    onClick={() => setTool(active ? null : { kind: "number", value: n })}
                  >
                    <span className={red ? "num red" : "num"}>{n}</span>
                    <span className="left">{left}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="panel">
            <h3>Sea ports</h3>
            <div className="tool-grid">
              {PORTS.map((pt) => {
                const left = portLeft(pt);
                const active = sameTool(tool, { kind: "port", value: pt });
                return (
                  <button
                    key={pt}
                    className={`tool-chip ${active ? "active" : ""} ${left === 0 ? "done" : ""}`}
                    draggable
                    onDragStart={() => setDrag({ kind: "port", value: pt })}
                    onDragEnd={() => setDrag(null)}
                    onClick={() => setTool(active ? null : { kind: "port", value: pt })}
                  >
                    <span className="swatch round" style={{ background: PORT_FILL[pt] }} />
                    {PORT_TOOL_LABEL[pt]}
                    <span className="left">{left}</span>
                  </button>
                );
              })}
            </div>
            <button className="link" onClick={resetPorts}>Reset ports to standard</button>
          </div>

          <div className="panel">
            <p className="muted small">
              Drag a tile, number, or port onto the board — or click one to select,
              then click a target. Click the same target again to clear it. Numbers go
              on producing hexes only; ports drop onto the perimeter docks.
            </p>
            <p className="small">
              Tiles {placedTerrains}/{tpl.hexes.length} · numbers left {missingNumbers} ·
              ports {portsPlaced}/{totalPorts}
            </p>
            <button className="link" onClick={reset}>Reset tiles &amp; numbers</button>
            {error && <div className="msg err">{error}</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
