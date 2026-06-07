"""High-level game service: the entry point for the CLI and API.

Wraps the engine (validate + reduce) and the event store so callers deal in
commands and states, never in raw events or SQL.
"""

from __future__ import annotations

import uuid

from ..domain import commands as cmd
from ..domain import events as ev
from ..domain.state import GameState
from ..engine.reduce import reduce
from ..engine.validate import Result, validate
from .event_store import EventStore


class GameService:
    def __init__(self, store: EventStore | None = None) -> None:
        self.store = store or EventStore()

    def create_game(
        self, command: cmd.CreateGame, mode: str = "strict", owner: str | None = None
    ) -> str:
        result = validate(None, command)
        if not result.ok:
            raise ValueError("; ".join(result.errors))
        game_id = uuid.uuid4().hex
        self.store.create_game(game_id, mode, owner)
        self.store.append(game_id, result.events)
        return game_id

    def state(self, game_id: str, *, up_to: int | None = None) -> GameState:
        return self.store.load_state(game_id, up_to=up_to)

    def get_mode(self, game_id: str) -> str:
        return self.store.get_mode(game_id)

    def set_mode(self, game_id: str, mode: str) -> None:
        self.store.set_mode(game_id, mode)

    def apply(self, game_id: str, command: cmd.Command) -> tuple[GameState, list[ev.Event]]:
        """Validate against current state, persist resulting events, return new state."""
        state = self.store.load_state(game_id)
        strict = self.store.get_mode(game_id) != "dev"
        result: Result = validate(state, command, strict=strict)
        if not result.ok:
            raise ValueError("; ".join(result.errors))

        new_state = state
        for event in result.events:
            new_state = reduce(new_state, event)

        last_seq = self.store.append(game_id, result.events)
        if self.store.should_snapshot(last_seq):
            self.store.save_snapshot(game_id, last_seq, new_state)
        return new_state, result.events

    def try_apply(self, game_id: str, command: cmd.Command) -> Result:
        """Like :meth:`apply` but returns the validation result instead of raising."""
        state = self.store.load_state(game_id)
        strict = self.store.get_mode(game_id) != "dev"
        result = validate(state, command, strict=strict)
        if result.ok:
            last_seq = self.store.append(game_id, result.events)
            new_state = state
            for event in result.events:
                new_state = reduce(new_state, event)
            if self.store.should_snapshot(last_seq):
                self.store.save_snapshot(game_id, last_seq, new_state)
        return result

    def list_games(self, owner: str | None = None) -> list[str]:
        return self.store.list_games(owner)

    def delete_game(self, game_id: str) -> None:
        self.store.delete_game(game_id)
