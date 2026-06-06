"""Validation: legal play paths and rejection of illegal moves."""

from catan.domain import commands as cmd
from catan.domain.board import standard_board
from catan.domain.constants import Resource
from catan.domain.state import GameState, Phase
from catan.engine.validate import execute, validate

PLAYERS = ("red", "blue", "white")


# --- helpers ---------------------------------------------------------------

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


def incident_edge(topo, v):
    return next(iter(topo.vertex_edges[v]))


def run_setup():
    board = standard_board()
    state, _ = execute(None, cmd.CreateGame(board=board, player_order=PLAYERS))
    topo = board.topology
    snake = list(PLAYERS) + list(reversed(PLAYERS))
    verts = pick_nonadjacent(topo, 2 * len(PLAYERS))
    for player, v in zip(snake, verts, strict=True):
        state, _ = execute(state, cmd.PlaceSetupSettlement(player=player, vertex=v))
        state, _ = execute(state, cmd.PlaceSetupRoad(player=player, edge=incident_edge(topo, v)))
    return state


def play_state(*, has_rolled=True):
    state = GameState.new(standard_board(), list(PLAYERS))
    state.phase = Phase.PLAY
    state.turn_number = 1
    state.has_rolled = has_rolled
    return state


def give(state, pid, **res):
    for name, amt in res.items():
        state.players[pid].resources[Resource(name)] += amt


# --- setup -----------------------------------------------------------------

def test_full_setup_reaches_play_phase():
    state = run_setup()
    assert state.phase is Phase.PLAY
    assert state.current_player == "red"
    for p in state.players.values():
        assert len(p.settlements) == 2 and len(p.roads) == 2


def test_setup_rejects_wrong_player_and_wrong_action():
    board = standard_board()
    state, _ = execute(None, cmd.CreateGame(board=board, player_order=PLAYERS))
    # Setup expects a settlement from red first.
    assert not validate(state, cmd.PlaceSetupRoad(player="red", edge=0)).ok
    assert not validate(state, cmd.PlaceSetupSettlement(player="blue", vertex=0)).ok
    assert validate(state, cmd.PlaceSetupSettlement(player="red", vertex=0)).ok


def test_setup_distance_rule():
    board = standard_board()
    state, _ = execute(None, cmd.CreateGame(board=board, player_order=PLAYERS))
    state, _ = execute(state, cmd.PlaceSetupSettlement(player="red", vertex=0))
    state, _ = execute(state, cmd.PlaceSetupRoad(player="red", edge=incident_edge(board.topology, 0)))
    neighbor = next(iter(board.topology.vertex_neighbors[0]))
    res = validate(state, cmd.PlaceSetupSettlement(player="blue", vertex=neighbor))
    assert not res.ok and "distance" in res.errors[0]


# --- turn structure --------------------------------------------------------

def test_must_roll_before_acting():
    state = run_setup()  # red's turn, not yet rolled
    assert not validate(state, cmd.EndTurn(player="red")).ok
    assert not validate(state, cmd.BuildRoad(player="red", edge=0)).ok
    assert validate(state, cmd.RollDice(player="red", die1=5, die2=3)).ok


def test_cannot_roll_twice():
    state = run_setup()
    state, _ = execute(state, cmd.RollDice(player="red", die1=5, die2=3))
    assert not validate(state, cmd.RollDice(player="red", die1=2, die2=2)).ok


def test_only_current_player_may_roll():
    state = run_setup()
    assert not validate(state, cmd.RollDice(player="blue", die1=1, die2=1)).ok


# --- building --------------------------------------------------------------

def test_build_road_requires_resources_and_connection():
    state = play_state()
    state.players["red"].roads.add(5)  # gives a network anchor
    a, b = state.board.topology.edge_vertices[5]
    connected = next(
        e for e in state.board.topology.vertex_edges[a] if e != 5
        and state.owner_of_edge(e) is None
    )
    # No resources yet.
    assert not validate(state, cmd.BuildRoad(player="red", edge=connected)).ok
    give(state, "red", brick=1, lumber=1)
    assert validate(state, cmd.BuildRoad(player="red", edge=connected)).ok
    # A disconnected edge is rejected even with resources.
    disconnected = next(
        e for e in range(len(state.board.topology.edges))
        if a not in state.board.topology.edge_vertices[e]
        and b not in state.board.topology.edge_vertices[e]
        and state.owner_of_edge(e) is None
    )
    assert not validate(state, cmd.BuildRoad(player="red", edge=disconnected)).ok


def test_build_settlement_legal_and_distance():
    state = play_state()
    edge = 5
    a, b = state.board.topology.edge_vertices[edge]
    state.players["red"].roads.add(edge)
    give(state, "red", brick=1, lumber=1, wool=1, grain=1)
    assert validate(state, cmd.BuildSettlement(player="red", vertex=a)).ok
    # Place it, then an adjacent vertex violates the distance rule.
    state, _ = execute(state, cmd.BuildSettlement(player="red", vertex=a))
    give(state, "red", brick=1, lumber=1, wool=1, grain=1)
    res = validate(state, cmd.BuildSettlement(player="red", vertex=b))
    assert not res.ok and any("distance" in e for e in res.errors)


def test_build_city_must_upgrade_own_settlement():
    state = play_state()
    give(state, "red", ore=3, grain=2)
    assert not validate(state, cmd.BuildCity(player="red", vertex=10)).ok
    state.players["red"].settlements.add(10)
    assert validate(state, cmd.BuildCity(player="red", vertex=10)).ok


# --- development cards -----------------------------------------------------

def test_buy_dev_card_needs_resources():
    state = play_state()
    assert not validate(state, cmd.BuyDevCard(player="red")).ok
    give(state, "red", ore=1, wool=1, grain=1)
    assert validate(state, cmd.BuyDevCard(player="red")).ok


def test_buy_dev_card_blocked_when_deck_empty():
    state = play_state()
    give(state, "red", ore=1, wool=1, grain=1)
    state.dev_deck_size = 0
    res = validate(state, cmd.BuyDevCard(player="red"))
    assert not res.ok and any("deck is empty" in e for e in res.errors)


def test_one_dev_card_per_turn():
    state = play_state()
    state.players["red"].hidden_dev = 2
    target = next(h for h in state.board.numbers if h != state.robber)
    state, _ = execute(state, cmd.PlayKnight(player="red", hex=target))
    # Robber now sits on target; pick a different hex for the second knight.
    other = next(h for h in state.board.numbers if h != state.robber)
    res = validate(state, cmd.PlayKnight(player="red", hex=other))
    assert not res.ok and any("already played" in e for e in res.errors)


def test_cannot_play_dev_card_bought_this_turn():
    state = play_state()
    state.players["red"].hidden_dev = 1
    state.dev_bought_this_turn = 1
    target = next(h for h in state.board.numbers if h != state.robber)
    res = validate(state, cmd.PlayKnight(player="red", hex=target))
    assert not res.ok and any("no playable" in e for e in res.errors)


def test_reveal_vp_requires_a_hidden_card():
    state = play_state()
    res = validate(state, cmd.RevealVictoryPoint(player="red"))
    assert not res.ok and any("no hidden" in e for e in res.errors)
    state.players["red"].hidden_dev = 1
    assert validate(state, cmd.RevealVictoryPoint(player="red")).ok


def test_reveal_vp_allowed_the_turn_it_was_bought():
    state = play_state()
    state.players["red"].hidden_dev = 1
    state.dev_bought_this_turn = 1
    # Unlike playing a card, a VP card can be revealed the same turn it is drawn.
    assert validate(state, cmd.RevealVictoryPoint(player="red")).ok


# --- the seven -------------------------------------------------------------

def test_seven_forces_discard_then_robber_then_steal():
    state = play_state(has_rolled=False)
    give(state, "red", brick=4, lumber=4)     # 8 cards -> discard 4
    give(state, "blue", ore=8)                # 8 cards -> discard 4
    give(state, "white", wool=3)              # safe

    state, _ = execute(state, cmd.RollDice(player="red", die1=3, die2=4))
    assert state.pending_discards == {"red": 4, "blue": 4}

    # Cannot act before discarding.
    assert not validate(state, cmd.EndTurn(player="red")).ok
    assert not validate(state, cmd.MoveRobber(player="red", hex=state.robber)).ok

    state, _ = execute(state, cmd.Discard(player="red", resources={Resource.BRICK: 4}))
    state, _ = execute(state, cmd.Discard(player="blue", resources={Resource.ORE: 4}))
    assert state.pending_discards == {}
    assert state.robber_pending

    # Steal from blue: give blue a building on a non-desert hex, then rob it.
    target = next(h for h in state.board.numbers if h != state.robber)
    victim_vertex = next(iter(state.board.topology.hex_vertices[target]))
    state.players["blue"].settlements.add(victim_vertex)

    # Robber must actually move and must steal from the adjacent victim.
    assert not validate(state, cmd.MoveRobber(player="red", hex=target)).ok
    state, _ = execute(
        state,
        cmd.MoveRobber(player="red", hex=target, victim="blue", resource=Resource.ORE),
    )
    assert state.robber == target
    assert not state.robber_pending
    assert state.players["red"].resources[Resource.ORE] == 1


# --- trading ---------------------------------------------------------------

def test_maritime_trade_enforces_ratio():
    state = play_state()
    give(state, "red", brick=4)
    assert validate(
        state, cmd.TradeWithBank(player="red", give=Resource.BRICK, give_amount=4,
                                 receive=Resource.ORE, receive_amount=1)
    ).ok
    # Wrong ratio (3 brick for 1 with no port) is rejected.
    bad = validate(
        state, cmd.TradeWithBank(player="red", give=Resource.BRICK, give_amount=3,
                                 receive=Resource.ORE, receive_amount=1)
    )
    assert not bad.ok


def test_domestic_trade_requires_both_sides_have_goods():
    state = play_state()
    give(state, "red", wool=1)
    give(state, "blue", ore=1)
    assert validate(
        state, cmd.TradeWithPlayer(player="red", partner="blue",
                                   gave={Resource.WOOL: 1}, received={Resource.ORE: 1})
    ).ok
    # Partner cannot cover their side.
    bad = validate(
        state, cmd.TradeWithPlayer(player="red", partner="blue",
                                   gave={Resource.WOOL: 1}, received={Resource.GRAIN: 1})
    )
    assert not bad.ok
    # Gifts (one-sided trades) are illegal.
    assert not validate(
        state, cmd.TradeWithPlayer(player="red", partner="blue",
                                   gave={Resource.WOOL: 1}, received={})
    ).ok
