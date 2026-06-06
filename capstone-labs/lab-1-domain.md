# Lab 1 — Domain Modeling

> **Goal:** Define the data structures that represent the game world. No game logic yet — just types and the geometry that derives the board graph.
>
> **Branch:** `git checkout -b lab-1-domain-models`

---

## Background

Domain modeling means translating real-world concepts into code structures. Before writing game logic you must answer: "How does my program represent a Catan board? A player? A turn?"

Good domain models are:
- **Immutable where possible** — data that can't change is easier to reason about.
- **Self-documenting** — a named enum member is clearer than a magic string or integer.
- **Complete** — every concept in the game has a corresponding type.

This lab is mostly *declaring* types. The one place you write a real algorithm is `build_topology`, which turns a set of hex coordinates into a graph of vertices and edges. That algorithm is the hardest part of the lab — budget time for it.

---

## Specification

You will create six modules under `catan/domain/`. The names below are a **hard contract**: the persistence codec (Lab 3), the API DTOs (Lab 5), and the frontend types (Lab 6) all depend on these exact identifiers and string values. Match them precisely.

### `catan/domain/constants.py`

Define these enumerations. Each must subclass `(str, Enum)` so that members carry string values (the codec relies on this). The string values must be exactly as shown.

| Enum | Members → values |
|------|------------------|
| `Resource` | `BRICK="brick"`, `LUMBER="lumber"`, `WOOL="wool"`, `GRAIN="grain"`, `ORE="ore"` |
| `Terrain` | `HILLS="hills"`, `FOREST="forest"`, `PASTURE="pasture"`, `FIELDS="fields"`, `MOUNTAINS="mountains"`, `DESERT="desert"` |
| `DevCard` | `KNIGHT="knight"`, `VICTORY_POINT="victory_point"`, `ROAD_BUILDING="road_building"`, `YEAR_OF_PLENTY="year_of_plenty"`, `MONOPOLY="monopoly"` |
| `PortType` | `GENERIC="generic"`, `BRICK="brick"`, `LUMBER="lumber"`, `WOOL="wool"`, `GRAIN="grain"`, `ORE="ore"` |

> **Why `LUMBER`/`WOOL`/`GRAIN` and not `WOOD`/`SHEEP`/`WHEAT`?** These are the official Catan card names. Using them avoids confusion in analytics and CLI output. **The grading rubric penalizes the wrong names.**

You must also define the following module-level constants. The *values* come from the rules — read [Appendix A: Catan Rules](appendix-rules.md) and fill them in yourself. Do not look them up in the guided capstone.

| Constant | Type | What it holds |
|----------|------|---------------|
| `TERRAIN_RESOURCE` | `dict[Terrain, Resource \| None]` | Which resource each terrain produces (desert → `None`) |
| `TERRAIN_COUNTS` | `dict[Terrain, int]` | How many of each terrain tile (19 total) |
| `NUMBER_TOKEN_COUNTS` | `dict[int, int]` | How many of each number token (no 7; 18 total) |
| `PIPS` | `dict[int, int]` | Dice-combination count for each total 2–12 (7 → 0) |
| `DEV_CARD_COUNTS` | `dict[DevCard, int]` | Deck composition (25 total) |
| `PORT_TRADE_RATIO` | `dict[PortType, int]` | Generic → 3, specific → 2 |
| `PORT_COUNTS` | `dict[PortType, int]` | 4 generic + 1 of each resource (9 total) |
| `ROAD_COST`, `SETTLEMENT_COST`, `CITY_COST`, `DEV_CARD_COST` | `dict[Resource, int]` | Build costs — **separate constants, not a nested dict** |

Plus these scalar constants (derive from the rules): `BANK_RESOURCE_COUNT`, `SETTLEMENTS_PER_PLAYER`, `CITIES_PER_PLAYER`, `ROADS_PER_PLAYER`, `VICTORY_POINTS_TO_WIN`, `LONGEST_ROAD_MIN`, `LARGEST_ARMY_MIN`, `ROBBER_DISCARD_THRESHOLD`, `DEFAULT_BANK_TRADE_RATIO`, and the topology sanity constants `HEX_COUNT`, `VERTEX_COUNT`, `EDGE_COUNT`.

### `catan/domain/geometry.py`

Define these type aliases (they are aliases, **not** classes):

```python
Coord     = tuple[int, int]       # axial hex coordinate (q, r)
VertexKey = frozenset[Coord]      # the ≤3 hexes meeting at a vertex
EdgeKey   = frozenset[VertexKey]  # the 2 vertices an edge connects
```

Implement these, matching the signatures exactly:

```python
def hex_distance(a: Coord, b: Coord) -> int: ...

def standard_hexes() -> list[Coord]:
    """Return the 19 axial coordinates of a standard board (all hexes within
    distance BOARD_RADIUS=2 of the center), sorted for reproducibility."""

def build_topology(hexes: list[Coord] | None = None) -> BoardTopology:
    """Given a set of hex positions, compute the full board graph: every unique
    vertex, every unique edge, and all adjacency maps. Vertices are corners shared
    by up to 3 hexes; edges are sides shared by up to 2 hexes. Uses standard_hexes()
    when no argument is given."""
```

`BoardTopology` must be a `frozen=True` dataclass carrying **all** of these fields (downstream code indexes into each one by name):

| Field | Type | Meaning |
|-------|------|---------|
| `hexes` | `list[Coord]` | the input hexes |
| `vertices` | `dict[int, VertexKey]` | vertex id → the hexes meeting there |
| `edges` | `list[tuple[int, int]]` | each edge as a `(vertex_id, vertex_id)` pair |
| `vertex_id` | `dict[VertexKey, int]` | reverse map of `vertices` |
| `vertex_neighbors` | `dict[int, frozenset[int]]` | which vertex ids touch this one |
| `vertex_edges` | `dict[int, frozenset[int]]` | which edge indices touch this vertex |
| `vertex_hexes` | `dict[int, frozenset[Coord]]` | which hexes touch this vertex |
| `hex_vertices` | `dict[Coord, frozenset[int]]` | which vertex ids belong to this hex |
| `edge_vertices` | `dict[int, tuple[int, int]]` | edge index → its two vertex ids |

It must also expose `is_adjacent(self, v1: int, v2: int) -> bool`.

### `catan/domain/board.py`

A `Port` dataclass: a `type: PortType` and `vertices: tuple[int, int]` (the two vertex ids with access).

A `frozen=True` `Board` dataclass with fields: `topology: BoardTopology`, `terrain: dict[Coord, Terrain]`, `numbers: dict[Coord, int]`, `ports: list[Port]`, `robber: Coord`, `pips: dict[Coord, int]`.

You must also provide three board generators:

```python
def standard_board() -> Board:          # official fixed terrain + spiral number placement
def random_board(rng=...) -> Board:      # shuffled; reject boards with adjacent 6/8 tokens
def custom_board(terrains, numbers, ports, ...) -> Board:  # built from a physical board
```

### `catan/domain/state.py`

Define the `Phase` enum **here** (not in constants.py): `SETUP="setup"`, `PLAY="play"`, `FINISHED="finished"`.

`PlayerState` dataclass carrying: `pid: str`, `resources: dict[Resource, int]`, `dev_cards: dict[DevCard, int]`, `dev_cards_played: dict[DevCard, int]`, `knights_played: int`, `settlements: set[int]`, `cities: set[int]`, `roads: set[int]`, `bonus_vp: int`. It must expose `hand_size` (sum of resources), `settlements_left`, and a `clone()` returning a deep copy.

`GameState` dataclass carrying the full game: `board`, `player_order: list[str]`, `players: dict[str, PlayerState]`, `phase`, `current_index: int`, `turn_number: int`, `dice: tuple[int,int] | None`, `has_rolled: bool`, `bank: dict[Resource, int]`, `dev_deck: dict[DevCard, int]`, `robber: Coord`, `longest_road_holder: str | None`, `largest_army_holder: str | None`, `winner: str | None`, `pending_discards: dict[str, int]`, `robber_pending: bool`, `dev_played_this_turn: bool`, `dev_bought_this_turn: dict[DevCard, int]`. It must expose a `current_player` property and a `clone()` deep copy.

> **Why `bonus_vp` and `dev_bought_this_turn`?** `bonus_vp` is a dev-mode override for testing arbitrary VP totals. `dev_bought_this_turn` tracks cards bought this turn so the engine can forbid playing a just-bought card.

### `catan/domain/commands.py` and `catan/domain/events.py`

Commands represent **intent** (can be rejected). Events represent **facts** (cannot be rejected). Every command and event is a `frozen=True` dataclass.

You must define exactly these command types and expose a `Command` union of all of them:

`CreateGame`, `PlaceSetupSettlement`, `PlaceSetupRoad`, `RollDice`, `EndTurn`, `Discard`, `MoveRobber`, `BuildRoad`, `BuildSettlement`, `BuildCity`, `BuyDevCard`, `PlayKnight`, `PlayRoadBuilding`, `PlayYearOfPlenty`, `PlayMonopoly`, `TradeWithBank`, `TradeWithPlayer`, `SetResources`, `SetVictoryPoints`.

And exactly these event types, with an `Event` union:

`GameCreated`, `SetupSettlementPlaced`, `SetupRoadPlaced`, `DiceRolled`, `TurnEnded`, `DiscardRequired`, `Discarded`, `RobberMoved`, `Stolen`, `RoadBuilt`, `SettlementBuilt`, `CityBuilt`, `DevCardBought`, `KnightPlayed`, `RoadBuildingPlayed`, `YearOfPlentyPlayed`, `MonopolyPlayed`, `VictoryPointRevealed`, `MaritimeTrade`, `PlayerTrade`, `ResourcesSet`, `VictoryPointsSet`.

You must design the fields of each command/event yourself from the rules. Some design requirements that downstream labs depend on:

- `RollDice` and `DiceRolled` carry `pid`, `d1`, `d2`. `DiceRolled` exposes a `total` property.
- `BuyDevCard` and `DevCardBought` carry the actual `card: DevCard` that was drawn (this is a companion app — the recorder observes which card came up).
- `MoveRobber`/`KnightPlayed` carry the target `coord`, an optional `victim: str | None`, and the observed stolen `resource: Resource | None`.
- `Stolen` carries `thief`, `victim`, and `resource: Resource | None` (None = victim had an empty hand or the card was unobserved).
- Trade commands/events distinguish maritime (bank) trades from domestic (player) trades.
- `SetResources`/`SetVictoryPoints` and their events exist only for dev mode.

> **Why separate commands and events?** A command carries intent and can be rejected ("Alice *wants* to build"). An event is a recorded fact ("a settlement *was* built"). If you used one type for both, you would lose the ability to store only facts in the log and replay them deterministically.

---

## Your Tasks

1. Implement `constants.py`: all enums (exact values) and all constants (values derived from the rules appendix).
2. Implement `geometry.py`: type aliases, `hex_distance`, `standard_hexes`, the `BoardTopology` dataclass, and `build_topology`.
3. Implement `board.py`: `Port`, `Board`, and the three board generators.
4. Implement `state.py`: `Phase`, `PlayerState` (with `hand_size`, `settlements_left`, `clone`), `GameState` (with `current_player`, `clone`).
5. Implement `commands.py` and `events.py`: every type listed, all `frozen=True`, plus the union aliases.

---

## Hints & Pitfalls

- **The vertex-identity insight (the crux of `build_topology`):** a vertex is uniquely identified by *the set of hexes that share it*. If you compute a corner from hex A, hex B, or hex C, you get the *same* `frozenset({A, B, C})`. That means you never hard-code adjacency — you derive it. See [Appendix B: Hex Math](appendix-hex-math.md) for the coordinate system, the six neighbor directions, and how to express "corner k of hex h" as a frozenset of three coordinates.
- Assign vertex and edge integer IDs by **sorting** the unique keys first, so IDs are reproducible across runs (tests depend on this).
- An edge is the frozenset of its two endpoint vertex-keys, taken from consecutive corners of a hex.
- Build the adjacency maps (`vertex_neighbors`, `vertex_edges`, etc.) in a second pass once every vertex and edge has an ID.
- `random_board` must reject layouts with adjacent red (6/8) tokens — generate, check, regenerate.

---

## Tests First (write these before implementing)

- `standard_hexes()` returns exactly `HEX_COUNT` (19) coordinates.
- `build_topology(standard_hexes())` produces exactly `VERTEX_COUNT` (54) vertices and `EDGE_COUNT` (72) edges.
- Adjacency is symmetric: if `v1` is in `vertex_neighbors[v2]`, then `v2` is in `vertex_neighbors[v1]`.
- Every hex maps to exactly 6 vertices in `hex_vertices`.
- Handshake check: the sum of all vertex degrees equals `2 × len(edges)`.
- A `PlayerState` with two settlements and one city reports the correct VP count from your VP logic (you can stub a quick computation here; full VP logic lands in Lab 2).
- Every command and event dataclass raises when you try to mutate a field (proves `frozen=True`).

---

## Checkpoint

- [ ] All enums import cleanly and use `LUMBER`/`WOOL`/`GRAIN` (not `WOOD`/`SHEEP`/`WHEAT`)
- [ ] `Phase` lives in `state.py`, not `constants.py`
- [ ] Build costs are separate constants (`ROAD_COST`, `SETTLEMENT_COST`, `CITY_COST`, `DEV_CARD_COST`)
- [ ] `Coord` is a `tuple[int, int]` alias, not a class with methods
- [ ] `build_topology(standard_hexes())` returns 54 vertices and 72 edges
- [ ] All command and event dataclasses are `frozen=True`
- [ ] `from catan.domain.state import GameState` imports without error
- [ ] Commit: `"Lab 1: Complete domain models"`
