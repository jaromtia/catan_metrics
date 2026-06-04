"""Dev (sandbox) vs strict mode: lenient validation and admin commands."""

import pytest

from catan.domain import commands as cmd
from catan.domain.board import standard_board
from catan.domain.constants import Resource
from catan.engine.validate import execute, validate
from catan.store.event_store import EventStore, UnknownGame
from catan.store.repository import GameService


def _new_state():
    board = standard_board()
    state, _ = execute(None, cmd.CreateGame(board=board, player_order=("red", "blue")))
    return state


def test_strict_rejects_build_before_setup():
    state = _new_state()
    res = validate(state, cmd.BuildSettlement(player="red", vertex=0), strict=True)
    assert not res.ok


def test_dev_allows_build_during_setup_for_any_player():
    state = _new_state()
    res = validate(state, cmd.BuildSettlement(player="blue", vertex=0), strict=False)
    assert res.ok
    assert res.events[0].vertex == 0


def test_dev_allows_roll_off_turn_and_repeatedly():
    state = _new_state()
    res = validate(state, cmd.RollDice(player="blue", die1=3, die2=4), strict=False)
    assert res.ok


def test_dev_still_blocks_structurally_invalid_ids():
    state = _new_state()
    assert not validate(state, cmd.BuildRoad(player="red", edge=9999), strict=False).ok
    assert not validate(state, cmd.RollDice(player="red", die1=9, die2=1), strict=False).ok


def test_dev_set_resources_sets_hand():
    state = _new_state()
    cmd_set = cmd.SetResources(player="red", resources={Resource.ORE: 5, Resource.GRAIN: 2})
    res = validate(state, cmd_set, strict=False)
    assert res.ok
    new = state
    from catan.engine.reduce import reduce
    for e in res.events:
        new = reduce(new, e)
    assert new.players["red"].resources[Resource.ORE] == 5
    assert new.players["red"].resources[Resource.GRAIN] == 2


def test_admin_commands_rejected_in_strict_mode():
    state = _new_state()
    assert not validate(state, cmd.SetResources(player="red", resources={Resource.ORE: 5}), strict=True).ok
    assert not validate(state, cmd.SetVictoryPoints(player="red", bonus=3), strict=True).ok


def test_set_victory_points_adds_to_score():
    from catan.engine.reduce import reduce
    state = _new_state()
    res = validate(state, cmd.SetVictoryPoints(player="red", bonus=4), strict=False)
    assert res.ok
    new = reduce(state, res.events[0])
    assert new.victory_points("red") == 4


def test_service_persists_and_toggles_mode():
    svc = GameService(EventStore())
    board = standard_board()
    gid = svc.create_game(cmd.CreateGame(board=board, player_order=("red", "blue")), mode="dev")
    assert svc.get_mode(gid) == "dev"

    # Dev mode lets red build a settlement immediately (no setup/turn gating).
    result = svc.try_apply(gid, cmd.BuildSettlement(player="red", vertex=0))
    assert result.ok

    svc.set_mode(gid, "strict")
    assert svc.get_mode(gid) == "strict"
    # Now the same kind of free build is rejected.
    assert not svc.try_apply(gid, cmd.BuildSettlement(player="red", vertex=5)).ok


def test_set_mode_unknown_game():
    svc = GameService(EventStore())
    with pytest.raises(UnknownGame):
        svc.set_mode("nope", "dev")


def test_default_mode_is_strict():
    svc = GameService(EventStore())
    gid = svc.create_game(cmd.CreateGame(board=standard_board(), player_order=("red", "blue")))
    assert svc.get_mode(gid) == "strict"
