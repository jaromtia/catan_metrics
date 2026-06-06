# Lab 4 — CLI Interface

> **Goal:** Build a command-line interface to create, inspect, and play games without a browser.
>
> **Branch:** `git checkout -b lab-4-cli`

---

## Background

A CLI lets you exercise the full game flow interactively before you build the frontend. If the engine has bugs, you will find them faster at a text prompt than through a web UI. The CLI is also where you build the **text command parser**, which the API reuses in Lab 5 — so design it cleanly.

---

## Specification

Three modules under `catan/cli/`.

### `catan/cli/main.py`

Implement `main(argv=None)` using `argparse`. It must support a global `--db` option (defaulting to the `CATAN_DB` environment variable, then `catan.db`) and these subcommands:

| Subcommand | Arguments | Purpose |
|------------|-----------|---------|
| `new` | `--players P...` (required), `--board {standard,random}`, `--mode {strict,dev}` | Create a game, print its id |
| `games` | — | List all games |
| `state` | `game_id`, `--at SEQ` | Print current state (or state at a sequence) |
| `board` | `game_id` | Print the board layout |
| `log` | `game_id` | Print the event log |
| `replay` | `game_id` | Replay the log and verify invariants |
| `metrics` | `game_id`, `--json` | Print post-game metrics (Lab 7) |
| `play` | `game_id` | Enter the interactive REPL |
| `delete` | `game_id` | Delete a game |
| `serve` | `--host`, `--port` | Start the web server (Lab 5) |

Dispatch each subcommand to a handler function. All handlers receive a `GameService` built from the resolved `--db` path.

> **`CATAN_DB`:** both the CLI and the API server read this env var as the default database. Set it once per session to avoid repeating `--db`.

### `catan/cli/parser.py`

```python
class ParseError(ValueError): ...

def build_command(state: GameState, line: str) -> Command:
    """Parse a REPL text line into a Command, inferring the acting player from
    game state (no need to type your name). Raise ParseError on unrecognized
    input. In the setup phase, parse setup-specific verbs."""
```

The parser must accept human synonyms and map them to engine types — e.g. `wood→LUMBER`, `sheep→WOOL`, `wheat→GRAIN`; `soldier→KNIGHT`, `roads→ROAD_BUILDING`, `plenty→YEAR_OF_PLENTY`. Provide helper parsers for hex coordinates (`"q,r"`) and resource maps (`"brick:2,wool:1"` or `"brick wool"`).

You design the exact verb grammar, but at minimum support: `roll d1 d2`, `end`, `build {road|settlement|city} N`, `buy <card>`, `robber q,r [victim] [resource]`, `discard <resources>`, `trade ...`, `play ...`, plus setup placement verbs.

### `catan/cli/render.py`

```python
def render_state(state: GameState) -> str:  # multi-line scoreboard summary
def render_board(state: GameState) -> str:   # textual board view
def render_event(event: Event) -> str:        # one-line human description
```

`render_state` should show phase/turn/current player, any pending discards or robber-placement warning, each player's VP + resources + structure counts, and the bank.

---

## Your Tasks

1. Implement `main` with the argument parser and subcommand dispatch.
2. Implement the simple read-only handlers: `games`, `state`, `board`, `log`, `delete`.
3. Implement `new` (creates a game and prints the id) and `serve` (starts uvicorn — stub it until Lab 5).
4. Implement `render.py` (`render_state`, `render_board`, `render_event`).
5. Implement `build_command` and its synonym/coordinate/resource helpers in `parser.py`.
6. Implement the `play` REPL: loop, read a line, handle meta-commands (`help`, `state`, `board`, `log`, `quit`), otherwise parse and apply via `service.try_apply`, printing rendered events or the error.
7. Implement the `replay` handler: replay the full log with `apply_all`, then assert the conservation invariants (see below) and print `OK` or the violation.

### The `replay` invariants you must check

- **Resource conservation:** for each resource, `bank + sum(player hands) == BANK_RESOURCE_COUNT` (19).
- **Dev card conservation:** for each dev card, `in_deck + in_hands + played == DEV_CARD_COUNTS[card]`.

If any invariant fails, print which one and exit non-zero.

---

## Hints & Pitfalls

- The REPL should infer the acting player from `state.current_player`, so the user never types their name.
- Print friendly parse/validation errors — never let a traceback reach the user.
- Reload state at the top of each REPL iteration so the prompt always reflects reality.
- Keep `build_command` free of side effects (no DB, no I/O). It is pure parsing — that is what makes it reusable by the API and unit-testable.

---

## Tests First

- `build_command` maps synonyms correctly (`wood`→a `BuildRoad`/resource using `LUMBER`, etc.).
- Parsing a malformed line raises `ParseError`, not a generic exception.
- A round trip: parse `"build settlement 0"` → get the right command dataclass with `vertex_id=0`.
- `replay` on a valid game prints `OK`; a deliberately corrupted event list trips an invariant.

---

## Checkpoint

- [ ] `uv run catan new --players alice bob charlie` creates a game and prints the id
- [ ] `uv run catan play <id>` enters the REPL
- [ ] A full setup phase is playable via the REPL
- [ ] Roll, collect, build, end turn all work via text commands
- [ ] Invalid commands print helpful messages (not tracebacks)
- [ ] `uv run catan replay <id>` reports `OK` after a valid game
- [ ] Commit: `"Lab 4: CLI REPL and text command parser"`
