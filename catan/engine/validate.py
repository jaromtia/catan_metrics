"""Command validation: turn the recorder into a rules engine.

``validate(state, command)`` returns a :class:`Result`. On success it carries
the :mod:`~catan.domain.events` the command expands into; on failure it carries
human-readable error strings and no events. ``execute`` chains validation with
the reducer.

The validator owns *all* legality: phase/turn ordering, the settlement distance
rule, road connectivity (including being blocked by opponent buildings), build
costs and piece/bank/deck limits, the 7 discard-then-move-robber sequence, and
"one development card per turn / not the turn you bought it".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain import commands as cmd
from ..domain import events as ev
from ..domain.constants import (
    CITY_COST,
    DEFAULT_BANK_TRADE_RATIO,
    DEV_CARD_COST,
    DEV_CARD_COUNTS,
    ROAD_COST,
    SETTLEMENT_COST,
    DevCard,
    PortType,
    Resource,
)
from ..domain.state import GameState, Phase, PlayerId
from .reduce import reduce


@dataclass
class Result:
    ok: bool
    events: list[ev.Event] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def ok(*events: ev.Event) -> Result:
    return Result(ok=True, events=list(events))


def err(*messages: str) -> Result:
    return Result(ok=False, errors=list(messages))


def execute(
    state: GameState | None, command: cmd.Command, *, strict: bool = True
) -> tuple[GameState, list[ev.Event]]:
    """Validate then fold. Raises ``ValueError`` if the command is illegal."""
    result = validate(state, command, strict=strict)
    if not result.ok:
        raise ValueError("; ".join(result.errors))
    s = state
    for event in result.events:
        s = reduce(s, event)
    assert s is not None
    return s, result.events


# --- topology / state helpers ---------------------------------------------

def _valid_vertex(state: GameState, v: int) -> bool:
    return v in state.board.topology.vertices


def _valid_edge(state: GameState, e: int) -> bool:
    return 0 <= e < len(state.board.topology.edges)


def _valid_hex(state: GameState, h) -> bool:
    return h in state.board.terrain


def _can_afford(state: GameState, pid: PlayerId, cost: dict[Resource, int]) -> bool:
    res = state.players[pid].resources
    return all(res[r] >= amt for r, amt in cost.items())


def _respects_distance(state: GameState, v: int) -> bool:
    if state.owner_of_vertex(v) is not None:
        return False
    return all(
        state.owner_of_vertex(n) is None
        for n in state.board.topology.vertex_neighbors[v]
    )


def _player_road_at(state: GameState, pid: PlayerId, vertex: int) -> bool:
    roads = state.players[pid].roads
    return any(e in roads for e in state.board.topology.vertex_edges[vertex])


def _edge_connected(
    state: GameState, pid: PlayerId, edge: int, extra_roads: frozenset[int] = frozenset()
) -> bool:
    topo = state.board.topology
    a, b = topo.edge_vertices[edge]
    roads = state.players[pid].roads | extra_roads
    for x in (a, b):
        owner = state.owner_of_vertex(x)
        if owner is not None:
            if owner[0] == pid:
                return True
            continue  # opponent building blocks connecting through this vertex
        if any(e in roads for e in topo.vertex_edges[x] if e != edge):
            return True
    return False


def _owned_port_types(state: GameState, pid: PlayerId) -> set[PortType]:
    ps = state.players[pid]
    buildings = ps.settlements | ps.cities
    return {p.type for p in state.board.ports if p.vertices & buildings}


def _best_ratio(state: GameState, pid: PlayerId, resource: Resource) -> int:
    owned = _owned_port_types(state, pid)
    ratio = DEFAULT_BANK_TRADE_RATIO
    if PortType.GENERIC in owned:
        ratio = 3
    if PortType(resource.value) in owned:
        ratio = 2
    return ratio


def setup_expectation(state: GameState) -> tuple[str, PlayerId] | None:
    """Public: what setup placement is expected next, or None if setup is done."""
    return _setup_expectation(state)


def _setup_expectation(state: GameState) -> tuple[str, PlayerId] | None:
    order = state.player_order
    snake = list(order) + list(reversed(order))
    n = len(order)
    settlements = sum(len(p.settlements) for p in state.players.values())
    roads = sum(len(p.roads) for p in state.players.values())
    if settlements >= 2 * n and roads >= 2 * n:
        return None
    if settlements == roads:
        return ("settlement", snake[settlements])
    return ("road", snake[roads])


def _eligible_victims(state: GameState, pid: PlayerId, hexc) -> list[PlayerId]:
    topo = state.board.topology
    victims: list[PlayerId] = []
    for v in topo.hex_vertices[hexc]:
        owner = state.owner_of_vertex(v)
        if owner is None:
            continue
        other = owner[0]
        if other != pid and other not in victims and state.players[other].hand_size > 0:
            victims.append(other)
    return victims


# --- gating ----------------------------------------------------------------

def _gate_play_action(state: GameState, pid: PlayerId, strict: bool = True) -> list[str]:
    """Common gate for build/buy/trade: your turn, rolled, no pending 7."""
    if not strict:
        return []  # dev/sandbox mode: game-flow gating is off
    e: list[str] = []
    if state.phase is not Phase.PLAY:
        e.append("not in play phase")
        return e
    if state.winner is not None:
        e.append("game is over")
    if pid != state.current_player:
        e.append(f"not {pid}'s turn")
    if not state.has_rolled:
        e.append("must roll the dice first")
    if state.pending_discards:
        e.append("resolve discards from the 7 first")
    if state.robber_pending:
        e.append("move the robber first")
    return e


def _resolved_count(state: GameState, card: DevCard) -> int:
    """How many cards of this type have already left the deck (across players).

    Victory Point cards are "resolved" by being revealed (held face-up); the
    others by being played.
    """
    if card is DevCard.VICTORY_POINT:
        return sum(ps.dev_cards[DevCard.VICTORY_POINT] for ps in state.players.values())
    return sum(ps.dev_cards_played[card] for ps in state.players.values())


def _gate_play_dev(
    state: GameState, pid: PlayerId, card: DevCard, strict: bool = True
) -> list[str]:
    """Gate for playing a development card (allowed before rolling).

    Drawn cards are hidden, so any one of a player's hidden cards may be declared
    to be the card being played. A card cannot be played the same turn it was
    drawn, and no more of a type may exist than the deck ever held.
    """
    if not strict:
        return []  # dev/sandbox mode: game-flow gating is off
    e: list[str] = []
    if state.phase is not Phase.PLAY:
        e.append("not in play phase")
        return e
    if state.winner is not None:
        e.append("game is over")
    if pid != state.current_player:
        e.append(f"not {pid}'s turn")
    if state.pending_discards:
        e.append("resolve discards from the 7 first")
    if state.robber_pending:
        e.append("move the robber first")
    if state.dev_played_this_turn:
        e.append("already played a development card this turn")
    playable = state.players[pid].hidden_dev - state.dev_bought_this_turn
    if playable <= 0:
        e.append("no playable development card")
    elif _resolved_count(state, card) >= DEV_CARD_COUNTS[card]:
        e.append(f"all {DEV_CARD_COUNTS[card]} {card.value} cards have been played")
    return e


def _validate_robber_move(
    state: GameState, pid: PlayerId, hexc, victim, resource, strict: bool = True
) -> list[str]:
    e: list[str] = []
    if not _valid_hex(state, hexc):
        e.append("invalid hex")
        return e
    # Always required so the reducer has a concrete card to move.
    if victim is not None and resource is None:
        e.append("must specify the stolen resource")
    if not strict:
        return e
    if hexc == state.robber:
        e.append("robber must move to a different hex")
    eligible = _eligible_victims(state, pid, hexc)
    if victim is not None:
        if victim not in eligible:
            e.append("victim has no building adjacent to the robber or no cards")
        elif state.players[victim].resources[resource] <= 0:
            e.append("victim does not have that resource")
    elif eligible:
        e.append("must steal from an adjacent player")
    return e


# --- dispatch --------------------------------------------------------------

def validate(state: GameState | None, command: cmd.Command, *, strict: bool = True) -> Result:
    if isinstance(command, cmd.CreateGame):
        if state is not None:
            return err("game already created")
        if not 2 <= len(command.player_order) <= 4:
            return err("base game supports 2-4 players")
        if len(set(command.player_order)) != len(command.player_order):
            return err("duplicate player ids")
        return ok(ev.GameCreated(board=command.board, player_order=command.player_order))

    if state is None:
        return err("no game in progress")

    match command:
        case cmd.PlaceSetupSettlement(player=p, vertex=v):
            return _v_setup_settlement(state, p, v, strict)
        case cmd.PlaceSetupRoad(player=p, edge=e):
            return _v_setup_road(state, p, e, strict)
        case cmd.RollDice(player=p, die1=d1, die2=d2):
            return _v_roll(state, p, d1, d2, strict)
        case cmd.EndTurn(player=p):
            return _v_end_turn(state, p, strict)
        case cmd.Discard(player=p, resources=res):
            return _v_discard(state, p, res, strict)
        case cmd.MoveRobber(player=p, hex=h, victim=vic, resource=r):
            return _v_move_robber(state, p, h, vic, r, strict)
        case cmd.BuildRoad(player=p, edge=e):
            return _v_build_road(state, p, e, strict)
        case cmd.BuildSettlement(player=p, vertex=v):
            return _v_build_settlement(state, p, v, strict)
        case cmd.BuildCity(player=p, vertex=v):
            return _v_build_city(state, p, v, strict)
        case cmd.BuyDevCard(player=p):
            return _v_buy_dev(state, p, strict)
        case cmd.RevealVictoryPoint(player=p):
            return _v_reveal_vp(state, p, strict)
        case cmd.PlayKnight(player=p, hex=h, victim=vic, resource=r):
            return _v_play_knight(state, p, h, vic, r, strict)
        case cmd.PlayRoadBuilding(player=p, edges=edges):
            return _v_play_road_building(state, p, edges, strict)
        case cmd.PlayYearOfPlenty(player=p, resources=res):
            return _v_play_yop(state, p, res, strict)
        case cmd.PlayMonopoly(player=p, resource=r):
            return _v_play_monopoly(state, p, r, strict)
        case cmd.TradeWithBank(player=p, give=g, give_amount=ga, receive=rc, receive_amount=ra):
            return _v_maritime(state, p, g, ga, rc, ra, strict)
        case cmd.TradeWithPlayer(player=p, partner=q, gave=gave, received=recv):
            return _v_domestic(state, p, q, gave, recv, strict)
        case cmd.SetResources(player=p, resources=res):
            return _v_set_resources(state, p, res, strict)
        case cmd.SetVictoryPoints(player=p, bonus=b):
            return _v_set_vp(state, p, b, strict)
        case _:
            return err(f"unknown command: {command!r}")


def _v_setup_settlement(state: GameState, p: PlayerId, v: int, strict: bool = True) -> Result:
    if not _valid_vertex(state, v):
        return err("invalid vertex")
    if p not in state.players:
        return err("unknown player")
    if strict:
        if state.phase is not Phase.SETUP:
            return err("not in setup phase")
        exp = _setup_expectation(state)
        if exp != ("settlement", p):
            return err(f"setup expects {exp}, not a settlement from {p}")
        if not _respects_distance(state, v):
            return err("violates the distance rule")
    return ok(ev.SetupSettlementPlaced(player=p, vertex=v))


def _v_setup_road(state: GameState, p: PlayerId, e: int, strict: bool = True) -> Result:
    if not _valid_edge(state, e):
        return err("invalid edge")
    if p not in state.players:
        return err("unknown player")
    if strict:
        if state.phase is not Phase.SETUP:
            return err("not in setup phase")
        exp = _setup_expectation(state)
        if exp != ("road", p):
            return err(f"setup expects {exp}, not a road from {p}")
        if state.owner_of_edge(e) is not None:
            return err("edge already has a road")
        a, b = state.board.topology.edge_vertices[e]
        touches_new_settlement = any(
            v in state.players[p].settlements and not _player_road_at(state, p, v)
            for v in (a, b)
        )
        if not touches_new_settlement:
            return err("setup road must touch your just-placed settlement")
    return ok(ev.SetupRoadPlaced(player=p, edge=e))


def _v_roll(state: GameState, p: PlayerId, d1: int, d2: int, strict: bool = True) -> Result:
    if not (1 <= d1 <= 6 and 1 <= d2 <= 6):
        return err("dice must each be 1-6")
    if strict:
        if state.phase is not Phase.PLAY:
            return err("not in play phase")
        if p != state.current_player:
            return err(f"not {p}'s turn")
        if state.has_rolled:
            return err("already rolled this turn")
    return ok(ev.DiceRolled(player=p, die1=d1, die2=d2))


def _v_end_turn(state: GameState, p: PlayerId, strict: bool = True) -> Result:
    if strict:
        if state.phase is not Phase.PLAY:
            return err("not in play phase")
        if p != state.current_player:
            return err(f"not {p}'s turn")
        if not state.has_rolled:
            return err("must roll before ending the turn")
        if state.pending_discards:
            return err("resolve discards first")
        if state.robber_pending:
            return err("move the robber first")
    return ok(ev.TurnEnded(player=p))


def _v_discard(state: GameState, p: PlayerId, res: dict[Resource, int], strict: bool = True) -> Result:
    if p not in state.players:
        return err("unknown player")
    if any(amt < 0 for amt in res.values()):
        return err("negative discard amount")
    if strict:
        if p not in state.pending_discards:
            return err(f"{p} does not need to discard")
        required = state.pending_discards[p]
        if sum(res.values()) != required:
            return err(f"{p} must discard exactly {required} cards")
        hand = state.players[p].resources
        if any(hand[r] < amt for r, amt in res.items()):
            return err("cannot discard resources you do not have")
    return ok(ev.DiscardedToRobber(player=p, resources=dict(res)))


def _v_move_robber(state: GameState, p: PlayerId, h, vic, r, strict: bool = True) -> Result:
    if strict:
        if state.phase is not Phase.PLAY:
            return err("not in play phase")
        if p != state.current_player:
            return err(f"not {p}'s turn")
        if state.pending_discards:
            return err("resolve discards before moving the robber")
        if not state.robber_pending:
            return err("the robber is not awaiting a move")
    errors = _validate_robber_move(state, p, h, vic, r, strict)
    if errors:
        return Result(ok=False, errors=errors)
    events: list[ev.Event] = [ev.RobberMoved(player=p, hex=h)]
    if vic is not None:
        events.append(ev.ResourceStolen(player=p, victim=vic, resource=r))
    return Result(ok=True, events=events)


def _v_build_road(state: GameState, p: PlayerId, e: int, strict: bool = True) -> Result:
    errors = _gate_play_action(state, p, strict)
    if not _valid_edge(state, e):
        errors.append("invalid edge")
        return Result(ok=False, errors=errors)
    if p not in state.players:
        return err("unknown player")
    if strict:
        if state.players[p].roads_left <= 0:
            errors.append("no roads left")
        if not _can_afford(state, p, ROAD_COST):
            errors.append("cannot afford a road")
        if state.owner_of_edge(e) is not None:
            errors.append("edge already has a road")
        elif not _edge_connected(state, p, e):
            errors.append("road must connect to your network")
    if errors:
        return Result(ok=False, errors=errors)
    return ok(ev.RoadBuilt(player=p, edge=e))


def _v_build_settlement(state: GameState, p: PlayerId, v: int, strict: bool = True) -> Result:
    errors = _gate_play_action(state, p, strict)
    if not _valid_vertex(state, v):
        errors.append("invalid vertex")
        return Result(ok=False, errors=errors)
    if p not in state.players:
        return err("unknown player")
    if strict:
        if state.players[p].settlements_left <= 0:
            errors.append("no settlements left")
        if not _can_afford(state, p, SETTLEMENT_COST):
            errors.append("cannot afford a settlement")
        if not _respects_distance(state, v):
            errors.append("violates the distance rule")
        if not _player_road_at(state, p, v):
            errors.append("settlement must connect to your road")
    if errors:
        return Result(ok=False, errors=errors)
    return ok(ev.SettlementBuilt(player=p, vertex=v))


def _v_build_city(state: GameState, p: PlayerId, v: int, strict: bool = True) -> Result:
    errors = _gate_play_action(state, p, strict)
    if not _valid_vertex(state, v):
        errors.append("invalid vertex")
        return Result(ok=False, errors=errors)
    if p not in state.players:
        return err("unknown player")
    if strict:
        if state.players[p].cities_left <= 0:
            errors.append("no cities left")
        if not _can_afford(state, p, CITY_COST):
            errors.append("cannot afford a city")
        if v not in state.players[p].settlements:
            errors.append("city must upgrade your own settlement")
    if errors:
        return Result(ok=False, errors=errors)
    return ok(ev.CityBuilt(player=p, vertex=v))


def _v_buy_dev(state: GameState, p: PlayerId, strict: bool = True) -> Result:
    errors = _gate_play_action(state, p, strict)
    if p not in state.players:
        return err("unknown player")
    if strict:
        if state.dev_deck_size <= 0:
            errors.append("development deck is empty")
        if not _can_afford(state, p, DEV_CARD_COST):
            errors.append("cannot afford a development card")
    if errors:
        return Result(ok=False, errors=errors)
    return ok(ev.DevCardBought(player=p))


def _v_reveal_vp(state: GameState, p: PlayerId, strict: bool = True) -> Result:
    if p not in state.players:
        return err("unknown player")
    if strict:
        errors: list[str] = []
        if state.phase is not Phase.PLAY:
            return err("not in play phase")
        if state.winner is not None:
            errors.append("game is over")
        if p != state.current_player:
            errors.append(f"not {p}'s turn")
        # A VP card may be revealed the same turn it is drawn (e.g. to win), so
        # there is no "bought this turn" restriction here -- only that a hidden
        # card exists and that fewer than the deck's VP cards are already shown.
        if state.players[p].hidden_dev <= 0:
            errors.append("no hidden development card to reveal")
        elif _resolved_count(state, DevCard.VICTORY_POINT) >= DEV_CARD_COUNTS[DevCard.VICTORY_POINT]:
            errors.append("all victory point cards are already revealed")
        if errors:
            return Result(ok=False, errors=errors)
    return ok(ev.VictoryPointRevealed(player=p))


def _v_play_knight(state: GameState, p: PlayerId, h, vic, r, strict: bool = True) -> Result:
    errors = _gate_play_dev(state, p, DevCard.KNIGHT, strict)
    errors += _validate_robber_move(state, p, h, vic, r, strict)
    if errors:
        return Result(ok=False, errors=errors)
    return ok(ev.KnightPlayed(player=p, hex=h, victim=vic, resource=r))


def _v_play_road_building(
    state: GameState, p: PlayerId, edges: tuple[int, ...], strict: bool = True
) -> Result:
    errors = _gate_play_dev(state, p, DevCard.ROAD_BUILDING, strict)
    if not 1 <= len(edges) <= 2:
        errors.append("road building places one or two roads")
        return Result(ok=False, errors=errors)
    for e in edges:
        if not _valid_edge(state, e):
            errors.append("invalid edge")
    if strict:
        if len(set(edges)) != len(edges):
            errors.append("duplicate edge")
        if len(edges) > state.players[p].roads_left:
            errors.append("not enough roads left")
        placed: set[int] = set()
        for e in edges:
            if not _valid_edge(state, e):
                continue
            if state.owner_of_edge(e) is not None or e in placed:
                errors.append("edge already has a road")
                continue
            if not _edge_connected(state, p, e, extra_roads=frozenset(placed)):
                errors.append("road must connect to your network")
                continue
            placed.add(e)
    if errors:
        return Result(ok=False, errors=errors)
    return ok(ev.RoadBuildingPlayed(player=p, edges=tuple(edges)))


def _v_play_yop(
    state: GameState, p: PlayerId, res: tuple[Resource, Resource], strict: bool = True
) -> Result:
    errors = _gate_play_dev(state, p, DevCard.YEAR_OF_PLENTY, strict)
    if len(res) != 2:
        errors.append("year of plenty takes exactly two resources")
        return Result(ok=False, errors=errors)
    if strict:
        need: dict[Resource, int] = {}
        for r in res:
            need[r] = need.get(r, 0) + 1
        for r, amt in need.items():
            if state.bank[r] < amt:
                errors.append(f"bank lacks {amt} {r.value}")
    if errors:
        return Result(ok=False, errors=errors)
    return ok(ev.YearOfPlentyPlayed(player=p, resources=res))


def _v_play_monopoly(state: GameState, p: PlayerId, r: Resource, strict: bool = True) -> Result:
    errors = _gate_play_dev(state, p, DevCard.MONOPOLY, strict)
    if errors:
        return Result(ok=False, errors=errors)
    return ok(ev.MonopolyPlayed(player=p, resource=r))


def _v_maritime(
    state: GameState, p: PlayerId, give: Resource, ga: int, recv: Resource, ra: int,
    strict: bool = True,
) -> Result:
    errors = _gate_play_action(state, p, strict)
    if ga <= 0 or ra <= 0:
        errors.append("trade amounts must be positive")
    if strict:
        if give == recv:
            errors.append("cannot trade a resource for itself")
        if ga > 0 and ra > 0:
            ratio = _best_ratio(state, p, give)
            if ga != ra * ratio:
                errors.append(f"maritime trade for {give.value} is {ratio}:1")
            if state.players[p].resources[give] < ga:
                errors.append("you do not have enough to give")
            if state.bank[recv] < ra:
                errors.append("bank does not have enough to give")
    if errors:
        return Result(ok=False, errors=errors)
    return ok(ev.MaritimeTrade(
        player=p, gave={give: ga}, received={recv: ra}, ratio=_best_ratio(state, p, give)
    ))


def _v_domestic(
    state: GameState, p: PlayerId, q: PlayerId, gave: dict[Resource, int],
    recv: dict[Resource, int], strict: bool = True,
) -> Result:
    errors = _gate_play_action(state, p, strict)
    if q not in state.players or p not in state.players:
        errors.append("unknown partner")
        return Result(ok=False, errors=errors)
    gave = {r: a for r, a in gave.items() if a}
    recv = {r: a for r, a in recv.items() if a}
    if any(a < 0 for a in gave.values()) or any(a < 0 for a in recv.values()):
        errors.append("negative trade amount")
    if strict:
        if q == p:
            errors.append("cannot trade with yourself")
        if not gave or not recv:
            errors.append("both sides must trade at least one resource")
        if any(state.players[p].resources[r] < a for r, a in gave.items()):
            errors.append(f"{p} lacks the resources to give")
        if any(state.players[q].resources[r] < a for r, a in recv.items()):
            errors.append(f"{q} lacks the resources to give")
    if errors:
        return Result(ok=False, errors=errors)
    return ok(ev.DomesticTrade(player=p, partner=q, gave=gave, received=recv))


# --- dev/sandbox admin -----------------------------------------------------

def _v_set_resources(
    state: GameState, p: PlayerId, res: dict[Resource, int], strict: bool = True
) -> Result:
    if strict:
        return err("setting resources is only allowed in dev mode")
    if p not in state.players:
        return err("unknown player")
    if any(a < 0 for a in res.values()):
        return err("resource amounts cannot be negative")
    return ok(ev.ResourcesSet(player=p, resources=dict(res)))


def _v_set_vp(state: GameState, p: PlayerId, bonus: int, strict: bool = True) -> Result:
    if strict:
        return err("setting victory points is only allowed in dev mode")
    if p not in state.players:
        return err("unknown player")
    return ok(ev.VictoryPointsSet(player=p, bonus=bonus))
