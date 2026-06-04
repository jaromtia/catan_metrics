# Phase 4 — CLI Interface

> **Goal:** Build a command-line interface to play and inspect games without a browser.
>
> **Branch:** `git checkout -b phase-4-cli`

---

## 4.1 Why CLI First?

A CLI lets you test the full game flow interactively before building the frontend. If the engine has bugs, you'll find them faster at the command line than through a web UI.

---

## 4.2 Subcommands

**`catan/cli/main.py`**

```python
import argparse
import os

def main(argv=None):
    parser = argparse.ArgumentParser(prog="catan", description="Catan Companion")
    parser.add_argument(
        "--db", default=os.environ.get("CATAN_DB", "catan.db"),
        help="SQLite database path (default: $CATAN_DB or catan.db)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # catan new --players alice bob charlie --board standard
    new_p = sub.add_parser("new", help="Start a new game")
    new_p.add_argument("--players", nargs="+", required=True)
    new_p.add_argument("--board", choices=["standard", "random"], default="standard")
    new_p.add_argument("--mode", choices=["strict", "dev"], default="strict")

    # catan games
    sub.add_parser("games", help="List all games")

    # catan state <game-id> [--at SEQ]
    state_p = sub.add_parser("state", help="Print current game state")
    state_p.add_argument("game_id")
    state_p.add_argument("--at", type=int, default=None, metavar="SEQ",
                         help="Show state at this event sequence number")

    # catan board <game-id>
    board_p = sub.add_parser("board", help="Print board layout")
    board_p.add_argument("game_id")

    # catan log <game-id>
    log_p = sub.add_parser("log", help="Print event log")
    log_p.add_argument("game_id")

    # catan replay <game-id>  (validates conservation invariants)
    replay_p = sub.add_parser("replay", help="Replay and validate event log")
    replay_p.add_argument("game_id")

    # catan metrics <game-id> [--json]
    metrics_p = sub.add_parser("metrics", help="Show post-game metrics")
    metrics_p.add_argument("game_id")
    metrics_p.add_argument("--json", action="store_true")

    # catan play <game-id>
    play_p = sub.add_parser("play", help="Play in interactive REPL mode")
    play_p.add_argument("game_id")

    # catan delete <game-id>
    delete_p = sub.add_parser("delete", help="Delete a game")
    delete_p.add_argument("game_id")

    # catan serve [--host HOST] [--port PORT]
    serve_p = sub.add_parser("serve", help="Start the web server")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)
    svc  = GameService(EventStore(args.db))

    dispatch = {
        "new":     cmd_new,
        "games":   cmd_games,
        "state":   cmd_state,
        "board":   cmd_board,
        "log":     cmd_log,
        "replay":  cmd_replay,
        "metrics": cmd_metrics,
        "play":    cmd_play,
        "delete":  cmd_delete,
        "serve":   cmd_serve,
    }
    dispatch[args.command](svc, args)
```

> **`CATAN_DB` environment variable:** Both the CLI (`--db`) and the API server read this env var as the default database path. Set it once per session to avoid specifying `--db` every command.
> ```bash
> export CATAN_DB=my_game.db
> uv run catan new --players alice bob charlie
> ```

---

## 4.3 The `replay` Command

This command replays the full event log and verifies conservation invariants — a useful sanity check:

```python
def cmd_replay(svc: GameService, args):
    state, _ = svc.state(args.game_id)
    events   = svc._store.load_events(args.game_id)

    # Replay from scratch.
    from catan.engine.reduce import apply_all
    replayed = apply_all(events)

    # Check resource conservation: bank + all players = 19 per resource.
    for r in Resource:
        total = replayed.bank.get(r, 0)
        total += sum(p.resources.get(r, 0) for p in replayed.players.values())
        if total != BANK_RESOURCE_COUNT:
            print(f"CONSERVATION VIOLATION: {r.value} total={total} (expected 19)")
            sys.exit(1)

    # Check dev card conservation.
    for card in DevCard:
        in_deck  = replayed.dev_deck.get(card, 0)
        in_hands = sum(p.dev_cards.get(card, 0) for p in replayed.players.values())
        played   = sum(p.dev_cards_played.get(card, 0) for p in replayed.players.values())
        if in_deck + in_hands + played != DEV_CARD_COUNTS[card]:
            print(f"DEV CARD VIOLATION: {card.value}")
            sys.exit(1)

    print(f"OK — {len(events)} events replayed, all invariants hold")
```

---

## 4.4 The REPL

A **REPL** (Read-Evaluate-Print Loop) is an interactive prompt:

```
alice> roll 3 4
Rolled 7. Discard required: bob (4 cards).
alice> robber 0,1 bob lumber
Robber moved to (0,1). Stole 1 lumber from bob.
alice> build road 5
Built road at edge 5.
alice> end
Turn ended. bob's turn.
bob> state
Phase: play  Turn: 2  Current: bob  Rolled: no
  alice:  3 VP | brick:0 lumber:1 wool:0 grain:0 ore:0
  bob:    2 VP | brick:1 lumber:0 wool:2 grain:1 ore:0
Bank: brick:15 lumber:16 wool:15 grain:16 ore:19
```

```python
def cmd_play(svc: GameService, args):
    game_id = args.game_id
    print(f"Playing game {game_id}. Type 'help' for commands, 'quit' to exit.")

    while True:
        state, _ = svc.state(game_id)
        actor = _current_actor(state)
        prompt = f"{actor}> "

        try:
            line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not line:
            continue
        if line in ("quit", "exit", "q"):
            break
        if line == "help":
            print(HELP)
            continue
        if line == "state":
            print(render_state(state))
            continue
        if line == "board":
            print(render_board(state))
            continue
        if line == "log":
            events = svc._store.load_events(game_id)
            for i, e in enumerate(events):
                print(f"  {i:3d}  {type(e).__name__}")
            continue

        try:
            cmd = build_command(state, line)
        except ParseError as e:
            print(f"Parse error: {e}")
            continue

        result = svc.try_apply(game_id, cmd)
        if result.ok:
            for event in result.events:
                print(render_event(event))
        else:
            print(f"Invalid: {'; '.join(result.errors)}")
```

---

## 4.5 Command Parser

**`catan/cli/parser.py`**

The parser infers the acting player from game state — no need to type your name every command.

```python
from catan.domain.commands import *
from catan.domain.constants import Resource, DevCard

# Synonym maps: what the CLI accepts → what the engine uses.
_RES: dict[str, Resource] = {
    "brick":  Resource.BRICK,
    "lumber": Resource.LUMBER, "wood": Resource.LUMBER,
    "wool":   Resource.WOOL,   "sheep": Resource.WOOL,
    "grain":  Resource.GRAIN,  "wheat": Resource.GRAIN,
    "ore":    Resource.ORE,
}

_DEV: dict[str, DevCard] = {
    "knight":  DevCard.KNIGHT, "soldier": DevCard.KNIGHT,
    "road":    DevCard.ROAD_BUILDING, "roads": DevCard.ROAD_BUILDING,
    "yop":     DevCard.YEAR_OF_PLENTY, "plenty": DevCard.YEAR_OF_PLENTY,
    "monopoly": DevCard.MONOPOLY,
    "vp":      DevCard.VICTORY_POINT,
}

class ParseError(ValueError):
    pass

def build_command(state: GameState, line: str) -> Command:
    """
    Parse a REPL text line into a Command, inferring the acting player.
    Raises ParseError on unrecognized input.
    """
    parts = line.lower().split()
    if not parts:
        raise ParseError("Empty command")
    verb = parts[0]

    if state.phase == Phase.SETUP:
        return _parse_setup(state, verb, parts)

    actor = state.current_player

    if verb == "roll" and len(parts) == 3:
        d1, d2 = int(parts[1]), int(parts[2])
        return RollDice(pid=actor, d1=d1, d2=d2)

    if verb == "end":
        return EndTurn(pid=actor)

    if verb == "build" and len(parts) >= 3:
        what = parts[1]
        loc  = int(parts[2])
        if what == "road":
            return BuildRoad(pid=actor, edge_index=loc)
        if what == "settlement":
            return BuildSettlement(pid=actor, vertex_id=loc)
        if what == "city":
            return BuildCity(pid=actor, vertex_id=loc)

    if verb == "buy":
        # "buy knight", "buy yop", etc. — requires specifying which card
        if len(parts) < 2:
            raise ParseError("buy requires a card name: buy <knight|road|yop|monopoly|vp>")
        card = _DEV.get(parts[1])
        if card is None:
            raise ParseError(f"Unknown dev card: {parts[1]}")
        return BuyDevCard(pid=actor, card=card)

    if verb == "robber" and len(parts) >= 2:
        coord  = _hex(parts[1])
        victim = parts[2] if len(parts) > 2 else None
        res    = _RES.get(parts[3]) if len(parts) > 3 else None
        return MoveRobber(pid=actor, coord=coord, victim=victim, resource=res)

    if verb == "discard" and len(parts) >= 2:
        resources = _resmap(" ".join(parts[1:]))
        return Discard(pid=actor, resources=resources)

    if verb == "trade" and len(parts) >= 2:
        return _parse_trade(actor, parts[1:])

    if verb == "play" and len(parts) >= 2:
        return _parse_play(actor, parts[1:])

    raise ParseError(f"Unknown command: {line!r}")


def _hex(s: str) -> tuple[int, int]:
    """Parse 'q,r' string to Coord tuple."""
    q, r = s.split(",")
    return (int(q), int(r))


def _resmap(s: str) -> dict[Resource, int]:
    """Parse 'brick:2,wool:1' or 'brick wool' into a resource dict."""
    result: dict[Resource, int] = {}
    for token in s.replace(",", " ").split():
        if ":" in token:
            name, count = token.split(":")
            result[_RES[name]] = int(count)
        else:
            r = _RES.get(token)
            if r:
                result[r] = result.get(r, 0) + 1
    return result
```

---

## 4.6 Text Renderer

**`catan/cli/render.py`**

```python
def render_state(state: GameState) -> str:
    rolled = f"dice:{state.dice[0]+state.dice[1]}" if state.dice else "not rolled"
    lines  = [f"Phase: {state.phase.value}  Turn: {state.turn_number}  "
              f"Current: {state.current_player}  {rolled}"]
    if state.robber_pending:
        lines.append("  ⚠ Robber must be placed!")
    if state.pending_discards:
        for pid, count in state.pending_discards.items():
            lines.append(f"  ⚠ {pid} must discard {count} cards")
    lines.append("")
    for pid in state.player_order:
        p   = state.players[pid]
        res = "  ".join(f"{r.value}:{p.resources.get(r,0)}" for r in Resource)
        vp  = state.victory_points(pid, include_hidden=True)
        lines.append(f"  {pid:10s}  {vp} VP  {res}  "
                     f"S:{len(p.settlements)} C:{len(p.cities)} "
                     f"R:{len(p.roads)} K:{p.knights_played}")
    bank = "  ".join(f"{r.value}:{state.bank.get(r,0)}" for r in Resource)
    lines.append(f"\nBank: {bank}")
    return "\n".join(lines)
```

---

## Phase 4 Checkpoint

- [ ] `uv run catan new --players alice bob charlie` creates a game and prints the ID
- [ ] `uv run catan play <id>` enters the REPL
- [ ] Full setup phase playable via CLI: `settlement 0`, `road 1`, etc.
- [ ] Roll dice, collect resources, build, end turn — all working
- [ ] Invalid commands print helpful error messages (not tracebacks)
- [ ] `uv run catan replay <id>` reports "OK" after a valid game
- [ ] `uv run catan serve` starts uvicorn (implement the server in Phase 5 first)
- [ ] Commit: `"Phase 4: CLI REPL and text command parser"`
