# Option B — Current-Context as Trusted Synthesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the current-context (live-news) section behave like a trusted-source-guided LLM synthesis — grade each claim (verified / partially verified / unverified) instead of deleting it, present it under a "verify before use" label with per-claim confidence chips, and make the `missing_current_context_support` check non-fatal so a review never fails solely for thin/unverified live news.

**Architecture:** Grade claims at the boundary where the verification checks already run (`public_research.py`), thread the grade through `CurrentContextClaim` → `EvidenceItem` → export, and add a two-value `severity` to `ValidationIssue` so `missing_current_context_support` becomes advisory (surfaced, never fatal). The evidence-tier logic in `research_controller` counts only recent + verified/partially-verified claims toward FULL/REDUCED; unverified claims are context-only and never elevate the tier. Every other check stays fully fail-closed.

**Tech Stack:** Python 3.13, Pydantic v2, Flask, pytest. Frontend: vanilla JS (`static/app.js`). DOCX via python-docx (`export_docx.py`). All tests are provider-free.

## Implementation status (2026-09-07)

Implemented and deployed through the Option B, FCV readout, and follow-up validation
releases. The full Guinea acceptance on `63b16da` reached `run_complete` with zero
independent current-context evidence and a six-theme context-only readout. The plan is
retained as the implementation record; current limitations and source-coverage work are
tracked in `docs/PROJECT_STATUS.md`.

**Spec:** `docs/superpowers/specs/2026-09-06-option-b-current-context-design.md`

**Pre-flight for every test run:** clear inherited CA env so pytest does not try the corporate proxy:
```bash
unset SSL_CERT_FILE REQUESTS_CA_BUNDLE CURL_CA_BUNDLE
```
Run tests from the worktree root: `.worktrees/option-b-current-context`.

---

## Reference: current claim/verification vocabulary

`CurrentContextClaim` (in `src/cpf_fcv_reviewer/public_research.py`) currently requires:
`claim_id, text, publisher, source_title, source_url, source_date, source_type, relevance,
context_kind, relationship, licensed_data_required` (+ optional `supporting_quote`,
`publication_date_basis`). This plan adds one field: `verification`.

The three grades and their meaning:
- `verified` — source has a resolved publication date **and** the supporting quote is an exact
  substring of the source excerpt (`_quote_is_from_source`).
- `partially_verified` — exactly one of {date present, exact quote} holds.
- `unverified` — neither holds.

Recency ("within the 24-month window") is enforced separately by `research_controller`, which
caps any non-recent claim to `unverified` and excludes unverified claims from tier elevation.

---

## Task 1: Add `verification` field + `_grade_claim` helper

**Files:**
- Modify: `src/cpf_fcv_reviewer/public_research.py` (add field to `CurrentContextClaim` ~`:133`; add helper near `_quote_is_from_source` ~`:1201`)
- Test: `tests/test_current_context_grading.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_current_context_grading.py
from cpf_fcv_reviewer.public_research import (
    ResearchSource,
    _grade_claim,
)


def _source(*, published, excerpt):
    return ResearchSource(
        title="Guinea security update",
        url="https://www.crisisgroup.org/guinea-update",
        publisher="International Crisis Group",
        published_at=published,
        excerpt=excerpt,
    )


def test_dated_source_with_verbatim_quote_grades_verified():
    from datetime import date

    source = _source(published=date(2025, 4, 30), excerpt="Armed clashes displaced thousands.")
    assert _grade_claim(source, "Armed clashes displaced thousands.") == "verified"


def test_dated_source_with_paraphrased_quote_grades_partial():
    from datetime import date

    source = _source(published=date(2025, 4, 30), excerpt="Armed clashes displaced thousands.")
    assert _grade_claim(source, "Thousands were displaced by clashes.") == "partially_verified"


def test_undated_source_with_verbatim_quote_grades_partial():
    source = _source(published=None, excerpt="Armed clashes displaced thousands.")
    assert _grade_claim(source, "Armed clashes displaced thousands.") == "partially_verified"


def test_undated_source_with_paraphrased_quote_grades_unverified():
    source = _source(published=None, excerpt="Armed clashes displaced thousands.")
    assert _grade_claim(source, "Thousands were displaced by clashes.") == "unverified"


def test_missing_quote_grades_unverified_when_undated():
    source = _source(published=None, excerpt="Armed clashes displaced thousands.")
    assert _grade_claim(source, None) == "unverified"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_current_context_grading.py -v`
Expected: FAIL with `ImportError: cannot import name '_grade_claim'`

- [ ] **Step 3: Add the `verification` field to `CurrentContextClaim`**

In `src/cpf_fcv_reviewer/public_research.py`, inside `class CurrentContextClaim`, add the field
directly after `licensed_data_required: StrictBool` (~`:159`):

```python
    licensed_data_required: StrictBool
    verification: Literal["verified", "partially_verified", "unverified"] = "unverified"
```

(`Literal` is already imported from `typing` at the top of the file.)

- [ ] **Step 4: Add the `_grade_claim` helper**

In `src/cpf_fcv_reviewer/public_research.py`, add immediately after `_quote_is_from_source`
(~`:1206`):

```python
def _grade_claim(
    source: "ResearchSource", supporting_quote: str | None
) -> Literal["verified", "partially_verified", "unverified"]:
    """Grade a floor-passing claim by how strongly it is machine-verifiable.

    Recency is enforced separately by the research controller, which caps non-recent
    claims to ``unverified`` and excludes them from evidence-tier elevation.
    """
    has_date = source.published_at is not None
    has_exact_quote = _quote_is_from_source(supporting_quote, source.excerpt)
    if has_date and has_exact_quote:
        return "verified"
    if has_date or has_exact_quote:
        return "partially_verified"
    return "unverified"
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_current_context_grading.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add src/cpf_fcv_reviewer/public_research.py tests/test_current_context_grading.py
git commit -m "feat: add current-context claim grading helper and verification field"
```

---

## Task 2: Grade instead of drop in normalization + salvage

**Files:**
- Modify: `src/cpf_fcv_reviewer/public_research.py` — `_validate_normalized_claims` (~`:1318`) and `_salvage_grounded_segments` (~`:1358`)
- Test: `tests/test_current_context_grading.py` (append)

The floor (permitted public source, country match, non-licensed) is unchanged and still drops.
Only the two soft checks (date, exact quote) stop causing a drop — they now set the grade.

- [ ] **Step 1: Write the failing test (append)**

```python
def test_salvage_keeps_undated_source_as_unverified():
    from datetime import date
    from cpf_fcv_reviewer.public_research import (
        ResearchSource,
        _salvage_grounded_segments,
    )

    dated = ResearchSource(
        title="Guinea update",
        url="https://www.crisisgroup.org/guinea-a",
        publisher="International Crisis Group",
        published_at=date(2025, 4, 30),
        excerpt="Armed clashes displaced thousands in Guinea.",
    )
    undated = ResearchSource(
        title="Guinea update B",
        url="https://www.crisisgroup.org/guinea-b",
        publisher="International Crisis Group",
        published_at=None,
        excerpt="Security incidents were reported across Guinea.",
    )
    segments = (
        ("Armed clashes displaced thousands in Guinea.", (dated,)),
        ("Security incidents were reported across Guinea.", (undated,)),
    )
    claims = _salvage_grounded_segments(segments, selected_country="Guinea")
    grades = {claim.source_url: claim.verification for claim in claims}
    # Both are kept; the undated one is graded rather than deleted.
    assert grades["https://www.crisisgroup.org/guinea-a"] == "verified"
    assert grades["https://www.crisisgroup.org/guinea-b"] == "partially_verified"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_current_context_grading.py::test_salvage_keeps_undated_source_as_unverified -v`
Expected: FAIL — currently the undated source is dropped, so `guinea-b` is absent from `grades` (KeyError).

- [ ] **Step 3: Update `_salvage_grounded_segments` to grade, not drop on soft checks**

In `_salvage_grounded_segments`, the current loop skips a segment when
`source.published_at is None`. Change the guard so **only floor conditions** skip, and the
date no longer forces a skip. Replace the condition block (~`:1367`):

```python
            supporting_quote = cited_text.strip()
            if (
                source.published_at is None
                or source.publisher == "ReliefWeb"
                or supporting_quote is None
                or not _is_unambiguous_single_sentence(supporting_quote)
                or not _text_mentions_country(supporting_quote, selected_country)
            ):
                continue
```

with:

```python
            supporting_quote = cited_text.strip()
            if (
                source.publisher == "ReliefWeb"
                or not supporting_quote
                or not _is_unambiguous_single_sentence(supporting_quote)
                or not _text_mentions_country(supporting_quote, selected_country)
            ):
                continue
```

Then, in the same function, when the `CurrentContextClaim(...)` is constructed (~`:1389`), add the
grade and make `source_date` tolerate a missing date. First, above the append, compute:

```python
            grade = _grade_claim(source, supporting_quote)
```

Change the digest and claim to use a stable date sentinel for undated sources. Replace the
`digest_input` `source_date` line and the `CurrentContextClaim(...)` `source_date=` / add
`verification=`:

```python
            digest_input = json.dumps(
                {
                    "source_date": source.published_at.isoformat()
                    if source.published_at is not None
                    else "undated",
                    "source_title": source.title,
                    "source_url": source.url,
                    "text": supporting_quote,
                },
                sort_keys=True,
            ).encode("utf-8")
            claims.append(
                CurrentContextClaim(
                    claim_id=f"sha256:{hashlib.sha256(digest_input).hexdigest()}",
                    text=supporting_quote,
                    publisher=_publisher_from_source(source),
                    source_title=source.title,
                    source_url=source.url,
                    source_date=source.published_at or date(1900, 1, 1),
                    supporting_quote=supporting_quote,
                    publication_date_basis=source.publication_date_basis,
                    source_type="public institutional source",
                    relevance="Salvaged from a cited source excerpt.",
                    context_kind="current_development",
                    relationship="establishes",
                    licensed_data_required=False,
                    verification=grade,
                )
            )
```

(`date` is already imported at the top: `from datetime import date, datetime`.)

- [ ] **Step 4: Update `_validate_normalized_claims` to grade, not drop on soft checks**

In `_validate_normalized_claims` (~`:1325`), the current guard drops a claim when
`source.published_at is None` or the quote is not an exact substring. Change it so those two
conditions set the grade instead of dropping, while the floor (source present, country match)
still drops. Replace the guard block:

```python
        supporting_quote = _as_nonblank_string(claim.supporting_quote)
        if (
            source.published_at is None
            or source.publisher == "ReliefWeb"
            or not _quote_is_from_source(supporting_quote, source.excerpt)
            or not _text_mentions_country(supporting_quote, selected_country)
        ):
            continue
        matched_claims.append(
            claim.model_copy(
                update={
                    "text": supporting_quote,
                    "publisher": _publisher_from_source(source),
                    "source_title": source.title,
                    "source_url": source.url,
                    "source_date": source.published_at,
                    "supporting_quote": supporting_quote,
                    "publication_date_basis": source.publication_date_basis,
                }
            )
        )
```

with:

```python
        supporting_quote = _as_nonblank_string(claim.supporting_quote)
        if (
            source.publisher == "ReliefWeb"
            or not supporting_quote
            or not _text_mentions_country(supporting_quote, selected_country)
        ):
            continue
        grade = _grade_claim(source, supporting_quote)
        matched_claims.append(
            claim.model_copy(
                update={
                    "text": supporting_quote,
                    "publisher": _publisher_from_source(source),
                    "source_title": source.title,
                    "source_url": source.url,
                    "source_date": source.published_at or date(1900, 1, 1),
                    "supporting_quote": supporting_quote,
                    "publication_date_basis": source.publication_date_basis,
                    "verification": grade,
                }
            )
        )
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_current_context_grading.py tests/test_public_research.py -v`
Expected: PASS. If any existing `test_public_research.py` test asserted that an undated or
paraphrased claim is dropped, update that test to assert it is now retained with the expected
grade (that is the intended behaviour change) and note it in the commit message.

- [ ] **Step 6: Commit**

```bash
git add src/cpf_fcv_reviewer/public_research.py tests/test_current_context_grading.py tests/test_public_research.py
git commit -m "feat: grade current-context claims instead of deleting on soft checks"
```

---

## Task 3: Recency cap + tier honesty in the controller

**Files:**
- Modify: `src/cpf_fcv_reviewer/research_controller.py` — `_qualifying_claims` (~`:540`), add a recency-cap pass
- Test: `tests/test_research_controller.py` (append)

Goal: (a) a non-recent claim is capped to `unverified`; (b) `unverified` claims do not count
toward the FULL/REDUCED evidence tier. Verified/partially-verified recent claims still can.

- [ ] **Step 1: Write the failing test (append to `tests/test_research_controller.py`)**

```python
def test_recency_cap_downgrades_non_recent_claim():
    from datetime import date
    from cpf_fcv_reviewer.research_controller import _cap_verification_by_recency

    assert _cap_verification_by_recency("verified", is_recent=True) == "verified"
    assert _cap_verification_by_recency("verified", is_recent=False) == "unverified"
    assert _cap_verification_by_recency("partially_verified", is_recent=False) == "unverified"
    assert _cap_verification_by_recency("unverified", is_recent=True) == "unverified"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_research_controller.py::test_recency_cap_downgrades_non_recent_claim -v`
Expected: FAIL with `ImportError: cannot import name '_cap_verification_by_recency'`

- [ ] **Step 3: Add the recency-cap helper and apply it in `_qualifying_claims`**

In `src/cpf_fcv_reviewer/research_controller.py`, add a module-level helper near
`_subtract_calendar_years` (~`:806`):

```python
def _cap_verification_by_recency(verification: str, *, is_recent: bool) -> str:
    if not is_recent:
        return "unverified"
    return verification
```

In `_qualifying_claims` (~`:540`), after computing whether each claim is recent, apply the cap
so the returned claims carry an honest grade. Replace the `qualifying = sorted(...)` construction
so it also caps verification:

```python
        graded = tuple(
            claim.model_copy(
                update={
                    "verification": _cap_verification_by_recency(
                        claim.verification,
                        is_recent=self._is_recent(claim, request),
                    )
                }
            )
            for claim in claims
        )
        qualifying = sorted(
            (
                claim
                for claim in graded
                if self._is_recent(claim, request)
                and self._is_substantive_fcv(claim)
            ),
            key=lambda claim: (-claim.source_date.toordinal(), claim.claim_id),
        )
```

- [ ] **Step 4: Exclude `unverified` claims from tier-elevation counting**

Still in `research_controller.py`, `_missing_coverage` (~`:677`) decides FULL vs REDUCED by
counting claims/publishers/kinds. Make it count only non-`unverified` claims so a page of
context-only claims cannot reach FULL. At the top of `_missing_coverage`, add:

```python
        claims = tuple(
            claim for claim in claims if claim.verification != "unverified"
        )
```

(Leave the rest of the function unchanged — `_qualifying_claims` still returns unverified claims
for display; only the coverage/tier decision ignores them.)

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_research_controller.py -v`
Expected: PASS. Update any existing tier test that assumed undated claims were dropped — a page
of unverified claims should now yield REDUCED/DOCUMENT_LED, not FULL.

- [ ] **Step 6: Commit**

```bash
git add src/cpf_fcv_reviewer/research_controller.py tests/test_research_controller.py
git commit -m "feat: cap non-recent claims to unverified and keep evidence tiers honest"
```

---

## Task 4: Ambiguous-country search disambiguation

**Files:**
- Modify: `src/cpf_fcv_reviewer/research_controller.py` — add `AMBIGUOUS_COUNTRY_QUALIFIERS`, inject into `_prompt` (~`:630`)
- Test: `tests/test_research_controller.py` (append)

- [ ] **Step 1: Write the failing test (append)**

```python
def test_prompt_disambiguates_ambiguous_country():
    from datetime import date
    from cpf_fcv_reviewer.research_controller import (
        ResearchController,
        ResearchRequest,
        ResearchMode,
    )

    controller = ResearchController(gateway=object())
    request = ResearchRequest(
        country="Guinea",
        review_date=date(2026, 9, 1),
        mode=ResearchMode.HOLISTIC,
    )
    prompt = controller._prompt(request, attempt=1, missing=())
    assert "not Guinea-Bissau" in prompt
    assert "not Equatorial Guinea" in prompt


def test_prompt_leaves_unambiguous_country_unqualified():
    from datetime import date
    from cpf_fcv_reviewer.research_controller import (
        ResearchController,
        ResearchRequest,
        ResearchMode,
    )

    controller = ResearchController(gateway=object())
    request = ResearchRequest(
        country="Kenya",
        review_date=date(2026, 9, 1),
        mode=ResearchMode.HOLISTIC,
    )
    prompt = controller._prompt(request, attempt=1, missing=())
    assert "not " not in prompt.split("country:")[1].splitlines()[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_research_controller.py::test_prompt_disambiguates_ambiguous_country -v`
Expected: FAIL (`AssertionError` — qualifier not present)

- [ ] **Step 3: Add the qualifier map and inject it**

In `src/cpf_fcv_reviewer/research_controller.py`, add near the other module constants (~`:58`):

```python
AMBIGUOUS_COUNTRY_QUALIFIERS = {
    "guinea": "Guinea (Conakry) — not Guinea-Bissau, not Equatorial Guinea, not Papua New Guinea",
    "congo": "Republic of the Congo (Brazzaville) — not the Democratic Republic of the Congo",
    "niger": "Niger (Niamey) — not Nigeria",
}
```

In `_prompt`, where the `country:` line is added (~`:639`), append a qualifier line when the
canonicalised country name matches. Replace:

```python
            f"country: {request.country.strip()}",
```

with:

```python
            f"country: {request.country.strip()}",
            *(
                (f"country_disambiguation: {qualifier}",)
                for qualifier in (
                    AMBIGUOUS_COUNTRY_QUALIFIERS.get(
                        " ".join(request.country.casefold().split())
                    ),
                )
                if qualifier
            ),
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_research_controller.py::test_prompt_disambiguates_ambiguous_country tests/test_research_controller.py::test_prompt_leaves_unambiguous_country_unqualified -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/cpf_fcv_reviewer/research_controller.py tests/test_research_controller.py
git commit -m "feat: disambiguate ambiguous country names in research prompt"
```

---

## Task 5: Thread `verification` onto the current-context `EvidenceItem`

**Files:**
- Modify: `src/cpf_fcv_reviewer/contracts.py` — `EvidenceItem` (~`:144`)
- Modify: `src/cpf_fcv_reviewer/runtime.py` — `build_uploaded_evidence` current-context loop (~`:982`)
- Test: `tests/test_contracts.py` (append) + `tests/test_evidence_builder.py` (append if present)

- [ ] **Step 1: Write the failing test (append to `tests/test_contracts.py`)**

```python
def test_current_context_evidence_carries_verification():
    from datetime import date
    from cpf_fcv_reviewer.contracts import EvidenceItem

    item = EvidenceItem(
        evidence_id="current-001",
        evidence_type="current_context",
        text="Armed clashes displaced thousands.",
        confidence="medium",
        source_url="https://www.crisisgroup.org/guinea",
        source_title="Guinea update",
        source_publisher="International Crisis Group",
        source_date=date(2025, 4, 30),
        supporting_quote="Armed clashes displaced thousands.",
        verification="verified",
    )
    assert item.verification == "verified"


def test_verification_defaults_to_unverified():
    from datetime import date
    from cpf_fcv_reviewer.contracts import EvidenceItem

    item = EvidenceItem(
        evidence_id="current-002",
        evidence_type="current_context",
        text="Security incidents reported.",
        confidence="low",
        source_url="https://www.crisisgroup.org/guinea-b",
    )
    assert item.verification == "unverified"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_contracts.py::test_current_context_evidence_carries_verification -v`
Expected: FAIL (`ValidationError: extra fields not permitted` or `AttributeError`)

- [ ] **Step 3: Add the field to `EvidenceItem`**

In `src/cpf_fcv_reviewer/contracts.py`, inside `class EvidenceItem`, add after `document_role`
(~`:169`):

```python
    document_role: DocumentRole | None = None
    verification: Literal["verified", "partially_verified", "unverified"] = "unverified"
```

(`Literal` is already imported in `contracts.py`.)

- [ ] **Step 4: Copy the grade in `build_uploaded_evidence`**

In `src/cpf_fcv_reviewer/runtime.py`, in the current-context loop that builds `EvidenceItem`
from `context["research_result"].claims` (~`:987`), add the grade to the constructor. After the
`confidence=(...)` argument, add:

```python
                    confidence=(
                        "high"
                        if _is_explicit_authoritative_claim(claim)
                        else "medium"
                    ),
                    verification=claim.verification,
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_contracts.py tests/test_evidence_builder.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/cpf_fcv_reviewer/contracts.py src/cpf_fcv_reviewer/runtime.py tests/test_contracts.py
git commit -m "feat: carry current-context verification grade onto evidence items"
```

---

## Task 6: Add `severity` to `ValidationIssue`; mark current-context support advisory

**Files:**
- Modify: `src/cpf_fcv_reviewer/validators.py` — `ValidationIssue` (~`:198`), `_append_current_context_support_issue` (~`:682`)
- Modify: `src/cpf_fcv_reviewer/runtime.py` — `review_validation_issues` (~`:1207`) to include `severity` in each issue dict
- Test: `tests/test_current_context_advisory.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_current_context_advisory.py
from cpf_fcv_reviewer.validators import ValidationIssue


def test_validation_issue_defaults_to_fatal_severity():
    issue = ValidationIssue("stage_overreach", "example")
    assert issue.severity == "fatal"


def test_missing_current_context_support_is_advisory():
    issue = ValidationIssue(
        "missing_current_context_support", "example", severity="advisory"
    )
    assert issue.severity == "advisory"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_current_context_advisory.py -v`
Expected: FAIL (`TypeError: __init__() got an unexpected keyword argument 'severity'`)

- [ ] **Step 3: Add `severity` to the dataclass**

In `src/cpf_fcv_reviewer/validators.py`, change the `ValidationIssue` dataclass (~`:198`):

```python
@dataclass(frozen=True)
class ValidationIssue:
    code: ValidationIssueCode
    message: str
    severity: Literal["fatal", "advisory"] = "fatal"
```

(`Literal` is already imported in `validators.py`.)

- [ ] **Step 4: Mark the current-context support issue advisory**

In `_append_current_context_support_issue` (~`:682`), the single `issues.append(...)` builds a
`ValidationIssue("missing_current_context_support", ...)`. Add `severity="advisory"`:

```python
        issues.append(
            ValidationIssue(
                "missing_current_context_support",
                f"{priority_area.priority_area_id} cites current-context evidence that "
                f"does not substantively support its present-day FCV claim: {unsupported}.",
                severity="advisory",
            )
        )
```

- [ ] **Step 5: Include `severity` in the issue dicts**

In `src/cpf_fcv_reviewer/runtime.py`, `review_validation_issues` (~`:1207`) returns
`[{"code": issue.code, "message": issue.message} for issue in issues]`. Change it to carry
severity (default fatal for the reproducibility issues, which are plain and have no severity
attr only if constructed without it — but they are `ValidationIssue` too, so `.severity` exists):

```python
        return [
            {
                "code": issue.code,
                "message": issue.message,
                "severity": getattr(issue, "severity", "fatal"),
            }
            for issue in issues
        ]
```

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_current_context_advisory.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/cpf_fcv_reviewer/validators.py src/cpf_fcv_reviewer/runtime.py tests/test_current_context_advisory.py
git commit -m "feat: mark missing_current_context_support as an advisory validation issue"
```

---

## Task 7: Orchestrator gates repair/fail on fatal severity only

**Files:**
- Modify: `src/cpf_fcv_reviewer/orchestrator.py` — `run` (~`:55`)
- Test: `tests/test_orchestrator.py` (append)

- [ ] **Step 1: Write the failing test (append to `tests/test_orchestrator.py`)**

```python
def test_advisory_only_issues_do_not_fail_the_run():
    from cpf_fcv_reviewer.orchestrator import ReviewOrchestrator

    events = []

    def emit(name, data):
        events.append((name, data))

    def validate(context):
        context["validation_issues"] = [
            {
                "code": "missing_current_context_support",
                "message": "advisory",
                "severity": "advisory",
            }
        ]
        return context

    def repair(context, issues):
        raise AssertionError("repair must not run for advisory-only issues")

    orchestrator = ReviewOrchestrator(
        steps=(("validate", validate),),
        repair=repair,
    )
    orchestrator.run({}, emit)
    names = [name for name, _ in events]
    assert "run_complete" in names
    assert "run_failed" not in names
    assert "repair_start" not in names


def test_fatal_issue_still_repairs_and_can_fail():
    from cpf_fcv_reviewer.orchestrator import ReviewOrchestrator

    events = []

    def emit(name, data):
        events.append((name, data))

    def validate(context):
        context["validation_issues"] = [
            {"code": "stage_overreach", "message": "fatal", "severity": "fatal"}
        ]
        return context

    def repair(context, issues):
        # repair does not clear the fatal issue
        context["validation_issues"] = [
            {"code": "stage_overreach", "message": "fatal", "severity": "fatal"}
        ]
        return context

    orchestrator = ReviewOrchestrator(
        steps=(("validate", validate),),
        repair=repair,
    )
    try:
        orchestrator.run({}, emit)
    except ValueError:
        pass
    names = [name for name, _ in events]
    assert "repair_start" in names
    assert "run_failed" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_orchestrator.py::test_advisory_only_issues_do_not_fail_the_run -v`
Expected: FAIL — the current orchestrator treats any non-empty `validation_issues` as fatal, so
it calls `repair` (hitting the `AssertionError`).

- [ ] **Step 3: Partition issues by severity in `run`**

In `src/cpf_fcv_reviewer/orchestrator.py`, replace the `if name == "validate" and
context.get("validation_issues"):` block (~`:63`) so it only repairs/fails on fatal issues and
surfaces advisory ones without failing:

```python
                if name == "validate" and context.get("validation_issues"):
                    all_issues = list(context["validation_issues"])
                    fatal_issues = [
                        issue
                        for issue in all_issues
                        if not (
                            isinstance(issue, dict)
                            and issue.get("severity") == "advisory"
                        )
                    ]
                    advisory_issues = [
                        issue
                        for issue in all_issues
                        if isinstance(issue, dict)
                        and issue.get("severity") == "advisory"
                    ]
                    if advisory_issues:
                        emit(
                            "advisory_notice",
                            {
                                "issue_count": len(advisory_issues),
                                "codes": list(
                                    dict.fromkeys(
                                        issue["code"]
                                        for issue in advisory_issues
                                        if isinstance(issue, dict)
                                        and isinstance(issue.get("code"), str)
                                    )
                                ),
                            },
                        )
                    if fatal_issues:
                        if repaired:
                            raise ValueError("Validation failed after the only repair.")
                        emit(
                            "repair_start",
                            {
                                "issue_count": len(fatal_issues),
                                "codes": list(
                                    dict.fromkeys(
                                        issue["code"]
                                        for issue in fatal_issues
                                        if isinstance(issue, dict)
                                        and isinstance(issue.get("code"), str)
                                    )
                                ),
                            },
                        )
                        context = self.repair(context, fatal_issues)
                        repaired = True
                        remaining_fatal = [
                            issue
                            for issue in context.get("validation_issues", [])
                            if not (
                                isinstance(issue, dict)
                                and issue.get("severity") == "advisory"
                            )
                        ]
                        if remaining_fatal:
                            emit(
                                "repair_failed",
                                {
                                    "issue_count": len(remaining_fatal),
                                    "codes": list(
                                        dict.fromkeys(
                                            issue["code"]
                                            for issue in remaining_fatal
                                            if isinstance(issue, dict)
                                            and isinstance(issue.get("code"), str)
                                        )
                                    ),
                                },
                            )
                            raise ValueError("Validation failed after the only repair.")
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_orchestrator.py -v`
Expected: PASS (both new tests + existing orchestrator tests). Existing tests that pass issues as
bare strings still count as fatal because `issue.get` is guarded by `isinstance(issue, dict)`.

- [ ] **Step 5: Commit**

```bash
git add src/cpf_fcv_reviewer/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: gate orchestrator repair and failure on fatal severity only"
```

---

## Task 8: Tiered-influence guidance in the review prompt

**Files:**
- Modify: `prompts/review.md`
- Test: `tests/test_review_prompt.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_review_prompt.py
from cpf_fcv_reviewer.prompts import load_prompt


def test_review_prompt_states_tiered_current_context_influence():
    prompt = load_prompt("review").casefold()
    assert "verify before use" in prompt
    assert "partially verified" in prompt
    assert "unverified" in prompt
    # unverified current context must be context-only
    assert "context only" in prompt or "context-only" in prompt
```

(Confirm the import: `from cpf_fcv_reviewer.prompts import load_prompt` — the module already
exposes `load_prompt` used in `runtime.py`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_review_prompt.py -v`
Expected: FAIL (`AssertionError` — phrases absent)

- [ ] **Step 3: Add the guidance to `prompts/review.md`**

Append a section to `prompts/review.md` (place it with the other current-context / evidence
instructions):

```markdown
## Current-context evidence: confidence tiers

Current-context evidence carries a `verification` grade. Treat it as an AI-generated synthesis
from trusted sources that the reader must verify before use:

- `verified` — you may use it to support an FCV Strategy rating and to justify a priority
  recommendation.
- `partially verified` — you may cite it as corroboration, but it must not be the sole basis of
  a rating change or a recommendation.
- `unverified` — you may use it only as context-only narrative framing of present-day conditions.
  It must not, on its own, change a rating or generate a recommendation.

Never present current-context claims as established fact. When a present-day FCV assertion rests
only on partially verified or unverified evidence, phrase it as reported/indicative and keep it
context only.
```

- [ ] **Step 4: Run test**

Run: `python -m pytest tests/test_review_prompt.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add prompts/review.md tests/test_review_prompt.py
git commit -m "feat: instruct tiered current-context influence in the review prompt"
```

---

## Task 9: Export banner + per-claim chips (DOCX + frontend)

**Files:**
- Modify: `src/cpf_fcv_reviewer/export_docx.py` — `_evidence_type_label` / `locator_text` region (~`:287`)
- Modify: `src/cpf_fcv_reviewer/static/app.js` — current-context evidence rendering (~`:557`)
- Test: `tests/test_docx_export.py` (append); `tests/test_frontend_contract.py` (append)

- [ ] **Step 1: Write the failing DOCX test (append to `tests/test_docx_export.py`)**

```python
def test_docx_labels_current_context_verification():
    from cpf_fcv_reviewer.export_docx import current_context_chip_label

    assert current_context_chip_label("verified") == "Verified"
    assert current_context_chip_label("partially_verified") == "Partially verified — verify before use"
    assert current_context_chip_label("unverified") == "Unverified — verify before use"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_docx_export.py::test_docx_labels_current_context_verification -v`
Expected: FAIL (`ImportError: cannot import name 'current_context_chip_label'`)

- [ ] **Step 3: Add the chip label helper and use it in the current-context evidence line**

In `src/cpf_fcv_reviewer/export_docx.py`, add near `_evidence_type_label` (~`:287`):

```python
def current_context_chip_label(verification: str) -> str:
    return {
        "verified": "Verified",
        "partially_verified": "Partially verified — verify before use",
        "unverified": "Unverified — verify before use",
    }.get(verification, "Unverified — verify before use")
```

In `locator_text` (~`:297`), where a `current_context` item is labelled, append the chip:

```python
def locator_text(item: EvidenceItem) -> str:
    parts = []
    if item.evidence_type == "current_context":
        parts.append(_evidence_type_label(item))
        parts.append(current_context_chip_label(item.verification))
    if item.locator is not None:
        parts.append(target_text(item.locator))
    if item.source_url:
        parts.append(item.source_url)
    if not parts:
        parts.append(_evidence_type_label(item))
    return " | ".join(parts)
```

If the DOCX has a dedicated current-context section header, add the banner text there. If the
current-context evidence is only rendered inline (as above), the per-item "verify before use"
chip satisfies the requirement; add a one-line banner where the current-context group is
introduced. Locate the current-context section heading in `export_docx.py` (search for the
"Current context" section title) and insert, immediately under it:

```python
        document.add_paragraph(
            "AI-generated from trusted sources — verify before use."
        )
```

- [ ] **Step 4: Write the failing frontend test (append to `tests/test_frontend_contract.py`)**

The frontend tests assert on the contents of `static/app.js` as text. Add:

```python
def test_app_js_renders_current_context_verification_banner():
    from pathlib import Path

    app_js = Path("src/cpf_fcv_reviewer/static/app.js").read_text(encoding="utf-8")
    assert "AI-generated from trusted sources" in app_js
    assert "verify before use" in app_js.casefold()
    # per-claim chip classes / labels present
    assert "partially verified" in app_js.casefold()
```

- [ ] **Step 5: Run frontend test to verify it fails**

Run: `python -m pytest tests/test_frontend_contract.py::test_app_js_renders_current_context_verification_banner -v`
Expected: FAIL

- [ ] **Step 6: Add the banner + chips to `static/app.js`**

In `src/cpf_fcv_reviewer/static/app.js`, find the current-context evidence label map (~`:557`,
`current_context: "Current context"`). Add a verification-label map and a chip renderer nearby:

```javascript
const CURRENT_CONTEXT_VERIFICATION_LABEL = {
  verified: "Verified",
  partially_verified: "Partially verified — verify before use",
  unverified: "Unverified — verify before use",
};

function currentContextChip(verification) {
  const label =
    CURRENT_CONTEXT_VERIFICATION_LABEL[verification] ||
    CURRENT_CONTEXT_VERIFICATION_LABEL.unverified;
  const chip = text("span", label);
  chip.className = "current-context-chip current-context-chip--" + (verification || "unverified");
  return chip;
}
```

Where the current-context evidence group is rendered, add the banner once at the top of the
group:

```javascript
  const banner = text("p", "AI-generated from trusted sources — verify before use");
  banner.className = "current-context-banner";
  container.append(banner);
```

and append `currentContextChip(item.verification)` to each current-context evidence row. (Use the
existing `text(tag, content)` helper already imported in this file; match the surrounding DOM
construction style.)

- [ ] **Step 7: Run tests**

Run: `python -m pytest tests/test_docx_export.py tests/test_frontend_contract.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/cpf_fcv_reviewer/export_docx.py src/cpf_fcv_reviewer/static/app.js tests/test_docx_export.py tests/test_frontend_contract.py
git commit -m "feat: render current-context verify-before-use banner and per-claim chips"
```

---

## Task 10: Full suite, provider-free smoke, status update

**Files:**
- Modify: `docs/PROJECT_STATUS.md`
- Test: full suite

- [ ] **Step 1: Run the complete provider-free suite**

```bash
unset SSL_CERT_FILE REQUESTS_CA_BUNDLE CURL_CA_BUNDLE
python -m pytest -q
```
Expected: all pass. Fix any test that encoded the old delete-and-fail behaviour by updating it to
the new grade-and-keep / advisory behaviour (these are intended changes; call them out in the
commit).

- [ ] **Step 2: Run the provider-free browser smoke (if the runner is available)**

Run the repository's smoke runner (see `scripts/` / `smoke.py`) against the deterministic
synthetic service. Expected: `BROWSER_QA_PASS`, a valid DOCX, and a current-context section that
shows the banner and graded chips. Save PNGs/DOCX under a unique gitignored `output/` folder.

- [ ] **Step 3: Update `docs/PROJECT_STATUS.md`**

Add a dated entry summarising Option B: current-context is now graded (verified / partially
verified / unverified), presented under a verify-before-use label with per-claim chips;
`missing_current_context_support` is advisory (non-fatal); tier counting excludes unverified
claims; ambiguous country names are disambiguated in the search prompt. Note that the change is
scoped to the current-context path and that the paid Guinea run remains the acceptance gate and
is not yet run.

- [ ] **Step 4: Commit**

```bash
git add docs/PROJECT_STATUS.md
git commit -m "docs: record Option B current-context synthesis change"
```

- [ ] **Step 5: STOP — request maintainer authorization for the paid Guinea run**

Do **not** trigger a paid assessment automatically. Present the provider-free results and ask the
maintainer to authorise the single paid Guinea CPF+RRA acceptance run
(`guineacpf.pdf` + `guinearra.pdf`). Only after explicit authorization: deploy the branch, run
`/health`, then submit exactly one paid run; capture the Render log line and terminal event; a
"good" outcome is `run_complete` with a labelled current-context section and no `review_failed`
for thin live news.

---

## Self-review notes (coverage against the spec)

- Spec §4 confidence model → Tasks 1–3 (grading + recency cap + tier honesty).
- Spec §5.1 grade instead of drop → Task 2.
- Spec §5.2 tier honesty + disambiguation → Tasks 3, 4.
- Spec §5.3 thread grade through evidence → Task 5.
- Spec §5.4 advisory severity → Task 6.
- Spec §5.5 orchestrator fatal-only gating → Task 7.
- Spec §5.6 review-prompt tiered influence → Task 8.
- Spec §5.7 banner + chips (DOCX + HTML) → Task 9.
- Spec §6 scope guard → severity defaults to `fatal`; only two current-context codes are advisory.
- Spec §7 testing + paid-run gate → Task 10 (with the money-action stop).
