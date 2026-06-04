# Architecture

Catan Metrics is an **event-sourced** application. This document explains that
model, the layered package design, how data flows through a command, and the
invariants the design relies on.

## Event sourcing in one paragraph

Nothing in this system stores "current state" as the source of truth. Instead,
the source of truth is an **append-only log of events** — immutable facts about
what happened (`DiceRolled`, `SettlementBuilt`, `ResourceStolen`, …). The
current game state is computed by *folding* (reducing) the event log from the
beginning. Because state is a pure function of events:

- The game is **fully replayable** — replay the log and you always get the same
  state.
- You can **time-travel** — fold only the first *N* events to see the game as it
  was at any point.
- The log is **auditable** — every change is an explicit, named event.
- State representation can change without migrations — only the (small) event
  schema matters.

## The layers

The package is split so that pure logic never depends on I/O. Dependencies only
point downward.

```
        ┌─────────────────────────────────────────────┐
        │  Interfaces:   cli/        api/               │   I/O, user-facing
        └───────────────┬───────────────┬──────────────┘
                        │               │
        ┌───────────────▼───────────────▼──────────────┐
        │  store/   (EventStore, GameService, codec)    │   persistence
        └───────────────┬──────────────────────────────┘
                        │
        ┌───────────────▼──────────────────────────────┐
        │  engine/  (validate, reduce, awards, projn.)  │   pure logic
        └───────────────┬──────────────────────────────┘
                        │
        ┌───────────────▼──────────────────────────────┐
        │  domain/  (geometry, board, events, commands, │   pure data
        │            constants, state)                  │
        └───────────────────────────────────────────────┘
```

- **`domain/`** — Plain, mostly-frozen dataclasses and enums. Geometry, board
  content, the event and command catalogs, and the `GameState` model. No logic
  beyond pure helpers. See [domain-model.md](domain-model.md).
- **`engine/`** — The rules. `validate` turns a command into events (or
  errors); `reduce` folds an event into a new state; `awards` computes Longest
  Road / Largest Army; `projections` derives metrics. All pure functions. See
  [engine.md](engine.md).
- **`store/`** — Durability. An append-only SQLite event log with periodic
  snapshots, a JSON codec, and `GameService`, the façade the interfaces use. See
  [persistence.md](persistence.md).
- **`cli/`** and **`api/`** — The two interfaces. They decode input into
  commands, call `GameService`, and render/serialize the result. See
  [cli.md](cli.md) and [api.md](api.md).

## Commands vs. events

This distinction is central:

- A **command** expresses *intent* — "build a settlement at vertex 23". Commands
  are the only thing the outside world submits. They can be **rejected**.
- An **event** records *what happened* — "SettlementBuilt at vertex 23". Events
  are immutable facts that have already passed validation.

The validator is the bridge: `validate(state, command) -> Result`. On success
the `Result` carries one or more events; on failure it carries human-readable
error strings and no events. A single command may expand into **several** events
(e.g. `MoveRobber` produces `RobberMoved` and possibly `ResourceStolen`).

## Data flow of a single command

```
client (CLI/web)
   │  submit command (typed or JSON)
   ▼
GameService.apply / try_apply
   │  1. load current state  (snapshot + tail of events)
   ▼
engine.validate(state, command)
   │  2. legal?  ──no──▶ Result(ok=False, errors=[…])  ─▶ rejected to client
   │  yes
   ▼  Result(ok=True, events=[…])
EventStore.append(events)          3. persist (atomic, assigns seq numbers)
   │
   ├─▶ engine.reduce over events    4. compute the new state
   │       └─▶ maybe save snapshot  (every SNAPSHOT_INTERVAL events)
   ▼
new state returned to client
   └─▶ (API only) broadcast new state to all WebSocket clients for live update
```

## The deterministic-consequence rule

Events store only what cannot be derived; everything the reducer can recompute
from `state + event` is **not** stored. Examples:

- `DiceRolled` carries only the two dice. Resource **production** is derived by
  the reducer from the board and current buildings.
- `MonopolyPlayed` carries only the chosen resource. The **transfer amounts**
  are derived.
- Longest Road / Largest Army holders, win detection, and bank movements are all
  recomputed in the reducer, never stored on events.

This keeps the log minimal and guarantees replay determinism: there is exactly
one way the state can evolve from a given event.

## Key invariants

- **State is never mutated in place.** `reduce` clones the state, mutates the
  clone, and returns it. The immutable `Board` is *shared* across clones (its
  topology dictionaries are large and never change mid-game).
- **Only the acting player can win, and only on their own turn.** If a move
  hands an award to a third player who thereby reaches 10 VP, the win is detected
  when that player next acts — matching the official rules.
- **Conservation holds.** Across the bank and all hands, each resource always
  totals 19; development cards (deck + held + played) always total their deck
  counts. `catan replay` checks exactly this.
- **Topology is derived, not stored.** Vertex and edge ids come from sorting the
  hex set canonically, so they are reproducible. The codec stores board
  *content* and rebuilds the topology on load, yielding identical ids.

## Where to go next

- The data types every layer shares: [domain-model.md](domain-model.md)
- How rules are enforced and metrics computed: [engine.md](engine.md)
- How the log is stored and replayed: [persistence.md](persistence.md)
