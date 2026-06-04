# CLI reference

The `catan` command is a stdlib-`argparse` front end over `GameService`. It is
installed as a console script (`uv run catan …`) or runnable as
`python -m catan …`.

## Global options

```
catan [--db PATH] <subcommand> [...]
```

- `--db PATH` — SQLite file to use. Defaults to the `CATAN_DB` environment
  variable, else `catan.db`. Use a real file (not the default `:memory:` of the
  API) so games persist.

If a subcommand references a game id that doesn't exist, the CLI prints a helpful
error and hints at `catan games`.

## Subcommands

| Command | Purpose |
| --- | --- |
| `new` | Create a game |
| `games` | List stored games |
| `state` | Show state, optionally time-traveled |
| `board` | Show the board |
| `delete` | Delete a game |
| `log` | Print the event stream |
| `replay` | Re-fold all events and check integrity |
| `metrics` | Quick metrics (dice histogram, VP, pip equity, luck) |
| `play` | Interactive REPL to drive a game |
| `serve` | Run the HTTP/WebSocket API |

### `new`

```
catan new [--players red,blue,white] [--board standard|random|custom]
          [--seed N] [--layout FILE]
```

- `--players` — comma-separated ids (2–4, must be unique).
- `--board` — `standard` (reproducible), `random` (shuffled, legal), or
  `custom`.
- `--seed` — RNG seed for `--board random` (reproducible shuffles).
- `--layout FILE` — required for `--board custom`; a JSON file:

  ```json
  {
    "terrain": ["forest", "hills", ...19 in spiral order...],
    "numbers": [5, 2, 6, ...18 in spiral order, skipping the desert...],
    "ports":   ["generic", "brick", ...9 optional, perimeter order...]
  }
  ```

Prints the new `game_id`, the board, and the command to start playing.

### `state`

```
catan state <game_id> [--at SEQ] [--show-board]
```

- `--at SEQ` — time-travel: rebuild the state as of (inclusive) sequence `SEQ`.
- `--show-board` — also render the board.

### `board`, `delete`, `log`

```
catan board  <game_id>      # render terrain + numbers + robber + ports
catan delete <game_id>      # remove the game and its events/snapshots
catan log    <game_id>      # seq, event type, and fields (board payload elided)
```

### `replay`

```
catan replay <game_id>
```

Re-folds all events and verifies conservation (resources total 19 each;
dev cards deck+held+played match). Prints `replay OK …` or lists the broken
invariants and exits non-zero.

### `metrics`

```
catan metrics <game_id> [--json]
```

Text mode prints a dice histogram (observed vs. expected) and per-player
production, luck, trades, robber stats, dev cards, and builds. `--json` emits the
full `GameMetrics.to_dict()` structure (the same shape the API returns).

### `serve`

```
catan serve [--host 127.0.0.1] [--port 8000]
```

Runs the FastAPI app via uvicorn against the `--db`. See [api.md](api.md).

### `play` — the REPL

```
catan play <game_id>
```

Opens an interactive prompt that shows the board, the state, and whose turn it
is. The **acting player is inferred** from the game (the current player in play,
the expected player in setup), so you type as little as possible. Each line is
parsed into a command and applied; rejected commands print the reasons and the
game stays alive.

Meta commands inside the REPL: `state`, `board`, `log`, `help`, `quit`/`exit`/`q`.

## REPL command grammar

The parser is deliberately forgiving and accepts synonyms
(`wood`/`sheep`/`wheat`/`clay`/`rock`/`ore`, `soldier` for knight, `yop` for year
of plenty, etc.).

```
setup:  settlement <v>            road <e>
turn:   roll <d1> <d2>            end
build:  build road <e>           build settlement <v>      build city <v>
dev:    buy <card>               play knight <q,r> [victim [res]]
        play road <e1> [e2]      play yop <res> <res>       play monopoly <res>
seven:  discard <player> <res:n,...>     robber <q,r> [victim [res]]
trade:  trade bank <give> <n> <recv> <n>
        trade player <partner> <give:n,...> <recv:n,...>
meta:   state   board   log   help   quit
```

Notes:

- `<v>` = vertex id, `<e>` = edge id, `<q,r>` = hex axial coordinate.
- Resource maps use `name:count` and commas, e.g. `brick:2,ore:1`. A bare name
  means 1.
- `roll` takes the two physical dice you actually rolled.
- For `robber`/`play knight`, the victim and stolen resource are optional — omit
  them if there is no one to steal from.

### Example session

```
red> settlement 10
red> road 14
blue> settlement 29
blue> road 41
white> settlement 19
white> road 25
white> settlement 42        # snake draft reverses for the second placement
white> road 53
blue> settlement 7
blue> road 9
red> settlement 33
red> road 44
red> roll 3 4               # play phase begins
red> build road 15
red> end
blue> roll 6 1
...
```

## See also

- The commands and events behind the grammar: [domain-model.md](domain-model.md)
- The rules enforced on each command: [engine.md](engine.md)
