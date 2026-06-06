"""Metrics projections over the event stream."""

import math

from catan.domain import events as ev
from catan.domain.board import standard_board
from catan.domain.constants import TERRAIN_RESOURCE, DevCard, Resource, Terrain
from catan.engine.projections import compute_metrics, pip_equity
from catan.engine.reduce import apply_all

PLAYERS = ("red", "blue")


def split(total):
    for a in range(1, 7):
        b = total - a
        if 1 <= b <= 6:
            return a, b
    raise AssertionError(total)


def producing_hex(board):
    for h, num in board.numbers.items():
        if board.terrain[h] is not Terrain.DESERT:
            return h, num
    raise AssertionError


def test_dice_histogram_production_and_luck():
    board = standard_board()
    h, roll = producing_hex(board)
    v = min(board.topology.hex_vertices[h])

    events = [
        ev.GameCreated(board=board, player_order=PLAYERS),
        ev.SetupSettlementPlaced(player="red", vertex=v),
    ]
    before_roll = apply_all(events)
    a, b = split(roll)
    events.append(ev.DiceRolled(player="red", die1=a, die2=b))

    m = compute_metrics(events)
    assert m.dice_histogram[roll] == 1
    assert m.dice_total == 1

    # Production equals red buildings on hexes numbered `roll` (one settlement).
    expected_count = sum(
        1 for hx in board.topology.vertex_hexes[v] if board.numbers.get(hx) == roll
    )
    assert m.players["red"].production_total == expected_count

    expected = pip_equity(before_roll, "red") / 36
    assert math.isclose(m.players["red"].expected_production, expected, rel_tol=1e-9)
    assert math.isclose(
        m.players["red"].luck, expected_count - expected, rel_tol=1e-9, abs_tol=1e-9
    )


def test_discards_and_steals():
    board = standard_board()
    h = next(iter(board.numbers))
    events = [
        ev.GameCreated(board=board, player_order=PLAYERS),
        ev.DiceRolled(player="red", die1=3, die2=4),                 # a 7
        ev.DiscardedToRobber(player="blue", resources={Resource.ORE: 2}),
        ev.RobberMoved(player="red", hex=h),
        ev.ResourceStolen(player="red", victim="blue", resource=Resource.WOOL),
        ev.KnightPlayed(player="red", hex=h, victim="blue", resource=Resource.ORE),
    ]
    m = compute_metrics(events)
    assert m.dice_histogram[7] == 1
    assert m.players["blue"].cards_discarded == 2
    assert m.players["red"].steals_made == 2          # 7-steal + knight-steal
    assert m.players["blue"].cards_stolen_from_me == 2
    assert m.players["red"].knights_played == 1
    assert m.players["red"].dev_played[DevCard.KNIGHT] == 1


def test_trades_and_dev_counts():
    board = standard_board()
    events = [
        ev.GameCreated(board=board, player_order=PLAYERS),
        ev.DomesticTrade(player="red", partner="blue",
                         gave={Resource.WOOL: 1}, received={Resource.ORE: 2}),
        ev.MaritimeTrade(player="red", gave={Resource.BRICK: 4},
                         received={Resource.GRAIN: 1}, ratio=4),
        ev.DevCardBought(player="red"),
        ev.MonopolyPlayed(player="red", resource=Resource.WOOL),
    ]
    m = compute_metrics(events)
    red, blue = m.players["red"], m.players["blue"]
    assert red.trades_domestic == 1 and blue.trades_domestic == 1
    assert red.trades_maritime == 1
    assert red.trade_net[Resource.ORE] == 2
    assert red.trade_net[Resource.WOOL] == -1
    assert red.trade_net[Resource.GRAIN] == 1
    assert red.trade_net[Resource.BRICK] == -4
    assert blue.trade_net[Resource.WOOL] == 1
    assert blue.trade_net[Resource.ORE] == -2
    assert red.dev_bought == 1
    assert red.dev_played[DevCard.MONOPOLY] == 1


def test_vp_timeline_matches_final_state():
    board = standard_board()
    topo = board.topology
    v1 = min(topo.vertices)
    # A far-apart second vertex so nothing odd happens.
    v2 = max(topo.vertices)
    events = [
        ev.GameCreated(board=board, player_order=PLAYERS),
        ev.SetupSettlementPlaced(player="red", vertex=v1),
        ev.SetupSettlementPlaced(player="red", vertex=v2),
        ev.CityBuilt(player="red", vertex=v1),
    ]
    m = compute_metrics(events)
    final = apply_all(events)
    assert m.players["red"].final_vp == final.victory_points("red", include_hidden=True)
    assert m.players["red"].final_vp == 3   # 1 settlement + 1 city
    # Timeline has one entry per event.
    assert len(m.players["red"].vp_timeline) == len(events)


def test_builds_timeline_records_kinds():
    board = standard_board()
    v = min(board.topology.vertices)
    events = [
        ev.GameCreated(board=board, player_order=PLAYERS),
        ev.SetupSettlementPlaced(player="red", vertex=v),
        ev.SetupRoadPlaced(player="red", edge=0),
        ev.CityBuilt(player="red", vertex=v),
    ]
    m = compute_metrics(events)
    kinds = [kind for _, _, kind in m.players["red"].builds]
    assert kinds == ["settlement", "road", "city"]
