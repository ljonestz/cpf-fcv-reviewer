# Role-Aware Source Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace exact-once RRA page mapping with representative thematic citations while fully processing bounded accompanying package documents in the final review.

**Architecture:** Reuse the existing extraction, diagnostic-map, evidence-pack, and final-review stages. The application will fully re-extract non-RRA package uploads and pass every extractable package segment to the existing review call; the RRA map will validate known representative citations instead of a complete page partition. No new provider stage, retrieval layer, dependency, or frontend framework is introduced.

**Tech Stack:** Python 3.13, Flask, Pydantic 2, Anthropic structured output, pytest, vanilla JavaScript, python-docx, Playwright.

---

## File map

- `src/cpf_fcv_reviewer/diagnostic_map.py`: validate representative RRA citations.
- `src/cpf_fcv_reviewer/extraction.py`: define the safe package-coverage failure type.
- `src/cpf_fcv_reviewer/runtime.py`: re-extract package uploads fully, enforce package bounds, build complete package evidence, and simplify the RRA map flow.
- `src/cpf_fcv_reviewer/evidence_builder.py`: enforce representative RRA validation when constructing an RRA-alignment evidence pack.
- `src/cpf_fcv_reviewer/review_engine.py`: enforce the complete serialized review-input budget.
- `src/cpf_fcv_reviewer/orchestrator.py`: map package coverage failures to a safe code.
- `prompts/diagnostic_map.md`: request representative citations and remove exact-once coverage correction.
- `prompts/review.md`: state the primary/package/context attention hierarchy.
- `src/cpf_fcv_reviewer/static/app.js`: add the safe package-coverage message.
- Existing focused test modules: cover contracts, extraction, runtime integration, prompts, review budget, failure codes, browser contracts, and regression behavior.
- `README.md`, `CLAUDE.md`, `docs/PROJECT_STATUS.md`, and a new dated validation record: document the final verified behavior.

## Task 1: Replace exact-once RRA coverage with representative-reference validation

**Files:**
- Modify: `src/cpf_fcv_reviewer/diagnostic_map.py`
- Modify: `src/cpf_fcv_reviewer/evidence_builder.py`
- Modify: `src/cpf_fcv_reviewer/runtime.py`
- Modify: `prompts/diagnostic_map.md`
- Modify: `tests/test_diagnostic_map.py`
- Modify: `tests/test_evidence_builder.py`
- Modify: `tests/test_prompt_guardrails.py`
- Modify: `tests/test_runtime_wiring.py`

- [ ] **Step 1: Write failing representative-reference tests**

Replace exact partition expectations with tests that require known, nonempty citations but permit uncited pages and cross-theme reuse:

```python
def test_representative_diagnostic_references_allow_uncited_and_reused_pages():
    entries = (
        _entry("driver", "ev-1"),
        _entry("resilience", "ev-1", group="resilience_opportunity"),
    )
    validate_diagnostic_references(("ev-1", "ev-2", "ev-3"), entries)


def test_representative_diagnostic_references_reject_empty_entry():
    empty = _entry("driver", "ev-1").model_copy(
        update={"source_evidence_ids": ()}
    )
    with pytest.raises(ValueError, match="requires source evidence"):
        validate_diagnostic_references(("ev-1",), (empty,))


def test_representative_diagnostic_references_reject_unknown_id():
    with pytest.raises(ValueError, match="Unknown diagnostic evidence"):
        validate_diagnostic_references(("ev-1",), (_entry("driver", "other"),))


def test_representative_diagnostic_references_reject_duplicate_within_entry():
    duplicate = _entry("driver", "ev-1").model_copy(
        update={"source_evidence_ids": ("ev-1", "ev-1")}
    )
    with pytest.raises(ValueError, match="repeats source evidence"):
        validate_diagnostic_references(("ev-1",), (duplicate,))
```

Add a runtime regression where a 101-ID RRA map cites only pages 3, 44, and 101 and succeeds after one map call. Assert the evidence pack retains only those three RRA excerpts and the deep-page locator. Add prompt tests asserting that `coverage_retry`, `scaffold`, `exactly once`, and `Every supplied extractable-page evidence ID` are absent.

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

```powershell
C:\WBG\Python313\python.exe -m pytest -q tests/test_diagnostic_map.py tests/test_evidence_builder.py tests/test_prompt_guardrails.py tests/test_runtime_wiring.py -k "diagnostic or rra"
```

Expected: failures because `validate_diagnostic_references` does not exist and runtime still requires exact-once coverage.

- [ ] **Step 3: Implement the minimal reference validator**

In `diagnostic_map.py`, retain `validate_diagnostic_entry_ids` and replace the exact partition validator at active call sites with:

```python
def validate_diagnostic_references(
    authoritative_evidence_ids: tuple[str, ...],
    entries: tuple[DiagnosticEntry, ...],
) -> None:
    validate_diagnostic_entry_ids(entries)
    authoritative = set(authoritative_evidence_ids)
    for entry in entries:
        if not entry.source_evidence_ids:
            raise ValueError(
                f"Diagnostic entry {entry.entry_id} requires source evidence."
            )
        counts = Counter(entry.source_evidence_ids)
        repeated = [item for item, count in counts.items() if count > 1]
        if repeated:
            raise ValueError(
                f"Diagnostic entry {entry.entry_id} repeats source evidence: "
                + ", ".join(repeated)
            )
        unknown = [item for item in entry.source_evidence_ids if item not in authoritative]
        if unknown:
            raise ValueError("Unknown diagnostic evidence: " + ", ".join(unknown))
```

Use this validator in `build_evidence_pack` when `diagnostic_mode` is `RRA_ALIGNMENT` and in `map_uploaded_diagnostic` after the initial/schema-retry response. Delete `_safe_diagnostic_map_coverage_issues`, `_safe_diagnostic_map_coverage_scaffold`, `schema_retry_used`, and the coverage-retry branch. Build cited RRA excerpts from the union of validated references; do not compare cited-excerpt count with all extracted pages.

Change `_diagnostic_coverage_warning` to return:

```python
return (
    f"{document.name}: {attempted} pages attempted; "
    f"{extractable} pages with extractable text; thematic diagnostic synthesis complete."
)
```

Update `diagnostic_map.md` to require 8-12 thematic entries (up to 20), one or more representative supplied IDs per entry, known IDs only, optional cross-entry reuse, and no requirement to cite every page. Retain the untrusted-document boundary and the single sanitized schema retry.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run the Step 2 command.

Expected: all selected diagnostic/RRA tests pass; no coverage-retry payload is emitted.

- [ ] **Step 5: Commit the RRA simplification**

```powershell
git add -- prompts/diagnostic_map.md src/cpf_fcv_reviewer/diagnostic_map.py src/cpf_fcv_reviewer/evidence_builder.py src/cpf_fcv_reviewer/runtime.py tests/test_diagnostic_map.py tests/test_evidence_builder.py tests/test_prompt_guardrails.py tests/test_runtime_wiring.py
git diff --cached --check
git commit -m "fix: simplify RRA thematic coverage"
```

## Task 2: Fully re-extract bounded package documents

**Files:**
- Modify: `src/cpf_fcv_reviewer/extraction.py`
- Modify: `src/cpf_fcv_reviewer/runtime.py`
- Modify: `tests/test_extraction.py`
- Modify: `tests/test_runtime_wiring.py`

- [ ] **Step 1: Write failing package extraction and bound tests**

Add tests for these exact behaviors:

```python
def test_runtime_full_package_reextract_does_not_sample_pdf(monkeypatch):
    calls = []
    document = ExtractedDocument(
        "annex.pdf",
        (ExtractedSegment("Late package evidence", 40, None, "page 40"),),
        (),
    )
    monkeypatch.setattr(
        runtime,
        "extract_document",
        lambda data, name, **kwargs: calls.append((name, kwargs)) or document,
    )
    context = {
        "package_documents": (document,),
        "package_document_uploads": ((1, {"name": "annex.pdf", "bytes": b"pdf"}),),
    }
    runtime._reextract_full_package_documents(context)
    expected = {
        "max_pdf_pages": runtime.DIAGNOSTIC_MAX_PAGES,
        "sample_pdf_across_document": False,
        "max_segments": runtime.DIAGNOSTIC_MAX_PAGES,
        "max_characters": runtime.DIAGNOSTIC_MAX_CHARACTERS,
        "max_uncompressed_bytes": runtime.DIAGNOSTIC_MAX_UNCOMPRESSED_BYTES,
    }
    assert package_full_calls == [("annex.pdf", expected)]


def test_runtime_rejects_more_than_ten_package_documents(monkeypatch):
    uploads = tuple(
        {"name": f"annex-{index}.txt", "bytes": b"package text"}
        for index in range(11)
    )
    with pytest.raises(PackageCoverageUnavailable):
        runtime._extract_optional_uploads(uploads, strict_package=True)


def test_runtime_package_segment_bound_fails_closed():
    document = ExtractedDocument(
        "annex.txt",
        tuple(
            ExtractedSegment("x", None, None, f"paragraph {index}")
            for index in range(401)
        ),
        (),
    )
    with pytest.raises(PackageCoverageUnavailable, match="segment"):
        runtime._validate_full_package_documents((document,))


def test_runtime_package_character_bound_fails_closed():
    document = ExtractedDocument(
        "annex.txt",
        (ExtractedSegment("x" * 300_001, None, None, "paragraph 1"),),
        (),
    )
    with pytest.raises(PackageCoverageUnavailable, match="character"):
        runtime._validate_full_package_documents((document,))
```

Add a regression proving an invalid container, unreadable file, or extraction-limit error in the package bucket raises `PackageCoverageUnavailable` instead of returning `OPTIONAL_UPLOAD_EXCLUDED_WARNING`. Add a case proving a recognized RRA in the package field is excluded from detailed package aggregation and handled only by the RRA path.

- [ ] **Step 2: Run package-focused tests and confirm RED**

Run:

```powershell
C:\WBG\Python313\python.exe -m pytest -q tests/test_extraction.py tests/test_runtime_wiring.py -k "package or optional or diagnostic"
```

Expected: failures because package preflight is not strict and non-RRA package PDFs are never fully re-extracted.

- [ ] **Step 3: Add the safe failure and role-specific bounds**

In `extraction.py` add:

```python
class PackageCoverageUnavailable(ExtractionLimitExceeded):
    """Raised when supplied package documents cannot be reviewed in full."""
```

In `runtime.py` add only these bounds:

```python
PACKAGE_MAX_DOCUMENTS = 10
PACKAGE_MAX_SEGMENTS_TOTAL = 400
PACKAGE_MAX_CHARACTERS_TOTAL = 300_000
```

Add a strict flag to the existing optional preflight rather than creating a parallel parser:

```python
def _extract_optional_uploads(
    items: tuple | list,
    *,
    strict_package: bool = False,
) -> tuple[tuple, tuple, tuple[str, ...]]:
    if strict_package and len(items) > PACKAGE_MAX_DOCUMENTS:
        raise PackageCoverageUnavailable("Package document-count budget exceeded.")
```

Within the existing invalid-container and exception branches, use the same narrow gate:

```python
if suffix not in SUPPORTED_UPLOAD_SUFFIXES or not _has_valid_optional_container(
    data, suffix
):
    if strict_package:
        raise PackageCoverageUnavailable("A package document is unreadable.")
    warnings.append(OPTIONAL_UPLOAD_EXCLUDED_WARNING)
    continue

# In both expected extraction-exception branches:
if strict_package:
    raise PackageCoverageUnavailable(
        "A package document could not be extracted in full."
    ) from exc
```

Call it with `strict_package=True` only for `payload["package_documents"]`.

After diagnostic identification/full-RRA replacement, re-extract every retained non-RRA package upload with:

```python
document = extract_document(
    upload["bytes"],
    upload["name"],
    max_pdf_pages=DIAGNOSTIC_MAX_PAGES,
    sample_pdf_across_document=False,
    max_segments=DIAGNOSTIC_MAX_PAGES,
    max_characters=DIAGNOSTIC_MAX_CHARACTERS,
    max_uncompressed_bytes=DIAGNOSTIC_MAX_UNCOMPRESSED_BYTES,
)
```

Put that call in one helper with this contract and call it once after diagnostic
identification:

```python
def _reextract_full_package_documents(context: dict) -> None:
    documents = list(context.get("package_documents", ()))
    uploads = tuple(context.get("package_document_uploads", ()))
    diagnostic_position = (
        context.get("diagnostic_document_position")
        if context.get("diagnostic_document_role") is DocumentRole.PACKAGE
        else None
    )
    for position, (_upload_index, upload) in enumerate(uploads):
        if position == diagnostic_position:
            continue
        try:
            document = extract_document(
                upload["bytes"],
                upload["name"],
                max_pdf_pages=DIAGNOSTIC_MAX_PAGES,
                sample_pdf_across_document=False,
                max_segments=DIAGNOSTIC_MAX_PAGES,
                max_characters=DIAGNOSTIC_MAX_CHARACTERS,
                max_uncompressed_bytes=DIAGNOSTIC_MAX_UNCOMPRESSED_BYTES,
            )
        except EXPECTED_OPTIONAL_EXTRACTION_ERRORS + (ExtractionLimitExceeded,) as exc:
            raise PackageCoverageUnavailable(
                "A package document could not be extracted in full."
            ) from exc
        if not _has_usable_uploaded_document(document):
            raise PackageCoverageUnavailable("A package document is unreadable.")
        documents[position] = document
    full_package = tuple(
        document
        for position, document in enumerate(documents)
        if position != diagnostic_position
    )
    _validate_full_package_documents(full_package)
    context["package_documents"] = tuple(documents)
```

Preserve tuple positions so the recognized RRA can remain at `diagnostic_document_position`. Validate the resulting non-RRA package subset with:

```python
def _validate_full_package_documents(documents: tuple) -> None:
    segment_count = sum(len(document.segments) for document in documents)
    character_count = sum(
        len(segment.text)
        for document in documents
        for segment in document.segments
    )
    if segment_count > PACKAGE_MAX_SEGMENTS_TOTAL:
        raise PackageCoverageUnavailable("Package segment budget exceeded.")
    if character_count > PACKAGE_MAX_CHARACTERS_TOTAL:
        raise PackageCoverageUnavailable("Package character budget exceeded.")
```

Convert expected extraction/container errors to a generic `PackageCoverageUnavailable` without including filenames or extracted text.

- [ ] **Step 4: Run focused package tests and confirm GREEN**

Run the Step 2 command.

Expected: all package, optional, and diagnostic extraction tests pass; contextual PDFs retain the existing bounded sample.

- [ ] **Step 5: Commit role-specific package extraction**

```powershell
git add -- src/cpf_fcv_reviewer/extraction.py src/cpf_fcv_reviewer/runtime.py tests/test_extraction.py tests/test_runtime_wiring.py
git diff --cached --check
git commit -m "feat: fully extract bounded package documents"
```

## Task 3: Put every package segment into the review evidence pack

**Files:**
- Modify: `src/cpf_fcv_reviewer/runtime.py`
- Modify: `tests/test_runtime_wiring.py`
- Modify: `tests/test_adversarial_matrix.py`

- [ ] **Step 1: Write failing complete-package evidence tests**

Add a ten-document case with three segments per document and assert all 30 stable IDs, texts, and locators reach the captured `EvidencePack`. Add duplicate-filename inputs and assert IDs remain unique because they use positions rather than names. Add a long 40-page package PDF whose page 40 contains `LATE_PACKAGE_MATERIAL`; assert that page and marker reach the review payload.

Use these exact ID expectations:

```python
assert package_ids[:3] == [
    "package-doc-001-segment-001",
    "package-doc-001-segment-002",
    "package-doc-001-segment-003",
]
assert package_ids[-1] == "package-doc-010-segment-003"
assert len(package_ids) == len(set(package_ids)) == 30
```

Assert package text is not passed through `_truncate_at_word_boundary(..., 1600)` by using a 2,000-character marker-bearing segment and comparing the captured text exactly.

- [ ] **Step 2: Run the exact evidence tests and confirm RED**

Run:

```powershell
C:\WBG\Python313\python.exe -m pytest -q tests/test_runtime_wiring.py tests/test_adversarial_matrix.py -k "package_evidence or package_injection or role_budgets"
```

Expected: failures because `_select_package_segments` still selects only a bounded subset and package IDs are global role counters.

- [ ] **Step 3: Build complete package evidence with existing contracts**

Delete `PACKAGE_SECTION_MARKERS`, `PACKAGE_BASE_SEGMENTS`, `PACKAGE_MIN_SEGMENTS_PER_DOCUMENT`, `PACKAGE_MAX_SEGMENTS`, `_package_segment_budget`, and `_select_package_segments` after their tests are removed or replaced.

In `build_uploaded_evidence`, keep the current primary and contextual selection. Add package items directly before contextual evidence:

```python
for document_index, document in enumerate(package_documents, start=1):
    for segment_index, segment in enumerate(document.segments, start=1):
        evidence.append(
            EvidenceItem(
                evidence_id=(
                    f"package-doc-{document_index:03d}-"
                    f"segment-{segment_index:03d}"
                ),
                evidence_type="document_fact",
                text=segment.text,
                locator=EvidenceLocator(
                    document_title=document.name,
                    page=segment.page,
                    heading=segment.heading,
                    element=segment.element,
                    excerpt=_truncate_at_word_boundary(segment.text, 600),
                ),
                confidence="high",
                document_role=DocumentRole.PACKAGE,
            )
        )
```

Continue excluding the recognized RRA position before this loop. Keep current-country, registry, correction, and contextual evidence behavior unchanged. Uploaded text remains untrusted evidence; do not add it to prompts, diagnostics, or logs outside the evidence payload.

- [ ] **Step 4: Run the evidence tests and confirm GREEN**

Run the Step 2 command, then:

```powershell
C:\WBG\Python313\python.exe -m pytest -q tests/test_runtime_wiring.py tests/test_evidence_builder.py tests/test_adversarial_matrix.py
```

Expected: all tests pass and all package evidence is present exactly once.

- [ ] **Step 5: Commit complete package evidence**

```powershell
git add -- src/cpf_fcv_reviewer/runtime.py tests/test_runtime_wiring.py tests/test_adversarial_matrix.py
git diff --cached --check
git commit -m "feat: review complete package evidence"
```

## Task 4: Enforce final request budget and role hierarchy

**Files:**
- Modify: `src/cpf_fcv_reviewer/review_engine.py`
- Modify: `src/cpf_fcv_reviewer/orchestrator.py`
- Modify: `prompts/review.md`
- Modify: `src/cpf_fcv_reviewer/static/app.js`
- Modify: `tests/test_review_engine.py`
- Modify: `tests/test_routes.py`
- Modify: `tests/test_prompt_guardrails.py`
- Modify: `tests/test_task13_frontend_contract.py`

- [ ] **Step 1: Write failing budget, failure-code, and hierarchy tests**

Add a review-engine test that serializes a payload just over the ceiling and asserts the gateway is never called:

```python
def test_review_rejects_over_budget_complete_payload_before_gateway():
    gateway = RecordingGateway()
    engine = ReviewEngine(gateway)
    pack = evidence_pack_with_package_text("x" * 500_000)
    with pytest.raises(PackageCoverageUnavailable, match="request budget"):
        engine.review(pack)
    assert gateway.calls == []
```

Add an exact-boundary test using the serialized byte-sensitive estimator so a payload at the ceiling proceeds and one token above fails. Add safe-code and browser-label assertions:

```python
assert safe_failure_code(PackageCoverageUnavailable("secret")) == (
    "package_coverage_unavailable"
)
assert failureLabels.package_coverage_unavailable == (
    "The accompanying package could not be reviewed in full. "
    "Upload fewer, shorter, or text-searchable package documents."
)
```

Add prompt assertions for `primary CPF/CEN is the principal analytical lens`, `accompanying package evidence is detailed`, and `RRA and contextual evidence are thematic supporting lenses`.

- [ ] **Step 2: Run focused tests and confirm RED**

Run:

```powershell
C:\WBG\Python313\python.exe -m pytest -q tests/test_review_engine.py tests/test_routes.py tests/test_prompt_guardrails.py tests/test_task13_frontend_contract.py -k "budget or package_coverage or analytical_lens"
```

Expected: failures because no review-payload ceiling or package failure code exists.

- [ ] **Step 3: Add the exact serialized-input guard**

In `review_engine.py` add:

```python
import json

from .extraction import PackageCoverageUnavailable

REVIEW_MAX_ESTIMATED_INPUT_TOKENS = 160_000


def _estimated_input_tokens(payload: dict) -> int:
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (
        max(len(serialized), len(serialized.encode("utf-8"))) + 2
    ) // 3
```

Immediately after constructing the complete payload in `ReviewEngine.review`, before `gateway.generate`, add:

```python
if _estimated_input_tokens(payload) > REVIEW_MAX_ESTIMATED_INPUT_TOKENS:
    raise PackageCoverageUnavailable(
        "Complete review request exceeds the safe request budget."
    )
```

Add `PackageCoverageUnavailable` to `SAFE_FAILURES` in `orchestrator.py`. Add the generic label to `failureLabels` in `app.js`. Update `review.md` with the approved role hierarchy without changing ReviewDraft shape or reader-facing output structure.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run the Step 2 command.

Expected: all selected tests pass; no error details or document names appear in the client message.

- [ ] **Step 5: Commit request-budget and hierarchy behavior**

```powershell
git add -- prompts/review.md src/cpf_fcv_reviewer/orchestrator.py src/cpf_fcv_reviewer/review_engine.py src/cpf_fcv_reviewer/static/app.js tests/test_prompt_guardrails.py tests/test_review_engine.py tests/test_routes.py tests/test_task13_frontend_contract.py
git diff --cached --check
git commit -m "feat: enforce role-aware review coverage"
```

## Task 5: Integrated provider-free verification and documentation

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `docs/PROJECT_STATUS.md`
- Create: `docs/validation/2026-09-02-role-aware-source-coverage-validation.md`
- Modify only if smoke fixtures require the new valid RRA semantics: `src/cpf_fcv_reviewer/smoke.py`

- [ ] **Step 1: Run the full targeted source-coverage set**

Run:

```powershell
C:\WBG\Python313\python.exe -m pytest -q tests/test_extraction.py tests/test_diagnostic_map.py tests/test_evidence_builder.py tests/test_runtime_wiring.py tests/test_review_engine.py tests/test_prompt_guardrails.py tests/test_adversarial_matrix.py tests/test_routes.py tests/test_task13_frontend_contract.py
```

Expected: PASS. If Windows sandbox temp ACLs block pytest fixture setup, rerun the identical command with normal host temp access; do not change code to accommodate the environment.

- [ ] **Step 2: Run provider-free smoke and the complete local suite**

Run:

```powershell
C:\WBG\Python313\python.exe -m pytest -q -m smoke
C:\WBG\Python313\python.exe -m pytest -q
C:\WBG\Python313\python.exe -m compileall -q src tests
node --check src/cpf_fcv_reviewer/static/app.js
git diff --check
```

Expected: every command passes. Run Ruff only if installed:

```powershell
C:\WBG\Python313\python.exe -m ruff check .
```

If Ruff is unavailable, record that limitation once; do not install a new dependency for this cycle.

- [ ] **Step 3: Run provider-free browser and DOCX QA**

Start the deterministic smoke application and use the existing Playwright/browser harness. Save new unique full-page PNGs for intake with multiple package documents, holding/progress, Five-minute readout, Detailed analysis, streamed assistant response, refresh-restored conversation, correction/rerun, safe package failure, and mobile summary. Download the smoke DOCX.

Visually inspect every selected PNG. Validate the DOCX as ZIP/OOXML and structurally inspect headings, paragraphs, sections, expected reader-facing content, and absence of technical evidence registers or assistant transcripts. Render DOCX pages only if LibreOffice is available; otherwise record the existing environment limitation without claiming visual DOCX acceptance.

- [ ] **Step 4: Inspect the integrated diff directly**

Run:

```powershell
git status --short
git diff --stat 388f98c..HEAD
git diff 388f98c..HEAD -- src prompts tests README.md CLAUDE.md docs/PROJECT_STATUS.md docs/validation
git ls-files -- output/playwright '*.pdf' '*run-state.json'
```

Confirm the stable FCV Project Screener is untouched; no uploaded documents, raw model output, assistant conversations, secrets, live assessment IDs, browser artifacts, or DOCX files are tracked; and the diff contains no extra provider stage, retrieval service, dependency, or unrelated refactor.

- [ ] **Step 5: Update current documentation and create the validation record**

Document:

- the primary/package/context attention order;
- full bounded package extraction and exact package-input completeness;
- thematic representative RRA citations and removal of exact-once output mapping;
- safe package and RRA failure behavior;
- test counts and browser/DOCX evidence;
- Ruff/LibreOffice limitations if still applicable; and
- deployed/provider status as not yet run.

Do not edit historical validation records. Do not include input filenames, raw provider output, conversations, secrets, or assessment IDs.

- [ ] **Step 6: Commit and push the provider-free checkpoint**

```powershell
git add -- README.md CLAUDE.md docs/PROJECT_STATUS.md docs/validation/2026-09-02-role-aware-source-coverage-validation.md
git diff --cached --check
git diff --cached
git commit -m "docs: validate role-aware source coverage"
git push origin fix/guinea-production-fixes
```

- [ ] **Step 7: Stop before deployment**

Report the provider-free evidence, commit SHAs, remaining environmental limitations, and the exact proposed deployment commit. Seek separate user approval before moving the deployment branch, triggering Render, or submitting one paid Guinea assessment. Never rerun unchanged code.
