"""FastAPI application: REST endpoints plus a live WebSocket per game.

The HTTP layer is thin — it decodes JSON into commands, calls
:class:`~catan.store.repository.GameService`, and serializes the result. Every
successful command broadcasts the new state to all WebSocket clients watching
that game, so the frontend updates live.
"""

from __future__ import annotations

import math
import os
import random

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..cli.parser import ParseError, build_command
from ..domain import commands as cmd
from ..domain.board import Board, custom_board, random_board, standard_board
from ..engine.projections import compute_metrics
from ..store.codec import decode_command, encode_event, encode_state
from ..store.event_store import EventStore, UnknownGame
from ..store.repository import GameService


def _offset_outward(x: float, y: float, dist: float = 0.62) -> list[float]:
    """Push a point radially away from the board center so ports float in the
    sea outside the hexes instead of overlapping number tokens."""
    mag = math.hypot(x, y) or 1.0
    return [x + x / mag * dist, y + y / mag * dist]


def _layout(board: Board) -> dict:
    """Pixel geometry for the SVG board (pointy-top axial -> x/y)."""

    def center(c):
        q, r = c
        return (math.sqrt(3) * (q + r / 2), 1.5 * r)

    topo = board.topology
    vertices: dict[int, list[float]] = {}
    for vid, vk in topo.vertices.items():
        pts = [center(c) for c in vk]
        vertices[vid] = [
            sum(p[0] for p in pts) / len(pts),
            sum(p[1] for p in pts) / len(pts),
        ]

    hexes = []
    for h in topo.hexes:
        cx, cy = center(h)
        corners = sorted(
            topo.hex_vertices[h],
            key=lambda v: math.atan2(vertices[v][1] - cy, vertices[v][0] - cx),
        )
        hexes.append(
            {
                "coord": list(h),
                "center": [cx, cy],
                "terrain": board.terrain[h].value,
                "number": board.numbers.get(h),
                "vertices": corners,
            }
        )

    ports = []
    for p in board.ports:
        vids = sorted(p.vertices)
        mx = sum(vertices[v][0] for v in vids) / len(vids)
        my = sum(vertices[v][1] for v in vids) / len(vids)
        ports.append(
            {"type": p.type.value, "vertices": vids, "pos": _offset_outward(mx, my)}
        )

    return {
        "hexes": hexes,
        "vertices": vertices,
        "edges": {str(eid): [a, b] for eid, (a, b) in topo.edge_vertices.items()},
        "ports": ports,
    }


def _board_template() -> dict:
    """Empty board geometry for the custom-board designer.

    Hexes are returned in *spiral order*, the same order ``custom_board``
    consumes, so the frontend can submit its terrain/number arrays by hex index
    directly. Also returns the exact base-game tile and number-token counts the
    designer enforces.
    """
    from ..domain.board import _perimeter_edges, _port_type_pool, _spiral_order
    from ..domain.constants import (
        NUMBER_TOKEN_COUNTS,
        PORT_COUNTS,
        TERRAIN_COUNTS,
    )
    from ..domain.geometry import build_topology

    def center(c):
        q, r = c
        return (math.sqrt(3) * (q + r / 2), 1.5 * r)

    topo = build_topology()
    vertices: dict[int, list[float]] = {}
    for vid, vk in topo.vertices.items():
        pts = [center(c) for c in vk]
        vertices[vid] = [
            sum(p[0] for p in pts) / len(pts),
            sum(p[1] for p in pts) / len(pts),
        ]

    hexes = []
    for h in _spiral_order(topo):
        cx, cy = center(h)
        corners = sorted(
            topo.hex_vertices[h],
            key=lambda v: math.atan2(vertices[v][1] - cy, vertices[v][0] - cx),
        )
        hexes.append({"coord": list(h), "center": [cx, cy], "vertices": corners})

    perim = _perimeter_edges(topo)
    perimeter_edges = []
    for eid in perim:
        a, b = topo.edge_vertices[eid]
        mx = (vertices[a][0] + vertices[b][0]) / 2
        my = (vertices[a][1] + vertices[b][1]) / 2
        perimeter_edges.append(
            {"edge": eid, "vertices": [a, b], "pos": _offset_outward(mx, my)}
        )

    # The even spread the engine uses by default; the designer starts here and
    # lets you drag ports to wherever they sit on your physical board.
    pool = _port_type_pool()
    n, count = len(perim), len(pool)
    default_ports = [
        {"type": pool[i].value, "edge": perim[round(i * n / count) % n]}
        for i in range(count)
    ]

    return {
        "hexes": hexes,
        "vertices": vertices,
        "edges": {str(eid): [a, b] for eid, (a, b) in topo.edge_vertices.items()},
        "terrain_counts": {t.value: n for t, n in TERRAIN_COUNTS.items()},
        "number_counts": {str(num): n for num, n in NUMBER_TOKEN_COUNTS.items()},
        "port_counts": {pt.value: c for pt, c in PORT_COUNTS.items()},
        "perimeter_edges": perimeter_edges,
        "default_ports": default_ports,
    }


def _owner(x_catan_client: str | None) -> str | None:
    """Normalize the per-browser client id header into an owner id.

    Each browser mints and persists its own random id (no login); games it
    creates are tagged with that id so its lobby only lists its own games (plus
    ownerless/legacy ones). A blank or missing header means "no notion of a
    browser session" — e.g. the CLI or a bare API client — so listing/creation
    fall back to the unfiltered, ownerless behavior that predates this feature.
    """
    client = (x_catan_client or "").strip()
    return client or None


def _build_board(board: str, seed: int | None, layout: dict | None) -> Board:
    """Construct a board from a request spec, raising HTTPException on bad input."""
    if board == "random":
        return random_board(random.Random(seed))
    if board == "custom":
        if not layout:
            raise HTTPException(status_code=400, detail="custom board requires a layout")
        raw_ports = layout.get("ports")
        port_edges = [(p["type"], p["edge"]) for p in raw_ports] if raw_ports else None
        try:
            return custom_board(
                terrains=layout.get("terrain", []),
                numbers=layout.get("numbers", []),
                port_edges=port_edges,
            )
        except (ValueError, KeyError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"bad layout: {e}")
    return standard_board()


class CreateGameRequest(BaseModel):
    players: list[str]
    board: str = "standard"
    seed: int | None = None
    layout: dict | None = None  # for board == "custom": terrain/numbers/ports
    mode: str = "strict"        # "strict" (guided rules) or "dev" (sandbox)


class SetModeRequest(BaseModel):
    mode: str


class ConnectionManager:
    """Tracks the live sockets watching each game so state pushes reach them."""

    def __init__(self) -> None:
        self.connections: dict[str, set[WebSocket]] = {}

    async def connect(self, game_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.connections.setdefault(game_id, set()).add(ws)

    def disconnect(self, game_id: str, ws: WebSocket) -> None:
        self.connections.get(game_id, set()).discard(ws)

    async def broadcast(self, game_id: str, message: dict) -> None:
        for ws in list(self.connections.get(game_id, set())):
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001 - drop dead sockets
                self.disconnect(game_id, ws)


def create_app(service: GameService | None = None) -> FastAPI:
    svc = service or GameService(EventStore(os.environ.get("CATAN_DB", ":memory:")))
    manager = ConnectionManager()
    app = FastAPI(title="Catan Companion API")
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )

    def _encode_with_mode(game_id: str, state) -> dict:
        d = encode_state(state)
        d["mode"] = svc.get_mode(game_id)
        return d

    def _state_dict(game_id: str, *, up_to: int | None = None) -> dict:
        try:
            return _encode_with_mode(game_id, svc.state(game_id, up_to=up_to))
        except UnknownGame:
            raise HTTPException(status_code=404, detail=f"unknown game {game_id}")

    async def _broadcast_new_state(game_id: str, state) -> None:
        await manager.broadcast(
            game_id, {"type": "state", "state": _encode_with_mode(game_id, state)}
        )

    @app.get("/api/board_template")
    def board_template() -> dict:
        return _board_template()

    @app.post("/api/games")
    def create_game(req: CreateGameRequest, x_catan_client: str | None = Header(None)) -> dict:
        board = _build_board(req.board, req.seed, req.layout)
        mode = req.mode if req.mode in ("strict", "dev") else "strict"
        try:
            game_id = svc.create_game(
                cmd.CreateGame(board=board, player_order=tuple(req.players)),
                mode=mode,
                owner=_owner(x_catan_client),
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"game_id": game_id, "mode": mode, "state": _state_dict(game_id)}

    @app.get("/api/games")
    def list_games(x_catan_client: str | None = Header(None)) -> list[dict]:
        out = []
        for gid in svc.list_games(_owner(x_catan_client)):
            st = svc.state(gid)
            out.append(
                {
                    "game_id": gid,
                    "phase": st.phase.value,
                    "turn": st.turn_number,
                    "winner": st.winner,
                    "players": st.player_order,
                    "mode": svc.get_mode(gid),
                }
            )
        return out

    @app.post("/api/games/{game_id}/mode")
    def set_mode(game_id: str, req: SetModeRequest) -> dict:
        if req.mode not in ("strict", "dev"):
            raise HTTPException(status_code=400, detail="mode must be 'strict' or 'dev'")
        try:
            svc.set_mode(game_id, req.mode)
        except UnknownGame:
            raise HTTPException(status_code=404, detail="unknown game")
        return {"ok": True, "mode": req.mode}

    @app.delete("/api/games/{game_id}")
    def delete_game(game_id: str) -> dict:
        svc.delete_game(game_id)
        return {"ok": True}

    @app.get("/api/games/{game_id}/state")
    def get_state(game_id: str, at: int | None = None) -> dict:
        return _state_dict(game_id, up_to=at)

    @app.get("/api/games/{game_id}/layout")
    def get_layout(game_id: str) -> dict:
        try:
            return _layout(svc.state(game_id).board)
        except UnknownGame:
            raise HTTPException(status_code=404, detail="unknown game")

    @app.get("/api/games/{game_id}/events")
    def get_events(game_id: str) -> list[dict]:
        try:
            stored = svc.store.load_events(game_id)
        except UnknownGame:
            raise HTTPException(status_code=404, detail="unknown game")
        out = []
        for se in stored:
            payload = encode_event(se.event)
            payload.pop("board", None)
            out.append({"seq": se.seq, "ts": se.ts, **payload})
        return out

    @app.get("/api/games/{game_id}/metrics")
    def get_metrics(game_id: str) -> dict:
        events = [se.event for se in svc.store.load_events(game_id)]
        if not events:
            raise HTTPException(status_code=404, detail="unknown game")
        return compute_metrics(events).to_dict()

    @app.post("/api/games/{game_id}/commands")
    async def submit_command(game_id: str, body: dict) -> dict:
        try:
            command = decode_command(body)
        except (ValueError, KeyError) as e:
            raise HTTPException(status_code=400, detail=f"bad command: {e}")
        try:
            result = svc.try_apply(game_id, command)
        except UnknownGame:
            raise HTTPException(status_code=404, detail="unknown game")
        if not result.ok:
            raise HTTPException(status_code=422, detail=result.errors)
        new_state = svc.state(game_id)
        await _broadcast_new_state(game_id, new_state)
        return {
            "ok": True,
            "events": [type(e).__name__ for e in result.events],
            "state": _encode_with_mode(game_id, new_state),
        }

    @app.post("/api/games/{game_id}/command_text")
    async def submit_command_text(game_id: str, body: dict) -> dict:
        line = (body or {}).get("line", "")
        try:
            state = svc.state(game_id)
        except UnknownGame:
            raise HTTPException(status_code=404, detail="unknown game")
        try:
            command = build_command(state, line)
        except ParseError as e:
            raise HTTPException(status_code=400, detail=f"parse error: {e}")
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"bad command: {e}")
        result = svc.try_apply(game_id, command)
        if not result.ok:
            raise HTTPException(status_code=422, detail=result.errors)
        new_state = svc.state(game_id)
        await _broadcast_new_state(game_id, new_state)
        return {
            "ok": True,
            "events": [type(e).__name__ for e in result.events],
            "state": _encode_with_mode(game_id, new_state),
        }

    @app.websocket("/api/games/{game_id}/ws")
    async def game_ws(ws: WebSocket, game_id: str) -> None:
        await manager.connect(game_id, ws)
        try:
            try:
                await ws.send_json(
                    {"type": "state", "state": _encode_with_mode(game_id, svc.state(game_id))}
                )
            except UnknownGame:
                await ws.send_json({"type": "error", "error": "unknown game"})
            while True:
                await ws.receive_text()  # keep-alive; inbound messages ignored
        except WebSocketDisconnect:
            manager.disconnect(game_id, ws)

    return app


app = create_app()
