# Web frontend

`web/` is a React + TypeScript + Vite single-page app. It is a thin, live view
over the [API](api.md): it never holds game rules of its own (beyond mirroring a
couple of read-only helpers), submits commands, and re-renders from server state
pushed over the WebSocket.

## Running

```bash
# Terminal 1: the API
CATAN_DB=game.db catan serve            # http://localhost:8000

# Terminal 2: the dev server
cd web
npm install
npm run dev                             # Vite, proxies /api → :8000
```

`vite.config.ts` proxies both `/api` HTTP and the WebSocket to
`http://localhost:8000`, so the SPA and server appear same-origin in dev. Build
for production with `npm run build` (`tsc -b && vite build`).

## Structure

```
web/src/
├── main.tsx              React entry point
├── App.tsx               Lobby + GameView (top-level state & wiring)
├── api.ts                Typed fetch wrapper around every REST endpoint
├── useGameSocket.ts      Hook: subscribe to live state pushes
├── types.ts              DTOs mirroring the backend JSON (GameStateDTO, …)
├── colors.ts             Per-player colors and terrain fills
├── styles.css            App styles
└── components/
    ├── Board.tsx          SVG board: hexes, vertices, edges, pieces, robber
    ├── Palette.tsx        Drag source for road/settlement/city/robber tools
    ├── ActionsPanel.tsx   Buttons/forms for roll, build, buy, trade, dev cards
    ├── CommandBar.tsx     Free-text REPL input (→ /command_text)
    ├── RobberPanel.tsx    Pick a victim/resource after moving the robber
    ├── Players.tsx        Per-player resource/VP/piece summary
    ├── Metrics.tsx        Dice histogram, luck, timelines
    ├── EventLog.tsx       Scrollable list of the event stream
    └── BoardDesigner.tsx  Custom-board editor (paint terrain + numbers)
```

## Top-level flow (`App.tsx`)

`App` switches between three screens by local state:

- **Lobby** — list/create/delete games. Choosing the `custom` board opens the
  designer; otherwise it `POST`s `/api/games` and opens the game.
- **BoardDesigner** — paint a real-table layout, then create the game from it.
- **GameView** — the live board and panels for an open game.

`GameView` is the hub. It loads layout, state, events, and metrics; subscribes to
the WebSocket; and exposes two apply helpers:

- `applyCommand(cmd)` → `POST /commands` (structured),
- `applyText(line)` → `POST /command_text` (REPL text).

Both set state from the **response** (not only the socket) so updates are
reliable, then refresh derived data (events + metrics).

### Acting player inference

The UI mirrors the backend's setup snake-draft logic (`setupExpected`) so it
knows who places next during setup — the engine keeps `current_index` at 0 until
play begins. In the play phase the acting player is `player_order[current_index]`.
Selecting a player chip overrides until the expected player changes again.

### Placement & the robber

Pieces are placed by selecting a tool from the `Palette` (or dragging it) and
clicking a vertex/edge on the `Board`; `GameView.onPlace` builds the right
command (`PlaceSetup*` in setup, `Build*` in play) for the acting player. After a
7, `robber_pending` flips the UI into robber mode automatically; clicking a hex
opens `RobberPanel` to choose the victim and stolen resource, which submits
`MoveRobber` (or `PlayKnight` when not resolving a 7). `Esc` cancels the active
tool.

### History scrubber & live mode

A range slider (`viewSeq`) lets you scrub to any sequence number; the view
fetches `GET /state?at=<seq>` for that point. At the maximum it returns to
**live** mode (`viewSeq === null`). `useGameSocket` only applies pushes while
live, so scrubbing through history isn't interrupted by new events.

## API client (`api.ts`)

A small typed wrapper: one function per endpoint, all returning typed promises.
`ApiError` carries the HTTP `status` and the server's `detail` (a string, or the
list of rule-violation strings on a `422`), which the UI surfaces as the
red/green placement message.

## Socket hook (`useGameSocket.ts`)

Opens a `WebSocket` to `/api/games/{id}/ws`, parses `{ type: "state", state }`
messages, and calls back with the new state — but only when `enabled` (live
mode). Uses refs so the latest callback/flag are seen without reopening the
socket.

## See also

- The endpoints and DTOs this consumes: [api.md](api.md)
- The state shape rendered on the board: [domain-model.md](domain-model.md)
