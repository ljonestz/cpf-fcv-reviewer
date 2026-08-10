from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import RLock
from uuid import uuid4


class SessionExpired(KeyError):
    """Raised when a volatile assessment session is unavailable."""


@dataclass
class SessionState:
    session_id: str
    payload: dict
    expires_at: datetime
    events: deque[dict] = field(default_factory=deque)


class VolatileSessionStore:
    """Thread-safe, process-local assessment state with expiring event queues."""

    def __init__(
        self,
        ttl_seconds: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._items: dict[str, SessionState] = {}
        self._lock = RLock()

    def create(self, payload: dict) -> str:
        with self._lock:
            session_id = uuid4().hex
            self._items[session_id] = SessionState(
                session_id=session_id,
                payload=payload.copy(),
                expires_at=self._clock() + self._ttl,
            )
            return session_id

    def get(self, session_id: str) -> SessionState:
        with self._lock:
            state = self._items.get(session_id)
            if state is None:
                raise SessionExpired(session_id)
            if state.expires_at <= self._clock():
                self._items.pop(session_id, None)
                raise SessionExpired(session_id)
            return state

    def update(self, session_id: str, payload: dict) -> SessionState:
        with self._lock:
            state = self.get(session_id)
            state.payload.update(payload)
            state.expires_at = self._clock() + self._ttl
            return state

    def emit(self, session_id: str, event_type: str, data: dict) -> None:
        with self._lock:
            self.get(session_id).events.append({"type": event_type, "data": data})

    def next_event(self, session_id: str) -> dict | None:
        with self._lock:
            events = self.get(session_id).events
            return events.popleft() if events else None

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._items.pop(session_id, None)

    def count(self) -> int:
        with self._lock:
            for session_id in list(self._items):
                try:
                    self.get(session_id)
                except SessionExpired:
                    pass
            return len(self._items)
