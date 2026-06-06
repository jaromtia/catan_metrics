"""The pure reducer: ``reduce(state, event) -> new_state``.

This is the only place game state changes. It never mutates its input; it works
on a clone and returns it. Deterministic consequences of an event (resource
production, monopoly transfers, award recomputation, win detection) are applied
here rather than stored on events, so the event log stays minimal and replayable.
"""

from __future__ import annotations

from collections import defaultdict

from ..domain import events as ev
from ..domain.board import Board
from ..domain.constants import (
    CITY_COST,
    DEV_CARD_COST,
    ROAD_COST,
    SETTLEMENT_COST,
    TERRAIN_RESOURCE,
    VICTORY_POINTS_TO_WIN,
    DevCard,
    Resource,
)
from ..domain.state import GameState, Phase, PlayerId
from .awards import recompute_longest_road, update_largest_army


def reduce(state: GameState | None, event: ev.Event) -> GameState:
    if isinstance(event, ev.GameCreated):
        return GameState.new(event.board, list(event.player_order))

    assert state is not None, "first event must be GameCreated"
    s = state.clone()
    _apply(s, event)

    # Only the acting player can win, and only on their own turn -- per the
    # official rules. If a move hands an award (e.g. Longest Road) to a third
    # player who thereby reaches 10 VP, that is not a win here; it is detected
    # when that player next acts.
    acting = getattr(event, "player", None)
    if s.phase is Phase.PLAY and acting is not None:
        if s.victory_points(acting, include_hidden=True) >= VICTORY_POINTS_TO_WIN:
            s.winner = acting
            s.phase = Phase.FINISHED
    return s


def apply_all(events: list[ev.Event]) -> GameState:
    state: GameState | None = None
    for event in events:
        state = reduce(state, event)
    assert state is not None, "empty event stream"
    return state


# --- dispatch --------------------------------------------------------------

def _apply(s: GameState, event: ev.Event) -> None:
    match event:
        case ev.SetupSettlementPlaced(player=p, vertex=v):
            _setup_settlement(s, p, v)
        case ev.SetupRoadPlaced(player=p, edge=e):
            s.players[p].roads.add(e)
            _maybe_finish_setup(s)
        case ev.DiceRolled(die1=d1, die2=d2):
            s.dice = (d1, d2)
            s.has_rolled = True
            if d1 + d2 == 7:
                s.pending_discards = {
                    pid: p.hand_size // 2
                    for pid, p in s.players.items()
                    if p.hand_size > 7
                }
                s.robber_pending = True
            else:
                _apply_production(s, d1 + d2)
        case ev.TurnEnded():
            _end_turn(s)
        case ev.DiscardedToRobber(player=p, resources=res):
            for r, amt in res.items():
                s.players[p].resources[r] -= amt
                s.bank[r] += amt
            s.pending_discards.pop(p, None)
        case ev.RobberMoved(hex=h):
            s.robber = h
            s.robber_pending = False
        case ev.ResourceStolen(player=p, victim=vic, resource=r):
            s.players[vic].resources[r] -= 1
            s.players[p].resources[r] += 1
        case ev.DomesticTrade(player=p, partner=q, gave=gave, received=recv):
            _move(s, p, q, gave)
            _move(s, q, p, recv)
        case ev.MaritimeTrade(player=p, gave=gave, received=recv):
            for r, amt in gave.items():
                s.players[p].resources[r] -= amt
                s.bank[r] += amt
            for r, amt in recv.items():
                s.bank[r] -= amt
                s.players[p].resources[r] += amt
        case ev.RoadBuilt(player=p, edge=e):
            _pay(s, p, ROAD_COST)
            s.players[p].roads.add(e)
            s.longest_road_holder = recompute_longest_road(s)
        case ev.SettlementBuilt(player=p, vertex=v):
            _pay(s, p, SETTLEMENT_COST)
            s.players[p].settlements.add(v)
            s.longest_road_holder = recompute_longest_road(s)
        case ev.CityBuilt(player=p, vertex=v):
            _pay(s, p, CITY_COST)
            s.players[p].settlements.discard(v)
            s.players[p].cities.add(v)
        case ev.DevCardBought(player=p):
            _pay(s, p, DEV_CARD_COST)
            s.dev_deck_size -= 1
            s.players[p].hidden_dev += 1
            s.dev_bought_this_turn += 1
        case ev.KnightPlayed(player=p, hex=h, victim=vic, resource=r):
            ps = s.players[p]
            ps.hidden_dev -= 1
            ps.dev_cards_played[DevCard.KNIGHT] += 1
            ps.knights_played += 1
            s.robber = h
            if vic is not None and r is not None:
                s.players[vic].resources[r] -= 1
                ps.resources[r] += 1
            s.dev_played_this_turn = True
            s.largest_army_holder = update_largest_army(s, p)
        case ev.RoadBuildingPlayed(player=p, edges=edges):
            ps = s.players[p]
            ps.hidden_dev -= 1
            ps.dev_cards_played[DevCard.ROAD_BUILDING] += 1
            for e in edges:
                ps.roads.add(e)
            s.dev_played_this_turn = True
            s.longest_road_holder = recompute_longest_road(s)
        case ev.YearOfPlentyPlayed(player=p, resources=res):
            ps = s.players[p]
            ps.hidden_dev -= 1
            ps.dev_cards_played[DevCard.YEAR_OF_PLENTY] += 1
            for r in res:
                s.bank[r] -= 1
                ps.resources[r] += 1
            s.dev_played_this_turn = True
        case ev.MonopolyPlayed(player=p, resource=r):
            ps = s.players[p]
            ps.hidden_dev -= 1
            ps.dev_cards_played[DevCard.MONOPOLY] += 1
            s.dev_played_this_turn = True
            taken = 0
            for other in s.player_order:
                if other == p:
                    continue
                taken += s.players[other].resources[r]
                s.players[other].resources[r] = 0
            ps.resources[r] += taken
        case ev.VictoryPointRevealed(player=p):
            # A hidden card is revealed to be a VP card; it now counts toward VP.
            ps = s.players[p]
            ps.hidden_dev -= 1
            ps.dev_cards[DevCard.VICTORY_POINT] += 1
        case ev.ResourcesSet(player=p, resources=res):
            for r, amt in res.items():
                s.players[p].resources[r] = amt
        case ev.VictoryPointsSet(player=p, bonus=b):
            s.players[p].bonus_vp = b
        case _:
            raise ValueError(f"unhandled event: {event!r}")


# --- helpers ---------------------------------------------------------------

def _move(s: GameState, frm: PlayerId, to: PlayerId, bundle: dict[Resource, int]) -> None:
    for r, amt in bundle.items():
        s.players[frm].resources[r] -= amt
        s.players[to].resources[r] += amt


def _pay(s: GameState, pid: PlayerId, cost: dict[Resource, int]) -> None:
    ps = s.players[pid]
    for r, amt in cost.items():
        ps.resources[r] -= amt
        s.bank[r] += amt


def _setup_settlement(s: GameState, pid: PlayerId, vertex: int) -> None:
    ps = s.players[pid]
    is_second = len(ps.settlements) == 1
    ps.settlements.add(vertex)
    if is_second:
        for hexc in s.board.topology.vertex_hexes[vertex]:
            res = TERRAIN_RESOURCE[s.board.terrain[hexc]]
            if res is None:
                continue
            if s.bank[res] > 0:
                ps.resources[res] += 1
                s.bank[res] -= 1
    _maybe_finish_setup(s)


def _maybe_finish_setup(s: GameState) -> None:
    if s.phase is not Phase.SETUP:
        return
    n = len(s.player_order)
    settlements = sum(len(p.settlements) for p in s.players.values())
    roads = sum(len(p.roads) for p in s.players.values())
    if settlements == 2 * n and roads == 2 * n:
        s.phase = Phase.PLAY
        s.current_index = 0
        s.has_rolled = False
        s.turn_number = 1


def _end_turn(s: GameState) -> None:
    n = len(s.player_order)
    s.current_index = (s.current_index + 1) % n
    s.has_rolled = False
    s.dice = None
    s.dev_played_this_turn = False
    s.dev_bought_this_turn = 0
    s.robber_pending = False
    s.pending_discards = {}
    if s.current_index == 0:
        s.turn_number += 1


def _apply_production(s: GameState, roll: int) -> None:
    board: Board = s.board
    per_player: dict[PlayerId, dict[Resource, int]] = defaultdict(lambda: defaultdict(int))

    for hexc, num in board.numbers.items():
        if num != roll or hexc == s.robber:
            continue
        res = TERRAIN_RESOURCE[board.terrain[hexc]]
        if res is None:
            continue
        for v in board.topology.hex_vertices[hexc]:
            owner = s.owner_of_vertex(v)
            if owner is None:
                continue
            pid, kind = owner
            per_player[pid][res] += 2 if kind == "city" else 1

    # Regroup by resource to apply the bank-shortage rule.
    by_resource: dict[Resource, dict[PlayerId, int]] = defaultdict(dict)
    for pid, rmap in per_player.items():
        for res, amt in rmap.items():
            by_resource[res][pid] = amt

    for res, pid_amts in by_resource.items():
        total = sum(pid_amts.values())
        available = s.bank[res]
        if total <= available:
            grant = pid_amts
        elif len(pid_amts) == 1:
            pid = next(iter(pid_amts))
            grant = {pid: min(pid_amts[pid], available)}
        else:
            grant = {}  # not enough for multiple players -> none produced
        for pid, amt in grant.items():
            s.players[pid].resources[res] += amt
            s.bank[res] -= amt
