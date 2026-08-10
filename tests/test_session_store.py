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


def test_update_applies_keyword_values_and_extends_expiry():
    now = datetime.now(UTC)
    store = VolatileSessionStore(ttl_seconds=60, clock=lambda: now)
    session_id = store.create({"country": "A"})
    original_expiry = store.get(session_id).expires_at

    now = now + timedelta(seconds=1)
    store.update(session_id, status="complete", result={"ok": True})

    state = store.get(session_id)
    assert state.payload["status"] == "complete"
    assert state.payload["result"] == {"ok": True}
    assert state.expires_at == now + timedelta(seconds=60)
    assert state.expires_at > original_expiry
