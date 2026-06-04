# Capstone Project: Catan Companion App
## CS 499 — Senior Capstone in Software Engineering
### Lab Guide & Project Specification

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Learning Objectives](#2-learning-objectives)
3. [Prerequisites](#3-prerequisites)
4. [Project Management & Planning](#4-project-management--planning)
5. [Environment Setup](#5-environment-setup)
6. [Phase 1 — Domain Modeling](#6-phase-1--domain-modeling)
7. [Phase 2 — Game Engine](#7-phase-2--game-engine)
8. [Phase 3 — Persistence Layer](#8-phase-3--persistence-layer)
9. [Phase 4 — CLI Interface](#9-phase-4--cli-interface)
10. [Phase 5 — REST API & WebSockets](#10-phase-5--rest-api--websockets)
11. [Phase 6 — React Frontend](#11-phase-6--react-frontend)
12. [Phase 7 — Metrics & Analytics](#12-phase-7--metrics--analytics)
13. [Phase 8 — Testing Strategy](#13-phase-8--testing-strategy)
14. [Phase 9 — Polish & Delivery](#14-phase-9--polish--delivery)
15. [Grading Rubric](#15-grading-rubric)
16. [Appendix A — Catan Rules Reference](#16-appendix-a--catan-rules-reference)
17. [Appendix B — Hex Grid Mathematics](#17-appendix-b--hex-grid-mathematics)
18. [Appendix C — Recommended Reading](#18-appendix-c--recommended-reading)

---

## 1. Project Overview

### What You Are Building

A **Catan Companion App** — a real-time digital tool that players use alongside a physical copy of Settlers of Catan. Players sit at a real board and enter each action (roll dice, build a road, trade with the bank, play a dev card) into the app. The app:

- Enforces all official Catan rules so illegal moves are rejected before they happen
- Maintains a complete, time-travelable game history in a database
- Computes post-game analytics: luck scores, dice histograms, production efficiency, pip equity
- Pushes live state to every connected browser tab via WebSockets so all players share one view

This is **not** an AI opponent or a video game. The "game" happens at the physical table. The app is the scorekeeper, referee, and statistician.

### Why This Project

This capstone touches every layer of a modern full-stack application:

| Layer | What You'll Learn |
|---|---|
| Domain modeling | Translating board-game rules into clean data structures |
| Functional core | Pure functions, immutability, event sourcing |
| Persistence | SQLite, append-only event logs, snapshots |
| Web API | REST design, WebSockets, FastAPI |
| Frontend | React hooks, SVG rendering, real-time state |
| Testing | Unit, integration, and API testing |
| Dev practices | Git workflow, project structure, documentation |

### Final Deliverables

By the end of the semester you will turn in:
1. A working application (backend + frontend)
2. A test suite with ≥80% coverage
3. A `README.md` with setup instructions
4. A design document (written during planning phases)
5. A 15-minute live demo

---

## 2. Learning Objectives

After completing this project, you will be able to:

- **LO1** — Design a layered software architecture separating domain logic from infrastructure
- **LO2** — Implement event sourcing: append-only logs, snapshots, and state replay
- **LO3** — Write pure validation and reduction functions that are easy to test in isolation
- **LO4** — Build a REST API with proper HTTP semantics and WebSocket support
- **LO5** — Render interactive SVG graphics driven by data from an API
- **LO6** — Apply a test-first mindset: write tests that define behavior before implementing it
- **LO7** — Use git branching and pull requests as a professional workflow tool
- **LO8** — Estimate, track, and reflect on software project scope

---

## 3. Prerequisites

### Knowledge Required
- Python 3.10+ (data structures, classes, functions)
- Basic JavaScript / TypeScript (variables, functions, async/await)
- HTML & CSS fundamentals
- Command line basics (cd, ls, mkdir, running scripts)
- Git basics (clone, commit, push, branch)

### Knowledge That Helps But Is Not Required
- React (you will pick it up during Phase 6)
- SQL (explained when needed in Phase 3)
- HTTP / REST concepts (explained in Phase 5)

### Tools You Need Installed
```
Python 3.11 or newer
Node.js 20 or newer (includes npm)
Git
A code editor (VS Code recommended)
```

---

## 4. Project Management & Planning

> **Instructor Note:** This section is not optional. Professional developers spend more time planning than coding. Skipping it causes projects to fail. You will be graded on your planning artifacts as well as your code.

### 4.1 The Software Development Lifecycle

Every professional software project follows some version of this cycle:

```
Requirements → Design → Implementation → Testing → Deployment → Maintenance
       ↑                                                              |
       └──────────────────────── Feedback ──────────────────────────┘
```

For this capstone you will move through the cycle multiple times — once per phase. Each phase ends with a checkpoint where you verify the phase works before moving on.

### 4.2 Breaking Down the Problem

Before writing a single line of code, you must understand the problem deeply. Ask yourself:

1. **What is the system's job?** (Track a Catan game and enforce rules)
2. **Who uses it?** (Players at a physical table, usually 3–4 people)
3. **What inputs does it accept?** (Player actions: roll, build, trade, etc.)
4. **What does it output?** (Current game state, metrics, visual board)
5. **What are the failure modes?** (Invalid moves, disconnected browser, corrupt save)

**Exercise 4.2.1 (Due before Phase 1):** Write one paragraph answering each of these five questions. Keep this in a file called `design/requirements.md`. Commit it before you write any code.

### 4.3 Architecture First

Architecture is the high-level structure of your system — which pieces exist, what each one does, and how they connect. Getting this right early saves enormous refactoring pain later.

The architecture for this project is **layered**:

```
┌─────────────────────────────────────────────────┐
│                  Web Browser                     │
│  React UI (components, state, WebSocket client)  │
└────────────────────────┬────────────────────────┘
                         │ HTTP / WebSocket
┌────────────────────────▼────────────────────────┐
│                   FastAPI Server                  │
│    (HTTP routes, WebSocket hub, request logic)   │
└────────────────────────┬────────────────────────┘
                         │ Python function calls
┌────────────────────────▼────────────────────────┐
│               Game Service / Repository          │
│    (orchestrates engine + storage together)      │
└──────────┬─────────────────────────┬────────────┘
           │                         │
┌──────────▼──────────┐   ┌──────────▼──────────┐
│    Game Engine       │   │    Event Store       │
│  (validate, reduce)  │   │    (SQLite DB)       │
└──────────┬──────────┘   └─────────────────────-┘
           │
┌──────────▼──────────┐
│    Domain Models     │
│  (Board, GameState,  │
│   Commands, Events)  │
└─────────────────────┘
```

**The key rule:** Lower layers never import from upper layers. Domain models know nothing about the database. The engine knows nothing about HTTP. Violations of this rule make code impossible to test.

**Exercise 4.3.1:** Draw this diagram by hand. Label each box with: (a) what language/framework is in that box, and (b) one sentence describing its responsibility. This diagram goes into `design/architecture.md`.

### 4.4 Project Tracking

Use a simple task board. Create a file `design/tasks.md` with this structure:

```markdown
## Backlog
- [ ] Set up project structure
- [ ] Define Resource and Terrain enums
- [ ] ...

## In Progress
- [ ] (move items here when you start)

## Done
- [x] Created git repo
```

Update this file at every work session. At the end of the project, your task history is part of your grade.

**The most important rule of project tracking:** Break every task into something that can be completed in one sitting (1–3 hours). "Build the frontend" is not a task. "Render one hexagon on screen as SVG" is a task.

### 4.5 Git Workflow

You will use git throughout this project. Follow these rules:

**Commit often.** A commit should represent one small, complete thought. "Add Roll command dataclass" is a good commit. "Various changes" is not.

**Write commit messages that explain WHY, not what.** The diff already shows what changed.
```
Bad:  "fix bug"
Good: "Reject SetRobber command when robber is already on the target hex"
```

**Use branches for each phase.** Never work directly on `main`.
```bash
git checkout -b phase-1-domain-models
# ... do work ...
git push origin phase-1-domain-models
# Open a pull request → merge → delete branch
```

**Branch naming convention:**
```
phase-N-short-description
```

**Commit checklist (before every commit):**
- [ ] Does the code run without errors?
- [ ] Did I break any existing tests?
- [ ] Is my commit message a complete sentence?

---

## 5. Environment Setup

### 5.1 Create the Repository

```bash
# On GitHub, create a new repo called "catan-companion"
# Then clone it locally:
git clone https://github.com/YOUR_USERNAME/catan-companion.git
cd catan-companion
```

### 5.2 Python Project Setup

```bash
# Create the project layout
mkdir -p catan/{domain,engine,store,cli,api}
mkdir -p tests
mkdir -p design
touch catan/__init__.py
touch catan/domain/__init__.py
touch catan/engine/__init__.py
touch catan/store/__init__.py
touch catan/cli/__init__.py
touch catan/api/__init__.py
```

Create `pyproject.toml` — the modern Python project configuration file:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "catan"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi[standard]>=0.100",
    "uvicorn[standard]>=0.23",
]

[project.scripts]
catan = "catan.cli.main:main"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.hatch.build.targets.wheel]
packages = ["catan"]
```

Create a virtual environment and install:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pip install pytest httpx pytest-cov
```

Create `.gitignore`:
```
__pycache__/
*.pyc
.venv/
*.db
.env
dist/
web/node_modules/
web/dist/
```

### 5.3 Frontend Setup

```bash
cd web
npm create vite@latest . -- --template react-ts
npm install
```

Commit everything:
```bash
git add .
git commit -m "Initial project scaffolding with Python backend and React frontend"
```

### 5.4 Verify Setup

```bash
# Python
python -c "import catan; print('Python OK')"
pytest  # Should report "no tests" — that's fine for now

# Frontend
cd web && npm run dev  # Should open a browser with the Vite default page
```

---

## 6. Phase 1 — Domain Modeling

> **Goal:** Define the data structures that represent the game world. No logic yet — just types.

> **Branch:** `git checkout -b phase-1-domain-models`

### 6.1 What Is Domain Modeling?

Domain modeling means translating real-world concepts into code structures. Before you can write game logic, you need to answer: "How will my program represent a Catan board? A player? A turn?"

Good domain models have these properties:
- **Immutable where possible** — data that can't change is easier to reason about and test
- **Self-documenting** — a type named `Resource` with values `WOOD`, `BRICK`, etc. is clearer than using integer codes
- **Complete** — every concept in the game has a corresponding type

### 6.2 Enumerations: Named Constants

Python's `enum.Enum` lets you give meaningful names to fixed sets of values. This is far better than using magic strings or numbers.

**File: `catan/domain/constants.py`**

```python
from enum import Enum, auto

class Resource(Enum):
    WOOD = "wood"
    BRICK = "brick"
    WHEAT = "wheat"
    SHEEP = "sheep"
    ORE = "ore"

class Terrain(Enum):
    FOREST = "forest"      # produces WOOD
    HILLS = "hills"        # produces BRICK
    FIELDS = "fields"      # produces WHEAT
    PASTURE = "pasture"    # produces SHEEP
    MOUNTAINS = "mountains"  # produces ORE
    DESERT = "desert"      # produces nothing
    SEA = "sea"            # ocean tile

class Phase(Enum):
    SETUP = "setup"    # players placing initial settlements
    PLAY = "play"      # main game
    FINISHED = "finished"

class DevCard(Enum):
    KNIGHT = "knight"
    ROAD_BUILDING = "road_building"
    YEAR_OF_PLENTY = "year_of_plenty"
    MONOPOLY = "monopoly"
    VICTORY_POINT = "victory_point"
```

**Why enums?** Compare these two versions of the same check:
```python
# Bad: magic string — typos are silent bugs
if terrain == "forrest":   # this will never match, but Python won't warn you
    give_resource("wood")

# Good: enum — typos are caught immediately
if terrain == Terrain.FOREST:
    give_resource(Resource.WOOD)
```

**Add game constants:**
```python
# Building costs: what resources each structure requires
COSTS: dict[str, dict[Resource, int]] = {
    "road":       {Resource.WOOD: 1, Resource.BRICK: 1},
    "settlement": {Resource.WOOD: 1, Resource.BRICK: 1,
                   Resource.WHEAT: 1, Resource.SHEEP: 1},
    "city":       {Resource.WHEAT: 2, Resource.ORE: 3},
    "dev_card":   {Resource.WHEAT: 1, Resource.SHEEP: 1, Resource.ORE: 1},
}

# Pip values: how often each number is rolled on 2d6
PIPS = {2:1, 3:2, 4:3, 5:4, 6:5, 8:5, 9:4, 10:3, 11:2, 12:1}

# Which terrain produces which resource
TERRAIN_RESOURCE: dict[Terrain, Resource | None] = {
    Terrain.FOREST:    Resource.WOOD,
    Terrain.HILLS:     Resource.BRICK,
    Terrain.FIELDS:    Resource.WHEAT,
    Terrain.PASTURE:   Resource.SHEEP,
    Terrain.MOUNTAINS: Resource.ORE,
    Terrain.DESERT:    None,
    Terrain.SEA:       None,
}
```

### 6.3 Coordinate System: Axial Hex Coordinates

A Catan board is a grid of hexagons. There are several ways to represent hex positions mathematically. We will use **axial coordinates** — a system with two axes (q, r) that tile the plane with hexagons cleanly.

**File: `catan/domain/geometry.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import NamedTuple

class Coord(NamedTuple):
    """Axial hex coordinate. q = column axis, r = row axis."""
    q: int
    r: int

    def neighbors(self) -> list[Coord]:
        """Return the 6 adjacent hex coordinates."""
        directions = [(1,0),(-1,0),(0,1),(0,-1),(1,-1),(-1,1)]
        return [Coord(self.q + dq, self.r + dr) for dq, dr in directions]
```

> **Checkpoint:** Can you draw the first three rings of a hex grid on graph paper using `Coord` values? The center is `Coord(0, 0)`. Calling `.neighbors()` gives you the 6 adjacent hexes. Ring 2 is the neighbors of the neighbors (minus duplicates). Understanding this *before* you write more code will save you hours.

**See Appendix B for the full hex grid math reference.**

### 6.4 Board Topology: Vertices and Edges

In Catan, players build settlements on **vertices** (the corners where 3 hexes meet) and roads on **edges** (the sides of hexes). We need to compute all vertices and edges from the set of hex coordinates.

A vertex is uniquely identified by the three hexes that share it. An edge is a pair of vertex IDs.

```python
@dataclass(frozen=True)
class BoardTopology:
    """
    Precomputed graph structure for a hex board.
    Built once from a set of hex coordinates; never mutated.
    """
    hexes: frozenset[Coord]
    # vertex id → frozenset of hex coords sharing that corner
    vertices: dict[int, frozenset[Coord]]
    # list of (vertex_id, vertex_id) pairs for each edge
    edges: list[tuple[int, int]]
    # adjacency maps (computed from above, stored for fast lookup)
    vertex_neighbors: dict[int, list[int]]    # which vertices touch this vertex
    vertex_edges: dict[int, list[int]]        # which edge indices touch this vertex
    vertex_hexes: dict[int, list[Coord]]      # which hexes touch this vertex
    hex_vertices: dict[Coord, list[int]]      # which vertices belong to this hex
    edge_vertices: dict[int, tuple[int, int]] # edge index → (vid1, vid2)
```

**Building the topology** is the trickiest part of Phase 1. The algorithm:

1. For each hex in the board, compute its 6 corner coordinates in 2D space
2. Two corners from different hexes are the same vertex if they have the same 2D position (within floating point tolerance)
3. Assign each unique corner an integer vertex ID
4. An edge exists between two vertex IDs that share a hex side

**Exercise 6.4.1:** Before implementing, write this function signature and docstring:
```python
def build_topology(hexes: frozenset[Coord]) -> BoardTopology:
    """
    Given a set of hex positions, compute all vertices and edges.
    
    Vertices are corners shared by up to 3 hexes.
    Edges are sides shared by up to 2 hexes, represented as pairs of vertex IDs.
    
    Returns a fully connected topology graph.
    """
    ...
```

Then write down on paper: what is the expected number of vertices for a 19-hex standard board? (Answer: 54 land vertices, plus sea vertices on the border)

### 6.5 Board State

```python
# catan/domain/board.py
from dataclasses import dataclass
from .geometry import Coord, BoardTopology
from .constants import Terrain, Resource

@dataclass
class Port:
    resource: Resource | None  # None = 3:1 port
    rate: int                  # 2 or 3
    vertices: tuple[int, int]  # which two vertices have port access

@dataclass(frozen=True)
class Board:
    topology: BoardTopology
    terrain: dict[Coord, Terrain]
    numbers: dict[Coord, int]         # hex → number token (2-12, no 7)
    ports: list[Port]
    robber: Coord                     # current robber position
    pips: dict[Coord, int]            # hex → pip count (from PIPS table)
```

### 6.6 Player and Game State

```python
# catan/domain/state.py
from dataclasses import dataclass, field
from .board import Board
from .constants import Resource, DevCard, Phase

@dataclass
class PlayerState:
    pid: str                                  # unique player id (e.g. "alice")
    resources: dict[Resource, int]            # resource counts
    dev_cards: list[DevCard]                  # unplayed dev cards in hand
    dev_cards_played: list[DevCard]           # played dev cards
    knights_played: int                       # for Largest Army
    settlements: set[int]                     # vertex IDs with settlements
    cities: set[int]                          # vertex IDs with cities
    roads: set[int]                           # edge indices with roads
    bonus_vp: int                             # VP from victory point dev cards

    def victory_points(self) -> int:
        return (len(self.settlements)
                + len(self.cities) * 2
                + self.bonus_vp)

@dataclass
class GameState:
    board: Board
    player_order: list[str]                   # ordered list of pids
    players: dict[str, PlayerState]
    phase: Phase
    current_index: int                        # index into player_order
    turn_number: int
    dice: tuple[int, int] | None              # most recent roll
    has_rolled: bool
    bank: dict[Resource, int]                 # remaining bank resources
    dev_deck: list[DevCard]                   # remaining dev cards
    robber: Coord                             # (mirrors board.robber)
    longest_road_holder: str | None
    largest_army_holder: str | None
    winner: str | None
    pending_discards: dict[str, int]          # players who must discard
    robber_pending: bool                      # must place robber this turn
    dev_played_this_turn: bool
    dev_bought_this_turn: bool

    @property
    def current_player(self) -> str:
        return self.player_order[self.current_index]

    def clone(self) -> "GameState":
        """Return a deep copy. Used by the reducer."""
        import copy
        return copy.deepcopy(self)
```

### 6.7 Commands and Events

This is where the **event sourcing pattern** begins. Every player action is a **Command** (intent) that, if valid, produces one or more **Events** (facts about what happened).

```
Command: "Alice wants to build a settlement at vertex 12"
  ↓ validate
Event: "Settlement was built at vertex 12 by alice, costing {WOOD:1, BRICK:1, WHEAT:1, SHEEP:1}"
```

The distinction matters because:
- Commands can be **rejected** (illegal move) — events cannot
- Events are what gets stored in the database
- The current game state is always reconstructable by replaying events

**File: `catan/domain/commands.py`**

```python
from dataclasses import dataclass
from .constants import Resource, DevCard
from .geometry import Coord

# Every command is a frozen dataclass — immutable once created

@dataclass(frozen=True)
class RollDice:
    pid: str
    d1: int
    d2: int

@dataclass(frozen=True)
class BuildSettlement:
    pid: str
    vertex_id: int

@dataclass(frozen=True)
class BuildCity:
    pid: str
    vertex_id: int

@dataclass(frozen=True)
class BuildRoad:
    pid: str
    edge_index: int

@dataclass(frozen=True)
class BuyDevCard:
    pid: str

@dataclass(frozen=True)
class PlayKnight:
    pid: str
    robber_coord: Coord
    victim: str | None

@dataclass(frozen=True)
class TradeWithBank:
    pid: str
    give: Resource
    receive: Resource

@dataclass(frozen=True)
class EndTurn:
    pid: str

# ... add more as needed

Command = (RollDice | BuildSettlement | BuildCity | BuildRoad
           | BuyDevCard | PlayKnight | TradeWithBank | EndTurn)
```

**File: `catan/domain/events.py`** — similar structure, but events record *what actually happened*:

```python
@dataclass(frozen=True)
class DiceRolled:
    pid: str
    d1: int
    d2: int
    total: int

@dataclass(frozen=True)
class SettlementBuilt:
    pid: str
    vertex_id: int

@dataclass(frozen=True)
class ResourcesGranted:
    pid: str
    resources: dict[Resource, int]

@dataclass(frozen=True)
class ResourcesSpent:
    pid: str
    resources: dict[Resource, int]

# ...
```

> **Discussion Question:** Why are commands and events separate types? Could you use just one? What would break?

### Phase 1 Checkpoint

Before moving on, verify:
- [ ] All enum values are defined with no typos
- [ ] `Coord.neighbors()` returns 6 coordinates
- [ ] `PlayerState.victory_points()` returns the right number
- [ ] All command and event dataclasses are `frozen=True`
- [ ] You can import everything: `from catan.domain.state import GameState`
- [ ] Commit with message: `"Phase 1: Complete domain models"`

---

## 7. Phase 2 — Game Engine

> **Goal:** Implement the validation and reduction functions that enforce Catan rules.

> **Branch:** `git checkout -b phase-2-game-engine`

### 7.1 The Functional Core Pattern

The game engine follows the **functional core, imperative shell** pattern:

- **Functional core:** Pure functions that take input and return output with no side effects
  - `validate(state, command) → Result`
  - `reduce(state, event) → GameState`
- **Imperative shell:** Code that reads from databases, writes to files, handles HTTP requests

Pure functions are dramatically easier to test. You can test `validate()` by just calling it with data you construct — no database, no HTTP server, no file system needed.

### 7.2 The Result Type

Create a simple result type to represent success or failure:

```python
# catan/engine/validate.py
from dataclasses import dataclass, field
from catan.domain.events import Event

@dataclass
class Result:
    ok: bool
    events: list[Event] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @classmethod
    def success(cls, events: list[Event]) -> "Result":
        return cls(ok=True, events=events)

    @classmethod
    def failure(cls, *errors: str) -> "Result":
        return cls(ok=False, errors=list(errors))
```

### 7.3 Validation: Checking If a Move Is Legal

```python
from catan.domain.state import GameState
from catan.domain.commands import Command, BuildSettlement, RollDice

def validate(state: GameState, command: Command, strict: bool = True) -> Result:
    """
    Check whether `command` is legal given `state`.
    Returns Result.success(events) or Result.failure(reason).
    
    In strict mode, all Catan rules are enforced (turn order, resource costs, etc).
    In dev mode (strict=False), only structural rules apply (valid vertex IDs, etc).
    """
    match command:
        case RollDice():
            return _validate_roll(state, command, strict)
        case BuildSettlement():
            return _validate_build_settlement(state, command, strict)
        # ... one case per command type
        case _:
            return Result.failure(f"Unknown command type: {type(command).__name__}")
```

**Implementing one validator — BuildSettlement:**

```python
def _validate_build_settlement(state: GameState, cmd: BuildSettlement, strict: bool) -> Result:
    player = state.players.get(cmd.pid)
    if player is None:
        return Result.failure(f"Unknown player: {cmd.pid}")
    
    vid = cmd.vertex_id
    topology = state.board.topology
    
    # 1. Vertex must exist on the board
    if vid not in topology.vertices:
        return Result.failure(f"Vertex {vid} does not exist")
    
    # 2. No building already on this vertex (anyone's)
    for p in state.players.values():
        if vid in p.settlements or vid in p.cities:
            return Result.failure(f"Vertex {vid} is already occupied")
    
    # 3. Distance rule: no adjacent vertex may have a building (any player)
    for neighbor_vid in topology.vertex_neighbors[vid]:
        for p in state.players.values():
            if neighbor_vid in p.settlements or neighbor_vid in p.cities:
                return Result.failure(f"Too close to existing building (distance rule)")
    
    if strict:
        # 4. Must be player's turn
        if state.current_player != cmd.pid:
            return Result.failure("Not your turn")
        
        # 5. In main phase: must have road connection + resources
        if state.phase == Phase.PLAY:
            if not _player_has_road_to(state, cmd.pid, vid):
                return Result.failure("No road connection to this vertex")
            if not _can_afford(player, COSTS["settlement"]):
                return Result.failure("Insufficient resources")
    
    # All checks passed — produce the events
    events: list[Event] = [SettlementBuilt(pid=cmd.pid, vertex_id=vid)]
    if strict and state.phase == Phase.PLAY:
        events.append(ResourcesSpent(pid=cmd.pid, resources=COSTS["settlement"]))
    return Result.success(events)
```

**Exercise 7.3.1:** Implement `_validate_roll`. A dice roll is valid when:
1. The player exists
2. In strict mode: it's their turn
3. In strict mode: they haven't already rolled this turn
4. The dice values are each 1–6
5. The total equals d1 + d2

What events should a successful roll produce? At minimum: `DiceRolled`. But if the total is 7 and there are players with more than 7 cards, you also need `DiscardRequired` events. If the total is not 7, you need `ResourcesGranted` events for every player who has a settlement adjacent to a hex with that number token.

### 7.4 Reduction: Applying an Event to State

The reducer is the opposite direction — given a state and an event that we know already happened, return the new state.

```python
# catan/engine/reduce.py
from copy import deepcopy
from catan.domain.state import GameState
from catan.domain.events import Event, SettlementBuilt, ResourcesGranted, DiceRolled

def reduce(state: GameState, event: Event) -> GameState:
    """
    Apply a single event to state, returning a new state.
    This function must never raise an exception.
    All validation already happened in validate().
    """
    s = state.clone()  # work on a copy — never mutate the input
    _apply(s, event)
    return s

def _apply(s: GameState, event: Event) -> None:
    """Mutate s in place according to event."""
    match event:
        case SettlementBuilt(pid=pid, vertex_id=vid):
            s.players[pid].settlements.add(vid)
        
        case ResourcesGranted(pid=pid, resources=res):
            for resource, amount in res.items():
                s.players[pid].resources[resource] = (
                    s.players[pid].resources.get(resource, 0) + amount
                )
                s.bank[resource] -= amount
        
        case ResourcesSpent(pid=pid, resources=res):
            for resource, amount in res.items():
                s.players[pid].resources[resource] -= amount
                s.bank[resource] += amount
        
        # ... one case per event type
```

**The most important invariant:** After every `reduce()` call, total resources in the game must be conserved:
```
sum(player.resources) + bank resources = constants
```

Write a helper to check this — call it in every test.

### 7.5 Longest Road and Largest Army

These are the two "bonus VP" awards in Catan. Recalculate them after every event that could change them.

**Largest Army:** Straightforward — the player with the most knights played (minimum 3) wins 2 VP. If multiple players tie, the first to reach the threshold keeps it.

**Longest Road:** Harder — you need to find the longest continuous path through a player's roads. This is a **DFS (Depth-First Search)** graph traversal problem.

```python
# catan/engine/awards.py
def longest_road_for_player(topology, roads: set[int], settlements: dict[str, set[int]]) -> int:
    """
    Return the length of the longest continuous road for a player.
    
    `roads`: set of edge indices owned by this player
    `settlements`: all players' settlements (opponent settlements break the road)
    
    Try starting a DFS from every vertex on the player's road network.
    Return the maximum path length found.
    """
    ...
```

**Exercise 7.5.1:** Implement this using DFS. Your function should:
1. Build an adjacency graph of the player's roads
2. For each vertex in that graph, run DFS to find the longest path reachable from that vertex
3. Return the maximum

Test cases to write first (TDD):
- Single road: length 1
- Two connected roads: length 2
- A cycle (roads form a loop): should count each edge once
- An opponent's settlement in the middle of a chain: the chain is broken into two

### 7.6 The `execute` Convenience Function

```python
def execute(state: GameState, command: Command, strict: bool = True) -> tuple[GameState, list[Event]]:
    """
    Validate and apply a command in one step.
    Raises ValueError if the command is invalid.
    Returns (new_state, events).
    """
    result = validate(state, command, strict)
    if not result.ok:
        raise ValueError("; ".join(result.errors))
    new_state = state
    for event in result.events:
        new_state = reduce(new_state, event)
    return new_state, result.events
```

### Phase 2 Checkpoint

- [ ] `validate` returns `Result.failure` for each illegal move you test manually
- [ ] `reduce` never mutates its input (verify with `id()` checks)
- [ ] Resource totals are conserved across 10+ simulated turns
- [ ] Longest Road DFS handles cycles correctly
- [ ] Write at least 20 unit tests covering validation rules
- [ ] Commit: `"Phase 2: Game engine with validate and reduce"`

---

## 8. Phase 3 — Persistence Layer

> **Goal:** Store game events in SQLite so games survive server restarts.

> **Branch:** `git checkout -b phase-3-persistence`

### 8.1 Why Event Sourcing?

Traditional databases store current state: "Alice has 3 wood."

An **event-sourced** store records every change: "Alice gained 2 wood on turn 1. Alice spent 1 wood on turn 2."

Benefits:
- Full audit log — you can see every move ever made
- Time travel — reconstruct state at any point in history
- Debugging — the log tells you exactly how a state was reached
- Analytics — run projections over event history without touching live state

The tradeoff: reading state requires replaying all events (mitigated with **snapshots**).

### 8.2 SQLite Schema

SQLite is a file-based SQL database built into Python's standard library. No server needed.

```python
# catan/store/event_store.py
import sqlite3
import json
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    game_id   TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    mode      TEXT NOT NULL DEFAULT 'strict'
);

CREATE TABLE IF NOT EXISTS events (
    game_id TEXT NOT NULL,
    seq     INTEGER NOT NULL,
    ts      REAL NOT NULL,
    type    TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (game_id, seq),
    FOREIGN KEY (game_id) REFERENCES games(game_id)
);

CREATE TABLE IF NOT EXISTS snapshots (
    game_id TEXT NOT NULL,
    seq     INTEGER NOT NULL,
    state   TEXT NOT NULL,
    PRIMARY KEY (game_id, seq),
    FOREIGN KEY (game_id) REFERENCES games(game_id)
);
"""

SNAPSHOT_INTERVAL = 25  # save a snapshot every 25 events

class EventStore:
    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(SCHEMA)
    
    def create_game(self, game_id: str, mode: str = "strict") -> None:
        import time
        self._conn.execute(
            "INSERT INTO games (game_id, created_at, mode) VALUES (?, ?, ?)",
            (game_id, time.time(), mode)
        )
        self._conn.commit()
    
    def append(self, game_id: str, events: list, starting_seq: int) -> None:
        """Append a batch of events atomically."""
        import time
        rows = [
            (game_id, starting_seq + i, time.time(),
             type(e).__name__, json.dumps(encode_event(e)))
            for i, e in enumerate(events)
        ]
        self._conn.executemany(
            "INSERT INTO events (game_id, seq, ts, type, payload) VALUES (?,?,?,?,?)",
            rows
        )
        self._conn.commit()
```

### 8.3 Snapshots: Avoiding Full Replay

Replaying 500 events to get the current state is slow. Every `SNAPSHOT_INTERVAL` events, save the full state as JSON. Then, to load state, find the latest snapshot and only replay events after it.

```python
def load_state(self, game_id: str, at_seq: Optional[int] = None) -> tuple[GameState, int]:
    """
    Load game state at `at_seq` (or current if None).
    
    Strategy:
    1. Find the latest snapshot at or before at_seq
    2. Replay events from snapshot.seq + 1 up to at_seq
    3. Return (state, final_seq)
    """
    target = at_seq if at_seq is not None else self._latest_seq(game_id)
    
    # Find best snapshot
    snapshot_row = self._conn.execute(
        "SELECT seq, state FROM snapshots WHERE game_id=? AND seq<=? ORDER BY seq DESC LIMIT 1",
        (game_id, target)
    ).fetchone()
    
    if snapshot_row:
        start_seq = snapshot_row[0]
        state = decode_state(json.loads(snapshot_row[1]))
    else:
        start_seq = -1
        state = initial_state_for(game_id)  # you'll need to store initial state too
    
    # Replay remaining events
    rows = self._conn.execute(
        "SELECT seq, type, payload FROM events WHERE game_id=? AND seq>? AND seq<=? ORDER BY seq",
        (game_id, start_seq, target)
    ).fetchall()
    
    for seq, etype, payload in rows:
        event = decode_event(etype, json.loads(payload))
        state = reduce(state, event)
    
    return state, target
```

### 8.4 Serialization (Codec)

You need to convert Python objects to/from JSON for storage.

```python
# catan/store/codec.py

def encode_event(event) -> dict:
    """Convert an Event dataclass to a JSON-serializable dict."""
    d = asdict(event)  # from dataclasses module
    # Convert enum values to their .value strings
    # Convert frozensets to lists
    # (implement recursive conversion)
    return d

def decode_event(type_name: str, payload: dict):
    """Reconstruct an Event from its type name and payload dict."""
    event_classes = {
        "DiceRolled": DiceRolled,
        "SettlementBuilt": SettlementBuilt,
        # ...
    }
    cls = event_classes[type_name]
    # Convert string values back to enums, etc.
    return cls(**payload)
```

**Common serialization pitfalls:**
- Python `set` is not JSON-serializable → convert to sorted list
- Python `tuple` becomes a JSON array → convert back to tuple on decode
- Python `Enum` values: store `.value` (a string), reconstruct with `Resource("wood")`
- Nested objects need recursive handling

### 8.5 Game Service

The `GameService` is a thin orchestration layer that combines the store and engine:

```python
# catan/store/repository.py
from .event_store import EventStore
from catan.engine.validate import validate
from catan.engine.reduce import reduce

class GameService:
    def __init__(self, store: EventStore):
        self._store = store
    
    def apply(self, game_id: str, command) -> tuple[GameState, list]:
        """
        Load current state, validate command, append events, return new state.
        Raises ValueError if command is invalid.
        """
        state, current_seq = self._store.load_state(game_id)
        result = validate(state, command, strict=...)
        if not result.ok:
            raise ValueError("; ".join(result.errors))
        
        new_state = state
        for event in result.events:
            new_state = reduce(new_state, event)
        
        self._store.append(game_id, result.events, starting_seq=current_seq + 1)
        
        # Save snapshot if interval reached
        if (current_seq + len(result.events)) % SNAPSHOT_INTERVAL == SNAPSHOT_INTERVAL - 1:
            self._store.save_snapshot(game_id, current_seq + len(result.events), new_state)
        
        return new_state, result.events
```

### Phase 3 Checkpoint

- [ ] Create a game, apply 30 events, delete the `EventStore` object and reload — state is identical
- [ ] Time travel: load state at seq=10 during a 30-event game
- [ ] Snapshot is created at the right interval
- [ ] Encode and decode a round-trip for every event type — no data is lost
- [ ] Commit: `"Phase 3: SQLite event store with snapshot support"`

---

## 9. Phase 4 — CLI Interface

> **Goal:** Build a command-line REPL to play the game without a browser.

> **Branch:** `git checkout -b phase-4-cli`

### 9.1 Why Build a CLI First?

A CLI lets you test the full game flow interactively before you build the frontend. If your engine has bugs, you'll find them faster at the command line than through a web UI.

### 9.2 Argument Parser

```python
# catan/cli/main.py
import argparse

def main():
    parser = argparse.ArgumentParser(prog="catan", description="Catan Companion")
    sub = parser.add_subparsers(dest="command", required=True)
    
    # catan new --players alice bob charlie
    new_p = sub.add_parser("new", help="Start a new game")
    new_p.add_argument("--players", nargs="+", required=True)
    new_p.add_argument("--board", choices=["standard", "random", "custom"], default="standard")
    new_p.add_argument("--mode", choices=["strict", "dev"], default="strict")
    
    # catan play <game-id>
    play_p = sub.add_parser("play", help="Play a game in interactive REPL mode")
    play_p.add_argument("game_id")
    
    # catan metrics <game-id>
    metrics_p = sub.add_parser("metrics", help="Show post-game metrics")
    metrics_p.add_argument("game_id")
    
    # catan serve
    sub.add_parser("serve", help="Start the web server")
    
    args = parser.parse_args()
    
    svc = GameService(EventStore("catan.db"))
    
    if args.command == "new":
        handle_new(svc, args)
    elif args.command == "play":
        handle_play(svc, args)
    # ...
```

### 9.3 The REPL

A **REPL** (Read-Evaluate-Print Loop) is an interactive prompt:
```
> roll 3 4
Rolled 7. Place robber.
> robber 0,1 steal bob
Robber moved. Stole 1 WHEAT from bob.
> build road 5
Built road at edge 5.
```

```python
def handle_play(svc: GameService, args):
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        
        if line in ("quit", "exit", "q"):
            break
        if not line:
            continue
        
        command = parse_text_command(line, current_pid)
        if command is None:
            print(f"Unknown command: {line}")
            continue
        
        try:
            new_state, events = svc.apply(game_id, command)
            for event in events:
                print(render_event(event))
        except ValueError as e:
            print(f"Invalid: {e}")
```

### 9.4 Text Command Parser

```python
# catan/cli/parser.py

def parse_text_command(line: str, pid: str):
    """
    Parse a text line like "roll 3 4" into a Command dataclass.
    Returns None if the line cannot be parsed.
    """
    parts = line.lower().split()
    if not parts:
        return None
    
    verb = parts[0]
    
    if verb == "roll" and len(parts) == 3:
        try:
            d1, d2 = int(parts[1]), int(parts[2])
            return RollDice(pid=pid, d1=d1, d2=d2)
        except ValueError:
            return None
    
    if verb == "build" and len(parts) >= 3:
        structure = parts[1]
        location = int(parts[2])
        if structure == "settlement":
            return BuildSettlement(pid=pid, vertex_id=location)
        if structure == "road":
            return BuildRoad(pid=pid, edge_index=location)
        # ...
    
    # ... more verbs
    return None
```

### 9.5 Text Renderer

```python
# catan/cli/render.py

def render_state(state: GameState) -> str:
    """Return a multi-line text summary of the current game state."""
    lines = [f"Phase: {state.phase.value}  Turn: {state.turn_number}"]
    lines.append(f"Current player: {state.current_player}")
    for pid in state.player_order:
        p = state.players[pid]
        res = ", ".join(f"{r.value}:{n}" for r, n in p.resources.items() if n > 0)
        lines.append(f"  {pid}: {p.victory_points()} VP | {res or 'no resources'}")
    return "\n".join(lines)
```

### Phase 4 Checkpoint

- [ ] Play a complete setup phase via CLI
- [ ] Roll dice, collect resources, build, end turn — all via text commands
- [ ] Invalid commands print helpful error messages
- [ ] `catan serve` starts uvicorn (you'll implement the server in Phase 5)
- [ ] Commit: `"Phase 4: CLI REPL and text command parser"`

---

## 10. Phase 5 — REST API & WebSockets

> **Goal:** Expose the game service over HTTP so a browser can use it.

> **Branch:** `git checkout -b phase-5-api`

### 10.1 REST Design Principles

REST (Representational State Transfer) is a set of conventions for HTTP APIs:

| Convention | Example |
|---|---|
| Resources are nouns | `/api/games`, not `/api/getGames` |
| HTTP verbs express action | `POST` to create, `GET` to read, `DELETE` to delete |
| IDs in the URL | `/api/games/{id}` |
| Status codes have meaning | 200 OK, 201 Created, 400 Bad Request, 404 Not Found |
| Body is JSON | `Content-Type: application/json` |

**Your API endpoints:**

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/games` | `{players, board, mode}` | `{game_id}` |
| GET | `/api/games` | — | `[{game_id, players, created_at}]` |
| GET | `/api/games/{id}/state` | — | Full `GameStateDTO` |
| GET | `/api/games/{id}/layout` | — | SVG pixel coordinates |
| POST | `/api/games/{id}/commands` | Command JSON | `{state}` |
| DELETE | `/api/games/{id}` | — | 204 No Content |
| WS | `/api/games/{id}/ws` | — | WebSocket stream |

### 10.2 FastAPI Basics

```python
# catan/api/app.py
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware

def create_app(service: GameService) -> FastAPI:
    app = FastAPI(title="Catan Companion")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],  # Vite dev server
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.post("/api/games", status_code=201)
    def create_game(body: CreateGameRequest):
        game_id = str(uuid.uuid4())[:8]
        service.create(game_id, body.players, body.board, body.mode)
        return {"game_id": game_id}
    
    @app.get("/api/games/{game_id}/state")
    def get_state(game_id: str, at: int | None = None):
        try:
            state, seq = service.load(game_id, at_seq=at)
        except KeyError:
            raise HTTPException(404, "Game not found")
        return state_to_dto(state, seq)
    
    @app.post("/api/games/{game_id}/commands")
    def post_command(game_id: str, body: dict):
        command = decode_command(body)  # you build this
        try:
            new_state, events = service.apply(game_id, command)
        except ValueError as e:
            raise HTTPException(400, str(e))
        # Broadcast to WebSocket clients (see 10.3)
        asyncio.create_task(manager.broadcast(game_id, new_state))
        return state_to_dto(new_state)
    
    return app
```

### 10.3 WebSocket Hub

WebSockets maintain a persistent two-way connection. The pattern for broadcasting is:

```python
class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = {}
    
    async def connect(self, game_id: str, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(game_id, set()).add(ws)
    
    def disconnect(self, game_id: str, ws: WebSocket):
        self._connections.get(game_id, set()).discard(ws)
    
    async def broadcast(self, game_id: str, state: GameState):
        payload = {"type": "state", "state": state_to_dto(state)}
        dead = set()
        for ws in self._connections.get(game_id, set()):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(game_id, ws)

manager = ConnectionManager()

@app.websocket("/api/games/{game_id}/ws")
async def websocket_endpoint(game_id: str, ws: WebSocket):
    await manager.connect(game_id, ws)
    try:
        # Send current state immediately on connect
        state, seq = service.load(game_id)
        await ws.send_json({"type": "state", "state": state_to_dto(state, seq)})
        # Keep the connection alive
        while True:
            await ws.receive_text()  # wait for any message (or disconnect)
    except Exception:
        manager.disconnect(game_id, ws)
```

### 10.4 Board Layout: Hex to Pixel Coordinates

The frontend needs pixel coordinates to render the SVG board. Convert axial hex coordinates to pixel x/y:

```python
def hex_to_pixel(coord: Coord, size: float = 60.0) -> tuple[float, float]:
    """
    Convert axial hex coord to pixel center point.
    Uses flat-top hex orientation.
    """
    x = size * (3/2 * coord.q)
    y = size * (math.sqrt(3)/2 * coord.q + math.sqrt(3) * coord.r)
    return x, y
```

The 6 corners of a hex centered at `(cx, cy)` with flat-top orientation:
```python
def hex_corners(cx: float, cy: float, size: float = 60.0) -> list[tuple[float, float]]:
    return [
        (cx + size * math.cos(math.radians(60 * i)),
         cy + size * math.sin(math.radians(60 * i)))
        for i in range(6)
    ]
```

### Phase 5 Checkpoint

Use `curl` or a REST client (like Insomnia or Postman) to verify:
- [ ] `POST /api/games` creates a game and returns a `game_id`
- [ ] `GET /api/games/{id}/state` returns valid JSON
- [ ] `POST /api/games/{id}/commands` with a valid roll returns the new state
- [ ] `POST /api/games/{id}/commands` with an invalid move returns `400`
- [ ] Open two browser tabs to the WebSocket URL — both receive state updates when a command is posted
- [ ] Commit: `"Phase 5: FastAPI REST API with WebSocket broadcast"`

---

## 11. Phase 6 — React Frontend

> **Goal:** Build the browser UI that shows the board and accepts player input.

> **Branch:** `git checkout -b phase-6-frontend`

### 11.1 React Fundamentals Review

React builds UIs from **components** — functions that take **props** (inputs) and return JSX (markup).

**State** lives in components and changes over time. When state changes, React re-renders the component.

```tsx
// A simple counter component
import { useState } from 'react'

function Counter() {
  const [count, setCount] = useState(0)  // count starts at 0
  
  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>Increment</button>
    </div>
  )
}
```

**The mental model:**
```
state → render → user action → new state → re-render
```

### 11.2 TypeScript DTOs

TypeScript interfaces describe the shape of data coming from your API:

```typescript
// web/src/types.ts

export interface ResourceCounts {
  wood: number
  brick: number
  wheat: number
  sheep: number
  ore: number
}

export interface PlayerStateDTO {
  pid: string
  resources: ResourceCounts
  victory_points: number
  knights_played: number
  settlements: number[]
  cities: number[]
  roads: number[]
}

export interface GameStateDTO {
  game_id: string
  phase: "setup" | "play" | "finished"
  current_player: string
  turn_number: number
  players: Record<string, PlayerStateDTO>
  player_order: string[]
  dice: [number, number] | null
  has_rolled: boolean
  winner: string | null
  pending_discards: Record<string, number>
  robber_pending: boolean
  seq: number
}

export interface HexDTO {
  coord: { q: number; r: number }
  x: number
  y: number
  terrain: string
  number: number | null
  pips: number
  robber: boolean
  corners: [number, number][]  // pixel coordinates of 6 corners
}

export interface VertexDTO {
  id: number
  x: number
  y: number
  building: { pid: string; type: "settlement" | "city" } | null
}

export interface EdgeDTO {
  index: number
  x1: number; y1: number
  x2: number; y2: number
  road: { pid: string } | null
}

export interface LayoutDTO {
  hexes: HexDTO[]
  vertices: VertexDTO[]
  edges: EdgeDTO[]
  ports: PortDTO[]
}
```

### 11.3 API Client

```typescript
// web/src/api.ts

const BASE = "/api"

export async function fetchState(gameId: string): Promise<GameStateDTO> {
  const res = await fetch(`${BASE}/games/${gameId}/state`)
  if (!res.ok) throw new Error(`Failed to fetch state: ${res.status}`)
  return res.json()
}

export async function postCommand(gameId: string, command: object): Promise<GameStateDTO> {
  const res = await fetch(`${BASE}/games/${gameId}/commands`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(command),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || "Command failed")
  }
  return res.json()
}
```

### 11.4 WebSocket Hook

```typescript
// web/src/useGameSocket.ts
import { useEffect } from 'react'

export function useGameSocket(
  gameId: string,
  onState: (state: GameStateDTO) => void
) {
  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/games/${gameId}/ws`)
    
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.type === "state") {
        onState(msg.state)
      }
    }
    
    ws.onerror = (e) => console.error("WebSocket error", e)
    
    // Cleanup: close the WebSocket when the component unmounts
    return () => ws.close()
  }, [gameId])  // Only re-run if gameId changes
}
```

### 11.5 SVG Board Renderer

SVG (Scalable Vector Graphics) is XML markup for drawing shapes. React can render SVG inline.

```tsx
// web/src/components/Board.tsx
import { LayoutDTO, HexDTO, VertexDTO } from '../types'
import { terrainColor } from '../colors'

interface BoardProps {
  layout: LayoutDTO
  onVertexClick?: (vertexId: number) => void
  onEdgeClick?: (edgeIndex: number) => void
  activeTool: "settlement" | "road" | "city" | null
}

export function Board({ layout, onVertexClick, onEdgeClick, activeTool }: BoardProps) {
  return (
    <svg viewBox="-400 -350 800 700" width="600" height="525">
      {/* Render hex tiles */}
      {layout.hexes.map(hex => (
        <HexTile key={`${hex.coord.q},${hex.coord.r}`} hex={hex} />
      ))}
      
      {/* Render edges (roads) */}
      {layout.edges.map(edge => (
        <line
          key={edge.index}
          x1={edge.x1} y1={edge.y1}
          x2={edge.x2} y2={edge.y2}
          stroke={edge.road ? playerColor(edge.road.pid) : "#ccc"}
          strokeWidth={edge.road ? 6 : 3}
          style={{ cursor: activeTool === "road" ? "pointer" : "default" }}
          onClick={() => activeTool === "road" && onEdgeClick?.(edge.index)}
        />
      ))}
      
      {/* Render vertices (settlements/cities) */}
      {layout.vertices.map(v => (
        <VertexMarker
          key={v.id}
          vertex={v}
          onClick={() => onVertexClick?.(v.id)}
          clickable={activeTool === "settlement" || activeTool === "city"}
        />
      ))}
    </svg>
  )
}

function HexTile({ hex }: { hex: HexDTO }) {
  const points = hex.corners.map(([x, y]) => `${x},${y}`).join(" ")
  return (
    <g>
      <polygon
        points={points}
        fill={terrainColor(hex.terrain)}
        stroke="#555"
        strokeWidth={1}
      />
      {hex.number && (
        <text x={hex.x} y={hex.y} textAnchor="middle" dominantBaseline="middle"
              fontSize={18} fill={hex.number === 6 || hex.number === 8 ? "red" : "black"}>
          {hex.number}
        </text>
      )}
    </g>
  )
}
```

### 11.6 App State Management

```tsx
// web/src/App.tsx
import { useState, useEffect } from 'react'
import { fetchState, fetchLayout, postCommand } from './api'
import { useGameSocket } from './useGameSocket'
import { Board } from './components/Board'

function GameView({ gameId }: { gameId: string }) {
  const [state, setState] = useState<GameStateDTO | null>(null)
  const [layout, setLayout] = useState<LayoutDTO | null>(null)
  const [activeTool, setActiveTool] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  
  // Load initial data
  useEffect(() => {
    Promise.all([fetchState(gameId), fetchLayout(gameId)])
      .then(([s, l]) => { setState(s); setLayout(l) })
      .catch(e => setError(e.message))
  }, [gameId])
  
  // Live updates via WebSocket
  useGameSocket(gameId, setState)
  
  const apply = async (command: object) => {
    try {
      setError(null)
      const newState = await postCommand(gameId, command)
      setState(newState)
    } catch (e: any) {
      setError(e.message)
    }
  }
  
  const handleVertexClick = (vertexId: number) => {
    if (!state) return
    if (activeTool === "settlement") {
      apply({ type: "BuildSettlement", pid: state.current_player, vertex_id: vertexId })
    } else if (activeTool === "city") {
      apply({ type: "BuildCity", pid: state.current_player, vertex_id: vertexId })
    }
  }
  
  if (!state || !layout) return <div>Loading...</div>
  
  return (
    <div className="game-view">
      {error && <div className="error-banner">{error}</div>}
      <Board
        layout={layout}
        onVertexClick={handleVertexClick}
        onEdgeClick={(i) => apply({ type: "BuildRoad", pid: state.current_player, edge_index: i })}
        activeTool={activeTool}
      />
      <ActionsPanel state={state} onApply={apply} activeTool={activeTool} setActiveTool={setActiveTool} />
      <Players state={state} />
    </div>
  )
}
```

### 11.7 Vite Dev Proxy

Configure Vite to forward `/api` requests to your Python backend:

```typescript
// web/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,  // Enable WebSocket proxying
      }
    }
  }
})
```

With this, running `npm run dev` starts a dev server at `localhost:5173` that transparently proxies API calls to your Python server at `localhost:8000`.

### Phase 6 Checkpoint

- [ ] The board renders 19 hexes with correct terrain colors
- [ ] Clicking a vertex in settlement-placement mode sends the correct API command
- [ ] The error banner appears for invalid moves and disappears on the next action
- [ ] Opening two browser tabs: an action in one tab updates both within 1 second
- [ ] Commit: `"Phase 6: React frontend with SVG board and WebSocket updates"`

---

## 12. Phase 7 — Metrics & Analytics

> **Goal:** Compute and display post-game statistics.

> **Branch:** `git checkout -b phase-7-metrics`

### 12.1 Projections Over Event Streams

A **projection** is a function that reads the event stream and computes a derived view. Unlike the reducer (which tracks live state), projections are read-only and can be computed from the full history at any time.

```python
# catan/engine/projections.py
from dataclasses import dataclass, field

@dataclass
class PlayerMetrics:
    pid: str
    dice_roll_counts: dict[int, int] = field(default_factory=dict)    # {total: count}
    actual_production: dict[str, int] = field(default_factory=dict)   # {resource: total}
    expected_production: dict[int, float] = field(default_factory=dict)  # per roll number
    steals_given: int = 0
    steals_received: int = 0
    trades_with_bank: int = 0
    trades_with_players: int = 0
    build_timeline: list[tuple[int, str]] = field(default_factory=list)  # [(turn, structure)]
    vp_timeline: list[tuple[int, int]] = field(default_factory=list)    # [(turn, vp_total)]

@dataclass
class GameMetrics:
    players: dict[str, PlayerMetrics]
    dice_histogram: dict[int, int]  # {total: count} across all rolls
    total_turns: int
```

**Luck Score:** The difference between what a player actually produced and what probability says they *should* have produced, given their settlements' pip values.

```python
def compute_luck_score(actual: dict, expected: dict) -> float:
    """
    Positive = luckier than expected.
    Negative = unluckier than expected.
    """
    actual_total = sum(actual.values())
    expected_total = sum(expected.values())
    return actual_total - expected_total
```

**Computing expected production:** For each settlement/city a player has at turn T, look up the pip value of each adjacent hex. Each pip represents 1/36 probability of producing per roll.

```python
def expected_per_turn(settlements: set[int], cities: set[int], board: Board, topology) -> float:
    total_pips = 0.0
    for vid in settlements:
        for coord in topology.vertex_hexes[vid]:
            if board.numbers.get(coord):
                total_pips += PIPS[board.numbers[coord]] / 36.0
    for vid in cities:
        for coord in topology.vertex_hexes[vid]:
            if board.numbers.get(coord):
                total_pips += 2 * PIPS[board.numbers[coord]] / 36.0
    return total_pips
```

### 12.2 Metrics API Endpoint

```python
@app.get("/api/games/{game_id}/metrics")
def get_metrics(game_id: str):
    events = store.load_events(game_id)
    state_at_each_roll = ...  # you need to reconstruct state at each roll to compute expected production
    metrics = compute_metrics(events, board)
    return metrics_to_dto(metrics)
```

### 12.3 Frontend Charts

For charts, use a simple bar chart with SVG — no external library needed:

```tsx
function DiceHistogram({ histogram }: { histogram: Record<number, number> }) {
  const max = Math.max(...Object.values(histogram))
  const rolls = [2,3,4,5,6,7,8,9,10,11,12]
  
  return (
    <svg width="400" height="200">
      {rolls.map((n, i) => {
        const count = histogram[n] ?? 0
        const barHeight = max > 0 ? (count / max) * 150 : 0
        const x = i * 35 + 20
        const y = 160 - barHeight
        return (
          <g key={n}>
            <rect x={x} y={y} width={25} height={barHeight}
                  fill={n === 6 || n === 8 ? "#e55" : "#68a"} />
            <text x={x + 12} y={175} textAnchor="middle" fontSize={12}>{n}</text>
            {count > 0 && (
              <text x={x + 12} y={y - 4} textAnchor="middle" fontSize={11}>{count}</text>
            )}
          </g>
        )
      })}
    </svg>
  )
}
```

### Phase 7 Checkpoint

- [ ] After a complete game, `/api/games/{id}/metrics` returns valid JSON
- [ ] Dice histogram counts match what was actually rolled
- [ ] Luck score: a player who rolled 6/8 repeatedly with pip-rich positions shows positive luck
- [ ] VP timeline has the correct number of data points (one per turn)
- [ ] Commit: `"Phase 7: Game metrics and analytics projections"`

---

## 13. Phase 8 — Testing Strategy

> **Goal:** Build a test suite that verifies correctness and catches regressions.

> **Branch:** `git checkout -b phase-8-tests`

### 13.1 The Testing Pyramid

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
- **Unit tests:** Test `validate()`, `reduce()`, `awards.py`, `projections.py` in isolation
- **Integration tests:** Test `GameService` with a real SQLite database (`:memory:`)
- **API tests:** Test the FastAPI app with `httpx.AsyncClient`

### 13.2 Unit Tests: Validation

```python
# tests/test_validate.py
import pytest
from catan.domain.commands import BuildSettlement, RollDice
from catan.domain.constants import Resource, Phase
from catan.engine.validate import validate
from tests.fixtures import make_game_state  # helper you write

def test_build_settlement_valid():
    state = make_game_state(phase=Phase.SETUP)
    cmd = BuildSettlement(pid="alice", vertex_id=0)
    result = validate(state, cmd, strict=True)
    assert result.ok
    assert any(type(e).__name__ == "SettlementBuilt" for e in result.events)

def test_build_settlement_violates_distance_rule():
    state = make_game_state(phase=Phase.SETUP)
    # Place a settlement at vertex 0 for alice
    state.players["alice"].settlements.add(0)
    # Vertex 1 is adjacent to vertex 0 — this should fail
    cmd = BuildSettlement(pid="bob", vertex_id=1)  # vertex 1 is adjacent
    result = validate(state, cmd, strict=True)
    assert not result.ok
    assert "distance" in result.errors[0].lower()

def test_cannot_roll_twice():
    state = make_game_state(phase=Phase.PLAY, has_rolled=True)
    cmd = RollDice(pid="alice", d1=3, d2=4)
    result = validate(state, cmd, strict=True)
    assert not result.ok
```

### 13.3 Unit Tests: Reducer Invariants

```python
# tests/test_reduce.py

def total_resources(state: GameState) -> dict[Resource, int]:
    total = dict(state.bank)
    for p in state.players.values():
        for r, n in p.resources.items():
            total[r] = total.get(r, 0) + n
    return total

INITIAL_RESOURCES = {
    Resource.WOOD: 19,
    Resource.BRICK: 19,
    Resource.WHEAT: 19,
    Resource.SHEEP: 19,
    Resource.ORE: 19,
}

def test_resource_conservation_across_roll():
    state = make_game_state(phase=Phase.PLAY)
    cmd = RollDice(pid="alice", d1=3, d2=4)
    new_state, _ = execute(state, cmd)
    assert total_resources(new_state) == INITIAL_RESOURCES

def test_reduce_is_pure():
    state = make_game_state(phase=Phase.SETUP)
    original_id = id(state)
    new_state = reduce(state, SettlementBuilt(pid="alice", vertex_id=5))
    assert id(new_state) != original_id  # new object
    assert 5 not in state.players["alice"].settlements  # original unchanged
    assert 5 in new_state.players["alice"].settlements  # new state has change
```

### 13.4 API Tests

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from catan.api.app import create_app
from catan.store.repository import GameService
from catan.store.event_store import EventStore

@pytest.fixture
def client():
    svc = GameService(EventStore(":memory:"))
    app = create_app(svc)
    return TestClient(app)

def test_create_and_fetch_game(client):
    response = client.post("/api/games", json={
        "players": ["alice", "bob", "charlie"],
        "board": "standard",
        "mode": "dev"
    })
    assert response.status_code == 201
    game_id = response.json()["game_id"]
    
    state_response = client.get(f"/api/games/{game_id}/state")
    assert state_response.status_code == 200
    state = state_response.json()
    assert state["phase"] == "setup"
    assert set(state["player_order"]) == {"alice", "bob", "charlie"}

def test_invalid_command_returns_400(client):
    game_id = create_test_game(client, ["alice", "bob"])
    response = client.post(f"/api/games/{game_id}/commands", json={
        "type": "BuildSettlement",
        "pid": "bob",  # not bob's turn
        "vertex_id": 0
    })
    assert response.status_code == 400
```

### 13.5 Test Fixtures

Create a `tests/fixtures.py` with helper functions that build valid test states:

```python
# tests/fixtures.py
from catan.domain.state import GameState, PlayerState
from catan.domain.constants import Resource, Phase
from catan.domain.board import build_standard_board

def make_game_state(
    players: list[str] | None = None,
    phase: Phase = Phase.SETUP,
    has_rolled: bool = False,
    current_index: int = 0,
) -> GameState:
    """Build a minimal valid GameState for testing."""
    if players is None:
        players = ["alice", "bob"]
    board = build_standard_board()
    player_states = {
        pid: PlayerState(
            pid=pid,
            resources={r: 0 for r in Resource},
            dev_cards=[], dev_cards_played=[],
            knights_played=0,
            settlements=set(), cities=set(), roads=set(),
            bonus_vp=0,
        )
        for pid in players
    }
    return GameState(
        board=board,
        player_order=players,
        players=player_states,
        phase=phase,
        current_index=current_index,
        turn_number=1,
        dice=None,
        has_rolled=has_rolled,
        bank={r: 19 for r in Resource},
        dev_deck=[],
        robber=...,  # desert coord
        longest_road_holder=None,
        largest_army_holder=None,
        winner=None,
        pending_discards={},
        robber_pending=False,
        dev_played_this_turn=False,
        dev_bought_this_turn=False,
    )
```

### 13.6 Coverage

```bash
pytest --cov=catan --cov-report=term-missing

# Example output:
# catan/domain/constants.py    100%
# catan/engine/validate.py      87%   (missing lines 145-148)
```

Coverage tells you which lines of code are executed by tests. 80% is a reasonable minimum. 100% is hard and not always meaningful. Focus on **testing behavior, not lines**.

### Phase 8 Checkpoint

- [ ] `pytest` passes with 0 failures
- [ ] Coverage ≥ 80% across `catan/engine/` and `catan/store/`
- [ ] Every validation rule has at least one test for the valid case and one for the invalid case
- [ ] Resource conservation invariant test covers at least: roll, build, bank trade, player trade
- [ ] API tests cover: create game, fetch state, valid command, invalid command, 404
- [ ] Commit: `"Phase 8: Comprehensive test suite with 80%+ coverage"`

---

## 14. Phase 9 — Polish & Delivery

> **Goal:** Make the application production-ready and prepare your final submission.

> **Branch:** `git checkout -b phase-9-polish`

### 14.1 README.md

Your README is the front door to your project. It must answer these questions for a stranger who just found your repo:

```markdown
# Catan Companion

A digital companion for tracking physical Settlers of Catan games.

## Features
- Real-time board state with rule enforcement
- Post-game metrics: luck scores, dice histograms, production analytics
- WebSocket live sync across all connected browsers
- Time-travel: replay any historical game state

## Setup

### Requirements
- Python 3.11+
- Node.js 20+

### Installation
\`\`\`bash
# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# Frontend
cd web && npm install
\`\`\`

### Running
\`\`\`bash
# Terminal 1: Backend
catan serve

# Terminal 2: Frontend
cd web && npm run dev
\`\`\`

Open http://localhost:5173

## Architecture
[Brief description + link to design/architecture.md]

## Running Tests
\`\`\`bash
pytest --cov=catan
\`\`\`
```

### 14.2 Design Document

Your `design/` directory should contain:

- `requirements.md` — Problem statement and user stories
- `architecture.md` — System diagram and component descriptions
- `decisions.md` — Architectural decisions and why you made them (ADRs)
- `tasks.md` — Your project task history

**Architecture Decision Records (ADRs)** are short documents explaining *why* you made a design choice. Template:

```markdown
# ADR-001: Use Event Sourcing for Game Persistence

## Context
We need to store game state across server restarts.

## Options Considered
1. Store current state snapshot: simple, but no history, no time travel
2. Store all events: more complex, enables time travel, full audit log, better analytics
3. Store both (current state + events): redundant but fast reads

## Decision
We chose option 2 (event sourcing only, with periodic snapshots for performance).

## Consequences
- State replay required after server restart (mitigated by snapshots)
- Any bug in the reducer affects historical replay
- Post-game analytics can be computed from event stream without touching live state
```

Write an ADR for each significant design choice you made.

### 14.3 Error Handling Review

Go through your code and check:
- Every `except Exception` should be more specific
- Every `HTTPException(500)` should be `HTTPException(400)` with a user-facing message where possible
- The API should never return a Python traceback to the browser
- Database errors should be logged and surface a generic "internal error" to the API

### 14.4 Performance Considerations

- If snapshot interval is too high (e.g., every 100 events), loading state after 500 events could take a noticeable time. Keep it ≤ 25.
- The layout computation (hex-to-pixel conversion) runs on every `GET /layout` call. This is a pure function of the board — consider caching it.
- The frontend rerenders on every WebSocket message. This is fine for typical game sizes (< 50 components).

### 14.5 Security Considerations

- The API does **not** authenticate users. Anyone who knows a `game_id` can submit commands for any player. For a companion app played with friends on a local network, this is acceptable. For a public server, you would add session tokens.
- SQLite has no network exposure — it's a local file. Safe for single-machine deployment.
- Command inputs are validated by the game engine. An attacker cannot corrupt game state by sending malformed JSON — FastAPI will reject it before it reaches your code.

### 14.6 Live Demo Preparation

Your 15-minute demo should show:
1. (2 min) Quick tour of the architecture diagram — explain the layers
2. (3 min) Start a new game and show setup phase (placing first settlements and roads)
3. (3 min) Main game: roll dice, collect resources, build
4. (3 min) Two browser tabs: show both updating in real time
5. (2 min) Post-game metrics screen
6. (2 min) Questions

**Practice at least twice before the demo.** The most common failure mode is "it worked on my laptop."

### Phase 9 Checkpoint

- [ ] `README.md` lets a classmate run the app from scratch in under 10 minutes
- [ ] `design/` directory has all four files
- [ ] At least 3 ADRs written
- [ ] No Python tracebacks leak to the browser
- [ ] Final test run: `pytest` passes, coverage ≥ 80%
- [ ] Final commit: `"Phase 9: Documentation and polish for final submission"`
- [ ] Create a git tag: `git tag v1.0.0 && git push origin v1.0.0`

---

## 15. Grading Rubric

| Category | Points | Criteria |
|---|---|---|
| **Planning artifacts** | 15 | Requirements doc, architecture diagram, 3+ ADRs, task history |
| **Domain models** | 10 | Correct enums, immutable dataclasses, complete types |
| **Game engine** | 20 | Validates all standard Catan rules; reducer is pure; resource conservation invariant holds |
| **Persistence** | 10 | Events survive server restart; time travel works; snapshots reduce load time |
| **CLI** | 5 | REPL plays a full game; invalid commands give helpful errors |
| **REST API** | 10 | Correct HTTP status codes; WebSocket broadcasts; proper error responses |
| **Frontend** | 15 | Board renders correctly; clicking places buildings/roads; real-time updates visible |
| **Metrics** | 5 | Dice histogram, luck score, at least 2 other metrics |
| **Test suite** | 10 | ≥80% coverage; tests for valid AND invalid cases; integration tests |
| **README** | 5 | Stranger can run the app following only the README |
| **Live demo** | 10 | Working end-to-end; handles edge cases smoothly; explains design choices |
| **Penalty** | -5 | Per phase skipped or incomplete at the time of grading |
| **Total** | **115** | (15 extra credit points possible) |

### Extra Credit Opportunities (up to 15 points)

- **Custom board designer** (5 pts): Browser UI to enter your physical board layout tile-by-tile
- **Dev mode sandbox** (3 pts): Toggle that bypasses rule enforcement for testing/replay
- **Historical replay scrubber** (4 pts): UI slider to time-travel through game history
- **Port handling** (3 pts): Enforce 2:1 and 3:1 port trading rates

---

## 16. Appendix A — Catan Rules Reference

### Setup Phase
1. Players take turns in order placing one settlement and one road
2. Then in **reverse** order, each player places their second settlement and road
3. The second settlement triggers immediate resource collection from adjacent hexes

### Main Game Turn Order
1. **Roll dice** (mandatory, first action)
2. If 7: activate robber (player must move robber; if anyone has > 7 cards, they discard half)
3. If not 7: all players with settlements/cities adjacent to hexes matching the roll collect resources
4. **Trade** (optional): bank trade (usually 4:1, or 2:1/3:1 with ports); player trades
5. **Build** (optional): roads, settlements, cities, dev cards
6. **Play dev card** (optional, one per turn, not one bought this turn)
7. **End turn**

### Victory Conditions
- First to 10 victory points wins
- VP sources: settlements (1 each), cities (2 each), VP dev cards (1 each), Longest Road (2), Largest Army (2)
- Longest Road: ≥ 5 continuous roads, can be taken by another player who builds longer
- Largest Army: ≥ 3 knights played, can be taken by another player who plays more

### Resource Bank
- 19 of each resource (wood, brick, wheat, sheep, ore)
- Dev card deck: 14 knights, 5 VP, 2 road building, 2 year of plenty, 2 monopoly = 25 total

---

## 17. Appendix B — Hex Grid Mathematics

### Axial Coordinate System

A hex grid can be addressed with two coordinates (q, r). Think of them as two axes tilted 60 degrees from each other.

```
         (-1,-1)   (0,-1)   (1,-1)
       (-1, 0)   (0, 0)   (1, 0)
         (-1, 1)   (0, 1)   (1, 1)
```

### Six Directions

Moving from a hex to its 6 neighbors:
```
(+1,  0)  → East
(-1,  0)  → West
( 0, +1)  → South-East
( 0, -1)  → North-West
(+1, -1)  → North-East
(-1, +1)  → South-West
```

### Axial to Pixel (Flat-Top Hexagons)

```
x = size × (3/2 × q)
y = size × (√3/2 × q + √3 × r)
```

### Corner Positions

For a flat-top hex centered at (cx, cy) with outer radius `size`:
```
Corner i (0..5): angle = 60° × i
x_corner = cx + size × cos(angle)
y_corner = cy + size × sin(angle)
```

### Standard Catan Board Layout

The 19 land hexes in a standard Catan board form a hexagonal shape with rings of sizes 1, 6, 12:

```python
STANDARD_HEXES = [
    # Center
    Coord(0, 0),
    # Ring 1
    Coord(1, 0), Coord(0, 1), Coord(-1, 1),
    Coord(-1, 0), Coord(0, -1), Coord(1, -1),
    # Ring 2
    Coord(2, 0), Coord(1, 1), Coord(0, 2),
    Coord(-1, 2), Coord(-2, 2), Coord(-2, 1),
    Coord(-2, 0), Coord(-1, -1), Coord(0, -2),
    Coord(1, -2), Coord(2, -2), Coord(2, -1),
]
```

### Vertex Identification

A vertex is shared by up to 3 hexes. For flat-top hexes, two adjacent hexes share exactly 2 corners. To find all unique vertices:

1. For each hex, compute all 6 corner pixel positions (rounded to avoid float precision issues)
2. Group corners by position — each unique position is one vertex
3. Assign integer IDs starting from 0
4. Record which hexes share each vertex (for the `vertex_hexes` adjacency map)

---

## 18. Appendix C — Recommended Reading

### Required Background
- [Python Dataclasses](https://docs.python.org/3/library/dataclasses.html) — Official docs, read the whole page
- [Python Enums](https://docs.python.org/3/library/enum.html) — Focus on `Enum` and `auto()`
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/) — Complete the "First Steps" through "Path Parameters" and "Request Body"
- [React: Thinking in React](https://react.dev/learn/thinking-in-react) — The definitive mental model

### Deeper Reading (for strong students)
- [Hexagonal Grids Guide](https://www.redblobgames.com/grids/hexagons/) — Amit Patel's definitive reference on hex math; covers axial, cube, and offset coordinates with interactive demos
- [Event Sourcing Explained](https://martinfowler.com/eaaDev/EventSourcing.html) — Martin Fowler's original article
- [Functional Core, Imperative Shell](https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell) — Gary Bernhardt's talk on architectural purity
- [The Twelve-Factor App](https://12factor.net/) — Industry-standard principles for building deployable software
- [Writing Good Tests](https://martinfowler.com/bliki/UnitTest.html) — Martin Fowler on what a unit test actually is

### Tools Reference
- [SQLite Documentation](https://www.sqlite.org/lang.html) — SQL syntax reference
- [MDN SVG Reference](https://developer.mozilla.org/en-US/docs/Web/SVG/Element) — Every SVG element
- [pytest Documentation](https://docs.pytest.org/) — Fixtures, parametrize, and coverage
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/) — Types, interfaces, generics

---

*Capstone Lab Guide v1.0 — CS 499 Senior Capstone in Software Engineering*  
*Total estimated time: 120–160 hours across a 16-week semester*
