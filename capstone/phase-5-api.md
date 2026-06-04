# Phase 5 — REST API & WebSockets

> **Goal:** Expose the game service over HTTP so a browser can use it.
>
> **Branch:** `git checkout -b phase-5-api`

---

## 5.1 REST Design Principles

| Convention | Example |
|---|---|
| Resources are nouns | `/api/games`, not `/api/getGames` |
| HTTP verbs express action | `POST` to create, `GET` to read, `DELETE` to delete |
| IDs in the URL | `/api/games/{id}` |
| Status codes have meaning | 200 OK, 201 Created, 400 Bad Request, 404 Not Found, 422 Unprocessable |
| Body is JSON | `Content-Type: application/json` |

---

## 5.2 Your API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/board_template` | Empty board geometry for the custom board designer |
| POST | `/api/games` | Create a new game |
| GET | `/api/games` | List all games |
| DELETE | `/api/games/{id}` | Delete a game |
| GET | `/api/games/{id}/state?at=SEQ` | Current state (or state at seq) |
| GET | `/api/games/{id}/layout` | SVG pixel coordinates for the board |
| GET | `/api/games/{id}/events` | Full event log |
| GET | `/api/games/{id}/metrics` | Post-game analytics |
| POST | `/api/games/{id}/commands` | Submit a structured command (JSON) |
| POST | `/api/games/{id}/command_text` | Submit a REPL text command |
| POST | `/api/games/{id}/mode` | Switch strict/dev mode |
| WS | `/api/games/{id}/ws` | WebSocket live stream |

---

## 5.3 FastAPI App

**`catan/api/app.py`**

```python
import asyncio
import uuid
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

def create_app(service: GameService | None = None) -> FastAPI:
    if service is None:
        import os
        db_path = os.environ.get("CATAN_DB", ":memory:")
        service = GameService(EventStore(db_path))

    app = FastAPI(title="Catan Companion", docs_url="/docs")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],    # tighten in production
        allow_methods=["*"],
        allow_headers=["*"],
    )

    manager = ConnectionManager()

    @app.post("/api/games", status_code=201)
    def create_game(body: CreateGameRequest):
        game_id = uuid.uuid4().hex[:8]
        service.create_game(game_id, board_type=body.board, mode=body.mode,
                            players=body.players, layout=body.layout)
        return {"game_id": game_id}

    @app.get("/api/games")
    def list_games():
        return service.list_games()

    @app.get("/api/games/{game_id}/state")
    def get_state(game_id: str, at: int | None = None):
        try:
            state, seq = service.state(game_id, up_to=at)
        except UnknownGame:
            raise HTTPException(404, "Game not found")
        return _encode_with_mode(state, seq, service.get_mode(game_id))

    @app.get("/api/games/{game_id}/layout")
    def get_layout(game_id: str):
        try:
            state, _ = service.state(game_id)
        except UnknownGame:
            raise HTTPException(404, "Game not found")
        return _layout(state.board)

    @app.post("/api/games/{game_id}/commands")
    def post_command(game_id: str, body: dict):
        try:
            command = decode_command(body)
        except (KeyError, ValueError) as e:
            raise HTTPException(400, f"Bad command: {e}")
        try:
            result = service.try_apply(game_id, command)
        except UnknownGame:
            raise HTTPException(404, "Game not found")
        if not result.ok:
            raise HTTPException(422, detail=result.errors)
        state, seq = service.state(game_id)
        payload = _encode_with_mode(state, seq, service.get_mode(game_id))
        asyncio.create_task(manager.broadcast(game_id, payload))
        return payload

    @app.post("/api/games/{game_id}/command_text")
    def post_command_text(game_id: str, body: dict):
        """Accept a REPL text line, parse it, and apply."""
        text = body.get("text", "")
        try:
            state, _ = service.state(game_id)
            command  = build_command(state, text)   # from catan.cli.parser
        except ParseError as e:
            raise HTTPException(400, str(e))
        except UnknownGame:
            raise HTTPException(404, "Game not found")
        result = service.try_apply(game_id, command)
        if not result.ok:
            raise HTTPException(422, detail=result.errors)
        state, seq = service.state(game_id)
        payload = _encode_with_mode(state, seq, service.get_mode(game_id))
        asyncio.create_task(manager.broadcast(game_id, payload))
        return payload

    @app.post("/api/games/{game_id}/mode")
    def set_mode(game_id: str, body: dict):
        mode = body.get("mode", "strict")
        try:
            service.set_mode(game_id, mode)
        except UnknownGame:
            raise HTTPException(404, "Game not found")
        except ValueError as e:
            raise HTTPException(400, str(e))
        return {"mode": mode}

    @app.delete("/api/games/{game_id}", status_code=204)
    def delete_game(game_id: str):
        try:
            service.delete_game(game_id)
        except UnknownGame:
            raise HTTPException(404, "Game not found")

    @app.websocket("/api/games/{game_id}/ws")
    async def websocket_endpoint(game_id: str, ws: WebSocket):
        await manager.connect(game_id, ws)
        try:
            state, seq = service.state(game_id)
            payload = _encode_with_mode(state, seq, service.get_mode(game_id))
            await ws.send_json({"type": "state", "state": payload})
            while True:
                await ws.receive_text()   # keep alive; inbound messages ignored
        except (WebSocketDisconnect, Exception):
            manager.disconnect(game_id, ws)

    return app


# Module-level singleton for `uvicorn catan.api.app:app`
app = create_app()
```

---

## 5.4 HTTP Status Code Convention

- **200 OK** — GET that found data
- **201 Created** — POST that created a resource
- **204 No Content** — DELETE
- **400 Bad Request** — malformed JSON or unknown command type
- **404 Not Found** — game_id doesn't exist
- **422 Unprocessable** — structurally valid command that violates game rules

> **Note:** The reference implementation uses 422 (not 400) for rule violations because the request was *structurally* valid — it was a real `BuildSettlement` command — but the game rules rejected it. This is more precise than 400.

---

## 5.5 WebSocket Hub

```python
class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, game_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(game_id, set()).add(ws)

    def disconnect(self, game_id: str, ws: WebSocket) -> None:
        self._connections.get(game_id, set()).discard(ws)

    async def broadcast(self, game_id: str, payload: dict) -> None:
        message = {"type": "state", "state": payload}
        dead: set[WebSocket] = set()
        for ws in self._connections.get(game_id, set()):
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(game_id, ws)
```

---

## 5.6 Board Layout: Hex to Pixel Coordinates

The frontend needs pixel coordinates to render the SVG board. Convert axial coordinates to pixel x/y (pointy-top orientation):

```python
import math

def hex_to_pixel(coord: Coord, size: float = 60.0) -> tuple[float, float]:
    q, r = coord
    x = size * math.sqrt(3) * (q + r / 2)
    y = size * (3 / 2 * r)
    return x, y

def hex_corners(cx: float, cy: float, size: float = 60.0) -> list[tuple[float, float]]:
    """6 corner pixel coordinates for a pointy-top hex centered at (cx, cy)."""
    return [
        (cx + size * math.cos(math.radians(60 * i - 30)),
         cy + size * math.sin(math.radians(60 * i - 30)))
        for i in range(6)
    ]
```

The `GET /api/games/{id}/layout` endpoint returns:

```json
{
  "hexes": [
    {"coord": {"q": 0, "r": 0}, "x": 0, "y": 0, "terrain": "forest",
     "number": 5, "pips": 4, "robber": false,
     "corners": [[x,y], [x,y], [x,y], [x,y], [x,y], [x,y]]}
  ],
  "vertices": [
    {"id": 0, "x": 34.6, "y": -60.0, "building": null}
  ],
  "edges": [
    {"index": 0, "x1": 34.6, "y1": -60.0, "x2": 0.0, "y2": -60.0, "road": null}
  ],
  "ports": [
    {"type": "lumber", "x": ..., "y": ..., "vertices": [0, 1]}
  ]
}
```

---

## 5.7 The Board Template Endpoint

The `GET /api/board_template` endpoint powers the custom board designer (Phase 6 extra credit). It returns an empty board geometry with:

```json
{
  "hexes": [...],            // 19 hexes in spiral order
  "perimeter_edges": [...],  // edge indices on the board perimeter
  "default_ports": [...],    // suggested port positions
  "terrain_counts": {...},   // how many of each terrain type
  "number_counts": {...},    // how many of each number token
  "port_counts": {...}       // how many of each port type
}
```

This lets the frontend render an interactive board where the user can assign terrain, numbers, and ports to match their physical board before starting a game.

---

## Phase 5 Checkpoint

Use `curl` or a REST client (Insomnia, Postman, or `curl`) to verify:

```bash
# Create a game
curl -X POST http://localhost:8000/api/games \
  -H 'Content-Type: application/json' \
  -d '{"players": ["alice", "bob", "charlie"], "board": "standard", "mode": "strict"}'
# → {"game_id": "abc12345"}

# Get state
curl http://localhost:8000/api/games/abc12345/state

# Submit a command
curl -X POST http://localhost:8000/api/games/abc12345/commands \
  -H 'Content-Type: application/json' \
  -d '{"type": "PlaceSetupSettlement", "pid": "alice", "vertex_id": 0}'

# Invalid move → 422
curl -X POST http://localhost:8000/api/games/abc12345/commands \
  -H 'Content-Type: application/json' \
  -d '{"type": "RollDice", "pid": "alice", "d1": 3, "d2": 4}'
# → 422 (not alice's turn in setup phase)
```

- [ ] `POST /api/games` creates game, returns `game_id`
- [ ] `GET /api/games/{id}/state` returns valid JSON
- [ ] `POST /api/games/{id}/commands` with valid move returns new state
- [ ] `POST /api/games/{id}/commands` with invalid move returns 422 (not 500)
- [ ] Open two browser tabs to WS URL — both receive state updates on command POST
- [ ] `GET /api/games/{id}/layout` returns 19 hexes, 54 vertices, 72 edges
- [ ] Commit: `"Phase 5: FastAPI REST API with WebSocket broadcast"`
