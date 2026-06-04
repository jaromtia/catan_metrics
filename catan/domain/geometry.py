"""Hex-grid geometry for the standard Catan board.

The board is a hexagon of hexes with radius 2 (rows of 3-4-5-4-3 = 19 hexes).
We use axial coordinates ``(q, r)`` for hexes and derive vertices and edges
purely from hex adjacency, so the topology is computed rather than hand-coded.

Canonical identity trick:
  * A vertex is the meeting point of up to three mutually-adjacent hexes, so we
    identify it by the ``frozenset`` of those three hex coordinates. The same
    corner computed from any of its surrounding hexes yields the same frozenset.
  * An edge connects two consecutive corners of a hex, so we identify it by the
    ``frozenset`` of its two vertex identities.

After collection, vertices and edges are assigned stable integer ids by sorting
on a deterministic key, so ids are reproducible across runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

Coord = tuple[int, int]            # axial hex coordinate (q, r)
VertexKey = frozenset[Coord]       # the (up to 3) hexes meeting at a vertex
EdgeKey = frozenset[VertexKey]     # the two vertices an edge connects

# Pointy-top neighbor directions, ordered around the hex. Consecutive
# directions flank a shared corner; the edge on side k borders neighbor k.
DIRECTIONS: tuple[Coord, ...] = (
    (+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1),
)

BOARD_RADIUS = 2


def hex_distance(a: Coord, b: Coord) -> int:
    aq, ar = a
    bq, br = b
    return (abs(aq - bq) + abs(aq + ar - bq - br) + abs(ar - br)) // 2


def standard_hexes() -> list[Coord]:
    """The 19 hex coordinates of the base board (radius-2 hexagon)."""
    center: Coord = (0, 0)
    hexes = [
        (q, r)
        for q in range(-BOARD_RADIUS, BOARD_RADIUS + 1)
        for r in range(-BOARD_RADIUS, BOARD_RADIUS + 1)
        if hex_distance((q, r), center) <= BOARD_RADIUS
    ]
    return sorted(hexes)


def _add(a: Coord, b: Coord) -> Coord:
    return (a[0] + b[0], a[1] + b[1])


def _corner(h: Coord, k: int) -> VertexKey:
    """Vertex at corner ``k`` of hex ``h`` (between directions k and k+1)."""
    return frozenset((h, _add(h, DIRECTIONS[k]), _add(h, DIRECTIONS[(k + 1) % 6])))


def _vertex_sort_key(v: VertexKey) -> tuple:
    return tuple(sorted(v))


@dataclass(frozen=True)
class BoardTopology:
    """Immutable board graph: hexes, vertices, edges, and adjacency maps."""

    hexes: list[Coord]
    vertices: dict[int, VertexKey]
    edges: list[tuple[int, int]]                      # (vertex id, vertex id), sorted
    vertex_id: dict[VertexKey, int] = field(repr=False)
    vertex_neighbors: dict[int, frozenset[int]] = field(repr=False)
    vertex_edges: dict[int, frozenset[int]] = field(repr=False)
    vertex_hexes: dict[int, frozenset[Coord]] = field(repr=False)
    hex_vertices: dict[Coord, frozenset[int]] = field(repr=False)
    edge_vertices: dict[int, tuple[int, int]] = field(repr=False)

    def is_adjacent(self, v1: int, v2: int) -> bool:
        return v2 in self.vertex_neighbors[v1]


def build_topology(hexes: list[Coord] | None = None) -> BoardTopology:
    hex_list = hexes if hexes is not None else standard_hexes()
    hex_set = set(hex_list)

    # Collect every distinct corner across all on-board hexes.
    corner_keys: set[VertexKey] = set()
    for h in hex_list:
        for k in range(6):
            corner_keys.add(_corner(h, k))

    ordered_vertices = sorted(corner_keys, key=_vertex_sort_key)
    vertices = {i: vk for i, vk in enumerate(ordered_vertices)}
    vertex_id = {vk: i for i, vk in vertices.items()}

    # Edges: consecutive corners of each hex share an edge.
    edge_keys: set[EdgeKey] = set()
    for h in hex_list:
        for k in range(6):
            edge_keys.add(frozenset((_corner(h, k), _corner(h, (k + 1) % 6))))

    edges: list[tuple[int, int]] = []
    edge_vertices: dict[int, tuple[int, int]] = {}
    for ek in edge_keys:
        a, b = sorted(vertex_id[vk] for vk in ek)
        edges.append((a, b))
    edges.sort()
    for eid, (a, b) in enumerate(edges):
        edge_vertices[eid] = (a, b)

    # Adjacency maps.
    vertex_neighbors: dict[int, set[int]] = {i: set() for i in vertices}
    vertex_edges: dict[int, set[int]] = {i: set() for i in vertices}
    for eid, (a, b) in edge_vertices.items():
        vertex_neighbors[a].add(b)
        vertex_neighbors[b].add(a)
        vertex_edges[a].add(eid)
        vertex_edges[b].add(eid)

    vertex_hexes: dict[int, frozenset[Coord]] = {
        i: frozenset(c for c in vk if c in hex_set) for i, vk in vertices.items()
    }
    hex_vertices: dict[Coord, set[int]] = {h: set() for h in hex_list}
    for i, hs in vertex_hexes.items():
        for h in hs:
            hex_vertices[h].add(i)

    return BoardTopology(
        hexes=hex_list,
        vertices=vertices,
        edges=edges,
        vertex_id=vertex_id,
        vertex_neighbors={i: frozenset(s) for i, s in vertex_neighbors.items()},
        vertex_edges={i: frozenset(s) for i, s in vertex_edges.items()},
        vertex_hexes=vertex_hexes,
        hex_vertices={h: frozenset(s) for h, s in hex_vertices.items()},
        edge_vertices=edge_vertices,
    )
