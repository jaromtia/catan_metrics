"""Metrics projections over the event stream.

Everything here is a pure function of the events: replay them through the
reducer once, and at each step record both event-level detail (dice, trades,
steals, production diffs) and state snapshots (VP, hand size, pip equity).
Because it is derived purely from the log, it is fully reproducible and can be
recomputed at any time.

Headline metric: **luck**. Expected income from a single roll of two dice is a
player's *pip equity* / 36 (each pip is a 1/36 chance to draw a card). Summing
that over every roll gives expected production; comparing to what they actually
drew tells you whether the dice ran hot or cold for them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain import events as ev
from ..domain.constants import PIPS, TERRAIN_RESOURCE, DevCard, Resource
from ..domain.state import GameState, PlayerId
from .reduce import reduce


def pip_equity(state: GameState, pid: PlayerId) -> int:
    """Sum of probability pips on a player's hexes (settlements x1, cities x2)."""
    board = state.board
    p = state.players[pid]
    total = 0
    for v in p.settlements:
        total += sum(board.pips.get(h, 0) for h in board.topology.vertex_hexes[v])
    for v in p.cities:
        total += 2 * sum(board.pips.get(h, 0) for h in board.topology.vertex_hexes[v])
    return total


@dataclass
class PlayerMetrics:
    pid: PlayerId
    production: dict[Resource, int] = field(default_factory=lambda: {r: 0 for r in Resource})
    expected_production: float = 0.0
    cards_discarded: int = 0
    steals_made: int = 0
    cards_stolen_from_me: int = 0
    robber_blocked: int = 0       # production this player denied with their robber
    knights_played: int = 0
    dev_bought: dict[DevCard, int] = field(default_factory=lambda: {c: 0 for c in DevCard})
    dev_played: dict[DevCard, int] = field(default_factory=lambda: {c: 0 for c in DevCard})
    trades_domestic: int = 0
    trades_maritime: int = 0
    trade_net: dict[Resource, int] = field(default_factory=lambda: {r: 0 for r in Resource})
    builds: list[tuple[int, int, str]] = field(default_factory=list)   # (seq, turn, kind)
    vp_timeline: list[tuple[int, int, int]] = field(default_factory=list)  # (seq, true, public)
    hand_timeline: list[tuple[int, int]] = field(default_factory=list)     # (seq, hand)
    pip_timeline: list[tuple[int, int]] = field(default_factory=list)      # (seq, pip_equity)

    @property
    def production_total(self) -> int:
        return sum(self.production.values())

    @property
    def luck(self) -> float:
        return self.production_total - self.expected_production

    @property
    def final_vp(self) -> int:
        return self.vp_timeline[-1][1] if self.vp_timeline else 0

    @property
    def final_pip_equity(self) -> int:
        return self.pip_timeline[-1][1] if self.pip_timeline else 0


@dataclass
class GameMetrics:
    player_order: list[PlayerId]
    players: dict[PlayerId, PlayerMetrics]
    dice_histogram: dict[int, int] = field(default_factory=lambda: {n: 0 for n in range(2, 13)})
    num_turns: int = 0
    winner: PlayerId | None = None

    @property
    def dice_total(self) -> int:
        return sum(self.dice_histogram.values())

    def to_dict(self) -> dict:
        return {
            "player_order": list(self.player_order),
            "num_turns": self.num_turns,
            "winner": self.winner,
            "dice_histogram": {str(k): v for k, v in self.dice_histogram.items()},
            "dice_total": self.dice_total,
            "players": {
                pid: {
                    "production": {r.value: a for r, a in pm.production.items()},
                    "production_total": pm.production_total,
                    "expected_production": round(pm.expected_production, 3),
                    "luck": round(pm.luck, 3),
                    "cards_discarded": pm.cards_discarded,
                    "steals_made": pm.steals_made,
                    "cards_stolen_from_me": pm.cards_stolen_from_me,
                    "robber_blocked": pm.robber_blocked,
                    "knights_played": pm.knights_played,
                    "dev_bought": {c.value: a for c, a in pm.dev_bought.items()},
                    "dev_played": {c.value: a for c, a in pm.dev_played.items()},
                    "trades_domestic": pm.trades_domestic,
                    "trades_maritime": pm.trades_maritime,
                    "trade_net": {r.value: a for r, a in pm.trade_net.items()},
                    "builds": pm.builds,
                    "vp_timeline": pm.vp_timeline,
                    "hand_timeline": pm.hand_timeline,
                    "pip_timeline": pm.pip_timeline,
                    "final_vp": pm.final_vp,
                    "final_pip_equity": pm.final_pip_equity,
                }
                for pid, pm in self.players.items()
            },
        }


def compute_metrics(events: list[ev.Event]) -> GameMetrics:
    metrics: GameMetrics | None = None
    state: GameState | None = None
    robber_owner: PlayerId | None = None  # who last moved the robber

    for seq, event in enumerate(events):
        prev = state
        state = reduce(state, event)

        if isinstance(event, ev.GameCreated):
            metrics = GameMetrics(
                player_order=list(state.player_order),
                players={pid: PlayerMetrics(pid=pid) for pid in state.player_order},
            )
        assert metrics is not None, "first event must be GameCreated"

        if isinstance(event, (ev.RobberMoved, ev.KnightPlayed)):
            robber_owner = event.player
        if isinstance(event, ev.DiceRolled) and event.total != 7 and robber_owner:
            metrics.players[robber_owner].robber_blocked += _blocked_production(state, event.total)

        _record(metrics, prev, state, seq, event)
        _snapshot(metrics, state, seq)

    assert metrics is not None, "empty event stream"
    metrics.num_turns = state.turn_number
    metrics.winner = state.winner
    return metrics


def _blocked_production(state: GameState, roll: int) -> int:
    """Cards that the hex under the robber would have produced on this roll."""
    board = state.board
    total = 0
    for hexc, num in board.numbers.items():
        if num != roll or hexc != state.robber:
            continue
        if TERRAIN_RESOURCE[board.terrain[hexc]] is None:
            continue
        for v in board.topology.hex_vertices[hexc]:
            owner = state.owner_of_vertex(v)
            if owner is None:
                continue
            total += 2 if owner[1] == "city" else 1
    return total


def _record(g: GameMetrics, prev: GameState | None, state: GameState, seq: int, event: ev.Event) -> None:
    turn = state.turn_number
    match event:
        case ev.DiceRolled(die1=d1, die2=d2):
            g.dice_histogram[d1 + d2] += 1
            if d1 + d2 != 7 and prev is not None:
                for pid in state.player_order:
                    for r in Resource:
                        gained = state.players[pid].resources[r] - prev.players[pid].resources[r]
                        if gained > 0:
                            g.players[pid].production[r] += gained
                    g.players[pid].expected_production += pip_equity(prev, pid) / 36
        case ev.DiscardedToRobber(player=p, resources=res):
            g.players[p].cards_discarded += sum(res.values())
        case ev.ResourceStolen(player=p, victim=vic):
            _steal(g, p, vic)
        case ev.KnightPlayed(player=p, victim=vic):
            g.players[p].knights_played += 1
            g.players[p].dev_played[DevCard.KNIGHT] += 1
            if vic is not None:
                _steal(g, p, vic)
        case ev.DevCardBought(player=p, card=c):
            g.players[p].dev_bought[c] += 1
        case ev.RoadBuildingPlayed(player=p):
            g.players[p].dev_played[DevCard.ROAD_BUILDING] += 1
        case ev.YearOfPlentyPlayed(player=p):
            g.players[p].dev_played[DevCard.YEAR_OF_PLENTY] += 1
        case ev.MonopolyPlayed(player=p):
            g.players[p].dev_played[DevCard.MONOPOLY] += 1
        case ev.DomesticTrade(player=p, partner=q, gave=gave, received=recv):
            g.players[p].trades_domestic += 1
            g.players[q].trades_domestic += 1
            _flow(g, p, gave, recv)
            _flow(g, q, recv, gave)
        case ev.MaritimeTrade(player=p, gave=gave, received=recv):
            g.players[p].trades_maritime += 1
            _flow(g, p, gave, recv)
        case ev.RoadBuilt(player=p) | ev.SetupRoadPlaced(player=p):
            g.players[p].builds.append((seq, turn, "road"))
        case ev.SettlementBuilt(player=p) | ev.SetupSettlementPlaced(player=p):
            g.players[p].builds.append((seq, turn, "settlement"))
        case ev.CityBuilt(player=p):
            g.players[p].builds.append((seq, turn, "city"))
        case _:
            pass


def _steal(g: GameMetrics, robber: PlayerId, victim: PlayerId) -> None:
    g.players[robber].steals_made += 1
    g.players[victim].cards_stolen_from_me += 1


def _flow(g: GameMetrics, pid: PlayerId, gave: dict[Resource, int], received: dict[Resource, int]) -> None:
    for r, a in received.items():
        g.players[pid].trade_net[r] += a
    for r, a in gave.items():
        g.players[pid].trade_net[r] -= a


def _snapshot(g: GameMetrics, state: GameState, seq: int) -> None:
    for pid in state.player_order:
        pm = g.players[pid]
        pm.vp_timeline.append((
            seq,
            state.victory_points(pid, include_hidden=True),
            state.victory_points(pid, include_hidden=False),
        ))
        pm.hand_timeline.append((seq, state.players[pid].hand_size))
        pm.pip_timeline.append((seq, pip_equity(state, pid)))
