"""Base-game Catan constants, sourced from the official 2020 base rules.

Every count here is authoritative for the 3-4 player base game and is used by
the engine to validate moves and reconcile the bank.
"""

from __future__ import annotations

from enum import Enum


class Resource(str, Enum):
    BRICK = "brick"
    LUMBER = "lumber"
    WOOL = "wool"
    GRAIN = "grain"
    ORE = "ore"


class Terrain(str, Enum):
    HILLS = "hills"        # produces brick
    FOREST = "forest"      # produces lumber
    PASTURE = "pasture"    # produces wool
    FIELDS = "fields"      # produces grain
    MOUNTAINS = "mountains"  # produces ore
    DESERT = "desert"      # produces nothing


TERRAIN_RESOURCE: dict[Terrain, Resource | None] = {
    Terrain.HILLS: Resource.BRICK,
    Terrain.FOREST: Resource.LUMBER,
    Terrain.PASTURE: Resource.WOOL,
    Terrain.FIELDS: Resource.GRAIN,
    Terrain.MOUNTAINS: Resource.ORE,
    Terrain.DESERT: None,
}

# 19 hexes total.
TERRAIN_COUNTS: dict[Terrain, int] = {
    Terrain.FOREST: 4,
    Terrain.FIELDS: 4,
    Terrain.PASTURE: 4,
    Terrain.HILLS: 3,
    Terrain.MOUNTAINS: 3,
    Terrain.DESERT: 1,
}

# 18 number tokens (the desert gets none). No 7.
NUMBER_TOKEN_COUNTS: dict[int, int] = {
    2: 1, 3: 2, 4: 2, 5: 2, 6: 2,
    8: 2, 9: 2, 10: 2, 11: 2, 12: 1,
}

# "Pips" = dots on the token = number of dice combinations / 36 chance.
PIPS: dict[int, int] = {
    2: 1, 3: 2, 4: 3, 5: 4, 6: 5,
    7: 0,
    8: 5, 9: 4, 10: 3, 11: 2, 12: 1,
}

# Official starting layout: number tokens placed in spiral order (A-R) using
# this exact sequence (high-value 6/8 tokens are kept apart by this ordering).
STANDARD_NUMBER_SEQUENCE: list[int] = [
    5, 2, 6, 3, 8, 10, 9, 12, 11, 4, 8, 10, 9, 4, 5, 6, 3, 11,
]

# Bank holds 19 cards of each resource.
BANK_RESOURCE_COUNT = 19

# Development card deck (25 total).
class DevCard(str, Enum):
    KNIGHT = "knight"
    VICTORY_POINT = "victory_point"
    ROAD_BUILDING = "road_building"
    YEAR_OF_PLENTY = "year_of_plenty"
    MONOPOLY = "monopoly"


DEV_CARD_COUNTS: dict[DevCard, int] = {
    DevCard.KNIGHT: 14,
    DevCard.VICTORY_POINT: 5,
    DevCard.ROAD_BUILDING: 2,
    DevCard.YEAR_OF_PLENTY: 2,
    DevCard.MONOPOLY: 2,
}

# Total cards in the development deck (25). A purchase is recorded without
# observing the drawn type (it stays hidden in the buyer's hand); the type is
# only learned when the card is later played or revealed, so the deck is tracked
# as a single remaining count rather than per type.
DEV_DECK_SIZE = sum(DEV_CARD_COUNTS.values())

# Pieces available to each player.
SETTLEMENTS_PER_PLAYER = 5
CITIES_PER_PLAYER = 4
ROADS_PER_PLAYER = 15

# Build costs (resource -> quantity).
ROAD_COST: dict[Resource, int] = {Resource.BRICK: 1, Resource.LUMBER: 1}
SETTLEMENT_COST: dict[Resource, int] = {
    Resource.BRICK: 1,
    Resource.LUMBER: 1,
    Resource.WOOL: 1,
    Resource.GRAIN: 1,
}
CITY_COST: dict[Resource, int] = {Resource.ORE: 3, Resource.GRAIN: 2}
DEV_CARD_COST: dict[Resource, int] = {
    Resource.ORE: 1,
    Resource.WOOL: 1,
    Resource.GRAIN: 1,
}

# Victory conditions and awards.
VICTORY_POINTS_TO_WIN = 10
LONGEST_ROAD_MIN = 5      # minimum road length to claim Longest Road
LONGEST_ROAD_VP = 2
LARGEST_ARMY_MIN = 3      # minimum knights played to claim Largest Army
LARGEST_ARMY_VP = 2

# Robber / discard rule.
ROBBER_DISCARD_THRESHOLD = 7  # players with > 7 cards discard half on a 7.


class PortType(str, Enum):
    GENERIC = "generic"        # 3:1 any resource
    BRICK = "brick"            # 2:1 brick
    LUMBER = "lumber"          # 2:1 lumber
    WOOL = "wool"              # 2:1 wool
    GRAIN = "grain"            # 2:1 grain
    ORE = "ore"                # 2:1 ore


PORT_TYPE_RESOURCE: dict[PortType, Resource | None] = {
    PortType.GENERIC: None,
    PortType.BRICK: Resource.BRICK,
    PortType.LUMBER: Resource.LUMBER,
    PortType.WOOL: Resource.WOOL,
    PortType.GRAIN: Resource.GRAIN,
    PortType.ORE: Resource.ORE,
}

PORT_TRADE_RATIO: dict[PortType, int] = {
    PortType.GENERIC: 3,
    PortType.BRICK: 2,
    PortType.LUMBER: 2,
    PortType.WOOL: 2,
    PortType.GRAIN: 2,
    PortType.ORE: 2,
}

DEFAULT_BANK_TRADE_RATIO = 4  # 4:1 with no port.

# 9 ports total: four generic, one for each resource.
PORT_COUNTS: dict[PortType, int] = {
    PortType.GENERIC: 4,
    PortType.BRICK: 1,
    PortType.LUMBER: 1,
    PortType.WOOL: 1,
    PortType.GRAIN: 1,
    PortType.ORE: 1,
}

# Official port-type order clockwise from the top-left dock on the base board.
STANDARD_PORT_SEQUENCE: list[str] = [
    "generic",
    "wool",
    "generic",
    "generic",
    "brick",
    "lumber",
    "generic",
    "grain",
    "ore",
]

# Expected board topology (hexagon of radius 2).
HEX_COUNT = 19
VERTEX_COUNT = 54
EDGE_COUNT = 72
