import time
from threading import Event
from types import SimpleNamespace

from cpf_fcv_reviewer.background import PersistentAssessmentWorker


class ClaimingStore:
    def __init__(self):
        self.claims = ["assessment-1", None]
        self.requeued_with = None
        self.updated = []

    def requeue_stale(self, seconds):
        self.requeued_with = seconds
        return 1

    def claim_next(self):
        return self.claims.pop(0) if self.claims else None

    def update(self, assessment_id, **values):
        self.updated.append((assessment_id, values))

    def get(self, assessment_id):
        return SimpleNamespace(payload={})

    def remove_keys(self, assessment_id, *keys):
        pass


def test_persistent_worker_recovers_and_runs_claimed_assessment(monkeypatch):
    store = ClaimingStore()
    ran = Event()

    def fake_run(app, assessment_id):
        assert app == "app"
        assert assessment_id == "assessment-1"
        ran.set()

    monkeypatch.setattr("cpf_fcv_reviewer.routes.run_assessment", fake_run)
    worker = PersistentAssessmentWorker(
        "app",
        store,
        poll_seconds=0.01,
    )

    worker.start()
    assert ran.wait(timeout=1)
    worker.stop()

    assert store.requeued_with == 0


def test_persistent_worker_enqueue_keeps_job_claimable_and_wakes_worker():
    store = ClaimingStore()
    worker = PersistentAssessmentWorker("app", store, poll_seconds=0.01)

    worker.enqueue("assessment-2")

    assert store.updated == [("assessment-2", {"status": "queued"})]


class RaisingStore(ClaimingStore):
    def __init__(self, claims):
        super().__init__()
        self.claims = list(claims)


def test_persistent_worker_survives_a_failing_assessment(monkeypatch):
    """One unhandled error must not silently kill the only worker thread."""
    store = RaisingStore(["assessment-1", "assessment-2", None])
    completed = Event()
    seen = []

    def fake_run(app, assessment_id):
        seen.append(assessment_id)
        if assessment_id == "assessment-1":
            raise RuntimeError("store write failed")
        completed.set()

    monkeypatch.setattr("cpf_fcv_reviewer.routes.run_assessment", fake_run)
    worker = PersistentAssessmentWorker("app", store, poll_seconds=0.01)

    worker.start()
    assert completed.wait(timeout=2)

    assert seen == ["assessment-1", "assessment-2"]
    assert worker.worker_state == "alive"
    worker.stop()


def test_persistent_worker_reports_stopped_state_after_a_fatal_thread_exit(monkeypatch):
    store = ClaimingStore()
    monkeypatch.setattr("cpf_fcv_reviewer.routes.run_assessment", lambda app, i: None)
    worker = PersistentAssessmentWorker("app", store, poll_seconds=0.01)

    worker.start()
    worker.stop()

    assert worker.worker_state == "stopped"


class RecordingStore(ClaimingStore):
    def __init__(self, claims):
        super().__init__()
        self.claims = list(claims)
        self.emitted = []

    def emit(self, assessment_id, kind, data):
        self.emitted.append((assessment_id, kind, data))


def test_persistent_worker_marks_a_stuck_assessment_failed(monkeypatch):
    """If run_assessment could not record its own failure, the worker must.

    Otherwise the review stays `running` with no terminal event and the browser
    waits on a stream that will never resolve.
    """
    store = RecordingStore(["assessment-1", None])
    done = Event()

    def fake_run(app, assessment_id):
        done.set()
        raise RuntimeError("failure-state persistence failed")

    monkeypatch.setattr("cpf_fcv_reviewer.routes.run_assessment", fake_run)
    worker = PersistentAssessmentWorker("app", store, poll_seconds=0.01)
    worker.start()
    assert done.wait(timeout=2)
    worker.stop()

    assert ("assessment-1", {"status": "failed", "failure_code": "review_failed"}) in store.updated
    assert store.emitted == [("assessment-1", "run_failed", {"error": "review_failed"})]


def test_persistent_worker_survives_a_failing_claim(monkeypatch):
    """A store error in claim_next must not kill the worker either."""
    calls = []

    class BrokenClaimStore(ClaimingStore):
        def claim_next(self):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("database is locked")
            return None

    store = BrokenClaimStore()
    monkeypatch.setattr("cpf_fcv_reviewer.routes.run_assessment", lambda app, i: None)
    worker = PersistentAssessmentWorker("app", store, poll_seconds=0.01)
    worker.start()
    deadline = time.time() + 2
    while len(calls) < 3 and time.time() < deadline:
        time.sleep(0.02)
    state = worker.worker_state
    worker.stop()

    assert len(calls) >= 3, "worker stopped claiming after one store error"
    assert state == "alive"


def test_persistent_worker_does_not_log_exception_text(monkeypatch, caplog):
    """Logs record failure shape, never exception text that may quote a document."""
    store = RecordingStore(["assessment-1", None])
    done = Event()

    def fake_run(app, assessment_id):
        done.set()
        raise RuntimeError("SENSITIVE draft wording from an uploaded CPF")

    monkeypatch.setattr("cpf_fcv_reviewer.routes.run_assessment", fake_run)
    worker = PersistentAssessmentWorker("app", store, poll_seconds=0.01)
    with caplog.at_level("ERROR"):
        worker.start()
        assert done.wait(timeout=2)
        worker.stop()

    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "SENSITIVE" not in logged
    assert "Traceback" not in caplog.text
    assert "RuntimeError" in logged


def test_worker_fallback_removes_saved_output_before_failure(tmp_path, make_valid_result):
    from cpf_fcv_reviewer.app import create_app

    result, evidence = make_valid_result
    app = create_app({
        "TESTING": True,
        "START_BACKGROUND_RUNS": False,
        "PERSISTENCE_PATH": str(tmp_path / "reviews.sqlite3"),
    })
    store = app.extensions["session_store"]
    assessment_id = store.create({
        "status": "complete",
        "country": "Benin",
        "result": result.model_dump(mode="json"),
        "evidence_by_id": {key: item.model_dump(mode="json") for key, item in evidence.items()},
        "validation_issues": ["stale"],
        "research_summary": "partial",
        "current_research": "partial",
    })
    client = app.test_client()
    assert client.get(f"/api/reviews/{assessment_id}/result").status_code == 200

    PersistentAssessmentWorker(app, store)._fail_closed(assessment_id)

    payload = store.get(assessment_id).payload
    assert payload == {"status": "failed", "country": "Benin", "failure_code": "review_failed"}
    response = client.get(f"/api/reviews/{assessment_id}/result")
    assert response.status_code == 202
    assert response.get_json() == {"status": "failed"}
