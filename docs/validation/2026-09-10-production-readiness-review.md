# Production readiness review — 2026-09-10

Full-application review of `2fc2b77` (docs-only commit on top of the deployed `27ef3aa`),
carried out on branch `claude/production-readiness-review-6evrz7`.

**Nature of this record:** provider-free. No model API was called, no paid quality run was
performed, and no deployment was made. All evidence below is from source reading, the local
test suite, and a local deterministic smoke run driven through a real browser.

**Scope decision (from the requester):** the live Render service is reachable by anyone with
the URL; the readiness bar being measured is the **current supervised public-document pilot**.
Remediation in this session was limited to the top five blockers plus the misleading tests.

---

## Baseline verified at review start

| Check | Command | Result |
| --- | --- | --- |
| Test suite | `pytest -q` | **1,527 passed** in 15s — matches the documented count |
| Lint | `ruff check .` | **121 errors** (14 in `src/`): 92 `E501`, 20 `I001`, 3 `B905`, 2 `F401`, `B904`, `UP035`, `UP037`, `F601` |
| CI | — | **None.** No `.github/` directory exists |
| Smoke flow | `create_smoke_app()` + Playwright | Intake → holding → summary → detailed → assistant → refresh → both DOCX all work |

Note on the environment: this review ran on **Python 3.11.15**, while `pyproject.toml`
requires `>=3.13` and `.python-version` pins 3.13. `pip install -e .` refuses on 3.11, so the
suite was run via `PYTHONPATH=src`. The documented 1,527-test result has the same caveat.

---

## Findings inventory

Severity is judged against the supervised-pilot bar with a publicly reachable URL.
`[FIXED]` markers indicate work completed in this session; everything else is **open**.

### Blockers

**B1 `[FIXED]` — Primary document extracted with all safety budgets disabled.**
`runtime.py:885` called `extract_document(primary["bytes"], primary["name"])` with no
`max_pdf_pages`, `max_segments`, `max_characters`, `max_uncompressed_bytes` or
`max_archive_members`. Every other path passes them (`runtime.py:512-528`, `587-591`,
`routes.py:266-270`). Because `extract_docx_bytes` gates its zip-bomb check on
`if max_uncompressed_bytes is not None:` (`extraction.py:167`), passing nothing **disabled the
guard entirely**. The primary also skipped `_has_valid_optional_container`, so its type came
from the filename suffix alone.

Measured on the unpatched code:

```
compressed=479 KB  uncompressed=200 MB  ratio=427x
guarded path (as used for OPTIONAL uploads):  ExtractionLimitExceeded in 0.00s
unguarded path (exactly as runtime.py:885):   ACCEPTED — 203,015 segments, 33.7s, peak RSS 841 MB
```

841 MB on a 512 MB instance with `--workers 1` and `numInstances: 1` is an OOM kill from a
single anonymous request; `MAX_CONTENT_LENGTH` is 40 MB, leaving ample ratio headroom.

*Behaviour change to review:* the primary is now bounded by the same budgets already
applied to full RRA extraction — 250 pages / segments, 600,000 characters, 50 MB
uncompressed, 512 archive members. A primary longer than 250 pages, which previously
extracted without limit, now fails closed as `document_unreadable`. RRAs are typically
longer than CPFs and already live within this bound, so the convention is the repository's
own; but the failure code is generic, so a legitimate 300-page CPF would be told it is
"unreadable". If real packages exceed the bound, raise `DIAGNOSTIC_MAX_PAGES` for the
primary path (or give it its own constant) rather than removing the budget.

**B2 — No authentication and no rate limiting on endpoints that spend money. OPEN.**
`POST /api/reviews` (`routes.py:283`) queues the full pipeline, `/corrections` (`:473`) re-runs
it, `/assistant` (`:143`) streams 4,000 tokens. No `rate.limit|limiter|throttle|Authorization`
anywhere in `src/` or `render.yaml`. `DELETE /api/reviews/<id>` (`:548`) also needs no auth —
confirmed 204 against a review created in another client. Assessment IDs are `uuid4().hex`, so
they are not enumerable and the capability-URL design is sound; the missing perimeter is the
problem. **This is the largest open risk given the URL is publicly reachable.**

**B3 `[FIXED]` — The web UI rendered no evidence, sources, dates or verification status.**
`renderTraceabilityForEvidence` (`app.js:595`), `renderEvidenceGroup` (`:587`),
`renderTraceability` (`:591`), `renderCoverageView` (`:855`), `renderCoverage` (`:851`) and
`renderEvidenceStatusDisclosure` (`:627`) were dead — the only references were the wrappers
calling each other. `renderDetailedAnalysisView` (`:925`) called none of them. Confirmed in a
browser: the rendered result contained no `http`, no "Publisher", no "Retrieved", no "Current
context", no "Verified". The only on-screen locator was `Target: <document> | text chunk 1`,
which is where to *edit the CPF*, not where a claim came from. All of it is present in the
Word export (`export_docx.py:67, 316-332`), so the website silently dropped the product's
core "evidence-linked" promise.

`tests/test_frontend_contract.py:686` passed by substring-matching the **app.js source text**,
and `:530` explicitly asserted the detailed renderer did **not** call these functions — the
suite encoded the bug rather than catching it.

**B4 `[FIXED]` — One unhandled exception permanently bricked the queue while `/health` stayed green.**
`background.py:_run` called `run_assessment(self._app, assessment_id)` with no `try/except`.
`run_assessment`'s own handler catches only `SessionExpired` (`routes.py:618`), so a
`sqlite3.OperationalError` (disk full, I/O error) escaped, the daemon thread exited, and
nothing restarted it. Every later review sat in "queued" forever while SSE emitted keepalives.
`/health` read `queue` from a `getattr` on the object (`app.py:88`) and never checked
`thread.is_alive()`.

**B5 `[FIXED]` — An SSE stream pinned a gunicorn thread for the entire run.**
`routes.py:344-369` used `stream_with_context` with `while True` and blocking `sleep(5)`,
returning only on a terminal event. With `--threads 4`, four open streams — three colleagues
watching plus the mandated keep-awake tab — exhausted the pool; `/health` then queued behind
them, Render restarted the service, and the in-flight review was killed and re-run from
scratch. A dead worker or a half-open connection could hold a thread for the full 24-hour TTL.

### High — all OPEN

**H6 — The failure screen contradicts itself. `[FIXED]`**
`showRecoverableFailure` (`app.js:326-334`) called `showProgress()` then `resetProgress()`
(`:258`), so a failed run displayed heading "Building your FCV review", all three stages reset
to "Waiting", "0:00 elapsed · About 4-11 minutes remaining" and "Keep this page open while the
review is prepared" — with "Review stopped: …" wedged in the middle. Confirmed visually. After
a multi-minute wait it reads as *restarted*, not *failed*. Related CSS bug: `styles.css:29-31`
included `#return-to-intake` in the card rule, so "Start a new review" rendered as a
full-width white panel.

**H7 — The RRA date bug (readiness item 1): root cause identified, NOT fixed.**
The date the review prints is **model-authored and never checked**. There is exactly one
deterministic extractor (`diagnostic_sources.py:48-56`) and its four consumers all steer
*research*; none reaches the reviewer. Verified: the review payload (`review_engine.py:614-621`)
contains `evidence_pack`, `stage_profile`, `detail_profile`, `review_focus` and
`current_context_readout` — no date field, and `EvidenceLocator`/`ReviewDraft` have none
either. The RRA reaches the model as ~10-25 map-cited pages truncated to 600 characters
(`runtime.py:1226-1233`); a cover page is almost never among them. `prompts/review.md:304`
tells the model to compare diagnostic dates without ever supplying one.

The extractor is independently fragile in the matching direction: it reads
`document.segments[:4]` of a **16-page distributed sample**, skips no-text pages (so an
image-only cover shifts the window off the cover), and stores results in a **set**, discarding
document order so a mission date is indistinguishable from a cover date.

Proposed deterministic fix (three independent parts, all testable provider-free):
1. Make `_publication_date` order-aware and cover-anchored; cross-check PDF `/Info /CreationDate`.
2. Add an application-owned `diagnostic_provenance` block (`{title, publication_date, date_basis}`)
   to the review payload and instruct `prompts/review.md` to use only that date, or to state
   that the diagnostic date could not be established.
3. Add a `diagnostic_date_conflict` validator; it fits the existing `REPAIRABLE_ISSUE_CODES`
   machinery as a mechanical repair code.

**H8 — The repair call can silently delete priority areas.**
`review_engine.py:731` reconciles the repaired draft against the original **only** when
`issue_codes ⊆ {stage_length_overreach, unknown_institutional_referral, missing_registry_support}`
(verified). For `prohibited_policy_language`, `raw_evidence_id_in_narrative`,
`unknown_evidence` or any mixed set, the model's `priority_areas` are accepted wholesale
(`:798`). Post-repair validation (`validators.py:425-465`) catches duplicates and order, not
deletion. A repair for one banned phrase can return a 3-priority review where the model
produced 5, with no signal to the reader. This is the same class as the bug fixed on
2026-09-07 — that fix was scoped to three codes rather than to the mechanism.
*Suggested fix:* always reconcile `priority_areas` by `priority_area_id`, accepting model
edits only to the fields the cited issue codes actually target.

**H9 — `render.yaml` deployed 148-commit-old code. `[FIXED]`**
`branch: fix/research-resilience-guided-journey` resolves to `a52505c` (2026-09-02);
`git rev-list --count a52505c..origin/main` = **148**. `autoDeployTrigger: off` was the only
thing preventing a stale deploy, and `tests/test_render_blueprint.py:17` asserted the stale
branch name, blocking anyone from correcting it.
*Still open:* `render.yaml` declares `plan: starter` plus a 1 GB disk, while
`PRODUCTION_READINESS.md:30` says the live service is free-tier volatile. Both cannot be true,
and `tests/test_render_blueprint.py:7-11` asserts the persistent config. Someone with Render
dashboard access should reconcile the blueprint with the service that actually runs.

**H10 — Input validation is deferred until after the run starts.**
All of these return **201 Created** and only fail minutes later (verified against the running
app): missing `review_stage`; `review_stage=NOT_A_STAGE`; 2 KB of `/dev/urandom` named `.pdf`;
a shell script; 15 package documents when the cap is 10. An oversize upload returns Flask's
**HTML** 413 page, which the frontend turns into the generic "The review could not start."
An unreadable file surfaces as "**Country detection was unavailable**" (`app.js:447`), so the
user types a country, waits, and only then gets `document_unreadable`. Neither limit (40 MB,
10 documents) is stated anywhere in the UI.
*Note:* a permanently failed run returns **HTTP 202** from `/result` (`routes.py:378`) with
body `{"status": "failed"}` and no error category — a polling client can never tell it is
terminal.

**H11 — Raw uploaded bytes are held in the payload for 24 hours and re-serialized on every read.**
`routes.py:314-316` stores `{"bytes": ...}` for every uploaded file; `persistent_store.py:31-44`
base64s and zlib-compresses the whole payload. Measured encode peak ≈4×, decode peak ≈6× the
upload size, so `/result` and `/export.docx` each decode ~250 MB at the 40 MB cap merely to
reach `payload["result"]`, while the worker holds its own copy. Roughly 25 max-size reviews
fill the 1 GB disk; `_purge_expired` only runs on access; and `add_correction`
(`routes.py:513-534`) copies the parent's entire payload **including all document bytes**.
*Suggested fix:* drop the raw bytes from the payload once extraction completes (they are only
re-read by `_reextract_full_package_documents`, `runtime.py:585`).

**H12 — A transient SSE blip destroys a live run.**
After two errors (`app.js:1320`) the only control offered is `#return-to-intake` → `DELETE`,
even though the run is still executing and `Last-Event-ID` resume already works server-side.
Related: `#reset-review` sits between the two download buttons and deletes permanently with no
confirmation.

**H13 — `RELIEFWEB_APP_NAME` unset silently disables a whole research source.**
`curated_research.py:395` returns `()` on a blank name — no log, no warning, no disclosure.
It is `sync: false` in `render.yaml`, so unless someone entered it in the dashboard it has
never worked. A plausible contributor to readiness item 3 ("one publisher, reduced coverage")
being attributed to model behaviour rather than configuration. **Worth checking the dashboard
before any further source-breadth investigation.**

**H14 — Reviews are strictly serial with no queue feedback.**
`background.py:68` runs one at a time. User B waits out A's full run watching a stalled
progress bar with no position-in-queue signal, while burning one of the four threads.

### Medium — all OPEN

- **No lockfile.** `anthropic>=0.40.0,<1.0`, `pypdf>=4.0,<7.0`; this venv resolved `pypdf 6.18.0`,
  two majors past the floor. `pypdf` feeds `extract_document`, so a rebuild can change
  segmentation and character counts, which drive the exact-quotation guardrail and the
  400-segment / 300k-character budgets. `lxml` is imported directly at `runtime.py:16` — the
  DOCX XML hardening path — but is **undeclared**, working only transitively via `python-docx`.
- **Nothing pins determinism.** No `temperature`, no seed (`model_gateway.py:46`).
  `reproducibility.py:196` hardcodes `registry_versions={"bundle": "2026.08"}`, ignoring the
  loaded `bundle.version`, and `prompt_bundle_version="1.0.0"` while
  `prompts/diagnostic_map.md` is at 1.2.0. The per-prompt SHA-256s are correct and do the real work.
- **No `stop_reason` check** on the 12k output cap (`model_gateway.py:48`); a truncated
  response either burns the one schema retry or yields a silently short review.
- **No logging configuration anywhere.** Root defaults to WARNING so `logger.info` is dropped;
  no request IDs; the one useful failure log (`routes.py:609`) omits `assessment_id`, so a user
  report cannot be correlated to a log line.
- **The RRA map degrades where CLAUDE.md says fail closed.** `_downgrade_to_limited_framing`
  fires on four conditions including schema-invalid-after-retry (`runtime.py:1209`). The
  two-call bound itself **is** correct. Either the code or CLAUDE.md should change — this is a
  documentation-versus-behaviour decision for the owner, not obviously a code bug.
- **No security response headers** — no CSP, `X-Content-Type-Options`, `X-Frame-Options`, HSTS.
  Not exploitable today (no cookies, no `innerHTML`), but it is the layer that would contain a
  future rendering regression. `/result` and `/export.docx` set no `Cache-Control` while the
  assistant routes correctly set `no-store`.
- **`.eyebrow` fails WCAG 1.4.3**: `#009fda` on white = **3.01:1** at 12.8px bold
  (`styles.css:24`), affecting every section label.
- **Completed reviews are unreachable outside the originating tab** — `sessionStorage` only, no
  URL parameter, no History API. Closing the tab loses a review still alive server-side for 24h.
- **Neither result tab shows a model caution.** The Word exports open with one; the website's
  advisory boundary is in the hero, scrolled far away by results time, and basis/limitations is
  a collapsed `<details>` on the Detailed tab only.
- **Model output can reach the logs.** `research_controller.py:791` logs `str(exc)[:400]`;
  pydantic's `ValidationError` is a `ValueError`, which `_classify_exception` does not re-raise,
  and its string embeds `input_value=…`. `security.redact_log_value` exists and is unused here.
- **Streaming assistant re-announces the whole answer on every chunk** — `role="log"
  aria-live="polite"` plus `textContent` reassignment (`app.js:1165`).
- **Three backend failure codes have no frontend label or retry path**: `research_failed`,
  `research_configuration`, `research_source_rejected` — the last is exactly the case where
  retry is the right action.
- **Registry bundle expires 2027-08-22** and the app will not boot after that
  (`registry.py:135`). `[Partly addressed]` — a real-clock check now warns 90 days ahead.
- **`APP_ENV` is not validated against an allowlist** — `APP_ENV=prod` silently removes the
  persistence guard (`app.py:37`).
- **Repo hygiene.** `src/cpf_fcv_reviewer.egg-info/` is tracked; `20260907_diagnose_diagnostic_map.py`
  sits in the repo root and writes JSON output there while `.gitignore` has no `*.json` or
  `*.png` rule; 35 stale remote branches; the staff UPI `wb559324` appears in 14 tracked files
  in a repository intended to be public.

---

## Verified as sound — do not spend time re-auditing

- **SSRF defence.** Two independent layers: a hard host allowlist with https-only,
  port ∈ {None, 443}, no userinfo, no fragment (`curated_research.py:543-560`), and
  `_is_public_http_url` blocking private/loopback/link-local/reserved IPs plus decimal and hex
  authorities (`public_research.py:173-248`). All clients use `follow_redirects=False`,
  explicit timeouts, content-type allowlists and streaming byte caps.
- **Citation integrity.** A claim must resolve to a URL actually returned in the
  `web_search_tool_result` block, and its quote must be an **exact** normalized substring of
  that source's excerpt (`public_research.py:1178`) — substring, not fuzzy. A fabricated URL or
  invented quote cannot pass.
- **No `innerHTML`/`outerHTML`/`eval` in 59 KB of JS.** A file named
  `<img src=x onerror=alert(1)>.txt` flows into the payload unsanitized and renders inert as text.
- **Fail-closed startup.** Registry hash required, `compare_digest`, expiry and
  synthetic-in-production checks — all at app construction, before any request.
  `ALLOW_SYNTHETIC_REGISTRY` is hardcoded `False` and deliberately not env-readable.
- **No-partial-output discipline.** `orchestrator.py:120` clears context before re-raising;
  `routes.py:620` strips `result`/`evidence_by_id`/`research_*` before marking failed; only
  stable enum codes reach the client.
- **Prompt injection defences.** Untrusted-content instructions in every prompt, document text
  JSON-fenced with explicit markers (`research_controller.py:664-698`), and no tool with local
  side effects to escalate into.
- **SQLite threading.** Connection-per-operation, process-wide `RLock`, WAL, `BEGIN IMMEDIATE`
  on claim, `PRAGMA foreign_keys=ON` so TTL purge cascades.
- **Budgets are arithmetically correct.** 10 / 400 / 300,000 / 160,000 all enforced with
  correct inclusive comparisons and no off-by-one. The token estimator is chars/3
  (`review_engine.py:83`), deliberately conservative, and applied **before** both the initial
  and the retry call, raising rather than truncating.
- **Frontend concurrency.** Every `fetch` has a `catch`, and `operationEpoch` /
  `detectionEpoch` / `assistantRequestEpoch` guards prevent stale responses clobbering a newer
  run. Expiry handling is consistent across all four surfaces; result tabs are a correct ARIA
  tablist; `prefers-reduced-motion` is respected; 400px holds with no horizontal scroll.
- **Progress reporting is honest** — stages advance only on real backend SSE events; the ticker
  animation is decorative; the server replays from cursor 0 so a refresh resyncs correctly.

---

## A caution about the test suite

Three separate places where a green test asserted the wrong thing were found in one review:

1. `tests/test_frontend_contract.py:686` matched **app.js source text** rather than rendered
   DOM, and `:530` asserted the buggy behaviour as correct.
2. `tests/test_render_blueprint.py:17` pinned a stale deploy branch, blocking its own fix.
3. `tests/test_registry.py:231` freezes the clock at 2026-08-23, so a bundle-expiry boot
   failure can never be caught.

All three are addressed. Anyone extending this suite should prefer asserting behaviour over
source text, and treat a frozen clock as a reason for a second real-clock test.

---

## Not done, and why

- **No paid quality run, no deployment.** Everything above is reachable provider-free.
- **B2 (auth and rate limiting) is not implemented** — out of the scope agreed for this session,
  but it is the largest open risk while the URL is publicly reachable.
- **H7 (the RRA date) is diagnosed, not fixed** — the proposed change touches the review
  payload and `prompts/review.md`, which requires guardrail tests per CLAUDE.md.
