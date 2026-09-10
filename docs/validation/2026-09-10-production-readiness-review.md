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

Note on the environment: the review itself ran on **Python 3.11.15** via `PYTHONPATH=src`,
because `pip install -e .` refuses on 3.11 while `pyproject.toml` requires `>=3.13`. A
reviewer rightly pointed out that this does not validate the documented runtime, so
**everything was re-run on Python 3.13.12 with a real editable install and no `PYTHONPATH`
override**: `1,563 passed`. The pre-existing 1,527-count in earlier records still carries the
3.11 caveat; this one does not.

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

*Second iteration, after external review.* The first version of this fix was wrong in two
ways, both found by a reviewer and then reproduced here:

1. **It would have rejected almost every real DOCX CPF.** It reused `DIAGNOSTIC_MAX_PAGES = 250`
   as `max_segments`, but a segment is only a page for PDFs — for DOCX it is one paragraph or
   one table row (`extraction.py:198-231`). Measured: a 400-paragraph DOCX was rejected, and
   real CPFs run to well over a thousand paragraphs. The primary now has its own
   role-appropriate budgets — `PRIMARY_MAX_PDF_PAGES = 400` for PDFs (page and segment bounds
   deliberately equal, because an unequal pair makes `extract_pdf_bytes` silently truncate
   instead of failing closed) and `PRIMARY_MAX_SEGMENTS = 10,000` for flowing documents, with
   `PRIMARY_MAX_CHARACTERS = 600,000` as the real volume guard in both cases. A
   1,200-paragraph DOCX is now accepted, with a regression test.

2. **Container validation was itself an unbounded decompression path, and it ran first.**
   `_has_valid_docx_container` reads `[Content_Types].xml` and every `.rels` part through
   `_read_docx_part` → `archive.read()` with no size bound, before the bounded extraction is
   ever reached. Measured on the previous commit: a 537 KB upload declaring a 120 MB
   `[Content_Types].xml` was inflated during validation at **479 MB peak RSS** in 0.9s — still
   an OOM on a 512 MB instance. The validator now checks member count and total declared
   uncompressed size from the zip central directory *before* reading any part; the same upload
   is refused in **0.001s with no measurable memory growth**. This also closes the identical
   pre-existing gap on the optional/package upload paths, which share the validator.

3. **The original bomb test proved the wrong thing.** It built its DOCX with unnamespaced
   `<Types/>` and `<Relationships/>` parts, which the container validator rejects on structure
   alone, so the extraction budget was never exercised. The tests now use a structurally valid
   DOCX and assert each guard at the layer where it actually fires: the size gate for an
   oversized archive, and the extraction budget for a valid, modestly sized document with too
   many segments.

An over-limit primary now fails as the distinct `document_too_large` rather than
`document_unreadable`, and the UI says so: "The primary document is too large to review in
full. Upload a shorter version, or split the annexes into package documents."

4. **Oversized and malformed are reported separately.** A first pass at the size gate folded
   both into `document_unreadable`, so an image-heavy but perfectly valid DOCX over the
   uncompressed budget would have been reported as corrupt. The primary now checks the
   archive's declared size from the central directory *before* container validation and
   raises `DocumentTooLarge`; structural problems still raise `DocumentUnreadable`. Verified
   end to end through real gunicorn: a 1,200-paragraph DOCX CPF completes, and a 312 KB
   upload declaring 55 MB returns `document_too_large`.

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
which is where to *edit the CPF*, not where a claim came from. The Word export does carry the
source URL and a `Source` label (`export_docx.py:331-332`, `:566`), so the website was the
weaker surface — but *correcting an earlier draft of this record*: "Publisher" and "Retrieved"
fields do not exist in the Word export either, and listing them as web-only omissions was
wrong. The gap was source URL, excerpt, verification chip and coverage, not those two fields.

`tests/test_frontend_contract.py:686` passed by substring-matching the **app.js source text**,
and `:530` explicitly asserted the detailed renderer did **not** call these functions — the
suite encoded the bug rather than catching it.

**B4 `[FIXED]` — One unhandled exception permanently bricked the queue while `/health` stayed green.**
`background.py:_run` called `run_assessment(self._app, assessment_id)` with no `try/except`.

*Correction to an earlier draft of this record:* `run_assessment` does have a broad
`except Exception` (`routes.py:598`) that records a safe failure code and a terminal event —
that part is sound. The escape path is narrower: the **inner** recovery block that persists
the failure state catches only `SessionExpired` (`routes.py:642`), so a `sqlite3.OperationalError`
raised while *recording* the failure propagates out of `run_assessment` entirely. The daemon
thread then exited and nothing restarted it, leaving every later review queued forever while
SSE emitted keepalives. `/health` read `queue` from a `getattr` (`app.py:88`) and never
checked `thread.is_alive()`.

The worker now also (a) guards `claim_next()`, which was still outside the original catch, so
a store error there cannot end the loop either, and (b) marks a review that escaped this way
as `failed` and emits a terminal `run_failed`, so it does not sit in `running` with a browser
waiting on a stream that never resolves. Logging records only exception type and cause chain,
matching the deliberately sanitized pattern in `routes.py:614` — the first version used
`logger.exception`, whose traceback can quote uploaded document text.

**B5 `[PARTLY FIXED — bound raised, not removed]` — SSE streams starved the health check.**
`routes.py:344-369` used `stream_with_context` with `while True` and blocking `sleep(5)`,
returning only on a terminal event, so each open stream held one of the four request threads
for the whole multi-minute run.

*Second iteration, after external review.* The first fix — a 90-second cap on a single stream
— was described as fixing this. That was wrong, and a reviewer was right to challenge it. Under
real gunicorn with the deployed configuration the starvation was reproduced directly:

| Configuration | Streams connected | `/health` latency |
| --- | --- | --- |
| `--threads 4` (as deployed) | 4 of 8 | 15.0s, 15.0s, 15.0s — all timed out |
| `--threads 16` (now) | 8 of 8 | all sub-second |

Render's health check would have failed the first case and restarted the instance mid-review.
The thread pool is now 16 in `render.yaml`, `Procfile` and `gunicorn.conf.py` — which are now
identical to each other, where previously the `Procfile` did not even load `gunicorn.conf.py`
and so silently used gunicorn's 30-second graceful timeout against `maxShutdownDelaySeconds: 300`.
`tests/test_stream_concurrency.py` launches real gunicorn with the argv parsed out of
`render.yaml` and asserts `/health` answers under load; it was red before the change and is
green after.

**The failure mechanism is unchanged; only the number moved.** A reviewer pressed on exactly
this, and they were right to. One stream still occupies one request thread for its lifetime,
so the pool size is the concurrency ceiling. Measured against the deployed `gthread` config
with the cap disabled, to isolate the thread-count effect:

| Concurrent streams | `/health` latency | |
| --- | --- | --- |
| 8 | 0.00s | healthy |
| 15 | 2.96s | degraded |
| 16 | timeout | starved |
| 24 | timeout | starved |

So the honest tolerance is **roughly 8-12 concurrent viewers, not 15** — an earlier note in
this record claimed ~15, which the measurement above does not support: at 15 the health check
is already at 3 seconds because the probe itself needs a thread. For a single-instance
supervised-expert pilot that is comfortable headroom over realistic load, but it is headroom,
not a fix.

The 90-second cap is complementary and remains, and it is worth being precise about what it
buys: it does **not** reduce steady-state occupancy, because a live viewer's browser
reconnects immediately. What it does is reclaim threads from connections that are dead but not
closed — a slept laptop, a dropped network — which would otherwise hold a slot until TCP
timeout, or for the full 24-hour TTL if the worker died without emitting a terminal event.

**What would actually remove the mechanism, measured.** `gevent` is already a declared
dependency and `wsgi.py` already carries a monkey-patch hook, both currently unused. Under
`--worker-class gevent --worker-connections 200`, the same experiment is flat:

| Concurrent streams | 8 | 15 | 16 | 24 |
| --- | --- | --- | --- | --- |
| `/health` latency | 0.00s | 0.00s | 0.00s | 0.00s |

No server errors. **This was not adopted, and should not be adopted on the strength of that
table alone.** The experiment ran with `start_background_runs=False`, so it demonstrates only
that SSE concurrency scales — it does not show the review pipeline behaving correctly under
monkey-patching. Three things need validating first: `sqlite3` calls are blocking C calls that
gevent does not patch, so a slow disk write would block the whole hub rather than one thread;
the Anthropic SDK's httpx usage needs checking under patching; and `wsgi.py`'s existing hook
(`if "gevent" in sys.argv`) patches at worker-import time, which is later than
`monkey.patch_all()` wants to run and does not match the `--worker-class=gevent` equals form.
`tests/test_app_factory.py:90` also suggests the current thread-based choice was deliberate.
This is an architecture decision for the owner, with its own validation cycle — not a
drop-in.

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
`PRODUCTION_READINESS.md:30` describes the live service as free-tier volatile. I have no
Render access, so I could not determine which describes the running service — only that the
repository asserts both, and that `tests/test_render_blueprint.py:7-11` locks in the
persistent one. Someone with dashboard access should reconcile them; until then, treat the
blueprint as the intended operational configuration rather than evidence of the live one.

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

## Reviewed and found sound at this commit

These were examined in this review and no defect was found. That is a statement about what
was checked on `340c0ad`, not a guarantee of correctness, and not a reason to skip them if a
change lands nearby or new evidence appears.

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


---

## How this record was corrected

An external reviewer (codex) inspected the pushed commit `340c0ad` rather than its summary and
raised six points. Five were correct and are addressed above; all were reproduced locally
before acting, and none was taken on assertion alone:

1. **The 250-segment primary limit was not 250 pages.** Correct, and worse than stated — a
   400-paragraph DOCX was rejected. Fixed with separate PDF-page and flowing-document segment
   budgets; see B1.
2. **DOCX container validation decompressed parts before any budget check, and the bomb test
   used an invalid container.** Both correct, both reproduced (479 MB peak RSS during
   validation; the test's `<Types/>` failed structural validation so the budget was never
   exercised). Fixed and re-tested; see B1.
3. **The 90-second cap mitigated starvation rather than fixing it.** Correct, and now measured
   rather than argued: 4 streams timed out `/health` at 15s under the deployed config. See B5,
   which no longer claims the problem is eliminated.
4. **Worker survival left the failed review stuck, and `claim_next` was outside the catch.**
   Correct. Both fixed, plus the `logger.exception` traceback replaced with sanitized
   type/cause logging; see B4.
5. **The reported test result was on an unsupported Python version.** Correct; re-run on 3.13.
6. **This record repeated factual mistakes.** Partly correct. The `run_assessment` and Word
   export claims were wrong and are corrected inline above, as is the absolute
   "do not re-audit" framing. On the blueprint-versus-live-configuration point the record now
   says plainly that the repository asserts both and that I could not check the running
   service.

One point I did not adopt as stated: the reviewer suggested treating the restored evidence
panels as a presentation decision reversing a deliberate simplification. The panels were not
simplified away deliberately — `renderTraceabilityForEvidence` and its siblings were complete,
reachable-looking functions that nothing called, and a test asserted the absence as correct
while another passed by matching source text. That reads as drift, not a decision. It is still
worth a product owner confirming the restored presentation, and that confirmation is listed as
an open item rather than assumed.
