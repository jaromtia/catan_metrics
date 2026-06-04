"""The event catalog.

Events are immutable payloads describing something that *happened* in the game.
They are the single source of truth: game state is a pure fold over the event
stream (see :mod:`catan.engine.reduce`). The persistence layer (Phase 4) wraps
each event with envelope metadata (sequence number, timestamp); these payloads
stay free of storage concerns.

Deterministic-consequence rule: anything the reducer can compute from current
state + the event is *not* stored on the event. For example ``DiceRolled`` only
carries the two dice; resource production is derived. ``MonopolyPlayed`` only
carries the chosen resource; the transfer amounts are derived.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .board import Board
from .constants import DevCard, Resource

PlayerId = str
Coord = tuple[int, int]
ResourceMap = dict[Resource, int]


# --- Lifecycle / setup -----------------------------------------------------

@dataclass(frozen=True)
class GameCreated:
    board: Board
    player_order: tuple[PlayerId, ...]


@dataclass(frozen=True)
class SetupSettlementPlaced:
    player: PlayerId
    vertex: int


@dataclass(frozen=True)
class SetupRoadPlaced:
    player: PlayerId
    edge: int


# --- Turns / dice ----------------------------------------------------------

@dataclass(frozen=True)
class DiceRolled:
    player: PlayerId
    die1: int
    die2: int

    @property
    def total(self) -> int:
        return self.die1 + self.die2


@dataclass(frozen=True)
class TurnEnded:
    player: PlayerId


# --- Robber / the 7 --------------------------------------------------------

@dataclass(frozen=True)
class DiscardedToRobber:
    player: PlayerId
    resources: ResourceMap


@dataclass(frozen=True)
class RobberMoved:
    player: PlayerId
    hex: Coord


@dataclass(frozen=True)
class ResourceStolen:
    player: PlayerId          # the one playing/rolling (gains the card)
    victim: PlayerId
    resource: Resource


# --- Trades ----------------------------------------------------------------

@dataclass(frozen=True)
class DomesticTrade:
    player: PlayerId
    partner: PlayerId
    gave: ResourceMap         # player -> partner
    received: ResourceMap     # partner -> player


@dataclass(frozen=True)
class MaritimeTrade:
    player: PlayerId
    gave: ResourceMap         # to the bank
    received: ResourceMap     # from the bank
    ratio: int


# --- Builds ----------------------------------------------------------------

@dataclass(frozen=True)
class RoadBuilt:
    player: PlayerId
    edge: int


@dataclass(frozen=True)
class SettlementBuilt:
    player: PlayerId
    vertex: int


@dataclass(frozen=True)
class CityBuilt:
    player: PlayerId
    vertex: int


# --- Development cards ------------------------------------------------------

@dataclass(frozen=True)
class DevCardBought:
    player: PlayerId
    card: DevCard


@dataclass(frozen=True)
class KnightPlayed:
    player: PlayerId
    hex: Coord                       # where the robber goes
    victim: PlayerId | None = None   # whom to steal from (None if no target)
    resource: Resource | None = None  # the stolen card (None if none stolen)


@dataclass(frozen=True)
class RoadBuildingPlayed:
    player: PlayerId
    edges: tuple[int, ...]           # up to two edges


@dataclass(frozen=True)
class YearOfPlentyPlayed:
    player: PlayerId
    resources: tuple[Resource, Resource]


@dataclass(frozen=True)
class MonopolyPlayed:
    player: PlayerId
    resource: Resource


@dataclass(frozen=True)
class VictoryPointRevealed:
    player: PlayerId


# --- Dev/sandbox admin overrides -------------------------------------------

@dataclass(frozen=True)
class ResourcesSet:
    player: PlayerId
    resources: ResourceMap     # absolute amounts for the listed resources


@dataclass(frozen=True)
class VictoryPointsSet:
    player: PlayerId
    bonus: int                 # absolute manual VP adjustment


Event = (
    GameCreated
    | SetupSettlementPlaced
    | SetupRoadPlaced
    | DiceRolled
    | TurnEnded
    | DiscardedToRobber
    | RobberMoved
    | ResourceStolen
    | DomesticTrade
    | MaritimeTrade
    | RoadBuilt
    | SettlementBuilt
    | CityBuilt
    | DevCardBought
    | KnightPlayed
    | RoadBuildingPlayed
    | YearOfPlentyPlayed
    | MonopolyPlayed
    | VictoryPointRevealed
    | ResourcesSet
    | VictoryPointsSet
)
