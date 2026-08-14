# Research Resilience and Guided Journey Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make valid CPF/CEN reviews complete through malformed or thin live research while presenting a dedicated, accessible, stage-aware guided journey.

**Architecture:** Split Anthropic research into cited search and structured normalization, then recover through citation salvage and fixed-host institutional adapters. Replace the binary sufficiency gate with explicit full, reduced, and document-led tiers that propagate into immutable metadata, limitations, browser output, DOCX output, and safe telemetry. Add an explicitly local deterministic smoke service and enhance the existing single-page application with a full-page progress state, timer, stage rail, and rotating guidance cards.

**Tech Stack:** Python 3.13, Flask, Pydantic 2, Anthropic Python SDK, httpx, vanilla JavaScript, HTML/CSS, pytest, Ruff, Node syntax checks, python-docx, in-app browser testing.

---

## File structure

- Modify `src/cpf_fcv_reviewer/public_research.py`: provider response models, mixed-block extraction, structured normalization, and citation-preserving salvage.
- Create `src/cpf_fcv_reviewer/curated_research.py`: fixed-host World Bank recovery and optional approved-app ReliefWeb recovery plus bounded HTTP client.
- Modify `src/cpf_fcv_reviewer/research_controller.py`: recovery orchestration and evidence-tier decisions.
- Modify `src/cpf_fcv_reviewer/contracts.py`: immutable evidence-tier metadata.
- Modify `src/cpf_fcv_reviewer/reproducibility.py`: build evidence-tier metadata.
- Modify `src/cpf_fcv_reviewer/evidence_builder.py`: pass evidence-tier metadata into the evidence pack.
- Modify `src/cpf_fcv_reviewer/runtime.py`: wire recovery, document-led eligibility, limitations, and safe events.
- Modify `src/cpf_fcv_reviewer/config.py`: bounded recovery and smoke configuration.
- Create `src/cpf_fcv_reviewer/smoke.py`: deterministic no-provider research and review gateways.
- Create `scripts/run_smoke.py`: project-relative local smoke launcher.
- Modify `src/cpf_fcv_reviewer/templates/index.html`: dedicated guided-journey markup and evidence-status result region.
- Modify `src/cpf_fcv_reviewer/static/app.js`: stage state, elapsed/remaining timer, rotating cards, recovery status, and result evidence badge.
- Modify `src/cpf_fcv_reviewer/static/styles.css`: desktop/mobile guided-journey presentation and reduced motion.
- Modify `src/cpf_fcv_reviewer/export_docx.py`: evidence-status wording in exported notes and reproducibility metadata.
- Modify focused tests under `tests/`; create `tests/test_curated_research.py` and `tests/test_smoke_mode.py`.
- Create `docs/validation/2026-08-14-research-resilience-guided-journey-validation.md`: fresh verification record.
- Update `docs/PROJECT_STATUS.md` without replacing or staging unrelated pre-existing edits.

### Task 1: Parse cited search responses and normalize in a second call

**Files:**
- Modify: `src/cpf_fcv_reviewer/public_research.py`
- Test: `tests/test_public_research.py`

- [ ] **Step 1: Write failing mixed-content and structured-normalization tests**

Add fakes that return a preamble text block, `server_tool_use`, `web_search_tool_result`, and a final cited text block. Assert that only the final cited narrative is supplied to `messages.parse`, that the parsed `ResearchClaimBatch` is returned, and that a `pause_turn` response is continued once.

```python
def test_gateway_uses_final_cited_text_then_structured_normalization():
    gateway, search_client, parse_client = gateway_with_mixed_blocks()
    claims = gateway.search("country: Benin")
    assert claims[0].publisher == "World Bank"
    normalization_payload = json.loads(parse_client.calls[0]["messages"][0]["content"])
    assert normalization_payload["narrative"] == "Benin cited synthesis."
    assert normalization_payload["sources"][0]["url"] == "https://www.worldbank.org/benin"
    assert "Searching" not in normalization_payload["narrative"]


def test_gateway_continues_pause_turn_without_losing_search_results():
    gateway, search_client, _ = gateway_with_pause_turn()
    assert gateway.search("country: Benin")
    assert len(search_client.calls) == 2
```

- [ ] **Step 2: Run the tests and confirm the existing JSON concatenation fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_public_research.py -k "final_cited or pause_turn" -q`

Expected: FAIL because the gateway currently concatenates all text and calls `json.loads` once.

- [ ] **Step 3: Add provider-neutral models and two-pass gateway code**

Implement frozen Pydantic models and keep `PublicResearchGateway.search()` returning the existing claim tuple.

```python
class ResearchSource(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    title: str
    url: str
    published_at: date | None = None


class SearchArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    narrative: str
    sources: tuple[ResearchSource, ...]


class ResearchClaimBatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    claims: tuple[CurrentContextClaim, ...]
```

Add `_extract_search_artifact(response)`, `_continue_pause_turn(response, prompt)`, and `_normalize(artifact)`. The search system prompt must request a concise cited synthesis, not JSON. `_normalize` must call `self._client.messages.parse` without tools, with `output_format=ResearchClaimBatch`, and reject a missing `parsed_output`.

- [ ] **Step 4: Add conservative citation salvage tests and implementation**

```python
def test_gateway_salvages_grounded_claim_when_normalization_is_malformed():
    gateway, _, _ = gateway_with_invalid_parsed_output()
    claims = gateway.search("country: Benin")
    assert [(claim.publisher, claim.relationship) for claim in claims] == [
        ("World Bank", "establishes")
    ]
```

Implement `_salvage_claims(artifact)` so it emits claims only for source-associated sentences, uses stable `sha256`-derived IDs, never invents a date, and rejects undated sources rather than assigning the review date.

Extend source-policy tests so licensed claims, blogs, social-media URLs, user-generated sources, and non-institutional publishers are rejected. The permitted hierarchy is encoded as a small publisher/source-type allowlist covering World Bank, UN entities, OECD, IMF, regional development banks, ICRC, IOM, and ReliefWeb; unknown sources cannot enable `FULL` or `REDUCED` status.

- [ ] **Step 5: Run focused tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_public_research.py -q`

Expected: all public-research tests pass.

- [ ] **Step 6: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/public_research.py tests/test_public_research.py
git commit -m "fix: normalize cited research responses"
```

### Task 2: Add bounded institutional recovery adapters

**Files:**
- Create: `src/cpf_fcv_reviewer/curated_research.py`
- Create: `tests/test_curated_research.py`
- Modify: `src/cpf_fcv_reviewer/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing adapter security and partial-failure tests**

```python
def test_curated_gateway_combines_world_bank_and_approved_reliefweb_claims(fake_http):
    gateway = CuratedResearchGateway(
        client=fake_http,
        reliefweb_app_name="cpf-fcv-reviewer",
    )
    claims = gateway.search(ResearchRequest(country="Benin", review_date=date(2026, 8, 14), mode=ResearchMode.HOLISTIC))
    assert {claim.publisher for claim in claims} == {"World Bank", "ReliefWeb"}


def test_curated_gateway_keeps_world_bank_when_reliefweb_is_not_configured(fake_http):
    gateway = CuratedResearchGateway(client=fake_http, reliefweb_app_name=None)
    claims = gateway.search(benin_request())
    assert claims and {claim.publisher for claim in claims} == {"World Bank"}


def test_curated_gateway_keeps_other_adapter_when_one_times_out(fake_http):
    fake_http.fail_host("api.worldbank.org", httpx.ReadTimeout("timeout"))
    claims = CuratedResearchGateway(client=fake_http).search(benin_request())
    assert claims and {claim.publisher for claim in claims} == {"ReliefWeb"}


@pytest.mark.parametrize("url", ["http://127.0.0.1/x", "https://evil.example/x"])
def test_bounded_client_rejects_non_allowlisted_hosts(url):
    with pytest.raises(ValueError, match="allowlisted"):
        BoundedInstitutionalClient().get_json(url)
```

- [ ] **Step 2: Run tests and verify the module is absent**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_curated_research.py -q`

Expected: collection fails with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the bounded client and two adapters**

Use only these hosts initially. `BoundedInstitutionalClient.__init__` validates its numeric limits; `get_json` parses the URL, requires HTTPS and an exact allowlisted host, performs an `httpx.Client.stream` request, rejects non-JSON content, stops once `max_bytes` is exceeded, and returns `response.json()`.

```python
ALLOWED_HOSTS = frozenset({"api.worldbank.org", "api.reliefweb.int"})


class BoundedInstitutionalClient:
    def __init__(self, *, timeout_seconds: float = 8.0, max_bytes: int = 500_000):
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes


class CuratedResearchGateway:
    def search(self, request: ResearchRequest) -> tuple[CurrentContextClaim, ...]:
        claims: list[CurrentContextClaim] = []
        for adapter in (self._world_bank, self._reliefweb):
            try:
                claims.extend(adapter(request))
            except (httpx.HTTPError, ValueError, KeyError, TypeError):
                continue
        return tuple(claims)
```

Resolve the country through the World Bank country endpoint, cache that public mapping in memory, and call `https://api.worldbank.org/v2/country/{iso3}/indicator/{indicator}?format=json&per_page=5`. ReliefWeb uses the current `https://api.reliefweb.int/v2/reports` endpoint, includes the configured pre-approved `appname`, and applies country, date, and institutional-source filters. If `RELIEFWEB_APP_NAME` is blank, skip ReliefWeb without failing recovery. Map only explicit response fields into claims and pass every output through `retain_public_claims` later in the controller.

- [ ] **Step 4: Add validated recovery settings**

Add `RESEARCH_RECOVERY_TIMEOUT_SECONDS=8.0`, `RESEARCH_RECOVERY_MAX_BYTES=500000`, and optional trimmed `RELIEFWEB_APP_NAME`. Reject booleans, non-finite values, non-positive timeouts, and byte limits outside `10_000..2_000_000`.

- [ ] **Step 5: Run focused tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_curated_research.py tests/test_config.py -q`

Expected: all tests pass with no network access.

- [ ] **Step 6: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/curated_research.py src/cpf_fcv_reviewer/config.py tests/test_curated_research.py tests/test_config.py
git commit -m "feat: add curated public research recovery"
```

### Task 3: Replace binary research sufficiency with explicit evidence tiers

**Files:**
- Modify: `src/cpf_fcv_reviewer/contracts.py`
- Modify: `src/cpf_fcv_reviewer/research_controller.py`
- Test: `tests/test_contracts.py`
- Test: `tests/test_research_controller.py`

- [ ] **Step 1: Write failing tier and recovery tests**

```python
def test_full_evidence_returns_full_tier():
    result = controller(primary=sufficient_claims()).run(request(), emit)
    assert result.tier is CurrentEvidenceTier.FULL
    assert result.limitation is None


def test_thin_independent_evidence_completes_as_reduced():
    result = controller(primary=(claim("one"),)).run(request(), emit)
    assert result.tier is CurrentEvidenceTier.REDUCED
    assert "one public source" in result.limitation


def test_provider_failure_uses_curated_recovery():
    result = controller(primary=TimeoutError(), recovery=(claim("fallback"),)).run(request(), emit)
    assert result.claims[0].claim_id == "fallback"
    assert emitted("research_curated_recovery")


def test_no_independent_claims_returns_document_led_when_allowed():
    result = controller(primary=TimeoutError(), recovery=(), allow_document_led=True).run(request(), emit)
    assert result.tier is CurrentEvidenceTier.DOCUMENT_LED
    assert result.claims == ()
```

- [ ] **Step 2: Run the tests and verify they fail against the hard gate**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_research_controller.py -k "tier or curated or document_led" -q`

Expected: FAIL because `EvidenceTier`, recovery, and document-led completion do not exist.

- [ ] **Step 3: Implement tier contracts and bounded recovery**

```python
class CurrentEvidenceTier(StrEnum):
    FULL = "full"
    REDUCED = "reduced"
    DOCUMENT_LED = "document_led"


@dataclass(frozen=True)
class ResearchResult:
    claims: tuple[CurrentContextClaim, ...]
    rejected: dict[str, str]
    attempts: int
    tier: CurrentEvidenceTier
    limitation: str | None = None
```

Define `CurrentEvidenceTier` in `contracts.py` so metadata and controller results share one enum. Extend `ResearchController` with `recovery_gateway` and change `run` to `run(request, emit, *, allow_document_led=False)`. After primary retries, call recovery once and merge/deduplicate accepted claims. Return `FULL` when `_missing_coverage` is empty; return `REDUCED` when at least one recent permitted public claim exists; return `DOCUMENT_LED` only when `allow_document_led=True`; otherwise preserve `ResearchSourceRejected` or `InsufficientResearch`. Apply a deterministic injected jitter function to each configured backoff and cap the delay to the remaining total budget, so tests can pass `jitter=lambda delay: delay` while production uses a narrow random range.

Emit only allowlisted counters and labels:

```python
emit("research_curated_recovery", {"accepted_count": len(accepted)})
emit("research_reduced", {"missing_coverage": missing})
emit("research_document_led", {"reason": "independent_evidence_unavailable"})
```

Log one stable server-side code for each terminal research route—`research_primary`, `research_salvaged`, `research_curated_recovery`, `research_reduced`, or `research_document_led`—with duration and counts only. Never log prompts, provider payloads, document names/text, claim text, or URLs.

- [ ] **Step 4: Preserve strict blocking cases**

Add tests that configuration errors still fail immediately, rejected private/licensed sources cannot enable reduced mode, and `allow_document_led=False` still raises.

- [ ] **Step 5: Run controller and failure tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_research_controller.py tests/test_failure_handling.py tests/test_session_store.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/contracts.py src/cpf_fcv_reviewer/research_controller.py tests/test_contracts.py tests/test_research_controller.py tests/test_failure_handling.py tests/test_session_store.py
git commit -m "feat: grade current evidence sufficiency"
```

### Task 4: Propagate evidence status into metadata, limitations, browser JSON, and DOCX

**Files:**
- Modify: `src/cpf_fcv_reviewer/contracts.py`
- Modify: `src/cpf_fcv_reviewer/reproducibility.py`
- Modify: `src/cpf_fcv_reviewer/evidence_builder.py`
- Modify: `src/cpf_fcv_reviewer/runtime.py`
- Modify: `src/cpf_fcv_reviewer/export_docx.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_contracts.py`
- Test: `tests/test_reproducibility.py`
- Test: `tests/test_runtime_wiring.py`
- Test: `tests/test_docx_export.py`
- Test: `tests/test_output_parity.py`

- [ ] **Step 1: Write failing metadata and output-parity tests**

```python
def test_run_metadata_records_evidence_tier_and_limitation(make_valid_result):
    result, _ = make_valid_result
    assert result.metadata.current_evidence_tier == "full"
    assert result.metadata.current_evidence_limitation is None


def test_document_led_status_is_visible_in_docx(make_valid_result):
    result, evidence = document_led_result(make_valid_result)
    text = docx_text(build_docx(result, evidence=evidence, hydrated_referrals=()))
    assert "Review based primarily on submitted documents" in text
    assert result.metadata.current_evidence_limitation in text
```

- [ ] **Step 2: Run focused tests and verify missing fields**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_contracts.py tests/test_reproducibility.py tests/test_runtime_wiring.py tests/test_docx_export.py tests/test_output_parity.py -q`

Expected: FAIL on absent evidence-status metadata.

- [ ] **Step 3: Add immutable metadata fields and builder parameters**

```python
class RunMetadata(FrozenModel):
    current_evidence_tier: CurrentEvidenceTier = CurrentEvidenceTier.FULL
    current_evidence_limitation: str | None = None
```

Add a validator requiring a nonblank limitation for `REDUCED` and `DOCUMENT_LED`, and requiring `None` for `FULL`. Thread both values through `build_run_metadata` and `build_reproducible_evidence_pack`.

- [ ] **Step 4: Make runtime choose document-led mode only from usable uploaded context**

Before calling the controller, compute `allow_document_led` from readable primary/context evidence and pass it explicitly. After research, append `research_result.limitation` to evidence-pack warnings and ensure it is included exactly once in the final `ReviewResult.limitations`, including after repair. Do not convert an uploaded RRA into a current-context evidence item.

- [ ] **Step 5: Render evidence status consistently**

Add a DOCX paragraph immediately before limitations using exactly one of:

```python
EVIDENCE_STATUS_LABELS = {
    CurrentEvidenceTier.FULL: "Current evidence established",
    CurrentEvidenceTier.REDUCED: "Current evidence partially established",
    CurrentEvidenceTier.DOCUMENT_LED: "Review based primarily on submitted documents",
}
```

Include the tier and limitation in reproducibility metadata. The JSON result route needs no bespoke serializer because it already dumps `ReviewResult`.

- [ ] **Step 6: Run focused tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_contracts.py tests/test_reproducibility.py tests/test_runtime_wiring.py tests/test_docx_export.py tests/test_output_parity.py -q`

Expected: all tests pass.

- [ ] **Step 7: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/contracts.py src/cpf_fcv_reviewer/reproducibility.py src/cpf_fcv_reviewer/evidence_builder.py src/cpf_fcv_reviewer/runtime.py src/cpf_fcv_reviewer/export_docx.py tests/conftest.py tests/test_contracts.py tests/test_reproducibility.py tests/test_runtime_wiring.py tests/test_docx_export.py tests/test_output_parity.py
git commit -m "feat: disclose current evidence status"
```

### Task 5: Add explicit provider-free smoke mode

**Files:**
- Create: `src/cpf_fcv_reviewer/smoke.py`
- Create: `scripts/run_smoke.py`
- Create: `tests/test_smoke_mode.py`
- Modify: `src/cpf_fcv_reviewer/app.py`
- Modify: `src/cpf_fcv_reviewer/config.py`
- Test: `tests/test_app_factory.py`

- [ ] **Step 1: Write failing smoke-mode safety and end-to-end tests**

```python
def test_smoke_mode_is_rejected_with_production_environment():
    with pytest.raises(RuntimeError, match="development only"):
        build_config({"SMOKE_MODE": True, "APP_ENV": "production"})


def test_smoke_app_completes_without_anthropic_key(tmp_path):
    app = create_smoke_app(start_background_runs=False)
    response = submit_synthetic_benin_review(app.test_client())
    run_assessment(app, response.json["assessment_id"])
    result = app.test_client().get(response.json["result_url"]).get_json()
    assert result["metadata"]["model_id"] == "deterministic-smoke"
    assert result["metadata"]["current_evidence_tier"] == "full"
```

- [ ] **Step 2: Run tests and verify smoke services are absent**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_smoke_mode.py tests/test_app_factory.py -q`

Expected: FAIL because `create_smoke_app` does not exist.

- [ ] **Step 3: Implement deterministic gateways and launcher**

`SmokeResearchGateway.search()` returns four dated, public synthetic claims across two publishers and required context kinds. `SmokeModelGateway.generate()` returns a schema-valid `ReviewDraft` derived only from evidence IDs in the supplied payload. Neither gateway imports or instantiates Anthropic.

```python
def create_smoke_app(*, start_background_runs: bool = True):
    root = Path(__file__).parents[2]
    registry = root / "tests" / "fixtures" / "registry_bundle.synthetic.json"
    config = {
        "APP_ENV": "development",
        "SMOKE_MODE": True,
        "START_BACKGROUND_RUNS": start_background_runs,
        "REGISTRY_BUNDLE_PATH": str(registry),
        "REGISTRY_BUNDLE_SHA256": sha256(registry.read_bytes()).hexdigest(),
        "ALLOW_SYNTHETIC_REGISTRY": True,
        "ANTHROPIC_API_KEY": "",
    }
    return create_app(config, services=build_smoke_services(config))
```

`scripts/run_smoke.py` calls `create_smoke_app().run(host="127.0.0.1", port=58422, debug=False)`. Config must permit smoke mode only with `APP_ENV=development`; normal non-test startup still requires an API key.

- [ ] **Step 4: Run smoke tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_smoke_mode.py tests/test_app_factory.py tests/test_end_to_end.py -q`

Expected: all tests pass and no external request is made.

- [ ] **Step 5: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/smoke.py scripts/run_smoke.py src/cpf_fcv_reviewer/app.py src/cpf_fcv_reviewer/config.py tests/test_smoke_mode.py tests/test_app_factory.py
git commit -m "feat: add deterministic browser smoke mode"
```

### Task 6: Build the Option A guided journey

**Files:**
- Modify: `src/cpf_fcv_reviewer/templates/index.html`
- Modify: `src/cpf_fcv_reviewer/static/app.js`
- Modify: `src/cpf_fcv_reviewer/static/styles.css`
- Test: `tests/test_frontend_contract.py`
- Test: `tests/test_frontend_accessibility.py`
- Test: `tests/test_task13_frontend_contract.py`

- [ ] **Step 1: Write failing markup, state, timer, and privacy contract tests**

Assert the progress section has `progress-kicker`, `elapsed-time`, `remaining-time`, three stages with status slots, `while-we-work`, and an evidence-status result region. Assert JavaScript uses safe static maps, `performance.now()`, interval cleanup, `matchMedia("(prefers-reduced-motion: reduce)")`, and no interpolation of event payload values other than allowlisted stage names/count-free labels.

```python
def test_guided_journey_has_stage_timing_and_rotating_guidance():
    html = HTML.read_text(encoding="utf-8")
    for fragment in ('id="elapsed-time"', 'id="remaining-time"', 'id="while-we-work"'):
        assert fragment in html
    assert html.count('data-progress-step="') == 3


def test_progress_events_never_render_backend_payload_text():
    javascript = JS.read_text(encoding="utf-8")
    for unsafe in ("data.claim", "data.source", "data.prompt", "data.reason", "data.missing_coverage"):
        assert unsafe not in javascript
```

- [ ] **Step 2: Run frontend tests and verify the new journey contract fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_frontend_contract.py tests/test_frontend_accessibility.py tests/test_task13_frontend_contract.py -q`

Expected: FAIL on absent timing, cards, and evidence-status elements.

- [ ] **Step 3: Replace the progress markup with the approved three-stage journey**

Use these user-facing labels:

```html
<p id="progress-kicker">Building your FCV review</p>
<p><span id="elapsed-time">0:00 elapsed</span><span id="remaining-time">About 4–7 minutes remaining</span></p>
<ol id="progress-steps" aria-label="Review progress">
  <li data-progress-step="documents">Reading documents</li>
  <li data-progress-step="research">Establishing current country evidence</li>
  <li data-progress-step="note">Drafting and validating the review</li>
</ol>
<aside id="while-we-work" aria-live="off"><h2>While we work</h2><p id="guidance-card"></p></aside>
```

- [ ] **Step 4: Implement stage-aware timing and safe progress state**

Use static stage ranges and static labels:

```javascript
const stageEstimates = { documents: [45, 120], research: [90, 300], note: [90, 240] };
const guidanceCards = [
  "Strong FCV reviews connect context, design choices, delivery arrangements, and results.",
  "A useful recommendation identifies both the change and where it belongs in the draft.",
  "Uploaded diagnostics and independently retrieved evidence remain clearly separated.",
];
```

Implement `startJourneyClock`, `updateJourneyClock`, `stopJourneyClock`, and `rotateGuidanceCard`. `showProgress()` starts and resets them; result, failure, reset, and superseded-operation paths stop them. Mark earlier stages `is-complete`, the current stage `is-active`, and later stages pending.

Keep the existing return/reset behavior as the cancellation boundary: closing the active `EventSource` and deleting the volatile assessment stops client monitoring and removes the session. Do not add a misleading server-cancellation control while the background provider call cannot be interrupted safely.

- [ ] **Step 5: Add result evidence-status rendering**

Map only metadata enum values to static labels:

```javascript
const evidenceStatusLabels = {
  full: "Current evidence established",
  reduced: "Current evidence partially established",
  document_led: "Review based primarily on submitted documents",
};
```

Render the label and the server-validated limitation from result metadata. This is final result content, not an SSE payload.

- [ ] **Step 6: Implement responsive and reduced-motion CSS**

Create a full-viewport progress surface within the existing header/footer shell, a horizontal desktop rail, stacked mobile cards at `max-width: 760px`, visible focus states, and:

```css
@media (prefers-reduced-motion: reduce) {
  .progress-stage, .progress-stage::before, .guidance-card { animation: none; transition: none; }
}
```

- [ ] **Step 7: Run frontend and JavaScript checks**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_frontend_contract.py tests/test_frontend_accessibility.py tests/test_task13_frontend_contract.py -q`

Run: `node --check src/cpf_fcv_reviewer/static/app.js`

Expected: all tests pass; Node exits 0.

- [ ] **Step 8: Commit**

```powershell
git add -- src/cpf_fcv_reviewer/templates/index.html src/cpf_fcv_reviewer/static/app.js src/cpf_fcv_reviewer/static/styles.css tests/test_frontend_contract.py tests/test_frontend_accessibility.py tests/test_task13_frontend_contract.py
git commit -m "feat: add guided review journey"
```

### Task 7: Verify integrated recovery, privacy, correction lineage, and repeated browser smoke

**Files:**
- Modify: `tests/test_end_to_end.py`
- Modify: `tests/test_routes.py`
- Modify: `tests/test_correction_rerun.py`
- Modify: `tests/test_adversarial_matrix.py`

- [ ] **Step 1: Add failing integrated scenarios**

Add end-to-end tests for: malformed primary normalization recovered from citations; provider failure recovered by curated evidence; all research unavailable but readable RRA/CPF completing document-led; no usable documents and no research still blocking; correction rerun retaining the new tier and purging superseded research state; and SSE events containing only the approved key sets.

```python
SAFE_RESEARCH_EVENT_KEYS = {
    "research_attempt": {"attempt", "accepted_count", "rejected_count", "publisher_count", "missing_coverage", "elapsed_seconds"},
    "research_retry": {"attempt", "next_attempt", "missing_coverage"},
    "research_curated_recovery": {"accepted_count"},
    "research_reduced": {"missing_coverage"},
    "research_document_led": {"reason"},
}
```

- [ ] **Step 2: Run integrated tests and verify any missing wiring fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_end_to_end.py tests/test_routes.py tests/test_correction_rerun.py tests/test_adversarial_matrix.py -q`

Expected: all tests pass because Tasks 1–6 established the integrated behavior. If a test fails, return to the owning task and correct that task's implementation before continuing.

- [ ] **Step 3: Run three provider-free browser scenarios**

Start: `.\.venv\Scripts\python.exe scripts/run_smoke.py`

Before browser automation, read the browser skill's local-web-development and file-upload documentation. At 1280px, run full, reduced, and document-led synthetic cases; at 390px rerun the full case. Verify intake-to-progress-to-results transitions, live timer, all stages, card rotation, evidence badge, correction rerun, DOCX download, no horizontal overflow, and zero console errors. Repeat the standard full smoke three times to catch stale state or timer leakage.

- [ ] **Step 4: Commit integrated test changes**

```powershell
git add -- tests/test_end_to_end.py tests/test_routes.py tests/test_correction_rerun.py tests/test_adversarial_matrix.py
git commit -m "test: cover resilient research journeys"
```

### Task 8: Full verification, visual QA, quality run, documentation, and deployment check

**Files:**
- Create: `docs/validation/2026-08-14-research-resilience-guided-journey-validation.md`
- Modify: `docs/PROJECT_STATUS.md`

- [ ] **Step 1: Run the full automated verification once**

Run: `.\.venv\Scripts\python.exe -m pytest -q`

Run: `.\.venv\Scripts\python.exe -m ruff check .`

Run: `node --check src/cpf_fcv_reviewer/static/app.js`

Run: `git diff --check`

Expected: every command exits 0. Record the exact test count and output; do not reuse the earlier 622-pass claim.

- [ ] **Step 2: Render and inspect DOCX variants**

Export full, reduced, and document-led smoke notes. Render with the repository's documented Word fallback because LibreOffice is unavailable. Inspect every page for clipping, overlap, broken list numbering, source separation, and evidence-status parity.

- [ ] **Step 3: Decide whether the paid Benin quality run is authorized and safe**

Inspect file identity and country consistency without uploading. Use only the Benin RRA plus a Benin CPF/CEN that is confirmed public or approved. Do not upload the Burkina Faso CPF/PLR files as part of a Benin run. If approval/public status or provider credentials remain unavailable, record the external gate and omit the run. Otherwise perform exactly one paid run and verify that it completes at full or reduced evidence tier with traceable public sources.

- [ ] **Step 4: Write the new validation record**

Record root cause, commit, commands and results, smoke scenarios and viewport sizes, DOCX inspection, paid-run decision/result, provider and registry gates, and deployment state. Do not edit historical validation records.

- [ ] **Step 5: Update project status without capturing unrelated work**

Read the current diff first. Add only a concise dated entry for this feature. If `docs/PROJECT_STATUS.md` still contains unrelated working-tree edits, stage only the new hunk with an index patch and confirm `git diff --cached` contains no pre-existing user content.

- [ ] **Step 6: Run final diff and status audit**

Run: `git status --short`

Run: `git diff --stat HEAD^`

Run: `git diff --check`

Expected: only planned files are changed; `.pytest_*`, `docs/handoffs/`, and the pre-existing documentation edits remain untouched unless their exact new hunk was intentionally staged.

- [ ] **Step 7: Commit documentation**

```powershell
git add -- docs/validation/2026-08-14-research-resilience-guided-journey-validation.md
git commit -m "docs: validate resilient research journey"
```

Commit the isolated `PROJECT_STATUS.md` hunk separately only if the staged diff contains no unrelated edits:

```powershell
git commit -m "docs: update CPF reviewer status"
```

- [ ] **Step 8: Request code review and address only verified findings**

Use `superpowers:requesting-code-review`, inspect the actual diff and test evidence, and fix any Critical or Important issue with a new failing test first. Re-run only affected checks, then the full suite once if code changed.

- [ ] **Step 9: Push and verify the deployed commit**

Push the feature branch after checking `git status` and `git diff --staged`. Verify `/health` reports the exact pushed `APP_RELEASE` and use authenticated Render logs to confirm a smoke request completes. If deployment access is absent or Render remains on an older release, report this as an external gate rather than claiming production deployment.

---

## Acceptance checklist

- The two observed `research_malformed` response shapes are represented by regression tests.
- Full, reduced, and document-led runs are distinguishable and responsibly worded.
- Uploaded RRA evidence is never represented as independent current research.
- Curated recovery uses only verified fixed institutional hosts and bounded responses.
- Guided journey works at 1280px and 390px with reduced-motion support.
- SSE progress contains no document text, filenames, prompts, claims, URLs, or provider exception details.
- Deterministic smoke mode makes no paid-provider call and cannot start as production.
- Browser and DOCX outputs disclose the same evidence tier and limitation.
- The full suite, Ruff, JavaScript syntax, and diff checks pass from fresh outputs.
- Push and deployment are reported separately and tied to exact commits.
