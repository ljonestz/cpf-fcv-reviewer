# Guinea acceptance after limited-mode validation correction

## Release and scope

PR #21 merged as `63b16da72b39406452fbfb6a5044839be95d2ba2` and was manually
deployed to the existing CPF FCV Reviewer service. Render reported the deployment
live and `/health` returned the same commit. Auto-deploy remains off. The service
uses the existing volatile prototype mode. No stable Project Screener changes.

One explicitly authorized Guinea CPF plus RRA assessment was submitted through
the browser at decision-review stage. It reached `run_complete` after approximately
ten minutes. No additional assessment or paid follow-on assistant request was made.

## Provider-free preflight

Local synthetic browser flow verified file upload, country entry, decision-review
selection, submission, progress, completed summary and detailed views, assistant
response, refresh restoration, and DOCX export. The browser download event hook
timed out, but the export request returned 200 and the downloaded DOCX ZIP/XML was
validated directly. The local smoke server was stopped after testing.

## Live results

- Full `rra_alignment`, not limited framing.
- Five RRA driver assessments; four FCV Strategy assessments; four priority areas.
- No independent current-context evidence items. Research degraded to document-led.
- `fcv_readout_generated` reported six themes.
- One bounded repair phase corrected unknown institutional referral,
  stage-length overreach, and prohibited policy-language issues.
- No `limited_mode_overclaim` or diagnostic-map schema failure was reported.
- Browser summary and detailed results rendered; completed review restored on refresh.
- Result contract and reproducibility metadata validation passed. The result's
  app_release field uses package version `0.1.0`; deployed commit was independently
  verified with `/health` and Render.
- DOCX endpoint returned 200; 48,924 bytes, valid ZIP and OOXML, 103 paragraphs.
  Content checks found Guinea, RRA analysis, priorities, and the AI-generated caveat.
  DOCX pagination was not visually verified because a document renderer was unavailable.

## Quality conclusion

Execution and export acceptance passed; this does not establish production readiness.
No current-source news was accepted in this run. The fallback is disclosed in the
limitations, but the main synthesis states some post-RRA directional developments
without qualification, and some recommendations use that unverified context.
The current-context provenance therefore needs stronger treatment in the main
analysis, alongside improving reliable current-source retrieval. Do not remove
safety validation or treat successful completion as factual verification.

The supplied primary document is treated as an excerpt, which the note discloses;
this run is not evidence of full-package analytical coverage.

## Local artifacts

Artifacts are in `output/20260907_acceptance_0845/` in the acceptance worktree:
`20260907_guinea-review.docx`, `acceptance-safe-summary.json`, and dated Guinea
intake, progress, summary, detailed, result-header, `20260907-guinea-five-minute-full.png`,
and `20260907-guinea-detailed-full.png` PNGs. The two `*-full.png` files are direct
full-panel captures (760 x 6,951 and 760 x 21,759 pixels), rather than stitched viewport
screenshots. Artifacts and live assessment identifiers are not committed.
The live run ID is retained only in the existing non-repository Guinea handoff.

## Next work

Investigate the current-research no-parsed-output failure using sanitized diagnostics;
ensure model-knowledge fallback claims remain clearly qualified in summary,
assessments, and recommendations. Use local regression tests before another
explicitly authorized paid acceptance cycle. No further deployment or paid run is
authorized by this validation record.
