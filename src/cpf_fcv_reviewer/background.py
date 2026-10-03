from __future__ import annotations

import logging
from queue import Empty, Full, Queue
from threading import Condition, Event, Lock, Thread

logger = logging.getLogger(__name__)


class AssessmentQueueFull(RuntimeError):
    """The bounded development queue has no free pending slot."""


class InProcessAssessmentQueue:
    """Bounded single-worker queue for development and the volatile prototype."""

    mode = "in_process"

    def __init__(self, app, enabled: bool, *, max_pending: int = 4) -> None:
        self._app = app
        self._enabled = enabled
        self._jobs = Queue(maxsize=max_pending)
        self._stop = Event()
        self._lock = Lock()
        self._thread = None

    def enqueue(self, assessment_id: str) -> None:
        if not self._enabled:
            return
        with self._lock:
            try:
                self._jobs.put_nowait(assessment_id)
            except Full as error:
                raise AssessmentQueueFull() from error
            if self._thread is None:
                self._thread = Thread(target=self._run, name="cpf-fcv-development-worker", daemon=True)
                self._thread.start()

    def _run(self) -> None:
        from .routes import run_assessment
        while not self._stop.is_set():
            try:
                assessment_id = self._jobs.get(timeout=0.1)
            except Empty:
                continue
            try:
                run_assessment(self._app, assessment_id)
            except Exception as error:
                logger.error("development_worker_failed error_type=%s", type(error).__name__)
            finally:
                self._jobs.task_done()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)


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
        if hasattr(self._store, "interrupt_running"):
            self._store.interrupt_running()
        else:
            self._store.requeue_stale(0)
        self._thread.start()

    def enqueue(self, assessment_id: str) -> None:
        self._store.update(assessment_id, status="queued")
        with self._condition:
            self._condition.notify()

    @property
    def worker_state(self) -> str:
        return "alive" if self._thread.is_alive() else "stopped"

    def stop(self) -> None:
        self._stop.set()
        with self._condition:
            self._condition.notify()
        self._thread.join(timeout=max(1.0, self._poll_seconds * 2))

    def _log_failure(self, event: str, assessment_id: str, error: Exception) -> None:
        """Record the shape of a failure only.

        Exception text can quote an uploaded document or model output, which this
        project does not log, so this mirrors the sanitized reporting in
        routes.run_assessment rather than using logger.exception.
        """
        causes = []
        cause = error.__cause__
        while cause is not None and len(causes) < 3:
            causes.append(type(cause).__name__)
            cause = cause.__cause__
        logger.error(
            "%s assessment_id=%s error_type=%s cause_chain=%s",
            event,
            assessment_id,
            type(error).__name__,
            ">".join(causes) or "none",
        )

    def _fail_closed(self, assessment_id: str) -> None:
        """Last-resort terminal state when run_assessment could not record its own.

        Without this the review stays `running` with no terminal event and the
        browser waits on a stream that never resolves.
        """
        from .routes import _partial_research_keys

        try:
            # A late completion/emit failure can leave a saved result behind.
            # Clear it before publishing the terminal failure, as run_assessment does.
            state = self._store.get(assessment_id)
            self._store.remove_keys(
                assessment_id,
                "result",
                "evidence_by_id",
                "validation_issues",
                *_partial_research_keys(state.payload),
            )
            self._store.update(
                assessment_id, status="failed", failure_code="review_failed"
            )
            self._store.emit(assessment_id, "run_failed", {"error": "review_failed"})
        except Exception as error:
            self._log_failure("assessment_worker_fail_closed_failed", assessment_id, error)

    def _run(self) -> None:
        from .routes import run_assessment

        while not self._stop.is_set():
            # Nothing else in the process runs reviews, so no failure here may be
            # allowed to end this loop: losing it strands every later review.
            try:
                assessment_id = self._store.claim_next()
            except Exception as error:
                self._log_failure("assessment_worker_claim_failed", "none", error)
                with self._condition:
                    self._condition.wait(timeout=self._poll_seconds)
                continue
            if assessment_id is None:
                with self._condition:
                    self._condition.wait(timeout=self._poll_seconds)
                continue
            try:
                run_assessment(self._app, assessment_id)
            except Exception as error:
                self._log_failure("assessment_worker_run_failed", assessment_id, error)
                self._fail_closed(assessment_id)
