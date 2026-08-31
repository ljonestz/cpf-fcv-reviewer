# Guinea production quality-run validation

Date: 2026-08-31

## Scope

This record covers the explicitly authorized provider-backed Guinea quality assessment
on the public Render prototype after deployment of the bounded initial schema retry. It
contains no raw provider output, credentials, or live assessment identifier.

## Environment and inputs

| Item | Verified state |
|---|---|
| Public service | `https://cpf-fcv-review-prototype.onrender.com/` |
| Render service | `cpf-fcv-review-prototype` |
| Deployed code commit | `1ba44bf` |
| Review stage | Finalization |
| Primary document | Public Guinea CPF (`guineacpf.pdf`) |
| Context document | Public Guinea RRA (`guinearra.pdf`) |
| Package documents | None |

The free Render service was awakened before submission. Separate lightweight site tabs
were opened during the run to prevent idling; they did not create additional reviews.

## Production execution

- Review creation returned HTTP 201 at 13:23:45 UTC.
- The result endpoint returned HTTP 200 at 13:34:45 UTC, approximately 11 minutes later.
- Document reading, current-country research, drafting, and validation all reached the
  complete state in the browser ticker.
- The DOCX export endpoint returned HTTP 200 with 49,830 bytes.
- Render reported no error-level logs during the assessment.

Only this one provider-backed assessment was initiated for the deployed fix cycle.
Repeated GET requests used to retrieve the already-generated JSON and DOCX did not
invoke another assessment or model call.

## Result acceptance

The saved 79 KB API response passed the production contracts used by the result route:

- core `ReviewResult` schema: passed;
- 32 `EvidenceItem` records and evidence-key identity: passed;
- reproducibility metadata: zero issues;
- application `validate_review`: zero issues;
- priority areas: 3;
- explicit limitations: 5; and
- current-evidence tier: `reduced`.

The `reduced` tier is a disclosed evidence limitation, not a validation failure. The
review established only two recent public sources and correctly stated that current
coverage remained incomplete for minimum claims, structural dynamics, and current
developments. The result did not overstate the available current evidence.

## Browser evidence

The following full browser-viewport screenshots are saved in the existing
`GuineaCPFRRA` validation-output folder. The browser exporter preserved the desktop
layout while downscaling the PNGs to 800 pixels wide:

- `20260831_guinea_production_ready_fullscreen_800x500.png`;
- `20260831_guinea_production_holding_initial_fullscreen_800x500.png`;
- `20260831_guinea_production_holding_drafting_fullscreen_800x500.png`;
- `20260831_guinea_production_result_summary_fullscreen_800x742.png`; and
- `20260831_guinea_production_result_detailed_selected_fullscreen_800x742.png`.

The screenshots confirm the Project Screener-aligned holding ticker, compact timer,
rotating phrases, completed Five-minute readout, evidence-status disclosure, and selected
Detailed analysis view. Browser result rendering showed no visible overlap or clipping at
the tested full-width viewport.

## Saved outputs and DOCX checks

- `20260831_guinea_production_result.json` (79 KB response);
- `20260831_guinea_production_detailed_review.docx` (49,830 bytes); and
- the five browser screenshots listed above.

The DOCX passed ZIP integrity and opened through `python-docx`. It contains one section,
198 paragraphs, no tables, approximately 40,925 extracted text characters, and the
expected priority-area and limitations sections. LibreOffice/`soffice` is not installed
in the Windows environment, so DOCX-to-PNG visual QA could not be completed; no claim of
rendered DOCX visual acceptance is made.

## Acceptance outcome

Guinea provider acceptance is established for the public advisory prototype on deployed
commit `1ba44bf`. The previously failing initial schema boundary no longer prevents a
complete, validated result or DOCX export. This does not change the prototype's advisory,
public-material-only scope or confer operational ITS production approval. Broader
cross-country acceptance remains optional work for Haiti and Benin.
