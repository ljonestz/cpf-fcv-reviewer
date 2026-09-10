from threading import Event

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
