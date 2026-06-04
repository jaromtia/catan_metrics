# Catan Metrics

A companion engine for tracking metrics during a **physical** game of Catan. You
play the board game on a real table; this app records every move, enforces the
rules, and turns the game into a stream of analytics — dice luck, pip equity,
production, trades, victory-point timelines, and more.

It is built as an **event-sourced** system: the only thing ever written to disk
is an append-only log of events. All game state and every metric is a pure
function of that log, so the engine is fully replayable, time-travelable, and
auditable.

```
physical game  ─▶  command  ─▶  validate  ─▶  events  ─▶  SQLite log
                                                 │
                                                 ├─▶ reduce ─▶ game state
                                                 └─▶ project ─▶ metrics
```

## Features

- **Full base-game rules engine** — setup snake draft, the distance rule, road
  connectivity (blocked by opponents), build costs, the 7 / robber / discard
  sequence, maritime & domestic trades, all five development cards, Longest Road
  and Largest Army with proper tie handling, and win detection.
- **Three board sources** — a reproducible `standard` board, a rules-legal
  `random` board (6 and 8 never adjacent), or a `custom` board you transcribe
  from the real table on your desk.
- **Event-sourced persistence** — append-only SQLite log with periodic state
  snapshots for fast replay; integrity is verifiable by resource/dev-card
  conservation.
- **Time travel** — rebuild the exact game state as of any sequence number.
- **Metrics & "luck"** — expected vs. actual production from pip equity, dice
  histograms, trade flows, steals, and per-player VP/hand/pip timelines.
- **Three frontends** — a terminal REPL, a CLI, and a live React web UI
  (drag-and-drop board, history scrubber, custom-board designer) backed by a
  FastAPI HTTP + WebSocket server.

## Project layout

```
catan_metrics/
├── catan/                  Python package (the engine)
│   ├── domain/             Pure data: geometry, board, constants, events,
│   │                       commands, and the game-state model
│   ├── engine/             Pure logic: validate, reduce, awards, projections
│   ├── store/              Persistence: SQLite event store, JSON codec, service
│   ├── api/                FastAPI HTTP + WebSocket app
│   ├── cli/                argparse CLI, REPL parser, text renderers
│   └── __main__.py         `python -m catan`
├── web/                    React + TypeScript + Vite frontend
├── tests/                  pytest suite (one file per engine concern)
├── pyproject.toml          Package metadata, deps, console script
└── docs/                   Detailed documentation (see below)
```

## Requirements

- **Python ≥ 3.14** (uses modern `match` statements and typing).
- [**uv**](https://docs.astral.sh/uv/) for Python dependency management.
- **Node ≥ 18** and npm, only if you want the web UI.

## Quickstart

### 1. Install

```bash
cd catan_metrics
uv sync
```

This installs the runtime deps (`fastapi`, `uvicorn`) and the `catan` console
script into the project's virtual environment.

### 2. Play from the terminal

```bash
# Create a game on the standard board with three players.
uv run catan new --players red,blue,white --db game.db

# Drive it interactively (the prompt shows whose turn it is).
uv run catan play <game_id> --db game.db
```

Inside the REPL, type `help` for the command grammar. A minimal turn:

```
red> settlement 10        # setup placements (snake draft)
red> road 14
...
red> roll 4 3             # play phase: roll, then act
red> build settlement 23
red> end
```

### 3. Or run the web UI

```bash
# Terminal 1 — the API (persist to a file so games survive restarts).
CATAN_DB=game.db uv run catan serve

# Terminal 2 — the frontend dev server (proxies /api to :8000).
cd web && npm install && npm run dev
```

Open the printed Vite URL, create a game, and place pieces by dragging from the
palette onto the board.

## Inspecting a game

```bash
uv run catan games                       # list stored games
uv run catan state <id> --show-board     # current state + board
uv run catan state <id> --at 40          # time-travel to sequence 40
uv run catan log <id>                    # print the raw event stream
uv run catan metrics <id>                # luck, dice histogram, per-player stats
uv run catan replay <id>                 # re-fold and check integrity
```

## Testing

```bash
uv run pytest
```

The suite mirrors the engine layers: `test_geometry`, `test_board`,
`test_reduce`, `test_validate`, `test_awards`, `test_projections`, `test_store`,
`test_api`, and `test_cli`.

## Documentation

| Doc | What it covers |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | Event-sourcing model, layered design, data flow, key invariants |
| [docs/domain-model.md](docs/domain-model.md) | Geometry, board generation, constants, events, commands, state model |
| [docs/engine.md](docs/engine.md) | Command validation, the reducer, awards, and metric projections |
| [docs/persistence.md](docs/persistence.md) | SQLite event store, snapshots, JSON codec, the `GameService` |
| [docs/cli.md](docs/cli.md) | Full CLI subcommand and REPL command reference |
| [docs/api.md](docs/api.md) | REST endpoints and the live WebSocket protocol |
| [docs/web.md](docs/web.md) | React frontend architecture and components |
