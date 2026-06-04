# Domain model

The `catan/domain/` package holds the pure data of the game: the board graph,
its content, the game constants, the event and command catalogs, and the
`GameState` model. Nothing here performs I/O or rules logic — that lives in the
[engine](engine.md).

Files:

| Module | Responsibility |
| --- | --- |
| `geometry.py` | The hex/vertex/edge graph (topology), computed from hex adjacency |
| `board.py` | Board *content*: terrains, number tokens, ports, robber; three generators |
| `constants.py` | Authoritative base-game counts, costs, and enums |
| `events.py` | The event catalog (immutable facts) |
| `commands.py` | The command catalog (intents submitted by clients) |
| `state.py` | `GameState` and `PlayerState`, plus derived properties |

## Geometry (`geometry.py`)

The board is a hexagon of hexes with **radius 2** — rows of 3-4-5-4-3 = **19
hexes**. Hexes use axial coordinates `(q, r)`. Vertices and edges are *derived*
from hex adjacency rather than hand-coded.

The canonical-identity trick makes ids stable and reproducible:

- A **vertex** is where up to three mutually-adjacent hexes meet, so it is
  identified by the `frozenset` of those hex coordinates. Computing the same
  corner from any surrounding hex yields the same frozenset.
- An **edge** connects two consecutive corners, so it is identified by the
  `frozenset` of its two vertex identities.

After collection, vertices and edges are sorted on a deterministic key and
assigned **integer ids**, so the ids are identical across runs and machines.

`build_topology()` returns an immutable `BoardTopology` with:

- `hexes`, `vertices` (id → key), `edges` (list of vertex-id pairs)
- adjacency maps: `vertex_neighbors`, `vertex_edges`, `vertex_hexes`,
  `hex_vertices`, `edge_vertices`

Expected sizes for the base board: **19 hexes, 54 vertices, 72 edges**.

## Board content (`board.py`)

A `Board` layers content onto the topology:

```python
@dataclass(frozen=True)
class Board:
    topology: BoardTopology
    terrain: dict[Coord, Terrain]      # 19 hexes
    numbers: dict[Coord, int]          # 18 tokens (desert has none)
    ports: list[Port]                  # 9 ports
    robber: Coord                      # starts on the desert
    pips: dict[Coord, int]             # probability pips per hex
```

Three ways to obtain a board:

- **`standard_board()`** — Reproducible. The desert is fixed at the center and
  the 18-number official spiral sequence (`STANDARD_NUMBER_SEQUENCE`) maps onto
  the 18 producing hexes. Terrains are dealt in pool order, so it is reproducible
  but **not** a faithful copy of any official setup.
- **`random_board(rng)`** — Shuffled but rules-legal: the red numbers **6 and 8
  are never placed on adjacent hexes**. Retries until a legal layout is found.
- **`custom_board(terrains, numbers, port_types=None)`** — The exact board on
  your table, transcribed in **spiral order** (outer ring → center, the same
  order as the official A–R token sequence). Terrain names accept synonyms
  (`wood`→forest, `wheat`→fields, `clay`→hills, etc.). Counts must match the base
  game exactly, which catches most data-entry mistakes.

Ports are spread evenly across the perimeter edges. A `Port` knows its
`PortType`, the two vertices it touches, its trade `ratio`, and the `resource`
it discounts (or `None` for a generic 3:1).

"Spiral order" and "pip" helpers (`_spiral_order`, `_compute_pips`) are reused by
the API's board template and metrics.

## Constants (`constants.py`)

Authoritative base-game values. Highlights:

- **Resources**: brick, lumber, wool, grain, ore. `Terrain` maps to a resource
  (desert → none) via `TERRAIN_RESOURCE`.
- **Counts**: `TERRAIN_COUNTS` (19 hexes), `NUMBER_TOKEN_COUNTS` (18 tokens,
  no 7), `PORT_COUNTS` (9), `BANK_RESOURCE_COUNT = 19` per resource.
- **Pips**: `PIPS` maps a token to its number of dice combinations (2 and 12 → 1,
  6 and 8 → 5). This drives expected production / "luck".
- **Development cards** (`DevCard`, 25 total): 14 knight, 5 victory point,
  2 road building, 2 year of plenty, 2 monopoly.
- **Pieces per player**: 5 settlements, 4 cities, 15 roads.
- **Build costs**: road = brick+lumber; settlement = brick+lumber+wool+grain;
  city = 3 ore + 2 grain; dev card = ore+wool+grain.
- **Win & awards**: 10 VP to win; Longest Road needs ≥ 5 (worth 2 VP); Largest
  Army needs ≥ 3 knights (worth 2 VP).
- **Trading**: default bank ratio 4:1; generic port 3:1; resource port 2:1.

## Events (`events.py`)

Events are immutable (`frozen=True`) payloads describing something that
happened. They are storage-agnostic — the persistence layer wraps each in an
envelope with a sequence number and timestamp. Per the
deterministic-consequence rule, events carry only what cannot be derived.

The catalog (the `Event` union):

| Group | Events |
| --- | --- |
| Lifecycle / setup | `GameCreated`, `SetupSettlementPlaced`, `SetupRoadPlaced` |
| Turns / dice | `DiceRolled` (carries only the dice), `TurnEnded` |
| Robber / the 7 | `DiscardedToRobber`, `RobberMoved`, `ResourceStolen` |
| Trades | `DomesticTrade`, `MaritimeTrade` |
| Builds | `RoadBuilt`, `SettlementBuilt`, `CityBuilt` |
| Development cards | `DevCardBought`, `KnightPlayed`, `RoadBuildingPlayed`, `YearOfPlentyPlayed`, `MonopolyPlayed`, `VictoryPointRevealed` |

## Commands (`commands.py`)

Commands express intent and are the only thing clients submit. They mirror
events but are distinct: a command may be rejected, may require derivation (e.g.
a maritime ratio is *looked up*, not trusted), and may expand into several
events.

The catalog (the `Command` union):

| Command | Notes |
| --- | --- |
| `CreateGame` | board + player order (2–4 players) |
| `PlaceSetupSettlement`, `PlaceSetupRoad` | setup snake draft |
| `RollDice` | the companion observes the physical dice |
| `EndTurn` | |
| `Discard` | resolve a 7 for one player |
| `MoveRobber` | hex + optional victim/resource to steal |
| `BuildRoad`, `BuildSettlement`, `BuildCity` | |
| `BuyDevCard` | carries the *actually drawn* card (the operator sees it) |
| `PlayKnight`, `PlayRoadBuilding`, `PlayYearOfPlenty`, `PlayMonopoly` | |
| `TradeWithBank` | give/receive resources + amounts (ratio is derived) |
| `TradeWithPlayer` | partner + the two resource bundles |

Because this is a companion to a real game, commands record observed reality:
the dice you rolled, the card you drew, the card you stole.

## Game state (`state.py`)

`GameState` is the folded result of the event log. It is a mutable dataclass,
but the reducer only ever mutates a **clone**.

`PlayerState` tracks one player's resources, dev cards (held and played),
knights played, and the sets of vertex/edge ids they occupy
(`settlements`, `cities`, `roads`). Derived properties include `hand_size` and
`settlements_left` / `cities_left` / `roads_left`.

`GameState` tracks the board, player order, per-player states, and:

- `phase` (`SETUP` → `PLAY` → `FINISHED`), `current_index`, `turn_number`
- `dice`, `has_rolled`
- `bank` and `dev_deck` (remaining counts)
- `robber` position, `longest_road_holder`, `largest_army_holder`, `winner`
- **turn-scoped flags** the reducer maintains and the validator reads:
  `pending_discards`, `robber_pending`, `dev_played_this_turn`,
  `dev_bought_this_turn` (so a card bought this turn can't be played this turn)

Useful methods:

- `clone()` — deep-copies game progress, shares the immutable board.
- `current_player` — the player whose turn it is.
- `owner_of_vertex(v)` / `owner_of_edge(e)` — who occupies a spot.
- `victory_points(pid, include_hidden=…)` — settlements + 2×cities + awards
  (+ hidden VP cards when `include_hidden`). The "public" VP (without hidden
  cards) is what opponents can see.

## See also

- How these types are validated and folded: [engine.md](engine.md)
- How they are serialized to SQLite: [persistence.md](persistence.md)
