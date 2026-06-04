# Persistence

The `catan/store/` package makes games durable. The event log is the source of
truth; snapshots are a replay optimization. Everything is stored in a single
SQLite file (or `:memory:` for ephemeral runs).

| Module | Responsibility |
| --- | --- |
| `event_store.py` | `EventStore`: append-only log + snapshots over SQLite |
| `codec.py` | JSON (de)serialization of events, boards, state, and commands |
| `repository.py` | `GameService`: the façade used by the CLI and API |

## Schema (`event_store.py`)

Three tables:

```sql
games(    game_id PK, created_at )
events(   game_id, seq, ts, type, payload,  PRIMARY KEY (game_id, seq) )
snapshots(game_id, seq, state,               PRIMARY KEY (game_id, seq) )
```

- **`events`** is append-only. Each row is one event: a monotonically increasing
  `seq` within a game, a timestamp, the event type name, and the JSON `payload`.
- **`snapshots`** stores the full encoded `GameState` at periodic sequence
  numbers, so replay doesn't always start from zero.

## Append & sequence numbers

`append(game_id, events)` assigns the next sequence numbers
(`MAX(seq) + 1` for the game), encodes each event to JSON, inserts them in one
`executemany`, commits, and returns the last assigned `seq`. Appends are atomic
per call.

## Rebuilding state — `load_state`

```python
load_state(game_id, up_to=None)   # up_to = inclusive sequence ceiling
```

1. Determine the ceiling: the latest sequence, or `up_to` for time travel.
2. Find the latest snapshot at or before the ceiling.
3. Start from that snapshot (or `None` if there is none) and `reduce` the tail of
   events up to the ceiling.

This is what powers `catan state <id> --at <seq>` and the web history scrubber:
pass `up_to` to reconstruct the game exactly as it was at any point.

## Snapshots

`SNAPSHOT_INTERVAL = 25`. After an append, the caller asks
`should_snapshot(seq)`; when true, it saves the freshly computed state via
`save_snapshot`. Snapshots are purely an optimization — deleting them only makes
replay slower, never wrong, because the event log remains the source of truth.

## Codec (`codec.py`)

Everything is converted to plain JSON-serializable dicts so it can live in
SQLite text columns.

- **Board** — `encode_board` / `decode_board`. The board's **topology is never
  stored**: vertex/edge ids derive deterministically from the (canonically
  sorted) hex set, so the codec stores only board *content* (hexes, terrain,
  numbers, ports, robber) and rebuilds the topology on load, yielding identical
  ids. Pips are recomputed from the numbers.
- **State** — `encode_state` / `decode_state` for snapshots: players, bank,
  dev deck, phase, turn flags, awards, winner, etc.
- **Events** — `encode_event` / `decode_event`, one branch per event type. The
  CLI/API strip the large `board` payload from `GameCreated` when printing logs.
- **Commands** — `decode_command` only (clients submit commands as JSON; the
  server never needs to *encode* a command). Coordinate keys are stored as
  `"q,r"` strings; resource and dev-card maps key by their enum `.value`.

## `GameService` (`repository.py`)

The high-level façade. The CLI and API deal in commands and states, never in raw
events or SQL.

| Method | What it does |
| --- | --- |
| `create_game(CreateGame)` | validates, creates the game row, appends `GameCreated`, returns a new `game_id` (uuid4 hex) |
| `state(game_id, up_to=None)` | rebuilds state (optionally time-traveled) |
| `apply(game_id, command)` | validate → persist events → reduce → maybe snapshot; **raises** on rejection; returns `(new_state, events)` |
| `try_apply(game_id, command)` | like `apply` but returns the `Result` instead of raising (used by the REPL and API so they can report errors gracefully) |
| `list_games()` / `delete_game(id)` | catalog management |

The store opens SQLite with `check_same_thread=False` so the FastAPI app can use
it across the request/WebSocket tasks. Reads use `sqlite3.Row` for name-based
access.

## Integrity checking

`catan replay <id>` rebuilds state and asserts conservation laws hold:

- every resource totals `BANK_RESOURCE_COUNT` (19) across the bank and all hands;
- every development card's `deck + held + played` equals its original deck count.

If either fails, replay reports exactly which invariant broke — a strong signal
that an event was mis-recorded or the reducer has a bug.

## See also

- What the reducer does with each event: [engine.md](engine.md)
- The interfaces that call `GameService`: [cli.md](cli.md), [api.md](api.md)
