from io import BytesIO

from cpf_fcv_reviewer.app import create_app
from cpf_fcv_reviewer.persistent_store import SQLiteSessionStore


def test_sqlite_store_round_trips_binary_payload_across_instances(tmp_path):
    path = tmp_path / "reviews.sqlite3"
    first = SQLiteSessionStore(path, ttl_seconds=60)
    assessment_id = first.create(
        {
            "country": "Haiti",
            "cpf": {"name": "cpf.pdf", "bytes": b"%PDF-1.7\x00payload"},
            "status": "created",
        }
    )
    second = SQLiteSessionStore(path, ttl_seconds=60)

    assert second.get(assessment_id).payload["cpf"]["bytes"] == b"%PDF-1.7\x00payload"


def test_sqlite_store_restores_bounded_assistant_history_across_instances(tmp_path):
    path = tmp_path / "reviews.sqlite3"
    first = SQLiteSessionStore(path, ttl_seconds=60)
    assessment_id = first.create({"status": "complete"})
    history = [
        {"role": "user", "content": "Clarify the assessment."},
        {"role": "assistant", "content": "Grounded clarification."},
    ]
    first.update(assessment_id, assistant_history=history)

    second = SQLiteSessionStore(path, ttl_seconds=60)

    assert second.get(assessment_id).payload["assistant_history"] == history


def test_sqlite_events_are_replayable_by_cursor(tmp_path):
    store = SQLiteSessionStore(tmp_path / "reviews.sqlite3", ttl_seconds=60)
    assessment_id = store.create({"status": "created"})
    store.emit(assessment_id, "step_start", {"step": "extract"})
    store.emit(assessment_id, "step_complete", {"step": "extract"})

    assert store.read_events(assessment_id, after=0) == (
        (1, {"type": "step_start", "data": {"step": "extract"}}),
        (2, {"type": "step_complete", "data": {"step": "extract"}}),
    )
    assert store.read_events(assessment_id, after=1) == (
        (2, {"type": "step_complete", "data": {"step": "extract"}}),
    )


def test_sqlite_claim_is_transactional_and_restart_visible(tmp_path):
    path = tmp_path / "reviews.sqlite3"
    first = SQLiteSessionStore(path, ttl_seconds=60)
    assessment_id = first.create({"status": "created"})
    second = SQLiteSessionStore(path, ttl_seconds=60)
    first.update(assessment_id, status="queued")

    assert first.claim_next() == assessment_id
    assert second.claim_next() is None
    assert second.get(assessment_id).payload["status"] == "running"


def test_sqlite_lineage_delete_removes_parent_children_and_grandchildren(tmp_path):
    store = SQLiteSessionStore(tmp_path / "reviews.sqlite3", ttl_seconds=60)
    parent = store.create({"status": "complete"})
    child = store.create({"status": "complete", "parent_assessment_id": parent})
    grandchild = store.create({"status": "complete", "parent_assessment_id": child})
    unrelated = store.create({"status": "created"})

    store.delete(grandchild)

    assert store.count() == 1
    assert store.get(unrelated).payload["status"] == "created"


class RecordingQueue:
    mode = "recording"

    def __init__(self):
        self.assessment_ids = []

    def enqueue(self, assessment_id):
        self.assessment_ids.append(assessment_id)


def test_create_review_enqueues_instead_of_starting_route_thread():
    queue = RecordingQueue()
    app = create_app(
        {"TESTING": True, "START_BACKGROUND_RUNS": True},
        services={"assessment_queue": queue},
    )
    response = app.test_client().post(
        "/api/reviews",
        data={
            "country": "Haiti",
            "review_stage": "concept_review",
            "cpf": (BytesIO(b"Readable CPF text " * 20), "cpf.txt"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assert queue.assessment_ids == [response.get_json()["assessment_id"]]


def test_sse_replays_events_after_last_event_id_without_consuming_them():
    app = create_app({"TESTING": True, "START_BACKGROUND_RUNS": False})
    store = app.extensions["session_store"]
    assessment_id = store.create({"status": "complete"})
    store.emit(assessment_id, "step_complete", {"step": "extract"})
    store.emit(assessment_id, "run_complete", {"repair_count": 0})

    response = app.test_client().get(
        f"/api/reviews/{assessment_id}/events",
        headers={"Last-Event-ID": "1"},
    )

    body = response.get_data(as_text=True)
    assert "event: step_complete" not in body
    assert "id: 2" in body
    assert "event: run_complete" in body
    assert store.read_events(assessment_id, after=0)[-1][1]["type"] == "run_complete"
