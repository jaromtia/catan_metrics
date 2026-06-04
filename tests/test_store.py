"""Persistence: codec round-trips, append/reload, replay==live, snapshots."""

from catan.domain import commands as cmd
from catan.domain import events as ev
from catan.domain.board import standard_board
from catan.domain.constants import Resource, DevCard
from catan.engine.validate import execute
from catan.store.codec import (
    decode_board,
    decode_event,
    decode_state,
    encode_board,
    encode_event,
    encode_state,
)
from catan.store.event_store import EventStore
from catan.store.repository import GameService

PLAYERS = ("red", "blue", "white")


def pick_nonadjacent(topo, count):
    forbidden, chosen = set(), []
    for v in sorted(topo.vertices):
        if v in forbidden:
            continue
        chosen.append(v)
        forbidden.add(v)
        forbidden |= topo.vertex_neighbors[v]
        if len(chosen) == count:
            break
    return chosen


def setup_commands(board):
    snake = list(PLAYERS) + list(reversed(PLAYERS))
    verts = pick_nonadjacent(board.topology, 2 * len(PLAYERS))
    out = []
    for player, v in zip(snake, verts, strict=True):
        out.append(cmd.PlaceSetupSettlement(player=player, vertex=v))
        out.append(cmd.PlaceSetupRoad(player=player, edge=next(iter(board.topology.vertex_edges[v]))))
    return out


# --- codec round-trips -----------------------------------------------------

def test_board_round_trips():
    board = standard_board()
    again = decode_board(encode_board(board))
    assert again == board


def test_state_round_trips():
    board = standard_board()
    state, _ = execute(None, cmd.CreateGame(board=board, player_order=PLAYERS))
    for c in setup_commands(board):
        state, _ = execute(state, c)
    state, _ = execute(state, cmd.RollDice(player="red", die1=5, die2=3))
    assert decode_state(encode_state(state)) == state


def test_every_event_type_round_trips():
    board = standard_board()
    h = next(iter(board.numbers))
    samples = [
        ev.GameCreated(board=board, player_order=PLAYERS),
        ev.SetupSettlementPlaced(player="red", vertex=3),
        ev.SetupRoadPlaced(player="red", edge=2),
        ev.DiceRolled(player="red", die1=4, die2=2),
        ev.TurnEnded(player="red"),
        ev.DiscardedToRobber(player="red", resources={Resource.BRICK: 2}),
        ev.RobberMoved(player="red", hex=h),
        ev.ResourceStolen(player="red", victim="blue", resource=Resource.ORE),
        ev.DomesticTrade(player="red", partner="blue",
                         gave={Resource.WOOL: 1}, received={Resource.ORE: 1}),
        ev.MaritimeTrade(player="red", gave={Resource.BRICK: 4},
                         received={Resource.ORE: 1}, ratio=4),
        ev.RoadBuilt(player="red", edge=7),
        ev.SettlementBuilt(player="red", vertex=9),
        ev.CityBuilt(player="red", vertex=9),
        ev.DevCardBought(player="red", card=DevCard.KNIGHT),
        ev.KnightPlayed(player="red", hex=h, victim="blue", resource=Resource.WOOL),
        ev.KnightPlayed(player="red", hex=h),
        ev.RoadBuildingPlayed(player="red", edges=(1, 2)),
        ev.YearOfPlentyPlayed(player="red", resources=(Resource.ORE, Resource.GRAIN)),
        ev.MonopolyPlayed(player="red", resource=Resource.WOOL),
        ev.VictoryPointRevealed(player="red"),
    ]
    for e in samples:
        assert decode_event(encode_event(e)) == e, e


# --- event store -----------------------------------------------------------

def test_append_and_reload_events_match():
    board = standard_board()
    store = EventStore()
    store.create_game("g1")
    events = [ev.GameCreated(board=board, player_order=PLAYERS),
              ev.SetupSettlementPlaced(player="red", vertex=0)]
    store.append("g1", events)
    loaded = [se.event for se in store.load_events("g1")]
    assert loaded == events


def test_replay_matches_live_state():
    board = standard_board()
    svc = GameService()
    game_id = svc.create_game(cmd.CreateGame(board=board, player_order=PLAYERS))
    live = None
    for c in setup_commands(board):
        live, _ = svc.apply(game_id, c)
    live, _ = svc.apply(game_id, cmd.RollDice(player="red", die1=6, die2=2))
    rebuilt = svc.state(game_id)
    assert rebuilt == live


def test_snapshot_reconstruction_matches_full_replay():
    board = standard_board()
    store = EventStore()
    svc = GameService(store)
    game_id = svc.create_game(cmd.CreateGame(board=board, player_order=PLAYERS))
    for c in setup_commands(board):
        svc.apply(game_id, c)
    state_after_setup = svc.state(game_id)

    # Force a snapshot at the current head, then add one more event.
    head = store._max_seq(game_id)
    store.save_snapshot(game_id, head, state_after_setup)
    live, _ = svc.apply(game_id, cmd.RollDice(player="red", die1=3, die2=2))

    # load_state must use the snapshot + replay the tail and match the live state.
    assert svc.state(game_id) == live


def test_time_travel_to_earlier_sequence():
    board = standard_board()
    store = EventStore()
    svc = GameService(store)
    game_id = svc.create_game(cmd.CreateGame(board=board, player_order=PLAYERS))
    states = []
    for c in setup_commands(board):
        s, _ = svc.apply(game_id, c)
        states.append(s)
    # State as of the very first setup settlement (seq 1) should match.
    assert svc.state(game_id, up_to=1) == states[0]
