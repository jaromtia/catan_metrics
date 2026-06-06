# Appendix B — Hex Grid Mathematics

This appendix is a *reference* for the coordinate system, not a solution. It gives you the math you need; assembling it into `build_topology` (Lab 1) is your job.

---

## Axial Coordinates

Hex grids can be addressed with two axes `(q, r)`:

```
         (-1,-1)   (0,-1)   (1,-1)
       (-1, 0)   (0, 0)   (1, 0)
         (-1, 1)   (0, 1)   (1, 1)
```

In this project `Coord` is a plain `tuple[int, int]` (a type alias, **not** a NamedTuple). Access components with `coord[0]` (q) and `coord[1]` (r).

---

## Six Neighbor Directions

The 6 hex neighbors, ordered clockwise starting from east:

```python
DIRECTIONS = (
    (+1,  0),   # E
    (+1, -1),   # NE
    ( 0, -1),   # NW
    (-1,  0),   # W
    (-1, +1),   # SW
    ( 0, +1),   # SE
)
```

The neighbors of `(q, r)` are `(q + dq, r + dr)` for each `(dq, dr)` in `DIRECTIONS`.

---

## Hex Distance

The axial distance between two hexes:

```
distance(a, b) = (|aq - bq| + |aq + ar - bq - br| + |ar - br|) / 2
```

The standard 19-hex board is every hex within distance 2 of the center `(0, 0)`. Generate those coordinates (sorted, for reproducibility) — that is `standard_hexes()`.

---

## Vertex Identity (the key insight for `build_topology`)

A vertex is the meeting point of up to three hexes. The trick that makes the topology easy: **identify a vertex by the frozenset of the hexes that touch it.**

A corner "k" of a hex `h` lies between neighbor direction `k` and direction `k+1`. So the three hexes meeting at that corner are `h` itself, the neighbor in direction `k`, and the neighbor in direction `(k+1) % 6`. Bundle those three coordinates into a `frozenset` and you have a stable vertex key:

```
VertexKey = frozenset[Coord]   # the up-to-3 hexes meeting at a corner
```

Because the *same* corner computed from any of its surrounding hexes yields the *same* frozenset, you can collect every vertex by walking all six corners of every hex and deduplicating. **You must write the corner function and the collection loop yourself.**

An edge connects two consecutive corners of a hex; identify it by the frozenset of its two `VertexKey`s.

---

## Stable Integer IDs

After collecting the unique vertex keys and edge keys, assign integer IDs by **sorting** the keys with a deterministic sort key (e.g. `sorted(vk)` as a tuple) and enumerating. Sorting first makes IDs reproducible across runs — your tests will depend on that.

---

## Expected Topology for the Standard Board

| Entity | Count |
|--------|-------|
| Hexes | 19 |
| Vertices | 54 |
| Edges | 72 |

Two useful invariants to test:
- Every hex maps to exactly 6 vertices.
- Handshake lemma: the sum of all vertex degrees equals `2 × edge_count`.

---

## Axial to Pixel

To render the board you convert each hex coordinate to a pixel center. Pick **one** orientation and use it everywhere.

Pointy-top:
```
x = size * √3 * (q + r/2)
y = size * (3/2 * r)
```

The six corners of a pointy-top hex centered at `(cx, cy)` are at angles `60° × i - 30°` for `i = 0..5`:
```
corner_x = cx + size * cos(angle)
corner_y = cy + size * sin(angle)
```

Flat-top uses `angle = 60° × i` instead. The two produce different visual layouts — choose one and stay consistent.

---

## Further Reading

- [Hexagonal Grids by Amit Patel](https://www.redblobgames.com/grids/hexagons/) — the definitive reference, with interactive demos covering axial, cube, and offset coordinates. Read this before attempting `build_topology`.
