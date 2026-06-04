# Phase 6 — React Frontend

> **Goal:** Build the browser UI that shows the board and accepts player input.
>
> **Branch:** `git checkout -b phase-6-frontend`

---

## 6.1 React Fundamentals Review

React builds UIs from **components** — functions that take **props** and return JSX.

**State** lives in components and changes over time. When state changes, React re-renders.

```tsx
// A simple counter
import { useState } from 'react'

function Counter() {
  const [count, setCount] = useState(0)
  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>+</button>
    </div>
  )
}
```

Mental model: `state → render → user action → new state → re-render`

---

## 6.2 TypeScript Types

**`web/src/types.ts`**

```typescript
export type GameMode = "strict" | "dev"

export interface ResourceCounts {
  brick: number
  lumber: number
  wool: number
  grain: number
  ore: number
}

export interface PlayerStateDTO {
  pid:            string
  resources:      ResourceCounts
  victory_points: number    // public VP only
  true_vp:        number    // includes hidden VP cards
  knights_played: number
  settlements:    number[]  // vertex ids
  cities:         number[]  // vertex ids
  roads:          number[]  // edge indices
}

export interface GameStateDTO {
  game_id:              string
  mode:                 GameMode
  phase:                "setup" | "play" | "finished"
  current_player:       string
  turn_number:          number
  player_order:         string[]
  players:              Record<string, PlayerStateDTO>
  dice:                 [number, number] | null
  has_rolled:           boolean
  winner:               string | null
  pending_discards:     Record<string, number>  // pid → card count to discard
  robber_pending:       boolean
  dev_played_this_turn: boolean
  dev_bought_this_turn: Record<string, number>  // card name → count
  seq:                  number
}

export interface HexDTO {
  coord:   { q: number; r: number }
  x:       number
  y:       number
  terrain: string
  number:  number | null
  pips:    number
  robber:  boolean
  corners: [number, number][]   // 6 pixel corners
}

export interface VertexDTO {
  id:       number
  x:        number
  y:        number
  building: { pid: string; type: "settlement" | "city" } | null
}

export interface EdgeDTO {
  index: number
  x1: number; y1: number
  x2: number; y2: number
  road: { pid: string } | null
}

export interface PortDTO {
  type:     string
  x:        number
  y:        number
  vertices: number[]
}

export interface LayoutDTO {
  hexes:    HexDTO[]
  vertices: VertexDTO[]
  edges:    EdgeDTO[]
  ports:    PortDTO[]
}
```

---

## 6.3 API Client

**`web/src/api.ts`**

```typescript
export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail))
  }
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, body.detail ?? body)
  }
  return res.json()
}

export const api = {
  createGame: (players: string[], board: string, mode: GameMode, layout?: object) =>
    json<{ game_id: string }>(fetch("/api/games", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ players, board, mode, layout }),
    })),

  getState:  (id: string, at?: number) =>
    json<GameStateDTO>(fetch(`/api/games/${id}/state${at != null ? `?at=${at}` : ""}`)),

  getLayout: (id: string) =>
    json<LayoutDTO>(fetch(`/api/games/${id}/layout`)),

  getEvents: (id: string) =>
    json<EventDTO[]>(fetch(`/api/games/${id}/events`)),

  getMetrics: (id: string) =>
    json<GameMetricsDTO>(fetch(`/api/games/${id}/metrics`)),

  sendCommand: (id: string, command: object) =>
    json<GameStateDTO>(fetch(`/api/games/${id}/commands`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(command),
    })),

  sendCommandText: (id: string, text: string) =>
    json<GameStateDTO>(fetch(`/api/games/${id}/command_text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    })),

  setMode: (id: string, mode: GameMode) =>
    json<{ mode: string }>(fetch(`/api/games/${id}/mode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    })),

  listGames: () =>
    json<GameSummaryDTO[]>(fetch("/api/games")),

  deleteGame: (id: string) =>
    fetch(`/api/games/${id}`, { method: "DELETE" }),
}
```

---

## 6.4 WebSocket Hook

**`web/src/useGameSocket.ts`**

```typescript
import { useEffect, useRef } from 'react'
import type { GameStateDTO } from './types'

export function useGameSocket(
  gameId: string,
  enabled: boolean,
  onState: (state: GameStateDTO) => void
) {
  // Use refs so the socket doesn't reconnect when callbacks change.
  const onStateRef = useRef(onState)
  const enabledRef = useRef(enabled)
  onStateRef.current  = onState
  enabledRef.current  = enabled

  useEffect(() => {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:"
    const ws = new WebSocket(`${protocol}//${location.host}/api/games/${gameId}/ws`)

    ws.onmessage = (event) => {
      if (!enabledRef.current) return   // ignore pushes during history scrub
      const msg = JSON.parse(event.data)
      if (msg.type === "state") {
        onStateRef.current(msg.state)
      }
    }

    ws.onerror = (e) => console.error("WebSocket error", e)

    return () => ws.close()
  }, [gameId])   // only reconnect when gameId changes
}
```

> **The `enabled` ref pattern:** When the user scrubs through history (see 6.8), the WebSocket stays connected but live state pushes are ignored. Using a ref avoids disconnecting and reconnecting the socket on every render.

---

## 6.5 SVG Board Renderer

**`web/src/components/Board.tsx`**

```tsx
import type { LayoutDTO, HexDTO, VertexDTO, EdgeDTO } from '../types'
import { terrainColor, playerColor } from '../colors'

interface BoardProps {
  layout:         LayoutDTO
  activeTool:     string | null
  onVertexClick?: (vertexId: number) => void
  onEdgeClick?:   (edgeIndex: number) => void
  onHexClick?:    (coord: { q: number; r: number }) => void
}

const S = 60  // size constant (pixels per board unit)

export function Board({ layout, activeTool, onVertexClick, onEdgeClick, onHexClick }: BoardProps) {
  // Compute a tight viewBox from vertex positions.
  const xs = layout.vertices.map(v => v.x)
  const ys = layout.vertices.map(v => v.y)
  const PAD = 40
  const minX = Math.min(...xs) - PAD
  const minY = Math.min(...ys) - PAD
  const width  = Math.max(...xs) - minX + PAD
  const height = Math.max(...ys) - minY + PAD

  return (
    <svg viewBox={`${minX} ${minY} ${width} ${height}`} width={600}>
      {/* Hex tiles */}
      {layout.hexes.map(hex => (
        <HexTile key={`${hex.coord.q},${hex.coord.r}`} hex={hex}
                 onClick={() => onHexClick?.(hex.coord)}
                 isRobberTool={activeTool === "robber"} />
      ))}

      {/* Edges (roads) */}
      {layout.edges.map(edge => (
        <line key={edge.index}
              x1={edge.x1} y1={edge.y1} x2={edge.x2} y2={edge.y2}
              stroke={edge.road ? playerColor(edge.road.pid) : "#ccc"}
              strokeWidth={edge.road ? 6 : 3}
              style={{ cursor: activeTool === "road" ? "pointer" : "default" }}
              onClick={() => activeTool === "road" && onEdgeClick?.(edge.index)} />
      ))}

      {/* Vertices (settlements/cities) */}
      {layout.vertices.map(v => (
        <VertexMarker key={v.id} vertex={v}
                      clickable={activeTool === "settlement" || activeTool === "city"}
                      onClick={() => onVertexClick?.(v.id)} />
      ))}
    </svg>
  )
}

function HexTile({ hex, onClick, isRobberTool }: {
  hex: HexDTO
  onClick: () => void
  isRobberTool: boolean
}) {
  const points = hex.corners.map(([x, y]) => `${x},${y}`).join(" ")
  return (
    <g onClick={isRobberTool ? onClick : undefined}
       style={{ cursor: isRobberTool ? "pointer" : "default" }}>
      <polygon points={points} fill={terrainColor(hex.terrain)} stroke="#555" strokeWidth={1} />
      {hex.number && (
        <circle cx={hex.x} cy={hex.y} r={18} fill="white" stroke="#888" strokeWidth={1} />
      )}
      {hex.number && (
        <text x={hex.x} y={hex.y} textAnchor="middle" dominantBaseline="middle"
              fontSize={16} fill={hex.number === 6 || hex.number === 8 ? "red" : "#333"}
              fontWeight={hex.number === 6 || hex.number === 8 ? "bold" : "normal"}>
          {hex.number}
        </text>
      )}
      {hex.robber && (
        <text x={hex.x} y={hex.y + 22} textAnchor="middle" fontSize={18}>🦹</text>
      )}
    </g>
  )
}
```

---

## 6.6 Component Overview

The app has 9 components beyond `Board.tsx`. Build them in this order:

| Component | What it does |
|-----------|-------------|
| `Players.tsx` | Scoreboard: VP, resources, roads/settlements/cities per player |
| `ActionsPanel.tsx` | Roll dice button, End Turn, trade buttons, dev card menu |
| `Palette.tsx` | Tool selector: settlement / road / city / robber |
| `DiscardPanel.tsx` | Modal shown when `pending_discards` is non-empty |
| `RobberPanel.tsx` | Victim/resource picker after placing robber |
| `EventLog.tsx` | Scrolling list of recent events (from `/events` endpoint) |
| `CommandBar.tsx` | Text input for REPL-style commands (`command_text` endpoint) |
| `AdminPanel.tsx` | Dev-mode only: set resources, set VP for any player |
| `BoardDesigner.tsx` | Custom board builder (extra credit — see 6.9) |

---

## 6.7 App State

**`web/src/App.tsx`** (simplified structure)

```tsx
import { useState, useEffect } from 'react'
import { api } from './api'
import { useGameSocket } from './useGameSocket'
import { Board } from './components/Board'
import type { GameStateDTO, LayoutDTO } from './types'

function GameView({ gameId }: { gameId: string }) {
  const [state,   setState]   = useState<GameStateDTO | null>(null)
  const [layout,  setLayout]  = useState<LayoutDTO | null>(null)
  const [tool,    setTool]    = useState<string | null>(null)
  const [viewSeq, setViewSeq] = useState<number | null>(null)  // null = live
  const [error,   setError]   = useState<string | null>(null)

  // Load on mount.
  useEffect(() => {
    Promise.all([api.getState(gameId), api.getLayout(gameId)])
      .then(([s, l]) => { setState(s); setLayout(l) })
      .catch(e => setError(e.message))
  }, [gameId])

  // Live WebSocket updates (disabled while scrubbing history).
  useGameSocket(gameId, viewSeq === null, setState)

  const applyCommand = async (command: object) => {
    try {
      setError(null)
      const newState = await api.sendCommand(gameId, command)
      setState(newState)
    } catch (e: any) {
      setError(e.message)
    }
  }

  const handleVertexClick = (vertexId: number) => {
    if (!state) return
    const pid = state.current_player
    if (tool === "settlement") {
      applyCommand({ type: "BuildSettlement", pid, vertex_id: vertexId })
    } else if (tool === "city") {
      applyCommand({ type: "BuildCity", pid, vertex_id: vertexId })
    } else if (tool === "setup_settlement") {
      applyCommand({ type: "PlaceSetupSettlement", pid, vertex_id: vertexId })
    }
  }

  const handleEdgeClick = (edgeIndex: number) => {
    if (!state) return
    const pid = state.current_player
    if (tool === "road" || tool === "setup_road") {
      applyCommand({ type: tool === "setup_road" ? "PlaceSetupRoad" : "BuildRoad",
                     pid, edge_index: edgeIndex })
    }
  }

  // History scrubber: load state at a specific sequence number.
  const scrubTo = async (seq: number) => {
    const s = await api.getState(gameId, seq)
    setState(s)
    setViewSeq(seq)
  }

  if (!state || !layout) return <div>Loading…</div>

  return (
    <div className="game-view">
      {error && <div className="error-banner" onClick={() => setError(null)}>{error}</div>}
      <Board layout={layout} activeTool={tool}
             onVertexClick={handleVertexClick}
             onEdgeClick={handleEdgeClick}
             onHexClick={(coord) => {
               if (tool === "robber") {
                 // Show RobberPanel to pick victim/resource.
               }
             }} />
      <div className="sidebar">
        <Players state={state} />
        <ActionsPanel state={state} onApply={applyCommand}
                      tool={tool} setTool={setTool} />
        {state.pending_discards && Object.keys(state.pending_discards).length > 0 && (
          <DiscardPanel state={state} onApply={applyCommand} />
        )}
        <EventLog gameId={gameId} />
        {state.mode === "dev" && <AdminPanel state={state} onApply={applyCommand} />}
      </div>
      {/* History scrubber */}
      {state.seq > 0 && (
        <div className="scrubber">
          <input type="range" min={0} max={state.seq} value={viewSeq ?? state.seq}
                 onChange={e => scrubTo(Number(e.target.value))} />
          {viewSeq !== null && (
            <button onClick={() => { setViewSeq(null); api.getState(gameId).then(setState) }}>
              Back to Live
            </button>
          )}
        </div>
      )}
    </div>
  )
}
```

---

## 6.8 History Scrubber

The `GET /api/games/{id}/state?at=SEQ` endpoint lets you load any historical state. The UI exposes this as a range slider:

- Slider at max → live mode (`viewSeq = null`, WebSocket updates applied)
- Slider moved left → scrub mode (`viewSeq = N`, WebSocket updates ignored)
- "Back to Live" button resets to current state

---

## 6.9 Extra Credit: Custom Board Designer

The `BoardDesigner` component lets users enter their physical board layout before starting a game:

1. Fetch `GET /api/board_template` to get an empty board with positions
2. Render each hex with a dropdown for terrain and a dropdown for number token
3. Assign ports by clicking perimeter edges
4. On confirm, POST to `POST /api/games` with the full `layout` object

---

## 6.10 Terrain Colors

**`web/src/colors.ts`**

```typescript
const TERRAIN_COLORS: Record<string, string> = {
  forest:    "#3a7d44",
  hills:     "#c1440e",
  pasture:   "#8ab855",
  fields:    "#e8c84a",
  mountains: "#888888",
  desert:    "#d4b483",
}

export function terrainColor(terrain: string): string {
  return TERRAIN_COLORS[terrain] ?? "#cccccc"
}

const PLAYER_COLORS = ["#e63946", "#457b9d", "#2a9d8f", "#e9c46a"]

export function playerColor(pid: string, order: string[] = []): string {
  const idx = order.indexOf(pid)
  return PLAYER_COLORS[idx >= 0 ? idx : 0]
}
```

---

## Phase 6 Checkpoint

- [ ] Board renders 19 hexes with correct terrain colors
- [ ] Number tokens show (6 and 8 in red)
- [ ] Clicking a vertex in settlement mode sends the correct API command
- [ ] Error banner appears on invalid moves
- [ ] Two browser tabs: action in one updates both within 1 second
- [ ] History scrubber lets you step back through events
- [ ] `DiscardPanel` appears when players must discard after a 7
- [ ] Dev mode shows `AdminPanel` (not visible in strict mode)
- [ ] Commit: `"Phase 6: React frontend with SVG board and WebSocket updates"`
