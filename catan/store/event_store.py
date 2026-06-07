"""SQLite append-only event store with periodic snapshots.

The event log is the source of truth; snapshots are a replay optimization. A
game's state can always be rebuilt by folding its events, and
:meth:`EventStore.load_state` uses the latest snapshot plus the tail of events
after it.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass

from ..domain import events as ev
from ..domain.state import GameState
from ..engine.reduce import reduce
from .codec import decode_event, decode_state, encode_event, encode_state

SNAPSHOT_INTERVAL = 25


class UnknownGame(Exception):
    """Raised when a game id has no stored events."""

VALID_MODES = ("strict", "dev")
DEFAULT_MODE = "strict"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    game_id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    mode TEXT NOT NULL DEFAULT 'strict',
    owner TEXT
);
CREATE TABLE IF NOT EXISTS events (
    game_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    ts REAL NOT NULL,
    type TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (game_id, seq)
);
CREATE TABLE IF NOT EXISTS snapshots (
    game_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    state TEXT NOT NULL,
    PRIMARY KEY (game_id, seq)
);
"""


@dataclass(frozen=True)
class StoredEvent:
    seq: int
    ts: float
    event: ev.Event


class EventStore:
    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        """Add columns to ``games`` for databases created before they existed."""
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(games)")}
        if "mode" not in cols:
            self.conn.execute(
                "ALTER TABLE games ADD COLUMN mode TEXT NOT NULL DEFAULT 'strict'"
            )
        if "owner" not in cols:
            # NULL = ownerless/legacy game, visible to every browser.
            self.conn.execute("ALTER TABLE games ADD COLUMN owner TEXT")

    def close(self) -> None:
        self.conn.close()

    # --- writes ------------------------------------------------------------

    def create_game(self, game_id: str, mode: str = DEFAULT_MODE, owner: str | None = None) -> None:
        self.conn.execute(
            "INSERT INTO games (game_id, created_at, mode, owner) VALUES (?, ?, ?, ?)",
            (game_id, time.time(), mode, owner),
        )
        self.conn.commit()

    def set_mode(self, game_id: str, mode: str) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"unknown mode {mode!r}")
        cur = self.conn.execute(
            "UPDATE games SET mode = ? WHERE game_id = ?", (mode, game_id)
        )
        self.conn.commit()
        if cur.rowcount == 0:
            raise UnknownGame(game_id)

    def _next_seq(self, game_id: str) -> int:
        row = self.conn.execute(
            "SELECT MAX(seq) AS m FROM events WHERE game_id = ?", (game_id,)
        ).fetchone()
        return 0 if row["m"] is None else row["m"] + 1

    def append(self, game_id: str, events: list[ev.Event]) -> int:
        """Append events atomically; returns the last assigned sequence number."""
        seq = self._next_seq(game_id)
        now = time.time()
        rows = []
        for event in events:
            payload = json.dumps(encode_event(event))
            rows.append((game_id, seq, now, type(event).__name__, payload))
            seq += 1
        self.conn.executemany(
            "INSERT INTO events (game_id, seq, ts, type, payload) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return seq - 1

    def delete_game(self, game_id: str) -> None:
        """Remove a game and all of its events and snapshots."""
        self.conn.execute("DELETE FROM events WHERE game_id = ?", (game_id,))
        self.conn.execute("DELETE FROM snapshots WHERE game_id = ?", (game_id,))
        self.conn.execute("DELETE FROM games WHERE game_id = ?", (game_id,))
        self.conn.commit()

    def save_snapshot(self, game_id: str, seq: int, state: GameState) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO snapshots (game_id, seq, state) VALUES (?, ?, ?)",
            (game_id, seq, json.dumps(encode_state(state))),
        )
        self.conn.commit()

    # --- reads -------------------------------------------------------------

    def list_games(self, owner: str | None = None) -> list[str]:
        """List game ids, oldest first.

        With ``owner`` set, only that owner's games plus ownerless/legacy
        games (``owner IS NULL``) are returned — each browser's private lobby
        plus anything pre-dating per-browser ownership. With ``owner=None``
        (e.g. the CLI, which has no notion of "this browser"), every game is
        returned, matching the pre-ownership behavior.
        """
        if owner is None:
            rows = self.conn.execute(
                "SELECT game_id FROM games ORDER BY created_at"
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT game_id FROM games WHERE owner IS NULL OR owner = ? ORDER BY created_at",
                (owner,),
            ).fetchall()
        return [r["game_id"] for r in rows]

    def get_mode(self, game_id: str) -> str:
        row = self.conn.execute(
            "SELECT mode FROM games WHERE game_id = ?", (game_id,)
        ).fetchone()
        if row is None:
            raise UnknownGame(game_id)
        return row["mode"]

    def load_events(self, game_id: str, *, after: int = -1) -> list[StoredEvent]:
        rows = self.conn.execute(
            "SELECT seq, ts, payload FROM events WHERE game_id = ? AND seq > ? ORDER BY seq",
            (game_id, after),
        ).fetchall()
        return [
            StoredEvent(seq=r["seq"], ts=r["ts"], event=decode_event(json.loads(r["payload"])))
            for r in rows
        ]

    def _latest_snapshot(self, game_id: str, *, up_to: int) -> tuple[int, GameState] | None:
        row = self.conn.execute(
            "SELECT seq, state FROM snapshots WHERE game_id = ? AND seq <= ? "
            "ORDER BY seq DESC LIMIT 1",
            (game_id, up_to),
        ).fetchone()
        if row is None:
            return None
        return row["seq"], decode_state(json.loads(row["state"]))

    def load_state(self, game_id: str, *, up_to: int | None = None) -> GameState:
        """Rebuild state, optionally as of sequence ``up_to`` (inclusive)."""
        ceiling = self._max_seq(game_id) if up_to is None else up_to
        snap = self._latest_snapshot(game_id, up_to=ceiling)
        if snap is None:
            state: GameState | None = None
            after = -1
        else:
            snap_seq, state = snap
            after = snap_seq
        for stored in self.load_events(game_id, after=after):
            if stored.seq > ceiling:
                break
            state = reduce(state, stored.event)
        if state is None:
            raise UnknownGame(game_id)
        return state

    def _max_seq(self, game_id: str) -> int:
        row = self.conn.execute(
            "SELECT MAX(seq) AS m FROM events WHERE game_id = ?", (game_id,)
        ).fetchone()
        if row["m"] is None:
            raise UnknownGame(game_id)
        return row["m"]

    def should_snapshot(self, seq: int) -> bool:
        return seq > 0 and (seq + 1) % SNAPSHOT_INTERVAL == 0
