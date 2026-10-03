"""Provider-free regressions for public cost and concurrency admission."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Event

import pytest

from cpf_fcv_reviewer.app import create_app


def configured_app(tmp_path, *, services=None, **overrides):
    return create_app({
        "TESTING": True, "START_BACKGROUND_RUNS": False,
        "PUBLIC_LIMITS_ENABLED": True,
        "PERSISTENCE_PATH": str(tmp_path / "reviews.sqlite3"),
        "PUBLIC_REVIEW_DAILY_LIMIT": 4,
        "PUBLIC_CLIENT_REVIEW_HOURLY_LIMIT": 10,
        "MAX_PENDING_ASSESSMENTS": 10,
        **overrides,
    }, services=services, use_environment=False)


def submit(app, *, client="192.0.2.1", stage="concept_review"):
    return app.test_client().post("/api/reviews", data={
        "country": "Benin", "review_stage": stage,
        "cpf": (BytesIO(b"Readable synthetic CPF text. " * 20), "cpf.txt"),
    }, environ_overrides={"REMOTE_ADDR": client})


class RejectingQueue:
    def enqueue(self, assessment_id):
        from cpf_fcv_reviewer.background import AssessmentQueueFull

        raise AssessmentQueueFull()


class StubFollowOnGateway:
    def stream(self, **kwargs):
        yield "Synthetic response."


def create_complete_review(app, make_valid_result):
    result, evidence = make_valid_result
    return app.extensions["session_store"].create({
        "status": "complete",
        "result": result.model_dump(mode="json"),
        "evidence_by_id": {
            evidence_id: item.model_dump(mode="json")
            for evidence_id, item in evidence.items()
        },
    })


def test_invalid_stage_allocates_no_session_or_daily_quota(tmp_path):
    app = configured_app(tmp_path)
    response = submit(app, stage="unsupported")
    assert response.status_code == 400
    assert app.extensions["session_store"].count() == 0
    assert submit(app).status_code == 201


def test_daily_cap_is_global_persistent_and_not_reset_by_deleting_reviews(tmp_path):
    app = configured_app(tmp_path)
    for index in range(4):
        response = submit(app, client=f"192.0.2.{index + 1}")
        assert response.status_code == 201
        app.extensions["session_store"].delete(response.json["assessment_id"])
    assert submit(app, client="192.0.2.99").status_code == 429
    restored = configured_app(tmp_path)
    response = submit(restored, client="192.0.2.100")
    assert response.status_code == 429
    assert response.json["code"] == "daily_assessment_limit"
    assert int(response.headers["Retry-After"]) > 0


def test_parallel_submissions_cannot_exceed_daily_cap(tmp_path):
    app = configured_app(tmp_path)
    with ThreadPoolExecutor(max_workers=12) as pool:
        codes = list(pool.map(lambda index: submit(app, client=f"192.0.2.{index}").status_code,
                              range(1, 13)))
    assert codes.count(201) == 4
    assert codes.count(429) == 8
    assert app.extensions["session_store"].count() == 4


def test_pending_cap_rejects_before_session_allocation(tmp_path):
    app = configured_app(tmp_path, MAX_PENDING_ASSESSMENTS=1)
    assert submit(app).status_code == 201
    response = submit(app, client="192.0.2.2")
    assert response.status_code == 503
    assert response.json["code"] == "assessment_queue_full"
    assert app.extensions["session_store"].count() == 1


def test_client_rate_does_not_trust_spoofed_forwarded_header(tmp_path):
    app = configured_app(tmp_path, PUBLIC_CLIENT_REVIEW_HOURLY_LIMIT=1)
    assert submit(app).status_code == 201
    response = app.test_client().post("/api/reviews", data={
        "country": "Benin", "review_stage": "concept_review",
        "cpf": (BytesIO(b"synthetic CPF"), "cpf.txt"),
    }, headers={"X-Forwarded-For": "203.0.113.9",
                "CF-Connecting-IP": "203.0.113.9"},
       environ_overrides={"REMOTE_ADDR": "192.0.2.1"})
    assert response.status_code == 429
    assert response.json["code"] == "client_review_limit"


def test_trusted_proxy_uses_valid_cf_ip_and_falls_back_on_invalid_ip(tmp_path):
    app = configured_app(
        tmp_path,
        TRUST_RENDER_PROXY=True,
        PUBLIC_CLIENT_REVIEW_HOURLY_LIMIT=1,
    )
    client = app.test_client()

    def post(remote_addr, cf_ip):
        return client.post(
            "/api/reviews",
            data={
                "country": "Benin",
                "review_stage": "concept_review",
                "cpf": (BytesIO(b"synthetic CPF"), "cpf.txt"),
            },
            headers={"CF-Connecting-IP": cf_ip},
            environ_overrides={"REMOTE_ADDR": remote_addr},
        )

    assert post("192.0.2.1", "203.0.113.1").status_code == 201
    assert post("192.0.2.1", "203.0.113.2").status_code == 201
    assert post("198.51.100.7", "invalid").status_code == 201
    response = post("198.51.100.7", "invalid")
    assert response.status_code == 429
    assert response.json["code"] == "client_review_limit"


def test_corrections_and_retries_share_daily_review_allowance(tmp_path):
    app = configured_app(tmp_path, PUBLIC_REVIEW_DAILY_LIMIT=3)
    client = app.test_client()
    original = submit(app)
    assessment_id = original.json["assessment_id"]

    correction = client.post(
        f"/api/reviews/{assessment_id}/corrections",
        json={"text": "Clarify the geographic targeting."},
        environ_overrides={"REMOTE_ADDR": "192.0.2.1"},
    )
    assert correction.status_code == 201
    app.extensions["session_store"].update(
        assessment_id,
        status="failed",
        failure_code="research_provider_failed",
    )

    retry = client.post(
        f"/api/reviews/{assessment_id}/retry-research",
        environ_overrides={"REMOTE_ADDR": "192.0.2.1"},
    )
    assert retry.status_code == 202
    response = client.post(
        f"/api/reviews/{assessment_id}/corrections",
        json={"text": "One more change."},
        environ_overrides={"REMOTE_ADDR": "192.0.2.1"},
    )
    assert response.status_code == 429
    assert response.json["code"] == "daily_assessment_limit"


def test_queue_full_correction_discards_only_new_child(tmp_path):
    app = configured_app(tmp_path)
    parent = submit(app)
    parent_id = parent.json["assessment_id"]
    app.extensions["assessment_queue"] = RejectingQueue()

    response = app.test_client().post(
        f"/api/reviews/{parent_id}/corrections",
        json={"text": "Clarify the geographic targeting."},
    )

    assert response.status_code == 503
    assert response.json["code"] == "assessment_queue_full"
    store = app.extensions["session_store"]
    assert store.get(parent_id).payload["status"] == "created"
    assert store.count() == 1


def test_retry_queue_full_returns_503_and_restores_failed_state(tmp_path):
    app = configured_app(tmp_path)
    store = app.extensions["session_store"]
    assessment_id = store.create({
        "status": "failed",
        "failure_code": "research_timeout",
        "research_context": {"partial": "retained"},
    })
    app.extensions["assessment_queue"] = RejectingQueue()

    response = app.test_client().post(
        f"/api/reviews/{assessment_id}/retry-research",
    )

    assert response.status_code == 503
    assert response.json["code"] == "assessment_queue_full"
    state = store.get(assessment_id)
    assert state.payload["status"] == "failed"
    assert state.payload["failure_code"] == "research_timeout"
    assert state.payload["research_context"] == {"partial": "retained"}
    assert state.events[-1]["type"] == "run_failed"


def test_assistant_daily_cap_applies_across_reviews(tmp_path, make_valid_result):
    app = configured_app(
        tmp_path,
        services={"follow_on_gateway": StubFollowOnGateway()},
        PUBLIC_ASSISTANT_DAILY_LIMIT=1,
    )
    first_id = create_complete_review(app, make_valid_result)
    second_id = create_complete_review(app, make_valid_result)
    client = app.test_client()

    first = client.post(
        f"/api/reviews/{first_id}/assistant", json={"message": "Explain this."}
    )
    assert first.status_code == 200
    first.get_data()
    first.close()
    response = client.post(
        f"/api/reviews/{second_id}/assistant", json={"message": "Explain this."}
    )

    assert response.status_code == 429
    assert response.json["code"] == "daily_assistant_limit"


def test_unstarted_assistant_stream_close_clears_active_and_releases_slot(
    tmp_path, make_valid_result
):
    app = configured_app(
        tmp_path,
        services={"follow_on_gateway": StubFollowOnGateway()},
    )
    first_id = create_complete_review(app, make_valid_result)
    second_id = create_complete_review(app, make_valid_result)
    client = app.test_client()

    first = client.post(
        f"/api/reviews/{first_id}/assistant",
        json={"message": "Explain this."},
        buffered=False,
    )
    assert first.status_code == 200
    assert app.extensions["session_store"].get(first_id).payload["assistant_active"] is True
    busy = client.post(
        f"/api/reviews/{second_id}/assistant", json={"message": "Explain this."}
    )
    assert busy.status_code == 503
    assert busy.json["code"] == "assistant_busy"

    first.close()
    first.close()
    assert app.extensions["session_store"].get(first_id).payload["assistant_active"] is False
    retry = client.post(
        f"/api/reviews/{first_id}/assistant", json={"message": "Try again."}
    )
    assert retry.status_code == 200


def test_assistant_active_update_failure_releases_slot(tmp_path, make_valid_result, monkeypatch):
    app = configured_app(
        tmp_path,
        services={"follow_on_gateway": StubFollowOnGateway()},
    )
    assessment_id = create_complete_review(app, make_valid_result)
    store = app.extensions["session_store"]
    original_update = store.update

    def fail_after_update(session_id, **values):
        original_update(session_id, **values)
        if values.get("assistant_active") is True:
            raise RuntimeError("synthetic persistence failure")

    monkeypatch.setattr(store, "update", fail_after_update)
    response = app.test_client().post(
        f"/api/reviews/{assessment_id}/assistant",
        json={"message": "Explain this."},
    )

    assert response.status_code == 503
    assert store.get(assessment_id).payload["assistant_active"] is False
    slot = app.extensions["public_admission"].assistant_slots
    assert slot.acquire(blocking=False)
    slot.release()


def test_assistant_close_releases_slot_even_if_store_cleanup_fails(
    tmp_path, make_valid_result, monkeypatch
):
    app = configured_app(
        tmp_path,
        services={"follow_on_gateway": StubFollowOnGateway()},
    )
    assessment_id = create_complete_review(app, make_valid_result)
    store = app.extensions["session_store"]
    original_update = store.update

    def fail_deactivation(session_id, **values):
        if values.get("assistant_active") is False:
            raise RuntimeError("synthetic persistence failure")
        original_update(session_id, **values)

    monkeypatch.setattr(store, "update", fail_deactivation)
    response = app.test_client().post(
        f"/api/reviews/{assessment_id}/assistant",
        json={"message": "Explain this."},
        buffered=False,
    )
    assert response.status_code == 200

    response.close()
    slot = app.extensions["public_admission"].assistant_slots
    assert slot.acquire(blocking=False)
    slot.release()


def test_review_event_streams_are_bounded_and_close_releases_slot(tmp_path):
    app = configured_app(tmp_path, MAX_EVENT_STREAMS=1)
    assessment_id = app.extensions["session_store"].create({"status": "running"})
    client = app.test_client()

    first = client.get(f"/api/reviews/{assessment_id}/events", buffered=False)
    assert first.status_code == 200
    busy = client.get(f"/api/reviews/{assessment_id}/events", buffered=False)
    assert busy.status_code == 503
    assert busy.json["code"] == "event_stream_limit"

    first.close()
    reopened = client.get(f"/api/reviews/{assessment_id}/events", buffered=False)
    assert reopened.status_code == 200
    reopened.close()


def test_development_queue_uses_one_worker_and_bounded_pending_capacity(monkeypatch):
    from cpf_fcv_reviewer.background import InProcessAssessmentQueue, AssessmentQueueFull
    entered, release = Event(), Event()
    seen = []
    def run(app, assessment_id):
        seen.append(assessment_id)
        entered.set()
        release.wait(2)
    monkeypatch.setattr("cpf_fcv_reviewer.routes.run_assessment", run)
    queue = InProcessAssessmentQueue("synthetic", enabled=True, max_pending=1)
    try:
        queue.enqueue("one")
        assert entered.wait(1)
        queue.enqueue("two")
        with pytest.raises(AssessmentQueueFull):
            queue.enqueue("three")
        assert seen == ["one"]
    finally:
        release.set()
        queue.stop()


def test_restart_fails_running_work_without_replay_but_preserves_queue(tmp_path):
    from cpf_fcv_reviewer.persistent_store import SQLiteSessionStore
    store = SQLiteSessionStore(tmp_path / "reviews.sqlite3", ttl_seconds=60)
    interrupted = store.create({"status": "running"})
    queued = store.create({"status": "queued"})
    assert store.interrupt_running() == 1
    assert store.get(interrupted).payload["failure_code"] == "assessment_interrupted"
    assert store.claim_next() == queued
    assert store.claim_next() is None
