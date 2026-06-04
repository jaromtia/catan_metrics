"""Topology integrity tests for the standard board graph."""

from catan.domain.constants import EDGE_COUNT, HEX_COUNT, VERTEX_COUNT
from catan.domain.geometry import build_topology, standard_hexes


def topology():
    return build_topology()


def test_hex_count():
    assert len(standard_hexes()) == HEX_COUNT


def test_vertex_count():
    assert len(topology().vertices) == VERTEX_COUNT


def test_edge_count():
    assert len(topology().edges) == EDGE_COUNT


def test_vertex_degrees_are_two_or_three():
    topo = topology()
    degrees = {len(n) for n in topo.vertex_neighbors.values()}
    assert degrees <= {2, 3}


def test_sum_of_vertex_degrees_equals_twice_edges():
    topo = topology()
    total = sum(len(n) for n in topo.vertex_neighbors.values())
    assert total == 2 * EDGE_COUNT


def test_vertex_degree_matches_hex_membership():
    topo = topology()
    # Outer-corner vertices touch a single hex and have degree 2; any vertex
    # touching all three of its hexes is fully interior and has degree 3.
    for vid, neighbors in topo.vertex_neighbors.items():
        if len(neighbors) == 2:
            assert len(topo.vertex_hexes[vid]) == 1
        if len(topo.vertex_hexes[vid]) == 3:
            assert len(neighbors) == 3


def test_adjacency_is_symmetric():
    topo = topology()
    for vid, neighbors in topo.vertex_neighbors.items():
        for other in neighbors:
            assert vid in topo.vertex_neighbors[other]


def test_every_hex_has_six_vertices():
    topo = topology()
    for h in topo.hexes:
        assert len(topo.hex_vertices[h]) == 6


def test_edge_vertices_are_adjacent():
    topo = topology()
    for a, b in topo.edges:
        assert topo.is_adjacent(a, b)
