"""Plain-text renderers for the board and game state."""

from __future__ import annotations

from ..domain.constants import (
    PIPS,
    TERRAIN_RESOURCE,
    Resource,
    Terrain,
)
from ..domain.state import GameState
from ..engine.projections import GameMetrics

_TERRAIN_GLYPH = {
    Terrain.HILLS: "Bri",
    Terrain.FOREST: "Lum",
    Terrain.PASTURE: "Wol",
    Terrain.FIELDS: "Gra",
    Terrain.MOUNTAINS: "Ore",
    Terrain.DESERT: "Des",
}

_RES_ABBR = {
    Resource.BRICK: "bri",
    Resource.LUMBER: "lum",
    Resource.WOOL: "wol",
    Resource.GRAIN: "gra",
    Resource.ORE: "ore",
}


def render_board(state: GameState) -> str:
    board = state.board
    rows: dict[int, list] = {}
    for h in board.topology.hexes:
        rows.setdefault(h[1], []).append(h)

    width = max(len(v) for v in rows.values())
    lines = ["Board (terrain + number, * = robber):"]
    for r in sorted(rows):
        hexes = sorted(rows[r], key=lambda c: c[0])
        pad = "    " * (width - len(hexes))
        cells = []
        for h in hexes:
            glyph = _TERRAIN_GLYPH[board.terrain[h]]
            num = board.numbers.get(h)
            mark = "*" if h == state.robber else " "
            cells.append(f"{glyph}{(str(num) if num else '--'):>2}{mark}")
        lines.append(pad + "  ".join(cells))

    ports = ", ".join(sorted(p.type.value for p in board.ports))
    lines.append(f"Ports: {ports}")
    return "\n".join(lines)


def render_state(state: GameState) -> str:
    lines = []
    lines.append(
        f"phase={state.phase.value}  turn={state.turn_number}  "
        f"current={state.current_player}  rolled={state.has_rolled}"
        + (f"  dice={state.dice[0]}+{state.dice[1]}={sum(state.dice)}" if state.dice else "")
    )
    if state.robber_pending:
        lines.append("  >> robber awaiting move")
    if state.pending_discards:
        disc = ", ".join(f"{p}:{n}" for p, n in state.pending_discards.items())
        lines.append(f"  >> pending discards: {disc}")
    lines.append(
        f"longest_road={state.longest_road_holder}  "
        f"largest_army={state.largest_army_holder}  winner={state.winner}"
    )

    header = (
        f"{'player':<8} {'VP':>3} {'hand':>4}  "
        + " ".join(f"{a:>3}" for a in _RES_ABBR.values())
        + f"  {'S':>2} {'C':>2} {'R':>2} {'kt':>2} {'dev':>3}"
    )
    lines.append(header)
    for pid in state.player_order:
        p = state.players[pid]
        mark = "*" if pid == state.current_player else " "
        res = " ".join(f"{p.resources[r]:>3}" for r in _RES_ABBR)
        dev = p.dev_cards_in_hand
        lines.append(
            f"{mark}{pid:<7} {state.victory_points(pid):>3} {p.hand_size:>4}  {res}  "
            f"{len(p.settlements):>2} {len(p.cities):>2} {len(p.roads):>2} "
            f"{p.knights_played:>2} {dev:>3}"
        )

    bank = " ".join(f"{_RES_ABBR[r]}:{state.bank[r]}" for r in _RES_ABBR)
    lines.append(f"bank   {bank}   dev_deck:{state.dev_deck_size}")
    return "\n".join(lines)


def render_metrics(g: GameMetrics) -> str:
    lines = [f"turns={g.num_turns}  winner={g.winner}  dice_rolls={g.dice_total}"]

    lines.append("\nDice histogram (obs vs expected):")
    total = g.dice_total
    for n in range(2, 13):
        obs = g.dice_histogram[n]
        exp = total * PIPS[n] / 36
        bar = "#" * obs
        lines.append(f"  {n:>2}: {obs:>3} (exp {exp:5.1f}) {bar}")

    lines.append("\nPer player:")
    for pid in g.player_order:
        pm = g.players[pid]
        lines.append(f"\n  [{pid}]  VP={pm.final_vp}  pip_equity={pm.final_pip_equity}")
        prod = " ".join(f"{_RES_ABBR[r]}:{pm.production[r]}" for r in _RES_ABBR)
        lines.append(f"    production: {prod}  total={pm.production_total}")
        lines.append(
            f"    luck: {pm.luck:+.1f}  (expected {pm.expected_production:.1f}, "
            f"got {pm.production_total})"
        )
        net = " ".join(f"{_RES_ABBR[r]}:{pm.trade_net[r]:+d}" for r in _RES_ABBR)
        lines.append(
            f"    trades: domestic={pm.trades_domestic} maritime={pm.trades_maritime}  "
            f"net[{net}]"
        )
        lines.append(
            f"    robber: knights={pm.knights_played} steals_made={pm.steals_made} "
            f"stolen_from_me={pm.cards_stolen_from_me} discarded={pm.cards_discarded}"
        )
        dev_b = pm.dev_bought
        dev_p = sum(pm.dev_played.values())
        builds = ", ".join(f"{kind}@t{turn}" for _, turn, kind in pm.builds) or "(none)"
        lines.append(f"    dev: bought={dev_b} played={dev_p}    builds: {builds}")
    return "\n".join(lines)
