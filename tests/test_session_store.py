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


def test_create_deeply_owns_nested_payloads_and_session_snapshots():
    store = VolatileSessionStore(ttl_seconds=60)
    source = {"context": {"items": ["initial"]}}
    first = store.create(source)
    second = store.create(source)

    source["context"]["items"].append("caller-mutation")
    first_snapshot = store.get(first)
    first_snapshot.payload["context"]["items"].append("snapshot-mutation")

    assert store.get(first).payload["context"]["items"] == ["initial"]
    assert store.get(second).payload["context"]["items"] == ["initial"]


def test_get_returns_a_detached_snapshot_and_delete_discards_store_state():
    now = datetime.now(UTC)
    store = VolatileSessionStore(ttl_seconds=60, clock=lambda: now)
    session_id = store.create({"context": {"status": "new"}})
    store.emit(session_id, "step_start", {"step": "extract"})

    snapshot = store.get(session_id)
    snapshot.payload["context"]["status"] = "mutated"
    snapshot.events.clear()
    snapshot.expires_at = now

    actual = store.get(session_id)
    assert actual.payload["context"]["status"] == "new"
    assert actual.expires_at == now + timedelta(seconds=60)
    assert store.next_event(session_id) == {
        "type": "step_start",
        "data": {"step": "extract"},
    }

    store.delete(session_id)
    snapshot.payload["context"]["status"] = "irrelevant"
    with pytest.raises(SessionExpired):
        store.get(session_id)


def test_update_deep_copies_keyword_values():
    store = VolatileSessionStore(ttl_seconds=60)
    session_id = store.create({"country": "A"})
    result = {"questions": ["one"]}

    store.update(session_id, result=result)
    result["questions"].append("caller-mutation")

    assert store.get(session_id).payload["result"] == {"questions": ["one"]}


def test_emit_deep_copies_data_and_returns_detached_events():
    store = VolatileSessionStore(ttl_seconds=60)
    session_id = store.create({"country": "A"})
    data = {"steps": ["extract"]}

    store.emit(session_id, "step_start", data)
    store.emit(session_id, "step_start", data)
    data["steps"].append("caller-mutation")

    first = store.next_event(session_id)
    assert first == {"type": "step_start", "data": {"steps": ["extract"]}}
    first["data"]["steps"].append("returned-mutation")

    assert store.next_event(session_id) == {
        "type": "step_start",
        "data": {"steps": ["extract"]},
    }


@pytest.mark.parametrize("ttl_seconds", [0, -1])
def test_ttl_must_be_positive(ttl_seconds):
    with pytest.raises(ValueError):
        VolatileSessionStore(ttl_seconds=ttl_seconds)


def test_public_operations_opportunistically_sweep_all_expired_sessions():
    now = datetime.now(UTC)
    store = VolatileSessionStore(ttl_seconds=2, clock=lambda: now)
    expired = store.create({"country": "expired"})

    now = now + timedelta(seconds=1)
    live = store.create({"country": "live"})
    now = now + timedelta(seconds=1, milliseconds=500)

    assert store.get(live).payload["country"] == "live"
    assert set(store._items) == {live}
    assert expired not in store._items

    another_expired = store.create({"country": "another-expired"})
    now = now + timedelta(seconds=3)
    replacement = store.create({"country": "replacement"})

    assert set(store._items) == {replacement}
    assert another_expired not in store._items

    now = now + timedelta(seconds=3)
    assert store.count() == 0


def test_update_refreshes_expiry_but_event_operations_do_not():
    now = datetime.now(UTC)
    store = VolatileSessionStore(ttl_seconds=10, clock=lambda: now)
    session_id = store.create({"country": "A"})

    now = now + timedelta(seconds=2)
    store.update(session_id, status="complete")
    refreshed_expiry = now + timedelta(seconds=10)

    now = now + timedelta(seconds=1)
    store.emit(session_id, "step_start", {"step": "extract"})
    assert store.get(session_id).expires_at == refreshed_expiry
    now = now + timedelta(seconds=1)
    assert store.next_event(session_id) == {
        "type": "step_start",
        "data": {"step": "extract"},
    }
    assert store.get(session_id).expires_at == refreshed_expiry


def test_remove_keys_clears_stale_payload_and_refreshes_expiry():
    now = datetime.now(UTC)
    store = VolatileSessionStore(ttl_seconds=10, clock=lambda: now)
    session_id = store.create(
        {
            "country": "A",
            "result": {"stale": True},
            "evidence": ["stale evidence"],
            "failure": "stale failure",
            "status": "running",
        }
    )
    original_expiry = store.get(session_id).expires_at

    now = now + timedelta(seconds=2)
    store.remove_keys(session_id, "result", "evidence", "failure")

    state = store.get(session_id)
    assert state.payload == {"country": "A", "status": "running"}
    assert state.expires_at == now + timedelta(seconds=10)
    assert state.expires_at > original_expiry


def test_remove_keys_ignores_missing_keys_and_preserves_session():
    store = VolatileSessionStore(ttl_seconds=60)
    session_id = store.create({"country": "A", "status": "running"})

    store.remove_keys(session_id, "result", "failure", "missing")

    assert store.get(session_id).payload == {"country": "A", "status": "running"}


def test_remove_keys_raises_for_nonexistent_session():
    store = VolatileSessionStore(ttl_seconds=60)

    with pytest.raises(SessionExpired):
        store.remove_keys("missing", "result")
