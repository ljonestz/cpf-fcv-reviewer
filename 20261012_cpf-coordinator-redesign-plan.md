# CPF coordinator review redesign implementation plan

> For agentic workers: execute this plan task by task using
> superpowers:executing-plans. Keep implementation inline unless a bounded
> delegation is explicitly authorised and the requested model is available.
> Preserve the user's stage limits and scope; do not invent extra approval gates.

**Goal:** Implement the agreed coordinator drafting workflow with four concise
findings, a grounded unsigned email and optional feedback.

**Architecture:** Extend the existing review contracts, evidence pipeline,
validation, session state and presentation. Separate prior-comment follow-through
from independent review, and draft the email only from validated findings. Keep
existing provider configuration, reference approval, source coverage and bounded
repair; confidential references stay outside the public repository.

**Tech stack:** Existing Python 3.13, Flask, Pydantic, SQLite session storage,
python-docx, Anthropic gateway and existing HTML/CSS/browser JavaScript.
No new framework or dependency.

**Specification:** 20261012_cpf-coordinator-redesign-spec.md.
**Baseline:** a210b29, refreshed origin/main, including the October package-reading
and evidence fixes. Worktree:
.worktrees/20261012-coordinator-review-redesign.
**Branch:** feat/coordinator-review-redesign.

## Verified planning baseline

The existing provider-free smoke suite passed 38 tests on this worktree on
12 October 2026. A pytest cache-write warning occurred; it did not fail the tests.
Use -p no:cacheprovider for later runs in this environment.

The requested GPT-5.6 Luna model is not among the available model overrides.
Do not silently replace it with a different model. Inline execution is sufficient
for these sequential changes.

The current source already supports full primary reading, up to 40 package
documents, validated digests, diagnostic provenance, all four Strategy shifts,
stage profiles, child-review corrections, refresh restoration and native Word
exports. Retain those behaviours.

## File responsibilities

| Area | Existing files / focused additions |
| --- | --- |
| Typed findings and destinations | src/cpf_fcv_reviewer/contracts.py |
| Stage and editorial constraints | src/cpf_fcv_reviewer/review_profiles.py; prompts/review.md; prompts/repair.md; prompts/follow_on.md |
| Source separation and integration | src/cpf_fcv_reviewer/runtime.py; src/cpf_fcv_reviewer/review_engine.py; new src/cpf_fcv_reviewer/prior_comments.py |
| Validation and reference checks | src/cpf_fcv_reviewer/validators.py; src/cpf_fcv_reviewer/reproducibility.py |
| Email generation and validation | new src/cpf_fcv_reviewer/email_draft.py; new prompts/peer_email.md |
| Intake, email edits and feedback | src/cpf_fcv_reviewer/routes.py; existing session_store.py / persistent_store.py only if current payload methods are insufficient |
| Views and download | src/cpf_fcv_reviewer/templates/index.html; static/app.js; static/styles.css; export_docx.py |
| Deterministic services | src/cpf_fcv_reviewer/smoke.py; tests/conftest.py |
| Tests and living status | focused tests named below; README.md; docs/PROJECT_STATUS.md; new dated validation record |

Existing files are updated because the user explicitly requested an update to the
reviewer. New planning and validation artifacts use dated, non-overwriting names.

## Task 1: Extend the result contract without weakening legacy or evidence checks

**Files:** contracts.py, validators.py, reproducibility.py, review_engine.py,
smoke.py, tests/conftest.py; new tests/test_coordinator_findings.py.

- [ ] Add the four question identifiers and explicit recommendation destinations:

```python
class CoreQuestion(StrEnum):
    DRIVERS_PRIORITIES = "drivers_priorities"
    ACTIONS_COMMITMENT = "actions_commitment"
    PROGRAM_IMPLICATIONS = "program_implications"
    IF_THEN_CALIBRATION = "if_then_calibration"


class RecommendationDestination(StrEnum):
    CPF_TEXT = "cpf_text"
    RESULTS_FRAMEWORK = "results_framework"
    MEETING_RECORD = "meeting_record"
    ANNUAL_BUSINESS_PLANNING = "annual_business_planning"


class CoreFinding(FrozenModel):
    question: CoreQuestion
    assessment: ReviewNarrative
    basis: Literal["assessed", "limited"]
    evidence_ids: tuple[ReviewNarrative, ...] = ()
    priority_area_ids: tuple[ReviewNarrative, ...] = ()
```

Use existing nonblank-text and nonblank-item validators. Assessed findings require
evidence; limited findings must explain the limitation. Every evidence and priority
reference must resolve to the supplied pack/result.

- [ ] Extend PriorityArea with destination and issue_kind
  (explanation or program_design). Preserve the document anchor separately.
- [ ] Add core_findings and proposed_context_framing to ReviewDraft/ReviewResult.
  Framing contains category, rationale, confidence, evidence IDs and whether it is
  model-proposed or a coordinator override. Include undetermined as a valid outcome.
  Do not add model-authored official list or Envelope eligibility fields.
- [ ] Use a new application-owned schema/rubric version for new reviews. Require
  exactly the four ordered findings in that version. Old sessions keep explicit
  legacy presentation for their existing lifetime; do not fabricate findings.
- [ ] Extend narrative/evidence collection, export completeness and repair
  preservation to include the new fields. Repair must preserve unaffected
  findings, priorities, destinations and metadata.
- [ ] Add regressions for missing/duplicated questions, unknown references,
  empty assessed evidence, limited coverage, explicit legacy results and
  preservation during an unrelated repair.

Representative contract test:

```python
import pytest
from pydantic import ValidationError
from cpf_fcv_reviewer.contracts import CoreFinding, CoreQuestion

def test_assessed_finding_requires_evidence():
    with pytest.raises(ValidationError):
        CoreFinding(
            question=CoreQuestion.ACTIONS_COMMITMENT,
            assessment="Commitment is stated but corroboration is limited.",
            basis="assessed",
            evidence_ids=(),
        )
```

- [ ] Run the new test first and observe failure, implement, then run:

```powershell
& 'C:\WBG\Python313\python.exe' -X utf8 -m pytest -p no:cacheprovider tests/test_coordinator_findings.py tests/test_contracts.py tests/test_validators.py tests/test_review_engine.py tests/test_reproducibility.py -q
```

- [ ] Commit the verified result: feat: add coordinator findings and destinations.

## Task 2: Apply the analytical questions and stage constraints

**Files:** review_profiles.py, review_engine.py, runtime.py, prompts/review.md,
prompts/repair.md, prompts/follow_on.md; tests/test_review_prompt.py,
tests/test_prompt_guardrails.py; new tests/test_coordinator_stage_advice.py.

- [ ] Add the optional CMU review_questions input separately from review_focus.
  Bound it to 4,000 characters and treat it as untrusted task context.
- [ ] Require each core finding to examine the agreed question and connect to
  supplied RRA and approved Strategy evidence where relevant.
- [ ] Require observable evidence on commitment, comparison with CLR/previous
  CPF where available, and explicit limitations when such evidence is missing.
- [ ] Preserve the existing ROC/OC allowed recommendation scales. Add instructions
  on feasible meeting referrals and destinations rather than permitting routine
  substantive revision. Retain the finalisation profile.
- [ ] Require primary wording suggestions to respect the stage's current word
  limits. Preserve existing proposal qualification and source-backed figures.
- [ ] Keep Strategy assessments internally; use a concise RRA/Strategy synthesis
  in the new presentation. Corporate observations remain qualitative and material,
  without ratings or inferred applicability.
- [ ] Extend all guardrail and repair paths. Neither a repair nor the follow-on
  assistant may convert a proposed framing into an official classification.
- [ ] Add stage-parameterised cases demonstrating that the same concern produces
  early-stage program advice, ROC/OC clarification/referral and final wording
  correction. Include a results-framework destination at ROC/OC.

The expected allowed scales are already defined by STAGE_PROFILES; test them
against actual generated fixture content rather than creating duplicate policy
logic in the tests.

- [ ] Verify:

```powershell
& 'C:\WBG\Python313\python.exe' -X utf8 -m pytest -p no:cacheprovider tests/test_coordinator_stage_advice.py tests/test_review_prompt.py tests/test_prompt_guardrails.py tests/test_recommendation_grounding.py tests/test_policy_adversarial.py -q
```

- [ ] Commit: feat: calibrate coordinator advice to review stage.

## Task 3: Isolate previous comments and add follow-through

**Files:** new prior_comments.py and prompts/prior_comments.md; runtime.py,
review_engine.py, contracts.py, smoke.py; new tests/test_prior_comment_isolation.py;
tests/test_large_package_coverage.py.

- [ ] Add optional previous_comments uploads alongside the existing package
  uploads. Auto-recognise clearly labelled prior comments and decision records
  within package documents using title/structure and source-purpose metadata.
  Record uncertain roles; do not silently treat commentary as current facts.
- [ ] Partition dedicated prior-comment content before research focus, evidence
  building and full-document digesting. Keep the primary CPF full and preserve
  ordinary CPF references to past decisions.
- [ ] Implement a post-review follow-through function in prior_comments.py using
  the existing gateway and typed output. Call it only when prior material exists.
  Supply the current validated result and located current-package evidence.
- [ ] Return comment references, a supported follow-through description, status
  (addressed, partly_addressed, unresolved or not_assessable) and real evidence
  IDs. The function returns separate data and cannot modify the fresh result.
- [ ] Apply existing input budgets and coverage rules. Do not add repeated
  automatic calls or expand the existing review repair allowance.
- [ ] Add adversarial tests using a distinctive sentinel in a prior email.
  Assert the sentinel and its digest never reach the initial review/research
  payload but do reach the follow-through payload. Include a mixed package
  document, a decision note, no prior comments and unreadable content.
- [ ] Assert the original priority IDs and core findings are unchanged after
  follow-through. Update deterministic smoke fixtures with a synthetic example.

- [ ] Verify:

```powershell
& 'C:\WBG\Python313\python.exe' -X utf8 -m pytest -p no:cacheprovider tests/test_prior_comment_isolation.py tests/test_large_package_coverage.py tests/test_source_precedence.py tests/test_runtime_wiring.py -q
```

- [ ] Commit: feat: separate independent review from comment follow-through.

## Task 4: Generate a grounded unsigned peer-review email

**Files:** new email_draft.py and prompts/peer_email.md; contracts.py, runtime.py,
prompts.py, model_gateway.py only for the existing prompt dispatch; smoke.py;
new tests/test_peer_email.py.

- [ ] Add the model-authored email contract:

```python
class PeerEmailComment(FrozenModel):
    heading: ReviewNarrative
    text: ReviewNarrative
    priority_area_ids: tuple[ReviewNarrative, ...] = Field(min_length=1)
    tier: Literal["tier_1", "tier_2"] | None = None


class PeerEmailDraft(FrozenModel):
    opening: ReviewNarrative
    comments: tuple[PeerEmailComment, ...]
```

Reuse nonblank validators. Salutation and a short generic closing are rendered by
the application, with no named signature field. The coordinator can edit the
rendered text.

- [ ] Implement generate_peer_email(result, gateway, *, review_questions,
  follow_through, style_entries) in email_draft.py. Supply only validated findings,
  approved wording, stage profile and selected reference material. Raw prior
  emails and raw country-style examples must not be mistaken for review evidence.
- [ ] Use one normal synthesis call through the existing gateway. Do not repeat
  research, extraction or review. Do not add unbounded email retries.
- [ ] Require comments to reference existing priorities and preserve their order.
  Several adjacent priorities can form one email comment. In the standard case,
  flattened priority IDs equal the result priority order exactly.
- [ ] Validate stage constraints, policy guardrails, unknown/duplicate priority
  references, unsupported named sign-offs and raw evidence IDs. Do not publish
  an invalid email. A drafting failure is clearly labelled and preserves the
  validated note instead of presenting a successful three-output run.
- [ ] Organise around CMU questions where supplied. Allow descriptive thematic
  headings and optional tiers. Do not impose a fixed comment count.
- [ ] Use an approved external registry/reference input for internal style
  entries. Public fixtures contain synthetic examples only. Extend the existing
  source hash metadata so the style version used can be reproduced.
- [ ] Provide a pure render_peer_email(draft) function for copy and Word output.

Representative renderer test using the existing result fixture:

```python
from cpf_fcv_reviewer.contracts import PeerEmailComment, PeerEmailDraft
from cpf_fcv_reviewer.email_draft import render_peer_email

def test_email_is_unsigned():
    draft = PeerEmailDraft(
        opening="Thank you for sharing the draft.",
        comments=(PeerEmailComment(
            heading="Delivery arrangements",
            text="Clarify how the proposed delivery arrangement supports the outcome.",
            priority_area_ids=("pa-1",),
        ),),
    )
    text = render_peer_email(draft)
    assert "Delivery arrangements" in text
    assert not text.rstrip().endswith("Shubham")
```

Also test the absence of any signature field, genuine strengths derived from
findings, qualified unanswered CMU questions, tier ordering and style-input
country-content isolation.

- [ ] Verify:

```powershell
& 'C:\WBG\Python313\python.exe' -X utf8 -m pytest -p no:cacheprovider tests/test_peer_email.py tests/test_review_engine.py tests/test_prompt_guardrails.py -q
```

- [ ] Commit: feat: draft unsigned evidence-linked peer-review emails.

## Task 5: Add light intake, email editing and optional feedback routes

**Files:** routes.py, contracts.py, templates/index.html, static/app.js,
static/styles.css, smoke.py; new tests/test_review_email_state.py and
tests/test_review_feedback.py; tests/test_review_focus_intake.py,
tests/test_correction_rerun.py, tests/test_session_store.py,
tests/test_persistent_processing.py.

- [ ] Keep primary document and review stage as the substantive required inputs.
  Add optional CMU questions, previous comments and contextual framing override.
  Retain current country detection/confirmation when country identity is ambiguous.
- [ ] Expose proposed framing and a simple override without another blocking screen.
  An override is labelled coordinator guidance; it is not official status.
- [ ] Add PUT /api/reviews/<assessment_id>/email for explicitly saved wording.
  Accept text and base_run_id; bound text to 12,000 characters. Validate completed,
  unexpired state and base identity. Store email wording in the session overlay.
  Never send email or alter the analytical result from this endpoint.
- [ ] Extend the existing corrections child-review flow to retain the parent's
  edits, generate an updated draft and mark older wording as based on an earlier
  analysis. Do not silently replace user edits.
- [ ] Add POST /api/reviews/<assessment_id>/feedback with optional accuracy,
  usefulness, comment and final_comments file. Use rating enums, a 2,000-character
  comment limit, one bounded final file, existing allowed document types and
  extraction controls. Reject over-budget/unreadable uploads safely.
- [ ] Store feedback separately from analytical evidence in the existing session
  payload; retain the existing lifetime and deletion controls. No public archive,
  automatic training, corpus promotion or new database is introduced.
- [ ] Make rating, comments and final upload all optional. Explain the configured
  lifetime. Feedback is never required for download.
- [ ] Ensure result restoration returns generated email, active overlay and
  stale-edit state without feeding them into the underlying review model.
- [ ] Add tests for malicious HTML rendered as text, invalid state, expired
  sessions, stale base identity, edited download, correction preservation,
  feedback validation, deletion, expiry and exclusion from review payloads.

- [ ] Verify:

```powershell
& 'C:\WBG\Python313\python.exe' -X utf8 -m pytest -p no:cacheprovider tests/test_review_email_state.py tests/test_review_feedback.py tests/test_review_focus_intake.py tests/test_correction_rerun.py tests/test_session_store.py tests/test_persistent_processing.py -q
```

- [ ] Commit: feat: add optional coordinator editing and feedback.

## Task 6: Present the three views and verify exports end to end

**Files:** templates/index.html, static/app.js, static/styles.css, export_docx.py,
routes.py, smoke.py, scripts/run_smoke_browser.py; tests/test_output_parity.py,
tests/test_docx_export.py, tests/test_frontend_accessibility.py,
tests/test_frontend_contract.py, tests/test_smoke_mode.py; README.md,
docs/PROJECT_STATUS.md; new dated validation record.

- [ ] Keep the five-minute summary as the default results tab; add Detailed note
  and Draft email tabs with keyboard/ARIA behaviour matching the existing tabs.
- [ ] Render the agreed note order and concise qualitative four-question findings.
  Preserve evidence links and compact RRA/Strategy connections. Hide empty
  follow-through/corporate sections.
- [ ] Render summary priorities in email order, including material qualifications.
  Show destination next to each detailed response.
- [ ] Use a native textarea, Save wording and Copy actions for the email. Render
  model and user text as text, never executable HTML.
- [ ] Extend GET /api/reviews/<id>/export.docx with view=email. Use the saved overlay
  when present; otherwise render the generated email. Keep detailed/summary routes
  and native editable Word formatting. No .eml sending integration.
- [ ] Preserve the existing Word opening caution and banner. Use the agreed concise
  detailed structure instead of full RRA/Strategy matrices; evidence checks still
  include the retained internal structured assessments.
- [ ] Extend the deterministic smoke runner to exercise questions, framing override,
  all three tabs, evidence, email save, refresh, correction/stale edits, optional
  feedback, deletion and all three Word downloads. Synthetic content is labelled.
- [ ] Prefer Edge for a new browser session and use the installed control CLI under
  the workstation instructions. Preflight connection and inspect actual screenshots.
  Store new screenshots/exports under a unique dated output folder in this worktree.
- [ ] Run the provider-free acceptance ladder:

```powershell
& 'C:\WBG\Python313\python.exe' -X utf8 -m pytest -p no:cacheprovider tests/test_output_parity.py tests/test_docx_export.py tests/test_frontend_accessibility.py tests/test_frontend_contract.py tests/test_smoke_mode.py -q
& 'C:\WBG\Python313\python.exe' -X utf8 -m pytest -p no:cacheprovider -q
& 'C:\WBG\Python313\python.exe' -X utf8 -m ruff check .
git diff --check
```

- [ ] Render changed Word exports with the document skill and inspect every page.
  Run the exact browser runner in synthetic mode before considering a paid run.
- [ ] Record actual test counts, browser/export artifacts and remaining limitations
  in the dated validation record and living status. Do not imply analytical quality
  acceptance from synthetic tests.
- [ ] Commit: feat: present coordinator review and email outputs.
- [ ] Review staged files, push the feature branch and create/update the draft PR.
  No merge, deployment, hosted confidential-document use or provider-backed quality
  run is part of this implementation checkpoint. Apply the repository's existing
  authorisation and verification requirements to any subsequent release.

## Plan acceptance checklist

- [ ] Every specification requirement maps to a task above.
- [ ] New source roles cannot leak prior comments or final feedback into fresh review.
- [ ] Stage constraints survive every generation, repair and editing path.
- [ ] No corporate ratings, inferred official status or named signatures are added.
- [ ] Legacy sessions and the October coverage fixes remain intact.
- [ ] Provider-free tests, browser smoke and Word inspection establish behaviour.
- [ ] Internal reference approval and longer-term evaluation storage remain governed
  integration matters, not promises that the public prototype can handle secrets.
