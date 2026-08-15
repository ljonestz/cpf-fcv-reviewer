# RRA and 2026–2030 FCV Strategy Assessment Design

**Date:** 2026-08-15  
**Status:** Approved for implementation planning

## Purpose

Strengthen the full detailed CPF review so it consistently assesses whether the CPF translates the Risk and Resilience Assessment (RRA) and the 2026–2030 WBG FCV Strategy into country outcomes, delivery arrangements, and results. The change must also prevent document-retrieval failures from being reported as substantive CPF gaps and make recommendation summaries less prescriptive.

This is a narrow redesign of evidence selection, the review contract, prompt, presentation, and DOCX export. It does not introduce a separate assessment service, a second generated report, or a generalized rules engine.

## Problem to solve

The reviewed run produced plausible prose but missed material evidence in the uploaded Results Matrix and implementation documents. The runtime currently gives the entire package a fixed eight-segment allowance and samples from the beginning of each document. With several package files, the model may see only opening sections. The review can then mistake unavailable evidence for an actual omission.

The current narrative-only contract also does not require:

- an explicit RRA driver-to-response chain;
- a systematic assessment of the four new FCV Strategy strategic shifts;
- a distinction between absent evidence and evidence that was not available to assess;
- separation of a concise recommendation title from its detailed drafting action.

Consequently, the output can omit core FCV questions while making overly precise recommendations such as prescribing a particular number of sentences in a named section.

## Authoritative Strategy framing

The assessment will use the terminology and expectations in *A World Bank Group Strategy for Engaging in Fragility, Conflict and Violence Affected Settings (2026–2030)*, not a website-only summary and not the four pillars of the preceding 2020–2025 Strategy.

The four strategic shifts are:

1. Anticipate better.
2. Adopt a differentiated approach.
3. Deliver as One WBG on the jobs agenda.
4. Enhance WBG knowledge, operational toolkit, partnerships, and staffing.

For CPF review purposes, the Strategy specifically supports checking whether:

- CPF outcomes address FCV drivers and support trajectory-shifting actions;
- trajectory-shifting actions and government commitment, or sustainable delivery pathways in acute crisis settings, shape program choices;
- forward-looking risks, scenarios, preparedness, and adaptive management inform the engagement;
- jobs objectives are explicit and roles across IDA/IBRD, IFC, MIGA, and their instruments are defined;
- RRAs inform country strategies and operations, including risks and opportunities for private sector engagement;
- programs address FCV drivers or strengthen resilience without exacerbating FCV risks;
- operational modalities and partnerships are fit for the context.

Gender and climate–FCV integration are cross-cutting Strategy priorities. They should be assessed where material to the country context, not represented as additional strategic shifts.

Authoritative source: https://documents1.worldbank.org/curated/en/099060826095532931/pdf/BOSIB-aa382b38-8b68-43a1-b9e9-0ab02bdac2ce.pdf

## Proposed assessment structure

### 1. Evidence coverage preflight

Before drafting findings, the review must establish which uploaded documents and relevant sections were available. Evidence selection must provide meaningful coverage across every package document rather than a single small package-wide segment budget.

The smallest reliable change is to allocate a bounded minimum per package document, then use the remaining bounded allowance for high-value sections identified by headings and search terms. Priority sections include results frameworks, intervention logic, implementation arrangements, adaptive management, risk monitoring, partnerships, and FCV/RRA discussion.

If evidence needed for a criterion was not extracted, uploaded, or readable, the result must be `Not assessable`. It must not become `Not evidenced` or a recommendation asserting that the CPF lacks the content.

### 2. RRA driver-to-response assessment

The detailed review will contain a compact row for each material RRA driver:

`RRA driver → CPF response → delivery mechanism → result/indicator → remaining gap`

Each row will cite available evidence and receive a status and confidence level. The assessment should test the full chain rather than merely checking whether an RRA driver is mentioned. A gap may occur in prioritization, intervention logic, delivery, results measurement, or adaptation.

The reviewer may consolidate closely related drivers to keep the output useful. It must not invent an exhaustive driver taxonomy when the RRA does not support one.

### 3. FCV Strategy alignment assessment

The detailed review will visibly assess the four strategic shifts:

| Strategic shift | CPF-facing assessment focus |
|---|---|
| Anticipate better | Forward-looking FCV risks, scenarios, preparedness triggers, risk monitoring, and adaptation mechanisms |
| Differentiated approach | RRA-derived trajectory-shifting actions, government commitment or sustainable delivery pathways, selectivity, regional dimensions, and program calibration |
| One WBG on jobs | Explicit FCV-informed jobs objective; foundations, business-enabling reforms, and financing/capabilities; MSMEs and inclusion; defined and sequenced institutional roles |
| Knowledge, toolkit, partnerships, and staffing | RRA uptake, conflict sensitivity, fit-for-context delivery and operational flexibilities, implementation and analytical partnerships; staffing only where the CPF materials make it assessable |

Cross-cutting gender and climate–FCV considerations will be included where the evidence establishes their materiality.

### 4. Status, confidence, and gap classification

Every RRA and Strategy item will use one of four statuses:

- `Aligned`: the relevant chain is substantively present and supported by evidence.
- `Partially aligned`: material elements are present but an important link is weak or absent.
- `Not evidenced`: the reviewed materials are sufficient to assess the item and do not evidence it.
- `Not assessable`: the necessary evidence was unavailable, unreadable, outside the supplied materials, or not reasonably expected in the document under review.

Confidence will be `High`, `Medium`, or `Low`, based on the completeness and directness of the evidence. Each material gap will also identify its locus: CPF narrative, results framework, delivery/implementation arrangements, monitoring/adaptation, or downstream operationalization. This prevents downstream detail from automatically being treated as a missing CPF-level commitment, and vice versa.

### 5. Recommendations and summary

Only three to five material, cross-cutting priorities will appear in the summary. Priority selection should be driven by the structured assessments, significance to the country’s FCV trajectory, and whether a CPF-level drafting response is warranted.

Each priority will separate:

- a short issue title, such as `Strengthen the FCV jobs pathway`;
- the assessment and why it matters;
- the appropriate recommendation locus;
- a proportionate drafting action.

Detailed recommendations may identify a section or content requirement when supported by the source materials. Summary titles must not prescribe sentence counts, exact wording, or overly narrow edit instructions. Recommendations must avoid fabricated precision, unsupported numerical targets, or time-bound commitments not grounded in evidence.

## Output and interface

The existing summary and detailed-results experience remains. No new workflow stage is needed.

The detailed results and DOCX will use two layers within the same report:

1. A concise briefing layer: overall assessment, three to five priorities, RRA synthesis, and four-shift Strategy synthesis.
2. A technical evidence layer: driver rows, Strategy rows, statuses, confidence, evidence references, coverage, and limitations.

The JSON contract will expose the structured rows so the browser and DOCX render the same conclusions. Existing evidence-status metadata remains and is extended rather than replaced.

## Guardrails

- Evidence absence and evidence unavailability are different states.
- An `Aligned` judgment requires affirmative source evidence.
- `Not assessable` items do not generate substantive recommendations by themselves.
- Strategy criteria should be applied at the level relevant to a CPF; corporate-only matters such as staff career incentives are not automatic CPF gaps.
- The primary CPF remains the document being reviewed, while package documents supply necessary results and implementation evidence.
- The assessment remains advisory and evidence-led; it does not assert internal policy compliance beyond what the supplied and approved public sources support.

## Verification

Implementation will add focused tests for:

1. meaningful evidence selection from every uploaded package document;
2. `Not assessable` behavior when required evidence is unavailable;
3. complete serialization and rendering of RRA and four-shift Strategy rows;
4. short recommendation titles separated from detailed actions;
5. no priority generated solely from unavailable evidence;
6. browser and DOCX rendering of status, confidence, locus, and evidence references;
7. regression coverage for existing full, reduced, document-led, and smoke modes.

A deterministic fixture based on the observed multi-document failure should demonstrate that Results Matrix and implementation-arrangement evidence reaches the reviewer and prevents the prior false-negative conclusions.

## Out of scope

- Building a generalized policy-compliance engine.
- Requiring the model to reproduce every RRA section.
- Adding a second report file or new user journey.
- Treating all corporate Strategy commitments as CPF drafting requirements.
- Fixing the separate download-navigation bug in the same change unless explicitly added to the implementation scope.
