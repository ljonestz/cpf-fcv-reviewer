"""Single-instance public admission quotas; persistent alongside review state."""
from __future__ import annotations

import sqlite3
from hashlib import sha256
from threading import BoundedSemaphore, RLock
from time import time


class AdmissionDenied(Exception):
    def __init__(self, code: str, message: str, *, status: int = 429,
                 retry_after: int = 60) -> None:
        self.code, self.message = code, message
        self.status, self.retry_after = status, max(1, retry_after)
        super().__init__(code)


class PublicAdmission:
    def __init__(self, config, *, path: str = "") -> None:
        self.config = config
        self.enabled = config["PUBLIC_LIMITS_ENABLED"]
        # ponytail: one process/instance; use a shared admission service before scaling.
        self.lock = RLock()
        self.assistant_slots = BoundedSemaphore(1)
        self.stream_slots = BoundedSemaphore(config["MAX_EVENT_STREAMS"])
        self._db = sqlite3.connect(path or ":memory:", check_same_thread=False, timeout=30)
        self._db.execute("""CREATE TABLE IF NOT EXISTS public_admissions (
            scope TEXT NOT NULL, client TEXT NOT NULL, bucket INTEGER NOT NULL,
            count INTEGER NOT NULL, PRIMARY KEY(scope, client, bucket))""")
        self._db.commit()

    def check_and_record(self, kind: str, client: str, *, assessment_id: str = "") -> None:
        if not self.enabled:
            return
        now = int(time())
        day, hour = now // 86400, now // 3600
        key = sha256(client.encode("utf-8")).hexdigest()
        if kind == "review":
            limits = [
                ("review_day", "global", day, self.config["PUBLIC_REVIEW_DAILY_LIMIT"],
                 "daily_assessment_limit", "Today's public assessment allowance is used. Try tomorrow.",
                 (day + 1) * 86400 - now),
                ("review_hour", key, hour, self.config["PUBLIC_CLIENT_REVIEW_HOURLY_LIMIT"],
                 "client_review_limit", "Too many assessments from this connection. Try later.",
                 (hour + 1) * 3600 - now),
            ]
        elif kind == "assistant":
            limits = [
                ("assistant_day", "global", day, self.config["PUBLIC_ASSISTANT_DAILY_LIMIT"],
                 "daily_assistant_limit", "Today's public assistant allowance is used. Try tomorrow.",
                 (day + 1) * 86400 - now),
                ("assistant_hour", key, hour, 6, "client_assistant_limit",
                 "Too many assistant requests from this connection. Try later.",
                 (hour + 1) * 3600 - now),
                ("assistant_review", assessment_id, day, 6, "review_assistant_limit",
                 "This review's assistant allowance is used for today.",
                 (day + 1) * 86400 - now),
            ]
        else:
            limits = [("request_hour", key, hour, 30, "client_request_limit",
                       "Too many upload requests from this connection. Try later.",
                       (hour + 1) * 3600 - now)]
        with self.lock, self._db:
            self._db.execute("BEGIN IMMEDIATE")
            # Counters survive review deletion and restarts, but not indefinitely.
            self._db.execute("DELETE FROM public_admissions WHERE "
                             "(scope LIKE '%hour' AND bucket < ?) OR "
                             "(scope NOT LIKE '%hour' AND bucket < ?)", (hour - 48, day - 2))
            for scope, client_key, bucket, limit, code, message, retry_after in limits:
                row = self._db.execute(
                    "SELECT count FROM public_admissions WHERE scope=? AND client=? AND bucket=?",
                    (scope, client_key, bucket)).fetchone()
                if row and row[0] >= limit:
                    raise AdmissionDenied(code, message, retry_after=retry_after)
            for scope, client_key, bucket, *_ in limits:
                self._db.execute("""INSERT INTO public_admissions VALUES (?, ?, ?, 1)
                    ON CONFLICT(scope,client,bucket) DO UPDATE SET count=count+1""",
                                 (scope, client_key, bucket))

    def require_capacity(self, store) -> None:
        if self.enabled and store.active_count() >= self.config["MAX_PENDING_ASSESSMENTS"]:
            raise AdmissionDenied("assessment_queue_full",
                                  "The assessment queue is full. Try again later.", status=503)
