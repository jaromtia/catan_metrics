"""Longest Road and Largest Army computation.

Both are pure functions of :class:`~catan.domain.state.GameState`. Longest Road
is the genuinely tricky one: it is the longest *trail* (no edge reused) through a
player's road network, where an opponent's settlement or city blocks the trail
from passing *through* that vertex (it may still be an endpoint).
"""

from __future__ import annotations

from ..domain.constants import LARGEST_ARMY_MIN, LONGEST_ROAD_MIN
from ..domain.state import GameState, PlayerId


def longest_road_length(state: GameState, pid: PlayerId) -> int:
    topo = state.board.topology
    roads = state.players[pid].roads
    if not roads:
        return 0

    # Adjacency among this player's roads, keyed by vertex.
    edges_at: dict[int, list[tuple[int, int]]] = {}  # vertex -> [(edge_id, other_vertex)]
    for eid in roads:
        a, b = topo.edge_vertices[eid]
        edges_at.setdefault(a, []).append((eid, b))
        edges_at.setdefault(b, []).append((eid, a))

    def blocked(vertex: int) -> bool:
        owner = state.owner_of_vertex(vertex)
        return owner is not None and owner[0] != pid

    best = 0

    def dfs(vertex: int, used: set[int], entered: bool) -> int:
        # Cannot pass *through* an opponent's building (but may start there).
        if entered and blocked(vertex):
            return 0
        local = 0
        for eid, nxt in edges_at.get(vertex, ()):
            if eid in used:
                continue
            used.add(eid)
            local = max(local, 1 + dfs(nxt, used, True))
            used.discard(eid)
        return local

    for start in edges_at:
        best = max(best, dfs(start, set(), False))
    return best


def recompute_longest_road(state: GameState) -> PlayerId | None:
    """Award holder after a road/settlement change, applying Catan tie rules."""
    lengths = {pid: longest_road_length(state, pid) for pid in state.player_order}
    holder = state.longest_road_holder

    # Holder loses the card if their road drops below the minimum (e.g. broken).
    if holder is not None and lengths[holder] < LONGEST_ROAD_MIN:
        holder = None

    max_len = max(lengths.values(), default=0)
    if max_len < LONGEST_ROAD_MIN:
        return None

    leaders = [pid for pid, length in lengths.items() if length == max_len]

    if holder is not None:
        # The holder keeps the card until someone strictly surpasses them.
        if lengths[holder] == max_len:
            return holder
        return leaders[0] if len(leaders) == 1 else holder

    # Unheld card goes to a unique leader; a tie leaves it unheld.
    return leaders[0] if len(leaders) == 1 else None


def update_largest_army(state: GameState, player: PlayerId) -> PlayerId | None:
    """Award holder after ``player`` plays a knight (knights only ever increase)."""
    holder = state.largest_army_holder
    knights = state.players[player].knights_played
    if knights < LARGEST_ARMY_MIN:
        return holder
    if holder is None:
        return player
    if player == holder:
        return holder
    if knights > state.players[holder].knights_played:
        return player
    return holder
