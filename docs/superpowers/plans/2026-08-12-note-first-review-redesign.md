# Note-First CPF Review Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fragmented CPF review output with a stage-sensitive, evidence-linked technical note and a guided three-bucket Express intake.

**Architecture:** Preserve the current Flask orchestration and volatile session store, but replace the model-authored finding/recommendation schema with narrative priority areas. Add deterministic review profiles for stage and detail level, retain upload-bucket identity in evidence, and add a preflight country-detection endpoint before review submission. Render one substantive structure in both the browser and DOCX.

**Tech Stack:** Python 3.13, Flask, Pydantic, Anthropic structured outputs, python-docx, vanilla JavaScript/CSS, pytest, Ruff

---

## Milestones and File Map

### Milestone 1: Narrative output foundation

- Modify `src/cpf_fcv_reviewer/contracts.py`: narrative review types, detail level, recommendation scale, document role, correction target.
- Create `src/cpf_fcv_reviewer/review_profiles.py`: deterministic stage and detail profiles.
- Modify `src/cpf_fcv_reviewer/review_engine.py`: inject profiles and focus guidance into the model request.
- Modify `prompts/review.md` and `prompts/repair.md`: note-first generation and repair requirements.
- Modify `src/cpf_fcv_reviewer/validators.py`: narrative evidence checks and structural stage validation.
- Modify `tests/conftest.py`, `tests/test_contracts.py`, `tests/test_review_engine.py`, `tests/test_validators.py`, `tests/test_prompt_guardrails.py`, `tests/test_adversarial*.py`, and affected runtime tests.

### Milestone 2: Intake and rendering

- Modify `src/cpf_fcv_reviewer/routes.py`: three upload fields, detail level, review focus, country preflight endpoint.
- Modify `src/cpf_fcv_reviewer/runtime.py`: bucket-aware extraction and evidence construction.
- Create `src/cpf_fcv_reviewer/country_detection.py`: bounded title-based country detection.
- Create `tests/test_country_detection.py` and update route/runtime tests.
- Modify `src/cpf_fcv_reviewer/templates/index.html`: guided landing page, upload buckets, detail selector, collapsible guidance, process modal.
- Modify `src/cpf_fcv_reviewer/static/app.js`: country preflight and note renderer.
- Modify `src/cpf_fcv_reviewer/static/styles.css`: note-first layout, upload zones, disclosures, responsive behavior.
- Modify front-end contract and Node harness tests.
- Modify `src/cpf_fcv_reviewer/export_docx.py` and DOCX parity tests.

### Milestone 3: Evaluation and release evidence

- Create `tests/fixtures/narrative_review_cases.json`: synthetic stage/detail evaluation cases.
- Create `tests/test_narrative_quality.py`: deterministic structural quality rubric.
- Create `docs/validation/2026-08-12-note-first-review-validation.md`: commands, results, and approved-material manual evaluation record.
- Modify `README.md` and `docs/PROJECT_STATUS.md`: revised workflow and current limitations.

Do not modify the separate `FCV-AGENT` repository. Do not commit Sahel or other restricted review source documents.

---

### Task 1: Replace the fragmented output contract with narrative review units

**Files:**
- Modify: `src/cpf_fcv_reviewer/contracts.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_contracts.py`

- [ ] **Step 1: Write failing contract tests**

Add tests that construct one complete narrative result and reject incomplete priority areas:

```python
from pydantic import ValidationError

from cpf_fcv_reviewer.contracts import (
    DetailLevel,
    DocumentCoverage,
    EvidenceLocator,
    PriorityArea,
    RecommendationScale,
    RevisionSummaryItem,
)


def locator() -> EvidenceLocator:
    return EvidenceLocator(
        document_title="CPF.docx",
        heading="Implementation arrangements",
        element="paragraph 18",
        excerpt="Delivery arrangements will adapt to local conditions.",
    )


def test_priority_area_keeps_assessment_action_target_and_evidence_together():
    area = PriorityArea(
        priority_area_id="pa-1",
        heading="Make the delivery model explicit",
        assessment="The CPF recognizes insecurity but leaves adaptation implicit.",
        why_it_matters="Teams cannot see how delivery will change in insecure areas.",
        recommended_action="Add two sentences defining differentiated delivery arrangements.",
        target_locator=locator(),
        recommendation_scale=RecommendationScale.TARGETED_EDIT,
        evidence_ids=("ev-1",),
        sensitivity=SensitivityCategory.CAUTIOUS,
    )
    assert area.target_locator.document_title == "CPF.docx"


def test_priority_area_rejects_blank_action():
    with pytest.raises(ValidationError):
        PriorityArea(
            priority_area_id="pa-1",
            heading="Delivery",
            assessment="The operating model is implicit.",
            why_it_matters="Delivery choices remain unclear.",
            recommended_action="   ",
            target_locator=locator(),
            recommendation_scale=RecommendationScale.TARGETED_EDIT,
            evidence_ids=("ev-1",),
            sensitivity=SensitivityCategory.CAUTIOUS,
        )


def test_review_result_contains_no_priority_question_response_collection(make_valid_result):
    result, _ = make_valid_result
    assert "priority_question_responses" not in result.model_dump()
    assert result.metadata.detail_level is DetailLevel.STANDARD
```

- [ ] **Step 2: Run the contract tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_contracts.py -q
```

Expected: failures because `DetailLevel`, `PriorityArea`, `RevisionSummaryItem`, `DocumentCoverage`, and `RecommendationScale` do not exist.

- [ ] **Step 3: Implement the narrative contract**

Replace `Finding`, `Recommendation`, and `PriorityQuestionResponse` in the model-authored result with these types:

```python
class DetailLevel(StrEnum):
    BRIEF = "brief"
    STANDARD = "standard"
    IN_DEPTH = "in_depth"


class DocumentRole(StrEnum):
    PRIMARY = "primary"
    PACKAGE = "package"
    CONTEXT = "context"


class RecommendationScale(StrEnum):
    PREPARATION_PRIORITY = "preparation_priority"
    SUBSTANTIVE_REVISION = "substantive_revision"
    TARGETED_EDIT = "targeted_edit"
    FINE_TUNING = "fine_tuning"
    COMMENT_RESPONSE = "comment_response"


class RevisionSummaryItem(FrozenModel):
    priority_area_id: str
    action: str


class PriorityArea(FrozenModel):
    priority_area_id: str
    heading: str
    assessment: str
    why_it_matters: str
    recommended_action: str
    target_locator: EvidenceLocator
    recommendation_scale: RecommendationScale
    evidence_ids: tuple[str, ...]
    sensitivity: SensitivityCategory
    comment_reference: str | None = None

    @field_validator(
        "priority_area_id",
        "heading",
        "assessment",
        "why_it_matters",
        "recommended_action",
    )
    @classmethod
    def requires_nonblank_narrative(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Narrative review fields cannot be blank.")
        return value


class DocumentCoverage(FrozenModel):
    primary_document: str
    package_documents: tuple[str, ...] = ()
    context_documents: tuple[str, ...] = ()
    coverage_note: str


class ReviewResult(FrozenModel):
    metadata: RunMetadata
    overall_read: str
    revision_summary: tuple[RevisionSummaryItem, ...]
    priority_areas: tuple[PriorityArea, ...]
    institutional_referral_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    document_coverage: DocumentCoverage


class ReviewDraft(FrozenModel):
    overall_read: str
    revision_summary: tuple[RevisionSummaryItem, ...]
    priority_areas: tuple[PriorityArea, ...]
    institutional_referral_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    coverage_note: str
```

Add `detail_level: DetailLevel = DetailLevel.STANDARD` to `RunMetadata`. Add `document_role: DocumentRole | None = None` to `EvidenceItem`. Rename `UserCorrection.affected_finding_id` to `affected_priority_area_id`.

Update `tests/conftest.py::make_valid_result` to provide one `PriorityArea`, one linked `RevisionSummaryItem`, and a `DocumentCoverage` object. Keep the existing reproducibility metadata and `ev-1` locator unchanged.

- [ ] **Step 4: Run focused tests and verify passing behavior**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_contracts.py tests/test_reproducibility.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit the contract migration**

```powershell
git add -- src/cpf_fcv_reviewer/contracts.py tests/conftest.py tests/test_contracts.py tests/test_reproducibility.py
git commit -m "refactor: model CPF review as narrative priority areas"
```

---

### Task 2: Make stage and detail behavior deterministic inputs

**Files:**
- Create: `src/cpf_fcv_reviewer/review_profiles.py`
- Modify: `src/cpf_fcv_reviewer/review_engine.py`
- Modify: `src/cpf_fcv_reviewer/reproducibility.py`
- Modify: `src/cpf_fcv_reviewer/evidence_builder.py`
- Modify: `tests/test_review_engine.py`
- Modify: `tests/test_reproducibility.py`

- [ ] **Step 1: Write failing stage/detail profile tests**

```python
from cpf_fcv_reviewer.contracts import DetailLevel, RecommendationScale
from cpf_fcv_reviewer.review_profiles import DETAIL_PROFILES, STAGE_PROFILES


def test_early_drafting_allows_strategy_but_caps_immediate_insertions():
    profile = STAGE_PROFILES["early_drafting"]
    assert RecommendationScale.PREPARATION_PRIORITY in profile.allowed_scales
    assert profile.max_immediate_insertion_words == 80
    assert "short concept document" in profile.instruction


def test_finalization_allows_only_fine_tuning():
    profile = STAGE_PROFILES["finalization"]
    assert profile.allowed_scales == (RecommendationScale.FINE_TUNING,)
    assert profile.max_immediate_insertion_words == 60


def test_detail_profiles_bound_priority_area_counts():
    assert DETAIL_PROFILES[DetailLevel.BRIEF].priority_area_range == (2, 3)
    assert DETAIL_PROFILES[DetailLevel.STANDARD].priority_area_range == (3, 5)
    assert DETAIL_PROFILES[DetailLevel.IN_DEPTH].priority_area_range == (4, 7)
```

- [ ] **Step 2: Run tests and verify missing-module failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_review_engine.py -q
```

Expected: collection fails because `review_profiles.py` does not exist.

- [ ] **Step 3: Implement immutable profiles**

Create `review_profiles.py` with frozen dataclasses:

```python
from dataclasses import dataclass

from .contracts import DetailLevel, RecommendationScale


@dataclass(frozen=True)
class StageProfile:
    instruction: str
    allowed_scales: tuple[RecommendationScale, ...]
    max_immediate_insertion_words: int


@dataclass(frozen=True)
class DetailProfile:
    target_pages: int
    priority_area_range: tuple[int, int]


STAGE_PROFILES = {
    "early_drafting": StageProfile(
        "Challenge strategic framing where needed, but keep any immediate edit suitable "
        "for a short concept document. Carry larger changes as preparation priorities.",
        (RecommendationScale.PREPARATION_PRIORITY, RecommendationScale.TARGETED_EDIT),
        80,
    ),
    "concept_review": StageProfile(
        "Recommend material but bounded changes to strategic choices and architecture.",
        (RecommendationScale.SUBSTANTIVE_REVISION, RecommendationScale.TARGETED_EDIT),
        180,
    ),
    "decision_review": StageProfile(
        "Recommend specific revisions to objectives, results, risks, and delivery choices.",
        (RecommendationScale.SUBSTANTIVE_REVISION, RecommendationScale.TARGETED_EDIT),
        140,
    ),
    "roc_oc": StageProfile(
        "Focus on discrete management decisions and implementability refinements.",
        (RecommendationScale.TARGETED_EDIT,),
        100,
    ),
    "finalization": StageProfile(
        "Limit advice to precise clarification, correction, consistency, and indicator edits.",
        (RecommendationScale.FINE_TUNING,),
        60,
    ),
    "response_to_comments": StageProfile(
        "Link each action to the issue being resolved and propose concise response language.",
        (RecommendationScale.COMMENT_RESPONSE,),
        100,
    ),
}

DETAIL_PROFILES = {
    DetailLevel.BRIEF: DetailProfile(1, (2, 3)),
    DetailLevel.STANDARD: DetailProfile(2, (3, 5)),
    DetailLevel.IN_DEPTH: DetailProfile(3, (4, 7)),
}
```

Update `ReviewEngine.review()` to read both profiles and pass serialized fields under `stage_profile`, `detail_profile`, and `review_focus`. Build `ReviewResult.document_coverage` locally from evidence roles and `draft.coverage_note`; do not ask the model to invent filenames:

```python
def review(
    self,
    evidence_pack: EvidencePack,
    *,
    review_focus: str = "",
) -> ReviewResult:
    stage_profile = STAGE_PROFILES[evidence_pack.metadata.review_stage]
    detail_profile = DETAIL_PROFILES[evidence_pack.metadata.detail_level]
    draft = self.gateway.generate(
        prompt_name="review",
        payload={
            "evidence_pack": evidence_pack.model_dump(mode="json"),
            "stage_profile": asdict(stage_profile),
            "detail_profile": asdict(detail_profile),
            "review_focus": review_focus,
        },
        output_type=ReviewDraft,
    )
    names = {
        role: tuple(
            dict.fromkeys(
                item.locator.document_title
                for item in evidence_pack.evidence
                if item.document_role is role and item.locator is not None
            )
        )
        for role in DocumentRole
    }
    coverage = DocumentCoverage(
        primary_document=names[DocumentRole.PRIMARY][0],
        package_documents=names[DocumentRole.PACKAGE],
        context_documents=names[DocumentRole.CONTEXT],
        coverage_note=draft.coverage_note,
    )
    content = draft.model_dump(exclude={"coverage_note"})
    return ReviewResult(
        metadata=evidence_pack.metadata,
        document_coverage=coverage,
        **content,
    )
```

Import `asdict` from `dataclasses`. Catch unsupported stages before the gateway call with the existing `ValueError` behavior. Require at least one primary-role evidence item before constructing coverage.

Update `ReviewEngine.repair()` so the model may repair only `coverage_note`, while application-derived filenames remain unchanged:

```python
coverage = result.document_coverage.model_copy(
    update={"coverage_note": draft.coverage_note}
)
content = draft.model_dump(exclude={"coverage_note"})
metadata = result.metadata.model_copy(update={"repair_count": 1})
return ReviewResult(
    metadata=metadata,
    document_coverage=coverage,
    **content,
)
```

Thread `detail_level` through `build_run_metadata()` and `build_reproducible_evidence_pack()`.

- [ ] **Step 4: Run stage and reproducibility tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_review_engine.py tests/test_reproducibility.py tests/test_evidence_builder.py -q
```

Expected: all selected tests pass, including every supported stage and all three detail levels.

- [ ] **Step 5: Commit profile behavior**

```powershell
git add -- src/cpf_fcv_reviewer/review_profiles.py src/cpf_fcv_reviewer/review_engine.py src/cpf_fcv_reviewer/reproducibility.py src/cpf_fcv_reviewer/evidence_builder.py tests/test_review_engine.py tests/test_reproducibility.py tests/test_evidence_builder.py
git commit -m "feat: add stage and detail review profiles"
```

---

### Task 3: Rewrite review and repair prompts for note-first synthesis

**Files:**
- Modify: `prompts/review.md`
- Modify: `prompts/repair.md`
- Modify: `tests/test_prompt_guardrails.py`

- [ ] **Step 1: Add failing prompt contract assertions**

```python
def test_review_prompt_requires_note_first_stage_sensitive_output():
    prompt = load_prompt("review")
    for phrase in (
        "connected technical review note",
        "Overall read",
        "What to revise",
        "Priority areas for strengthening",
        "Do not create a Questions for confirmation section",
        "primary document is the principal lens",
        "max_immediate_insertion_words",
        "Do not report pathway by pathway",
    ):
        assert phrase in prompt


def test_repair_prompt_preserves_narrative_links():
    prompt = load_prompt("repair")
    assert "revision_summary priority_area_id" in prompt
    assert "Do not add a question section" in prompt
```

- [ ] **Step 2: Run prompt tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prompt_guardrails.py -q
```

Expected: the new phrase assertions fail.

- [ ] **Step 3: Replace prompt instructions**

Retain every existing injection, policy, citation, limited-mode, and language guardrail. Add explicit instructions that:

```text
Write a connected technical review note, not a dashboard, checklist, or pathway-by-pathway report.
Use the primary document as the principal lens. Use package documents to corroborate or qualify it and contextual documents to test its framing.
Compose, in order: Overall read; What to revise; Priority areas for strengthening; Limitations and document coverage.
Do not create a Questions for confirmation section. Calibrate uncertain claims and record material coverage limits instead.
Apply stage_profile.allowed_scales and max_immediate_insertion_words to every recommended action.
Apply detail_profile.priority_area_range as a ceiling unless evidence is too thin, in which case return fewer areas without padding.
Every revision_summary priority_area_id must resolve to exactly one priority area.
At response_to_comments stage, every priority area must include comment_reference identifying the issue being resolved.
Do not report pathway by pathway. Select only issues that materially affect strategy, implementation, risk, or results.
```

Increment both prompt version headers to `Version: 2.0.0` so reproducibility hashes distinguish the output redesign.

- [ ] **Step 4: Run prompt tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prompt_guardrails.py -q
```

Expected: all prompt guardrail and hash tests pass.

- [ ] **Step 5: Commit prompt redesign**

```powershell
git add -- prompts/review.md prompts/repair.md tests/test_prompt_guardrails.py
git commit -m "feat: prompt for note-first CPF review synthesis"
```

---

### Task 4: Validate narrative links, evidence, and stage realism

**Files:**
- Modify: `src/cpf_fcv_reviewer/validators.py`
- Modify: `src/cpf_fcv_reviewer/runtime.py`
- Modify: `tests/test_validators.py`
- Modify: `tests/test_adversarial.py`
- Modify: `tests/test_adversarial_matrix.py`
- Remove: `tests/test_priority_question_validation.py`

- [ ] **Step 1: Write failing validator tests**

```python
def test_revision_summary_must_link_to_exactly_one_priority_area(make_valid_result):
    result, evidence = make_valid_result
    broken = result.model_copy(
        update={
            "revision_summary": (
                RevisionSummaryItem(priority_area_id="missing", action="Clarify delivery."),
            )
        }
    )
    issues = validate_review(broken, evidence_ids=set(evidence), prohibited_terms=set())
    assert "unknown_priority_area" in {issue.code for issue in issues}


def test_finalization_rejects_non_fine_tuning_scale(make_valid_result):
    result, evidence = make_valid_result
    area = result.priority_areas[0].model_copy(
        update={"recommendation_scale": RecommendationScale.SUBSTANTIVE_REVISION}
    )
    result = result.model_copy(update={"priority_areas": (area,)})
    issues = validate_review(result, evidence_ids=set(evidence), prohibited_terms=set())
    assert "stage_overreach" in {issue.code for issue in issues}


def test_early_drafting_rejects_long_immediate_action(make_valid_result):
    result, evidence = make_valid_result
    metadata = result.metadata.model_copy(update={"review_stage": "early_drafting"})
    area = result.priority_areas[0].model_copy(
        update={"recommended_action": "word " * 81}
    )
    issues = validate_review(
        result.model_copy(update={"metadata": metadata, "priority_areas": (area,)}),
        evidence_ids=set(evidence),
        prohibited_terms=set(),
    )
    assert "stage_length_overreach" in {issue.code for issue in issues}


def test_response_to_comments_requires_comment_reference(make_valid_result):
    result, evidence = make_valid_result
    metadata = result.metadata.model_copy(update={"review_stage": "response_to_comments"})
    area = result.priority_areas[0].model_copy(
        update={
            "recommendation_scale": RecommendationScale.COMMENT_RESPONSE,
            "comment_reference": None,
        }
    )
    issues = validate_review(
        result.model_copy(update={"metadata": metadata, "priority_areas": (area,)}),
        evidence_ids=set(evidence),
        prohibited_terms=set(),
    )
    assert "missing_comment_reference" in {issue.code for issue in issues}
```

- [ ] **Step 2: Run validator tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_validators.py tests/test_adversarial.py -q
```

Expected: failures because validators still traverse findings, recommendations, and priority responses.

- [ ] **Step 3: Implement structural validation**

Update `result_text()` to include `overall_read`, revision-summary actions, every priority-area narrative field, limitations, and coverage note.

Update `validate_review()` to:

```python
area_ids = {area.priority_area_id for area in result.priority_areas}
for summary in result.revision_summary:
    if summary.priority_area_id not in area_ids:
        issues.append(ValidationIssue("unknown_priority_area", summary.priority_area_id))

profile = STAGE_PROFILES[result.metadata.review_stage]
for area in result.priority_areas:
    _append_unknown_evidence_issue(
        issues, area.priority_area_id, area.evidence_ids, evidence_ids
    )
    if area.recommendation_scale not in profile.allowed_scales:
        issues.append(
            ValidationIssue(
                "stage_overreach",
                f"{area.priority_area_id} uses {area.recommendation_scale.value} at "
                f"{result.metadata.review_stage}.",
            )
        )
    if (
        result.metadata.review_stage == "early_drafting"
        and len(area.recommended_action.split()) > profile.max_immediate_insertion_words
    ):
        issues.append(
            ValidationIssue(
                "stage_length_overreach",
                f"{area.priority_area_id} proposes too much immediate PCN text.",
            )
        )
    if result.metadata.review_stage == "response_to_comments" and not area.comment_reference:
        issues.append(
            ValidationIssue(
                "missing_comment_reference",
                f"{area.priority_area_id} is not linked to a review comment.",
            )
        )
```

Delete dedicated priority-question response validation. Keep optional review-focus text in the model payload, but do not require or render a separate answer collection.

- [ ] **Step 4: Run focused safety and validator tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_validators.py tests/test_adversarial.py tests/test_adversarial_matrix.py tests/test_policy_adversarial.py -q
```

Expected: all selected tests pass with policy and limited-mode protections unchanged.

- [ ] **Step 5: Commit validation migration**

```powershell
git add -- src/cpf_fcv_reviewer/validators.py src/cpf_fcv_reviewer/runtime.py tests/test_validators.py tests/test_adversarial.py tests/test_adversarial_matrix.py tests/test_policy_adversarial.py
git rm -- tests/test_priority_question_validation.py
git commit -m "feat: validate stage-sensitive narrative reviews"
```

---

### Task 5: Preserve the three upload roles through intake and evidence construction

**Files:**
- Modify: `src/cpf_fcv_reviewer/routes.py`
- Modify: `src/cpf_fcv_reviewer/runtime.py`
- Modify: `tests/test_routes.py`
- Modify: `tests/test_runtime_wiring.py`
- Modify: `tests/test_evidence_builder.py`
- Create: `tests/test_review_focus_intake.py`
- Remove: `src/cpf_fcv_reviewer/priority_questions.py`
- Remove: `tests/test_priority_question_intake.py`
- Remove: `tests/test_priority_questions.py`

- [ ] **Step 1: Write failing route and runtime tests**

```python
def test_create_review_preserves_upload_buckets_and_detail_level():
    app = make_app()
    response = app.test_client().post(
        "/api/reviews",
        data={
            "country": "Testland",
            "review_stage": "concept_review",
            "detail_level": "in_depth",
            "cpf": (BytesIO(b"CPF text " * 30), "cpf.txt"),
            "package_documents": (BytesIO(b"Results matrix"), "results.txt"),
            "context_documents": (BytesIO(b"RRA context"), "rra.txt"),
            "review_focus": "Pay particular attention to delivery arrangements.",
        },
        content_type="multipart/form-data",
    )
    state = app.extensions["session_store"].get(response.get_json()["assessment_id"])
    assert state.payload["detail_level"] == "in_depth"
    assert state.payload["package_documents"][0]["name"] == "results.txt"
    assert state.payload["context_documents"][0]["name"] == "rra.txt"
    assert "delivery arrangements" in state.payload["review_focus"]
```

Add a runtime test asserting primary, package, and context evidence carry `DocumentRole.PRIMARY`, `.PACKAGE`, and `.CONTEXT`, and that reproducibility fingerprint keys preserve the same role prefixes.

- [ ] **Step 2: Run route/runtime tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_routes.py tests/test_runtime_wiring.py tests/test_evidence_builder.py -q
```

Expected: failures because the route accepts only `supporting`, has no detail level, and evidence has no role.

- [ ] **Step 3: Implement bucket-aware intake and evidence**

In `create_review()`, validate `DetailLevel` and store:

```python
def uploaded_files(field_name: str) -> list[dict[str, object]]:
    return [
        {"name": item.filename, "bytes": item.read()}
        for item in request.files.getlist(field_name)
        if item.filename
    ]


try:
    detail_level = DetailLevel(request.form.get("detail_level", DetailLevel.STANDARD))
except ValueError:
    return jsonify(error="Unsupported detail level."), 400

payload = {
    "country": request.form.get("country", "").strip(),
    "review_stage": request.form.get("review_stage", "").strip(),
    "detail_level": detail_level.value,
    "cpf": {"name": cpf.filename, "bytes": cpf.read()},
    "package_documents": uploaded_files("package_documents"),
    "context_documents": uploaded_files("context_documents"),
    "review_focus": request.form.get("review_focus", "").strip()[:4000],
    "corrections": [],
    "status": "created",
}
```

In runtime extraction, keep `primary_document`, `package_documents`, and `context_documents` separate. Build evidence IDs as `primary-###`, `package-###`, and `context-###`; set `document_role` on each item. Give the primary document the largest segment budget, package documents a moderate budget, and context documents a bounded corroboration budget. Include all three role-prefixed document groups in reproducibility fingerprints.

Remove automatic question detection and checkbox confirmation. Preserve user focus as one bounded untrusted instruction string.

- [ ] **Step 4: Run intake/evidence tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_routes.py tests/test_runtime_wiring.py tests/test_evidence_builder.py tests/test_review_focus_intake.py -q
```

Expected: all selected tests pass. `review_focus` is stored once as bounded emphasis and does not generate a dedicated response collection.

- [ ] **Step 5: Commit upload-role support**

```powershell
git add -- src/cpf_fcv_reviewer/routes.py src/cpf_fcv_reviewer/runtime.py tests/test_routes.py tests/test_runtime_wiring.py tests/test_evidence_builder.py tests/test_review_focus_intake.py
git rm -- src/cpf_fcv_reviewer/priority_questions.py tests/test_priority_question_intake.py tests/test_priority_questions.py
git commit -m "feat: preserve CPF package and context upload roles"
```

---

### Task 6: Add bounded country detection before submission

**Files:**
- Create: `src/cpf_fcv_reviewer/country_detection.py`
- Create: `tests/test_country_detection.py`
- Modify: `src/cpf_fcv_reviewer/routes.py`
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Write failing detector and endpoint tests**

```python
from cpf_fcv_reviewer.country_detection import detect_country
from cpf_fcv_reviewer.extraction import ExtractedDocument, ExtractedSegment


def document(text: str, name: str = "cpf.txt") -> ExtractedDocument:
    return ExtractedDocument(
        name,
        (ExtractedSegment(text, None, None, "full text"),),
        (),
    )


def test_detects_country_from_cpf_title():
    result = detect_country(
        document("Country Partnership Framework for the Republic of Chad for FY26-FY30")
    )
    assert result.country == "Chad"
    assert result.confidence == "high"


def test_ambiguous_title_requires_confirmation():
    result = detect_country(document("Regional country partnership discussion draft"))
    assert result.country is None
    assert result.confidence == "low"
```

Add a route test posting a primary file to `/api/detect-country` and asserting `{"country": "Chad", "requires_confirmation": false}`. Add an unreadable-file test expecting HTTP 400 with a safe error message.

- [ ] **Step 2: Run tests and verify missing-module/route failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_country_detection.py tests/test_routes.py -q
```

Expected: failures because the detector and endpoint do not exist.

- [ ] **Step 3: Implement title-based detection**

Create a frozen result type and bounded patterns:

```python
@dataclass(frozen=True)
class CountryDetection:
    country: str | None
    confidence: Literal["high", "low"]
    evidence: str | None


TITLE_PATTERNS = (
    re.compile(
        r"(?:country partnership framework|country engagement note)\s+for\s+"
        r"(?:the\s+)?(?P<country>[^\n,]+?)(?:\s+for\s+(?:fy|the period)|\s+fy\d|[,\n])",
        re.IGNORECASE,
    ),
)

PREFIXES = ("Republic of ", "The Republic of ", "Federal Republic of ")


def detect_country(document: ExtractedDocument) -> CountryDetection:
    sample = "\n".join(segment.text for segment in document.segments[:8])[:8000]
    for pattern in TITLE_PATTERNS:
        match = pattern.search(sample)
        if match:
            country = match.group("country").strip(" .:-")
            for prefix in PREFIXES:
                if country.casefold().startswith(prefix.casefold()):
                    country = country[len(prefix):]
                    break
            return CountryDetection(country, "high", match.group(0)[:240])
    return CountryDetection(None, "low", None)
```

The `/api/detect-country` endpoint extracts only the primary document, calls `require_readable_primary()`, and returns the detected value. It never starts a review or stores uploaded bytes. The final review route still accepts the confirmed hidden country value and rejects a blank country.

- [ ] **Step 4: Run detector and route tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_country_detection.py tests/test_routes.py tests/test_security.py -q
```

Expected: all selected tests pass; no extracted text is returned beyond the bounded title evidence needed for confirmation.

- [ ] **Step 5: Commit country preflight**

```powershell
git add -- src/cpf_fcv_reviewer/country_detection.py src/cpf_fcv_reviewer/routes.py tests/test_country_detection.py tests/test_routes.py tests/test_security.py
git commit -m "feat: infer country from the primary CPF"
```

---

### Task 7: Rebuild the landing page as a guided Express intake

**Files:**
- Modify: `src/cpf_fcv_reviewer/templates/index.html`
- Modify: `src/cpf_fcv_reviewer/static/styles.css`
- Modify: `src/cpf_fcv_reviewer/static/app.js`
- Modify: `tests/test_frontend_contract.py`
- Modify: `tests/test_task13_frontend_contract.py`

- [ ] **Step 1: Replace old front-end contract assertions with failing new ones**

Assert the HTML contains:

```python
for fragment in (
    'id="primary-upload"',
    'id="package-documents"',
    'id="context-documents"',
    'id="detail-level"',
    '<option value="standard" selected>Standard</option>',
    'id="additional-guidance"',
    'id="review-focus"',
    'id="process-dialog"',
    'Early drafting / PCN',
    'Express review',
):
    assert fragment in html
assert '<label for="country">' not in html
assert "Questions requiring a dedicated response" not in html
```

Assert CSS defines a three-column `.upload-zones` layout and collapses it to one column below 760px. Assert JavaScript calls `/api/detect-country`, fills a hidden `country` input, and presents a correction input only when confirmation is required.

- [ ] **Step 2: Run front-end tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_frontend_contract.py tests/test_task13_frontend_contract.py -q
```

Expected: failures against the old country field, single supporting upload, and question controls.

- [ ] **Step 3: Implement the guided landing structure**

Build the form in this order:

```html
<section class="hero">...</section>
<section class="form-card" aria-labelledby="express-review-heading">
  <h2 id="express-review-heading">Express review</h2>
  <div class="upload-zones">
    <label class="upload-zone" id="primary-upload">...</label>
    <label class="upload-zone">...<input id="package-documents" name="package_documents" multiple></label>
    <label class="upload-zone">...<input id="context-documents" name="context_documents" multiple></label>
  </div>
  <div id="country-detection" aria-live="polite"></div>
  <input id="country" name="country" type="hidden">
  <div class="field-grid">
    <label>Review stage<select id="review-stage" name="review_stage" required>...</select></label>
    <label>Level of detail<select id="detail-level" name="detail_level">...</select></label>
  </div>
  <details id="additional-guidance">
    <summary>Additional guidance</summary>
    <label for="review-focus">What should the review pay particular attention to?</label>
    <textarea id="review-focus" name="review_focus"></textarea>
  </details>
</section>
<dialog id="process-dialog">...</dialog>
```

Keep the advisory boundary and public/non-sensitive material warning prominent. The process dialog explains extraction, evidence selection, contextual checking, stage-sensitive synthesis, validation, and DOCX rendering in plain language.

Implement native `<dialog>` open/close controls and country preflight on primary-file change. Disable the review button while detection is pending or a country requires confirmation.

- [ ] **Step 4: Run front-end tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_frontend_contract.py tests/test_task13_frontend_contract.py -q
```

Expected: all selected tests pass, including the existing session-only and stale-event protections.

- [ ] **Step 5: Commit landing-page redesign**

```powershell
git add -- src/cpf_fcv_reviewer/templates/index.html src/cpf_fcv_reviewer/static/styles.css src/cpf_fcv_reviewer/static/app.js tests/test_frontend_contract.py tests/test_task13_frontend_contract.py
git commit -m "feat: add guided three-bucket CPF review intake"
```

---

### Task 8: Render the browser result as a connected note

**Files:**
- Modify: `src/cpf_fcv_reviewer/routes.py`
- Modify: `src/cpf_fcv_reviewer/static/app.js`
- Modify: `src/cpf_fcv_reviewer/static/styles.css`
- Modify: `tests/test_frontend_contract.py`
- Modify: `tests/test_task13_frontend_contract.py`
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Write failing note-renderer tests**

Assert `app.js` renders the four agreed sections and does not reference old collections:

```python
for fragment in (
    'text("h2", "Overall read")',
    'text("h2", "What to revise")',
    'text("h2", "Priority areas for strengthening")',
    'text("h2", "Limitations and document coverage")',
    "result.revision_summary",
    "result.priority_areas",
    "area.recommended_action",
    "area.target_locator",
):
    assert fragment in javascript
for obsolete in (
    "result.findings",
    "result.recommendations",
    "result.priority_question_responses",
    'text("h2", "Priority questions")',
):
    assert obsolete not in javascript
```

Update the Node harness result fixture to the new schema and assert a summary link targets the matching priority-area element.

- [ ] **Step 2: Run front-end and result-route tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_frontend_contract.py tests/test_task13_frontend_contract.py tests/test_routes.py -q
```

Expected: failures because the browser and result-route evidence check still traverse findings.

- [ ] **Step 3: Implement the note renderer and evidence disclosure**

Add these focused renderer helpers:

```javascript
function labelledParagraph(label, value, className) {
  const paragraph = document.createElement("p");
  paragraph.className = className;
  const lead = document.createElement("strong");
  lead.textContent = `${label}. `;
  paragraph.append(lead, document.createTextNode(value));
  return paragraph;
}

function locatorLabel(locator) {
  return [
    locator.document_title,
    locator.page ? `page ${locator.page}` : "",
    locator.heading || "",
    locator.element || "",
  ].filter(Boolean).join(" | ");
}

function renderEvidenceGroup(result, evidenceIds) {
  const details = document.createElement("details");
  details.className = "evidence-group";
  details.append(text("summary", "Evidence and document locations"));
  for (const evidenceId of evidenceIds) {
    const item = result.evidence_by_id?.[evidenceId];
    if (!item) continue;
    details.append(
      text("p", locatorLabel(item.locator), "evidence-locator"),
      text("p", item.locator?.excerpt || item.text, "evidence-excerpt"),
    );
  }
  return details;
}
```

Then rewrite `renderResult()`:

```javascript
results.append(text("h2", "Overall read"), text("p", result.overall_read, "overall-read"));

const summary = document.createElement("ol");
for (const item of result.revision_summary) {
  const link = document.createElement("a");
  link.href = `#${item.priority_area_id}`;
  link.textContent = item.action;
  const row = document.createElement("li");
  row.append(link);
  summary.append(row);
}
results.append(text("h2", "What to revise"), summary);

results.append(text("h2", "Priority areas for strengthening"));
for (const area of result.priority_areas) {
  const section = document.createElement("section");
  section.id = area.priority_area_id;
  section.className = "priority-area";
  section.append(
    text("h3", area.heading),
    text("p", area.assessment),
    text("p", area.why_it_matters),
    labelledParagraph("Recommended action", area.recommended_action, "recommended-action"),
    labelledParagraph("Target", locatorLabel(area.target_locator), "target-location"),
  );
  if (area.comment_reference) {
    section.append(
      labelledParagraph("Comment addressed", area.comment_reference, "comment-reference"),
    );
  }
  section.append(renderEvidenceGroup(result, area.evidence_ids));
  results.append(section);
}
```

Evidence disclosure summaries say `Evidence and document locations`, not internal evidence IDs. Keep `textContent` construction and no `innerHTML`. Update the result route to verify every `priority_area.evidence_ids` value exists.

- [ ] **Step 4: Run renderer, route, and accessibility contract tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_frontend_contract.py tests/test_task13_frontend_contract.py tests/test_routes.py -q
```

Expected: all selected tests pass; disclosure controls remain keyboard-native.

- [ ] **Step 5: Commit browser note rendering**

```powershell
git add -- src/cpf_fcv_reviewer/routes.py src/cpf_fcv_reviewer/static/app.js src/cpf_fcv_reviewer/static/styles.css tests/test_frontend_contract.py tests/test_task13_frontend_contract.py tests/test_routes.py
git commit -m "feat: render CPF review as a connected web note"
```

---

### Task 9: Make DOCX substantively identical to the web note

**Files:**
- Modify: `src/cpf_fcv_reviewer/export_docx.py`
- Modify: `tests/test_docx_export.py`
- Modify: `tests/test_output_parity.py`
- Modify: `tests/test_reproducibility_export.py`

- [ ] **Step 1: Write failing DOCX structure and parity tests**

```python
def test_docx_uses_note_first_sections_and_omits_question_section(make_valid_result):
    result, evidence = make_valid_result
    data = build_docx(result, evidence=evidence, hydrated_referrals=())
    text = "\n".join(p.text for p in Document(BytesIO(data)).paragraphs)
    assert "Overall read" in text
    assert "What to revise" in text
    assert "Priority areas for strengthening" in text
    assert result.priority_areas[0].recommended_action in text
    assert "Questions for confirmation" not in text
    assert "Priority questions" not in text
    assert "ev-1" not in text
```

Update parity tests to assert `overall_read`, every revision action, every priority-area narrative field, target locator, limitations, and coverage note appear in the DOCX.

- [ ] **Step 2: Run export tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_docx_export.py tests/test_output_parity.py tests/test_reproducibility_export.py -q
```

Expected: failures because export still expects findings, practical options, and priority responses.

- [ ] **Step 3: Rewrite DOCX body composition**

Keep document setup, advisory text, source locator helper, and reproducibility section. Add these helpers:

```python
def target_text(locator: EvidenceLocator) -> str:
    parts = [locator.document_title]
    if locator.page is not None:
        parts.append(f"page {locator.page}")
    if locator.heading:
        parts.append(locator.heading)
    if locator.element:
        parts.append(locator.element)
    return " | ".join(parts)


def evidence_excerpt(item: EvidenceItem) -> str:
    return item.locator.excerpt if item.locator is not None else item.text
```

Replace the body with:

```python
document.add_heading("Overall read", level=1)
document.add_paragraph(result.overall_read)

document.add_heading("What to revise", level=1)
for item in result.revision_summary:
    document.add_paragraph(item.action, style="List Number")

document.add_heading("Priority areas for strengthening", level=1)
for area in result.priority_areas:
    document.add_heading(area.heading, level=2)
    document.add_paragraph(area.assessment)
    document.add_paragraph(area.why_it_matters)
    action = document.add_paragraph()
    action.add_run("Recommended action. ").bold = True
    action.add_run(area.recommended_action)
    document.add_paragraph(f"Target: {target_text(area.target_locator)}")
    if area.comment_reference:
        document.add_paragraph(f"Comment addressed: {area.comment_reference}")
    for evidence_id in area.evidence_ids:
        item = evidence.get(evidence_id)
        if item is not None:
            document.add_paragraph(
                f"Source: {locator_text(item)}\nExcerpt: {evidence_excerpt(item)}"
            )

document.add_heading("Limitations and document coverage", level=1)
document.add_paragraph(result.document_coverage.coverage_note)
for limitation in result.limitations:
    document.add_paragraph(limitation, style="List Bullet")
```

Hydrated institutional referrals, when present, belong in the restrained technical appendix rather than a user-facing “Matters for confirmation” section.

- [ ] **Step 4: Run DOCX and parity tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_docx_export.py tests/test_output_parity.py tests/test_reproducibility_export.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit DOCX parity**

```powershell
git add -- src/cpf_fcv_reviewer/export_docx.py tests/test_docx_export.py tests/test_output_parity.py tests/test_reproducibility_export.py
git commit -m "feat: export note-first CPF review DOCX"
```

---

### Task 10: Migrate orchestration, correction, and end-to-end tests

**Files:**
- Modify: `src/cpf_fcv_reviewer/routes.py`
- Modify: `src/cpf_fcv_reviewer/runtime.py`
- Modify: `tests/test_orchestrator.py`
- Modify: `tests/test_end_to_end.py`
- Modify: `tests/test_correction_rerun.py`
- Modify: `tests/test_failure_handling.py`
- Modify: `tests/test_runtime_wiring.py`

- [ ] **Step 1: Add a failing end-to-end narrative assertion**

Change the fake review engine to return the narrative contract, then assert:

```python
result = client.get(created["result_url"]).get_json()
assert result["overall_read"] == "The CPF has a credible foundation."
assert result["revision_summary"][0]["priority_area_id"] == "pa-1"
assert result["priority_areas"][0]["evidence_ids"] == ["primary-001"]
assert result["metadata"]["detail_level"] == "standard"
assert "priority_question_responses" not in result
```

For correction reruns, post `affected_priority_area_id` and assert it survives in the child evidence pack. Review-focus normalization is covered by `tests/test_review_focus_intake.py`; no priority-question helper remains.

- [ ] **Step 2: Run orchestration/end-to-end tests and verify migration failures**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_orchestrator.py tests/test_end_to_end.py tests/test_correction_rerun.py tests/test_failure_handling.py tests/test_runtime_wiring.py -q
```

Expected: failures from old fake results, old finding correction IDs, and old payload names.

- [ ] **Step 3: Complete migration without changing orchestration semantics**

Update fixtures and fake engines to the narrative contract. Keep the same step sequence, one repair attempt, event names, session expiry, reset behavior, and safe failure categories. Change correction payload handling to:

```python
"affected_priority_area_id": body.get("affected_priority_area_id"),
```

Pass `review_focus` to `ReviewEngine.review()`; do not create a separate response collection. Ensure repair receives the complete narrative draft and preserves all valid summary-to-area links.

- [ ] **Step 4: Run the full Python test suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests pass. Any test still naming findings, recommendations, or priority-question responses must be migrated or deliberately retained only for input compatibility.

- [ ] **Step 5: Commit the end-to-end migration**

```powershell
git add -- src/cpf_fcv_reviewer/routes.py src/cpf_fcv_reviewer/runtime.py tests/test_orchestrator.py tests/test_end_to_end.py tests/test_correction_rerun.py tests/test_failure_handling.py tests/test_runtime_wiring.py
git commit -m "test: migrate CPF review workflow to narrative output"
```

---

### Task 11: Add deterministic narrative-quality and stage comparison tests

**Files:**
- Create: `tests/fixtures/narrative_review_cases.json`
- Create: `tests/test_narrative_quality.py`

- [ ] **Step 1: Create synthetic evaluation cases**

Add three non-confidential cases with the same core weakness at `early_drafting`, `decision_review`, and `finalization`. Each case includes expected allowed scales, maximum action words, required target coordinates, and forbidden generic headings.

```json
[
  {
    "stage": "early_drafting",
    "allowed_scales": ["preparation_priority", "targeted_edit"],
    "max_action_words": 80,
    "forbidden_headings": ["Pathway 1", "Mini assessment", "Questions for confirmation"]
  },
  {
    "stage": "decision_review",
    "allowed_scales": ["substantive_revision", "targeted_edit"],
    "max_action_words": 140,
    "forbidden_headings": ["Pathway 1", "Mini assessment", "Questions for confirmation"]
  },
  {
    "stage": "finalization",
    "allowed_scales": ["fine_tuning"],
    "max_action_words": 60,
    "forbidden_headings": ["Pathway 1", "Mini assessment", "Questions for confirmation"]
  }
]
```

- [ ] **Step 2: Write and run the structural quality rubric**

```python
def assert_narrative_quality(result: ReviewResult, case: dict) -> None:
    assert result.overall_read.strip()
    assert 1 <= len(result.revision_summary) <= len(result.priority_areas)
    area_ids = {area.priority_area_id for area in result.priority_areas}
    assert all(item.priority_area_id in area_ids for item in result.revision_summary)
    for area in result.priority_areas:
        assert area.recommendation_scale.value in case["allowed_scales"]
        assert len(area.recommended_action.split()) <= case["max_action_words"]
        assert area.target_locator.document_title
        assert area.evidence_ids
        assert all(term not in area.heading for term in case["forbidden_headings"])
```

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_narrative_quality.py -q
```

Expected: all three synthetic stage cases pass.

- [ ] **Step 3: Commit the evaluation rubric**

```powershell
git add -- tests/fixtures/narrative_review_cases.json tests/test_narrative_quality.py
git commit -m "test: add narrative CPF review quality rubric"
```

---

### Task 12: Verify the complete redesign and record evidence

**Files:**
- Create: `docs/validation/2026-08-12-note-first-review-validation.md`
- Modify: `README.md`
- Modify: `docs/PROJECT_STATUS.md`

- [ ] **Step 1: Run automated verification**

Run each command separately:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: zero failures.

```powershell
.\.venv\Scripts\python.exe -m ruff check .
```

Expected: `All checks passed!`

```powershell
git diff --check
```

Expected: no output.

- [ ] **Step 2: Perform local browser verification**

Start the app with the repository's configured non-production environment:

```powershell
.\.venv\Scripts\python.exe -m flask --app cpf_fcv_reviewer.app run
```

Verify at desktop and narrow widths:

- three upload zones are distinct and stack on narrow screens;
- country preflight detects a synthetic title and allows correction when ambiguous;
- Additional guidance is collapsed initially;
- Standard is the default detail level;
- the result reads as a note in the agreed order;
- summary links navigate to the matching priority area;
- evidence is collapsed initially and keyboard accessible;
- no questions-for-confirmation section appears;
- DOCX wording and section order match the browser result; and
- reset removes volatile review state.

- [ ] **Step 3: Run approved-material reference evaluation**

Using local approved Sahel material only, run at least:

- one Standard Decision review;
- one Brief Early drafting / PCN review; and
- one Standard Finalization review.

Score each output from 0 to 2 on overall judgment, CPF specificity, prioritization, actionability, target precision, stage realism, sensitivity/responsiveness distinction, evidence fidelity, and narrative coherence. Require no zero scores and an average of at least 1.5. Record only scores, safe observations, filenames or stable local references permitted by the user, and remediation decisions. Do not commit source text or generated confidential prose.

- [ ] **Step 4: Write validation and status documentation**

The validation note records:

```markdown
# Note-First CPF Review Validation

## Automated checks
- Pytest: [pass count and date]
- Ruff: passed
- Diff check: passed

## Browser checks
- Intake, country detection, responsive layout, note rendering, evidence disclosure, DOCX parity, reset

## Reference evaluation
- Approved cases used
- Stage/detail combinations
- Rubric scores
- Safe summary of remaining limitations

## Safety confirmation
- No source documents or confidential generated prose committed
- FCV Project Screener repository unchanged
```

Update README and project status to describe the three upload buckets, inferred country, detail levels, note-first output, stage behavior, and remaining non-production limitations.

- [ ] **Step 5: Commit verification evidence**

```powershell
git add -- README.md docs/PROJECT_STATUS.md docs/validation/2026-08-12-note-first-review-validation.md
git commit -m "docs: validate note-first CPF review redesign"
```

---

## Final Integration Checkpoint

- [ ] Run `git status --short --branch` and confirm only intentional files are tracked; preserve the pre-existing untracked `docs/handoffs/` directory.
- [ ] Run `git log --oneline --decorate -12` and verify each task has a focused commit.
- [ ] Run the full pytest, Ruff, and `git diff --check` commands once more after documentation changes.
- [ ] Review the final diff against `docs/superpowers/specs/2026-08-12-note-first-review-redesign-design.md` requirement by requirement.
- [ ] Do not push or open a pull request until the user chooses the branch-completion workflow.
