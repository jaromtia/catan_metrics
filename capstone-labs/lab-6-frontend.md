# Lab 6 — React Frontend

> **Goal:** Build the browser UI that renders the board and accepts player input, updating live across tabs.
>
> **Branch:** `git checkout -b lab-6-frontend`

This is the second-largest lab. You will pick up React as you go if you haven't used it — read [Thinking in React](https://react.dev/learn/thinking-in-react) first.

---

## Background

React builds UIs from **components** — functions that take **props** and return JSX. **State** lives in components; when it changes, React re-renders. The mental model: `state → render → user action → new state → re-render`.

SVG (Scalable Vector Graphics) is XML markup for shapes. React can render SVG inline, which is how you will draw the hex board from the pixel geometry the API returns.

---

## Specification

All work lives under `web/src/`. The data shapes below mirror the API contract from Lab 5 — your TypeScript types must match what the server actually sends.

### `web/src/types.ts`

Declare TypeScript interfaces for the wire data. They must match the server's JSON exactly. At minimum:

- `ResourceCounts` — `{ brick, lumber, wool, grain, ore: number }`.
- `PlayerStateDTO` — `pid`, `resources`, `victory_points` (public), `true_vp` (incl. hidden), `knights_played`, `settlements: number[]`, `cities: number[]`, `roads: number[]`.
- `GameStateDTO` — `game_id`, `mode`, `phase`, `current_player`, `turn_number`, `player_order`, `players: Record<string, PlayerStateDTO>`, `dice`, `has_rolled`, `winner`, `pending_discards: Record<string, number>`, `robber_pending`, `dev_played_this_turn`, `dev_bought_this_turn`, `seq`.
- `HexDTO`, `VertexDTO`, `EdgeDTO`, `PortDTO`, and `LayoutDTO` matching the layout endpoint.

### `web/src/api.ts`

A typed API client wrapping `fetch`. Include an `ApiError` class that carries the HTTP status and the parsed `detail`, and a helper that throws it on non-2xx responses. Provide functions for: `createGame`, `getState(id, at?)`, `getLayout`, `getEvents`, `getMetrics`, `sendCommand`, `sendCommandText`, `setMode`, `listGames`, `deleteGame`.

### `web/src/useGameSocket.ts`

A React hook:

```ts
function useGameSocket(
  gameId: string,
  enabled: boolean,
  onState: (state: GameStateDTO) => void
): void
```

It opens a WebSocket to `/api/games/{id}/ws`, calls `onState` on each `{type:"state"}` message, and closes the socket on unmount. It must **not** reconnect when `onState` or `enabled` merely change value — only when `gameId` changes. (Hint: hold the latest callback and the `enabled` flag in refs so the effect's dependency array can stay `[gameId]`.) When `enabled` is false, ignore incoming pushes — this is how the history scrubber freezes the live feed.

### `web/src/components/Board.tsx`

An SVG board renderer taking `layout`, an `activeTool` string, and click callbacks `onVertexClick`, `onEdgeClick`, `onHexClick`. It must:
- Compute a tight `viewBox` from the vertex coordinates.
- Render each hex as a `<polygon>` from its `corners`, filled by terrain color, with its number token (6 and 8 in red/bold) and a robber marker when present.
- Render edges as `<line>`s (thicker/colored when a road is present), clickable when the road tool is active.
- Render vertices as markers (settlement vs. city), clickable when a build tool is active.

### Other components

Build these (you design their internals):

| Component | Responsibility |
|-----------|----------------|
| `Players.tsx` | Scoreboard: VP, resources, structure counts per player |
| `ActionsPanel.tsx` | Roll, End Turn, trade, dev-card actions |
| `Palette.tsx` | Tool selector (settlement / road / city / robber) |
| `DiscardPanel.tsx` | Modal shown when `pending_discards` is non-empty |
| `RobberPanel.tsx` | Victim/resource picker after moving the robber |
| `EventLog.tsx` | Scrolling list from the `/events` endpoint |
| `CommandBar.tsx` | Text input posting to `/command_text` |
| `AdminPanel.tsx` | Dev-mode only: set resources / VP |
| `BoardDesigner.tsx` | Custom board builder (extra credit) |

### `web/src/colors.ts`

`terrainColor(terrain)` and `playerColor(pid, order)` mapping functions. Choose a clear palette; 6/8 number tokens should read as "hot."

### `web/src/App.tsx`

The top-level `GameView`. It holds `state`, `layout`, the active `tool`, a `viewSeq` (null = live), and an `error`. It loads state + layout on mount, subscribes via `useGameSocket` (enabled only when `viewSeq === null`), and routes board clicks to the right command based on the active tool and the current phase (setup vs. play). It renders the board, the sidebar (players, actions, discard panel when needed, event log, admin panel in dev mode), and a **history scrubber**.

---

## Your Tasks

1. Write `types.ts` to match the server JSON.
2. Write `api.ts` with `ApiError` and all client functions.
3. Write `useGameSocket.ts` with the ref pattern so it reconnects only on `gameId` change.
4. Write `colors.ts`.
5. Write `Board.tsx` (hexes, edges, vertices, tokens, robber, click routing).
6. Write `Players.tsx`, `ActionsPanel.tsx`, `Palette.tsx`.
7. Write `App.tsx`: state wiring, command dispatch, live updates, error banner.
8. Add the **history scrubber**: a range slider over `0..state.seq`. Moving it left calls `getState(id, seq)` and sets `viewSeq` (freezing live updates); a "Back to Live" button clears `viewSeq` and refetches current state.
9. Write `DiscardPanel.tsx` (shown when a 7 forces discards) and `RobberPanel.tsx`.
10. Write `EventLog.tsx`, `CommandBar.tsx`, and the dev-only `AdminPanel.tsx`.

---

## Hints & Pitfalls

- Click → command: in settlement mode a vertex click posts `BuildSettlement`; in setup phase it posts `PlaceSetupSettlement`. Branch on both tool and phase.
- Keep the WebSocket alive while scrubbing — just ignore pushes (the `enabled` flag), don't tear down the socket.
- Show the error banner from `ApiError.detail`; clear it on the next successful action.
- Re-rendering the whole board on each WS message is fine for this scale; don't prematurely optimize.

---

## Tests First (manual acceptance is fine; automate what you can)

- The board renders 19 hexes with correct colors and number tokens.
- A vertex click in settlement mode posts the correct command and the building appears.
- An invalid move surfaces the server's error message in the banner.
- Two tabs open: an action in one updates both within ~1s.
- The scrubber steps backward through history and "Back to Live" returns to the present.

---

## Checkpoint

- [ ] Board renders 19 hexes with correct terrain colors; 6 and 8 in red
- [ ] Clicking a vertex in settlement mode sends the correct command
- [ ] Error banner appears on invalid moves
- [ ] Two tabs stay in sync within ~1 second
- [ ] History scrubber steps back through events
- [ ] `DiscardPanel` appears after a 7 forces discards
- [ ] `AdminPanel` shows only in dev mode
- [ ] Commit: `"Lab 6: React frontend with SVG board and WebSocket updates"`
