"""Parse a REPL line into a :mod:`~catan.domain.commands` command.

Deliberately forgiving: accepts common synonyms (wood/sheep/wheat/rock) and
infers the acting player from the game state (current player in play, the
expected player in setup) so the operator types as little as possible.
"""

from __future__ import annotations

from ..domain import commands as cmd
from ..domain.constants import Resource
from ..domain.state import GameState, Phase
from ..engine.validate import setup_expectation

_RES = {
    "brick": Resource.BRICK, "clay": Resource.BRICK,
    "lumber": Resource.LUMBER, "wood": Resource.LUMBER,
    "wool": Resource.WOOL, "sheep": Resource.WOOL,
    "grain": Resource.GRAIN, "wheat": Resource.GRAIN,
    "ore": Resource.ORE, "rock": Resource.ORE, "stone": Resource.ORE,
}


class ParseError(ValueError):
    pass


def _res(token: str) -> Resource:
    try:
        return _RES[token.lower()]
    except KeyError:
        raise ParseError(f"unknown resource '{token}'") from None


def _hex(token: str) -> tuple[int, int]:
    try:
        q, r = token.split(",")
        return (int(q), int(r))
    except ValueError:
        raise ParseError(f"hex must be 'q,r', got '{token}'") from None


def _resmap(token: str) -> dict[Resource, int]:
    out: dict[Resource, int] = {}
    for part in token.split(","):
        name, _, amt = part.partition(":")
        out[_res(name)] = int(amt or 1)
    return out


def _actor(state: GameState) -> str:
    return state.current_player


def build_command(state: GameState, line: str) -> cmd.Command:
    tokens = line.split()
    if not tokens:
        raise ParseError("empty command")
    head, args = tokens[0].lower(), tokens[1:]

    if state.phase is Phase.SETUP:
        exp = setup_expectation(state)
        who = exp[1] if exp else state.current_player
        if head in ("settlement", "sett", "s"):
            return cmd.PlaceSetupSettlement(player=who, vertex=int(args[0]))
        if head in ("road", "r"):
            return cmd.PlaceSetupRoad(player=who, edge=int(args[0]))
        raise ParseError(f"in setup, use 'settlement <v>' or 'road <e>' ({exp} expected)")

    p = _actor(state)
    match head:
        case "roll":
            return cmd.RollDice(player=p, die1=int(args[0]), die2=int(args[1]))
        case "end":
            return cmd.EndTurn(player=p)
        case "build":
            sub = args[0].lower()
            if sub == "road":
                return cmd.BuildRoad(player=p, edge=int(args[1]))
            if sub == "settlement":
                return cmd.BuildSettlement(player=p, vertex=int(args[1]))
            if sub == "city":
                return cmd.BuildCity(player=p, vertex=int(args[1]))
            raise ParseError("build road|settlement|city <id>")
        case "buy":
            return cmd.BuyDevCard(player=p)
        case "reveal":
            return cmd.RevealVictoryPoint(player=p)
        case "play":
            return _play(p, args)
        case "robber":
            victim = args[1] if len(args) > 1 else None
            resource = _res(args[2]) if len(args) > 2 else None
            return cmd.MoveRobber(player=p, hex=_hex(args[0]), victim=victim, resource=resource)
        case "discard":
            return cmd.Discard(player=args[0], resources=_resmap(args[1]))
        case "trade":
            return _trade(p, args)
        case _:
            raise ParseError(f"unknown command '{head}' (try 'help')")


def _play(p: str, args: list[str]) -> cmd.Command:
    kind = args[0].lower()
    if kind == "knight":
        victim = args[2] if len(args) > 2 else None
        resource = _res(args[3]) if len(args) > 3 else None
        return cmd.PlayKnight(player=p, hex=_hex(args[1]), victim=victim, resource=resource)
    if kind in ("road", "road_building", "roadbuilding"):
        edges = tuple(int(a) for a in args[1:])
        return cmd.PlayRoadBuilding(player=p, edges=edges)
    if kind in ("yop", "year_of_plenty"):
        return cmd.PlayYearOfPlenty(player=p, resources=(_res(args[1]), _res(args[2])))
    if kind == "monopoly":
        return cmd.PlayMonopoly(player=p, resource=_res(args[1]))
    raise ParseError("play knight|road|yop|monopoly ...")


def _trade(p: str, args: list[str]) -> cmd.Command:
    venue = args[0].lower()
    if venue == "bank":
        return cmd.TradeWithBank(
            player=p, give=_res(args[1]), give_amount=int(args[2]),
            receive=_res(args[3]), receive_amount=int(args[4]),
        )
    if venue == "player":
        return cmd.TradeWithPlayer(
            player=p, partner=args[1],
            gave=_resmap(args[2]), received=_resmap(args[3]),
        )
    raise ParseError("trade bank <give> <n> <recv> <n>  |  trade player <partner> <give:n> <recv:n>")


HELP = """\
commands (acting player is inferred):
  setup:  settlement <v>            road <e>
  turn:   roll <d1> <d2>            end
  build:  build road <e>           build settlement <v>      build city <v>
  dev:    buy                      reveal   (reveal a hidden card as a VP)
          play knight <q,r> [victim [res]]
          play road <e1> [e2]      play yop <res> <res>       play monopoly <res>
  seven:  discard <player> <res:n,...>     robber <q,r> [victim [res]]
  trade:  trade bank <give> <n> <recv> <n>
          trade player <partner> <give:n,...> <recv:n,...>
  meta:   state   board   log   help   quit
"""
