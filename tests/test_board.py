"""Board-assignment tests for standard, random, and custom layouts."""

import random
from collections import Counter

import pytest

from catan.domain.board import (
    RED_NUMBERS,
    _spiral_order,
    _terrain_pool,
    custom_board,
    random_board,
    standard_board,
)
from catan.domain.constants import (
    NUMBER_TOKEN_COUNTS,
    PORT_COUNTS,
    STANDARD_NUMBER_SEQUENCE,
    STANDARD_PORT_SEQUENCE,
    TERRAIN_COUNTS,
    Terrain,
)
from catan.domain.geometry import DIRECTIONS, build_topology


def _assert_valid(board):
    # Terrain multiset matches the base game exactly.
    assert Counter(board.terrain.values()) == Counter(TERRAIN_COUNTS)
    # Exactly one desert, and the robber starts on it.
    assert board.terrain[board.robber] is Terrain.DESERT
    # Number tokens: every producing hex has one, desert has none.
    assert len(board.numbers) == sum(NUMBER_TOKEN_COUNTS.values())
    assert board.robber not in board.numbers
    assert Counter(board.numbers.values()) == Counter(NUMBER_TOKEN_COUNTS)
    # Nine ports, correct type distribution.
    assert len(board.ports) == sum(PORT_COUNTS.values())
    assert Counter(p.type for p in board.ports) == Counter(PORT_COUNTS)
    # Each port attaches to a valid two-vertex perimeter edge.
    for port in board.ports:
        assert len(port.vertices) == 2


def test_standard_board_is_valid():
    _assert_valid(standard_board())


def test_standard_board_is_reproducible():
    a, b = standard_board(), standard_board()
    assert a.terrain == b.terrain
    assert a.numbers == b.numbers


def test_random_boards_are_valid():
    for seed in range(25):
        _assert_valid(random_board(random.Random(seed)))


def test_random_board_keeps_standard_ports():
    """Random boards shuffle terrain/numbers only -- ports stay on their docks."""
    for seed in range(10):
        board = random_board(random.Random(seed))
        assert [p.type.value for p in board.ports] == STANDARD_PORT_SEQUENCE
        assert board.ports == standard_board().ports


def test_random_board_has_no_adjacent_red_numbers():
    for seed in range(25):
        board = random_board(random.Random(seed))
        for h, num in board.numbers.items():
            if num in RED_NUMBERS:
                for d in DIRECTIONS:
                    nb = (h[0] + d[0], h[1] + d[1])
                    assert board.numbers.get(nb) not in RED_NUMBERS


def _spiral_terrains() -> list[Terrain]:
    """Same spiral terrain ordering standard_board uses (desert at center)."""
    spiral = _spiral_order(build_topology())
    producing = [t for t in _terrain_pool() if t is not Terrain.DESERT]
    return producing[: len(spiral) - 1] + [Terrain.DESERT]


def test_custom_board_is_valid():
    _assert_valid(custom_board(_spiral_terrains(), STANDARD_NUMBER_SEQUENCE))


def test_custom_board_reproduces_an_explicit_layout():
    board = custom_board(_spiral_terrains(), STANDARD_NUMBER_SEQUENCE)
    ref = standard_board()
    assert board.terrain == ref.terrain
    assert board.numbers == ref.numbers


def test_custom_board_accepts_terrain_synonyms():
    names = ["wood" if t is Terrain.FOREST else t.value for t in _spiral_terrains()]
    board = custom_board(names, STANDARD_NUMBER_SEQUENCE)
    assert Counter(board.terrain.values()) == Counter(TERRAIN_COUNTS)


def test_custom_board_rejects_wrong_terrain_count():
    with pytest.raises(ValueError):
        custom_board(_spiral_terrains()[:-1], STANDARD_NUMBER_SEQUENCE)


def test_custom_board_rejects_wrong_number_multiset():
    bad = list(STANDARD_NUMBER_SEQUENCE)
    bad[0] = 7  # not a legal token; breaks the multiset
    with pytest.raises(ValueError):
        custom_board(_spiral_terrains(), bad)


def _standard_port_placements():
    from catan.domain.board import standard_port_edges

    topo = build_topology()
    return topo, standard_port_edges(topo)


def test_standard_board_port_sequence():
    board = standard_board()
    assert [p.type.value for p in board.ports] == STANDARD_PORT_SEQUENCE


def test_custom_board_accepts_explicit_port_edges():
    topo, placements = _standard_port_placements()
    board = custom_board(_spiral_terrains(), STANDARD_NUMBER_SEQUENCE, port_edges=placements)
    _assert_valid(board)
    chosen = {frozenset(topo.edge_vertices[e]) for _, e in placements}
    assert {p.vertices for p in board.ports} == chosen


def test_custom_board_rejects_duplicate_port_edge():
    _, placements = _standard_port_placements()
    dup = [(t, placements[0][1]) for t, _ in placements]  # everything on one edge
    with pytest.raises(ValueError):
        custom_board(_spiral_terrains(), STANDARD_NUMBER_SEQUENCE, port_edges=dup)


def test_custom_board_rejects_non_perimeter_port_edge():
    from catan.domain.board import _perimeter_edges

    topo, placements = _standard_port_placements()
    perim = set(_perimeter_edges(topo))
    interior = next(e for e in topo.edge_vertices if e not in perim)
    placements[0] = (placements[0][0], interior)
    with pytest.raises(ValueError):
        custom_board(_spiral_terrains(), STANDARD_NUMBER_SEQUENCE, port_edges=placements)


def test_custom_board_rejects_wrong_port_distribution():
    _, placements = _standard_port_placements()
    # pool is 4 generic + one of each resource; overwrite a resource slot with a
    # 5th generic so a resource port goes missing.
    placements[-1] = ("generic", placements[-1][1])
    with pytest.raises(ValueError):
        custom_board(_spiral_terrains(), STANDARD_NUMBER_SEQUENCE, port_edges=placements)
