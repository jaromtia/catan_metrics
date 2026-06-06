"""JSON codec for events, boards, and game state.

Everything is converted to plain JSON-serializable dicts so it can live in
SQLite text columns. The board's *topology* is never stored: vertex/edge ids are
derived deterministically from the hex set (sorted canonically), so we store the
board content and rebuild the topology on load, yielding identical ids.
"""

from __future__ import annotations

from ..domain import commands as cmd
from ..domain import events as ev
from ..domain.board import Board, Port
from ..domain.constants import DEV_DECK_SIZE, PIPS, DevCard, PortType, Resource, Terrain
from ..domain.geometry import build_topology
from ..domain.state import GameState, Phase, PlayerState

Coord = tuple[int, int]


# --- primitives ------------------------------------------------------------

def _ck(c: Coord) -> str:
    return f"{c[0]},{c[1]}"


def _uck(s: str) -> Coord:
    q, r = s.split(",")
    return (int(q), int(r))


def _enc_resmap(m: dict[Resource, int]) -> dict[str, int]:
    return {r.value: a for r, a in m.items()}


def _dec_resmap(d: dict[str, int]) -> dict[Resource, int]:
    return {Resource(k): v for k, v in d.items()}


def _enc_devmap(m: dict[DevCard, int]) -> dict[str, int]:
    return {c.value: a for c, a in m.items()}


def _dec_devmap(d: dict[str, int]) -> dict[DevCard, int]:
    return {DevCard(k): v for k, v in d.items()}


def _coord_or_none(c) -> list | None:
    return list(c) if c is not None else None


# --- board -----------------------------------------------------------------

def encode_board(board: Board) -> dict:
    return {
        "hexes": [list(h) for h in board.topology.hexes],
        "terrain": {_ck(h): t.value for h, t in board.terrain.items()},
        "numbers": {_ck(h): n for h, n in board.numbers.items()},
        "ports": [
            {"type": p.type.value, "vertices": sorted(p.vertices)} for p in board.ports
        ],
        "robber": _coord_or_none(board.robber),
    }


def decode_board(d: dict) -> Board:
    hexes = [tuple(h) for h in d["hexes"]]
    topology = build_topology(hexes)
    terrain = {_uck(k): Terrain(v) for k, v in d["terrain"].items()}
    numbers = {_uck(k): v for k, v in d["numbers"].items()}
    ports = [
        Port(type=PortType(p["type"]), vertices=frozenset(p["vertices"]))
        for p in d["ports"]
    ]
    pips = {h: PIPS[n] for h, n in numbers.items()}
    return Board(
        topology=topology,
        terrain=terrain,
        numbers=numbers,
        ports=ports,
        robber=tuple(d["robber"]),
        pips=pips,
    )


# --- game state (for snapshots) -------------------------------------------

def encode_state(state: GameState) -> dict:
    return {
        "board": encode_board(state.board),
        "player_order": list(state.player_order),
        "players": {
            pid: {
                "resources": _enc_resmap(p.resources),
                "hidden_dev": p.hidden_dev,
                "dev_cards": _enc_devmap(p.dev_cards),
                "dev_cards_played": _enc_devmap(p.dev_cards_played),
                "knights_played": p.knights_played,
                "settlements": sorted(p.settlements),
                "cities": sorted(p.cities),
                "roads": sorted(p.roads),
                "bonus_vp": p.bonus_vp,
            }
            for pid, p in state.players.items()
        },
        "phase": state.phase.value,
        "current_index": state.current_index,
        "turn_number": state.turn_number,
        "dice": list(state.dice) if state.dice is not None else None,
        "has_rolled": state.has_rolled,
        "bank": _enc_resmap(state.bank),
        "dev_deck_size": state.dev_deck_size,
        "robber": _coord_or_none(state.robber),
        "longest_road_holder": state.longest_road_holder,
        "largest_army_holder": state.largest_army_holder,
        "winner": state.winner,
        "pending_discards": dict(state.pending_discards),
        "robber_pending": state.robber_pending,
        "dev_played_this_turn": state.dev_played_this_turn,
        "dev_bought_this_turn": state.dev_bought_this_turn,
    }


def decode_state(d: dict) -> GameState:
    players = {}
    for pid, p in d["players"].items():
        ps = PlayerState(pid=pid)
        ps.resources = _dec_resmap(p["resources"])
        ps.hidden_dev = p.get("hidden_dev", 0)
        ps.dev_cards = _dec_devmap(p["dev_cards"])
        ps.dev_cards_played = _dec_devmap(p["dev_cards_played"])
        ps.knights_played = p["knights_played"]
        ps.settlements = set(p["settlements"])
        ps.cities = set(p["cities"])
        ps.roads = set(p["roads"])
        ps.bonus_vp = p.get("bonus_vp", 0)
        players[pid] = ps
    return GameState(
        board=decode_board(d["board"]),
        player_order=list(d["player_order"]),
        players=players,
        phase=Phase(d["phase"]),
        current_index=d["current_index"],
        turn_number=d["turn_number"],
        dice=tuple(d["dice"]) if d["dice"] is not None else None,
        has_rolled=d["has_rolled"],
        bank=_dec_resmap(d["bank"]),
        dev_deck_size=d.get("dev_deck_size", DEV_DECK_SIZE),
        robber=tuple(d["robber"]) if d["robber"] is not None else None,
        longest_road_holder=d["longest_road_holder"],
        largest_army_holder=d["largest_army_holder"],
        winner=d["winner"],
        pending_discards=dict(d["pending_discards"]),
        robber_pending=d["robber_pending"],
        dev_played_this_turn=d["dev_played_this_turn"],
        dev_bought_this_turn=d.get("dev_bought_this_turn", 0),
    )


# --- events ----------------------------------------------------------------

def encode_event(e: ev.Event) -> dict:
    t = type(e).__name__
    match e:
        case ev.GameCreated(board=b, player_order=order):
            return {"type": t, "board": encode_board(b), "player_order": list(order)}
        case ev.SetupSettlementPlaced(player=p, vertex=v):
            return {"type": t, "player": p, "vertex": v}
        case ev.SetupRoadPlaced(player=p, edge=ed):
            return {"type": t, "player": p, "edge": ed}
        case ev.DiceRolled(player=p, die1=d1, die2=d2):
            return {"type": t, "player": p, "die1": d1, "die2": d2}
        case ev.TurnEnded(player=p):
            return {"type": t, "player": p}
        case ev.DiscardedToRobber(player=p, resources=res):
            return {"type": t, "player": p, "resources": _enc_resmap(res)}
        case ev.RobberMoved(player=p, hex=h):
            return {"type": t, "player": p, "hex": list(h)}
        case ev.ResourceStolen(player=p, victim=vic, resource=r):
            return {"type": t, "player": p, "victim": vic, "resource": r.value}
        case ev.DomesticTrade(player=p, partner=q, gave=g, received=rc):
            return {"type": t, "player": p, "partner": q,
                    "gave": _enc_resmap(g), "received": _enc_resmap(rc)}
        case ev.MaritimeTrade(player=p, gave=g, received=rc, ratio=ratio):
            return {"type": t, "player": p, "gave": _enc_resmap(g),
                    "received": _enc_resmap(rc), "ratio": ratio}
        case ev.RoadBuilt(player=p, edge=ed):
            return {"type": t, "player": p, "edge": ed}
        case ev.SettlementBuilt(player=p, vertex=v):
            return {"type": t, "player": p, "vertex": v}
        case ev.CityBuilt(player=p, vertex=v):
            return {"type": t, "player": p, "vertex": v}
        case ev.DevCardBought(player=p):
            return {"type": t, "player": p}
        case ev.KnightPlayed(player=p, hex=h, victim=vic, resource=r):
            return {"type": t, "player": p, "hex": list(h), "victim": vic,
                    "resource": r.value if r is not None else None}
        case ev.RoadBuildingPlayed(player=p, edges=edges):
            return {"type": t, "player": p, "edges": list(edges)}
        case ev.YearOfPlentyPlayed(player=p, resources=res):
            return {"type": t, "player": p, "resources": [r.value for r in res]}
        case ev.MonopolyPlayed(player=p, resource=r):
            return {"type": t, "player": p, "resource": r.value}
        case ev.VictoryPointRevealed(player=p):
            return {"type": t, "player": p}
        case ev.ResourcesSet(player=p, resources=res):
            return {"type": t, "player": p, "resources": _enc_resmap(res)}
        case ev.VictoryPointsSet(player=p, bonus=b):
            return {"type": t, "player": p, "bonus": b}
        case _:
            raise ValueError(f"cannot encode event: {e!r}")


def decode_event(d: dict) -> ev.Event:
    t = d["type"]
    match t:
        case "GameCreated":
            return ev.GameCreated(
                board=decode_board(d["board"]),
                player_order=tuple(d["player_order"]),
            )
        case "SetupSettlementPlaced":
            return ev.SetupSettlementPlaced(player=d["player"], vertex=d["vertex"])
        case "SetupRoadPlaced":
            return ev.SetupRoadPlaced(player=d["player"], edge=d["edge"])
        case "DiceRolled":
            return ev.DiceRolled(player=d["player"], die1=d["die1"], die2=d["die2"])
        case "TurnEnded":
            return ev.TurnEnded(player=d["player"])
        case "DiscardedToRobber":
            return ev.DiscardedToRobber(player=d["player"], resources=_dec_resmap(d["resources"]))
        case "RobberMoved":
            return ev.RobberMoved(player=d["player"], hex=tuple(d["hex"]))
        case "ResourceStolen":
            return ev.ResourceStolen(player=d["player"], victim=d["victim"],
                                     resource=Resource(d["resource"]))
        case "DomesticTrade":
            return ev.DomesticTrade(player=d["player"], partner=d["partner"],
                                    gave=_dec_resmap(d["gave"]),
                                    received=_dec_resmap(d["received"]))
        case "MaritimeTrade":
            return ev.MaritimeTrade(player=d["player"], gave=_dec_resmap(d["gave"]),
                                    received=_dec_resmap(d["received"]), ratio=d["ratio"])
        case "RoadBuilt":
            return ev.RoadBuilt(player=d["player"], edge=d["edge"])
        case "SettlementBuilt":
            return ev.SettlementBuilt(player=d["player"], vertex=d["vertex"])
        case "CityBuilt":
            return ev.CityBuilt(player=d["player"], vertex=d["vertex"])
        case "DevCardBought":
            return ev.DevCardBought(player=d["player"])
        case "KnightPlayed":
            r = d["resource"]
            return ev.KnightPlayed(player=d["player"], hex=tuple(d["hex"]),
                                   victim=d["victim"],
                                   resource=Resource(r) if r is not None else None)
        case "RoadBuildingPlayed":
            return ev.RoadBuildingPlayed(player=d["player"], edges=tuple(d["edges"]))
        case "YearOfPlentyPlayed":
            r1, r2 = d["resources"]
            return ev.YearOfPlentyPlayed(player=d["player"],
                                         resources=(Resource(r1), Resource(r2)))
        case "MonopolyPlayed":
            return ev.MonopolyPlayed(player=d["player"], resource=Resource(d["resource"]))
        case "VictoryPointRevealed":
            return ev.VictoryPointRevealed(player=d["player"])
        case "ResourcesSet":
            return ev.ResourcesSet(player=d["player"], resources=_dec_resmap(d["resources"]))
        case "VictoryPointsSet":
            return ev.VictoryPointsSet(player=d["player"], bonus=d["bonus"])
        case _:
            raise ValueError(f"unknown event type: {t}")


# --- commands (decode only; clients submit these as JSON) ------------------

def decode_command(d: dict) -> cmd.Command:
    t = d["type"]
    p = d.get("player")
    match t:
        case "PlaceSetupSettlement":
            return cmd.PlaceSetupSettlement(player=p, vertex=d["vertex"])
        case "PlaceSetupRoad":
            return cmd.PlaceSetupRoad(player=p, edge=d["edge"])
        case "RollDice":
            return cmd.RollDice(player=p, die1=d["die1"], die2=d["die2"])
        case "EndTurn":
            return cmd.EndTurn(player=p)
        case "Discard":
            return cmd.Discard(player=p, resources=_dec_resmap(d["resources"]))
        case "MoveRobber":
            r = d.get("resource")
            return cmd.MoveRobber(player=p, hex=tuple(d["hex"]), victim=d.get("victim"),
                                  resource=Resource(r) if r else None)
        case "BuildRoad":
            return cmd.BuildRoad(player=p, edge=d["edge"])
        case "BuildSettlement":
            return cmd.BuildSettlement(player=p, vertex=d["vertex"])
        case "BuildCity":
            return cmd.BuildCity(player=p, vertex=d["vertex"])
        case "BuyDevCard":
            return cmd.BuyDevCard(player=p)
        case "RevealVictoryPoint":
            return cmd.RevealVictoryPoint(player=p)
        case "PlayKnight":
            r = d.get("resource")
            return cmd.PlayKnight(player=p, hex=tuple(d["hex"]), victim=d.get("victim"),
                                  resource=Resource(r) if r else None)
        case "PlayRoadBuilding":
            return cmd.PlayRoadBuilding(player=p, edges=tuple(d["edges"]))
        case "PlayYearOfPlenty":
            r1, r2 = d["resources"]
            return cmd.PlayYearOfPlenty(player=p, resources=(Resource(r1), Resource(r2)))
        case "PlayMonopoly":
            return cmd.PlayMonopoly(player=p, resource=Resource(d["resource"]))
        case "TradeWithBank":
            return cmd.TradeWithBank(player=p, give=Resource(d["give"]),
                                     give_amount=d["give_amount"],
                                     receive=Resource(d["receive"]),
                                     receive_amount=d["receive_amount"])
        case "TradeWithPlayer":
            return cmd.TradeWithPlayer(player=p, partner=d["partner"],
                                       gave=_dec_resmap(d["gave"]),
                                       received=_dec_resmap(d["received"]))
        case "SetResources":
            return cmd.SetResources(player=p, resources=_dec_resmap(d["resources"]))
        case "SetVictoryPoints":
            return cmd.SetVictoryPoints(player=p, bonus=int(d["bonus"]))
        case _:
            raise ValueError(f"unknown command type: {t}")
