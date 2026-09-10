"""Concurrent SSE viewers must not starve the deployed gunicorn thread pool.

The bounded event-stream lifetime limits how long one viewer holds a request
thread, but it does not stop several viewers from holding every thread at
once. Render restarts the instance when `/health` stops answering, which kills
any in-flight review, so this is measured against real gunicorn with the
worker flags the deployment actually uses.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Concurrent viewers the production instance must survive. Held streams are
# the whole point of the test, so this stays below the configured thread count
# rather than being derived from it.
HELD_STREAMS = 8
HEALTH_BUDGET_SECONDS = 2.0
HEALTH_PROBES = 3

_START_COMMAND = re.compile(r"^\s*startCommand:\s*(?P<command>gunicorn .+?)\s*$", re.MULTILINE)


def deployed_gunicorn_argv() -> list[str]:
    """The candidate Blueprint command; live dashboard overrides need separate checks."""
    blueprint = (REPO_ROOT / "render.yaml").read_text(encoding="utf-8")
    match = _START_COMMAND.search(blueprint)
    assert match is not None, "render.yaml has no gunicorn startCommand"
    return shlex.split(match.group("command"))


def _free_port() -> int:
    # Bound and released immediately; CI parallelism makes a hardcoded port unsafe.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _multipart_body(boundary: str, fields: dict[str, str], filename: str, content: str) -> bytes:
    parts = [
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="cpf"; filename="{filename}"\r\n'
        f"Content-Type: text/plain\r\n\r\n{content}\r\n"
    ]
    for name, value in fields.items():
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; "
            f'name="{name}"\r\n\r\n{value}\r\n'
        )
    return ("".join(parts) + f"--{boundary}--\r\n").encode("utf-8")


def _create_pending_assessment(base_url: str) -> str:
    """Submit a review the disabled worker never runs, so its stream stays open."""
    boundary = "----cpffcvstreamprobe"
    body = _multipart_body(
        boundary,
        {"country": "Benin", "review_stage": "concept_review"},
        "synthetic.txt",
        "Strategic context for the synthetic smoke package. " * 40,
    )
    request = urllib.request.Request(
        f"{base_url}/api/reviews",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())["assessment_id"]


def _wait_for_health(base_url: str, deadline: float) -> bool:
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=5) as response:
                if response.status == 200:
                    return True
        except OSError:
            time.sleep(0.2)
    return False


def _probe_health(base_url: str) -> float:
    started = time.monotonic()
    with urllib.request.urlopen(f"{base_url}/health", timeout=5) as response:
        assert response.status == 200
        response.read()
    return time.monotonic() - started


def test_concurrent_event_streams_do_not_starve_the_health_check(tmp_path):
    if sys.platform.startswith("win") or importlib.util.find_spec("gunicorn") is None:
        pytest.skip("gunicorn is unavailable on this platform")

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    shim = tmp_path / "stream_probe_wsgi.py"
    shim.write_text(
        "from cpf_fcv_reviewer.app import create_smoke_app\n"
        "\n"
        "app = create_smoke_app(start_background_runs=False)\n",
        encoding="utf-8",
    )

    argv = deployed_gunicorn_argv()
    arguments = [
        argument.replace("0.0.0.0:$PORT", f"127.0.0.1:{port}") for argument in argv[1:]
    ]
    arguments[arguments.index("wsgi:app")] = "stream_probe_wsgi:app"
    log_path = tmp_path / "gunicorn.log"
    environment = dict(os.environ, PYTHONPATH=str(tmp_path))

    held: list = []
    established = threading.Semaphore(0)
    with log_path.open("wb") as log:
        server = subprocess.Popen(
            [sys.executable, "-m", "gunicorn", *arguments],
            cwd=str(REPO_ROOT),
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            if not _wait_for_health(base_url, time.monotonic() + 30):
                pytest.fail(
                    "gunicorn did not become healthy:\n"
                    + log_path.read_text(encoding="utf-8", errors="replace")
                )

            assessment_ids = [
                _create_pending_assessment(base_url) for _ in range(HELD_STREAMS)
            ]

            def hold(assessment_id: str) -> None:
                try:
                    stream = urllib.request.urlopen(
                        f"{base_url}/api/reviews/{assessment_id}/events", timeout=60
                    )
                except OSError:
                    return
                held.append(stream)
                established.release()

            holders = [
                threading.Thread(target=hold, args=(assessment_id,), daemon=True)
                for assessment_id in assessment_ids
            ]
            for holder in holders:
                holder.start()

            # Streams that never connect are themselves starvation, so give the
            # pool a bounded grace period instead of waiting for all of them.
            grace = time.monotonic() + 10
            connected = 0
            while connected < HELD_STREAMS and time.monotonic() < grace:
                if established.acquire(timeout=0.2):
                    connected += 1

            assert connected == HELD_STREAMS, (
                f"Only {connected}/{HELD_STREAMS} event streams connected"
            )
            latencies = []
            for _ in range(HEALTH_PROBES):
                latencies.append(_probe_health(base_url))
                time.sleep(0.2)

            assert max(latencies) < HEALTH_BUDGET_SECONDS, (
                f"{HELD_STREAMS} held event streams starved /health "
                f"({connected} streams connected; latencies="
                f"{[round(value, 2) for value in latencies]}s); "
                "raise the configured gunicorn thread count"
            )
        finally:
            for stream in held:
                stream.close()
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=15)


@pytest.mark.parametrize("error", [
    OSError("connection refused"),
    urllib.error.HTTPError("http://local/health", 503, "unhealthy", {}, None),
])
def test_health_probe_rejects_fast_failures(monkeypatch, error):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(urllib.request, "urlopen", fail)
    with pytest.raises(OSError):
        _probe_health("http://local")
