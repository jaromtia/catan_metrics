# Phase 8 — Testing Strategy

> **Goal:** Build a test suite that verifies correctness and catches regressions.
>
> **Branch:** `git checkout -b phase-8-tests`

---

## 8.1 The Testing Pyramid

```
        /\
       /E2E\         ← Few, slow, test full user flows
      /------\
     /Integr. \      ← Some, test multiple components together
    /----------\
   /   Unit     \    ← Many, fast, test one function at a time
  /--------------\
```

For this project:
- **Unit tests** — `validate()`, `reduce()`, `awards.py`, `projections.py` in isolation
- **Integration tests** — `GameService` with a real in-memory SQLite database
- **API tests** — FastAPI app with `httpx.TestClient`

The reference implementation has 10 test files:

| File | What it tests |
|------|---------------|
| `test_geometry.py` | `build_topology`, vertex/edge counts, adjacency symmetry |
| `test_board.py` | Board generators, terrain distribution, port placement |
| `test_validate.py` | Every validation rule, both the pass and fail case |
| `test_reduce.py` | Every event type, resource conservation, immutability |
| `test_awards.py` | Longest Road DFS, Largest Army, tie handling |
| `test_store.py` | Codec round-trips, snapshot/replay, time travel |
| `test_modes.py` | Strict vs dev mode behavior, admin commands |
| `test_projections.py` | Dice histogram, luck score, VP timeline |
| `test_cli.py` | Parser synonyms, REPL round-trip |
| `test_api.py` | All endpoints, error codes, WebSocket |

---

## 8.2 Test Fixtures

Create `tests/fixtures.py` with helpers that build valid test states:

```python
# tests/fixtures.py
from catan.domain.state import GameState, PlayerState, Phase
from catan.domain.constants import Resource, DevCard
from catan.domain.board import standard_board

def make_player(pid: str) -> PlayerState:
    return PlayerState(
        pid=pid,
        resources={r: 0 for r in Resource},
        dev_cards={c: 0 for c in DevCard},
        dev_cards_played={c: 0 for c in DevCard},
        knights_played=0,
        settlements=set(),
        cities=set(),
        roads=set(),
        bonus_vp=0,
    )

def make_game_state(
    players: list[str] | None = None,
    phase: Phase = Phase.SETUP,
    has_rolled: bool = False,
    current_index: int = 0,
) -> GameState:
    """Build a minimal valid GameState for testing."""
    if players is None:
        players = ["alice", "bob"]
    board = standard_board()
    return GameState(
        board=board,
        player_order=players,
        players={pid: make_player(pid) for pid in players},
        phase=phase,
        current_index=current_index,
        turn_number=1,
        dice=None,
        has_rolled=has_rolled,
        bank={r: 19 for r in Resource},
        dev_deck={c: n for c, n in DEV_CARD_COUNTS.items()},
        robber=_desert_coord(board),
        longest_road_holder=None,
        largest_army_holder=None,
        winner=None,
        pending_discards={},
        robber_pending=False,
        dev_played_this_turn=False,
        dev_bought_this_turn={},
    )

def _desert_coord(board) -> tuple[int, int]:
    from catan.domain.constants import Terrain
    return next(c for c, t in board.terrain.items() if t == Terrain.DESERT)
```

---

## 8.3 Unit Tests: Validation

```python
# tests/test_validate.py
import pytest
from catan.domain.commands import (
    BuildSettlement, RollDice, EndTurn, PlaceSetupSettlement, PlaceSetupRoad
)
from catan.domain.constants import Resource, Phase
from catan.engine.validate import validate
from tests.fixtures import make_game_state


def test_build_settlement_valid():
    state = make_game_state(phase=Phase.SETUP)
    cmd   = PlaceSetupSettlement(pid="alice", vertex_id=0)
    result = validate(state, cmd, strict=True)
    assert result.ok


def test_build_settlement_violates_distance_rule():
    state = make_game_state(phase=Phase.SETUP)
    state.players["alice"].settlements.add(0)
    # Find a vertex adjacent to 0.
    neighbor = next(iter(state.board.topology.vertex_neighbors[0]))
    cmd = PlaceSetupSettlement(pid="bob", vertex_id=neighbor)
    result = validate(state, cmd, strict=True)
    assert not result.ok
    assert any("distance" in e.lower() for e in result.errors)


def test_cannot_roll_twice():
    state = make_game_state(phase=Phase.PLAY, has_rolled=True)
    # Complete setup first (or set has_rolled=True directly for this test).
    cmd = RollDice(pid="alice", d1=3, d2=4)
    result = validate(state, cmd, strict=True)
    assert not result.ok


def test_roll_out_of_turn_rejected_in_strict():
    state = make_game_state(phase=Phase.PLAY, current_index=0)  # alice's turn
    cmd = RollDice(pid="bob", d1=3, d2=4)
    result = validate(state, cmd, strict=True)
    assert not result.ok


def test_roll_out_of_turn_allowed_in_dev():
    state = make_game_state(phase=Phase.PLAY, current_index=0)
    cmd = RollDice(pid="bob", d1=3, d2=4)
    result = validate(state, cmd, strict=False)
    assert result.ok


def test_dev_admin_commands_rejected_in_strict():
    from catan.domain.commands import SetResources
    state = make_game_state()
    cmd = SetResources(pid="alice", resources={Resource.LUMBER: 5})
    result = validate(state, cmd, strict=True)
    assert not result.ok


def test_dice_values_must_be_1_to_6():
    state = make_game_state(phase=Phase.PLAY)
    for bad_die in [0, 7, -1, 9]:
        cmd = RollDice(pid="alice", d1=bad_die, d2=3)
        result = validate(state, cmd, strict=False)
        assert not result.ok, f"d1={bad_die} should be rejected"
```

---

## 8.4 Unit Tests: Reducer Invariants

```python
# tests/test_reduce.py
from catan.domain.constants import Resource, BANK_RESOURCE_COUNT
from catan.engine.reduce import reduce
from catan.domain.events import SettlementBuilt


def resource_total(state) -> dict[Resource, int]:
    """Sum resources across all players + bank."""
    total = dict(state.bank)
    for p in state.players.values():
        for r, n in p.resources.items():
            total[r] = total.get(r, 0) + n
    return total


def assert_conserved(state):
    for r in Resource:
        total = resource_total(state).get(r, 0)
        assert total == BANK_RESOURCE_COUNT, \
            f"Conservation violated for {r.value}: {total} != {BANK_RESOURCE_COUNT}"


def test_reduce_does_not_mutate_input():
    from tests.fixtures import make_game_state
    state    = make_game_state(phase=Phase.SETUP)
    original = id(state)
    new_state = reduce(state, SettlementBuilt(pid="alice", vertex_id=5))
    assert id(new_state) != original                           # new object
    assert 5 not in state.players["alice"].settlements         # original unchanged
    assert 5 in new_state.players["alice"].settlements         # new state updated


def test_resource_conservation_across_roll():
    # Build a state where alice has a settlement, then roll.
    # See tests/test_reduce.py in the reference implementation for full setup.
    ...
```

---

## 8.5 API Tests

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from catan.api.app import create_app
from catan.store.repository import GameService
from catan.store.event_store import EventStore


@pytest.fixture
def client():
    svc = GameService(EventStore())   # in-memory SQLite
    return TestClient(create_app(svc))


def new_game(client, players=("alice", "bob"), mode="dev") -> str:
    r = client.post("/api/games", json={
        "players": list(players), "board": "standard", "mode": mode
    })
    assert r.status_code == 201
    return r.json()["game_id"]


def test_create_and_fetch_game(client):
    game_id = new_game(client)
    r = client.get(f"/api/games/{game_id}/state")
    assert r.status_code == 200
    state = r.json()
    assert state["phase"] == "setup"
    assert set(state["player_order"]) == {"alice", "bob"}


def test_invalid_command_returns_422(client):
    game_id = new_game(client, mode="strict")
    # In strict mode, bob can't build before alice finishes setup.
    r = client.post(f"/api/games/{game_id}/commands", json={
        "type": "PlaceSetupSettlement", "pid": "bob", "vertex_id": 0
    })
    assert r.status_code == 422


def test_unknown_game_returns_404(client):
    r = client.get("/api/games/doesnotexist/state")
    assert r.status_code == 404


def test_layout_has_correct_topology(client):
    game_id = new_game(client)
    r = client.get(f"/api/games/{game_id}/layout")
    assert r.status_code == 200
    layout = r.json()
    assert len(layout["hexes"])    == 19
    assert len(layout["vertices"]) == 54
    assert len(layout["edges"])    == 72
    assert len(layout["ports"])    == 9


def test_dev_mode_allows_out_of_turn(client):
    game_id = new_game(client, mode="dev")
    # In dev mode, bob can act out of turn.
    r = client.post(f"/api/games/{game_id}/commands", json={
        "type": "BuildSettlement", "pid": "bob", "vertex_id": 0
    })
    assert r.status_code == 200


def test_mode_switch(client):
    game_id = new_game(client, mode="dev")
    # Switch to strict.
    r = client.post(f"/api/games/{game_id}/mode", json={"mode": "strict"})
    assert r.status_code == 200
    assert r.json()["mode"] == "strict"
    # Now out-of-turn action should fail.
    r2 = client.post(f"/api/games/{game_id}/commands", json={
        "type": "BuildSettlement", "pid": "bob", "vertex_id": 5
    })
    assert r2.status_code == 422
```

---

## 8.6 Geometry Tests

```python
# tests/test_geometry.py
from catan.domain.geometry import build_topology, standard_hexes
from catan.domain.constants import HEX_COUNT, VERTEX_COUNT, EDGE_COUNT


def test_standard_hex_count():
    assert len(standard_hexes()) == HEX_COUNT   # 19


def topology():
    return build_topology(standard_hexes())


def test_vertex_count():
    assert len(topology().vertices) == VERTEX_COUNT   # 54


def test_edge_count():
    assert len(topology().edges) == EDGE_COUNT   # 72


def test_adjacency_is_symmetric():
    topo = topology()
    for v, neighbors in topo.vertex_neighbors.items():
        for n in neighbors:
            assert v in topo.vertex_neighbors[n], f"{v} adjacent to {n} but not vice versa"


def test_every_hex_has_six_vertices():
    topo = topology()
    for coord, vids in topo.hex_vertices.items():
        assert len(vids) == 6, f"Hex {coord} has {len(vids)} vertices"
```

---

## 8.7 Running Tests

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=catan --cov-report=term-missing

# A specific file
uv run pytest tests/test_validate.py -v
```

Coverage target: ≥80% on `catan/engine/` and `catan/store/`.

---

## Phase 8 Checkpoint

- [ ] `uv run pytest` passes with 0 failures
- [ ] Coverage ≥ 80% across `catan/engine/` and `catan/store/`
- [ ] Every validation rule has both a passing and a failing test
- [ ] Resource conservation invariant covered for: roll, build, bank trade, discard
- [ ] API tests cover: create, fetch, valid command, invalid command, 404, 422
- [ ] `test_geometry.py` verifies vertex/edge counts and adjacency symmetry
- [ ] `test_modes.py` verifies strict/dev mode behavior and admin commands
- [ ] Commit: `"Phase 8: Comprehensive test suite with 80%+ coverage"`
