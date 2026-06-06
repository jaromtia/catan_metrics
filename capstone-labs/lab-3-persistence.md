# Lab 3 — Persistence Layer

> **Goal:** Store game events in SQLite so games survive server restarts, support time travel, and stay fast via snapshots.
>
> **Branch:** `git checkout -b lab-3-persistence`

---

## Background

Traditional databases store *current state*: "Alice has 3 lumber." An **event-sourced** store records every *change*: "Alice gained 2 lumber on turn 1; spent 1 lumber on turn 2."

Benefits: a full audit log, time travel (reconstruct any historical state), analytics over history without touching live state, and easy debugging (the log shows exactly how a state was reached).

The tradeoff: reading current state means replaying all events. You mitigate this with **snapshots** — periodically persist the full state so you only replay the tail since the last snapshot.

---

## Specification

Three modules under `catan/store/`.

### `catan/store/event_store.py`

Define a SQLite schema with three tables:
- `games(game_id PK, created_at, mode)` — `mode` defaults to `'strict'`.
- `events(game_id, seq, ts, type, payload, PRIMARY KEY(game_id, seq))` — `payload` is JSON text.
- `snapshots(game_id, seq, state, PRIMARY KEY(game_id, seq))` — `state` is JSON text.

Define `SNAPSHOT_INTERVAL = 25` and the set of valid modes (`"strict"`, `"dev"`).

Implement an `EventStore` class with at least:

```python
class EventStore:
    def __init__(self, db_path: str = ":memory:"): ...
        # connect (check_same_thread=False), create schema, run any migrations

    def create_game(self, game_id: str, mode: str = "strict") -> None: ...
    def append(self, game_id: str, events: list) -> int:
        """Atomically append a batch. Compute sequence numbers from the current
        MAX(seq) yourself — the caller does NOT pass a starting seq. Return the
        last sequence number written."""
    def should_snapshot(self, seq: int) -> bool: ...
    def save_snapshot(self, game_id: str, seq: int, state: GameState) -> None: ...
    def load_state(self, game_id: str, *, up_to: int | None = None
                  ) -> tuple[GameState, int]:
        """Return (state, seq) at `up_to` (or current if None). Find the latest
        snapshot at or before the target, then replay events after it."""
    def load_events(self, game_id: str) -> list[Event]: ...
    def get_mode(self, game_id: str) -> str: ...
    def list_games(self) -> list[dict]: ...
    def delete_game(self, game_id: str) -> None: ...
```

> **Why `check_same_thread=False`?** FastAPI may touch SQLite from different async tasks. A single connection with this flag is fine here because requests are effectively serialized. A production multi-threaded service would use a pool.

### `catan/store/codec.py`

JSON is the storage format, so you must convert every domain object to/from JSON-safe types.

```python
def encode_event(event) -> dict: ...
def decode_event(type_name: str, payload: dict) -> Event: ...
def encode_state(state: GameState) -> dict: ...
def decode_state(d: dict) -> GameState: ...
def encode_board(board: Board) -> dict: ...
def decode_board(d: dict) -> Board: ...
```

Requirements:
- Round-trip must be lossless for **every** event type and for full `GameState`.
- `decode_board` must **rebuild the topology** by calling `build_topology(hexes)` — the topology is *not* stored in JSON (it is large and fully derivable from the hex list).
- Maintain a `type_name → class` table so `decode_event` can reconstruct the right dataclass.

### `catan/store/repository.py`

`GameService` is the single orchestration entry point used by both the CLI and the API.

```python
class GameService:
    def __init__(self, store: EventStore): ...

    def apply(self, game_id: str, command) -> tuple[GameState, list]:
        """Load state, look up the game's mode (→ strict flag), validate, reduce
        each event, append to the store, snapshot if due. Raise ValueError on an
        invalid command."""

    def try_apply(self, game_id: str, command) -> Result:
        """Same as apply() but return a Result instead of raising (persist on
        success, return the failure Result on an invalid command)."""

    # plus thin pass-throughs: create_game, state, load_events, list_games,
    # get_mode, set_mode, delete_game
```

> **`apply` vs `try_apply`:** the CLI uses `apply` (raising is convenient for a REPL); the API uses `try_apply` (structured errors map to 422 responses).

---

## Your Tasks

1. Implement the schema, `EventStore.__init__`, and any migration logic.
2. Implement `create_game`, `append` (compute seq from `MAX(seq)`), and `should_snapshot`.
3. Implement `save_snapshot` and `load_state` (snapshot lookup + tail replay).
4. Implement `load_events`, `get_mode`, `set_mode`, `list_games`, `delete_game`.
5. Implement the codec: `encode_event`/`decode_event`, `encode_state`/`decode_state`, `encode_board`/`decode_board`.
6. Implement `GameService.apply` and `try_apply`, plus the pass-through methods.

---

## Hints & Pitfalls

Serialization edge cases that will bite you if you skip them:

- A Python `set` is not JSON-serializable → store as a sorted list, restore as a `set`.
- `dict[Resource, int]` keys become strings (`"lumber"`) → restore keys with `Resource(k)`.
- A `frozenset` (vertex/edge keys) → store as a sorted list of lists, restore as `frozenset` of tuples.
- `Coord` is a `tuple[int, int]` → JSON makes it an array → restore with `tuple(...)`.
- A `None` resource (e.g. a steal from an empty hand) must survive as JSON `null` → `None`.
- Nested structures need *recursive* conversion — write a helper that walks dicts/lists and converts enums, sets, and tuples.

Other notes:
- `append` is a *batch* operation and must be atomic (one transaction).
- Snapshot timing: with interval 25 and 0-indexed sequences, a snapshot lands at seq 24, 49, … — make `should_snapshot` agree with this.
- Loading initial state when no snapshot exists: reconstruct from the `GameCreated` event at seq 0.

---

## Tests First

- Create a game, apply 30 events, drop the `EventStore` object, reopen the same DB, reload — the state is byte-for-byte identical.
- Time travel: `load_state(game_id, up_to=10)` returns the state after exactly 10 events.
- A snapshot row exists at the expected sequence after enough events.
- Encode→decode round-trip for **every** event type loses no data.
- `Resource.LUMBER`, `Terrain.FOREST`, etc. survive the codec unchanged.
- `decode_board` produces a board whose topology has 54 vertices and 72 edges (proving it was rebuilt, not stored).

---

## Checkpoint

- [ ] State survives a store restart (reload from disk is identical)
- [ ] Time travel via `up_to` works
- [ ] Snapshot created at the correct interval
- [ ] Round-trip codec for every event type loses nothing
- [ ] `decode_board` rebuilds topology rather than reading it from JSON
- [ ] Commit: `"Lab 3: SQLite event store with snapshot support"`
