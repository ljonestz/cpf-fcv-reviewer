# CPF Reviewer Output, Research, and Interface Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a screener-aligned two-page CPF/CEN reviewer that performs mandatory resilient current-country research and produces one canonical priority-led detailed note with a faithful five-minute readout.

**Architecture:** Preserve the Flask application, volatile session store, evidence-pack boundary, and one-run orchestration. Add a focused research controller between source resolution and evidence construction; extend the canonical review contract with one alignment synthesis used by the summary; then render dedicated intake, progress, summary, and detailed states from the same result. Keep the public Render adapter public-web-only while documenting the existing source-adapter boundary for a future permission-aware ITS SharePoint implementation.

**Tech Stack:** Python 3.12+, Flask, Pydantic v2, Anthropic Python SDK/web-search tool, python-docx, vanilla JavaScript, HTML/CSS, pytest, Ruff.

**Approved design:** `docs/superpowers/specs/2026-08-13-cpf-reviewer-output-research-ui-redesign-design.md`

---

## File structure and ownership

### New focused modules

- `src/cpf_fcv_reviewer/research_controller.py` — research mode, bounded attempt policy, parsing, sufficiency evaluation, progress events, and safe research exceptions.
- `src/cpf_fcv_reviewer/diagnostic_sources.py` — conservative identification and dating of an uploaded RRA or accepted equivalent; no web or SharePoint access.
- `tests/test_research_controller.py` — deterministic controller, retry, sufficiency, and timeout tests.
- `tests/test_diagnostic_sources.py` — RRA-present/no-RRA source-mode tests.

### Existing files to modify

- `src/cpf_fcv_reviewer/public_research.py` — strengthen claim metadata and make the provider return structured output with explicit timeout configuration.
- `prompts/public_research.md` — define RRA-update and holistic research modes, source hierarchy, and structured contract.
- `src/cpf_fcv_reviewer/config.py` — explicit bounded research settings.
- `src/cpf_fcv_reviewer/runtime.py` — execute research, attach current-context evidence, select diagnostic mode, and build one complete evidence pack.
- `src/cpf_fcv_reviewer/contracts.py` — add the canonical alignment synthesis used by both result views.
- `prompts/review.md` and `prompts/repair.md` — require the priority-led integrated note and faithful summary field.
- `src/cpf_fcv_reviewer/validators.py` — validate summary/priority consistency and current-context support.
- `src/cpf_fcv_reviewer/orchestrator.py` — stable research failure categories without weakening context clearing.
- `src/cpf_fcv_reviewer/routes.py` — preserve safe failure state and add bounded research retry using retained volatile uploads.
- `src/cpf_fcv_reviewer/export_docx.py` — full detailed note with alignment synthesis and evidence parity.
- `src/cpf_fcv_reviewer/templates/index.html` — screener-aligned intake and dedicated progress/results shells.
- `src/cpf_fcv_reviewer/static/app.js` — accessible Summary/Detailed tabs, safe research progress, and retry action.
- `src/cpf_fcv_reviewer/static/styles.css` — approved institutional visual system and responsive layouts.
- Existing tests under `tests/` — fixture, route, runtime, prompt, validator, DOCX, frontend, accessibility, and parity updates.
- `README.md`, `docs/PROJECT_STATUS.md`, and a new dated validation note — final verified behavior and remaining deployment limits.

### Explicitly out of scope

- No changes to `C:/Users/wb559324/OneDrive - WBG/Documents/GitHub/FCV-AGENT`.
- No SharePoint client or confidential RRA corpus in the Render prototype.
- No second public search provider in this slice.
- No durable storage, identity layer, or production authorization.

---

### Task 1: Make the canonical result support the five-minute alignment readout

**Files:**
- Modify: `src/cpf_fcv_reviewer/contracts.py:262-289`
- Modify: `tests/conftest.py:40-82`
- Modify: `tests/test_contracts.py`
- Modify: `tests/test_model_gateway.py`

- [ ] **Step 1: Write failing contract tests**

Add tests that require a nonblank alignment synthesis on both model-authored and application-owned results:

```python
def test_review_result_requires_nonblank_alignment_readout(make_valid_result):
    result, _ = make_valid_result
    with pytest.raises(ValidationError):
        ReviewResult.model_validate(
            {**result.model_dump(mode="json"), "alignment_readout": "   "}
        )


def test_review_draft_requires_alignment_readout(make_valid_result):
    result, _ = make_valid_result
    draft = ReviewDraft(
        overall_read=result.overall_read,
        alignment_readout=(
            "The draft partly reflects the diagnostic and current context, "
            "but the strategic response remains incomplete."
        ),
        revision_summary=result.revision_summary,
        priority_areas=result.priority_areas,
        institutional_referral_ids=result.institutional_referral_ids,
        limitations=result.limitations,
        coverage_note=result.document_coverage.coverage_note,
    )
    assert draft.alignment_readout.startswith("The draft partly reflects")
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_contracts.py tests/test_model_gateway.py -q
```

Expected: FAIL because `alignment_readout` is not defined.

- [ ] **Step 3: Add the minimal canonical field**

Add the same required field to `ReviewResult` and `ReviewDraft`, and include it in the shared nonblank validator:

```python
class ReviewResult(FrozenModel):
    metadata: RunMetadata
    overall_read: str
    alignment_readout: str
    revision_summary: tuple[RevisionSummaryItem, ...]
    priority_areas: tuple[PriorityArea, ...]
    institutional_referral_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    document_coverage: DocumentCoverage

    @field_validator("overall_read", "alignment_readout")
    @classmethod
    def requires_nonblank_readout(cls, value: str) -> str:
        return _requires_nonblank_text(value, "Review readout")


class ReviewDraft(FrozenModel):
    overall_read: str
    alignment_readout: str
    revision_summary: tuple[RevisionSummaryItem, ...]
    priority_areas: tuple[PriorityArea, ...]
    institutional_referral_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    coverage_note: str

    @field_validator("overall_read", "alignment_readout", "coverage_note")
    @classmethod
    def requires_nonblank_draft_text(cls, value: str) -> str:
        return _requires_nonblank_text(value, "Review draft text")
```

Update `make_valid_result` with a country-specific alignment paragraph. Do not add separate summary priorities; `revision_summary` remains the canonical concise priority list.

- [ ] **Step 4: Run focused tests**

Run the command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/contracts.py tests/conftest.py tests/test_contracts.py tests/test_model_gateway.py
git commit -m "feat: add canonical CPF alignment readout"
```

---

### Task 2: Define diagnostic-source and research-mode inputs

**Files:**
- Create: `src/cpf_fcv_reviewer/diagnostic_sources.py`
- Create: `tests/test_diagnostic_sources.py`
- Modify: `src/cpf_fcv_reviewer/sources.py`

- [ ] **Step 1: Write failing diagnostic-identification tests**

Cover an explicit RRA, an equivalent diagnostic, ordinary supporting analytics, and an undated RRA:

```python
from datetime import date
from types import SimpleNamespace

from cpf_fcv_reviewer.diagnostic_sources import identify_uploaded_diagnostic


def _document(name: str, text: str):
    return SimpleNamespace(
        name=name,
        segments=(SimpleNamespace(text=text, page=1, heading=None, element="paragraph 1"),),
    )


def test_identifies_and_dates_explicit_rra():
    document = _document(
        "benin-rra.pdf",
        "Benin Risk and Resilience Assessment\nPublished March 2022",
    )
    candidate = identify_uploaded_diagnostic((document,), country="Benin")
    assert candidate is not None
    assert candidate.kind == "rra"
    assert candidate.publication_date == date(2022, 3, 1)


def test_does_not_promote_generic_analytics_to_rra():
    document = _document("growth-note.pdf", "Benin growth and jobs diagnostic")
    assert identify_uploaded_diagnostic((document,), country="Benin") is None


def test_identifies_explicit_accepted_equivalent():
    document = _document(
        "benin-fcv-risk-assessment.pdf",
        "Benin FCV Risk Assessment\nAccepted equivalent diagnostic\nJune 2024",
    )
    candidate = identify_uploaded_diagnostic((document,), country="Benin")
    assert candidate is not None
    assert candidate.kind == "accepted_equivalent"


def test_keeps_explicit_undated_rra_as_baseline_with_unknown_date():
    document = _document("RRA-Benin.pdf", "Risk and Resilience Assessment: Benin")
    candidate = identify_uploaded_diagnostic((document,), country="Benin")
    assert candidate is not None
    assert candidate.publication_date is None
```

- [ ] **Step 2: Run the new test and verify failure**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_diagnostic_sources.py -q
```

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement a conservative classifier**

Create a frozen value object and deterministic classifier. Require explicit title/cover markers; do not infer an RRA from generic FCV content:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Literal


@dataclass(frozen=True)
class UploadedDiagnostic:
    name: str
    kind: Literal["rra", "accepted_equivalent"]
    publication_date: date | None


RRA_MARKERS = ("risk and resilience assessment", "risk & resilience assessment")
EQUIVALENT_MARKERS = (
    "accepted equivalent diagnostic",
    "fcv risk assessment",
)


def identify_uploaded_diagnostic(documents: tuple, *, country: str) -> UploadedDiagnostic | None:
    matches: list[UploadedDiagnostic] = []
    for document in documents:
        sample = "\n".join(segment.text for segment in document.segments[:3])[:6000]
        searchable = f"{document.name}\n{sample}".casefold()
        is_rra = any(marker in searchable for marker in RRA_MARKERS)
        is_equivalent = any(marker in searchable for marker in EQUIVALENT_MARKERS)
        if not is_rra and not is_equivalent:
            continue
        if country.casefold() not in searchable:
            continue
        matches.append(
            UploadedDiagnostic(
                name=document.name,
                kind="rra" if is_rra else "accepted_equivalent",
                publication_date=_extract_month_year(sample),
            )
        )
    return matches[0] if len(matches) == 1 else None
```

Implement `_extract_month_year()` with explicit English month names and four-digit years. Return `None` for ambiguity rather than guessing.

- [ ] **Step 4: Strengthen source precedence tests**

Add a test to `tests/test_sources.py` proving one current SharePoint original wins over an upload, while multiple current authoritative candidates return `None` for confirmation. Keep this as an interface contract only; do not add SharePoint access.

- [ ] **Step 5: Run focused tests**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_diagnostic_sources.py tests/test_sources.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/diagnostic_sources.py src/cpf_fcv_reviewer/sources.py tests/test_diagnostic_sources.py tests/test_sources.py
git commit -m "feat: identify uploaded RRA baselines"
```

---

### Task 3: Build structured research claims and prompts

**Files:**
- Modify: `src/cpf_fcv_reviewer/public_research.py`
- Modify: `prompts/public_research.md`
- Modify: `tests/test_public_research.py`

- [ ] **Step 1: Write failing structured-output tests**

Extend `CurrentContextClaim` with source and coverage metadata:

```python
def test_current_context_claim_records_source_and_context_kind():
    claim = _claim(
        publisher="World Bank",
        source_title="Benin Country Update",
        context_kind="current_development",
    )
    assert claim.publisher == "World Bank"
    assert claim.context_kind == "current_development"


def test_gateway_requests_json_and_parses_claims(monkeypatch):
    response = '[{"claim_id":"c1","text":"Current evidence.","source_url":"https://worldbank.org/a","source_date":"2026-06-01","publisher":"World Bank","source_title":"Update","source_type":"multilateral report","context_kind":"current_development","relevance":"Updates the RRA baseline.","relationship":"qualifies","licensed_data_required":false}]'
    gateway = _gateway_with_text(monkeypatch, response)
    claims = gateway.search("bounded prompt")
    assert claims[0].publisher == "World Bank"
    assert claims[0].context_kind == "current_development"
```

Use `Literal["structural_dynamic", "current_development", "resilience_factor", "implementation_condition"]` for `context_kind`, add `publisher` and `source_title` as required nonblank fields, and extend `relationship` with `"establishes"` for a sourced no-RRA proposition that is not being compared with an uploaded diagnostic claim.

- [ ] **Step 2: Run focused tests and verify failure**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_public_research.py -q
```

Expected: FAIL on missing fields and raw-string gateway output.

- [ ] **Step 3: Make the gateway return validated claims**

Change the protocol and implementation to return a tuple:

```python
class PublicResearchGateway(Protocol):
    def search(self, prompt: str) -> tuple[CurrentContextClaim, ...]: ...


class AnthropicPublicResearchGateway:
    def __init__(self, api_key: str, model_id: str, *, timeout_seconds: float) -> None:
        self._client = Anthropic(
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=0,
        )
        self._model_id = model_id

    def search(self, prompt: str) -> tuple[CurrentContextClaim, ...]:
        response = self._client.beta.messages.create(
            model=self._model_id,
            max_tokens=5000,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
            messages=[{"role": "user", "content": prompt}],
            betas=["web-search-2025-03-05"],
        )
        raw = "\n".join(
            block.text for block in response.content
            if getattr(block, "type", None) == "text"
        ).strip()
        payload = json.loads(raw)
        if not isinstance(payload, list):
            raise ValueError("Public research must return a JSON array.")
        return tuple(CurrentContextClaim.model_validate(item) for item in payload)
```

- [ ] **Step 4: Replace the research prompt contract**

Require these inputs and behaviors in `prompts/public_research.md`:

```text
Research mode is exactly one of:
- rra_update: treat the named RRA as a historical baseline and focus on the period after its publication date; also test whether material structural findings remain valid.
- holistic: separately assess structural dynamics and material recent developments without describing the result as an RRA.

Prioritize World Bank and other MDB reports, UN reporting, ICG and comparable specialist research, established public analytical products, and trusted media for genuinely recent developments. Use public sources only. Exclude licensed event-level data.
```

List every JSON field, including `publisher`, `source_title`, and `context_kind`.

- [ ] **Step 5: Run focused tests and Ruff**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_public_research.py -q
\.venv\Scripts\python.exe -m ruff check --no-cache src/cpf_fcv_reviewer/public_research.py tests/test_public_research.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/public_research.py prompts/public_research.md tests/test_public_research.py
git commit -m "feat: structure current-country research claims"
```

---

### Task 4: Implement the bounded research controller

**Files:**
- Create: `src/cpf_fcv_reviewer/research_controller.py`
- Create: `tests/test_research_controller.py`
- Modify: `src/cpf_fcv_reviewer/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing controller tests**

Use a scripted fake gateway and no real sleeping:

```python
def test_controller_stops_after_first_sufficient_attempt():
    gateway = ScriptedGateway((_sufficient_claims(),))
    events = []
    result = ResearchController(
        gateway,
        max_attempts=3,
        minimum_claims=4,
        minimum_publishers=2,
        sleep=lambda _: None,
    ).run(_holistic_request(), lambda kind, data: events.append((kind, data)))
    assert gateway.calls == 1
    assert result.sufficient is True
    assert events[-1][0] == "research_sufficient"


def test_controller_uses_targeted_fallback_for_thin_result():
    gateway = ScriptedGateway(((_claim("c1"),), _sufficient_claims()))
    result = ResearchController(
        gateway,
        max_attempts=3,
        minimum_claims=4,
        minimum_publishers=2,
        sleep=lambda _: None,
    ).run(_rra_request(), lambda *_: None)
    assert gateway.calls == 2
    assert "missing coverage" in gateway.prompts[1]
    assert result.sufficient is True


def test_controller_blocks_after_all_attempts_are_insufficient():
    gateway = ScriptedGateway((( _claim("c1"),),) * 3)
    with pytest.raises(InsufficientResearch):
        ResearchController(
            gateway,
            max_attempts=3,
            minimum_claims=4,
            minimum_publishers=2,
            sleep=lambda _: None,
        ).run(_holistic_request(), lambda *_: None)
```

Also test transient exception retry, stop-on-authentication/configuration failure, malformed response, recent-source coverage, publisher diversity, RRA date-window instructions, and safe count-only events.

- [ ] **Step 2: Run the new tests and verify failure**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_research_controller.py tests/test_config.py -q
```

Expected: FAIL because the controller and settings do not exist.

- [ ] **Step 3: Implement request, result, exceptions, and sufficiency**

Create these public types:

```python
class ResearchMode(StrEnum):
    RRA_UPDATE = "rra_update"
    HOLISTIC = "holistic"


@dataclass(frozen=True)
class ResearchRequest:
    country: str
    review_date: date
    mode: ResearchMode
    diagnostic_title: str | None = None
    diagnostic_date: date | None = None
    diagnostic_summary: str = ""


@dataclass(frozen=True)
class ResearchResult:
    claims: tuple[CurrentContextClaim, ...]
    rejected: dict[str, str]
    attempts: int
    sufficient: bool


class ResearchFailure(RuntimeError):
    failure_code = "research_failed"


class ResearchProviderFailure(ResearchFailure):
    failure_code = "research_provider_failed"


class ResearchTimeout(ResearchFailure):
    failure_code = "research_timeout"


class MalformedResearch(ResearchFailure):
    failure_code = "research_malformed"


class ResearchConfigurationError(ResearchFailure):
    failure_code = "research_configuration"


class ResearchSourceRejected(ResearchFailure):
    failure_code = "research_source_rejected"


class InsufficientResearch(ResearchFailure):
    failure_code = "research_insufficient"
```

`ResearchController.run()` must accumulate valid claims by normalized URL and claim ID, calculate missing structural/current/publisher coverage, emit count-only progress, stop when sufficient, and make at most `max_attempts` calls.

- [ ] **Step 4: Add explicit configuration**

Add bounded settings with override support:

```python
"RESEARCH_MAX_ATTEMPTS": int(os.getenv("RESEARCH_MAX_ATTEMPTS", "3")),
"RESEARCH_ATTEMPT_TIMEOUT_SECONDS": float(
    os.getenv("RESEARCH_ATTEMPT_TIMEOUT_SECONDS", "90")
),
"RESEARCH_TOTAL_BUDGET_SECONDS": float(
    os.getenv("RESEARCH_TOTAL_BUDGET_SECONDS", "300")
),
"RESEARCH_MINIMUM_CLAIMS": int(os.getenv("RESEARCH_MINIMUM_CLAIMS", "4")),
"RESEARCH_MINIMUM_PUBLISHERS": int(os.getenv("RESEARCH_MINIMUM_PUBLISHERS", "2")),
```

Validate positive values and ensure the per-attempt timeout does not exceed the total budget.

- [ ] **Step 5: Run focused tests and Ruff**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_research_controller.py tests/test_config.py -q
\.venv\Scripts\python.exe -m ruff check --no-cache src/cpf_fcv_reviewer/research_controller.py src/cpf_fcv_reviewer/config.py tests/test_research_controller.py tests/test_config.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/research_controller.py src/cpf_fcv_reviewer/config.py tests/test_research_controller.py tests/test_config.py
git commit -m "feat: add resilient public research cascade"
```

---

### Task 5: Execute research in the production runtime and evidence pack

**Files:**
- Modify: `src/cpf_fcv_reviewer/runtime.py:71-306`
- Modify: `src/cpf_fcv_reviewer/evidence_builder.py`
- Modify: `src/cpf_fcv_reviewer/orchestrator.py`
- Modify: `tests/test_runtime_wiring.py`
- Modify: `tests/test_end_to_end.py`
- Modify: `tests/test_reproducibility.py`
- Modify: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing production-wiring tests**

Replace gateway-construction-only assertions with behavioral assertions:

```python
def test_runtime_calls_research_and_adds_current_context_evidence(runtime_config):
    research = FakeResearchGateway(_sufficient_claims())
    services = build_runtime_services(
        runtime_config,
        research_gateway=research,
        model_gateway=FakeModelGateway(),
    )
    context = services["orchestrator"].run(_review_context(), lambda *_: None)
    assert research.calls
    current = [
        item for item in context["evidence_pack"].evidence
        if item.evidence_type == "current_context"
    ]
    assert len(current) >= 4
    assert all(item.source_url for item in current)


def test_runtime_uses_rra_update_mode_when_explicit_rra_is_uploaded(runtime_config):
    research = FakeResearchGateway(_sufficient_claims())
    services = build_runtime_services(
        runtime_config,
        research_gateway=research,
        model_gateway=FakeModelGateway(),
    )
    services["orchestrator"].run(_context_with_dated_rra(), lambda *_: None)
    assert "research_mode: rra_update" in research.prompts[0]
    assert "2022-03-01" in research.prompts[0]
```

Add the complementary no-RRA holistic test and a test proving rejected/licensed claims do not enter the evidence pack.

- [ ] **Step 2: Run focused tests and verify failure**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_runtime_wiring.py tests/test_end_to_end.py tests/test_reproducibility.py -q
```

Expected: FAIL because runtime never calls research.

- [ ] **Step 3: Permit dependency injection without changing production defaults**

Use optional keyword-only gateways:

```python
def build_runtime_services(
    config: dict,
    *,
    model_gateway=None,
    research_gateway=None,
) -> dict:
    model_gateway = model_gateway or AnthropicModelGateway(...)
    research_gateway = research_gateway or AnthropicPublicResearchGateway(...)
```

This keeps tests deterministic and avoids monkeypatching SDK construction.

- [ ] **Step 4: Replace the no-op research step**

Add focused runtime functions:

```python
def conduct_public_research(context):
    payload = context["payload"]
    diagnostic = identify_uploaded_diagnostic(
        tuple(context.get("context_documents", ())),
        country=payload["country"],
    )
    request = build_research_request(payload["country"], diagnostic, context)
    result = research_controller.run(request, context["_emit"])
    context["research_result"] = result
    context["uploaded_diagnostic"] = diagnostic
    return context
```

Pass the orchestrator emitter into the context before steps run, or give the research step a closure over an attempt-event emitter. Do not emit source text.

Use the smallest change to the existing orchestrator: assign
`context["_emit"] = emit` before the step loop and remove that private callable
before returning the completed context. Add an orchestrator test proving a step
can emit a safe sub-event and that `_emit` is absent from the returned context.

- [ ] **Step 5: Convert retained claims into evidence**

Before `build_reproducible_evidence_pack`, append:

```python
for index, claim in enumerate(context["research_result"].claims, start=1):
    evidence.append(
        EvidenceItem(
            evidence_id=f"current-{index:03d}",
            evidence_type="current_context",
            text=claim.text,
            confidence="high" if claim.source_type in AUTHORITATIVE_TYPES else "medium",
            source_url=claim.source_url,
        )
    )
```

Also add every approved registry entry to the model-visible evidence pack so
Strategy alignment can be grounded rather than reconstructed:

```python
for entry in bundle.entries:
    evidence.append(
        EvidenceItem(
            evidence_id=f"registry-{entry.entry_id}",
            evidence_type="registry_language",
            text=entry.approved_text,
            confidence="high",
        )
    )
```

Test that the review gateway receives those exact IDs/texts and that no
prohibited term is introduced by application-authored transformations.

Set `DiagnosticMode.RRA_ALIGNMENT` only for a recognized RRA/equivalent; otherwise use `DiagnosticMode.LIMITED_FRAMING`. Include `public_research.md` in `prompt_bytes` so reproducibility metadata covers the research prompt.

- [ ] **Step 6: Run focused tests**

Run the command from Step 2.

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/runtime.py src/cpf_fcv_reviewer/evidence_builder.py src/cpf_fcv_reviewer/orchestrator.py tests/test_runtime_wiring.py tests/test_end_to_end.py tests/test_reproducibility.py tests/test_orchestrator.py
git commit -m "feat: wire current research into CPF reviews"
```

---

### Task 6: Add safe research failures and retry without re-upload

**Files:**
- Modify: `src/cpf_fcv_reviewer/orchestrator.py`
- Modify: `src/cpf_fcv_reviewer/routes.py:133-379`
- Modify: `src/cpf_fcv_reviewer/session_store.py`
- Modify: `tests/test_failure_handling.py`
- Modify: `tests/test_routes.py`
- Modify: `tests/test_session_store.py`

- [ ] **Step 1: Write failing safe-failure tests**

```python
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ResearchTimeout(), "research_timeout"),
        (ResearchProviderFailure(), "research_provider_failed"),
        (MalformedResearch(), "research_malformed"),
        (InsufficientResearch(), "research_insufficient"),
        (ResearchSourceRejected(), "research_source_rejected"),
        (ResearchConfigurationError(), "research_configuration"),
    ],
)
def test_research_failures_have_stable_codes(error, expected):
    assert safe_failure_code(error) == expected
```

Add route tests proving a failed research run preserves uploaded bytes, returns no partial result, allows `POST /api/reviews/<id>/retry-research`, rejects retry for complete/non-research runs, and starts a new run with the same assessment ID.

- [ ] **Step 2: Run focused tests and verify failure**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_failure_handling.py tests/test_routes.py tests/test_session_store.py -q
```

Expected: FAIL on missing failure codes and endpoint.

- [ ] **Step 3: Persist only safe failure state**

In `run_assessment`, store:

```python
failure_code = safe_failure_code(exc)
store().update(
    assessment_id,
    status="failed",
    failure_code=failure_code,
)
```

Do not store exception messages, source text, prompts, or partial review context. Keep the existing safe log fields and add only `failure_code` and elapsed stage metadata.

- [ ] **Step 4: Add the retry route**

```python
RETRYABLE_RESEARCH_CODES = frozenset(
    {
        "research_provider_failed",
        "research_timeout",
        "research_malformed",
        "research_insufficient",
    }
)


@bp.post("/api/reviews/<assessment_id>/retry-research")
def retry_research(assessment_id):
    state = store().get(assessment_id)
    if state.payload.get("failure_code") not in RETRYABLE_RESEARCH_CODES:
        return jsonify(error="Research retry is unavailable."), 409
    store().update(
        assessment_id,
        status="created",
        failure_code=None,
        result=None,
        evidence_by_id=None,
    )
    if current_app.config["START_BACKGROUND_RUNS"]:
        app = current_app._get_current_object()
        Thread(target=run_assessment, args=(app, assessment_id), daemon=True).start()
    base = f"/api/reviews/{assessment_id}"
    return jsonify(event_url=f"{base}/events", result_url=f"{base}/result"), 202
```

When updating optional values, remove stale keys rather than leaving `None` where existing result handlers treat key presence as meaningful. Add a small `VolatileSessionStore.remove_keys()` method under the existing lock and test it.

- [ ] **Step 5: Run focused tests**

Run the command from Step 2.

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/orchestrator.py src/cpf_fcv_reviewer/routes.py src/cpf_fcv_reviewer/session_store.py tests/test_failure_handling.py tests/test_routes.py tests/test_session_store.py
git commit -m "feat: recover safely from research failures"
```

---

### Task 7: Generate and validate the integrated priority-led note

**Files:**
- Modify: `prompts/review.md`
- Modify: `prompts/repair.md`
- Modify: `src/cpf_fcv_reviewer/review_engine.py`
- Modify: `src/cpf_fcv_reviewer/validators.py`
- Modify: `src/cpf_fcv_reviewer/review_profiles.py`
- Modify: `tests/test_prompt_guardrails.py`
- Modify: `tests/test_review_engine.py`
- Modify: `tests/test_validators.py`
- Modify: `tests/fixtures/narrative_review_cases.json`
- Modify: `tests/test_narrative_quality.py`

- [ ] **Step 1: Write failing prompt and validator tests**

Require the exact summary sections and analytical relationships:

```python
def test_review_prompt_requires_integrated_priority_analysis():
    prompt = load_prompt("review")
    for text in (
        "How the draft responds to the RRA, current FCV dynamics, and the FCV Strategy",
        "corroborates, qualifies, contradicts, or supersedes",
        "name an FCV Strategy pillar only when materially relevant",
        "three to five priority areas",
        "alignment_readout",
    ):
        assert text in prompt


def test_priority_requires_current_context_support_when_available(make_valid_result):
    result, evidence = make_valid_result
    evidence["current-001"] = _current_context_evidence("current-001")
    issues = validate_review(result, evidence_ids=set(evidence), prohibited_terms=set())
    assert "missing_current_context_support" in {issue.code for issue in issues}
```

Add a consistency test that every `revision_summary` item resolves to a priority and that `alignment_readout` contains no claim unsupported by at least one selected priority/current-context source. Keep the structural validator deterministic; do not attempt semantic fact-checking in Python.

- [ ] **Step 2: Run focused tests and verify failure**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_prompt_guardrails.py tests/test_review_engine.py tests/test_validators.py tests/test_narrative_quality.py -q
```

Expected: FAIL on absent prompt requirements and field handling.

- [ ] **Step 3: Remove selectable detail from generation while preserving metadata compatibility**

Keep `DetailLevel` for old serialized results, but make new routes use `DetailLevel.IN_DEPTH`. Set the in-depth profile to the approved single output shape:

```python
DETAIL_PROFILES[DetailLevel.IN_DEPTH] = DetailProfile(
    target_pages=3,
    priority_area_range=(3, 5),
)
```

Do not force five priorities when evidence is thin.

- [ ] **Step 4: Rewrite review instructions around the canonical result**

Make `overall_read` the detailed opening, `alignment_readout` the balanced five-minute synthesis, `revision_summary` the concise three-to-five measures, and `priority_areas` the integrated full note. Require every priority to use uploaded-document evidence and, when current evidence is present and relevant, one or more `current_context` evidence IDs.

The prompt must distinguish source-supported fact, interpretation, and uncertainty; it must prohibit treating a web synthesis as an RRA and prohibit naming a Strategy pillar without supplied approved registry support.

- [ ] **Step 5: Update repair and validation**

Add repairable issue codes only for structural omissions that the supplied evidence can repair. Extend the existing literal with these entries:

```python
"missing_alignment_readout",
"missing_current_context_support",
```

The repair prompt must preserve valid priority order and must not invent new sources, Strategy IDs, or locators.

- [ ] **Step 6: Run focused tests and quality fixtures**

Run the command from Step 2.

Expected: PASS, with all deterministic narrative fixtures meeting the existing rubric.

- [ ] **Step 7: Commit**

```powershell
git add -- prompts/review.md prompts/repair.md src/cpf_fcv_reviewer/review_engine.py src/cpf_fcv_reviewer/validators.py src/cpf_fcv_reviewer/review_profiles.py tests/test_prompt_guardrails.py tests/test_review_engine.py tests/test_validators.py tests/fixtures/narrative_review_cases.json tests/test_narrative_quality.py
git commit -m "feat: generate integrated detailed CPF review notes"
```

---

### Task 8: Make DOCX the complete authoritative note

**Files:**
- Modify: `src/cpf_fcv_reviewer/export_docx.py:353-438`
- Modify: `tests/test_docx_export.py`
- Modify: `tests/test_output_parity.py`

- [ ] **Step 1: Write failing DOCX and parity tests**

```python
def test_docx_contains_full_note_and_alignment_synthesis(make_valid_result):
    result, evidence = make_valid_result
    text = _docx_text(build_docx(result, evidence=evidence, hydrated_referrals=()))
    assert "Overall assessment" in text
    assert result.overall_read in text
    assert "How the draft responds to the RRA, current FCV dynamics, and the FCV Strategy" in text
    assert result.alignment_readout in text
    assert "Priority areas for strengthening" in text
    assert result.priority_areas[0].assessment in text


def test_export_uses_detailed_result_not_selected_browser_view(make_valid_result):
    result, evidence = make_valid_result
    text = _docx_text(build_docx(result, evidence=evidence, hydrated_referrals=()))
    assert result.priority_areas[0].why_it_matters in text
    assert result.priority_areas[0].recommended_action in text
```

- [ ] **Step 2: Run focused tests and verify failure**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_docx_export.py tests/test_output_parity.py -q
```

Expected: FAIL because the new alignment section is absent.

- [ ] **Step 3: Update the document order**

Render:

```text
Title and advisory label
Overall assessment
How the draft responds to the RRA, current FCV dynamics, and the FCV Strategy
Priority measures to strengthen the CPF/CEN
Priority areas for strengthening
Limitations and document coverage
Restrained reproducibility metadata
```

Keep evidence source lines under the relevant detailed priority. Do not expose internal evidence IDs.

- [ ] **Step 4: Run focused tests**

Run the command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/export_docx.py tests/test_docx_export.py tests/test_output_parity.py
git commit -m "feat: export the full integrated CPF review note"
```

---

### Task 9: Redesign the intake and progress experience

**Files:**
- Modify: `src/cpf_fcv_reviewer/templates/index.html`
- Modify: `src/cpf_fcv_reviewer/static/styles.css`
- Modify: `src/cpf_fcv_reviewer/static/app.js`
- Modify: `tests/test_frontend_contract.py`
- Modify: `tests/test_task13_frontend_contract.py`

- [ ] **Step 1: Write failing frontend contract tests**

```python
def test_intake_matches_approved_three_box_flow():
    html = HTML.read_text(encoding="utf-8")
    assert "Draft CPF / CEN" in html
    assert "Accompanying CPF package documents" in html
    assert "RRA and supporting analytics" in html
    assert 'id="detail-level"' not in html
    assert "Generate CPF review note" in html


def test_progress_exposes_safe_research_milestones():
    javascript = JS.read_text(encoding="utf-8")
    for event in (
        "research_attempt_started",
        "research_retrying",
        "research_sufficient",
    ):
        assert event in javascript
    assert "data.claim_text" not in javascript
    assert "data.prompt" not in javascript
```

- [ ] **Step 2: Run focused tests and verify failure**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_frontend_contract.py tests/test_task13_frontend_contract.py -q
```

Expected: FAIL on old labels, detail selector, and generic progress.

- [ ] **Step 3: Replace intake markup**

Retain existing form field names for backend compatibility, but use the approved labels and helper prose. Remove the detail selector. Keep review stage and Additional guidance. Change the submit label to **Generate CPF review note**.

Add a three-stage progress component with semantic status text:

```html
<ol id="progress-steps" class="progress-steps" aria-label="Review progress">
  <li data-progress-step="documents">Reading the CPF package</li>
  <li data-progress-step="research">Checking current FCV dynamics</li>
  <li data-progress-step="note">Preparing the review note</li>
</ol>
<p id="progress-message" role="status" aria-live="polite"></p>
```

- [ ] **Step 4: Map backend events to truthful messages**

Use a fixed label map rather than displaying backend strings directly:

```javascript
const progressLabels = {
  extract: "Reading the CPF package",
  resolve_sources: "Establishing the diagnostic baseline",
  research: "Checking current FCV dynamics",
  build_evidence: "Organizing traceable evidence",
  map: "Mapping the RRA and FCV Strategy response",
  review: "Drafting the detailed review note",
  validate: "Checking the note and evidence links",
  render: "Preparing the final readout",
};
```

Research sub-events may show attempt number and retained-count metadata but never source or claim content.

- [ ] **Step 5: Implement screener-aligned responsive styling**

Adapt the approved visual direction using repository-owned CSS: institutional header, navy gradient hero, cyan accents, richer upload cards with Required/Optional badges, clear button hierarchy, and responsive stacking below 760px. Do not copy JavaScript or operational code from FCV-AGENT.

- [ ] **Step 6: Run frontend tests and JavaScript syntax check**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_frontend_contract.py tests/test_task13_frontend_contract.py -q
node --check src/cpf_fcv_reviewer/static/app.js
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/templates/index.html src/cpf_fcv_reviewer/static/styles.css src/cpf_fcv_reviewer/static/app.js tests/test_frontend_contract.py tests/test_task13_frontend_contract.py
git commit -m "feat: redesign the CPF review intake and progress flow"
```

---

### Task 10: Build the dedicated Summary/Detailed results experience

**Files:**
- Modify: `src/cpf_fcv_reviewer/templates/index.html`
- Modify: `src/cpf_fcv_reviewer/static/app.js`
- Modify: `src/cpf_fcv_reviewer/static/styles.css`
- Modify: `tests/test_frontend_contract.py`
- Modify: `tests/test_frontend_accessibility.py`
- Modify: `tests/test_output_parity.py`

- [ ] **Step 1: Write failing results-view tests**

```python
def test_results_have_accessible_summary_and_detailed_tabs():
    html = HTML.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")
    assert 'role="tablist"' in html
    assert "Five-minute readout" in html
    assert "Detailed analysis" in html
    assert "aria-selected" in javascript
    assert "ArrowLeft" in javascript
    assert "ArrowRight" in javascript
    assert 'case "Home"' in javascript
    assert 'case "End"' in javascript


def test_summary_uses_only_canonical_result_fields():
    javascript = JS.read_text(encoding="utf-8")
    assert "result.overall_read" in javascript
    assert "result.alignment_readout" in javascript
    assert "result.revision_summary" in javascript
    assert "fetchSummary" not in javascript
```

Add tests that Detailed analysis renders all priority prose/evidence, Summary is selected first, and export always calls `/export.docx`.

- [ ] **Step 2: Run focused tests and verify failure**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_frontend_contract.py tests/test_frontend_accessibility.py tests/test_output_parity.py -q
```

Expected: FAIL because tabs and dedicated panels are absent.

- [ ] **Step 3: Add dedicated result shell**

Add a result header, action row, tablist, Summary panel, and Detailed panel. Keep corrections below the detailed result but available from either view. The intake section remains hidden after completion so the result behaves as a separate page.

- [ ] **Step 4: Split rendering without duplicating analysis**

Create:

```javascript
function renderFiveMinuteReadout(result) {
  const fragment = document.createDocumentFragment();
  fragment.append(
    text("p", "Five-minute readout", "read-time"),
    text("h2", "Overall assessment"),
    text("p", result.overall_read, "overall-read"),
    text("h2", "How the draft responds to the RRA, current FCV dynamics, and the FCV Strategy"),
    text("p", result.alignment_readout, "alignment-readout"),
    text("h2", "Priority measures to strengthen the CPF / CEN"),
    renderRevisionSummary(result),
  );
  return fragment;
}


function renderDetailedAnalysis(result) {
  const fragment = document.createDocumentFragment();
  fragment.append(text("h2", "Overall assessment"));
  fragment.append(text("p", result.overall_read, "overall-read"));
  fragment.append(renderPriorityAreas(result));
  fragment.append(renderCoverage(result));
  return fragment;
}
```

Continue using `textContent` and DOM methods only. Do not introduce `innerHTML` for model or source content.

- [ ] **Step 5: Implement accessible view state**

`setResultView("summary" | "detailed")` updates `aria-selected`, roving `tabindex`, panel `hidden` state, and active styling. `handleResultTabKeydown` supports ArrowLeft, ArrowRight, Home, and End. View changes make no network request.

- [ ] **Step 6: Run focused tests and syntax check**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_frontend_contract.py tests/test_frontend_accessibility.py tests/test_output_parity.py -q
node --check src/cpf_fcv_reviewer/static/app.js
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/templates/index.html src/cpf_fcv_reviewer/static/app.js src/cpf_fcv_reviewer/static/styles.css tests/test_frontend_contract.py tests/test_frontend_accessibility.py tests/test_output_parity.py
git commit -m "feat: add summary and detailed CPF result views"
```

---

### Task 11: Add browser-side research recovery

**Files:**
- Modify: `src/cpf_fcv_reviewer/templates/index.html`
- Modify: `src/cpf_fcv_reviewer/static/app.js`
- Modify: `src/cpf_fcv_reviewer/static/styles.css`
- Modify: `tests/test_frontend_contract.py`
- Modify: `tests/test_frontend_accessibility.py`
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Write failing recovery tests**

```python
def test_research_failure_offers_retry_without_reupload():
    javascript = JS.read_text(encoding="utf-8")
    assert 'id="retry-research"' in HTML.read_text(encoding="utf-8")
    assert "research_insufficient" in javascript
    assert "research_timeout" in javascript
    assert "retry-research" in javascript
    assert "new FormData(form)" not in _retry_handler(javascript)
```

Add accessibility checks for focus moving to the recovery heading and the retry button being hidden for non-research failures.

- [ ] **Step 2: Run focused tests and verify failure**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_frontend_contract.py tests/test_frontend_accessibility.py tests/test_routes.py -q
```

Expected: FAIL because the retry control is absent.

- [ ] **Step 3: Implement the retry interaction**

For retryable codes, show a clear last-resort message and **Retry research**. POST to `/api/reviews/${assessmentId}/retry-research`, then reconnect to returned event/result URLs. Do not reconstruct or resend uploaded files.

Disable the button while the retry request is in flight, guard it with the existing operation epoch, and preserve **Start a new review** as the alternative.

- [ ] **Step 4: Run focused tests and syntax check**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_frontend_contract.py tests/test_frontend_accessibility.py tests/test_routes.py -q
node --check src/cpf_fcv_reviewer/static/app.js
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/templates/index.html src/cpf_fcv_reviewer/static/app.js src/cpf_fcv_reviewer/static/styles.css tests/test_frontend_contract.py tests/test_frontend_accessibility.py tests/test_routes.py
git commit -m "feat: retry blocked CPF research without reupload"
```

---

### Task 12: Run integrated verification and local browser QA

**Files:**
- Modify only if failures require focused fixes in files already named above.
- Create: `docs/validation/2026-08-13-cpf-output-research-ui-validation.md`

- [ ] **Step 1: Run the focused integration group**

```powershell
\.venv\Scripts\python.exe -m pytest tests/test_public_research.py tests/test_research_controller.py tests/test_diagnostic_sources.py tests/test_runtime_wiring.py tests/test_routes.py tests/test_review_engine.py tests/test_validators.py tests/test_docx_export.py tests/test_output_parity.py tests/test_frontend_contract.py tests/test_frontend_accessibility.py -q
```

Expected: PASS.

- [ ] **Step 2: Run static checks**

```powershell
\.venv\Scripts\python.exe -m ruff check --no-cache src tests
node --check src/cpf_fcv_reviewer/static/app.js
git diff --check
```

Expected: all commands exit 0. Existing inaccessible pytest artifact directories may emit warnings but must not be modified or committed.

- [ ] **Step 3: Run the full suite once**

```powershell
\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp "C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\20260813_output_research_ui_tests"
```

Expected: all tests pass. Do not rerun a successful full suite without a concrete reason.

- [ ] **Step 4: Run deterministic browser QA**

Start the local test server with deterministic research/model adapters and test at 1280px and 390px:

1. Three approved upload cards and no detail selector.
2. Country detection and stage selection.
3. Safe research progress and retry state.
4. Successful transition to a distinct results page.
5. Summary selected by default.
6. Detailed note contains all priority prose and evidence disclosures.
7. Tab keyboard behavior.
8. Correction rerun, reset, and full-note download.
9. No horizontal overflow or browser console errors.

Capture screenshots in a dated validation-only directory that remains uncommitted unless repository instructions explicitly require them.

- [ ] **Step 5: Render and inspect the DOCX**

Use the documents skill runtime and `render_docx.py` to inspect every page. Confirm heading hierarchy, page breaks, evidence lines, and absence of clipped or orphaned content. If the required renderer is unavailable, record that limitation rather than claiming visual verification.

- [ ] **Step 6: Write the local validation record**

Record exact commands, pass counts, browser sizes, deterministic fixture limitations, DOCX status, and any unresolved constraints. Do not include document text, source claims, secrets, or generated sensitive prose.

- [ ] **Step 7: Commit verified local implementation and validation**

```powershell
git add -- docs/validation/2026-08-13-cpf-output-research-ui-validation.md
git commit -m "docs: validate CPF output and research redesign"
```

Confirm each implementation fix was committed with its owning task before this documentation-only commit.

---

### Task 13: Run approved-material Benin and Render acceptance

**Files:**
- Modify: `docs/validation/2026-08-13-cpf-output-research-ui-validation.md`
- Modify: `docs/PROJECT_STATUS.md`
- Modify: `README.md`

- [ ] **Step 1: Confirm prerequisites without exposing values**

Verify only presence/status for `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL_ID`, `REGISTRY_BUNDLE_PATH`, and `REGISTRY_BUNDLE_SHA256`. Confirm the Benin CPF/package is approved for the intended local or Render test. Do not print secret values or restricted document content.

- [ ] **Step 2: Run the approved Benin assessment locally**

Use the real configured research and review path. Verify that research actually runs, the result contains current-context evidence, the five-minute readout reflects the detailed priorities, and the detailed note meets the approved rubric. Paste the final text to the user only when requested and permitted.

- [ ] **Step 3: Score the detailed note**

Apply the existing 0-2 rubric for overall judgment, country/CPF specificity, dated RRA handling, current structural/recent dynamics, Strategy alignment, prioritization, actionability, target precision, stage realism, evidence fidelity, and narrative coherence.

Expected: average at least 1.5/2 and no zero on a material criterion. If it misses the threshold, return to the smallest owning prompt/contract task and retest; do not polish the UI to mask output failure.

- [ ] **Step 4: Request deployment authorization at the action boundary**

Before pushing, opening a PR, changing Render configuration, or deploying, show the exact branch, commits, service, and intended test inputs. Proceed only after explicit authorization.

- [ ] **Step 5: Test the deployed Render service in the browser**

Run the approved Benin review through the deployed UI. Inspect:

- intake and upload behavior;
- progress and keepalives;
- research retry/fallback behavior;
- Summary and Detailed tabs;
- downloaded full DOCX;
- correction and reset flows;
- desktop and mobile layouts; and
- browser console/network failures.

- [ ] **Step 6: Inspect Render logs safely**

Confirm logs contain stage names, attempt counts, durations, retained/rejected counts, retry categories, and terminal status. Confirm they do not contain API keys, prompts, filenames, uploaded text, source extracts, claim text, or generated note prose.

- [ ] **Step 7: Update user-facing documentation**

Document the public/ITS boundary, mandatory research behavior, optional public RRA upload, future SharePoint adapter, full-note download behavior, deployment release identifier, and validation outcomes. Preserve the non-production advisory language.

- [ ] **Step 8: Run final verification once and commit docs**

```powershell
\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp "C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\cpf_screener\20260813_final_acceptance_tests"
\.venv\Scripts\python.exe -m ruff check --no-cache src tests
node --check src/cpf_fcv_reviewer/static/app.js
git diff --check
git status --short --branch
```

Expected: all checks pass and only intentional files are staged.

```powershell
git add -- README.md docs/PROJECT_STATUS.md docs/validation/2026-08-13-cpf-output-research-ui-validation.md
git commit -m "docs: record CPF reviewer acceptance results"
```

---

## Final review checklist

- [ ] Inspect every commit and the full branch diff against the approved design.
- [ ] Confirm mandatory research is executed by the production runtime, not only a synthetic orchestrator.
- [ ] Confirm an RRA updates the research window but never suppresses current-country research.
- [ ] Confirm no-RRA mode covers both structural and current dynamics without claiming RRA alignment.
- [ ] Confirm research blocks only after the bounded cascade.
- [ ] Confirm retry reuses retained volatile uploads and does not expose partial output.
- [ ] Confirm the five-minute readout and DOCX derive from the same canonical detailed result.
- [ ] Confirm FCV Strategy pillars are named only with approved support and explained in plain language.
- [ ] Confirm the detailed note is priority-led, integrated, and normally three pages when evidence supports it.
- [ ] Confirm no code, corpus, or deployment path in the stable FCV Project Screener changed.
- [ ] Confirm public Render and future ITS source boundaries remain explicit.
- [ ] Confirm browser, DOCX, approved Benin, and Render-log evidence is recorded before claiming completion.
