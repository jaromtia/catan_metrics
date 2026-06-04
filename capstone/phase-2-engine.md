# Phase 2 — Game Engine

> **Goal:** Implement the validation and reduction functions that enforce Catan rules.
>
> **Branch:** `git checkout -b phase-2-game-engine`

---

## 2.1 Functional Core Pattern

The game engine is a **pure functional core** — functions that take data and return data, with no side effects.

```
validate(state, command) → Result
reduce(state, event)     → GameState
```

No database access. No HTTP calls. No random numbers. This makes the engine trivially testable: call it with data you constructed, check the output.

---

## 2.2 The Result Type

**`catan/engine/validate.py`**

```python
from dataclasses import dataclass, field
from catan.domain.events import Event

@dataclass
class Result:
    ok:     bool
    events: list[Event]  = field(default_factory=list)
    errors: list[str]    = field(default_factory=list)

    @classmethod
    def success(cls, events: list[Event]) -> "Result":
        return cls(ok=True, events=events)

    @classmethod
    def failure(cls, *errors: str) -> "Result":
        return cls(ok=False, errors=list(errors))
```

---

## 2.3 Strict vs Dev Mode

Every `validate()` call takes a `strict` keyword argument:

```python
def validate(state: GameState, command: Command, *, strict: bool = True) -> Result:
    ...
```

- **strict=True** — all Catan rules enforced (turn order, resource costs, sequence)
- **strict=False** (dev mode) — only structural rules apply (valid vertex IDs, dice 1-6)

Dev mode exists so testers and QA can set up any board position quickly without following the full setup procedure. It's gated per-game via the `mode` field in the database.

---

## 2.4 Validation: Checking If a Move Is Legal

```python
from catan.domain.state import GameState
from catan.domain.commands import (
    Command, BuildSettlement, BuildRoad, RollDice, EndTurn, ...
)

def validate(state: GameState, command: Command, *, strict: bool = True) -> Result:
    """
    Check whether `command` is legal given `state`.
    Returns Result.success(events) or Result.failure(reason).
    """
    match command:
        case RollDice():
            return _v_roll(state, command, strict)
        case BuildSettlement():
            return _v_build_settlement(state, command, strict)
        case BuildRoad():
            return _v_build_road(state, command, strict)
        case PlaceSetupSettlement():
            return _v_setup_settlement(state, command, strict)
        case PlaceSetupRoad():
            return _v_setup_road(state, command, strict)
        case EndTurn():
            return _v_end_turn(state, command, strict)
        # ... one case per command type
        case SetResources() | SetVictoryPoints():
            if strict:
                return Result.failure("Admin commands not allowed in strict mode")
            return _v_admin(state, command)
        case _:
            return Result.failure(f"Unknown command: {type(command).__name__}")
```

### Example: BuildSettlement validator

```python
def _v_build_settlement(state, cmd, strict):
    player = state.players.get(cmd.pid)
    if player is None:
        return Result.failure(f"Unknown player: {cmd.pid}")

    vid = cmd.vertex_id
    topology = state.board.topology

    # Structural checks (always enforced).
    if vid not in topology.vertices:
        return Result.failure(f"Vertex {vid} does not exist")

    for p in state.players.values():
        if vid in p.settlements or vid in p.cities:
            return Result.failure(f"Vertex {vid} is already occupied")

    # Distance rule: no adjacent vertex may have any building.
    for neighbor in topology.vertex_neighbors[vid]:
        for p in state.players.values():
            if neighbor in p.settlements or neighbor in p.cities:
                return Result.failure("Violates distance rule")

    if strict:
        if state.current_player != cmd.pid:
            return Result.failure("Not your turn")
        if state.phase == Phase.PLAY:
            if not _has_road_to(state, cmd.pid, vid):
                return Result.failure("No road connection to this vertex")
            if not _can_afford(player, SETTLEMENT_COST):
                return Result.failure("Insufficient resources")

    events = [SettlementBuilt(pid=cmd.pid, vertex_id=vid)]
    if strict and state.phase == Phase.PLAY:
        events.append(ResourcesSpent(pid=cmd.pid, resources=SETTLEMENT_COST))
    return Result.success(events)
```

### Setup Phase: Snake Draft

The Catan setup follows a **snake draft**: players place in order 1→2→3, then reverse 3→2→1, each placing one settlement + one adjacent road.

```python
def _setup_expectation(state) -> tuple[str, str]:
    """Return (expected_pid, expected_action) for the current setup step."""
    order  = state.player_order
    n      = len(order)
    snake  = order + list(reversed(order))   # [P1, P2, P3, P3, P2, P1]
    # Count total placements already made (settlements + roads).
    placed = sum(len(p.settlements) + len(p.roads) for p in state.players.values())
    idx    = placed // 2   # each player places 1 settlement + 1 road per turn
    phase  = "road" if placed % 2 == 1 else "settlement"
    return snake[idx], phase
```

---

## 2.5 The `execute` Convenience Function

```python
def execute(
    state: GameState, command: Command, *, strict: bool = True
) -> tuple[GameState, list[Event]]:
    """
    Validate and apply a command in one step.
    Raises ValueError if the command is invalid.
    Returns (new_state, events).
    """
    result = validate(state, command, strict=strict)
    if not result.ok:
        raise ValueError("; ".join(result.errors))
    new_state = state
    for event in result.events:
        new_state = reduce(new_state, event)
    return new_state, result.events
```

---

## 2.6 Reduction: Applying an Event to State

The reducer takes a state + event and returns a new state. It must **never** mutate its input, and it **never** raises exceptions (all validation already happened).

**`catan/engine/reduce.py`**

```python
from copy import deepcopy
from catan.domain.state import GameState
from catan.domain.events import Event, SettlementBuilt, RoadBuilt, DiceRolled, ...

def reduce(state: GameState, event: Event) -> GameState:
    """Apply a single event, returning a new state. Never mutates input."""
    s = state.clone()
    _apply(s, event)
    _check_win(s, event)   # detect if the acting player just won
    return s

def _apply(s: GameState, event: Event) -> None:
    """Mutate s in-place to reflect event. Only called on a fresh clone."""
    match event:
        case SettlementBuilt(pid=pid, vertex_id=vid):
            s.players[pid].settlements.add(vid)

        case RoadBuilt(pid=pid, edge_index=eid):
            s.players[pid].roads.add(eid)

        case DiceRolled():
            s.dice = (event.d1, event.d2)
            s.has_rolled = True
            if event.total == 7:
                s.robber_pending = True
                # Mark players who must discard.
                for pid, p in s.players.items():
                    if p.hand_size > ROBBER_DISCARD_THRESHOLD:
                        s.pending_discards[pid] = p.hand_size // 2
            else:
                _apply_production(s, event.total)

        case TurnEnded(pid=pid):
            s.has_rolled = False
            s.dice = None
            s.dev_played_this_turn = False
            s.dev_bought_this_turn = {}
            s.pending_discards = {}
            s.robber_pending = False
            n = len(s.player_order)
            s.current_index = (s.current_index + 1) % n
            if s.current_index == 0:
                s.turn_number += 1

        # ... one case per event type
```

### Resource Production

When the dice show a non-7 total, every player with a settlement or city adjacent to a hex with that number token collects resources.

```python
def _apply_production(s: GameState, total: int) -> None:
    """Grant resources for a dice roll of `total`."""
    from collections import defaultdict
    grants: dict[str, dict[Resource, int]] = defaultdict(lambda: defaultdict(int))

    for coord, number in s.board.numbers.items():
        if number != total:
            continue
        if coord == s.robber:
            continue   # robber blocks this hex
        resource = TERRAIN_RESOURCE[s.board.terrain[coord]]
        if resource is None:
            continue
        for vid in s.board.topology.hex_vertices[coord]:
            for pid, p in s.players.items():
                if vid in p.settlements:
                    grants[pid][resource] += 1
                elif vid in p.cities:
                    grants[pid][resource] += 2

    # Bank shortage rule: if demand exceeds supply for a resource
    # and multiple players compete, nobody gets it.
    for resource in Resource:
        available = s.bank.get(resource, 0)
        total_demand = sum(g.get(resource, 0) for g in grants.values())
        competitors  = [pid for pid, g in grants.items() if g.get(resource, 0) > 0]
        if total_demand > available and len(competitors) > 1:
            for pid in competitors:
                grants[pid].pop(resource, None)
        elif total_demand > available and len(competitors) == 1:
            pid = competitors[0]
            grants[pid][resource] = min(grants[pid][resource], available)

    for pid, res in grants.items():
        for resource, amount in res.items():
            s.players[pid].resources[resource] = (
                s.players[pid].resources.get(resource, 0) + amount
            )
            s.bank[resource] -= amount
```

---

## 2.7 Awards: Longest Road and Largest Army

**`catan/engine/awards.py`**

### Largest Army

Straightforward — first to 3 knights, then strictly exceeded to transfer:

```python
def update_largest_army(state: GameState, player: str) -> str | None:
    """Return the new holder, or current holder if unchanged."""
    p = state.players[player]
    holder = state.largest_army_holder
    if holder is None:
        if p.knights_played >= LARGEST_ARMY_MIN:
            return player
    elif player != holder and p.knights_played > state.players[holder].knights_played:
        return player
    return holder
```

### Longest Road (DFS)

The tricky one. You must find the **longest trail** (each edge used at most once) through a player's roads, where opponent settlements can split the path.

```python
def longest_road_length(state: GameState, pid: str) -> int:
    """DFS to find the longest continuous road for player `pid`."""
    topology = state.board.topology
    roads    = state.players[pid].roads
    if not roads:
        return 0

    # Build adjacency for this player's roads only.
    edges_at: dict[int, set[int]] = {}   # vertex → {edge indices touching it}
    for eid in roads:
        a, b = topology.edge_vertices[eid]
        edges_at.setdefault(a, set()).add(eid)
        edges_at.setdefault(b, set()).add(eid)

    def blocked(vid: int) -> bool:
        """Opponent building on this vertex breaks our road."""
        for other_pid, p in state.players.items():
            if other_pid == pid:
                continue
            if vid in p.settlements or vid in p.cities:
                return True
        return False

    best = 0
    used: set[int] = set()

    def dfs(vertex: int, length: int) -> None:
        nonlocal best
        best = max(best, length)
        for eid in edges_at.get(vertex, set()):
            if eid in used:
                continue
            a, b = topology.edge_vertices[eid]
            next_v = b if a == vertex else a
            if blocked(next_v):
                continue
            used.add(eid)
            dfs(next_v, length + 1)
            used.discard(eid)   # backtrack

    for start_vertex in edges_at:
        dfs(start_vertex, 0)

    return best
```

> **Why DFS with backtracking?**
> Catan roads form a **trail** (each *edge* used once, vertices may repeat). This is different from "longest path" (each *vertex* once). The backtracking DFS correctly finds the longest trail. A simple BFS would give wrong answers.

---

## 2.8 Exercise: Implement `_v_roll`

A dice roll is valid when:
1. Player exists
2. (strict) It's their turn
3. (strict) They haven't already rolled this turn
4. (strict) No pending discards remain
5. Dice values are each 1–6
6. The total equals d1 + d2

What events should a successful roll produce?
- Always: `DiceRolled(pid, d1, d2)`
- If total == 7 and any player has > 7 cards: `DiscardRequired(pid, count)` for each
- If total != 7: production events are NOT separate events — they're derived in the reducer from `DiceRolled`

---

## Phase 2 Checkpoint

- [ ] `validate` returns `Result.failure` for each illegal move you test manually
- [ ] `reduce` never mutates input (verify: `id(state) != id(reduce(state, event))`)
- [ ] `validate(state, cmd, strict=False)` skips turn-order and resource checks
- [ ] Resource totals conserved: `sum(player.resources) + bank == 19 per resource`
- [ ] Longest Road DFS handles cycles and opponent-building splits correctly
- [ ] At least 20 unit tests covering validation rules
- [ ] Commit: `"Phase 2: Game engine with validate and reduce"`
