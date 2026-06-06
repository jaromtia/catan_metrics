"""``catan`` command-line entry point (argparse, stdlib only).

Subcommands:
  new       create a game (standard or random board)
  games     list stored games
  state     show state, optionally time-traveled with --at
  board     show the board
  log       print the event stream
  replay    re-fold all events and check integrity
  metrics   quick metrics (dice histogram, VP, pip equity)
  play      interactive REPL to drive a game
"""

from __future__ import annotations

import argparse
import os
import sys

from ..domain import commands as cmd
from ..domain.board import custom_board, random_board, standard_board
from ..domain.constants import BANK_RESOURCE_COUNT, DEV_DECK_SIZE, Resource, DevCard
from ..engine.projections import compute_metrics
from ..store.codec import encode_event
from ..store.event_store import EventStore, UnknownGame
from ..store.repository import GameService
from .parser import HELP, ParseError, build_command
from .render import render_board, render_metrics, render_state

DEFAULT_DB = os.environ.get("CATAN_DB", "catan.db")


def _service(args) -> GameService:
    return GameService(EventStore(args.db))


def _make_board(args):
    if args.board == "random":
        import random
        return random_board(random.Random(args.seed))
    if args.board == "custom":
        if not args.layout:
            raise SystemExit("custom board requires --layout FILE (JSON)")
        import json
        with open(args.layout) as f:
            data = json.load(f)
        return custom_board(
            terrains=data["terrain"],
            numbers=data["numbers"],
            port_types=data.get("ports"),
        )
    return standard_board()


def cmd_new(args) -> int:
    svc = _service(args)
    players = tuple(s.strip() for s in args.players.split(","))
    board = _make_board(args)
    game_id = svc.create_game(cmd.CreateGame(board=board, player_order=players))
    print(f"game: {game_id}")
    print(render_board(svc.state(game_id)))
    print(f"\nrun:  catan play {game_id} --db {args.db}")
    return 0


def cmd_games(args) -> int:
    svc = _service(args)
    games = svc.list_games()
    if not games:
        print("(no games)")
    for g in games:
        st = svc.state(g)
        print(f"{g}  phase={st.phase.value} turn={st.turn_number} winner={st.winner}")
    return 0


def cmd_state(args) -> int:
    svc = _service(args)
    state = svc.state(args.game_id, up_to=args.at)
    if args.show_board:
        print(render_board(state))
        print()
    print(render_state(state))
    return 0


def cmd_board(args) -> int:
    svc = _service(args)
    print(render_board(svc.state(args.game_id)))
    return 0


def cmd_delete(args) -> int:
    svc = _service(args)
    svc.delete_game(args.game_id)
    print(f"deleted {args.game_id}")
    return 0


def cmd_log(args) -> int:
    svc = _service(args)
    for stored in svc.store.load_events(args.game_id):
        payload = encode_event(stored.event)
        payload.pop("board", None)  # too large to print inline
        kind = payload.pop("type")
        fields = " ".join(f"{k}={v}" for k, v in payload.items())
        print(f"{stored.seq:>4}  {kind:<22} {fields}")
    return 0


def cmd_replay(args) -> int:
    svc = _service(args)
    state = svc.state(args.game_id)
    errors = []
    for r in Resource:
        total = state.bank[r] + sum(p.resources[r] for p in state.players.values())
        if total != BANK_RESOURCE_COUNT:
            errors.append(f"resource {r.value}: {total} != {BANK_RESOURCE_COUNT}")
    hidden = sum(p.hidden_dev for p in state.players.values())
    revealed = sum(p.dev_cards[c] for p in state.players.values() for c in DevCard)
    played = sum(p.dev_cards_played[c] for p in state.players.values() for c in DevCard)
    if state.dev_deck_size + hidden + revealed + played != DEV_DECK_SIZE:
        errors.append("dev cards: conservation broken")
    if errors:
        print("INTEGRITY FAILED:")
        for e in errors:
            print("  -", e)
        return 1
    print("replay OK — resource and development-card conservation hold")
    print(render_state(state))
    return 0


def cmd_metrics(args) -> int:
    svc = _service(args)
    events = [se.event for se in svc.store.load_events(args.game_id)]
    metrics = compute_metrics(events)
    if args.json:
        import json
        print(json.dumps(metrics.to_dict(), indent=2))
    else:
        print(render_metrics(metrics))
    return 0


def cmd_serve(args) -> int:
    import uvicorn

    from ..api.app import create_app
    app = create_app(_service(args))
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def cmd_play(args) -> int:
    svc = _service(args)
    game_id = args.game_id
    state = svc.state(game_id)
    print(render_board(state))
    print()
    print(render_state(state))
    print("\nType 'help' for commands, 'quit' to exit.")

    while True:
        state = svc.state(game_id)
        try:
            line = input(f"{state.current_player}> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        low = line.lower()
        if low in ("quit", "exit", "q"):
            break
        if low == "help":
            print(HELP)
            continue
        if low == "state":
            print(render_state(state))
            continue
        if low == "board":
            print(render_board(state))
            continue
        if low == "log":
            cmd_log(args)
            continue
        try:
            command = build_command(state, line)
            result = svc.try_apply(game_id, command)
        except ParseError as e:
            print(f"parse error: {e}")
            continue
        except Exception as e:  # noqa: BLE001 - REPL must stay alive
            print(f"error: {e}")
            continue
        if not result.ok:
            print("rejected: " + "; ".join(result.errors))
            continue
        new_state = svc.state(game_id)
        print("ok: " + ", ".join(type(e).__name__ for e in result.events))
        print(render_state(new_state))
        if new_state.winner:
            print(f"\n*** {new_state.winner} wins! ***")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="catan", description="Catan companion engine")
    parser.add_argument("--db", default=DEFAULT_DB, help="SQLite path (default: %(default)s)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="create a game")
    p_new.add_argument("--players", default="red,blue,white")
    p_new.add_argument("--board", choices=["standard", "random", "custom"], default="standard")
    p_new.add_argument("--seed", type=int, default=None)
    p_new.add_argument(
        "--layout",
        help="JSON file for --board custom: {terrain:[..19 spiral..], "
        "numbers:[..18 spiral..], ports?:[..9..]}",
    )
    p_new.set_defaults(func=cmd_new)

    sub.add_parser("games", help="list games").set_defaults(func=cmd_games)

    p_state = sub.add_parser("state", help="show state")
    p_state.add_argument("game_id")
    p_state.add_argument("--at", type=int, default=None, help="time-travel to a sequence")
    p_state.add_argument("--show-board", action="store_true")
    p_state.set_defaults(func=cmd_state)

    p_board = sub.add_parser("board", help="show the board")
    p_board.add_argument("game_id")
    p_board.set_defaults(func=cmd_board)

    p_delete = sub.add_parser("delete", help="delete a game")
    p_delete.add_argument("game_id")
    p_delete.set_defaults(func=cmd_delete)

    p_log = sub.add_parser("log", help="print the event stream")
    p_log.add_argument("game_id")
    p_log.set_defaults(func=cmd_log)

    p_replay = sub.add_parser("replay", help="re-fold events and check integrity")
    p_replay.add_argument("game_id")
    p_replay.set_defaults(func=cmd_replay)

    p_metrics = sub.add_parser("metrics", help="game metrics")
    p_metrics.add_argument("game_id")
    p_metrics.add_argument("--json", action="store_true", help="emit JSON")
    p_metrics.set_defaults(func=cmd_metrics)

    p_play = sub.add_parser("play", help="interactive REPL")
    p_play.add_argument("game_id")
    p_play.set_defaults(func=cmd_play)

    p_serve = sub.add_parser("serve", help="run the HTTP/WebSocket API")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UnknownGame as e:
        print(f"error: no game '{e}' in {args.db}", file=sys.stderr)
        print("hint: list games with:  catan --db "
              f"{args.db} games", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
