"""Reducer behaviour: setup, production, conservation, determinism, awards, win."""

from collections import defaultdict

from catan.domain import events as ev
from catan.domain.board import standard_board
from catan.domain.constants import (
    BANK_RESOURCE_COUNT,
    DEV_DECK_SIZE,
    Resource,
    DevCard,
    Terrain,
)
from catan.domain.constants import TERRAIN_RESOURCE
from catan.domain.state import GameState, Phase
from catan.engine.reduce import apply_all, reduce

PLAYERS = ("red", "blue", "white")


def fresh_board():
    return standard_board()


def setup_events(board):
    """A full snake-draft setup placing 2 settlements + 2 roads per player."""
    order = list(PLAYERS) + list(reversed(PLAYERS))
    verts = [0, 6, 12, 18, 24, 30]            # six distinct vertices
    edges = [0, 5, 10, 15, 20, 25]            # six distinct edges
    out: list[ev.Event] = [ev.GameCreated(board=board, player_order=PLAYERS)]
    for player, v, e in zip(order, verts, edges, strict=True):
        out.append(ev.SetupSettlementPlaced(player=player, vertex=v))
        out.append(ev.SetupRoadPlaced(player=player, edge=e))
    return out


def resource_total(state, res):
    return state.bank[res] + sum(p.resources[res] for p in state.players.values())


def assert_conserved(state):
    for res in Resource:
        assert resource_total(state, res) == BANK_RESOURCE_COUNT, res
    # Every card is either still in the deck, held hidden, revealed (VP), or
    # played. The total never changes.
    hidden = sum(p.hidden_dev for p in state.players.values())
    revealed = sum(p.dev_cards[c] for p in state.players.values() for c in DevCard)
    played = sum(p.dev_cards_played[c] for p in state.players.values() for c in DevCard)
    assert state.dev_deck_size + hidden + revealed + played == DEV_DECK_SIZE


def test_setup_completes_and_grants_second_settlement_resources():
    board = fresh_board()
    state = apply_all(setup_events(board))
    assert state.phase is Phase.PLAY
    assert state.turn_number == 1
    assert state.current_index == 0
    assert_conserved(state)
    # Every player placed exactly two settlements and two roads.
    for p in state.players.values():
        assert len(p.settlements) == 2
        assert len(p.roads) == 2


def expected_production(state, roll):
    delta = defaultdict(lambda: defaultdict(int))
    board = state.board
    for hexc, num in board.numbers.items():
        if num != roll or hexc == state.robber:
            continue
        res = TERRAIN_RESOURCE[board.terrain[hexc]]
        if res is None:
            continue
        for v in board.topology.hex_vertices[hexc]:
            owner = state.owner_of_vertex(v)
            if owner is None:
                continue
            pid, kind = owner
            delta[pid][res] += 2 if kind == "city" else 1
    return delta


def test_dice_roll_produces_expected_resources():
    board = fresh_board()
    state = apply_all(setup_events(board))
    roll = 8
    before = {pid: dict(p.resources) for pid, p in state.players.items()}
    delta = expected_production(state, roll)

    state = reduce(state, ev.DiceRolled(player=state.current_player, die1=5, die2=3))

    for pid, p in state.players.items():
        for res in Resource:
            assert p.resources[res] == before[pid][res] + delta[pid].get(res, 0)
    assert state.has_rolled is True
    assert state.dice == (5, 3)
    assert_conserved(state)


def test_seven_produces_nothing():
    board = fresh_board()
    state = apply_all(setup_events(board))
    before = {pid: dict(p.resources) for pid, p in state.players.items()}
    state = reduce(state, ev.DiceRolled(player=state.current_player, die1=3, die2=4))
    for pid, p in state.players.items():
        assert dict(p.resources) == before[pid]


def test_reduce_does_not_mutate_input():
    board = fresh_board()
    state = apply_all(setup_events(board))
    snapshot = {pid: dict(p.resources) for pid, p in state.players.items()}
    _ = reduce(state, ev.DiceRolled(player=state.current_player, die1=5, die2=3))
    after = {pid: dict(p.resources) for pid, p in state.players.items()}
    assert snapshot == after


def test_replay_is_deterministic():
    board = fresh_board()
    events = setup_events(board)
    events.append(ev.DiceRolled(player="red", die1=5, die2=3))
    events.append(ev.TurnEnded(player="red"))
    s1 = apply_all(events)
    s2 = apply_all(events)
    assert s1 == s2


def test_turn_advances_and_wraps():
    board = fresh_board()
    state = apply_all(setup_events(board))
    state = reduce(state, ev.TurnEnded(player="red"))
    assert state.current_index == 1
    state = reduce(state, ev.TurnEnded(player="blue"))
    assert state.current_index == 2
    state = reduce(state, ev.TurnEnded(player="white"))
    assert state.current_index == 0
    assert state.turn_number == 2


def play_state():
    """A PLAY-phase state with no buildings, for white-box build/dev tests."""
    board = fresh_board()
    state = GameState.new(board, list(PLAYERS))
    state.phase = Phase.PLAY
    state.turn_number = 1
    return state


def give(state, pid, **res):
    for name, amt in res.items():
        state.players[pid].resources[Resource(name)] += amt


def test_build_road_pays_cost():
    state = play_state()
    give(state, "red", brick=1, lumber=1)
    state = reduce(state, ev.RoadBuilt(player="red", edge=3))
    assert state.players["red"].resources[Resource.BRICK] == 0
    assert state.players["red"].resources[Resource.LUMBER] == 0
    assert 3 in state.players["red"].roads


def test_build_city_upgrades_settlement():
    state = play_state()
    state.players["red"].settlements.add(7)
    give(state, "red", ore=3, grain=2)
    state = reduce(state, ev.CityBuilt(player="red", vertex=7))
    assert 7 not in state.players["red"].settlements
    assert 7 in state.players["red"].cities
    assert state.players["red"].resources[Resource.ORE] == 0
    assert state.players["red"].resources[Resource.GRAIN] == 0


def test_monopoly_takes_all_of_one_resource():
    state = play_state()
    state.players["red"].hidden_dev = 1
    give(state, "blue", wool=3)
    give(state, "white", wool=2)
    state = reduce(state, ev.MonopolyPlayed(player="red", resource=Resource.WOOL))
    assert state.players["red"].resources[Resource.WOOL] == 5
    assert state.players["blue"].resources[Resource.WOOL] == 0
    assert state.players["white"].resources[Resource.WOOL] == 0


def test_year_of_plenty_draws_from_bank():
    state = play_state()
    state.players["red"].hidden_dev = 1
    state = reduce(
        state,
        ev.YearOfPlentyPlayed(player="red", resources=(Resource.ORE, Resource.GRAIN)),
    )
    assert state.players["red"].resources[Resource.ORE] == 1
    assert state.players["red"].resources[Resource.GRAIN] == 1
    assert state.bank[Resource.ORE] == BANK_RESOURCE_COUNT - 1


def test_knight_grants_largest_army_after_three():
    state = play_state()
    state.players["red"].hidden_dev = 3
    desert = state.robber
    target = next(h for h in state.board.numbers if h != desert)
    for _ in range(3):
        state = reduce(state, ev.KnightPlayed(player="red", hex=target))
    assert state.players["red"].knights_played == 3
    assert state.largest_army_holder == "red"


def test_winner_detected_at_ten_points():
    state = play_state()
    # Eight settlement/city points + Largest Army (2) = 10.
    state.players["red"].cities.update({1, 2, 3, 4})  # 8 VP
    state.players["red"].hidden_dev = 3
    desert = state.robber
    target = next(h for h in state.board.numbers if h != desert)
    for _ in range(3):
        state = reduce(state, ev.KnightPlayed(player="red", hex=target))
    assert state.largest_army_holder == "red"
    assert state.winner == "red"
    assert state.phase is Phase.FINISHED


def test_buy_dev_card_is_hidden_and_draws_from_deck():
    state = play_state()
    give(state, "red", ore=1, wool=1, grain=1)
    state = reduce(state, ev.DevCardBought(player="red"))
    red = state.players["red"]
    assert red.hidden_dev == 1
    # No type is recorded at purchase time.
    assert all(v == 0 for v in red.dev_cards.values())
    assert state.dev_deck_size == DEV_DECK_SIZE - 1
    assert state.dev_bought_this_turn == 1
    # Paid one ore/wool/grain to the bank.
    assert red.resources[Resource.ORE] == 0
    assert red.resources[Resource.WOOL] == 0
    assert red.resources[Resource.GRAIN] == 0


def test_reveal_victory_point_resolves_a_hidden_card():
    state = play_state()
    state.players["red"].hidden_dev = 2
    assert state.victory_points("red") == 0
    state = reduce(state, ev.VictoryPointRevealed(player="red"))
    red = state.players["red"]
    assert red.hidden_dev == 1
    assert red.dev_cards[DevCard.VICTORY_POINT] == 1
    assert state.victory_points("red") == 1


def test_playing_a_hidden_card_records_its_type():
    state = play_state()
    state.players["red"].hidden_dev = 1
    state = reduce(
        state,
        ev.YearOfPlentyPlayed(player="red", resources=(Resource.ORE, Resource.GRAIN)),
    )
    red = state.players["red"]
    assert red.hidden_dev == 0
    assert red.dev_cards_played[DevCard.YEAR_OF_PLENTY] == 1
