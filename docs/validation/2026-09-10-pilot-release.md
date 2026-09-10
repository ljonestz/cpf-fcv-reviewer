# CPF pilot release - 2026-09-10

## Outcome

PR 33 is merged and application commit `39049356713df8928edaf1434d812c2c58c0b95d`
is live on the existing CPF Render service. Render deployment
`dep-dah8cljbc2fs73fjc81g` finished live at 10:29:39 UTC on 10 September.
The owner requested release and explicitly wants the pilot to remain open without
passwords or institutional sign-in. No authentication changes were made.

## Released changes

- Application-owned diagnostic publication-date provenance and priority-preserving repair.
- Bounded primary extraction, pre-decompression DOCX archive gates, and accurate size errors.
- Worker recovery, sanitized error logging, and stale-result cleanup before fallback failure.
- Clear stopped-review presentation and preservation of the approved simplified evidence layout.
- Sixteen gthread request threads and bounded idle SSE responses, with reconnect handling.
- Provider-free Linux/Python 3.13 CI and a strengthened real-Gunicorn concurrency check.

The service dashboard command was changed from four to sixteen threads before the merge:

```text
gunicorn --config gunicorn.conf.py --worker-class gthread --workers 1 --threads 16 --bind 0.0.0.0:$PORT wsgi:app
```

Render MCP confirmed the saved command. Saving triggered a service-update deploy of the
previous commit, followed by the automatic deployment of merged PR 33. No manual duplicate
deploy was triggered. One paid 0.5 CPU / 512 MB instance remains configured.

## Verification and practical limits

The reviewed candidate had 1,610 passing tests on Linux/Python 3.13, including real
Gunicorn concurrency, and the synthetic browser flow passed with eight screenshots,
assistant restoration and two Word downloads. The merged commit's GitHub run
[34466250292](https://github.com/ljonestz/cpf-fcv-reviewer/actions/runs/34466250292)
also completed successfully.

No-cost checks after deployment:

- Render reported the exact commit above live.
- `/health`: HTTP success; status `ok`; exact release SHA matched.
- Queue `in_process`, storage `volatile`, worker `not_applicable`.
- Homepage HTTP 200 with the intake form.
- JavaScript HTTP 200 with the updated stopped-screen and size-error handling.
- Render application error-log query from 10:28:38 UTC through verification returned
  zero error-level entries. This is a bounded startup check, not ongoing monitoring.

No provider-backed assessment or paid model call was made. Analytical quality has not
been reaccepted on this deployment. Storage remains volatile: reviews do not survive
restarts. Sixteen threads mitigate the measured pilot concurrency problem; they do not
remove its ceiling. Proposal feasibility and research breadth still need expert judgment.
The stable FCV Project Screener was not changed.

The documentation-only follow-up uses Render's supported `[skip render]` commit marker
so recording this result does not restart the service or change the verified release.
See [Render's deployment documentation](https://render.com/docs/deploys#skipping-an-auto-deploy).
