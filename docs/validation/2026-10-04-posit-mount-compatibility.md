# Hosting URL-prefix compatibility - 2026-10-04

Application change: `e196b3d`. Draft PR 40 targets the existing repair branch,
not main. This is a hosting prerequisite; no deployment or model-provider change.

## Reproduction and change

At a non-root WSGI mount, browser assets, locally constructed API requests and
server-returned event/result links previously escaped to the host root. Browser
session keys also did not distinguish app mounts sharing one origin.

Flask now generates asset and returned API URLs. The HTML supplies `script_root`
to one browser URL helper. Session keys append that mount; the empty root preserves
existing URLs and storage keys. No forwarding headers are newly trusted. This does
not add authentication or establish server-side isolation between users.

## Validation

- Initial regressions: three failed, one passed. After the implementation and
  updates to existing source-string assertions, **138 focused tests passed**.
- Existing synthetic browser runner mounted through Werkzeug DispatcherMiddleware
  at `/content/cpf-preview`: **11/11 checks**, zero page/console/resource errors,
  normal exit 0, 129.61 seconds. Root requests were served by a 404 fallback.
- Tested uploads, assessment completion, summary/detail, assistant, refresh and
  history restoration, both Word downloads, and mobile wrapping. Desktop/mobile
  screenshots were visually inspected. All content/model responses were synthetic.
- Python compilation, JavaScript syntax and `git diff --check` passed.
- Final candidate `7e88c41`: **1,773 Linux tests**, including Gunicorn, and Python
  name/import checks passed in [CI](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/37195363337).
  The first CI attempt had one obsolete source-string expectation and 1,772 passes;
  the expectation was updated and its 11-test module passed before the full rerun.

Local ignored evidence:
`output/playwright/20260930_renewed_acceptance/browser/20261004-posit-prefix-01/`
and wrapper `output/20261004_posit_compatibility/20261004_mounted_browser_smoke.py`.

## Remaining deployment prerequisites

Authenticated publishing preflight succeeded on the intended external Connect
service and confirmed that APIs are permitted. Its newest installed Python is
3.11.9; this application still declares Python 3.13 or newer. Runtime compatibility
must be resolved and tested before publishing. The existing model-access guide
also has its own runtime prerequisites; no requirement was silently downgraded.

Model application credentials were not found in the current process or project
configuration. The platform documentation opened at institutional sign-in. Hosted
application authentication, allowed models, structured output, research tools,
streaming and network reachability remain unverified. Portal/desktop access is
not evidence of application credentials. No credentials or internal guide content
were copied into the repository, and no real model call was made.

Durable storage, worker lifecycle/concurrency, proxy client identity, access rules
and actual viewing-URL acceptance still need server-specific verification. The
four-per-day admission ceiling remains unchanged; separate live copies would need
a coordinated spending plan. This change does not resolve prior factual acceptance
or production-readiness gates. Render and the stable FCV Project Screener are untouched.
