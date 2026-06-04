# Appendix B — Hex Grid Mathematics

This appendix explains the coordinate system and topology used in the engine.

---

## Axial Coordinates

Hex grids can be addressed with two axes `(q, r)`:

```
         (-1,-1)   (0,-1)   (1,-1)
       (-1, 0)   (0, 0)   (1, 0)
         (-1, 1)   (0, 1)   (1, 1)
```

### Type

```python
Coord = tuple[int, int]   # (q, r) — a type alias, not a class
```

Note: **not** a NamedTuple with named attributes. Access components with `coord[0]` (q) and `coord[1]` (r).

---

## Six Neighbor Directions

The 6 hex neighbors, ordered clockwise starting from east:

```python
DIRECTIONS: tuple[Coord, ...] = (
    (+1,  0),   # E
    (+1, -1),   # NE
    ( 0, -1),   # NW
    (-1,  0),   # W
    (-1, +1),   # SW
    ( 0, +1),   # SE
)
```

Neighbors of `(q, r)`:
```python
[(q + dq, r + dr) for dq, dr in DIRECTIONS]
```

---

## Hex Distance

```python
def hex_distance(a: Coord, b: Coord) -> int:
    aq, ar = a
    bq, br = b
    return (abs(aq - bq) + abs(aq + ar - bq - br) + abs(ar - br)) // 2
```

---

## Standard Catan Board (19 Hexes)

All hexes within distance 2 of center `(0, 0)`:

```python
BOARD_RADIUS = 2

def standard_hexes() -> list[Coord]:
    center: Coord = (0, 0)
    return sorted(
        (q, r)
        for q in range(-BOARD_RADIUS, BOARD_RADIUS + 1)
        for r in range(-BOARD_RADIUS, BOARD_RADIUS + 1)
        if hex_distance((q, r), center) <= BOARD_RADIUS
    )
# Returns 19 coordinates.
```

---

## Vertex Identity

A vertex is the meeting point of up to three hexes. We identify it by the **frozenset of those hexes**:

```python
VertexKey = frozenset[Coord]

def _corner(h: Coord, k: int) -> VertexKey:
    """Vertex at corner k of hex h."""
    return frozenset((
        h,
        (h[0] + DIRECTIONS[k][0],     h[1] + DIRECTIONS[k][1]),
        (h[0] + DIRECTIONS[(k+1)%6][0], h[1] + DIRECTIONS[(k+1)%6][1]),
    ))
```

The same vertex computed from any of its surrounding hexes yields the same frozenset. This lets us collect all vertices by iterating all hex corners and deduplicating.

---

## Edge Identity

An edge connects two consecutive corners of a hex. We identify it by the **frozenset of its two vertex identities**:

```python
EdgeKey = frozenset[VertexKey]

# For hex h, the edge between corners k and (k+1):
edge_key = frozenset((_corner(h, k), _corner(h, (k+1) % 6)))
```

---

## Integer IDs

After collecting all unique `VertexKey` and `EdgeKey` sets, we assign stable integer IDs by sorting on a deterministic key:

```python
ordered_vertices = sorted(corner_keys, key=lambda vk: tuple(sorted(vk)))
vertices  = {i: vk for i, vk in enumerate(ordered_vertices)}
vertex_id = {vk: i for i, vk in vertices.items()}
```

This gives reproducible IDs across runs.

---

## Expected Topology for Standard Board

| Entity | Count | Why |
|--------|-------|-----|
| Hexes | 19 | Hexagon of radius 2 |
| Vertices | 54 | Inner land vertices + outer border |
| Edges | 72 | Inner + border edges |

Verify with:
```python
assert len(topo.vertices) == 54
assert len(topo.edges)    == 72
```

---

## Axial to Pixel (Pointy-Top Orientation)

Convert hex coordinate to pixel center point:

```python
import math

def hex_to_pixel(coord: Coord, size: float = 60.0) -> tuple[float, float]:
    q, r = coord
    x = size * math.sqrt(3) * (q + r / 2)
    y = size * (3 / 2 * r)
    return x, y
```

The 6 corners of a pointy-top hex centered at `(cx, cy)`:

```python
def hex_corners(cx: float, cy: float, size: float = 60.0) -> list[tuple[float, float]]:
    return [
        (cx + size * math.cos(math.radians(60 * i - 30)),
         cy + size * math.sin(math.radians(60 * i - 30)))
        for i in range(6)
    ]
```

> **Pointy-top vs flat-top:** The reference implementation uses pointy-top orientation (`angle - 30°`). Flat-top uses `angle = 60° * i`. They produce different visual layouts. Pick one and stay consistent throughout.

---

## Vertex Degrees

On a standard board:
- **Degree-2 vertices** touch exactly 1 hex (border corners)
- **Degree-3 vertices** touch exactly 3 hexes (interior corners)

The handshake lemma: `sum of all vertex degrees == 2 × edge_count`

```python
# Useful test assertion:
total_degree = sum(len(neighbors) for neighbors in topo.vertex_neighbors.values())
assert total_degree == 2 * len(topo.edges)
```

---

## Further Reading

- [Hexagonal Grids by Amit Patel](https://www.redblobgames.com/grids/hexagons/) — the definitive reference with interactive demos, covering axial, cube, and offset coordinates.
