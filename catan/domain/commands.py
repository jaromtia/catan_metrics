"""The command catalog.

Commands express *intent*. They are the only thing the outside world (CLI, API)
submits. The validator (:mod:`catan.engine.validate`) checks a command against
the current state and the rules, and on success produces one or more
:mod:`~catan.domain.events` to be folded by the reducer.

Commands are deliberately close to events but distinct: a command may be
rejected, may require derivation (e.g. a maritime ratio is looked up, not
trusted), and a single command may expand into several events (e.g. moving the
robber and stealing).
"""

from __future__ import annotations

from dataclasses import dataclass

from .board import Board
from .constants import DevCard, Resource

PlayerId = str
Coord = tuple[int, int]
ResourceMap = dict[Resource, int]


@dataclass(frozen=True)
class CreateGame:
    board: Board
    player_order: tuple[PlayerId, ...]


@dataclass(frozen=True)
class PlaceSetupSettlement:
    player: PlayerId
    vertex: int


@dataclass(frozen=True)
class PlaceSetupRoad:
    player: PlayerId
    edge: int


@dataclass(frozen=True)
class RollDice:
    player: PlayerId
    die1: int
    die2: int


@dataclass(frozen=True)
class EndTurn:
    player: PlayerId


@dataclass(frozen=True)
class Discard:
    player: PlayerId
    resources: ResourceMap


@dataclass(frozen=True)
class MoveRobber:
    player: PlayerId
    hex: Coord
    victim: PlayerId | None = None
    resource: Resource | None = None   # the observed stolen card


@dataclass(frozen=True)
class BuildRoad:
    player: PlayerId
    edge: int


@dataclass(frozen=True)
class BuildSettlement:
    player: PlayerId
    vertex: int


@dataclass(frozen=True)
class BuildCity:
    player: PlayerId
    vertex: int


@dataclass(frozen=True)
class BuyDevCard:
    player: PlayerId
    card: DevCard          # the card actually drawn (companion observes it)


@dataclass(frozen=True)
class PlayKnight:
    player: PlayerId
    hex: Coord
    victim: PlayerId | None = None
    resource: Resource | None = None


@dataclass(frozen=True)
class PlayRoadBuilding:
    player: PlayerId
    edges: tuple[int, ...]


@dataclass(frozen=True)
class PlayYearOfPlenty:
    player: PlayerId
    resources: tuple[Resource, Resource]


@dataclass(frozen=True)
class PlayMonopoly:
    player: PlayerId
    resource: Resource


@dataclass(frozen=True)
class TradeWithBank:
    player: PlayerId
    give: Resource
    give_amount: int
    receive: Resource
    receive_amount: int


@dataclass(frozen=True)
class TradeWithPlayer:
    player: PlayerId
    partner: PlayerId
    gave: ResourceMap          # player -> partner
    received: ResourceMap      # partner -> player


# --- Dev/sandbox admin (rejected in strict mode) ---------------------------

@dataclass(frozen=True)
class SetResources:
    """Set a player's hand to exact amounts (only the listed resources change)."""
    player: PlayerId
    resources: ResourceMap


@dataclass(frozen=True)
class SetVictoryPoints:
    """Set a player's manual VP adjustment (added to their derived score)."""
    player: PlayerId
    bonus: int


Command = (
    CreateGame
    | PlaceSetupSettlement
    | PlaceSetupRoad
    | RollDice
    | EndTurn
    | Discard
    | MoveRobber
    | BuildRoad
    | BuildSettlement
    | BuildCity
    | BuyDevCard
    | PlayKnight
    | PlayRoadBuilding
    | PlayYearOfPlenty
    | PlayMonopoly
    | TradeWithBank
    | TradeWithPlayer
    | SetResources
    | SetVictoryPoints
)
