"""Game state model.

State is never mutated in place by callers. The reducer produces a new state
for every event via :meth:`GameState.clone`, which deep-copies the mutable game
progress while *sharing* the immutable :class:`~catan.domain.board.Board`
(its topology dictionaries are large and never change mid-game).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .board import Board
from .constants import (
    BANK_RESOURCE_COUNT,
    CITIES_PER_PLAYER,
    DEV_DECK_SIZE,
    LARGEST_ARMY_VP,
    LONGEST_ROAD_VP,
    ROADS_PER_PLAYER,
    SETTLEMENTS_PER_PLAYER,
    DevCard,
    Resource,
)

PlayerId = str


class Phase(str, Enum):
    SETUP = "setup"
    PLAY = "play"
    FINISHED = "finished"


def _empty_resources() -> dict[Resource, int]:
    return {r: 0 for r in Resource}


@dataclass
class PlayerState:
    pid: PlayerId
    resources: dict[Resource, int] = field(default_factory=_empty_resources)
    # Cards drawn but not yet played/revealed. Their types are unknown to the
    # recorder, so they are tracked as a single count rather than per type.
    hidden_dev: int = 0
    # Known unplayed cards: only Victory Point cards land here, once revealed.
    dev_cards: dict[DevCard, int] = field(
        default_factory=lambda: {c: 0 for c in DevCard}
    )
    dev_cards_played: dict[DevCard, int] = field(
        default_factory=lambda: {c: 0 for c in DevCard}
    )
    knights_played: int = 0
    settlements: set[int] = field(default_factory=set)   # vertex ids
    cities: set[int] = field(default_factory=set)        # vertex ids
    roads: set[int] = field(default_factory=set)         # edge ids
    bonus_vp: int = 0   # dev-mode manual victory-point adjustment (+/-)

    def clone(self) -> PlayerState:
        return PlayerState(
            pid=self.pid,
            resources=dict(self.resources),
            hidden_dev=self.hidden_dev,
            dev_cards=dict(self.dev_cards),
            dev_cards_played=dict(self.dev_cards_played),
            knights_played=self.knights_played,
            settlements=set(self.settlements),
            cities=set(self.cities),
            roads=set(self.roads),
            bonus_vp=self.bonus_vp,
        )

    @property
    def hand_size(self) -> int:
        return sum(self.resources.values())

    @property
    def dev_cards_in_hand(self) -> int:
        """Unplayed development cards held: hidden draws + revealed VP cards."""
        return self.hidden_dev + sum(self.dev_cards.values())

    @property
    def settlements_left(self) -> int:
        return SETTLEMENTS_PER_PLAYER - len(self.settlements)

    @property
    def cities_left(self) -> int:
        return CITIES_PER_PLAYER - len(self.cities)

    @property
    def roads_left(self) -> int:
        return ROADS_PER_PLAYER - len(self.roads)


def _full_bank() -> dict[Resource, int]:
    return {r: BANK_RESOURCE_COUNT for r in Resource}


@dataclass
class GameState:
    board: Board
    player_order: list[PlayerId]
    players: dict[PlayerId, PlayerState]
    phase: Phase = Phase.SETUP
    current_index: int = 0
    turn_number: int = 0
    dice: tuple[int, int] | None = None
    has_rolled: bool = False
    bank: dict[Resource, int] = field(default_factory=_full_bank)
    dev_deck_size: int = DEV_DECK_SIZE   # cards remaining in the deck (type unknown)
    robber: tuple[int, int] | None = None
    longest_road_holder: PlayerId | None = None
    largest_army_holder: PlayerId | None = None
    winner: PlayerId | None = None

    # Turn-scoped flags maintained by the reducer, read by the validator.
    pending_discards: dict[PlayerId, int] = field(default_factory=dict)
    robber_pending: bool = False
    dev_played_this_turn: bool = False
    dev_bought_this_turn: int = 0   # cards drawn this turn (cannot be played yet)

    @classmethod
    def new(cls, board: Board, player_order: list[PlayerId]) -> GameState:
        return cls(
            board=board,
            player_order=list(player_order),
            players={pid: PlayerState(pid=pid) for pid in player_order},
            robber=board.robber,
        )

    def clone(self) -> GameState:
        return GameState(
            board=self.board,  # immutable, shared on purpose
            player_order=list(self.player_order),
            players={pid: ps.clone() for pid, ps in self.players.items()},
            phase=self.phase,
            current_index=self.current_index,
            turn_number=self.turn_number,
            dice=self.dice,
            has_rolled=self.has_rolled,
            bank=dict(self.bank),
            dev_deck_size=self.dev_deck_size,
            robber=self.robber,
            longest_road_holder=self.longest_road_holder,
            largest_army_holder=self.largest_army_holder,
            winner=self.winner,
            pending_discards=dict(self.pending_discards),
            robber_pending=self.robber_pending,
            dev_played_this_turn=self.dev_played_this_turn,
            dev_bought_this_turn=self.dev_bought_this_turn,
        )

    @property
    def current_player(self) -> PlayerId:
        return self.player_order[self.current_index]

    def owner_of_vertex(self, vertex: int) -> tuple[PlayerId, str] | None:
        """Return ``(player, 'settlement'|'city')`` occupying a vertex, else None."""
        for pid, ps in self.players.items():
            if vertex in ps.cities:
                return (pid, "city")
            if vertex in ps.settlements:
                return (pid, "settlement")
        return None

    def owner_of_edge(self, edge: int) -> PlayerId | None:
        for pid, ps in self.players.items():
            if edge in ps.roads:
                return pid
        return None

    def victory_points(self, pid: PlayerId, *, include_hidden: bool = True) -> int:
        ps = self.players[pid]
        vp = len(ps.settlements) + 2 * len(ps.cities)
        if self.longest_road_holder == pid:
            vp += LONGEST_ROAD_VP
        if self.largest_army_holder == pid:
            vp += LARGEST_ARMY_VP
        if include_hidden:
            vp += ps.dev_cards[DevCard.VICTORY_POINT]
        vp += ps.bonus_vp
        return vp
