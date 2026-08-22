from __future__ import annotations

import base64
import json
import sqlite3
from collections import deque
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock
from uuid import uuid4
from zlib import compress, decompress

from .session_store import SessionExpired, SessionState

_BYTES_MARKER = "__cpf_fcv_bytes__"


def _json_default(value):
    if isinstance(value, bytes):
        return {_BYTES_MARKER: base64.b64encode(value).decode("ascii")}
    raise TypeError(f"Unsupported session value: {type(value).__name__}")


def _json_object_hook(value):
    if set(value) == {_BYTES_MARKER} and isinstance(value[_BYTES_MARKER], str):
        return base64.b64decode(value[_BYTES_MARKER], validate=True)
    return value


def _encode(value) -> bytes:
    serialized = json.dumps(
        value,
        default=_json_default,
        separators=(",", ":"),
    ).encode("utf-8")
    return compress(serialized)


def _decode(value: bytes):
    return json.loads(
        decompress(value).decode("utf-8"),
        object_hook=_json_object_hook,
    )


class SQLiteSessionStore:
    """Restart-safe, expiring assessment state for a single Render instance."""

    storage_mode = "persistent"

    def __init__(self, path: str | Path, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive.")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ttl_seconds = ttl_seconds
        self._lock = RLock()
        self._next_offsets: dict[str, int] = {}
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    expires_at REAL NOT NULL,
                    status TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS session_values (
                    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    value BLOB NOT NULL,
                    PRIMARY KEY (session_id, name)
                );
                CREATE TABLE IF NOT EXISTS events (
                    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
                    sequence INTEGER NOT NULL,
                    value BLOB NOT NULL,
                    PRIMARY KEY (session_id, sequence)
                );
                CREATE INDEX IF NOT EXISTS sessions_status_updated
                    ON sessions(status, updated_at);
                """
            )

    @staticmethod
    def _now() -> float:
        return datetime.now(UTC).timestamp()

    def _purge_expired(self, connection, now: float) -> None:
        connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))

    def _require(self, connection, session_id: str, now: float):
        self._purge_expired(connection, now)
        row = connection.execute(
            "SELECT expires_at FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            raise SessionExpired(session_id)
        return row

    def create(self, payload: dict) -> str:
        session_id = uuid4().hex
        now = self._now()
        status = str(payload.get("status", "created"))
        with self._lock, self._connect() as connection:
            self._purge_expired(connection, now)
            connection.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?)",
                (session_id, now + self._ttl_seconds, status, now),
            )
            connection.executemany(
                "INSERT INTO session_values VALUES (?, ?, ?)",
                (
                    (session_id, name, _encode(value))
                    for name, value in deepcopy(payload).items()
                ),
            )
        return session_id

    def get(self, session_id: str) -> SessionState:
        now = self._now()
        with self._lock, self._connect() as connection:
            expires_at, = self._require(connection, session_id, now)
            payload = {
                name: _decode(value)
                for name, value in connection.execute(
                    "SELECT name, value FROM session_values WHERE session_id = ?",
                    (session_id,),
                )
            }
            events = deque(
                _decode(value)
                for value, in connection.execute(
                    "SELECT value FROM events WHERE session_id = ? ORDER BY sequence",
                    (session_id,),
                )
            )
        return SessionState(
            session_id=session_id,
            payload=payload,
            expires_at=datetime.fromtimestamp(expires_at, UTC),
            events=events,
        )

    def update(self, session_id: str, **values) -> None:
        now = self._now()
        with self._lock, self._connect() as connection:
            self._require(connection, session_id, now)
            connection.executemany(
                """
                INSERT INTO session_values(session_id, name, value) VALUES (?, ?, ?)
                ON CONFLICT(session_id, name) DO UPDATE SET value = excluded.value
                """,
                ((session_id, name, _encode(value)) for name, value in values.items()),
            )
            status = values.get("status")
            if status is None:
                connection.execute(
                    "UPDATE sessions SET expires_at = ?, updated_at = ? WHERE session_id = ?",
                    (now + self._ttl_seconds, now, session_id),
                )
            else:
                connection.execute(
                    """
                    UPDATE sessions SET expires_at = ?, updated_at = ?, status = ?
                    WHERE session_id = ?
                    """,
                    (now + self._ttl_seconds, now, str(status), session_id),
                )

    def remove_keys(self, assessment_id: str, *keys) -> None:
        now = self._now()
        with self._lock, self._connect() as connection:
            self._require(connection, assessment_id, now)
            connection.executemany(
                "DELETE FROM session_values WHERE session_id = ? AND name = ?",
                ((assessment_id, name) for name in keys),
            )
            connection.execute(
                "UPDATE sessions SET expires_at = ?, updated_at = ? WHERE session_id = ?",
                (now + self._ttl_seconds, now, assessment_id),
            )

    def emit(self, session_id: str, event_type: str, data: dict) -> None:
        now = self._now()
        with self._lock, self._connect() as connection:
            self._require(connection, session_id, now)
            row = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM events WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            connection.execute(
                "INSERT INTO events VALUES (?, ?, ?)",
                (
                    session_id,
                    row[0],
                    _encode({"type": event_type, "data": deepcopy(data)}),
                ),
            )

    def read_events(self, session_id: str, after: int = 0) -> tuple[tuple[int, dict], ...]:
        now = self._now()
        with self._lock, self._connect() as connection:
            self._require(connection, session_id, now)
            return tuple(
                (sequence, _decode(value))
                for sequence, value in connection.execute(
                    """
                    SELECT sequence, value FROM events
                    WHERE session_id = ? AND sequence > ? ORDER BY sequence
                    """,
                    (session_id, max(0, after)),
                )
            )

    def next_event(self, session_id: str) -> dict | None:
        offset = self._next_offsets.get(session_id, 0)
        events = self.read_events(session_id, after=offset)
        if not events:
            return None
        sequence, event = events[0]
        self._next_offsets[session_id] = sequence
        return event

    def reset_failed_research(self, session_id: str, retryable_codes: set[str]) -> bool:
        now = self._now()
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._require(connection, session_id, now)
            values = {
                name: _decode(value)
                for name, value in connection.execute(
                    "SELECT name, value FROM session_values WHERE session_id = ?",
                    (session_id,),
                )
            }
            if (
                values.get("status") != "failed"
                or values.get("failure_code") not in retryable_codes
            ):
                return False
            stale = [
                name
                for name in values
                if name in {"failure_code", "result", "evidence_by_id", "validation_issues"}
                or name.startswith("research_")
                or name.endswith("_research")
            ]
            connection.executemany(
                "DELETE FROM session_values WHERE session_id = ? AND name = ?",
                ((session_id, name) for name in stale),
            )
            connection.execute(
                "UPDATE session_values SET value = ? WHERE session_id = ? AND name = 'status'",
                (_encode("created"), session_id),
            )
            connection.execute("DELETE FROM events WHERE session_id = ?", (session_id,))
            connection.execute(
                "INSERT INTO events VALUES (?, 1, ?)",
                (session_id, _encode({"type": "run_started", "data": {}})),
            )
            connection.execute(
                """
                UPDATE sessions SET status = 'created', expires_at = ?, updated_at = ?
                WHERE session_id = ?
                """,
                (now + self._ttl_seconds, now, session_id),
            )
            self._next_offsets.pop(session_id, None)
            return True

    def delete(self, session_id: str) -> None:
        now = self._now()
        with self._lock, self._connect() as connection:
            self._purge_expired(connection, now)
            parents = {
                candidate_id: _decode(value)
                for candidate_id, value in connection.execute(
                    """
                    SELECT session_id, value FROM session_values
                    WHERE name = 'parent_assessment_id'
                    """
                )
            }
            existing = {
                value
                for value, in connection.execute("SELECT session_id FROM sessions")
            }
            lineage_ids = {session_id}
            while True:
                related = {
                    candidate_id
                    for candidate_id, parent_id in parents.items()
                    if parent_id in lineage_ids
                }
                related.update(
                    parent_id
                    for candidate_id, parent_id in parents.items()
                    if candidate_id in lineage_ids and parent_id in existing
                )
                if related <= lineage_ids:
                    break
                lineage_ids.update(related)
            connection.executemany(
                "DELETE FROM sessions WHERE session_id = ?",
                ((candidate_id,) for candidate_id in lineage_ids),
            )
            for candidate_id in lineage_ids:
                self._next_offsets.pop(candidate_id, None)

    def count(self) -> int:
        now = self._now()
        with self._lock, self._connect() as connection:
            self._purge_expired(connection, now)
            return connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]

    def requeue_stale(self, stale_after_seconds: int) -> int:
        now = self._now()
        cutoff = now - stale_after_seconds
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT session_id FROM sessions WHERE status = 'running' AND updated_at <= ?",
                (cutoff,),
            ).fetchall()
            for session_id, in rows:
                connection.execute(
                    "UPDATE sessions SET status = 'queued', updated_at = ? WHERE session_id = ?",
                    (now, session_id),
                )
                connection.execute(
                    "UPDATE session_values SET value = ? WHERE session_id = ? AND name = 'status'",
                    (_encode("queued"), session_id),
                )
            return len(rows)

    def claim_next(self) -> str | None:
        now = self._now()
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._purge_expired(connection, now)
            row = connection.execute(
                """
                SELECT session_id FROM sessions
                WHERE status = 'queued' ORDER BY updated_at, session_id LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            session_id = row[0]
            connection.execute(
                "UPDATE sessions SET status = 'running', updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )
            connection.execute(
                "UPDATE session_values SET value = ? WHERE session_id = ? AND name = 'status'",
                (_encode("running"), session_id),
            )
            return session_id
