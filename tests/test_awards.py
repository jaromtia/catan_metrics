"""Longest Road and Largest Army computation."""

from catan.domain.board import standard_board
from catan.domain.state import GameState
from catan.engine.awards import (
    longest_road_length,
    recompute_longest_road,
    update_largest_army,
)

PLAYERS = ("red", "blue", "white")


def state():
    return GameState.new(standard_board(), list(PLAYERS))


def road_path(topo, length):
    """Return (edge_ids, vertex_ids) for a connected path of ``length`` edges."""
    start = next(iter(topo.vertex_neighbors))
    visited = [start]
    edges = []
    current = start
    while len(edges) < length:
        nxt = None
        for cand in topo.vertex_neighbors[current]:
            if cand not in visited:
                nxt = cand
                break
        assert nxt is not None, "ran out of unvisited neighbors"
        for eid, (a, b) in topo.edge_vertices.items():
            if {a, b} == {current, nxt}:
                edges.append(eid)
                break
        visited.append(nxt)
        current = nxt
    return edges, visited


def test_longest_road_counts_a_straight_path():
    s = state()
    topo = s.board.topology
    edges, _ = road_path(topo, 5)
    s.players["red"].roads.update(edges)
    assert longest_road_length(s, "red") == 5


def test_longest_road_awarded_at_five():
    s = state()
    edges, _ = road_path(s.board.topology, 5)
    s.players["red"].roads.update(edges)
    assert recompute_longest_road(s) == "red"


def test_four_road_segments_do_not_qualify():
    s = state()
    edges, _ = road_path(s.board.topology, 4)
    s.players["red"].roads.update(edges)
    assert recompute_longest_road(s) is None


def test_opponent_settlement_breaks_the_road():
    s = state()
    topo = s.board.topology
    edges, verts = road_path(topo, 5)
    s.players["red"].roads.update(edges)
    # Drop a blue settlement on the middle vertex of red's 5-edge road.
    # The trail can no longer pass through it, leaving segments of 2 and 3.
    s.players["blue"].settlements.add(verts[2])
    assert longest_road_length(s, "red") == 3
    assert recompute_longest_road(s) is None


def test_largest_army_requires_three_and_transfers_on_strict_lead():
    s = state()
    s.players["red"].knights_played = 3
    assert update_largest_army(s, "red") == "red"
    s.largest_army_holder = "red"

    # Blue ties at 3 -> no transfer.
    s.players["blue"].knights_played = 3
    assert update_largest_army(s, "blue") == "red"

    # Blue takes the lead at 4 -> transfer.
    s.players["blue"].knights_played = 4
    assert update_largest_army(s, "blue") == "blue"
