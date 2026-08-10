from datetime import UTC, datetime, timedelta

import pytest

from cpf_fcv_reviewer.session_store import SessionExpired, VolatileSessionStore


def test_sessions_are_isolated_and_resettable():
    store = VolatileSessionStore(ttl_seconds=60)
    first = store.create({"country": "A"})
    second = store.create({"country": "B"})

    assert store.get(first).payload["country"] == "A"
    assert store.get(second).payload["country"] == "B"

    store.delete(first)
    with pytest.raises(SessionExpired):
        store.get(first)
    assert store.get(second).payload["country"] == "B"


def test_expired_session_is_purged():
    now = datetime.now(UTC)
    store = VolatileSessionStore(ttl_seconds=1, clock=lambda: now)
    session_id = store.create({"country": "A"})

    now = now + timedelta(seconds=2)

    with pytest.raises(SessionExpired):
        store.get(session_id)
    assert store.count() == 0


def test_each_session_has_an_independent_event_queue():
    store = VolatileSessionStore(ttl_seconds=60)
    first = store.create({"country": "A"})
    second = store.create({"country": "B"})

    store.emit(first, "step_start", {"step": "extract"})

    assert store.next_event(first) == {
        "type": "step_start",
        "data": {"step": "extract"},
    }
    assert store.next_event(second) is None
