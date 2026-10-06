# Country detection repair - 6 October 2026

## Reproduced problem and approved change

ITS reported automatic detection succeeding only for the newer Niger CPF. The six
local CPF files reproduce that pattern against the `99cba08` application code:

| CPF | Previous outcome | Cause |
| --- | --- | --- |
| Niger, newer | Niger / HTTP 200 | Recognised title, below 2 MiB |
| Ethiopia | No country / HTTP 200 | Federal Democratic Republic name not recognised |
| Guinea | No country / HTTP 200 | Mixed-language cover name not recognised |
| Burkina Faso | HTTP 400 | 3,054,684 bytes exceeds 2 MiB |
| Somalia | HTTP 400 | 3,621,887 bytes exceeds 2 MiB |
| Niger, older | HTTP 400 | 2,924,087 bytes exceeds 2 MiB |

TLS-verified synthetic probes on the live release reproduced both missing names and
the 2 MiB + 1 rejection, with a successful Niger control. Country-detection source
was unchanged between the prior `992c35a` and `99cba08` releases. This is separate
from the assessment-validation repairs. No real documents were uploaded to Render
for this diagnosis and no provider-backed review was started.

The owner approved exact aliases `Federal Democratic Republic of Ethiopia` and
`Republique of Guinea`, plus an automatic detector upload budget of **10 MiB** in
both Python and browser JavaScript. The limit message was updated. Five source
lines changed. Existing title/registry confidence checks and manual entry remain;
16 PDF pages, 256 segments, 100,000 text characters, 8 MiB decompressed content and
512 archive members are unchanged. No filename inference, model call or retry.

## Candidate verification

- Existing country-related baseline: **47 passed**. Four new cases failed before
  implementation: both aliases, a readable synthetic PDF above 2 MiB, and the
  updated frontend boundary/message contract.
- Complete detector/route/upload focused suite: **91 passed**.
- Final full provider-free suite: **1,686 passed, one Windows Gunicorn skip**.
  Two earlier attempts returned 31 setup errors because the pytest temporary
  directory's parent was missing. Explicit directory creation and a successful
  fixture probe preceded the passing full run; this was local QA setup.
- All six original local CPF files now return their correct country, HTTP 200 and
  `requires_confirmation=false` through the actual detector route. Standard CPF
  title checks also pass for all **196 canonical registry country names**. This
  synthetic title coverage is not a promise about every real PDF layout.
- Visible Edge intake exercised the six real local CPF detections, then manual
  entry above 10 MiB. Both screenshots were inspected. The first helper completed
  the six detections but failed constructing its oversized buffer because the CLI
  execution context has no `Buffer`; a continuation using a local synthetic file
  completed manual entry without another assessment or source change. The only
  initial browser console error was the existing missing favicon. No page error.
- Frontend regression checks cover 3 MiB, exactly 10 MiB, ordinary 2 MiB files,
  and manual confirmation above 10 MiB. Backend regression pins the explicit
  approved budget, accepts a valid 3 MiB PDF and rejects above the configured cap.
- Independent focused review found no implementation/security issue and one
  budget-synchronization test gap. The final backend budget assertion closes it;
  it passed in the final full suite. Coordinator inspected the actual diff.
- Ruff passes changed Python source and route tests. Other touched test files have
  unchanged E501/I001 findings also reproduced on origin/main; checking them with
  only those exclusions passes. `git diff --check` passes.

Initial candidate Linux CI stopped during collection because the new synthetic
PDF test used locally installed ReportLab, which is not a repository dependency.
The test now reuses the existing pypdf-only `make_pdf` fixture helper. Application
source is unchanged and no dependency was added; final focused checks and Linux
CI are required after this fixture correction. The recorded local full-suite pass
preceded that test-only correction.
Final local focused checks after correction: **92 passed**, including the module
that imports the route-test helpers; the final route-test Ruff check also passed.

Local screenshots, helper scripts, synthetic uploads and temporary test files
remain ignored under `output/playwright/`. No raw documents, model output,
credentials, conversations or review identifiers are committed.

## Release boundary

These are candidate checks. Linux CI, merge, exact Render deployment and live
detector-only synthetic/browser probes are subsequent acceptance steps. Scanned
documents, unusual or ambiguous titles and files beyond the limits can still
require manual country entry. Normal registry-supported CPF/CEN titles remain
deterministic; the increased upload allowance benefits every country.

## Deployment and live verification

PR [50](https://github.com/ljonestz/cpf-fcv-reviewer/pull/50) merged the repair to
`main` as **2ef01662c490810f4d346551a4555b6384222ece**. Final candidate Linux CI
[37497710576](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/37497710576)
passed **1,687 tests**, including real Gunicorn, after the fixture correction.
Merged-release CI
[37498076350](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/37498076350)
also passed.

Render's normal auto-deploy became live at **2026-10-06 16:45:29 UTC** on that exact
commit. TLS-verified `/health` returned HTTP 200 and the complete release hash;
the served JavaScript contains the matching 10 MiB limit. Detector-only live API
probes returned HTTP 200 and correct countries without confirmation for Niger,
Ethiopia, Guinea and a valid synthetic Somalia PDF above 3 MiB. A 10 MiB + 1 byte
synthetic input was rejected with HTTP 400.

The dedicated visible Edge session repeated those four synthetic detections on
the deployed intake. Above 10 MiB, the browser skipped the detector request,
displayed the new limit and accepted manual entry, enabling the review button.
Result: `LIVE_EDGE_COUNTRY_QA_PASS`, four detector POSTs, zero assessment POSTs and
zero page errors. Both live screenshots were inspected. The helper's initial
Playwright request-context health probe encountered the local certificate chain;
using browser-native fetch with normal certificate validation completed the check.
No TLS validation was disabled and no application change was needed.

Live helper scripts, synthetic uploads and screenshots remain ignored under
`output/playwright/`. No real documents were sent to Render and no model/provider
calls were made. The owned local smoke server was stopped; Edge remains open on a
fresh live intake. This closes the pending detector release checks above; it does
not add a full assessment quality run or guarantee unusual/scanned title layouts.
