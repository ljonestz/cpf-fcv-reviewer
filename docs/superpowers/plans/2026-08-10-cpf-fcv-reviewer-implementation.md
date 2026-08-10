# CPF FCV Reviewer MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and validate a standalone, country-team-first CPF FCV review prototype that produces traceable, stage-calibrated advisory results without making policy or institutional determinations.

**Architecture:** A modular Flask application accepts a CPF/CEN package, keeps all review state in assessment-scoped volatile memory, and exposes one user-visible server-sent-event run over explicit internal orchestration steps. Pydantic contracts separate the Evidence Pack from the immutable Review Result; deterministic validators enforce source locators, diagnostic-mode downgrading, approved registry language, sensitivity handling, and browser/DOCX parity.

**Tech Stack:** Python 3.13, Flask 3.1, Pydantic 2, Anthropic Python SDK behind an adapter, pypdf, python-docx, vanilla JavaScript, pytest, Ruff, gunicorn/gevent, private GitHub, and an isolated Render web service.

---

## Scope and approval gates

This plan implements the MVP reference prototype and validation layer from the approved specification. It does not implement WBG authentication, production retention or audit, operational SharePoint access, an authorized reviewer lane, or production use of sensitive CPF packages.

Target repository root after approval:

C:\Users\wb559324\OneDrive - WBG\Documents\GitHub\cpf-fcv-reviewer

The current specification and this plan remain in the existing cpf_screener folder until the new repository is created.

Two external-action gates are mandatory:

1. After this plan is approved, obtain action-time confirmation immediately before creating private repository ljonestz/cpf-fcv-reviewer.
2. After local implementation and validation are complete, obtain separate action-time confirmation immediately before creating Render service cpf-fcv-review-prototype.

Do not modify, redeploy, restart, or reuse environment variables from the stable FCV Project Screener service.

## Planned file structure

| Path | Responsibility |
|---|---|
| README.md | Purpose, safe-use boundary, setup, tests, and deployment |
| CLAUDE.md | Project-specific commands, architectural rules, and policy guardrails |
| pyproject.toml | Ruff and pytest configuration |
| requirements.txt | Runtime dependencies |
| requirements-dev.txt | Test and lint dependencies |
| Procfile | Render gunicorn/gevent start command |
| wsgi.py | Production application entry point |
| src/cpf_fcv_reviewer/app.py | Flask application factory |
| src/cpf_fcv_reviewer/config.py | Environment-backed settings and safe defaults |
| src/cpf_fcv_reviewer/contracts.py | Pydantic Evidence Pack, Review Result, locator, correction, and metadata types |
| src/cpf_fcv_reviewer/session_store.py | Volatile assessment state, isolation, expiry, reset, and event queues |
| src/cpf_fcv_reviewer/extraction.py | PDF, DOCX, TXT, and Markdown extraction with structural locators |
| src/cpf_fcv_reviewer/sources.py | Upload, approved-registry, public-web, and future SharePoint adapter interfaces |
| src/cpf_fcv_reviewer/registry.py | Approved bundle loading, version checks, exact-language hydration, and fail-closed behavior |
| src/cpf_fcv_reviewer/public_research.py | Public recency/plausibility research and retained-claim validation |
| src/cpf_fcv_reviewer/evidence_builder.py | Evidence Pack assembly and diagnostic-mode selection |
| src/cpf_fcv_reviewer/diagnostic_map.py | Grouped and prioritized RRA/equivalent mapping |
| src/cpf_fcv_reviewer/model_gateway.py | Model abstraction and Anthropic adapter |
| src/cpf_fcv_reviewer/prompts.py | Versioned prompt loading and hashes |
| src/cpf_fcv_reviewer/review_engine.py | Structured review and priority-question generation |
| src/cpf_fcv_reviewer/validators.py | Traceability, policy, stage, sensitivity, correction, and schema validators |
| src/cpf_fcv_reviewer/orchestrator.py | One-run internal workflow, one repair, progress events, and failure states |
| src/cpf_fcv_reviewer/routes.py | Intake, SSE, result, correction/rerun, export, health, and reset routes |
| src/cpf_fcv_reviewer/export_docx.py | DOCX rendering from the validated Review Result |
| src/cpf_fcv_reviewer/templates/index.html | Single-page interface |
| src/cpf_fcv_reviewer/static/app.js | Upload, progress, results, evidence, corrections, rerun, and export UI |
| src/cpf_fcv_reviewer/static/styles.css | Restrained WBG-style visual system |
| prompts/*.md | Diagnostic map, review, repair, and public-research instructions |
| registry_bundles/README.md | Approved-bundle governance and deployment requirement |
| tests/fixtures/* | Synthetic English, French, mixed-language, policy, RRA, and malformed-document fixtures |
| tests/test_*.py | Unit, route, parity, security, and adversarial regression tests |
| docs/superpowers/specs/* | Approved design specification |
| docs/superpowers/plans/* | This implementation plan |

### Task 0: Create the approval-gated private repository and scaffold

**Files:**
- Create: README.md
- Create: CLAUDE.md
- Create: .gitignore
- Create: pyproject.toml
- Create: requirements.txt
- Create: requirements-dev.txt
- Create: Procfile
- Create: wsgi.py
- Copy: docs/superpowers/specs/2026-08-10-cpf-fcv-review-prototype-design.md
- Copy: docs/superpowers/plans/2026-08-10-cpf-fcv-reviewer-implementation.md

- [ ] **Step 1: Obtain action-time confirmation**

Ask exactly whether to create private GitHub repository ljonestz/cpf-fcv-reviewer now. Do not run any gh mutation before the user confirms.

- [ ] **Step 2: Verify the target is unused**

Run:

~~~powershell
Test-Path -LiteralPath 'C:\Users\wb559324\OneDrive - WBG\Documents\GitHub\cpf-fcv-reviewer'
gh repo view ljonestz/cpf-fcv-reviewer
~~~

Expected: local path is False and gh reports that the repository does not exist. Stop for direction if either target already exists.

- [ ] **Step 3: Create and clone the private repository**

Run:

~~~powershell
Set-Location 'C:\Users\wb559324\OneDrive - WBG\Documents\GitHub'
gh repo create ljonestz/cpf-fcv-reviewer --private --clone
Set-Location 'cpf-fcv-reviewer'
git status --short --branch
~~~

Expected: an empty private repository on branch main.

- [ ] **Step 4: Add the initial scaffold**

Create requirements.txt with:

~~~text
flask==3.1.3
anthropic>=0.40.0,<1.0
httpx>=0.27,<1.0
pydantic>=2.9,<3.0
python-docx==1.1.2
pypdf>=4.0,<7.0
gunicorn>=21.2,<24.0
gevent>=23.9,<26.0
~~~

Create requirements-dev.txt with:

~~~text
-r requirements.txt
pytest>=8.3,<9.0
pytest-cov>=5.0,<7.0
ruff>=0.8,<1.0
~~~

Create Procfile with:

~~~text
web: gunicorn wsgi:app --worker-class gevent --workers 1 --threads 1 --bind 0.0.0.0:$PORT --timeout 1200
~~~

Create wsgi.py with:

~~~python
from cpf_fcv_reviewer.app import create_app

app = create_app()
~~~

Create .gitignore with:

~~~text
.env
*.key
*credentials*
__pycache__/
*.pyc
.venv/
.pytest_cache/
.ruff_cache/
coverage.xml
htmlcov/
instance/
tmp/
*.log
*.docx
*.pdf
*.xlsx
*.csv
.DS_Store
Thumbs.db
desktop.ini
~~~

Create pyproject.toml with:

~~~toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-ra"

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]
~~~

README.md must state that the service is advisory, accepts only approved historical/synthetic/non-sensitive packages on Render, stores review state only in volatile memory, makes no policy determinations, and is separate from the FCV Project Screener.

CLAUDE.md must include these commands:

~~~text
Test: .\.venv\Scripts\python.exe -m pytest -q
Lint: .\.venv\Scripts\python.exe -m ruff check .
Run:  .\.venv\Scripts\python.exe -m flask --app cpf_fcv_reviewer.app run
~~~

It must also prohibit unsupported OPCS claims, direct use of confidential policy files, durable review storage, secrets in Git, and changes to the stable FCV Project Screener.

- [ ] **Step 5: Copy the approved design and plan**

Run from the new repository:

~~~powershell
New-Item -ItemType Directory -Force 'docs\superpowers\specs','docs\superpowers\plans' | Out-Null
Copy-Item -LiteralPath 'C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\docs\superpowers\specs\2026-08-10-cpf-fcv-review-prototype-design.md' -Destination 'docs\superpowers\specs\'
Copy-Item -LiteralPath 'C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\docs\superpowers\plans\2026-08-10-cpf-fcv-reviewer-implementation.md' -Destination 'docs\superpowers\plans\'
~~~

Expected: both files exist under docs/superpowers.

- [ ] **Step 6: Create the virtual environment and verify dependencies**

Run:

~~~powershell
& 'C:\WBG\Python313\python.exe' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -c "import flask, anthropic, pydantic, docx, pypdf; print('DEPENDENCIES_OK')"
~~~

Expected: DEPENDENCIES_OK.

- [ ] **Step 7: Commit and push the scaffold**

Run:

~~~powershell
git status --short
git add -- .gitignore README.md CLAUDE.md pyproject.toml requirements.txt requirements-dev.txt Procfile wsgi.py docs
git diff --staged
git commit -m "chore: scaffold CPF FCV reviewer"
git push -u origin main
git checkout -b feat/mvp-review-run
~~~

Expected: scaffold is on main; implementation begins on feat/mvp-review-run.

### Task 1: Add the Flask application factory and safe configuration

**Files:**
- Create: src/cpf_fcv_reviewer/__init__.py
- Create: src/cpf_fcv_reviewer/app.py
- Create: src/cpf_fcv_reviewer/config.py
- Create: tests/test_app_factory.py

- [ ] **Step 1: Write the failing health and configuration tests**

Create tests/test_app_factory.py:

~~~python
from cpf_fcv_reviewer.app import create_app


def test_health_reports_release_without_secrets():
    app = create_app({"TESTING": True, "APP_RELEASE": "test-release"})
    response = app.test_client().get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "release": "test-release",
        "storage": "volatile",
    }
    assert "ANTHROPIC_API_KEY" not in response.get_data(as_text=True)


def test_production_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    try:
        create_app({"TESTING": False})
    except RuntimeError as exc:
        assert str(exc) == "ANTHROPIC_API_KEY is required outside tests."
    else:
        raise AssertionError("create_app must fail closed without an API key")
~~~

- [ ] **Step 2: Run the tests and verify failure**

Run:

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_app_factory.py -q
~~~

Expected: collection fails because cpf_fcv_reviewer.app does not exist.

- [ ] **Step 3: Implement minimal configuration and health route**

Create src/cpf_fcv_reviewer/config.py:

~~~python
from __future__ import annotations

import os


def build_config(overrides: dict | None = None) -> dict:
    config = {
        "APP_RELEASE": os.getenv("APP_RELEASE", "dev"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
        "MAX_CONTENT_LENGTH": 40 * 1024 * 1024,
        "SESSION_TTL_SECONDS": int(os.getenv("SESSION_TTL_SECONDS", "3600")),
        "START_BACKGROUND_RUNS": True,
        "TESTING": False,
    }
    config.update(overrides or {})
    if not config["TESTING"] and not config["ANTHROPIC_API_KEY"]:
        raise RuntimeError("ANTHROPIC_API_KEY is required outside tests.")
    return config
~~~

Create src/cpf_fcv_reviewer/app.py:

~~~python
from __future__ import annotations

from flask import Flask, jsonify

from .config import build_config


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(build_config(overrides))

    @app.get("/health")
    def health():
        return jsonify(
            status="ok",
            release=app.config["APP_RELEASE"],
            storage="volatile",
        )

    return app
~~~

Create src/cpf_fcv_reviewer/__init__.py:

~~~python
from .app import create_app

__all__ = ["create_app"]
~~~

- [ ] **Step 4: Run tests and lint**

Run:

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_app_factory.py -q
.\.venv\Scripts\python.exe -m ruff check src tests
~~~

Expected: 2 passed; Ruff exits 0.

- [ ] **Step 5: Commit**

~~~powershell
git add -- src tests/test_app_factory.py
git commit -m "feat: add safe Flask application factory"
~~~

### Task 2: Define the evidence and review contracts

**Files:**
- Create: src/cpf_fcv_reviewer/contracts.py
- Create: tests/test_contracts.py

- [ ] **Step 1: Write failing contract tests**

Create tests/test_contracts.py:

~~~python
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cpf_fcv_reviewer.contracts import (
    DiagnosticMode,
    EvidenceItem,
    EvidenceLocator,
    RunMetadata,
    SensitivityCategory,
)


def test_document_evidence_requires_a_real_locator():
    with pytest.raises(ValidationError):
        EvidenceLocator(document_title="CPF", excerpt="A claim")


def test_inference_can_omit_document_coordinates():
    item = EvidenceItem(
        evidence_id="ev-1",
        evidence_type="analytical_inference",
        text="The causal link is implicit.",
        locator=None,
        confidence="medium",
    )
    assert item.locator is None


def test_run_metadata_records_diagnostic_mode_and_versions():
    metadata = RunMetadata(
        run_id="run-1",
        created_at=datetime.now(UTC),
        review_stage="concept_review",
        diagnostic_mode=DiagnosticMode.LIMITED_FRAMING,
        app_release="0.1.0",
        schema_version="1.0.0",
        rubric_version="1.0.0",
        prompt_bundle_version="1.0.0",
        registry_versions={"fcv_strategy": "1.0.0"},
        model_id="test-model",
    )
    assert metadata.diagnostic_mode == DiagnosticMode.LIMITED_FRAMING
    assert SensitivityCategory.CONFIRM.value == "confirm"
~~~

- [ ] **Step 2: Run the tests and verify failure**

Run:

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_contracts.py -q
~~~

Expected: import fails because contracts.py does not exist.

- [ ] **Step 3: Implement the initial Pydantic contracts**

Create src/cpf_fcv_reviewer/contracts.py:

~~~python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DiagnosticMode(StrEnum):
    RRA_ALIGNMENT = "rra_alignment"
    LIMITED_FRAMING = "limited_framing"


class SensitivityCategory(StrEnum):
    DIRECT = "direct"
    CAUTIOUS = "cautious"
    CONFIRM = "confirm"
    WITHHOLD = "withhold"


class EvidenceLocator(FrozenModel):
    document_title: str
    document_version: str | None = None
    page: int | None = Field(default=None, ge=1)
    heading: str | None = None
    element: str | None = None
    excerpt: str
    is_paraphrase: bool = False

    @model_validator(mode="after")
    def require_structural_locator(self):
        if self.page is None and not self.heading and not self.element:
            raise ValueError("Document evidence requires page, heading, or element.")
        return self


class EvidenceItem(FrozenModel):
    evidence_id: str
    evidence_type: Literal[
        "document_fact",
        "current_context",
        "registry_language",
        "user_correction",
        "analytical_inference",
    ]
    text: str
    locator: EvidenceLocator | None = None
    confidence: Literal["high", "medium", "low"]
    source_url: str | None = None


class UserCorrection(FrozenModel):
    correction_id: str
    created_at: datetime
    affected_finding_id: str | None = None
    text: str
    rationale: str | None = None
    independently_supported: bool = False


class DiagnosticEntry(FrozenModel):
    entry_id: str
    short_name: str
    group: Literal[
        "principal_driver",
        "delivery_risk",
        "contextual_condition",
        "resilience_opportunity",
    ]
    materiality: Literal["high", "medium", "low"]
    source_evidence_ids: tuple[str, ...]
    grouping_rationale: str


class Finding(FrozenModel):
    finding_id: str
    title: str
    narrative: str
    status: Literal[
        "aligned",
        "partially_aligned",
        "not_reflected",
        "strong_foundation",
        "needs_strengthening",
        "material_gap",
    ]
    evidence_ids: tuple[str, ...]
    sensitivity: SensitivityCategory


class Recommendation(FrozenModel):
    recommendation_id: str
    finding_id: str
    priority_tier: Literal["core", "additional"]
    action: str
    why_it_matters: str
    target_locator: EvidenceLocator
    stage_behavior: str
    sensitivity: SensitivityCategory


class RunMetadata(FrozenModel):
    run_id: str
    created_at: datetime
    review_stage: str
    diagnostic_mode: DiagnosticMode
    app_release: str
    schema_version: str
    rubric_version: str
    prompt_bundle_version: str
    registry_versions: dict[str, str]
    model_id: str
    parent_run_id: str | None = None
    repair_count: int = Field(default=0, ge=0, le=1)


class EvidencePack(FrozenModel):
    metadata: RunMetadata
    evidence: tuple[EvidenceItem, ...]
    diagnostic_entries: tuple[DiagnosticEntry, ...]
    user_corrections: tuple[UserCorrection, ...] = ()
    warnings: tuple[str, ...] = ()


class ReviewResult(FrozenModel):
    metadata: RunMetadata
    executive_judgment: str
    diagnostic_title: str
    findings: tuple[Finding, ...]
    recommendations: tuple[Recommendation, ...]
    institutional_referral_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
~~~

- [ ] **Step 4: Run tests and lint**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_contracts.py -q
.\.venv\Scripts\python.exe -m ruff check src tests
~~~

Expected: 3 passed; Ruff exits 0.

- [ ] **Step 5: Commit**

~~~powershell
git add -- src/cpf_fcv_reviewer/contracts.py tests/test_contracts.py
git commit -m "feat: define evidence and review contracts"
~~~

### Task 3: Implement volatile assessment state and event queues

**Files:**
- Create: src/cpf_fcv_reviewer/session_store.py
- Create: tests/test_session_store.py

- [ ] **Step 1: Write failing isolation, expiry, and purge tests**

Create tests/test_session_store.py:

~~~python
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
    store.clock = lambda: now + timedelta(seconds=2)

    with pytest.raises(SessionExpired):
        store.get(session_id)
    assert store.count() == 0


def test_events_do_not_cross_sessions():
    store = VolatileSessionStore(ttl_seconds=60)
    first = store.create({})
    second = store.create({})

    store.emit(first, "step_start", {"step": "extract"})
    assert store.next_event(first)["type"] == "step_start"
    assert store.next_event(second) is None
~~~

- [ ] **Step 2: Run tests and verify failure**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_session_store.py -q
~~~

Expected: import fails because session_store.py does not exist.

- [ ] **Step 3: Implement the volatile store**

Create src/cpf_fcv_reviewer/session_store.py:

~~~python
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Callable
from uuid import uuid4


class SessionExpired(KeyError):
    pass


@dataclass
class SessionState:
    session_id: str
    payload: dict
    expires_at: datetime
    events: deque[dict] = field(default_factory=deque)


class VolatileSessionStore:
    def __init__(
        self,
        ttl_seconds: int,
        clock: Callable[[], datetime] | None = None,
    ):
        self.ttl_seconds = ttl_seconds
        self.clock = clock or (lambda: datetime.now(UTC))
        self._items: dict[str, SessionState] = {}
        self._lock = RLock()

    def create(self, payload: dict) -> str:
        with self._lock:
            session_id = uuid4().hex
            self._items[session_id] = SessionState(
                session_id=session_id,
                payload=dict(payload),
                expires_at=self.clock() + timedelta(seconds=self.ttl_seconds),
            )
            return session_id

    def get(self, session_id: str) -> SessionState:
        with self._lock:
            state = self._items.get(session_id)
            if state is None or state.expires_at <= self.clock():
                self._items.pop(session_id, None)
                raise SessionExpired(session_id)
            return state

    def update(self, session_id: str, **values) -> None:
        with self._lock:
            state = self.get(session_id)
            state.payload.update(values)
            state.expires_at = self.clock() + timedelta(seconds=self.ttl_seconds)

    def emit(self, session_id: str, event_type: str, data: dict) -> None:
        with self._lock:
            self.get(session_id).events.append({"type": event_type, "data": data})

    def next_event(self, session_id: str) -> dict | None:
        with self._lock:
            events = self.get(session_id).events
            return events.popleft() if events else None

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._items.pop(session_id, None)

    def count(self) -> int:
        with self._lock:
            for session_id in list(self._items):
                try:
                    self.get(session_id)
                except SessionExpired:
                    pass
            return len(self._items)
~~~

- [ ] **Step 4: Run tests and lint**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_session_store.py -q
.\.venv\Scripts\python.exe -m ruff check src tests
~~~

Expected: 3 passed; Ruff exits 0.

- [ ] **Step 5: Commit**

~~~powershell
git add -- src/cpf_fcv_reviewer/session_store.py tests/test_session_store.py
git commit -m "feat: add volatile assessment state"
~~~
### Task 4: Extract documents with structural traceability

**Files:**
- Create: src/cpf_fcv_reviewer/extraction.py
- Create: tests/test_extraction.py

- [ ] **Step 1: Write failing DOCX and page-segmentation tests**

Create tests/test_extraction.py:

~~~python
from io import BytesIO

from docx import Document

from cpf_fcv_reviewer.extraction import (
    extract_docx_bytes,
    segments_from_pdf_pages,
)


def make_docx() -> bytes:
    document = Document()
    document.add_heading("Strategic context", level=1)
    document.add_paragraph("The CPF identifies localized exclusion.")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Outcome"
    table.cell(0, 1).text = "Indicator"
    table.cell(1, 0).text = "Access"
    table.cell(1, 1).text = "People reached"
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def test_docx_segments_retain_heading_and_table_locator():
    extracted = extract_docx_bytes(make_docx(), "CPF.docx")

    paragraph = next(item for item in extracted.segments if "localized" in item.text)
    table = next(item for item in extracted.segments if "People reached" in item.text)

    assert paragraph.heading == "Strategic context"
    assert paragraph.element == "paragraph 2"
    assert table.heading == "Strategic context"
    assert table.element == "table 1 row 2"


def test_pdf_segments_use_real_page_numbers_only():
    extracted = segments_from_pdf_pages(
        "CPF.pdf",
        ["First page text", "", "Third page text"],
    )

    assert [segment.page for segment in extracted.segments] == [1, 3]
    assert "page 2 extracted no text" in extracted.warnings
~~~

- [ ] **Step 2: Run tests and verify failure**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_extraction.py -q
~~~

Expected: import fails because extraction.py does not exist.

- [ ] **Step 3: Implement focused extractors**

Create src/cpf_fcv_reviewer/extraction.py:

~~~python
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader


@dataclass(frozen=True)
class ExtractedSegment:
    text: str
    page: int | None
    heading: str | None
    element: str


@dataclass(frozen=True)
class ExtractedDocument:
    name: str
    segments: tuple[ExtractedSegment, ...]
    warnings: tuple[str, ...]


def segments_from_pdf_pages(name: str, pages: list[str]) -> ExtractedDocument:
    segments: list[ExtractedSegment] = []
    warnings: list[str] = []
    for index, text in enumerate(pages, start=1):
        clean = (text or "").strip()
        if clean:
            segments.append(
                ExtractedSegment(clean, index, None, f"page {index}")
            )
        else:
            warnings.append(f"page {index} extracted no text")
    return ExtractedDocument(name, tuple(segments), tuple(warnings))


def extract_pdf_bytes(data: bytes, name: str) -> ExtractedDocument:
    reader = PdfReader(BytesIO(data))
    return segments_from_pdf_pages(
        name,
        [(page.extract_text() or "") for page in reader.pages],
    )


def extract_docx_bytes(data: bytes, name: str) -> ExtractedDocument:
    document = Document(BytesIO(data))
    segments: list[ExtractedSegment] = []
    warnings: list[str] = []
    heading: str | None = None
    paragraph_number = 0
    table_number = 0

    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            paragraph = Paragraph(child, document)
            paragraph_number += 1
            text = paragraph.text.strip()
            if not text:
                continue
            if paragraph.style and paragraph.style.name.startswith("Heading"):
                heading = text
            segments.append(
                ExtractedSegment(
                    text=text,
                    page=None,
                    heading=heading,
                    element=f"paragraph {paragraph_number}",
                )
            )
        elif child.tag.endswith("}tbl"):
            table_number += 1
            table = Table(child, document)
            for row_number, row in enumerate(table.rows, start=1):
                values = [cell.text.strip() for cell in row.cells]
                text = " | ".join(value for value in values if value)
                if text:
                    segments.append(
                        ExtractedSegment(
                            text=text,
                            page=None,
                            heading=heading,
                            element=f"table {table_number} row {row_number}",
                        )
                    )

    if document.inline_shapes:
        warnings.append(
            f"{len(document.inline_shapes)} figure(s) detected; "
            "upload a readable text/table version if they contain material evidence"
        )
    return ExtractedDocument(name, tuple(segments), tuple(warnings))


def extract_text_bytes(data: bytes, name: str) -> ExtractedDocument:
    text = data.decode("utf-8-sig").strip()
    segment = ExtractedSegment(text, None, None, "full text")
    return ExtractedDocument(name, (segment,) if text else (), ())


def extract_document(data: bytes, name: str) -> ExtractedDocument:
    suffix = Path(name).suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_bytes(data, name)
    if suffix == ".docx":
        return extract_docx_bytes(data, name)
    if suffix in {".txt", ".md"}:
        return extract_text_bytes(data, name)
    raise ValueError(f"Unsupported file type: {suffix}")
~~~

- [ ] **Step 4: Add explicit unreadable-primary behavior**

Extend tests/test_extraction.py:

~~~python
import pytest

from cpf_fcv_reviewer.extraction import require_readable_primary


def test_empty_primary_is_rejected():
    with pytest.raises(ValueError, match="Primary CPF/CEN is unreadable"):
        require_readable_primary(
            type("Doc", (), {"segments": (), "warnings": ()})()
        )
~~~

Add to extraction.py:

~~~python
def require_readable_primary(document: ExtractedDocument) -> None:
    character_count = sum(len(segment.text) for segment in document.segments)
    if character_count < 100:
        raise ValueError("Primary CPF/CEN is unreadable or contains too little text.")
~~~

- [ ] **Step 5: Run tests and lint**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_extraction.py -q
.\.venv\Scripts\python.exe -m ruff check src tests
~~~

Expected: 3 passed; Ruff exits 0.

- [ ] **Step 6: Commit**

~~~powershell
git add -- src/cpf_fcv_reviewer/extraction.py tests/test_extraction.py
git commit -m "feat: extract documents with source locators"
~~~

### Task 5: Add source adapters and fail-closed registry loading

**Files:**
- Create: src/cpf_fcv_reviewer/sources.py
- Create: src/cpf_fcv_reviewer/registry.py
- Create: registry_bundles/README.md
- Create: tests/fixtures/registry_bundle.synthetic.json
- Create: tests/test_registry.py
- Create: tests/test_source_precedence.py

- [ ] **Step 1: Write failing registry tests**

Create tests/test_registry.py:

~~~python
from pathlib import Path

import pytest

from cpf_fcv_reviewer.registry import (
    RegistryUnavailable,
    hydrate_referrals,
    load_registry_bundle,
)


FIXTURE = Path("tests/fixtures/registry_bundle.synthetic.json")


def test_synthetic_bundle_is_allowed_only_in_tests():
    bundle = load_registry_bundle(FIXTURE, allow_synthetic=True)
    assert bundle.owner == "Synthetic OPCS Test Owner"

    with pytest.raises(RegistryUnavailable, match="Synthetic registry"):
        load_registry_bundle(FIXTURE, allow_synthetic=False)


def test_referral_language_is_hydrated_exactly_from_registry():
    bundle = load_registry_bundle(FIXTURE, allow_synthetic=True)
    hydrated = hydrate_referrals(("SYN-REF-001",), bundle)

    assert hydrated == (
        {
            "entry_id": "SYN-REF-001",
            "approved_text": "Consult the designated policy owner.",
            "version": "1.0.0-test",
        },
    )


def test_unknown_registry_id_fails_closed():
    bundle = load_registry_bundle(FIXTURE, allow_synthetic=True)
    with pytest.raises(RegistryUnavailable, match="Unknown registry entry"):
        hydrate_referrals(("MISSING",), bundle)
~~~

Create tests/fixtures/registry_bundle.synthetic.json:

~~~json
{
  "bundle_id": "synthetic-opcs-test",
  "version": "1.0.0-test",
  "owner": "Synthetic OPCS Test Owner",
  "approved_at": "2026-08-10T00:00:00Z",
  "expires_at": "2099-01-01T00:00:00Z",
  "synthetic": true,
  "entries": [
    {
      "entry_id": "SYN-REF-001",
      "approved_text": "Consult the designated policy owner.",
      "prohibited_terms": ["eligible", "compliant", "triggered"]
    }
  ]
}
~~~

- [ ] **Step 2: Run registry tests and verify failure**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_registry.py -q
~~~

Expected: import fails because registry.py does not exist.

- [ ] **Step 3: Implement registry bundle models and exact hydration**

Create src/cpf_fcv_reviewer/registry.py:

~~~python
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class RegistryUnavailable(RuntimeError):
    pass


class RegistryEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    entry_id: str
    approved_text: str
    prohibited_terms: tuple[str, ...] = ()


class RegistryBundle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    bundle_id: str
    version: str
    owner: str
    approved_at: datetime
    expires_at: datetime
    synthetic: bool
    entries: tuple[RegistryEntry, ...]

    def by_id(self) -> dict[str, RegistryEntry]:
        return {entry.entry_id: entry for entry in self.entries}


def load_registry_bundle(
    path: Path,
    *,
    allow_synthetic: bool,
    now: datetime | None = None,
) -> RegistryBundle:
    if not path.exists():
        raise RegistryUnavailable("Approved registry bundle is unavailable.")
    bundle = RegistryBundle.model_validate_json(path.read_text(encoding="utf-8"))
    if bundle.synthetic and not allow_synthetic:
        raise RegistryUnavailable("Synthetic registry bundles are test-only.")
    if bundle.expires_at <= (now or datetime.now(UTC)):
        raise RegistryUnavailable("Registry bundle has expired.")
    return bundle


def hydrate_referrals(
    entry_ids: tuple[str, ...],
    bundle: RegistryBundle,
) -> tuple[dict, ...]:
    entries = bundle.by_id()
    hydrated: list[dict] = []
    for entry_id in entry_ids:
        if entry_id not in entries:
            raise RegistryUnavailable(f"Unknown registry entry: {entry_id}")
        entry = entries[entry_id]
        hydrated.append(
            {
                "entry_id": entry.entry_id,
                "approved_text": entry.approved_text,
                "version": bundle.version,
            }
        )
    return tuple(hydrated)
~~~

- [ ] **Step 4: Define source adapter contracts and direct-original precedence**

Create tests/test_source_precedence.py:

~~~python
from cpf_fcv_reviewer.sources import SourceCandidate, choose_authoritative_source


def test_direct_sharepoint_original_beats_derived_markdown():
    original = SourceCandidate(
        source_id="sp-1",
        title="Country RRA.docx",
        version="3",
        source_kind="sharepoint_original",
        is_current=True,
    )
    derived = SourceCandidate(
        source_id="md-1",
        title="Country RRA.md",
        version="3",
        source_kind="derived_copy",
        is_current=True,
    )

    assert choose_authoritative_source((derived, original)) == original


def test_ambiguous_current_originals_require_user_fallback():
    first = SourceCandidate("sp-1", "RRA A.docx", "3", "sharepoint_original", True)
    second = SourceCandidate("sp-2", "RRA B.docx", "4", "sharepoint_original", True)

    assert choose_authoritative_source((first, second)) is None
~~~

Create src/cpf_fcv_reviewer/sources.py:

~~~python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class SourceCandidate:
    source_id: str
    title: str
    version: str
    source_kind: Literal[
        "upload",
        "sharepoint_original",
        "approved_summary",
        "derived_copy",
        "public_web",
    ]
    is_current: bool


class RraSourceAdapter(Protocol):
    def candidates(self, country: str) -> tuple[SourceCandidate, ...]: ...


def choose_authoritative_source(
    candidates: tuple[SourceCandidate, ...],
) -> SourceCandidate | None:
    current_originals = [
        item
        for item in candidates
        if item.is_current and item.source_kind == "sharepoint_original"
    ]
    if len(current_originals) == 1:
        return current_originals[0]
    if len(current_originals) > 1:
        return None

    current_uploads = [
        item
        for item in candidates
        if item.is_current and item.source_kind == "upload"
    ]
    return current_uploads[0] if len(current_uploads) == 1 else None
~~~

- [ ] **Step 5: Document the approved-bundle gate**

Create registry_bundles/README.md with these requirements:

~~~markdown
# Approved registry bundles

The running application must fail closed unless it receives an unexpired,
owner-approved, non-confidential registry bundle. Synthetic bundles are permitted
only under TESTING=true and live only in tests/fixtures.

Do not derive policy language from model memory. Do not copy confidential source
documents into this repository. Before a Render deployment, record the approved
bundle owner, immutable version, approval date, expiry date, checksum, and the
policy-sensitive regression result. If the owner-approved bundle is unavailable,
do not create or deploy the Render service.
~~~

- [ ] **Step 6: Run tests and lint**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_registry.py tests\test_source_precedence.py -q
.\.venv\Scripts\python.exe -m ruff check src tests
~~~

Expected: 5 passed; Ruff exits 0.

- [ ] **Step 7: Commit**

~~~powershell
git add -- src/cpf_fcv_reviewer/registry.py src/cpf_fcv_reviewer/sources.py registry_bundles tests
git commit -m "feat: add governed source and registry adapters"
~~~

### Task 6: Implement the public recency and plausibility check

**Files:**
- Create: src/cpf_fcv_reviewer/public_research.py
- Create: prompts/public_research.md
- Create: tests/test_public_research.py

- [ ] **Step 1: Write failing retained-claim tests**

Create tests/test_public_research.py:

~~~python
from datetime import date

from cpf_fcv_reviewer.public_research import (
    CurrentContextClaim,
    retain_public_claims,
)


def test_claim_requires_public_url_date_and_material_relevance():
    claims = (
        CurrentContextClaim(
            claim_id="c1",
            text="Material dated change",
            source_url="https://example.org/report",
            source_date=date(2026, 7, 1),
            source_type="un",
            relevance="Tests whether the CPF framing is current.",
            relationship="qualifies",
            licensed_data_required=False,
        ),
        CurrentContextClaim(
            claim_id="c2",
            text="Licensed event-level result",
            source_url="https://example.org/data",
            source_date=date(2026, 7, 1),
            source_type="dataset",
            relevance="Would require licensed ACLED data.",
            relationship="corroborates",
            licensed_data_required=True,
        ),
    )

    retained, rejected = retain_public_claims(claims)

    assert [claim.claim_id for claim in retained] == ["c1"]
    assert rejected == {"c2": "licensed data is not permitted"}


def test_missing_url_is_rejected():
    claim = CurrentContextClaim(
        claim_id="c3",
        text="Unlinked assertion",
        source_url=None,
        source_date=date(2026, 7, 1),
        source_type="media",
        relevance="Material",
        relationship="unresolved",
        licensed_data_required=False,
    )
    retained, rejected = retain_public_claims((claim,))
    assert retained == ()
    assert rejected["c3"] == "public source URL is required"
~~~

- [ ] **Step 2: Run tests and verify failure**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_public_research.py -q
~~~

Expected: import fails because public_research.py does not exist.

- [ ] **Step 3: Implement claim validation**

Create src/cpf_fcv_reviewer/public_research.py:

~~~python
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CurrentContextClaim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str
    text: str
    source_url: str | None
    source_date: date
    source_type: str
    relevance: str
    relationship: Literal[
        "corroborates",
        "qualifies",
        "contradicts",
        "unresolved",
    ]
    licensed_data_required: bool


def retain_public_claims(
    claims: tuple[CurrentContextClaim, ...],
) -> tuple[tuple[CurrentContextClaim, ...], dict[str, str]]:
    retained: list[CurrentContextClaim] = []
    rejected: dict[str, str] = {}
    for claim in claims:
        if claim.licensed_data_required:
            rejected[claim.claim_id] = "licensed data is not permitted"
        elif not claim.source_url or not claim.source_url.startswith(("http://", "https://")):
            rejected[claim.claim_id] = "public source URL is required"
        elif not claim.relevance.strip():
            rejected[claim.claim_id] = "material relevance is required"
        else:
            retained.append(claim)
    return tuple(retained), rejected
~~~

- [ ] **Step 4: Add the bounded research prompt**

Create prompts/public_research.md:

~~~markdown
You are performing a public-source recency and plausibility check for a CPF/CEN
FCV review. This is not a country diagnostic.

Retain only claims that test whether an uploaded diagnostic or CPF framing is
outdated, contradicted, incomplete, or still plausible. Every claim must provide
a public URL, publication date, source type, relevance to a named review
question, and one relationship: corroborates, qualifies, contradicts, unresolved.

Use public sources only. Do not request, infer access to, or reproduce licensed
ACLED event-level data or any other licensed dataset. Public ACLED analysis may
be treated like another public publication. Distinguish fact from interpretation,
frame politically sensitive claims cautiously, and preserve credible disagreement.
Return a JSON array matching CurrentContextClaim.
~~~

- [ ] **Step 5: Add the Anthropic research adapter behind a protocol**

Extend public_research.py:

~~~python
from pathlib import Path
from typing import Protocol

import anthropic


class PublicResearchGateway(Protocol):
    def search(self, prompt: str) -> str: ...


class AnthropicPublicResearchGateway:
    def __init__(self, api_key: str, model_id: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_id = model_id

    def search(self, prompt: str) -> str:
        response = self.client.beta.messages.create(
            model=self.model_id,
            max_tokens=5000,
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 5,
                }
            ],
            messages=[{"role": "user", "content": prompt}],
            betas=["web-search-2025-03-05"],
        )
        return "\n".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ).strip()


def load_research_prompt() -> str:
    path = Path(__file__).parents[2] / "prompts" / "public_research.md"
    return path.read_text(encoding="utf-8")
~~~

The structured model parser added in Task 8 converts the returned text to CurrentContextClaim objects. Tests use fakes and never call the network.

- [ ] **Step 6: Run tests and lint**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_public_research.py -q
.\.venv\Scripts\python.exe -m ruff check src tests
~~~

Expected: 2 passed; Ruff exits 0.

- [ ] **Step 7: Commit**

~~~powershell
git add -- src/cpf_fcv_reviewer/public_research.py prompts/public_research.md tests/test_public_research.py
git commit -m "feat: add public recency plausibility checks"
~~~

### Task 7: Build the Evidence Pack and grouped diagnostic map

**Files:**
- Create: src/cpf_fcv_reviewer/evidence_builder.py
- Create: src/cpf_fcv_reviewer/diagnostic_map.py
- Create: tests/test_evidence_builder.py
- Create: tests/test_diagnostic_map.py

- [ ] **Step 1: Write failing diagnostic-mode tests**

Create tests/test_evidence_builder.py:

~~~python
from cpf_fcv_reviewer.contracts import DiagnosticMode
from cpf_fcv_reviewer.evidence_builder import DocumentRole, select_diagnostic_mode


def test_current_rra_enables_alignment_mode():
    documents = (
        DocumentRole("cpf", "CPF.docx", True, False),
        DocumentRole("rra", "RRA.docx", True, True),
    )
    assert select_diagnostic_mode(documents) == DiagnosticMode.RRA_ALIGNMENT


def test_missing_or_unapproved_diagnostic_forces_limited_mode():
    only_cpf = (DocumentRole("cpf", "CPF.docx", True, False),)
    unapproved = (
        DocumentRole("cpf", "CPF.docx", True, False),
        DocumentRole("diagnostic", "Context.docx", True, False),
    )
    assert select_diagnostic_mode(only_cpf) == DiagnosticMode.LIMITED_FRAMING
    assert select_diagnostic_mode(unapproved) == DiagnosticMode.LIMITED_FRAMING
~~~

- [ ] **Step 2: Write failing diagnostic completeness tests**

Create tests/test_diagnostic_map.py:

~~~python
import pytest

from cpf_fcv_reviewer.contracts import DiagnosticEntry
from cpf_fcv_reviewer.diagnostic_map import validate_diagnostic_coverage


def test_every_material_source_item_is_mapped_once():
    entries = (
        DiagnosticEntry(
            entry_id="d1",
            short_name="Exclusion",
            group="principal_driver",
            materiality="high",
            source_evidence_ids=("ev-1",),
            grouping_rationale="Shapes objectives.",
        ),
        DiagnosticEntry(
            entry_id="d2",
            short_name="Access constraints",
            group="delivery_risk",
            materiality="medium",
            source_evidence_ids=("ev-2",),
            grouping_rationale="Shapes implementation.",
        ),
    )
    validate_diagnostic_coverage(("ev-1", "ev-2"), entries)


def test_dropped_material_item_fails():
    entry = DiagnosticEntry(
        entry_id="d1",
        short_name="Exclusion",
        group="principal_driver",
        materiality="high",
        source_evidence_ids=("ev-1",),
        grouping_rationale="Shapes objectives.",
    )
    with pytest.raises(ValueError, match="Unmapped diagnostic evidence: ev-2"):
        validate_diagnostic_coverage(("ev-1", "ev-2"), (entry,))
~~~

- [ ] **Step 3: Run tests and verify failure**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_evidence_builder.py tests\test_diagnostic_map.py -q
~~~

Expected: imports fail because evidence_builder.py and diagnostic_map.py do not exist.

- [ ] **Step 4: Implement diagnostic-mode selection**

Create src/cpf_fcv_reviewer/evidence_builder.py:

~~~python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .contracts import DiagnosticMode


@dataclass(frozen=True)
class DocumentRole:
    role: Literal["cpf", "rra", "diagnostic", "results", "comments", "other"]
    name: str
    readable: bool
    accepted_equivalent: bool


def select_diagnostic_mode(
    documents: tuple[DocumentRole, ...],
) -> DiagnosticMode:
    for document in documents:
        if not document.readable:
            continue
        if document.role == "rra":
            return DiagnosticMode.RRA_ALIGNMENT
        if document.role == "diagnostic" and document.accepted_equivalent:
            return DiagnosticMode.RRA_ALIGNMENT
    return DiagnosticMode.LIMITED_FRAMING
~~~

- [ ] **Step 5: Implement deterministic coverage validation**

Create src/cpf_fcv_reviewer/diagnostic_map.py:

~~~python
from __future__ import annotations

from collections import Counter

from .contracts import DiagnosticEntry


def validate_diagnostic_coverage(
    material_evidence_ids: tuple[str, ...],
    entries: tuple[DiagnosticEntry, ...],
) -> None:
    mapped = Counter(
        evidence_id
        for entry in entries
        for evidence_id in entry.source_evidence_ids
    )
    missing = [item for item in material_evidence_ids if mapped[item] == 0]
    duplicated = [item for item in material_evidence_ids if mapped[item] > 1]
    if missing:
        raise ValueError(f"Unmapped diagnostic evidence: {', '.join(missing)}")
    if duplicated:
        raise ValueError(
            f"Diagnostic evidence mapped more than once: {', '.join(duplicated)}"
        )


def priority_key(entry: DiagnosticEntry) -> tuple[int, int, str]:
    group_rank = {
        "principal_driver": 0,
        "resilience_opportunity": 1,
        "delivery_risk": 2,
        "contextual_condition": 3,
    }
    materiality_rank = {"high": 0, "medium": 1, "low": 2}
    return (
        group_rank[entry.group],
        materiality_rank[entry.materiality],
        entry.short_name.casefold(),
    )


def prioritize(entries: tuple[DiagnosticEntry, ...]) -> tuple[DiagnosticEntry, ...]:
    return tuple(sorted(entries, key=priority_key))
~~~

- [ ] **Step 6: Add the Evidence Pack assembly function**

Extend evidence_builder.py:

~~~python
from .contracts import DiagnosticEntry, EvidenceItem, EvidencePack, RunMetadata, UserCorrection
from .diagnostic_map import prioritize, validate_diagnostic_coverage


def build_evidence_pack(
    *,
    metadata: RunMetadata,
    evidence: tuple[EvidenceItem, ...],
    diagnostic_entries: tuple[DiagnosticEntry, ...],
    material_diagnostic_ids: tuple[str, ...],
    corrections: tuple[UserCorrection, ...] = (),
    warnings: tuple[str, ...] = (),
) -> EvidencePack:
    if metadata.diagnostic_mode == DiagnosticMode.RRA_ALIGNMENT:
        validate_diagnostic_coverage(material_diagnostic_ids, diagnostic_entries)
    return EvidencePack(
        metadata=metadata,
        evidence=evidence,
        diagnostic_entries=prioritize(diagnostic_entries),
        user_corrections=corrections,
        warnings=warnings,
    )
~~~

- [ ] **Step 7: Run tests and lint**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_evidence_builder.py tests\test_diagnostic_map.py -q
.\.venv\Scripts\python.exe -m ruff check src tests
~~~

Expected: 4 passed; Ruff exits 0.

- [ ] **Step 8: Commit**

~~~powershell
git add -- src/cpf_fcv_reviewer/evidence_builder.py src/cpf_fcv_reviewer/diagnostic_map.py tests
git commit -m "feat: build grouped diagnostic evidence packs"
~~~

### Task 8: Add versioned prompts, model gateway, and structured review engine

**Files:**
- Create: src/cpf_fcv_reviewer/model_gateway.py
- Create: src/cpf_fcv_reviewer/prompts.py
- Create: src/cpf_fcv_reviewer/review_engine.py
- Modify: src/cpf_fcv_reviewer/contracts.py
- Create: prompts/diagnostic_map.md
- Create: prompts/review.md
- Create: prompts/repair.md
- Create: tests/test_review_engine.py
- Create: tests/test_prompt_guardrails.py

- [ ] **Step 1: Extend the contract for priority-question responses**

Add to contracts.py before ReviewResult:

~~~python
class PriorityQuestionResponse(FrozenModel):
    question_id: str
    question: str
    direct_answer: str
    evidence_ids: tuple[str, ...]
    confidence: Literal["high", "medium", "low"]
    limitation: str | None = None
~~~

Add this field to ReviewResult:

~~~python
priority_question_responses: tuple[PriorityQuestionResponse, ...] = ()
~~~

- [ ] **Step 2: Write failing review-engine tests**

Create tests/test_review_engine.py:

~~~python
from datetime import UTC, datetime

from cpf_fcv_reviewer.contracts import (
    DiagnosticMode,
    EvidencePack,
    ReviewResult,
    RunMetadata,
)
from cpf_fcv_reviewer.review_engine import ReviewEngine


class FakeGateway:
    def __init__(self, result: ReviewResult):
        self.result = result
        self.calls = []

    def generate(self, *, prompt_name, payload, output_type):
        self.calls.append((prompt_name, payload, output_type))
        return self.result


def metadata(mode):
    return RunMetadata(
        run_id="run-1",
        created_at=datetime.now(UTC),
        review_stage="finalization",
        diagnostic_mode=mode,
        app_release="0.1.0",
        schema_version="1.0.0",
        rubric_version="1.0.0",
        prompt_bundle_version="1.0.0",
        registry_versions={"fcv_strategy": "1.0.0"},
        model_id="fake",
    )


def test_limited_mode_has_non_alignment_title():
    meta = metadata(DiagnosticMode.LIMITED_FRAMING)
    expected = ReviewResult(
        metadata=meta,
        executive_judgment="Evidence is limited.",
        diagnostic_title="Limited FCV diagnostic-framing assessment",
        findings=(),
        recommendations=(),
        limitations=("No RRA or accepted equivalent was available.",),
    )
    gateway = FakeGateway(expected)

    result = ReviewEngine(gateway).review(
        EvidencePack(metadata=meta, evidence=(), diagnostic_entries=())
    )

    assert result.diagnostic_title == "Limited FCV diagnostic-framing assessment"
    assert gateway.calls[0][0] == "review"


def test_finalization_stage_rule_is_injected():
    meta = metadata(DiagnosticMode.LIMITED_FRAMING)
    expected = ReviewResult(
        metadata=meta,
        executive_judgment="Targeted edits only.",
        diagnostic_title="Limited FCV diagnostic-framing assessment",
        findings=(),
        recommendations=(),
    )
    gateway = FakeGateway(expected)

    ReviewEngine(gateway).review(
        EvidencePack(metadata=meta, evidence=(), diagnostic_entries=())
    )

    payload = gateway.calls[0][1]
    assert "targeted, high-value edits" in payload["stage_rule"]
~~~

- [ ] **Step 3: Create the prompt guardrail tests**

Create tests/test_prompt_guardrails.py:

~~~python
from cpf_fcv_reviewer.prompts import load_prompt


def test_review_prompt_prohibits_determinations_and_policy_paraphrase():
    prompt = load_prompt("review")
    for phrase in (
        "must not determine",
        "approved registry entry identifiers",
        "Limited FCV diagnostic-framing assessment",
        "page, heading, table, figure, or paragraph",
        "English",
    ):
        assert phrase in prompt
~~~

- [ ] **Step 4: Run tests and verify failure**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_review_engine.py tests\test_prompt_guardrails.py -q
~~~

Expected: imports fail because model_gateway.py, prompts.py, and review_engine.py do not exist.

- [ ] **Step 5: Create the versioned prompts**

Create prompts/diagnostic_map.md:

~~~markdown
Version: 1.0.0

Map the accepted RRA/equivalent into four groups: principal FCV drivers and
trajectory-shifting priorities; delivery and implementation risks; contextual
conditions; sources of resilience and opportunities. Preserve every supplied
material evidence identifier exactly once. Assign materiality and explain the
grouping. Do not convert contextual background into a programming requirement.
Return only DiagnosticEntry JSON.
~~~

Create prompts/review.md:

~~~markdown
Version: 1.0.0

Produce an advisory CPF/CEN FCV ReviewResult from the supplied Evidence Pack.

You must not determine policy applicability, compliance, clearance, eligibility,
official classification, PC14/IDA21 FCV Policy Commitment status, FCV Envelope
status or readiness, PRA/RECA/TAA status, or OP 7.30 applicability. Do not
paraphrase policy or guidance. Refer only to approved registry entry identifiers;
the application hydrates approved language after validation.

If diagnostic_mode is limited_framing, title Core Review 1 exactly
"Limited FCV diagnostic-framing assessment". Do not claim or rate RRA alignment.

Every material finding and recommendation must cite evidence identifiers that
resolve to a page, heading, table, figure, or paragraph locator. Never invent a
page. Label analytical inference and user correction. Apply the supplied stage
rule and sensitivity categories. English is the default output. Preserve original
French excerpts and mark analytical translation or paraphrase.

Return only JSON matching ReviewResult.
~~~

Create prompts/repair.md:

~~~markdown
Version: 1.0.0

Repair only the validation issues supplied with the draft ReviewResult. Preserve
all valid content and identifiers. Do not add evidence, policy language, policy
determinations, citations, page numbers, or registry entries. Return one complete
ReviewResult JSON. This is the only repair attempt.
~~~

- [ ] **Step 6: Implement prompt loading and hashing**

Create src/cpf_fcv_reviewer/prompts.py:

~~~python
from __future__ import annotations

from hashlib import sha256
from pathlib import Path


PROMPT_ROOT = Path(__file__).parents[2] / "prompts"


def load_prompt(name: str) -> str:
    return (PROMPT_ROOT / f"{name}.md").read_text(encoding="utf-8")


def prompt_hash(name: str) -> str:
    return sha256(load_prompt(name).encode("utf-8")).hexdigest()
~~~

- [ ] **Step 7: Implement the model protocol and Anthropic JSON adapter**

Create src/cpf_fcv_reviewer/model_gateway.py:

~~~python
from __future__ import annotations

import json
from typing import Protocol, TypeVar

import anthropic
from pydantic import BaseModel

from .prompts import load_prompt


OutputModel = TypeVar("OutputModel", bound=BaseModel)


class ModelGateway(Protocol):
    def generate(
        self,
        *,
        prompt_name: str,
        payload: dict,
        output_type: type[OutputModel],
    ) -> OutputModel: ...


class AnthropicModelGateway:
    def __init__(self, api_key: str, model_id: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_id = model_id

    def generate(
        self,
        *,
        prompt_name: str,
        payload: dict,
        output_type: type[OutputModel],
    ) -> OutputModel:
        response = self.client.messages.create(
            model=self.model_id,
            max_tokens=12000,
            system=load_prompt(prompt_name),
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                }
            ],
        )
        text = "\n".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ).strip()
        return output_type.model_validate_json(text)
~~~

- [ ] **Step 8: Implement stage rules and the review engine**

Create src/cpf_fcv_reviewer/review_engine.py:

~~~python
from __future__ import annotations

from .contracts import EvidencePack, ReviewResult
from .model_gateway import ModelGateway


STAGE_RULES = {
    "early_drafting": (
        "May challenge strategic framing, selectivity, causal logic, "
        "outcome structure, and theory of change."
    ),
    "concept_review": (
        "Prioritize diagnostic alignment, strategic choices, outcome "
        "architecture, One WBG roles, partnerships, and results logic."
    ),
    "decision_review": (
        "Focus on specific revisions to objectives, results, risks, "
        "implementation arrangements, calibration, and decisions."
    ),
    "roc_oc": (
        "Focus on specific revisions to objectives, results, risks, "
        "implementation arrangements, calibration, and decisions."
    ),
    "finalization": (
        "Limit advice to targeted, high-value edits, factual corrections, "
        "caveats, indicator refinements, and genuine confirmation needs."
    ),
    "response_to_comments": (
        "Link each option to the prior comment and document location; use "
        "accept, partially accept, explain, or verify options."
    ),
}


class ReviewEngine:
    def __init__(self, gateway: ModelGateway):
        self.gateway = gateway

    def review(self, evidence_pack: EvidencePack) -> ReviewResult:
        stage = evidence_pack.metadata.review_stage
        return self.gateway.generate(
            prompt_name="review",
            payload={
                "evidence_pack": evidence_pack.model_dump(mode="json"),
                "stage_rule": STAGE_RULES[stage],
            },
            output_type=ReviewResult,
        )
~~~

- [ ] **Step 9: Run tests and lint**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_review_engine.py tests\test_prompt_guardrails.py -q
.\.venv\Scripts\python.exe -m ruff check src tests
~~~

Expected: 3 passed; Ruff exits 0.

- [ ] **Step 10: Commit**

~~~powershell
git add -- src prompts tests
git commit -m "feat: add structured advisory review engine"
~~~

### Task 9: Enforce traceability, policy, mode, stage, and sensitivity rules

**Files:**
- Create: src/cpf_fcv_reviewer/validators.py
- Create: tests/test_validators.py
- Create: tests/test_policy_adversarial.py

- [ ] **Step 1: Write failing traceability and policy tests**

Create tests/test_validators.py:

~~~python
from datetime import UTC, datetime

from cpf_fcv_reviewer.contracts import (
    DiagnosticMode,
    Finding,
    ReviewResult,
    RunMetadata,
    SensitivityCategory,
)
from cpf_fcv_reviewer.validators import validate_review


def metadata():
    return RunMetadata(
        run_id="run-1",
        created_at=datetime.now(UTC),
        review_stage="finalization",
        diagnostic_mode=DiagnosticMode.LIMITED_FRAMING,
        app_release="0.1.0",
        schema_version="1.0.0",
        rubric_version="1.0.0",
        prompt_bundle_version="1.0.0",
        registry_versions={"opcs": "1.0.0-test"},
        model_id="fake",
    )


def test_unknown_evidence_and_alignment_claim_fail():
    result = ReviewResult(
        metadata=metadata(),
        executive_judgment="The CPF is aligned with the RRA.",
        diagnostic_title="RRA-CPF alignment",
        findings=(
            Finding(
                finding_id="f1",
                title="Unsupported",
                narrative="A named policy is triggered.",
                status="material_gap",
                evidence_ids=("missing",),
                sensitivity=SensitivityCategory.DIRECT,
            ),
        ),
        recommendations=(),
    )
    issues = validate_review(result, evidence_ids=set(), prohibited_terms={"triggered"})

    assert {issue.code for issue in issues} == {
        "limited_mode_overclaim",
        "unknown_evidence",
        "prohibited_policy_language",
    }
~~~

Create tests/test_policy_adversarial.py:

~~~python
import pytest

from cpf_fcv_reviewer.validators import assert_no_unsupported_policy_claims


@pytest.mark.parametrize(
    "text",
    [
        "The package is eligible for the PRA.",
        "OP 7.30 is triggered.",
        "The CPF complies with PC14.",
        "The FCV Envelope criteria are met.",
        "OPCS has cleared this approach.",
    ],
)
def test_determination_language_is_blocked(text):
    with pytest.raises(ValueError, match="Unsupported policy or determination"):
        assert_no_unsupported_policy_claims(text, set())
~~~

- [ ] **Step 2: Run tests and verify failure**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_validators.py tests\test_policy_adversarial.py -q
~~~

Expected: import fails because validators.py does not exist.

- [ ] **Step 3: Implement validators**

Create src/cpf_fcv_reviewer/validators.py:

~~~python
from __future__ import annotations

from dataclasses import dataclass
import re

from .contracts import DiagnosticMode, ReviewResult


DETERMINATION_PATTERNS = (
    r"\beligible for\b",
    r"\bis triggered\b",
    r"\bcomplies? with\b",
    r"\bcriteria are met\b",
    r"\bhas cleared\b",
    r"\bconstitutes clearance\b",
)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


def result_text(result: ReviewResult) -> str:
    parts = [result.executive_judgment, result.diagnostic_title]
    parts.extend(finding.narrative for finding in result.findings)
    parts.extend(item.action for item in result.recommendations)
    return "\n".join(parts)


def assert_no_unsupported_policy_claims(
    text: str,
    prohibited_terms: set[str],
) -> None:
    lowered = text.casefold()
    if any(re.search(pattern, lowered) for pattern in DETERMINATION_PATTERNS):
        raise ValueError("Unsupported policy or determination language.")
    if any(term.casefold() in lowered for term in prohibited_terms):
        raise ValueError("Unsupported policy or determination language.")


def validate_review(
    result: ReviewResult,
    *,
    evidence_ids: set[str],
    prohibited_terms: set[str],
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    text = result_text(result)

    if result.metadata.diagnostic_mode == DiagnosticMode.LIMITED_FRAMING:
        if "rra" in result.diagnostic_title.casefold() and "alignment" in text.casefold():
            issues.append(
                ValidationIssue(
                    "limited_mode_overclaim",
                    "Limited mode must not claim RRA alignment.",
                )
            )

    for finding in result.findings:
        unknown = set(finding.evidence_ids) - evidence_ids
        if unknown:
            issues.append(
                ValidationIssue(
                    "unknown_evidence",
                    f"{finding.finding_id} cites unknown evidence: {sorted(unknown)}",
                )
            )

    try:
        assert_no_unsupported_policy_claims(text, prohibited_terms)
    except ValueError as exc:
        issues.append(ValidationIssue("prohibited_policy_language", str(exc)))

    for recommendation in result.recommendations:
        if recommendation.sensitivity.value == "withhold":
            issues.append(
                ValidationIssue(
                    "withheld_drafting",
                    f"{recommendation.recommendation_id} cannot be ready-to-paste.",
                )
            )
    return tuple(issues)
~~~

- [ ] **Step 4: Add stage-specific recommendation assertions**

Extend tests/test_validators.py:

~~~python
from cpf_fcv_reviewer.validators import validate_stage_behavior


def test_finalization_rejects_wholesale_redesign():
    issues = validate_stage_behavior(
        "finalization",
        "Replace all CPF outcome areas and rebuild the entire theory of change.",
    )
    assert issues[0].code == "stage_overreach"
~~~

Add to validators.py:

~~~python
def validate_stage_behavior(
    review_stage: str,
    action: str,
) -> tuple[ValidationIssue, ...]:
    if review_stage == "finalization":
        overreach = ("replace all", "rebuild the entire", "redesign the whole")
        if any(term in action.casefold() for term in overreach):
            return (
                ValidationIssue(
                    "stage_overreach",
                    "Finalization permits targeted edits, not wholesale redesign.",
                ),
            )
    return ()
~~~

- [ ] **Step 5: Run tests and lint**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_validators.py tests\test_policy_adversarial.py -q
.\.venv\Scripts\python.exe -m ruff check src tests
~~~

Expected: all tests pass; Ruff exits 0.

- [ ] **Step 6: Commit**

~~~powershell
git add -- src/cpf_fcv_reviewer/validators.py tests
git commit -m "feat: enforce review safety validators"
~~~

### Task 10: Orchestrate one visible run with truthful SSE progress and one repair

**Files:**
- Create: src/cpf_fcv_reviewer/orchestrator.py
- Create: src/cpf_fcv_reviewer/routes.py
- Create: src/cpf_fcv_reviewer/runtime.py
- Modify: src/cpf_fcv_reviewer/app.py
- Create: tests/test_orchestrator.py
- Create: tests/test_routes.py
- Create: tests/test_runtime_wiring.py

- [ ] **Step 1: Write failing orchestration-order and repair-limit tests**

Create tests/test_orchestrator.py:

~~~python
from cpf_fcv_reviewer.orchestrator import ReviewOrchestrator


class FakeStep:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __call__(self, context):
        context[self.name] = self.value
        return context


def test_one_run_reports_real_internal_step_order():
    events = []
    orchestrator = ReviewOrchestrator(
        steps=(
            ("extract", FakeStep("extract", True)),
            ("resolve_sources", FakeStep("sources", True)),
            ("build_evidence", FakeStep("evidence", True)),
            ("map", FakeStep("map", True)),
            ("review", FakeStep("review", True)),
            ("validate", FakeStep("validated", True)),
            ("render", FakeStep("rendered", True)),
        ),
        repair=lambda context, issues: context,
    )

    orchestrator.run({}, lambda kind, data: events.append((kind, data)))

    assert [
        data["step"]
        for kind, data in events
        if kind == "step_start"
    ] == [
        "extract",
        "resolve_sources",
        "build_evidence",
        "map",
        "review",
        "validate",
        "render",
    ]
    assert events[-1][0] == "run_complete"


def test_repair_runs_at_most_once():
    attempts = []

    def validate(context):
        if context.get("repaired"):
            return context
        context["validation_issues"] = ["bad"]
        return context

    def repair(context, issues):
        attempts.append(tuple(issues))
        context["repaired"] = True
        context["validation_issues"] = []
        return context

    orchestrator = ReviewOrchestrator(
        steps=(("validate", validate),),
        repair=repair,
    )
    orchestrator.run({}, lambda *_: None)

    assert attempts == [("bad",)]
~~~

- [ ] **Step 2: Run tests and verify failure**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_orchestrator.py -q
~~~

Expected: import fails because orchestrator.py does not exist.

- [ ] **Step 3: Implement the orchestrator**

Create src/cpf_fcv_reviewer/orchestrator.py:

~~~python
from __future__ import annotations

from collections.abc import Callable


Emitter = Callable[[str, dict], None]
Step = Callable[[dict], dict]
Repair = Callable[[dict, list], dict]


class ReviewOrchestrator:
    def __init__(
        self,
        *,
        steps: tuple[tuple[str, Step], ...],
        repair: Repair,
    ):
        self.steps = steps
        self.repair = repair

    def run(self, context: dict, emit: Emitter) -> dict:
        repaired = False
        try:
            for name, step in self.steps:
                emit("step_start", {"step": name})
                context = step(context)
                if name == "validate" and context.get("validation_issues"):
                    if repaired:
                        raise ValueError("Validation failed after the only repair.")
                    emit("repair_start", {"issues": context["validation_issues"]})
                    context = self.repair(
                        context,
                        context["validation_issues"],
                    )
                    repaired = True
                    if context.get("validation_issues"):
                        raise ValueError("Validation failed after the only repair.")
                emit("step_complete", {"step": name})
            emit("run_complete", {"repair_count": int(repaired)})
            return context
        except Exception as exc:
            emit(
                "run_failed",
                {"error_type": type(exc).__name__, "message": str(exc)},
            )
            raise
~~~

- [ ] **Step 4: Write the route contract tests**

Create tests/test_routes.py:

~~~python
from io import BytesIO

from cpf_fcv_reviewer.app import create_app


def create_review(client):
    response = client.post(
        "/api/reviews",
        data={
            "country": "Testland",
            "review_stage": "concept_review",
            "cpf": (BytesIO(b"Readable CPF text " * 20), "cpf.txt"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    return response.get_json()


def test_create_review_returns_assessment_and_event_urls():
    app = create_app({"TESTING": True, "START_BACKGROUND_RUNS": False})
    payload = create_review(app.test_client())

    assert payload["assessment_id"]
    assert payload["event_url"].endswith("/events")
    assert payload["result_url"].endswith("/result")


def test_reset_removes_active_review():
    app = create_app({"TESTING": True, "START_BACKGROUND_RUNS": False})
    client = app.test_client()
    created = create_review(client)

    assert client.delete(f"/api/reviews/{created['assessment_id']}").status_code == 204
    assert client.get(created["result_url"]).status_code == 410
~~~

- [ ] **Step 5: Implement intake, event, result, correction, and reset routes**

Create src/cpf_fcv_reviewer/routes.py:

~~~python
from __future__ import annotations

import json
from time import sleep

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

from .session_store import SessionExpired


bp = Blueprint("reviews", __name__)


def store():
    return current_app.extensions["session_store"]


@bp.post("/api/reviews")
def create_review():
    cpf = request.files.get("cpf")
    if cpf is None:
        return jsonify(error="A primary CPF/CEN is required."), 400
    payload = {
        "country": request.form.get("country", "").strip(),
        "review_stage": request.form.get("review_stage", "").strip(),
        "cpf": {"name": cpf.filename, "bytes": cpf.read()},
        "supporting": [
            {"name": item.filename, "bytes": item.read()}
            for item in request.files.getlist("supporting")
        ],
        "guidance": request.form.get("guidance", "").strip(),
        "corrections": [],
        "status": "created",
    }
    assessment_id = store().create(payload)
    base = f"/api/reviews/{assessment_id}"
    return (
        jsonify(
            assessment_id=assessment_id,
            event_url=f"{base}/events",
            result_url=f"{base}/result",
        ),
        201,
    )


@bp.get("/api/reviews/<assessment_id>/events")
def review_events(assessment_id):
    def generate():
        while True:
            try:
                event = store().next_event(assessment_id)
            except SessionExpired:
                yield "event: expired\ndata: {}\n\n"
                return
            if event:
                yield (
                    f"event: {event['type']}\n"
                    f"data: {json.dumps(event['data'])}\n\n"
                )
                if event["type"] in {"run_complete", "run_failed"}:
                    return
            else:
                yield "event: keepalive\ndata: {}\n\n"
                sleep(15)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@bp.get("/api/reviews/<assessment_id>/result")
def review_result(assessment_id):
    try:
        state = store().get(assessment_id)
    except SessionExpired:
        return jsonify(error="Assessment expired."), 410
    result = state.payload.get("result")
    if result is None:
        return jsonify(status=state.payload.get("status", "created")), 202
    return jsonify(result)


@bp.post("/api/reviews/<assessment_id>/corrections")
def add_correction(assessment_id):
    body = request.get_json(force=True)
    correction = {
        "label": "User-provided correction",
        "text": body["text"].strip(),
        "affected_finding_id": body.get("affected_finding_id"),
        "rationale": body.get("rationale"),
    }
    state = store().get(assessment_id)
    state.payload["corrections"].append(correction)
    state.payload["status"] = "rerun_requested"
    return jsonify(correction), 201


@bp.delete("/api/reviews/<assessment_id>")
def reset_review(assessment_id):
    store().delete(assessment_id)
    return "", 204
~~~

Modify app.py:

~~~python
from .routes import bp as review_blueprint
from .session_store import VolatileSessionStore

# Add inside create_app before return:
app.extensions["session_store"] = VolatileSessionStore(
    ttl_seconds=app.config["SESSION_TTL_SECONDS"]
)
app.register_blueprint(review_blueprint)
~~~

- [ ] **Step 6: Wire the background run without copying state**

Add to routes.py:

~~~python
from threading import Thread


def run_assessment(app, assessment_id):
    with app.app_context():
        state = store().get(assessment_id)
        orchestrator = current_app.extensions["review_orchestrator"]
        result_context = orchestrator.run(
            {"assessment_id": assessment_id, "payload": state.payload},
            lambda kind, data: store().emit(assessment_id, kind, data),
        )
        store().update(
            assessment_id,
            result=result_context["result"].model_dump(mode="json"),
            status="complete",
        )
~~~

In create_review, after assessment_id is created:

~~~python
if current_app.config["START_BACKGROUND_RUNS"]:
    app = current_app._get_current_object()
    Thread(
        target=run_assessment,
        args=(app, assessment_id),
        daemon=True,
    ).start()
~~~

The thread receives only the assessment identifier and reloads volatile state. It must not log filenames, document bytes, guidance, corrections, excerpts, or generated findings.

- [ ] **Step 6A: Wire runtime services through explicit dependency injection**

Create tests/test_runtime_wiring.py. Pass services={"review_orchestrator": fake_orchestrator, "registry_bundle": synthetic_bundle} to create_app, assert both appear in app.extensions, and assert production startup fails closed when the configured registry path, approval status, or expected hash is invalid.

Modify create_app to accept services without changing the Task 1 health contract:

~~~python
def create_app(
    overrides: dict | None = None,
    services: dict | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config.update(build_config(overrides))
    if services is None:
        services = {} if app.testing else build_runtime_services(app.config)
    app.extensions.update(services)
    # health route, volatile store, and blueprint registration follow
    return app
~~~

Create runtime.py with build_runtime_services(config). It must load and hash-verify the approved registry bundle before constructing AnthropicModelGateway, AnthropicPublicResearchGateway, ReviewEngine, and ReviewOrchestrator. Build the orchestrator with exactly these named steps: extract, resolve_sources, research, build_evidence, map, review, validate, render. The resolve_sources step uses an available SharePoint original when configured and otherwise the upload fallback; it never uses a Markdown derivative when a direct original exists. Return only review_orchestrator and registry_bundle in the extension dictionary. Production startup must fail before serving traffic if the registry is unavailable or invalid.

- [ ] **Step 7: Run tests and lint**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_orchestrator.py tests\test_routes.py -q
.\.venv\Scripts\python.exe -m ruff check src tests
~~~

Expected: 4 passed; Ruff exits 0.

- [ ] **Step 8: Commit**

~~~powershell
git add -- src tests
git commit -m "feat: orchestrate one visible review run"
~~~

### Task 11: Build the country-team interface without durable browser storage

**Files:**
- Create: src/cpf_fcv_reviewer/templates/index.html
- Create: src/cpf_fcv_reviewer/static/app.js
- Create: src/cpf_fcv_reviewer/static/styles.css
- Modify: src/cpf_fcv_reviewer/app.py
- Create: tests/test_frontend_contract.py

- [ ] **Step 1: Write failing frontend contract tests**

Create tests/test_frontend_contract.py:

~~~python
from pathlib import Path


HTML = Path("src/cpf_fcv_reviewer/templates/index.html")
JS = Path("src/cpf_fcv_reviewer/static/app.js")


def test_interface_has_required_review_controls():
    html = HTML.read_text(encoding="utf-8")
    for element_id in (
        'id="cpf"',
        'id="supporting"',
        'id="review-stage"',
        'id="guidance"',
        'id="progress"',
        'id="results"',
        'id="correction-text"',
        'id="export-docx"',
        'id="reset-review"',
    ):
        assert element_id in html


def test_browser_state_is_session_only():
    javascript = JS.read_text(encoding="utf-8")
    assert "sessionStorage" in javascript
    assert "localStorage" not in javascript


def test_sensitivity_and_source_labels_are_rendered():
    javascript = JS.read_text(encoding="utf-8")
    assert "Frame cautiously" in javascript
    assert "Confirm with country team or FCV specialist" in javascript
    assert "evidence_ids" in javascript
~~~

- [ ] **Step 2: Run tests and verify failure**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_frontend_contract.py -q
~~~

Expected: failure because template and static files do not exist.

- [ ] **Step 3: Create the semantic HTML shell**

Create src/cpf_fcv_reviewer/templates/index.html:

~~~html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>CPF FCV Reviewer</title>
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
  <header>
    <p class="eyebrow">FCV REVIEW PROTOTYPE</p>
    <h1>Strengthen the FCV framing of a CPF or CEN</h1>
    <p class="advisory">Advisory first pass only. No clearance, policy
      determination, eligibility finding, or official classification.</p>
  </header>
  <main>
    <form id="review-form">
      <label>Country <input id="country" name="country" required></label>
      <label>Review stage
        <select id="review-stage" name="review_stage" required>
          <option value="early_drafting">Early drafting</option>
          <option value="concept_review">Concept review</option>
          <option value="decision_review">Decision review</option>
          <option value="roc_oc">ROC / OC</option>
          <option value="finalization">Finalization</option>
          <option value="response_to_comments">Response to comments</option>
        </select>
      </label>
      <label>CPF or CEN <input id="cpf" name="cpf" type="file"
        accept=".pdf,.docx,.txt,.md" required></label>
      <label>Supporting package <input id="supporting" name="supporting"
        type="file" accept=".pdf,.docx,.txt,.md" multiple></label>
      <label>Analysis guidance
        <textarea id="guidance" name="guidance"></textarea>
      </label>
      <button type="submit">Run review</button>
    </form>

    <section id="progress" hidden aria-live="polite"></section>
    <section id="results" hidden></section>

    <section id="corrections" hidden>
      <h2>Add context or correct a finding</h2>
      <p>Corrections remain labelled as user-provided unless independently
        supported by evidence.</p>
      <textarea id="correction-text"></textarea>
      <button id="submit-correction" type="button">Add correction and rerun</button>
    </section>

    <nav id="actions" hidden>
      <button id="export-docx" type="button">Export Word note</button>
      <button id="reset-review" type="button">Reset and purge review</button>
    </nav>
  </main>
  <script src="/static/app.js"></script>
</body>
</html>
~~~

- [ ] **Step 4: Implement intake, SSE progress, result rendering, correction, and purge**

Create src/cpf_fcv_reviewer/static/app.js:

~~~javascript
const form = document.querySelector("#review-form");
const progress = document.querySelector("#progress");
const results = document.querySelector("#results");
const corrections = document.querySelector("#corrections");
const actions = document.querySelector("#actions");
let assessmentId = sessionStorage.getItem("cpf_fcv_assessment_id") || "";

const sensitivityLabels = {
  direct: "Suitable to state directly",
  cautious: "Frame cautiously",
  confirm: "Confirm with country team or FCV specialist",
  withhold: "Do not suggest for inclusion without guidance",
};

function text(tag, value, className = "") {
  const node = document.createElement(tag);
  node.textContent = value;
  if (className) node.className = className;
  return node;
}

function renderResult(result) {
  results.replaceChildren();
  results.append(
    text("h2", result.executive_judgment),
    text("h3", result.diagnostic_title)
  );
  for (const finding of result.findings) {
    const article = document.createElement("article");
    article.append(
      text("h3", finding.title),
      text("p", finding.narrative),
      text("p", sensitivityLabels[finding.sensitivity], "sensitivity"),
      text("p", `Evidence: ${finding.evidence_ids.join(", ")}`, "evidence")
    );
    results.append(article);
  }
  results.hidden = false;
  corrections.hidden = false;
  actions.hidden = false;
}

async function loadResult(resultUrl) {
  const response = await fetch(resultUrl);
  if (response.status === 202) return;
  if (!response.ok) throw new Error("Review result is unavailable.");
  renderResult(await response.json());
}

function watchEvents(eventUrl, resultUrl) {
  const source = new EventSource(eventUrl);
  source.addEventListener("step_start", (event) => {
    const data = JSON.parse(event.data);
    progress.textContent = `Working: ${data.step}`;
  });
  source.addEventListener("run_complete", async () => {
    source.close();
    progress.textContent = "Review complete";
    await loadResult(resultUrl);
  });
  source.addEventListener("run_failed", (event) => {
    source.close();
    const data = JSON.parse(event.data);
    progress.textContent = `Review stopped: ${data.message}`;
  });
  source.addEventListener("expired", () => {
    source.close();
    progress.textContent = "This volatile review session expired. Upload again.";
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  progress.hidden = false;
  progress.textContent = "Uploading and validating";
  const response = await fetch("/api/reviews", {
    method: "POST",
    body: new FormData(form),
  });
  if (!response.ok) {
    progress.textContent = "The review could not start.";
    return;
  }
  const created = await response.json();
  assessmentId = created.assessment_id;
  sessionStorage.setItem("cpf_fcv_assessment_id", assessmentId);
  watchEvents(created.event_url, created.result_url);
});

document.querySelector("#submit-correction").addEventListener("click", async () => {
  const correction = document.querySelector("#correction-text").value.trim();
  if (!correction || !assessmentId) return;
  const response = await fetch(`/api/reviews/${assessmentId}/corrections`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({text: correction}),
  });
  if (response.ok) {
    progress.hidden = false;
    progress.textContent = "User-provided correction saved; rerun requested.";
  }
});

document.querySelector("#export-docx").addEventListener("click", () => {
  if (assessmentId) {
    window.location.assign(`/api/reviews/${assessmentId}/export.docx`);
  }
});

document.querySelector("#reset-review").addEventListener("click", async () => {
  if (assessmentId) {
    await fetch(`/api/reviews/${assessmentId}`, {method: "DELETE"});
  }
  sessionStorage.removeItem("cpf_fcv_assessment_id");
  assessmentId = "";
  results.replaceChildren();
  results.hidden = true;
  corrections.hidden = true;
  actions.hidden = true;
  progress.hidden = true;
  form.reset();
});
~~~

- [ ] **Step 5: Add restrained styling**

Create src/cpf_fcv_reviewer/static/styles.css:

~~~css
:root {
  --navy: #002244;
  --blue: #009fda;
  --paper: #f7f8fa;
  --ink: #1f2937;
  --muted: #667085;
  --rule: #d9dee7;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink);
  font: 15px/1.55 "Open Sans", Arial, sans-serif; }
header, main { width: min(980px, calc(100% - 40px)); margin: 0 auto; }
header { padding: 52px 0 24px; }
h1, h2, h3 { color: var(--navy); }
.eyebrow { color: var(--blue); font-weight: 700; letter-spacing: .1em; }
.advisory { border-left: 4px solid var(--blue); padding: 12px 16px;
  background: white; }
form, article, #progress, #corrections, #actions { background: white;
  border: 1px solid var(--rule); border-radius: 8px; padding: 20px;
  margin: 16px 0; }
label { display: block; font-weight: 700; margin: 12px 0; }
input, select, textarea { display: block; width: 100%; margin-top: 6px;
  padding: 10px; border: 1px solid var(--rule); border-radius: 4px; }
textarea { min-height: 110px; }
button { border: 0; border-radius: 4px; padding: 10px 16px;
  background: var(--navy); color: white; font-weight: 700; cursor: pointer; }
.sensitivity, .evidence { color: var(--muted); font-size: .92rem; }
~~~

- [ ] **Step 6: Serve the template**

In app.py, import render_template and add:

~~~python
@app.get("/")
def index():
    return render_template("index.html")
~~~

- [ ] **Step 7: Run tests and inspect locally**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_frontend_contract.py -q
.\.venv\Scripts\python.exe -m flask --app cpf_fcv_reviewer.app run
~~~

Expected: frontend tests pass; http://127.0.0.1:5000 displays the intake page; browser storage shows only the sessionStorage assessment ID and no localStorage review content.

- [ ] **Step 8: Commit**

~~~powershell
git add -- src/cpf_fcv_reviewer/templates src/cpf_fcv_reviewer/static src/cpf_fcv_reviewer/app.py tests/test_frontend_contract.py
git commit -m "feat: add country-team review interface"
~~~

### Task 12: Render the validated Review Result to DOCX with reproducibility metadata

**Files:**
- Create: src/cpf_fcv_reviewer/export_docx.py
- Modify: src/cpf_fcv_reviewer/routes.py
- Create: tests/test_docx_export.py
- Create: tests/test_output_parity.py
- Create: tests/conftest.py

- [ ] **Step 1: Write failing DOCX content and sensitivity tests**

Create tests/test_docx_export.py:

~~~python
from datetime import UTC, datetime
from io import BytesIO

from docx import Document

from cpf_fcv_reviewer.contracts import (
    DiagnosticMode,
    EvidenceItem,
    EvidenceLocator,
    Finding,
    ReviewResult,
    RunMetadata,
    SensitivityCategory,
)
from cpf_fcv_reviewer.export_docx import build_docx


def make_result():
    metadata = RunMetadata(
        run_id="run-1",
        created_at=datetime.now(UTC),
        review_stage="finalization",
        diagnostic_mode=DiagnosticMode.LIMITED_FRAMING,
        app_release="0.1.0",
        schema_version="1.0.0",
        rubric_version="1.0.0",
        prompt_bundle_version="1.0.0",
        registry_versions={"opcs": "1.0.0-test"},
        model_id="fake-model",
    )
    return ReviewResult(
        metadata=metadata,
        executive_judgment="The CPF has a useful foundation.",
        diagnostic_title="Limited FCV diagnostic-framing assessment",
        findings=(
            Finding(
                finding_id="f1",
                title="Strengthen the causal link",
                narrative="The link remains implicit.",
                status="needs_strengthening",
                evidence_ids=("ev-1",),
                sensitivity=SensitivityCategory.CAUTIOUS,
            ),
        ),
        recommendations=(),
        institutional_referral_ids=("SYN-REF-001",),
        limitations=("No RRA was available.",),
    )


def test_docx_contains_same_result_and_source_locator():
    result = make_result()
    evidence = {
        "ev-1": EvidenceItem(
            evidence_id="ev-1",
            evidence_type="document_fact",
            text="The link is implicit.",
            confidence="high",
            locator=EvidenceLocator(
                document_title="CPF.docx",
                heading="Results framework",
                element="paragraph 12",
                excerpt="The program will support access.",
            ),
        )
    }

    data = build_docx(
        result,
        evidence=evidence,
        hydrated_referrals=(
            {
                "entry_id": "SYN-REF-001",
                "approved_text": "Consult the designated policy owner.",
                "version": "1.0.0-test",
            },
        ),
    )
    document = Document(BytesIO(data))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert result.executive_judgment in text
    assert "CPF.docx | Results framework | paragraph 12" in text
    assert "Frame cautiously" in text
    assert "Consult the designated policy owner." in text
    assert "fake-model" in text
    assert "No RRA was available." in text


def test_withheld_content_is_not_rendered_as_draft_language():
    result = make_result()
    data = build_docx(result, evidence={}, hydrated_referrals=())
    document = Document(BytesIO(data))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Suggested ready-to-paste text" not in text
~~~

- [ ] **Step 2: Run tests and verify failure**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_docx_export.py -q
~~~

Expected: import fails because export_docx.py does not exist.

- [ ] **Step 3: Implement the DOCX renderer**

Create src/cpf_fcv_reviewer/export_docx.py:

~~~python
from __future__ import annotations

from io import BytesIO

from docx import Document
from docx.shared import Inches, Pt

from .contracts import EvidenceItem, ReviewResult


SENSITIVITY_LABELS = {
    "direct": "Suitable to state directly",
    "cautious": "Frame cautiously",
    "confirm": "Confirm with country team or FCV specialist",
    "withhold": "Do not suggest for inclusion without guidance",
}


def locator_text(item: EvidenceItem) -> str:
    locator = item.locator
    if locator is None:
        return "Analytical inference; no document locator"
    parts = [locator.document_title]
    if locator.page is not None:
        parts.append(f"page {locator.page}")
    if locator.heading:
        parts.append(locator.heading)
    if locator.element:
        parts.append(locator.element)
    return " | ".join(parts)


def build_docx(
    result: ReviewResult,
    *,
    evidence: dict[str, EvidenceItem],
    hydrated_referrals: tuple[dict, ...],
) -> bytes:
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)

    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)

    document.add_heading("CPF FCV Review", level=0)
    document.add_paragraph(
        "AI-assisted advisory first pass. This is not clearance, policy advice, "
        "a compliance finding, an eligibility determination, or an official "
        "classification."
    )
    document.add_heading("Executive judgment", level=1)
    document.add_paragraph(result.executive_judgment)
    document.add_heading(result.diagnostic_title, level=1)

    for finding in result.findings:
        document.add_heading(finding.title, level=2)
        document.add_paragraph(finding.narrative)
        document.add_paragraph(
            f"Sensitivity: {SENSITIVITY_LABELS[finding.sensitivity.value]}"
        )
        for evidence_id in finding.evidence_ids:
            item = evidence.get(evidence_id)
            if item is None:
                continue
            document.add_paragraph(
                f"Source: {locator_text(item)}\nExcerpt: "
                f"{item.locator.excerpt if item.locator else item.text}"
            )

    if result.recommendations:
        document.add_heading("Practical options", level=1)
        for recommendation in result.recommendations:
            document.add_heading(recommendation.action, level=2)
            document.add_paragraph(recommendation.why_it_matters)
            document.add_paragraph(
                f"Target: {recommendation.target_locator.document_title} | "
                f"{recommendation.target_locator.heading or ''} | "
                f"{recommendation.target_locator.element or ''}"
            )
            document.add_paragraph(
                f"Sensitivity: "
                f"{SENSITIVITY_LABELS[recommendation.sensitivity.value]}"
            )

    if hydrated_referrals:
        document.add_heading("Matters for confirmation", level=1)
        for referral in hydrated_referrals:
            document.add_paragraph(referral["approved_text"])
            document.add_paragraph(
                f"Registry: {referral['entry_id']} | {referral['version']}"
            )

    document.add_heading("Limitations", level=1)
    for limitation in result.limitations:
        document.add_paragraph(limitation, style="List Bullet")

    document.add_heading("Reproducibility metadata", level=1)
    metadata = result.metadata
    for label, value in (
        ("Run", metadata.run_id),
        ("Created", metadata.created_at.isoformat()),
        ("Application", metadata.app_release),
        ("Schema", metadata.schema_version),
        ("Rubric", metadata.rubric_version),
        ("Prompts", metadata.prompt_bundle_version),
        ("Model", metadata.model_id),
        ("Diagnostic mode", metadata.diagnostic_mode.value),
        ("Repair count", str(metadata.repair_count)),
    ):
        document.add_paragraph(f"{label}: {value}")

    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()
~~~

- [ ] **Step 4: Add the export route**

Add to routes.py:

~~~python
from flask import send_file
from io import BytesIO

from .contracts import EvidenceItem, ReviewResult
from .export_docx import build_docx
from .registry import hydrate_referrals


@bp.get("/api/reviews/<assessment_id>/export.docx")
def export_review(assessment_id):
    try:
        state = store().get(assessment_id)
    except SessionExpired:
        return jsonify(error="Assessment expired."), 410
    result = ReviewResult.model_validate(state.payload["result"])
    bundle = current_app.extensions["registry_bundle"]
    data = build_docx(
        result,
        evidence={
            evidence_id: EvidenceItem.model_validate(item)
            for evidence_id, item in state.payload["evidence_by_id"].items()
        },
        hydrated_referrals=hydrate_referrals(
            result.institutional_referral_ids,
            bundle,
        ),
    )
    return send_file(
        BytesIO(data),
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        as_attachment=True,
        download_name="CPF-FCV-Review.docx",
    )
~~~

- [ ] **Step 5: Test browser/DOCX parity**

Create tests/test_output_parity.py:

~~~python
from io import BytesIO

from docx import Document

from cpf_fcv_reviewer.export_docx import build_docx


def test_browser_fields_are_present_in_docx(make_valid_result):
    result, evidence = make_valid_result()
    data = build_docx(result, evidence=evidence, hydrated_referrals=())
    document = Document(BytesIO(data))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert result.executive_judgment in text
    for finding in result.findings:
        assert finding.title in text
        assert finding.narrative in text
    for recommendation in result.recommendations:
        assert recommendation.action in text
        assert recommendation.why_it_matters in text
~~~

Put make_valid_result in tests/conftest.py so route, validator, and export tests share one contract-valid fixture rather than constructing diverging shapes.

- [ ] **Step 6: Run tests and lint**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_docx_export.py tests\test_output_parity.py -q
.\.venv\Scripts\python.exe -m ruff check src tests
~~~

Expected: all tests pass; Ruff exits 0.

- [ ] **Step 7: Commit**

~~~powershell
git add -- src tests
git commit -m "feat: export traceable CPF FCV review notes"
~~~

### Task 13: Complete priority-question confirmation and correction reruns

**Files:**
- Create: src/cpf_fcv_reviewer/priority_questions.py
- Modify: src/cpf_fcv_reviewer/routes.py
- Modify: src/cpf_fcv_reviewer/static/app.js
- Modify: src/cpf_fcv_reviewer/templates/index.html
- Create: tests/test_priority_questions.py
- Create: tests/test_correction_rerun.py

- [ ] **Step 1: Write failing priority-question detection tests**

Create tests/test_priority_questions.py:

~~~python
from cpf_fcv_reviewer.priority_questions import detect_priority_questions


def test_detects_questions_without_turning_statements_into_questions():
    guidance = """
    Please pay attention to regional spillovers.
    Does the results framework track geographic distribution?
    Is the partnership logic credible?
    """
    assert detect_priority_questions(guidance) == (
        "Does the results framework track geographic distribution?",
        "Is the partnership logic credible?",
    )


def test_deduplicates_questions_case_insensitively():
    guidance = "Is access addressed?\nis access addressed?"
    assert detect_priority_questions(guidance) == ("Is access addressed?",)
~~~

- [ ] **Step 2: Implement deterministic question detection**

Create src/cpf_fcv_reviewer/priority_questions.py:

~~~python
from __future__ import annotations


def detect_priority_questions(text: str) -> tuple[str, ...]:
    seen: set[str] = set()
    questions: list[str] = []
    for line in text.splitlines():
        clean = line.strip(" -\t")
        if not clean.endswith("?"):
            continue
        key = clean.casefold()
        if key not in seen:
            seen.add(key)
            questions.append(clean)
    return tuple(questions)
~~~

- [ ] **Step 3: Add confirmation controls to the frontend**

Add below the guidance textarea in index.html:

~~~html
<fieldset id="priority-questions" hidden>
  <legend>Questions requiring a dedicated response</legend>
  <div id="priority-question-list"></div>
</fieldset>
~~~

Add to app.js:

~~~javascript
const guidance = document.querySelector("#guidance");
const questionPanel = document.querySelector("#priority-questions");
const questionList = document.querySelector("#priority-question-list");

function detectedQuestions(value) {
  return [...new Set(
    value.split(/\r?\n/)
      .map((line) => line.trim().replace(/^[-*]\s*/, ""))
      .filter((line) => line.endsWith("?"))
  )];
}

function renderPriorityQuestions() {
  questionList.replaceChildren();
  for (const question of detectedQuestions(guidance.value)) {
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "priority_questions";
    checkbox.value = question;
    checkbox.checked = true;
    label.append(checkbox, document.createTextNode(question));
    questionList.append(label);
  }
  questionPanel.hidden = questionList.children.length === 0;
}

guidance.addEventListener("input", renderPriorityQuestions);
~~~

The multipart intake route reads request.form.getlist("priority_questions") and stores only confirmed questions.

- [ ] **Step 4: Write the failing correction-rerun lineage test**

Create tests/test_correction_rerun.py:

~~~python
from tests.test_routes import create_review

from cpf_fcv_reviewer.app import create_app


def test_correction_creates_child_run_with_label_and_parent():
    app = create_app({"TESTING": True, "START_BACKGROUND_RUNS": False})
    client = app.test_client()
    parent = create_review(client)

    response = client.post(
        f"/api/reviews/{parent['assessment_id']}/corrections",
        json={
            "text": "The cited reform was adopted in July.",
            "affected_finding_id": "f1",
            "rationale": "Country-team update",
        },
    )

    assert response.status_code == 201
    child = response.get_json()
    assert child["assessment_id"] != parent["assessment_id"]
    assert child["parent_assessment_id"] == parent["assessment_id"]

    state = app.extensions["session_store"].get(child["assessment_id"])
    correction = state.payload["corrections"][-1]
    assert correction["label"] == "User-provided correction"
    assert correction["independently_supported"] is False
~~~

- [ ] **Step 5: Implement child-run corrections**

Replace add_correction in routes.py:

~~~python
from datetime import UTC, datetime
from uuid import uuid4


@bp.post("/api/reviews/<assessment_id>/corrections")
def add_correction(assessment_id):
    parent = store().get(assessment_id)
    body = request.get_json(force=True)
    text = body.get("text", "").strip()
    if not text:
        return jsonify(error="Correction text is required."), 400

    child_payload = dict(parent.payload)
    child_payload["corrections"] = list(parent.payload.get("corrections", ()))
    child_payload["corrections"].append(
        {
            "correction_id": uuid4().hex,
            "created_at": datetime.now(UTC).isoformat(),
            "label": "User-provided correction",
            "text": text,
            "affected_finding_id": body.get("affected_finding_id"),
            "rationale": body.get("rationale"),
            "independently_supported": False,
        }
    )
    child_payload["parent_assessment_id"] = assessment_id
    child_payload["status"] = "created"
    child_payload.pop("result", None)

    child_id = store().create(child_payload)
    if current_app.config["START_BACKGROUND_RUNS"]:
        app = current_app._get_current_object()
        Thread(target=run_assessment, args=(app, child_id), daemon=True).start()
    base = f"/api/reviews/{child_id}"
    return (
        jsonify(
            assessment_id=child_id,
            parent_assessment_id=assessment_id,
            event_url=f"{base}/events",
            result_url=f"{base}/result",
        ),
        201,
    )
~~~

Update the frontend correction handler to replace assessmentId with the child identifier, update sessionStorage, and call watchEvents with the returned URLs.

- [ ] **Step 6: Test direct answers and explicit evidence gaps**

Extend tests/test_review_engine.py with a contract-valid result containing two confirmed questions. Assert that each confirmed question has exactly one PriorityQuestionResponse and that an unanswerable question contains limitation text instead of a fabricated answer.

Add a validator rule:

~~~python
def validate_priority_questions(
    confirmed: tuple[str, ...],
    result: ReviewResult,
) -> tuple[ValidationIssue, ...]:
    answered = {item.question for item in result.priority_question_responses}
    missing = set(confirmed) - answered
    if missing:
        return (
            ValidationIssue(
                "missing_priority_response",
                f"Missing priority responses: {sorted(missing)}",
            ),
        )
    return ()
~~~

- [ ] **Step 7: Run tests and lint**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_priority_questions.py tests\test_correction_rerun.py tests\test_review_engine.py -q
.\.venv\Scripts\python.exe -m ruff check src tests
~~~

Expected: all tests pass; Ruff exits 0.

- [ ] **Step 8: Commit**

~~~powershell
git add -- src tests
git commit -m "feat: add priority questions and correction reruns"
~~~

### Task 14: Complete reproducibility, failure handling, and adversarial validation

**Files:**
- Create: src/cpf_fcv_reviewer/reproducibility.py
- Modify: src/cpf_fcv_reviewer/contracts.py
- Modify: src/cpf_fcv_reviewer/evidence_builder.py
- Modify: src/cpf_fcv_reviewer/orchestrator.py
- Modify: src/cpf_fcv_reviewer/export_docx.py
- Create: tests/test_reproducibility.py
- Create: tests/test_failure_handling.py
- Create: tests/test_adversarial.py
- Create: tests/test_security.py
- Create: tests/fixtures/synthetic_en.txt
- Create: tests/fixtures/synthetic_fr.txt
- Create: tests/fixtures/synthetic_mixed.txt

- [ ] **Step 1: Write failing reproducibility tests**

Create tests/test_reproducibility.py:

~~~python
from datetime import UTC, datetime

from cpf_fcv_reviewer.reproducibility import build_run_metadata, sha256_bytes


def test_metadata_records_every_reproducibility_input():
    metadata = build_run_metadata(
        run_id="run-1",
        created_at=datetime(2026, 8, 10, tzinfo=UTC),
        review_stage="early_draft",
        diagnostic_mode="limited_diagnostic_framing",
        documents={"CPF draft": b"synthetic input"},
        registry_bundle=b'{"bundle_version":"2026.08"}',
        guidance="Check the conflict narrative.",
        prompt_bytes={"review": b"review-v1"},
        model_id="claude-sonnet-4-5",
        source_scan_at=datetime(2026, 8, 10, tzinfo=UTC),
        output_language="en",
        validation_outcomes=("contract_valid", "policy_guardrails_passed"),
        correction_ids=("c-1",),
        parent_run_id="run-0",
    )

    assert metadata.document_fingerprints == {
        "CPF draft": sha256_bytes(b"synthetic input")
    }
    assert metadata.registry_bundle_hash == sha256_bytes(
        b'{"bundle_version":"2026.08"}'
    )
    assert metadata.guidance_hash == sha256_bytes(
        b"Check the conflict narrative."
    )
    assert metadata.prompt_hashes == {"review": sha256_bytes(b"review-v1")}
    assert metadata.source_scan_at.isoformat() == "2026-08-10T00:00:00+00:00"
    assert metadata.output_language == "en"
    assert metadata.validation_outcomes[-1] == "policy_guardrails_passed"
    assert metadata.correction_ids == ("c-1",)
    assert metadata.parent_run_id == "run-0"
~~~

Run:

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_reproducibility.py -q
~~~

Expected: fail because the complete metadata builder and fields do not yet exist.

- [ ] **Step 2: Extend the immutable run metadata and build it deterministically**

Add these fields to RunMetadata in contracts.py:

~~~python
source_scan_at: datetime | None = None
output_language: Literal["en"] = "en"
document_fingerprints: dict[str, str] = Field(default_factory=dict)
registry_bundle_hash: str = ""
guidance_hash: str = ""
prompt_hashes: dict[str, str] = Field(default_factory=dict)
validation_outcomes: tuple[str, ...] = ()
correction_ids: tuple[str, ...] = ()
~~~

Create reproducibility.py:

~~~python
from datetime import datetime
from hashlib import sha256
from typing import Mapping

from .contracts import DiagnosticMode, RunMetadata


def sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def build_run_metadata(
    *,
    run_id: str,
    created_at: datetime,
    review_stage: str,
    diagnostic_mode: DiagnosticMode | str,
    documents: Mapping[str, bytes],
    registry_bundle: bytes,
    guidance: str,
    prompt_bytes: Mapping[str, bytes],
    model_id: str,
    source_scan_at: datetime,
    output_language: str,
    validation_outcomes: tuple[str, ...] = (),
    correction_ids: tuple[str, ...] = (),
    parent_run_id: str | None = None,
    repair_count: int = 0,
) -> RunMetadata:
    return RunMetadata(
        run_id=run_id,
        created_at=created_at,
        review_stage=review_stage,
        diagnostic_mode=diagnostic_mode,
        app_release="0.1.0",
        schema_version="1.0.0",
        rubric_version="1.0.0",
        prompt_bundle_version="1.0.0",
        registry_versions={"bundle": "2026.08"},
        model_id=model_id,
        parent_run_id=parent_run_id,
        repair_count=repair_count,
        source_scan_at=source_scan_at,
        output_language=output_language,
        document_fingerprints={
            name: sha256_bytes(content)
            for name, content in sorted(documents.items())
        },
        registry_bundle_hash=sha256_bytes(registry_bundle),
        guidance_hash=sha256_bytes(guidance.encode("utf-8")),
        prompt_hashes={
            name: sha256_bytes(content)
            for name, content in sorted(prompt_bytes.items())
        },
        validation_outcomes=validation_outcomes,
        correction_ids=correction_ids,
    )
~~~

Only hashes, versions, timestamps, identifiers, and validation labels enter metadata. Raw documents, excerpts, guidance, and corrections never enter logs or metadata. The defaults keep the red/green sequence type-consistent; add a final-result validator in this task that rejects missing source_scan_at, document fingerprints, registry hash, guidance hash, or prompt hashes before a result can be returned or exported.

- [ ] **Step 3: Write the adversarial matrix before extending behavior**

Create tests/test_adversarial.py. Use synthetic fixtures and explicit expected safe behavior:

~~~python
import pytest

from cpf_fcv_reviewer.contracts import DiagnosticMode
from cpf_fcv_reviewer.validators import validate_review


@pytest.mark.parametrize(
    ("case", "mode", "expected_issue"),
    [
        ("missing_rra", DiagnosticMode.LIMITED, "limited_mode_overclaim"),
        ("outdated_rra", DiagnosticMode.RRA_ALIGNMENT, "source_recency_warning"),
        ("ambiguous_original", DiagnosticMode.RRA_ALIGNMENT, "source_ambiguity"),
        ("policy_confirmation_request", DiagnosticMode.RRA_ALIGNMENT,
         "policy_determination"),
        ("late_stage_restructure", DiagnosticMode.RRA_ALIGNMENT,
         "finalization_stage_overreach"),
        ("user_steering", DiagnosticMode.RRA_ALIGNMENT,
         "unsupported_user_claim"),
    ],
)
def test_high_risk_cases_abstain_or_downgrade(
    adversarial_result_factory,
    case,
    mode,
    expected_issue,
):
    result, evidence, context = adversarial_result_factory(case, mode)
    issues = validate_review(result, evidence, context)
    assert expected_issue in {issue.code for issue in issues}
~~~

The adversarial_result_factory must also cover, as separate named scenarios:

- direct SharePoint original versus a derived Markdown copy, with the original selected;
- no RRA/equivalent, which forces limited diagnostic framing and grouped priority questions rather than alignment ratings;
- strongly contextual narrative with a weak results framework, and the inverse case;
- regional and cross-border risks whose country relevance is uncertain;
- scanned PDFs, dense tables, incomplete extraction, and unsupported embedded figures;
- English, French, and mixed-language input, with English output and preserved French evidence excerpts;
- prompt injection in uploaded text and in user guidance;
- stale, malformed, unapproved, or tampered registry bundles;
- public-source disagreement, missing publication dates, and any proposed licensed-ACLED dependency;
- restricted, sensitive, and highly sensitive excerpts;
- model timeout, schema failure after one repair, source failure, and DOCX-rendering failure;
- two concurrent sessions, session expiry, reset, and attempted cross-session access;
- attempts to place raw text, filenames, user corrections, or generated findings in application logs.

For each scenario, assert the exact downgrade, warning, abstention, 4xx/5xx status, or retained result. Do not accept snapshot-only assertions.

- [ ] **Step 4: Add explicit failure states and a non-content logger**

Create tests/test_failure_handling.py with fake adapters that raise TimeoutError and RegistryUnavailable. Assert that the orchestrator emits run_failed with only a stable error code and never emits raw exception text. Assert exactly one repair call after a structurally invalid result and zero further calls after the repair fails.

Add to orchestrator.py:

~~~python
SAFE_FAILURES = {
    TimeoutError: "model_timeout",
    RegistryUnavailable: "registry_unavailable",
    DocumentUnreadable: "document_unreadable",
}


def safe_failure_code(error: Exception) -> str:
    for error_type, code in SAFE_FAILURES.items():
        if isinstance(error, error_type):
            return code
    return "review_failed"
~~~

Define DocumentUnreadable(ValueError) in extraction.py and raise it from require_readable_primary. Import DocumentUnreadable and RegistryUnavailable in orchestrator.py. Wrap the workflow boundary, emit only the safe code, set the assessment state to failed, and preserve no partial model prose. Keep stack traces disabled in deployed configuration.

- [ ] **Step 5: Enforce language, source, sensitivity, and registry attack rules**

Add deterministic validators and tests with these outcomes:

~~~python
assert select_output_language("fr") == "en"
assert reject_source({"provider": "ACLED", "license": "licensed"})
with pytest.raises(RegistryUnavailable, match="hash"):
    load_registry_bundle(tampered_bundle, expected_hash="bad-hash")
assert redact_log_value("uploaded excerpt") == "[content omitted]"
~~~

The limited French-input path may detect headings and retain original French excerpts, but all interface labels, analysis, recommendations, limitations, and DOCX prose remain English. A source without a public URL, publication date, and relevance note cannot support a retained current-context claim. The registry loader fails closed if ownership, approval status, version, effective date, or bundle hash is absent or invalid.

- [ ] **Step 6: Add metadata to Evidence Pack creation and export**

Make evidence_builder.py call build_run_metadata after source discovery and before model invocation. On a correction rerun, record the parent run and correction identifiers without copying correction prose into metadata. Append all metadata fields to the DOCX reproducibility section and expose the same values in the browser result JSON.

- [ ] **Step 7: Run focused and full validation**

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests\test_reproducibility.py tests\test_failure_handling.py tests\test_adversarial.py tests\test_security.py -q
.\.venv\Scripts\python.exe -m pytest -q --cov=cpf_fcv_reviewer --cov-report=term-missing --cov-fail-under=90
.\.venv\Scripts\python.exe -m ruff check src tests
~~~

Expected: all tests pass, coverage is at least 90 percent, and Ruff exits 0.

- [ ] **Step 8: Commit**

~~~powershell
git add -- src tests
git commit -m "test: harden reproducibility and adversarial safeguards"
~~~

### Task 15: Validate the complete local workflow and document the handoff

**Files:**
- Create: tests/test_end_to_end.py
- Modify: README.md
- Modify: CLAUDE.md
- Create: docs/validation/2026-08-10-mvp-validation.md

- [ ] **Step 1: Write an end-to-end test using only synthetic content**

Create tests/test_end_to_end.py with fake SharePoint, public-search, and model adapters. Exercise upload, extraction, Evidence Pack construction, one visible SSE run, result retrieval, a labelled correction child run, reset, and DOCX export. Assert:

~~~python
assert result["metadata"]["diagnostic_mode"] == "limited_diagnostic_framing"
assert result["metadata"]["output_language"] == "en"
assert result["findings"][0]["evidence_ids"]
assert result["recommendations"][0]["target_locator"]["heading"]
assert "User-provided correction" in child_run_labels
assert docx_headings == browser_section_headings
assert stable_service_calls == []
~~~

Use synthetic English, French, and mixed-language inputs. No historical package is added unless the user separately approves that exact non-sensitive package for local validation.

- [ ] **Step 2: Run the application locally and complete a manual smoke test**

~~~powershell
$env:FLASK_APP = 'wsgi:app'
.\.venv\Scripts\python.exe -m flask run --host 127.0.0.1 --port 5055
~~~

In a second terminal, verify:

~~~powershell
Invoke-RestMethod http://127.0.0.1:5055/health
~~~

Expected: status healthy, no registry content or secrets in the response. In the browser, use the synthetic fixture and verify progressive phases, evidence expansion, sensitivity labels, correction lineage, DOCX parity, reset, and expiry messaging.

- [ ] **Step 3: Document the operational boundary**

Update README.md and CLAUDE.md with:

- advisory-only purpose and the prohibition on policy, compliance, eligibility, or clearance determinations;
- MVP versus validation versus production capability table;
- volatile session-only storage and the fact that restart/expiry/reset destroys review state;
- direct SharePoint original precedence and upload fallback for current RRAs, while noting that operational ITS access is outside this MVP;
- OPCS registry ownership, approved versioned summary requirement, fail-closed behavior, and no unsupported policy claims;
- public-web-only current-context research and no licensed ACLED dependency;
- supported English output and limited French-input behavior;
- test, local-run, export, and incident-stop commands;
- a bold prohibition on modifying the stable FCV Project Screener service.

Create docs/validation/2026-08-10-mvp-validation.md with executed command, timestamp, commit SHA, test counts, coverage, known limitations, synthetic package identifier, and the names of every adversarial scenario. Do not include raw source content, model output, secrets, or user corrections.

- [ ] **Step 4: Run release checks and inspect the diff**

~~~powershell
.\.venv\Scripts\python.exe -m pytest -q --cov=cpf_fcv_reviewer --cov-report=term-missing --cov-fail-under=90
.\.venv\Scripts\python.exe -m ruff check src tests
rg -n --hidden -g '!*.docx' -g '!*.pdf' '(ANTHROPIC_API_KEY\s*=\s*[^$]|BEGIN (RSA|OPENSSH|PRIVATE) KEY|sk-ant-|password\s*=)' .
git status --short
git diff --check
git diff --stat main...HEAD
~~~

Expected: tests and lint pass, the secret scan returns no matches, diff check is clean, and changes are limited to cpf-fcv-reviewer.

- [ ] **Step 5: Commit documentation, push the branch, and open a draft PR**

~~~powershell
git add -- README.md CLAUDE.md docs tests
git commit -m "docs: record MVP validation and safe-use boundary"
git push -u origin feat/mvp-review-run
gh pr create --draft --base main --head feat/mvp-review-run --title "feat: build CPF FCV review MVP" --body "Implements the approved MVP specification with volatile storage, traceable advisory outputs, registry-controlled institutional language, and adversarial validation."
~~~

Before pushing, inspect git status and git diff --staged. Never include .env files, source packages, generated review documents, or secrets.

### Task 16: Create and validate the isolated Render service after a separate confirmation

**Files:**
- Modify only if validation exposes a deployment defect: Procfile
- Modify only if validation exposes a deployment defect: README.md

- [ ] **Step 1: Enforce deployment preconditions**

Do not deploy unless all conditions are true:

1. The pull request contains only the approved MVP scope and all release checks pass.
2. The deployed registry bundle is an unexpired, OPCS-approved, versioned, non-confidential summary bundle whose hash matches the configured value.
3. The smoke-test package is explicitly approved historical non-sensitive content or the repository's synthetic package.
4. The service has no route, network reference, shared disk, environment import, or deployment hook connected to the stable FCV Project Screener.
5. No document retention, background persistence, analytics capture, or raw-content logging is enabled.

If any precondition fails, stop and report the failed condition without creating a service.

- [ ] **Step 2: Obtain action-time confirmation immediately before creation**

Ask exactly whether to create the isolated Render service cpf-fcv-review-prototype now. Do not click Create, call a Render API, or submit the service form before the user confirms.

- [ ] **Step 3: Create only the isolated service**

After confirmation, create cpf-fcv-review-prototype from private repository ljonestz/cpf-fcv-reviewer. Configure:

~~~text
Runtime: Python
Build command: pip install -r requirements.txt
Start command: gunicorn --worker-class gevent --workers 1 --bind 0.0.0.0:$PORT wsgi:app
Health check: /health
Persistent disk: none
Auto-deploy: disabled during validation
~~~

Use one worker because the approved MVP store is process-local and volatile. Set ANTHROPIC_API_KEY and the registry bundle hash only through Render's protected environment controls. Never put their values in chat, Git, build logs, screenshots, or documentation. Do not copy environment variables from another service.

- [ ] **Step 4: Verify safe deployment behavior**

Use only the approved synthetic or specifically approved non-sensitive package. Verify health, one complete run, visible progress phases, locator traceability, registry-controlled referrals, DOCX parity, correction child lineage, reset, expiry, and data loss after a controlled restart. Check logs for identifiers and safe status codes only; no filenames, excerpts, guidance, corrections, findings, tokens, or secrets may appear.

- [ ] **Step 5: Stop on any isolation or content-handling defect**

If the service touches the stable screener, persists review content, reveals a secret, logs raw content, accepts an invalid registry, or makes an unsupported policy claim, stop validation and disable the prototype service. Record only the non-sensitive defect category and remediation status.

## Plan self-review and requirements coverage

| Approved requirement | Implemented and verified in |
|---|---|
| Explicit MVP, validation, and production phasing | Scope section; Tasks 15 and 16; README capability table |
| Advisory and no-policy-determination guardrails | Tasks 5, 8, 9, 14, and 15 |
| Limited diagnostic framing without an RRA/equivalent | Tasks 7, 8, 9, and 14 |
| Grouped and prioritized diagnostic mapping | Tasks 7 and 14 |
| Stage-specific recommendation behavior | Tasks 8, 9, and 14 |
| Page, section, heading, and excerpt traceability | Tasks 4, 7, 9, 12, and 15 |
| Current-context recency/plausibility check | Tasks 6, 7, and 14 |
| Accurate multi-step orchestration in one visible run | Tasks 10, 11, and 15 |
| Volatile session-only storage | Tasks 3, 10, 11, 14, and 16 |
| Registry ownership, versioning, and change control | Tasks 5, 9, 12, 14, 15, and 16 |
| Labelled user corrections | Tasks 2, 13, 14, and 15 |
| Sensitivity categories | Tasks 2, 9, 11, 12, and 14 |
| English output with limited French-input support | Tasks 4, 8, 14, and 15 |
| Reproducibility metadata | Tasks 2, 8, 12, 14, and 15 |
| Expanded adversarial tests | Task 14 |
| ITS SharePoint originals with upload fallback | Tasks 5 and 15; production access remains explicitly deferred |
| Render uploads or approved non-confidential summaries | Tasks 5, 14, and 16 |
| OPCS-owned authoritative registry and versioned summaries | Tasks 5, 9, 12, 14, 15, and 16 |
| Public web only; no licensed ACLED dependency | Tasks 6, 14, and 15 |
| Direct originals preferred to Markdown derivatives | Tasks 5 and 14 |
| No factual OPCS policy/guidance claims outside registry language | Tasks 5, 9, 12, and 14 |
| Stable FCV Project Screener remains untouched | Scope section; Tasks 15 and 16 |
| Separate action-time confirmation for GitHub and Render | Tasks 0 and 16 |

Self-review checks before implementation begins:

- All production-affecting actions have an explicit, immediately preceding user-confirmation gate.
- Every model-visible assertion must resolve to an Evidence Pack identifier; every user-visible source claim must resolve to a page, section, heading, table, or excerpt locator.
- The model cannot create institutional referral prose: only approved registry identifiers are accepted, and exact approved text is hydrated after validation.
- Missing, stale, malformed, ambiguous, or unapproved authority sources cause downgrade, abstention, warning, or failure; they never trigger invented policy language.
- The reference prototype has no durable review storage and no multi-worker deployment.
- Operational SharePoint access, production identity, authorized-review workflows, persistence, audit retention, and production monitoring remain separate production work.
- Tests cover ordinary, degraded, adversarial, multilingual, concurrent, and failure paths.
- External content, secrets, and user corrections are absent from Git history, logs, test reports, and reproducibility metadata.

## Implementation approval and execution handoff

Approval of this plan authorizes the next conversation to ask for action-time confirmation to create the private GitHub repository. It does not itself authorize creating GitHub or Render resources, implementing code, deploying, or touching the stable FCV Project Screener.

After plan approval and GitHub action-time confirmation, execute task-by-task using superpowers:subagent-driven-development in this session (recommended) or superpowers:executing-plans in a separate task. Pause at test failures, scope changes, source-governance ambiguity, and the Render creation gate.





