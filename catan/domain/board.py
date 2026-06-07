"""Board assignment: terrains, number tokens, ports, and robber placement.

Topology (the hex/vertex/edge graph) comes from :mod:`catan.domain.geometry`.
This module layers the *content* of a base game onto that graph and supports
three ways to obtain a board (per the project decisions):

  * ``standard_board`` -- a fixed, reproducible layout using the official
    number-token spiral sequence. Terrains are dealt in pool order rather than
    arranged to match any official setup, so it is reproducible but *not* a
    faithful reproduction of a real table (use ``custom_board`` for that).
  * ``random_board`` -- a shuffled but rules-legal layout (the two red
    numbers, 6 and 8, are never placed on adjacent hexes).
  * ``custom_board`` -- an explicit layout entered from the physical board on
    your table, so the engine tracks the exact game you are playing.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass, field

from .constants import (
    NUMBER_TOKEN_COUNTS,
    PORT_COUNTS,
    PORT_TRADE_RATIO,
    PORT_TYPE_RESOURCE,
    STANDARD_NUMBER_SEQUENCE,
    STANDARD_PORT_SEQUENCE,
    TERRAIN_COUNTS,
    Resource,
    PortType,
    Terrain,
)
from .geometry import BoardTopology, Coord, VertexKey, build_topology

RED_NUMBERS = frozenset({6, 8})


def vertex_position(vk: VertexKey) -> tuple[float, float]:
    """Pixel position of a vertex = average of its (up to 3) hex centers."""
    pts = [_hex_center(c) for c in vk]
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def _hex_center(c: Coord) -> tuple[float, float]:
    q, r = c
    return (math.sqrt(3) * (q + r / 2), 1.5 * r)


def _angle(c: Coord) -> float:
    x, y = _hex_center(c)
    return math.atan2(y, x)


@dataclass(frozen=True)
class Port:
    type: PortType
    vertices: frozenset[int]   # settlements on either vertex may use this port

    @property
    def ratio(self) -> int:
        return PORT_TRADE_RATIO[self.type]

    @property
    def resource(self) -> Resource | None:
        return PORT_TYPE_RESOURCE[self.type]


@dataclass(frozen=True)
class Board:
    topology: BoardTopology
    terrain: dict[Coord, Terrain]
    numbers: dict[Coord, int]          # desert is absent (no token)
    ports: list[Port]
    robber: Coord                      # starts on the desert
    pips: dict[Coord, int] = field(default_factory=dict)


def _spiral_order(topology: BoardTopology) -> list[Coord]:
    """Hexes ordered outer-ring -> inner-ring -> center, by angle within a ring."""
    from .geometry import hex_distance

    rings: dict[int, list[Coord]] = {}
    for h in topology.hexes:
        d = hex_distance(h, (0, 0))
        rings.setdefault(d, []).append(h)
    ordered: list[Coord] = []
    for d in sorted(rings, reverse=True):
        ordered.extend(sorted(rings[d], key=_angle))
    return ordered


def _perimeter_edges(topology: BoardTopology) -> list[int]:
    """Edge ids that border exactly one on-board hex, ordered around the ring."""
    perim: list[tuple[float, int]] = []
    for eid, (a, b) in topology.edge_vertices.items():
        shared = topology.vertex_hexes[a] & topology.vertex_hexes[b]
        if len(shared) == 1:
            pa = vertex_position(topology.vertices[a])
            pb = vertex_position(topology.vertices[b])
            mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            perim.append((math.atan2(mid[1], mid[0]), eid))
    perim.sort()
    return [eid for _, eid in perim]


def _port_slot_indices(perim_len: int, count: int = 9) -> list[int]:
    """Indices into ``_perimeter_edges`` for the nine evenly spaced port docks."""
    return [round(i * perim_len / count) % perim_len for i in range(count)]


def _standard_port_slot_order(perim_len: int) -> list[int]:
    """Perimeter indices for docks clockwise from top-left (base-game frame)."""
    slots = _port_slot_indices(perim_len)
    # Even-spread slot order runs atan2 ascending (lower-left first); remap to
    # clockwise-from-top-left using the fixed base-board dock ring.
    return [slots[8], slots[7], slots[6], slots[5], slots[4], slots[3], slots[2], slots[1], slots[0]]


def _place_ports(topology: BoardTopology, port_types: list[PortType]) -> list[Port]:
    """Spread the 9 ports evenly across the perimeter edges."""
    perim = _perimeter_edges(topology)
    slots = _port_slot_indices(len(perim))
    ports: list[Port] = []
    for i, ptype in enumerate(port_types):
        eid = perim[slots[i]]
        a, b = topology.edge_vertices[eid]
        ports.append(Port(type=ptype, vertices=frozenset((a, b))))
    return ports


def standard_port_edges(topology: BoardTopology) -> list[tuple[PortType, int]]:
    """``(type, edge-id)`` pairs for the official clockwise port layout."""
    perim = _perimeter_edges(topology)
    order = _standard_port_slot_order(len(perim))
    types = [_parse_port(t) for t in STANDARD_PORT_SEQUENCE]
    return [(types[i], perim[order[i]]) for i in range(len(types))]


def place_standard_ports(topology: BoardTopology) -> list[Port]:
    """Nine ports on the base-board docks in ``STANDARD_PORT_SEQUENCE`` order."""
    return _ports_on_edges(topology, standard_port_edges(topology))


def _ports_on_edges(
    topology: BoardTopology, placements: list[tuple[PortType | str, int]]
) -> list[Port]:
    """Build ports from explicit ``(type, perimeter-edge-id)`` placements.

    Enforces the base-game distribution (four 3:1 generic plus one 2:1 per
    resource), one port per edge, and that every edge is on the board's
    perimeter -- so a hand-placed layout is still a legal board.
    """
    perim = set(_perimeter_edges(topology))
    parsed = [(_parse_port(t), int(e)) for t, e in placements]
    if Counter(t for t, _ in parsed) != Counter(PORT_COUNTS):
        raise ValueError("port counts do not match the base game")
    edges = [e for _, e in parsed]
    if len(set(edges)) != len(edges):
        raise ValueError("two ports placed on the same edge")
    off_board = [e for e in edges if e not in perim]
    if off_board:
        raise ValueError(f"ports must sit on perimeter edges (got {off_board})")
    return [
        Port(type=t, vertices=frozenset(topology.edge_vertices[e])) for t, e in parsed
    ]


def _terrain_pool() -> list[Terrain]:
    pool: list[Terrain] = []
    for terrain, n in TERRAIN_COUNTS.items():
        pool.extend([terrain] * n)
    return pool


def _number_pool() -> list[int]:
    pool: list[int] = []
    for num, n in NUMBER_TOKEN_COUNTS.items():
        pool.extend([num] * n)
    return pool


def _port_type_pool() -> list[PortType]:
    pool: list[PortType] = []
    for ptype, n in PORT_COUNTS.items():
        pool.extend([ptype] * n)
    return pool


def _compute_pips(numbers: dict[Coord, int]) -> dict[Coord, int]:
    from .constants import PIPS

    return {h: PIPS[num] for h, num in numbers.items()}


def _assign(
    topology: BoardTopology,
    terrains: list[Terrain],
    numbers_in_spiral: list[int],
    ports: list[Port],
) -> Board:
    spiral = _spiral_order(topology)
    terrain = dict(zip(spiral, terrains, strict=True))

    desert = next(h for h, t in terrain.items() if t is Terrain.DESERT)

    numbers: dict[Coord, int] = {}
    seq = iter(numbers_in_spiral)
    for h in spiral:
        if terrain[h] is Terrain.DESERT:
            continue
        numbers[h] = next(seq)

    return Board(
        topology=topology,
        terrain=terrain,
        numbers=numbers,
        ports=ports,
        robber=desert,
        pips=_compute_pips(numbers),
    )


def standard_board() -> Board:
    """Reproducible board using the official number-token spiral sequence.

    The desert is fixed at the center so the 18-number spiral maps cleanly onto
    the 18 producing hexes. Terrains are dealt in pool order (all four forests
    together, etc.), so this is a reproducible board rather than a faithful copy
    of any official setup. To track the real board on your table, enter it with
    :func:`custom_board`.
    """
    topology = build_topology()
    spiral = _spiral_order(topology)

    # Center hex (last in spiral) is the desert; the rest cycle the terrain pool.
    producing = [t for t in _terrain_pool() if t is not Terrain.DESERT]
    terrains = producing[: len(spiral) - 1] + [Terrain.DESERT]

    ports = place_standard_ports(topology)
    return _assign(topology, terrains, STANDARD_NUMBER_SEQUENCE, ports)


def _has_adjacent_red(board_topology: BoardTopology, numbers: dict[Coord, int]) -> bool:
    from .geometry import DIRECTIONS

    for h, num in numbers.items():
        if num not in RED_NUMBERS:
            continue
        for d in DIRECTIONS:
            nb = (h[0] + d[0], h[1] + d[1])
            if numbers.get(nb) in RED_NUMBERS:
                return True
    return False


def random_board(rng: random.Random | None = None) -> Board:
    """Shuffled, rules-legal board (6 and 8 never adjacent).

    Only the terrain tiles and number tokens are randomized; ports stay on
    their official standard docks (matching the physical pieces, which are
    glued to the frame and not reshuffled for casual random games).
    """
    rng = rng or random.Random()
    topology = build_topology()

    terrains = _terrain_pool()
    numbers_pool = _number_pool()
    ports = place_standard_ports(topology)

    for _ in range(1000):
        rng.shuffle(terrains)
        rng.shuffle(numbers_pool)
        board = _assign(topology, list(terrains), list(numbers_pool), ports)
        if not _has_adjacent_red(topology, board.numbers):
            return board
    # Extremely unlikely; surface rather than silently return an illegal board.
    raise RuntimeError("Could not generate a board without adjacent red numbers.")


_TERRAIN_ALIASES: dict[str, Terrain] = {
    "hills": Terrain.HILLS, "brick": Terrain.HILLS, "clay": Terrain.HILLS,
    "forest": Terrain.FOREST, "lumber": Terrain.FOREST, "wood": Terrain.FOREST,
    "pasture": Terrain.PASTURE, "wool": Terrain.PASTURE, "sheep": Terrain.PASTURE,
    "fields": Terrain.FIELDS, "grain": Terrain.FIELDS, "wheat": Terrain.FIELDS,
    "mountains": Terrain.MOUNTAINS, "ore": Terrain.MOUNTAINS, "rock": Terrain.MOUNTAINS,
    "desert": Terrain.DESERT,
}

_PORT_ALIASES: dict[str, PortType] = {
    "generic": PortType.GENERIC, "any": PortType.GENERIC, "3:1": PortType.GENERIC,
    "brick": PortType.BRICK, "lumber": PortType.LUMBER, "wool": PortType.WOOL,
    "grain": PortType.GRAIN, "ore": PortType.ORE,
}


def _parse_terrain(value: Terrain | str) -> Terrain:
    if isinstance(value, Terrain):
        return value
    try:
        return _TERRAIN_ALIASES[str(value).strip().lower()]
    except KeyError:
        raise ValueError(f"unknown terrain '{value}'") from None


def _parse_port(value: PortType | str) -> PortType:
    if isinstance(value, PortType):
        return value
    try:
        return _PORT_ALIASES[str(value).strip().lower()]
    except KeyError:
        raise ValueError(f"unknown port type '{value}'") from None


def custom_board(
    terrains: list[Terrain | str],
    numbers: list[int],
    port_types: list[PortType | str] | None = None,
    port_edges: list[tuple[PortType | str, int]] | None = None,
) -> Board:
    """Build the exact board sitting on your table from a layout you enter.

    The board is read in *spiral order* -- the same outer-ring-to-center order
    as the official A-R number-token sequence:

      * ``terrains``: the 19 hex terrains in spiral order. Names accept common
        synonyms (e.g. ``"wood"`` for forest, ``"wheat"`` for fields).
      * ``numbers``: the 18 number tokens in that same spiral order, skipping
        whichever hex you marked as the desert.
      * ``port_edges``: optionally the 9 ports as explicit ``(type, edge-id)``
        placements -- lets you put each port on the exact perimeter edge it
        occupies on your table.
      * ``port_types``: optionally the 9 ports in perimeter order; when both
        port arguments are omitted they are spread evenly using the standard
        port distribution.

    Counts must match the base game exactly, which catches most entry mistakes.
    """
    topology = build_topology()
    spiral = _spiral_order(topology)

    terr = [_parse_terrain(t) for t in terrains]
    if len(terr) != len(spiral):
        raise ValueError(f"expected {len(spiral)} terrains, got {len(terr)}")
    if Counter(terr) != Counter(TERRAIN_COUNTS):
        raise ValueError("terrain counts do not match the base game")

    expected = sum(NUMBER_TOKEN_COUNTS.values())
    nums = list(numbers)
    if len(nums) != expected:
        raise ValueError(f"expected {expected} number tokens, got {len(nums)}")
    if Counter(nums) != Counter(NUMBER_TOKEN_COUNTS):
        raise ValueError("number-token counts do not match the base game")

    if port_edges is not None:
        ports = _ports_on_edges(topology, port_edges)
    elif port_types is None:
        ports = _place_ports(topology, _port_type_pool())
    else:
        ptypes = [_parse_port(p) for p in port_types]
        if Counter(ptypes) != Counter(PORT_COUNTS):
            raise ValueError("port counts do not match the base game")
        ports = _place_ports(topology, ptypes)

    return _assign(topology, terr, nums, ports)
