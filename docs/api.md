# HTTP & WebSocket API

`catan/api/app.py` is a FastAPI app (`create_app(service)`) exposing REST
endpoints plus a live WebSocket per game. The HTTP layer is thin: it decodes
JSON into commands, calls `GameService`, and serializes the result. Every
successful command **broadcasts** the new state to all WebSocket clients
watching that game, so frontends update live.

## Running

```bash
CATAN_DB=game.db catan serve --host 127.0.0.1 --port 8000
```

- Without `CATAN_DB`, the default store is `:memory:` (games vanish on restart).
- CORS is wide open (`allow_origins=["*"]`) for easy local development.
- Title: *Catan Companion API*. Interactive docs at `/docs` (FastAPI default).

## Conventions

- All paths are under `/api`.
- Game state is serialized by the codec's `encode_state` (see
  [persistence.md](persistence.md)); its TypeScript shape is `GameStateDTO` in
  `web/src/types.ts`.
- Errors use standard HTTP codes: `400` bad request/layout/command, `404`
  unknown game, `422` a command that failed validation (body is the list of
  rule-violation strings).

## Endpoints

### `GET /api/board_template`

Empty board geometry for the custom-board designer. Returns hexes in **spiral
order** (the order `custom_board` consumes, so the client can submit
terrain/number arrays by hex index), plus pixel `vertices`, `edges`, and the
exact base-game `terrain_counts` and `number_counts` the designer enforces.

### `POST /api/games`

Create a game.

```json
{ "players": ["red", "blue", "white"],
  "board": "standard",          // "standard" | "random" | "custom"
  "seed": 42,                    // optional, for "random"
  "layout": {                    // required for "custom"
    "terrain": [ ...19... ],
    "numbers": [ ...18... ],
    "ports":   [ ...9 optional... ]
  } }
```

Returns `{ "game_id": "...", "state": <GameStateDTO> }`. A bad custom layout →
`400`; an invalid player set → `400`.

### `GET /api/games`

List games. Each item: `game_id`, `phase`, `turn`, `winner`, `players`.

### `DELETE /api/games/{game_id}`

Delete a game and its events/snapshots. Returns `{ "ok": true }`.

### `GET /api/games/{game_id}/state?at={seq}`

Current state, or the time-traveled state as of (inclusive) sequence `at`. `404`
if the game is unknown.

### `GET /api/games/{game_id}/layout`

Pixel geometry for the SVG board: hex centers + corners, vertex positions, edge
vertex pairs, and port positions. Computed from the board's pointy-top axial
coordinates.

### `GET /api/games/{game_id}/events`

The event stream as a list of `{ seq, ts, type, ...fields }`. The large `board`
payload on `GameCreated` is stripped.

### `GET /api/games/{game_id}/metrics`

The full metrics object (`GameMetrics.to_dict()` — dice histogram, per-player
production/luck/trades/timelines, etc.). `404` if the game has no events.

### `POST /api/games/{game_id}/commands`

Submit a **structured** command as JSON. The body is decoded by
`decode_command`; the `type` field selects the command, e.g.:

```json
{ "type": "BuildSettlement", "player": "red", "vertex": 23 }
{ "type": "RollDice", "player": "red", "die1": 4, "die2": 3 }
{ "type": "MoveRobber", "player": "red", "hex": [0, 1],
  "victim": "blue", "resource": "ore" }
{ "type": "TradeWithBank", "player": "red",
  "give": "ore", "give_amount": 4, "receive": "wool", "receive_amount": 1 }
```

(The full set of command `type`s matches the command catalog in
[domain-model.md](domain-model.md).)

Responses:

- success → `{ "ok": true, "events": ["RobberMoved", "ResourceStolen"], "state": <DTO> }`
  and a broadcast to WebSocket clients;
- bad command shape → `400`;
- unknown game → `404`;
- rejected by the rules → `422` with `detail` = list of error strings.

### `POST /api/games/{game_id}/command_text`

Submit a **REPL-style text** command, parsed server-side with the same grammar
as the CLI (see [cli.md](cli.md)):

```json
{ "line": "build settlement 23" }
```

Same response/broadcast behavior as `/commands`. Parse failures → `400`,
rule rejections → `422`.

## WebSocket

### `GET /api/games/{game_id}/ws`

On connect, the server immediately sends the current state. Thereafter, every
successful command (from any client) pushes the new state to all subscribers:

```json
{ "type": "state", "state": <GameStateDTO> }
```

If the game is unknown at connect time, the server sends
`{ "type": "error", "error": "unknown game" }`. Inbound client messages are
ignored (the socket is push-only / keep-alive). Dead sockets are dropped on the
next broadcast.

The frontend uses this to stay live; when scrubbing through history it pauses
applying pushes (see [web.md](web.md)).

## See also

- The command/event/state shapes: [domain-model.md](domain-model.md)
- State (de)serialization and time travel: [persistence.md](persistence.md)
- The client that consumes this API: [web.md](web.md)
