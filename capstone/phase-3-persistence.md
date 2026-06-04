# Phase 3 — Persistence Layer

> **Goal:** Store game events in SQLite so games survive server restarts.
>
> **Branch:** `git checkout -b phase-3-persistence`

---

## 3.1 Why Event Sourcing?

Traditional databases store current state: "Alice has 3 lumber."

An **event-sourced** store records every change: "Alice gained 2 lumber on turn 1. Alice spent 1 lumber on turn 2."

Benefits:
- Full audit log — every move ever made
- Time travel — reconstruct state at any point in history
- Analytics — run projections over history without touching live state
- Debugging — the log tells you exactly how a state was reached

The tradeoff: reading state requires replaying all events. Mitigated by **snapshots**.

---

## 3.2 SQLite Schema

**`catan/store/event_store.py`**

```python
import sqlite3
import json
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    game_id    TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    mode       TEXT NOT NULL DEFAULT 'strict'
);

CREATE TABLE IF NOT EXISTS events (
    game_id TEXT    NOT NULL,
    seq     INTEGER NOT NULL,
    ts      REAL    NOT NULL,
    type    TEXT    NOT NULL,
    payload TEXT    NOT NULL,
    PRIMARY KEY (game_id, seq),
    FOREIGN KEY (game_id) REFERENCES games(game_id)
);

CREATE TABLE IF NOT EXISTS snapshots (
    game_id TEXT    NOT NULL,
    seq     INTEGER NOT NULL,
    state   TEXT    NOT NULL,
    PRIMARY KEY (game_id, seq),
    FOREIGN KEY (game_id) REFERENCES games(game_id)
);
"""

SNAPSHOT_INTERVAL = 25   # save a snapshot every 25 events
VALID_MODES = ("strict", "dev")
```

> **Why `check_same_thread=False`?**
> FastAPI may call SQLite from different async tasks. A single connection with `check_same_thread=False` works for this app because all requests are effectively serialized by Python's GIL. For a production multi-threaded app you'd use a connection pool.

```python
class EventStore:
    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(SCHEMA)
        self._migrate()   # handle schema additions in older databases

    def _migrate(self) -> None:
        """Add columns added after initial release."""
        cols = {row[1] for row in self._conn.execute("PRAGMA table_info(games)")}
        if "mode" not in cols:
            self._conn.execute("ALTER TABLE games ADD COLUMN mode TEXT NOT NULL DEFAULT 'strict'")
            self._conn.commit()
```

---

## 3.3 Appending Events

```python
    def create_game(self, game_id: str, mode: str = "strict") -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode: {mode!r}")
        self._conn.execute(
            "INSERT INTO games (game_id, created_at, mode) VALUES (?, ?, ?)",
            (game_id, time.time(), mode),
        )
        self._conn.commit()

    def append(self, game_id: str, events: list) -> int:
        """
        Atomically append a batch of events. Returns the last sequence number.
        Sequence numbers are computed from the current max — caller does NOT
        pass starting_seq.
        """
        row = self._conn.execute(
            "SELECT COALESCE(MAX(seq), -1) FROM events WHERE game_id=?",
            (game_id,)
        ).fetchone()
        next_seq = row[0] + 1

        rows = [
            (game_id, next_seq + i, time.time(),
             type(e).__name__, json.dumps(encode_event(e)))
            for i, e in enumerate(events)
        ]
        self._conn.executemany(
            "INSERT INTO events (game_id, seq, ts, type, payload) VALUES (?,?,?,?,?)",
            rows,
        )
        self._conn.commit()
        return next_seq + len(events) - 1

    def should_snapshot(self, seq: int) -> bool:
        return (seq + 1) % SNAPSHOT_INTERVAL == 0
```

---

## 3.4 Loading State with Snapshots

```python
    def load_state(self, game_id: str, *, up_to: int | None = None) -> tuple[GameState, int]:
        """
        Return (state, seq) at up_to (or current if None).
        Strategy: find latest snapshot <= up_to, then replay tail.
        """
        target = up_to if up_to is not None else self._latest_seq(game_id)

        row = self._conn.execute(
            "SELECT seq, state FROM snapshots "
            "WHERE game_id=? AND seq<=? ORDER BY seq DESC LIMIT 1",
            (game_id, target),
        ).fetchone()

        if row:
            start_seq = row[0]
            state = decode_state(json.loads(row[1]))
        else:
            start_seq = -1
            # Load initial state from the GameCreated event.
            state = _initial_state(self, game_id)

        rows = self._conn.execute(
            "SELECT seq, type, payload FROM events "
            "WHERE game_id=? AND seq>? AND seq<=? ORDER BY seq",
            (game_id, start_seq, target),
        ).fetchall()

        for seq, etype, payload in rows:
            event = decode_event(etype, json.loads(payload))
            state = reduce(state, event)

        return state, target

    def save_snapshot(self, game_id: str, seq: int, state: GameState) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO snapshots (game_id, seq, state) VALUES (?,?,?)",
            (game_id, seq, json.dumps(encode_state(state))),
        )
        self._conn.commit()
```

---

## 3.5 Serialization (Codec)

**`catan/store/codec.py`**

Every event type needs an `encode` and `decode` path.

```python
from dataclasses import asdict
from catan.domain.events import *
from catan.domain.constants import Resource, DevCard, Terrain, PortType

def encode_event(event) -> dict:
    """Convert an Event dataclass to a JSON-serializable dict."""
    d = asdict(event)
    return _encode_dict(d)

def _encode_dict(obj):
    """Recursively convert enums/frozensets/tuples to JSON-safe types."""
    if isinstance(obj, dict):
        return {k: _encode_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_encode_dict(v) for v in obj]
    if isinstance(obj, Enum):
        return obj.value
    return obj
```

> **Common serialization pitfalls:**
> - Python `set` → sort and convert to list, restore as `set(...)` on decode
> - `dict[Resource, int]` → keys become `"lumber"` strings, restore with `Resource(k)`
> - `frozenset` → sort and convert to list; restore as `frozenset(tuple(x) for x in list)`
> - `tuple[int, int]` (Coord) → JSON array; restore with `tuple(x)`
> - `None` resource (desert, stolen unknown) → JSON `null`; restore as `None`

Decode is the inverse — match on `type_name` and reconstruct:

```python
def decode_event(type_name: str, payload: dict):
    EVENT_CLASSES = {
        "DiceRolled":           DiceRolled,
        "SettlementBuilt":      SettlementBuilt,
        "RoadBuilt":            RoadBuilt,
        "MaritimeTrade":        MaritimeTrade,
        "KnightPlayed":         KnightPlayed,
        # ... all 21 types
    }
    cls = EVENT_CLASSES[type_name]
    return cls(**_decode_payload(cls, payload))
```

Board encoding: store terrain/numbers/ports as content only. **Do NOT store the topology** — rebuild it from the hex list on decode.

```python
def encode_board(board: Board) -> dict:
    return {
        "hexes":   [[q, r] for q, r in board.topology.hexes],
        "terrain": {"q,r": terrain.value for (q,r), terrain in board.terrain.items()},
        "numbers": {"q,r": n for (q,r), n in board.numbers.items()},
        "ports":   [{"type": p.type.value, "vertices": list(p.vertices)} for p in board.ports],
        "robber":  list(board.robber),
    }

def decode_board(d: dict) -> Board:
    hexes    = [tuple(h) for h in d["hexes"]]
    topology = build_topology(hexes)   # recomputed, not stored
    # ... decode terrain, numbers, ports, robber ...
    return Board(topology=topology, terrain=..., numbers=..., ports=..., robber=...)
```

---

## 3.6 Game Service

The `GameService` is the single entry point for CLI and API — it orchestrates engine + storage.

**`catan/store/repository.py`**

```python
from .event_store import EventStore
from catan.engine.validate import validate, execute
from catan.engine.reduce import reduce

class GameService:
    def __init__(self, store: EventStore):
        self._store = store

    def apply(self, game_id: str, command) -> tuple[GameState, list]:
        """
        Load state, validate command, persist events, return new state.
        Raises ValueError if command is invalid.
        """
        state, current_seq = self._store.load_state(game_id)
        mode   = self._store.get_mode(game_id)
        strict = (mode != "dev")
        result = validate(state, command, strict=strict)
        if not result.ok:
            raise ValueError("; ".join(result.errors))

        new_state = state
        for event in result.events:
            new_state = reduce(new_state, event)

        last_seq = self._store.append(game_id, result.events)
        if self._store.should_snapshot(last_seq):
            self._store.save_snapshot(game_id, last_seq, new_state)

        return new_state, result.events

    def try_apply(self, game_id: str, command) -> Result:
        """
        Same as apply() but returns Result instead of raising.
        Persists on success; returns failure Result on invalid command.
        """
        state, current_seq = self._store.load_state(game_id)
        mode   = self._store.get_mode(game_id)
        strict = (mode != "dev")
        result = validate(state, command, strict=strict)
        if not result.ok:
            return result

        new_state = state
        for event in result.events:
            new_state = reduce(new_state, event)
        last_seq = self._store.append(game_id, result.events)
        if self._store.should_snapshot(last_seq):
            self._store.save_snapshot(game_id, last_seq, new_state)

        return result
```

> **`apply` vs `try_apply`:** The CLI uses `apply` (raises on failure, easier for REPL error display). The API uses `try_apply` (returns structured errors for 422 responses).

---

## Phase 3 Checkpoint

- [ ] Create a game, apply 30 events, reload — state is identical
- [ ] Time travel: `store.load_state(game_id, up_to=10)` returns state after 10 events
- [ ] Snapshot created at seq 24 (interval 25, 0-indexed)
- [ ] Encode + decode round-trip for every event type — no data lost
- [ ] `Resource.LUMBER`, `Terrain.FOREST`, etc. survive the codec round-trip
- [ ] `decode_board` rebuilds topology (not stored in JSON)
- [ ] Commit: `"Phase 3: SQLite event store with snapshot support"`
