# Lab 5 — REST API & WebSockets

> **Goal:** Expose the game service over HTTP and WebSocket so a browser can drive it.
>
> **Branch:** `git checkout -b lab-5-api`

---

## Background

REST (Representational State Transfer) is a set of HTTP conventions:

| Convention | Example |
|---|---|
| Resources are nouns | `/api/games`, not `/api/getGames` |
| Verbs express action | `POST` create, `GET` read, `DELETE` delete |
| IDs in the URL | `/api/games/{id}` |
| Status codes carry meaning | 200, 201, 204, 400, 404, 422 |
| JSON bodies | `Content-Type: application/json` |

A **WebSocket** is a persistent two-way connection. You use it to push new game state to every connected browser the instant a command succeeds, so all players share one live view.

---

## Specification

All work lives in `catan/api/app.py`. Provide a factory and a module-level app:

```python
def create_app(service: GameService | None = None) -> FastAPI:
    """Build the app. If no service is given, construct one from CATAN_DB
    (default :memory:). Configure CORS. Register all routes. Return the app."""

app = create_app()   # so `uvicorn catan.api.app:app` works
```

### Endpoints you must implement

| Method | Path | Purpose | Success code |
|--------|------|---------|--------------|
| GET | `/api/board_template` | Empty board geometry for the custom designer | 200 |
| POST | `/api/games` | Create a game (`{players, board, mode, layout?}`) → `{game_id}` | 201 |
| GET | `/api/games` | List games | 200 |
| DELETE | `/api/games/{id}` | Delete a game | 204 |
| GET | `/api/games/{id}/state?at=SEQ` | Current state (or state at a seq) | 200 |
| GET | `/api/games/{id}/layout` | SVG pixel geometry for the board | 200 |
| GET | `/api/games/{id}/events` | Full event log | 200 |
| GET | `/api/games/{id}/metrics` | Post-game analytics (Lab 7) | 200 |
| POST | `/api/games/{id}/commands` | Submit a structured command (JSON) | 200 |
| POST | `/api/games/{id}/command_text` | Submit a REPL text line | 200 |
| POST | `/api/games/{id}/mode` | Switch strict/dev | 200 |
| WS | `/api/games/{id}/ws` | Live state stream | — |

### Status-code contract (the grader checks this)

- **200** GET that found data, or a successful command.
- **201** game created.
- **204** game deleted.
- **400** malformed JSON or an unknown command type (a *structural* problem).
- **404** unknown `game_id`.
- **422** a structurally valid command that the *game rules* rejected.

> **Why 422, not 400, for rule violations?** The request was a real, well-formed command; the *game state* rejected it. 422 ("Unprocessable Entity") communicates that precisely. Reserve 400 for input you could not even parse.

### Supporting pieces you must build

- A `ConnectionManager` that tracks WebSocket connections per game and can `connect`, `disconnect`, and `broadcast` a payload to all sockets for a game (dropping dead ones). After every successful command, broadcast the new state.
- A `decode_command(body: dict) -> Command` that turns the JSON `{"type": ..., ...}` into the right command dataclass (the inverse of how the frontend encodes commands).
- A state-to-DTO encoder that serializes `GameState` for the wire (include the current `seq` and the game `mode`).
- A `layout(board) -> dict` that converts the board into pixel geometry (hexes with corner points, vertices, edges, ports) for the SVG renderer.
- A `board_template` response for the custom-board designer (hex positions, perimeter edges, suggested ports, and the terrain/number/port counts).

### Hex-to-pixel conversion

The layout endpoint must convert axial coordinates to pixel positions. Use a **single consistent orientation** (pointy-top or flat-top) everywhere. [Appendix B: Hex Math](appendix-hex-math.md) gives the axial-to-pixel formula and the corner formula. You implement `hex_to_pixel(coord, size)` and `hex_corners(cx, cy, size)` and build the layout DTO from them.

The layout DTO shape (the frontend in Lab 6 depends on it):

```json
{
  "hexes":    [{"coord":{"q":0,"r":0},"x":0,"y":0,"terrain":"forest","number":5,"pips":4,"robber":false,"corners":[[x,y],...6]}],
  "vertices": [{"id":0,"x":34.6,"y":-60,"building":null}],
  "edges":    [{"index":0,"x1":...,"y1":...,"x2":...,"y2":...,"road":null}],
  "ports":    [{"type":"lumber","x":...,"y":...,"vertices":[0,1]}]
}
```

---

## Your Tasks

1. Implement `create_app` with CORS and the factory/`app` pattern.
2. Implement the game-lifecycle routes: create (201), list, delete (204), get state (with `at`), get events.
3. Implement `decode_command` and the structured `POST /commands` route (400 on bad command, 404 on unknown game, 422 on rule violation, broadcast + return new state on success).
4. Implement `POST /command_text` reusing `build_command` from Lab 4.
5. Implement `POST /mode`.
6. Implement `hex_to_pixel`, `hex_corners`, the `layout` builder, and `GET /layout`.
7. Implement the `ConnectionManager` and the WebSocket endpoint (send current state on connect; keep alive; broadcast on commands).
8. Implement `GET /board_template`.

---

## Hints & Pitfalls

- Map exceptions to status codes carefully. Wrap `service` calls: unknown game → 404, bad/unknown command → 400, rule failure (`Result` not ok) → 422.
- Broadcasting from a sync route handler: schedule the async `broadcast` as a task rather than awaiting it in a sync function.
- The WebSocket handler must remove the connection on disconnect, or you will leak sockets.
- The layout is a pure function of the board — it is a good candidate for caching later, but correctness first.

---

## Tests First (use FastAPI's `TestClient`)

- `POST /api/games` returns 201 and a `game_id`; `GET .../state` returns 200 with `phase == "setup"`.
- A rule-violating command returns 422 (not 500, not 400).
- A malformed/unknown command type returns 400.
- An unknown game id returns 404.
- `GET .../layout` returns 19 hexes, 54 vertices, 72 edges, 9 ports.
- A mode switch from dev→strict then an out-of-turn command returns 422.

---

## Checkpoint

- [ ] `POST /api/games` creates a game and returns `game_id`
- [ ] `GET /api/games/{id}/state` returns valid JSON
- [ ] A valid command returns the new state; an invalid one returns 422
- [ ] Two browser tabs on the WS URL both receive updates when a command is posted
- [ ] `GET /api/games/{id}/layout` returns 19 hexes, 54 vertices, 72 edges
- [ ] Commit: `"Lab 5: FastAPI REST API with WebSocket broadcast"`
