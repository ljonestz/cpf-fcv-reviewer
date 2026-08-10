from __future__ import annotations

from collections import deque
from collections.abc import Callable
from copy import deepcopy
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
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive.")
        self._ttl = timedelta(seconds=ttl_seconds)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._items: dict[str, SessionState] = {}
        self._lock = RLock()

    def _purge_expired(self, now: datetime) -> None:
        expired_ids = [
            session_id
            for session_id, state in self._items.items()
            if state.expires_at <= now
        ]
        for session_id in expired_ids:
            self._items.pop(session_id, None)

    def _get_state(self, session_id: str, now: datetime) -> SessionState:
        self._purge_expired(now)
        state = self._items.get(session_id)
        if state is None:
            raise SessionExpired(session_id)
        return state

    def create(self, payload: dict) -> str:
        with self._lock:
            now = self._clock()
            self._purge_expired(now)
            session_id = uuid4().hex
            self._items[session_id] = SessionState(
                session_id=session_id,
                payload=deepcopy(payload),
                expires_at=now + self._ttl,
            )
            return session_id

    def get(self, session_id: str) -> SessionState:
        with self._lock:
            state = self._get_state(session_id, self._clock())
            return deepcopy(state)

    def update(self, session_id: str, **values) -> None:
        with self._lock:
            now = self._clock()
            state = self._get_state(session_id, now)
            state.payload.update(deepcopy(values))
            state.expires_at = now + self._ttl

    def emit(self, session_id: str, event_type: str, data: dict) -> None:
        with self._lock:
            state = self._get_state(session_id, self._clock())
            state.events.append(deepcopy({"type": event_type, "data": data}))

    def next_event(self, session_id: str) -> dict | None:
        with self._lock:
            state = self._get_state(session_id, self._clock())
            return deepcopy(state.events.popleft()) if state.events else None

    def delete(self, session_id: str) -> None:
        with self._lock:
            now = self._clock()
            self._purge_expired(now)
            self._items.pop(session_id, None)

    def count(self) -> int:
        with self._lock:
            self._purge_expired(self._clock())
            return len(self._items)
