"""CLI parser and an end-to-end drive through GameService."""

from catan.domain import commands as cmd
from catan.domain.board import standard_board
from catan.domain.constants import Resource
from catan.domain.state import GameState, Phase
from catan.cli.parser import build_command
from catan.engine.validate import execute, setup_expectation
from catan.store.event_store import EventStore
from catan.store.repository import GameService

PLAYERS = ("red", "blue", "white")


def play_state():
    s = GameState.new(standard_board(), list(PLAYERS))
    s.phase = Phase.PLAY
    s.has_rolled = True
    return s


def setup_state():
    s, _ = execute(None, cmd.CreateGame(board=standard_board(), player_order=PLAYERS))
    return s


def test_setup_parsing_infers_player():
    s = setup_state()
    assert build_command(s, "settlement 0") == cmd.PlaceSetupSettlement(player="red", vertex=0)


def test_play_command_parsing():
    s = play_state()
    cases = {
        "roll 5 3": cmd.RollDice(player="red", die1=5, die2=3),
        "end": cmd.EndTurn(player="red"),
        "build road 7": cmd.BuildRoad(player="red", edge=7),
        "build settlement 9": cmd.BuildSettlement(player="red", vertex=9),
        "build city 9": cmd.BuildCity(player="red", vertex=9),
        "buy": cmd.BuyDevCard(player="red"),
        "reveal": cmd.RevealVictoryPoint(player="red"),
        "play road 1 2": cmd.PlayRoadBuilding(player="red", edges=(1, 2)),
        "play monopoly wool": cmd.PlayMonopoly(player="red", resource=Resource.WOOL),
        "play yop ore grain": cmd.PlayYearOfPlenty(
            player="red", resources=(Resource.ORE, Resource.GRAIN)
        ),
        "robber 1,-1": cmd.MoveRobber(player="red", hex=(1, -1)),
        "discard blue ore:4": cmd.Discard(player="blue", resources={Resource.ORE: 4}),
        "trade bank brick 4 ore 1": cmd.TradeWithBank(
            player="red", give=Resource.BRICK, give_amount=4,
            receive=Resource.ORE, receive_amount=1,
        ),
        "trade player blue wool:1 ore:1": cmd.TradeWithPlayer(
            player="red", partner="blue",
            gave={Resource.WOOL: 1}, received={Resource.ORE: 1},
        ),
    }
    for line, expected in cases.items():
        assert build_command(s, line) == expected, line


def test_play_knight_with_victim():
    s = play_state()
    got = build_command(s, "play knight 1,-1 blue ore")
    assert got == cmd.PlayKnight(player="red", hex=(1, -1), victim="blue", resource=Resource.ORE)


def test_resource_synonyms():
    s = play_state()
    got = build_command(s, "play yop wood sheep")
    assert got == cmd.PlayYearOfPlenty(player="red", resources=(Resource.LUMBER, Resource.WOOL))


def test_end_to_end_setup_through_parser():
    svc = GameService(EventStore())
    game_id = svc.create_game(cmd.CreateGame(board=standard_board(), player_order=PLAYERS))

    # Drive the whole setup using the text parser + service.
    topo = standard_board().topology
    forbidden, verts = set(), []
    for v in sorted(topo.vertices):
        if v in forbidden:
            continue
        verts.append(v)
        forbidden.add(v)
        forbidden |= topo.vertex_neighbors[v]
    vi = 0
    last_vertex = None
    while True:
        state = svc.state(game_id)
        exp = setup_expectation(state)
        if exp is None:
            break
        kind, _ = exp
        if kind == "settlement":
            last_vertex = verts[vi]
            vi += 1
            result = svc.try_apply(game_id, build_command(state, f"settlement {last_vertex}"))
        else:
            edge = next(iter(topo.vertex_edges[last_vertex]))
            result = svc.try_apply(game_id, build_command(state, f"road {edge}"))
        assert result.ok, result.errors

    final = svc.state(game_id)
    assert final.phase is Phase.PLAY
