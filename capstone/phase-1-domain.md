# Phase 1 — Domain Modeling

> **Goal:** Define the data structures that represent the game world. No logic yet — just types.
>
> **Branch:** `git checkout -b phase-1-domain-models`

---

## 1.1 What Is Domain Modeling?

Domain modeling means translating real-world concepts into code structures. Before writing game logic you need to answer: "How does my program represent a Catan board? A player? A turn?"

Good domain models are:
- **Immutable where possible** — data that can't change is easier to reason about
- **Self-documenting** — `Resource.LUMBER` is clearer than `"lumber"` or `2`
- **Complete** — every concept in the game has a corresponding type

---

## 1.2 Constants

**`catan/domain/constants.py`**

```python
from __future__ import annotations
from enum import Enum


class Resource(str, Enum):
    BRICK  = "brick"
    LUMBER = "lumber"   # not "wood" — lumber is the official card name
    WOOL   = "wool"     # not "sheep"
    GRAIN  = "grain"    # not "wheat"
    ORE    = "ore"


class Terrain(str, Enum):
    HILLS     = "hills"      # produces BRICK
    FOREST    = "forest"     # produces LUMBER
    PASTURE   = "pasture"    # produces WOOL
    FIELDS    = "fields"     # produces GRAIN
    MOUNTAINS = "mountains"  # produces ORE
    DESERT    = "desert"     # produces nothing
    # Note: no SEA terrain — sea tiles are not tracked in this implementation


TERRAIN_RESOURCE: dict[Terrain, Resource | None] = {
    Terrain.HILLS:     Resource.BRICK,
    Terrain.FOREST:    Resource.LUMBER,
    Terrain.PASTURE:   Resource.WOOL,
    Terrain.FIELDS:    Resource.GRAIN,
    Terrain.MOUNTAINS: Resource.ORE,
    Terrain.DESERT:    None,
}

# 19 hexes in the base game.
TERRAIN_COUNTS: dict[Terrain, int] = {
    Terrain.FOREST:    4,
    Terrain.FIELDS:    4,
    Terrain.PASTURE:   4,
    Terrain.HILLS:     3,
    Terrain.MOUNTAINS: 3,
    Terrain.DESERT:    1,
}

# 18 number tokens (desert gets none, no 7 token).
NUMBER_TOKEN_COUNTS: dict[int, int] = {
    2: 1, 3: 2, 4: 2, 5: 2, 6: 2,
    8: 2, 9: 2, 10: 2, 11: 2, 12: 1,
}

# Pip count = number of dice combinations that produce this number.
PIPS: dict[int, int] = {
    2: 1, 3: 2, 4: 3, 5: 4, 6: 5,
    7: 0,
    8: 5, 9: 4, 10: 3, 11: 2, 12: 1,
}


class DevCard(str, Enum):
    KNIGHT         = "knight"
    VICTORY_POINT  = "victory_point"
    ROAD_BUILDING  = "road_building"
    YEAR_OF_PLENTY = "year_of_plenty"
    MONOPOLY       = "monopoly"


DEV_CARD_COUNTS: dict[DevCard, int] = {
    DevCard.KNIGHT:         14,
    DevCard.VICTORY_POINT:  5,
    DevCard.ROAD_BUILDING:  2,
    DevCard.YEAR_OF_PLENTY: 2,
    DevCard.MONOPOLY:       2,
}  # total: 25


class PortType(str, Enum):
    GENERIC = "generic"  # 3:1 any resource
    BRICK   = "brick"    # 2:1 brick
    LUMBER  = "lumber"   # 2:1 lumber
    WOOL    = "wool"     # 2:1 wool
    GRAIN   = "grain"    # 2:1 grain
    ORE     = "ore"      # 2:1 ore


PORT_TRADE_RATIO: dict[PortType, int] = {
    PortType.GENERIC: 3,
    PortType.BRICK: 2, PortType.LUMBER: 2,
    PortType.WOOL: 2,  PortType.GRAIN: 2, PortType.ORE: 2,
}

# 9 ports total: 4 generic + 1 per resource.
PORT_COUNTS: dict[PortType, int] = {
    PortType.GENERIC: 4,
    PortType.BRICK: 1, PortType.LUMBER: 1,
    PortType.WOOL: 1,  PortType.GRAIN: 1, PortType.ORE: 1,
}

# Build costs — separate constants (NOT a nested dict).
ROAD_COST:     dict[Resource, int] = {Resource.BRICK: 1, Resource.LUMBER: 1}
SETTLEMENT_COST: dict[Resource, int] = {
    Resource.BRICK: 1, Resource.LUMBER: 1,
    Resource.WOOL: 1,  Resource.GRAIN: 1,
}
CITY_COST:     dict[Resource, int] = {Resource.ORE: 3, Resource.GRAIN: 2}
DEV_CARD_COST: dict[Resource, int] = {Resource.ORE: 1, Resource.WOOL: 1, Resource.GRAIN: 1}

BANK_RESOURCE_COUNT = 19   # 19 cards of each resource in the bank
SETTLEMENTS_PER_PLAYER = 5
CITIES_PER_PLAYER = 4
ROADS_PER_PLAYER = 15
VICTORY_POINTS_TO_WIN = 10
LONGEST_ROAD_MIN = 5
LARGEST_ARMY_MIN = 3
ROBBER_DISCARD_THRESHOLD = 7  # players with > 7 cards discard on a 7
DEFAULT_BANK_TRADE_RATIO = 4  # 4:1 with no port

# Topology sanity constants.
HEX_COUNT    = 19
VERTEX_COUNT = 54
EDGE_COUNT   = 72
```

> **Why `Resource.LUMBER` and not `Resource.WOOD`?**
> The official Catan card names are Lumber, Wool, and Grain. Using the official names avoids confusion in the analytics and CLI output.

---

## 1.3 Hex Grid Geometry

**`catan/domain/geometry.py`**

The Catan board is a hexagonal grid of hexagons. We use **axial coordinates** — a 2-axis system that cleanly tiles the plane.

```python
from __future__ import annotations
from dataclasses import dataclass, field

# Type aliases — these are just type hints, not classes.
Coord     = tuple[int, int]      # axial hex coordinate (q, r)
VertexKey = frozenset[Coord]     # the ≤3 hexes meeting at a vertex
EdgeKey   = frozenset[VertexKey] # the 2 vertices an edge connects
```

### Vertex Identity Trick

The key insight: **a vertex is uniquely identified by the set of hexes that share it.**

```
 hex A | hex B
  corner shared by A, B, and C
 hex C |
```

The same corner computed from hex A, B, or C will produce the same `frozenset({A, B, C})`. This means we never have to hard-code adjacency — we derive it from the board geometry.

```python
DIRECTIONS: tuple[Coord, ...] = (
    (+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1),
)

def _corner(h: Coord, k: int) -> VertexKey:
    """Vertex at corner k of hex h (between directions k and k+1)."""
    return frozenset((h,
                      (h[0]+DIRECTIONS[k][0], h[1]+DIRECTIONS[k][1]),
                      (h[0]+DIRECTIONS[(k+1)%6][0], h[1]+DIRECTIONS[(k+1)%6][1])))
```

### BoardTopology

```python
@dataclass(frozen=True)
class BoardTopology:
    """Immutable board graph: hexes, vertices, edges, and all adjacency maps."""
    hexes:            list[Coord]
    vertices:         dict[int, VertexKey]          # id → vertex key
    edges:            list[tuple[int, int]]          # (vertex id, vertex id)
    vertex_id:        dict[VertexKey, int]           # reverse map: key → id
    vertex_neighbors: dict[int, frozenset[int]]      # which vertex ids touch this one
    vertex_edges:     dict[int, frozenset[int]]      # which edge indices touch this vertex
    vertex_hexes:     dict[int, frozenset[Coord]]    # which hexes touch this vertex
    hex_vertices:     dict[Coord, frozenset[int]]    # which vertex ids belong to this hex
    edge_vertices:    dict[int, tuple[int, int]]     # edge index → (vid1, vid2)

    def is_adjacent(self, v1: int, v2: int) -> bool:
        return v2 in self.vertex_neighbors[v1]
```

### Building the Topology

```python
def build_topology(hexes: list[Coord] | None = None) -> BoardTopology:
    hex_list = hexes if hexes is not None else standard_hexes()
    hex_set  = set(hex_list)

    # 1. Collect all distinct corners.
    corner_keys: set[VertexKey] = set()
    for h in hex_list:
        for k in range(6):
            corner_keys.add(_corner(h, k))

    # 2. Assign stable integer ids (sorted for reproducibility).
    ordered = sorted(corner_keys, key=lambda vk: tuple(sorted(vk)))
    vertices  = {i: vk for i, vk in enumerate(ordered)}
    vertex_id = {vk: i for i, vk in vertices.items()}

    # 3. Collect all distinct edges (consecutive corners of each hex).
    edge_keys: set[EdgeKey] = set()
    for h in hex_list:
        for k in range(6):
            edge_keys.add(frozenset((_corner(h, k), _corner(h, (k+1)%6))))

    edges: list[tuple[int, int]] = []
    edge_vertices: dict[int, tuple[int, int]] = {}
    for ek in edge_keys:
        a, b = sorted(vertex_id[vk] for vk in ek)
        edges.append((a, b))
    edges.sort()
    for eid, (a, b) in enumerate(edges):
        edge_vertices[eid] = (a, b)

    # 4. Build adjacency maps.
    # (see reference implementation for the full loop)
    ...
```

> **Checkpoint:** A standard 19-hex board produces exactly 54 vertices and 72 edges.
> Write a test that calls `build_topology(standard_hexes())` and asserts these counts.

### Standard Hex Set

```python
BOARD_RADIUS = 2

def hex_distance(a: Coord, b: Coord) -> int:
    aq, ar = a
    bq, br = b
    return (abs(aq-bq) + abs(aq+ar-bq-br) + abs(ar-br)) // 2

def standard_hexes() -> list[Coord]:
    center: Coord = (0, 0)
    return sorted(
        (q, r)
        for q in range(-BOARD_RADIUS, BOARD_RADIUS+1)
        for r in range(-BOARD_RADIUS, BOARD_RADIUS+1)
        if hex_distance((q, r), center) <= BOARD_RADIUS
    )
```

See [Appendix: Hex Math](appendix-hex-math.md) for the full coordinate system reference.

---

## 1.4 Board

**`catan/domain/board.py`**

```python
from dataclasses import dataclass
from .geometry import Coord, BoardTopology
from .constants import Terrain, PortType

@dataclass
class Port:
    type: PortType
    vertices: tuple[int, int]  # two vertex ids with port access

@dataclass(frozen=True)
class Board:
    topology: BoardTopology
    terrain:  dict[Coord, Terrain]
    numbers:  dict[Coord, int]         # hex → number token (2-12, no 7)
    ports:    list[Port]
    robber:   Coord                     # current robber position (starts on desert)
    pips:     dict[Coord, int]          # hex → pip count (from PIPS table)
```

You will implement three board generators:
- `standard_board()` — official spiral token placement
- `random_board(rng)` — shuffled, rejects boards with adjacent 6/8 tokens
- `custom_board(terrains, numbers, ...)` — manually entered from a physical board

---

## 1.5 Player and Game State

**`catan/domain/state.py`**

```python
from dataclasses import dataclass, field
from enum import Enum
from .board import Board
from .constants import Resource, DevCard

# Phase lives here (not in constants.py).
class Phase(Enum):
    SETUP    = "setup"
    PLAY     = "play"
    FINISHED = "finished"


@dataclass
class PlayerState:
    pid:              str
    resources:        dict[Resource, int]   # counts per resource
    dev_cards:        dict[DevCard, int]    # unplayed cards in hand
    dev_cards_played: dict[DevCard, int]    # played cards
    knights_played:   int
    settlements:      set[int]              # vertex ids
    cities:           set[int]              # vertex ids
    roads:            set[int]              # edge indices
    bonus_vp:         int                   # dev-mode VP override

    @property
    def hand_size(self) -> int:
        return sum(self.resources.values())

    @property
    def settlements_left(self) -> int:
        from .constants import SETTLEMENTS_PER_PLAYER
        return SETTLEMENTS_PER_PLAYER - len(self.settlements)

    def clone(self) -> "PlayerState":
        import copy
        return copy.deepcopy(self)


@dataclass
class GameState:
    board:               Board
    player_order:        list[str]
    players:             dict[str, PlayerState]
    phase:               Phase
    current_index:       int
    turn_number:         int
    dice:                tuple[int, int] | None
    has_rolled:          bool
    bank:                dict[Resource, int]
    dev_deck:            dict[DevCard, int]    # remaining cards in deck
    robber:              Coord
    longest_road_holder: str | None
    largest_army_holder: str | None
    winner:              str | None
    pending_discards:    dict[str, int]        # pid → cards to discard
    robber_pending:      bool
    dev_played_this_turn:   bool
    dev_bought_this_turn:   dict[DevCard, int] # cards bought this turn (can't play same turn)

    @property
    def current_player(self) -> str:
        return self.player_order[self.current_index]

    def clone(self) -> "GameState":
        import copy
        return copy.deepcopy(self)
```

> **Why `bonus_vp`?**
> The app supports a "dev mode" where an admin can set resources and VP freely for testing. `bonus_vp` is the sandbox override — it has no meaning in strict Catan play.

---

## 1.6 Commands

Commands represent **player intent** — what someone wants to do. They can be rejected if illegal.

**`catan/domain/commands.py`**

```python
from dataclasses import dataclass
from .constants import Resource, DevCard
from .geometry import Coord

# --- Game lifecycle ---

@dataclass(frozen=True)
class CreateGame:
    players: tuple[str, ...]
    board_type: str          # "standard", "random", or "custom"

# --- Setup phase (snake draft) ---

@dataclass(frozen=True)
class PlaceSetupSettlement:
    pid: str
    vertex_id: int

@dataclass(frozen=True)
class PlaceSetupRoad:
    pid: str
    edge_index: int

# --- Main play phase ---

@dataclass(frozen=True)
class RollDice:
    pid: str
    d1: int
    d2: int

@dataclass(frozen=True)
class EndTurn:
    pid: str

@dataclass(frozen=True)
class Discard:
    pid: str
    resources: dict[Resource, int]

@dataclass(frozen=True)
class MoveRobber:
    pid: str
    coord: Coord
    victim: str | None
    resource: Resource | None   # observed stolen card (companion-app model)

@dataclass(frozen=True)
class BuildRoad:
    pid: str
    edge_index: int

@dataclass(frozen=True)
class BuildSettlement:
    pid: str
    vertex_id: int

@dataclass(frozen=True)
class BuildCity:
    pid: str
    vertex_id: int

@dataclass(frozen=True)
class BuyDevCard:
    pid: str
    card: DevCard    # the actual card drawn (observer records what was bought)

@dataclass(frozen=True)
class PlayKnight:
    pid: str
    robber_coord: Coord
    victim: str | None
    resource: Resource | None

@dataclass(frozen=True)
class PlayRoadBuilding:
    pid: str
    edge1: int
    edge2: int | None   # can place just one road if no valid second placement

@dataclass(frozen=True)
class PlayYearOfPlenty:
    pid: str
    resource1: Resource
    resource2: Resource

@dataclass(frozen=True)
class PlayMonopoly:
    pid: str
    resource: Resource

@dataclass(frozen=True)
class TradeWithBank:
    pid: str
    give:    Resource
    receive: Resource
    amount:  int              # how many given (2, 3, or 4 depending on ports)

@dataclass(frozen=True)
class TradeWithPlayer:
    pid:      str
    other:    str
    give:     dict[Resource, int]
    receive:  dict[Resource, int]

# --- Dev/sandbox only (strict=False games) ---

@dataclass(frozen=True)
class SetResources:
    pid:       str
    resources: dict[Resource, int]

@dataclass(frozen=True)
class SetVictoryPoints:
    pid: str
    vp:  int

# Union type for dispatch.
Command = (CreateGame | PlaceSetupSettlement | PlaceSetupRoad
           | RollDice | EndTurn | Discard | MoveRobber
           | BuildRoad | BuildSettlement | BuildCity | BuyDevCard
           | PlayKnight | PlayRoadBuilding | PlayYearOfPlenty | PlayMonopoly
           | TradeWithBank | TradeWithPlayer
           | SetResources | SetVictoryPoints)
```

> **Why does `BuyDevCard` carry the actual card?**
> This is a companion app for a *physical* game. The engine doesn't control the deck — it witnesses reality. The person recording the game looks at what was drawn and logs it. The engine then validates that this card still existed in the deck before approving the event.

---

## 1.7 Events

Events represent **facts that happened** — they cannot be rejected.

**`catan/domain/events.py`**

```python
from dataclasses import dataclass
from .constants import Resource, DevCard
from .geometry import Coord

# --- Lifecycle ---
@dataclass(frozen=True)
class GameCreated:
    players: tuple[str, ...]
    board_type: str

# --- Setup ---
@dataclass(frozen=True)
class SetupSettlementPlaced:
    pid: str; vertex_id: int

@dataclass(frozen=True)
class SetupRoadPlaced:
    pid: str; edge_index: int

# --- Turn structure ---
@dataclass(frozen=True)
class DiceRolled:
    pid: str; d1: int; d2: int
    @property
    def total(self) -> int: return self.d1 + self.d2

@dataclass(frozen=True)
class TurnEnded:
    pid: str

# --- Robber / discard ---
@dataclass(frozen=True)
class DiscardRequired:
    pid: str; count: int

@dataclass(frozen=True)
class Discarded:
    pid: str; resources: dict[Resource, int]

@dataclass(frozen=True)
class RobberMoved:
    pid: str; coord: Coord

@dataclass(frozen=True)
class Stolen:
    thief: str; victim: str; resource: Resource | None

# --- Building ---
@dataclass(frozen=True)
class RoadBuilt:
    pid: str; edge_index: int

@dataclass(frozen=True)
class SettlementBuilt:
    pid: str; vertex_id: int

@dataclass(frozen=True)
class CityBuilt:
    pid: str; vertex_id: int

# --- Dev cards ---
@dataclass(frozen=True)
class DevCardBought:
    pid: str; card: DevCard

@dataclass(frozen=True)
class KnightPlayed:
    pid: str; coord: Coord; victim: str | None; resource: Resource | None

@dataclass(frozen=True)
class RoadBuildingPlayed:
    pid: str; edge1: int; edge2: int | None

@dataclass(frozen=True)
class YearOfPlentyPlayed:
    pid: str; resource1: Resource; resource2: Resource

@dataclass(frozen=True)
class MonopolyPlayed:
    pid: str; resource: Resource

@dataclass(frozen=True)
class VictoryPointRevealed:
    pid: str; card: DevCard   # informational only — reducer ignores this

# --- Trades ---
@dataclass(frozen=True)
class MaritimeTrade:
    pid: str; give: Resource; receive: Resource; ratio: int

@dataclass(frozen=True)
class PlayerTrade:
    initiator: str; other: str
    give: dict[Resource, int]; receive: dict[Resource, int]

# --- Sandbox / dev mode ---
@dataclass(frozen=True)
class ResourcesSet:
    pid: str; resources: dict[Resource, int]

@dataclass(frozen=True)
class VictoryPointsSet:
    pid: str; vp: int

Event = (GameCreated | SetupSettlementPlaced | SetupRoadPlaced
         | DiceRolled | TurnEnded | DiscardRequired | Discarded
         | RobberMoved | Stolen
         | RoadBuilt | SettlementBuilt | CityBuilt
         | DevCardBought | KnightPlayed | RoadBuildingPlayed
         | YearOfPlentyPlayed | MonopolyPlayed | VictoryPointRevealed
         | MaritimeTrade | PlayerTrade
         | ResourcesSet | VictoryPointsSet)
```

> **Discussion:** Why are commands and events separate? Commands carry *intent* and can be rejected. Events carry *facts* — once an event is in the log, it happened. If you used one type for both, you'd lose the ability to distinguish "requested to build" from "built."

---

## Phase 1 Checkpoint

- [ ] All enums import cleanly: `from catan.domain.constants import Resource, Terrain, DevCard, PortType`
- [ ] `Resource.LUMBER`, `Resource.WOOL`, `Resource.GRAIN` — NOT `WOOD`, `SHEEP`, `WHEAT`
- [ ] `Phase` is in `state.py`, not `constants.py`
- [ ] Build costs are separate constants: `ROAD_COST`, `SETTLEMENT_COST`, etc.
- [ ] `Coord` is a type alias `tuple[int, int]`, not a class with methods
- [ ] `build_topology(standard_hexes())` returns topology with 54 vertices and 72 edges
- [ ] All command and event dataclasses are `frozen=True`
- [ ] `from catan.domain.state import GameState` imports without errors
- [ ] Commit: `"Phase 1: Complete domain models"`
