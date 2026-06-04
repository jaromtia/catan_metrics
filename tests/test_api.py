"""API tests via FastAPI TestClient (REST + WebSocket)."""

from fastapi.testclient import TestClient

from catan.api.app import create_app
from catan.store.event_store import EventStore
from catan.store.repository import GameService


def client():
    return TestClient(create_app(GameService(EventStore())))


def new_game(c, players=("red", "blue")):
    resp = c.post("/api/games", json={"players": list(players), "board": "standard"})
    assert resp.status_code == 200
    return resp.json()["game_id"]


def test_create_and_list_games():
    c = client()
    gid = new_game(c)
    games = c.get("/api/games").json()
    assert any(g["game_id"] == gid for g in games)
    assert games[0]["phase"] == "setup"


def test_state_and_events_endpoints():
    c = client()
    gid = new_game(c)
    state = c.get(f"/api/games/{gid}/state").json()
    assert state["phase"] == "setup"
    assert set(state["players"]) == {"red", "blue"}
    events = c.get(f"/api/games/{gid}/events").json()
    assert events[0]["type"] == "GameCreated"


def test_valid_command_applies_and_invalid_is_rejected():
    c = client()
    gid = new_game(c)
    ok = c.post(f"/api/games/{gid}/commands",
                json={"type": "PlaceSetupSettlement", "player": "red", "vertex": 0})
    assert ok.status_code == 200
    assert ok.json()["events"] == ["SetupSettlementPlaced"]

    bad = c.post(f"/api/games/{gid}/commands",
                 json={"type": "RollDice", "player": "red", "die1": 3, "die2": 4})
    assert bad.status_code == 422  # cannot roll during setup


def test_delete_game():
    c = client()
    gid = new_game(c)
    assert any(g["game_id"] == gid for g in c.get("/api/games").json())
    assert c.delete(f"/api/games/{gid}").status_code == 200
    assert all(g["game_id"] != gid for g in c.get("/api/games").json())
    assert c.get(f"/api/games/{gid}/state").status_code == 404


def test_unknown_game_is_404():
    c = client()
    assert c.get("/api/games/nope/state").status_code == 404
    assert c.get("/api/games/nope/metrics").status_code == 404


def test_metrics_endpoint():
    c = client()
    gid = new_game(c)
    metrics = c.get(f"/api/games/{gid}/metrics").json()
    assert metrics["winner"] is None
    assert set(metrics["players"]) == {"red", "blue"}
    assert metrics["players"]["red"]["robber_blocked"] == 0


def test_layout_endpoint():
    c = client()
    gid = new_game(c)
    layout = c.get(f"/api/games/{gid}/layout").json()
    assert len(layout["hexes"]) == 19
    assert len(layout["vertices"]) == 54
    assert len(layout["edges"]) == 72
    assert len(layout["ports"]) == 9


def test_board_template_endpoint():
    c = client()
    tpl = c.get("/api/board_template").json()
    assert len(tpl["hexes"]) == 19
    assert len(tpl["vertices"]) == 54
    assert len(tpl["edges"]) == 72
    assert sum(tpl["terrain_counts"].values()) == 19
    assert sum(tpl["number_counts"].values()) == 18
    assert sum(tpl["port_counts"].values()) == 9
    assert len(tpl["default_ports"]) == 9
    assert len(tpl["perimeter_edges"]) > 9
    # Each hex carries the geometry the designer needs to draw it.
    assert all({"coord", "center", "vertices"} <= h.keys() for h in tpl["hexes"])
    # Default ports sit on perimeter edges and follow the base distribution.
    perim_ids = {s["edge"] for s in tpl["perimeter_edges"]}
    assert all(p["edge"] in perim_ids for p in tpl["default_ports"])


def test_create_custom_board_game():
    c = client()
    tpl = c.get("/api/board_template").json()
    # Build a legal layout straight from the template's required counts.
    terrains: list[str] = []
    for terrain, n in tpl["terrain_counts"].items():
        terrains.extend([terrain] * n)
    numbers: list[int] = []
    for num, n in tpl["number_counts"].items():
        numbers.extend([int(num)] * n)
    assert len(terrains) == 19 and len(numbers) == 18

    resp = c.post(
        "/api/games",
        json={
            "players": ["red", "blue"],
            "board": "custom",
            "layout": {"terrain": terrains, "numbers": numbers},
        },
    )
    assert resp.status_code == 200
    gid = resp.json()["game_id"]
    layout = c.get(f"/api/games/{gid}/layout").json()
    assert len(layout["hexes"]) == 19


def test_create_custom_board_with_explicit_ports():
    c = client()
    tpl = c.get("/api/board_template").json()
    terrains: list[str] = []
    for terrain, n in tpl["terrain_counts"].items():
        terrains.extend([terrain] * n)
    numbers: list[int] = []
    for num, n in tpl["number_counts"].items():
        numbers.extend([int(num)] * n)

    resp = c.post(
        "/api/games",
        json={
            "players": ["red", "blue"],
            "board": "custom",
            "layout": {
                "terrain": terrains,
                "numbers": numbers,
                "ports": tpl["default_ports"],
            },
        },
    )
    assert resp.status_code == 200
    gid = resp.json()["game_id"]
    layout = c.get(f"/api/games/{gid}/layout").json()
    assert len(layout["ports"]) == 9
    placed_edges = {tuple(sorted(s["vertices"])) for s in tpl["perimeter_edges"]
                    if s["edge"] in {p["edge"] for p in tpl["default_ports"]}}
    got_edges = {tuple(p["vertices"]) for p in layout["ports"]}
    assert got_edges == placed_edges


def test_create_custom_board_rejects_duplicate_port_edge():
    c = client()
    tpl = c.get("/api/board_template").json()
    terrains: list[str] = []
    for terrain, n in tpl["terrain_counts"].items():
        terrains.extend([terrain] * n)
    numbers: list[int] = []
    for num, n in tpl["number_counts"].items():
        numbers.extend([int(num)] * n)
    one_edge = tpl["perimeter_edges"][0]["edge"]
    bad_ports = [{"type": p["type"], "edge": one_edge} for p in tpl["default_ports"]]
    resp = c.post(
        "/api/games",
        json={
            "players": ["red", "blue"],
            "board": "custom",
            "layout": {"terrain": terrains, "numbers": numbers, "ports": bad_ports},
        },
    )
    assert resp.status_code == 400


def test_create_custom_board_rejects_bad_counts():
    c = client()
    resp = c.post(
        "/api/games",
        json={
            "players": ["red", "blue"],
            "board": "custom",
            "layout": {"terrain": ["desert"] * 19, "numbers": [6] * 18},
        },
    )
    assert resp.status_code == 400


def test_command_text_endpoint():
    c = client()
    gid = new_game(c)
    ok = c.post(f"/api/games/{gid}/command_text", json={"line": "settlement 0"})
    assert ok.status_code == 200
    assert ok.json()["events"] == ["SetupSettlementPlaced"]
    bad = c.post(f"/api/games/{gid}/command_text", json={"line": "frobnicate 9"})
    assert bad.status_code == 400


def test_mode_defaults_strict_and_is_reported():
    c = client()
    gid = new_game(c)
    assert c.get(f"/api/games/{gid}/state").json()["mode"] == "strict"
    assert all(g["mode"] == "strict" for g in c.get("/api/games").json())


def test_create_dev_game_and_toggle_mode():
    c = client()
    resp = c.post("/api/games", json={"players": ["red", "blue"], "mode": "dev"})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "dev"
    gid = resp.json()["game_id"]

    # Dev mode: build a settlement during setup for any player (no gating).
    ok = c.post(f"/api/games/{gid}/commands",
                json={"type": "BuildSettlement", "player": "blue", "vertex": 0})
    assert ok.status_code == 200
    assert ok.json()["state"]["mode"] == "dev"

    # Toggle to strict; an off-phase build is now rejected.
    assert c.post(f"/api/games/{gid}/mode", json={"mode": "strict"}).status_code == 200
    assert c.get(f"/api/games/{gid}/state").json()["mode"] == "strict"
    bad = c.post(f"/api/games/{gid}/commands",
                 json={"type": "BuildSettlement", "player": "red", "vertex": 5})
    assert bad.status_code == 422


def test_dev_admin_set_resources_and_vp():
    c = client()
    gid = c.post("/api/games", json={"players": ["red", "blue"], "mode": "dev"}).json()["game_id"]
    ok = c.post(f"/api/games/{gid}/commands",
                json={"type": "SetResources", "player": "red", "resources": {"ore": 4}})
    assert ok.status_code == 200
    assert ok.json()["state"]["players"]["red"]["resources"]["ore"] == 4
    vp = c.post(f"/api/games/{gid}/commands",
                json={"type": "SetVictoryPoints", "player": "red", "bonus": 3})
    assert vp.status_code == 200


def test_admin_command_rejected_in_strict_mode():
    c = client()
    gid = new_game(c)  # strict by default
    bad = c.post(f"/api/games/{gid}/commands",
                 json={"type": "SetResources", "player": "red", "resources": {"ore": 4}})
    assert bad.status_code == 422


def test_set_mode_rejects_unknown_mode():
    c = client()
    gid = new_game(c)
    assert c.post(f"/api/games/{gid}/mode", json={"mode": "wat"}).status_code == 400


def test_websocket_receives_initial_state_and_broadcasts():
    c = client()
    gid = new_game(c)
    with c.websocket_connect(f"/api/games/{gid}/ws") as ws:
        first = ws.receive_json()
        assert first["type"] == "state"
        assert first["state"]["phase"] == "setup"

        # A command over HTTP should broadcast a new state to the socket.
        c.post(f"/api/games/{gid}/commands",
               json={"type": "PlaceSetupSettlement", "player": "red", "vertex": 0})
        update = ws.receive_json()
        assert update["type"] == "state"
        assert update["state"]["players"]["red"]["settlements"] == [0]
