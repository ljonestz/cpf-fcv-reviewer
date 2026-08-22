from __future__ import annotations

from threading import Condition, Event, Thread


class InProcessAssessmentQueue:
    """Development queue preserving deterministic in-process behaviour."""

    mode = "in_process"

    def __init__(self, app, enabled: bool) -> None:
        self._app = app
        self._enabled = enabled

    def enqueue(self, assessment_id: str) -> None:
        if not self._enabled:
            return
        from .routes import run_assessment

        Thread(
            target=run_assessment,
            args=(self._app, assessment_id),
            daemon=True,
        ).start()


class PersistentAssessmentWorker:
    """Single-instance worker with durable claim and restart recovery."""

    mode = "persistent_worker"

    def __init__(
        self,
        app,
        store,
        *,
        poll_seconds: float = 1.0,
    ) -> None:
        self._app = app
        self._store = store
        self._poll_seconds = poll_seconds
        self._condition = Condition()
        self._stop = Event()
        self._thread = Thread(
            target=self._run,
            name="cpf-fcv-review-worker",
            daemon=True,
        )

    def start(self) -> None:
        self._store.requeue_stale(0)
        self._thread.start()

    def enqueue(self, assessment_id: str) -> None:
        self._store.update(assessment_id, status="queued")
        with self._condition:
            self._condition.notify()

    def stop(self) -> None:
        self._stop.set()
        with self._condition:
            self._condition.notify()
        self._thread.join(timeout=max(1.0, self._poll_seconds * 2))

    def _run(self) -> None:
        from .routes import run_assessment

        while not self._stop.is_set():
            assessment_id = self._store.claim_next()
            if assessment_id is None:
                with self._condition:
                    self._condition.wait(timeout=self._poll_seconds)
                continue
            run_assessment(self._app, assessment_id)
