# CPF Reviewer Output, Research, and Interface Redesign

**Date:** 2026-08-13

**Status:** Approved design

**Branch:** `feat/mvp-review-run`

## 1. Objective

Redesign the CPF FCV Reviewer around its intended primary product: a detailed,
senior-facing CPF or CEN peer-review note. The application should combine the
editorial depth of the previously referenced CPF review notes with the visual
clarity and interaction quality of the FCV Project Screener.

The redesign has four linked goals:

1. provide a concise five-minute readout and a complete detailed note from one
   authoritative assessment;
2. assess the CPF or CEN against uploaded diagnostics, current country FCV
   dynamics, and the latest approved FCV Strategy material;
3. make current-country public-web research mandatory and reliable enough that
   blocking is a last resort; and
4. keep the public Render prototype and a future ITS implementation within
   their different information-access boundaries.

The separate FCV Project Screener repository is a read-only design reference.
This work must not modify it, couple the two applications, or deploy through
the stable screener.

## 2. Product principles

- The detailed review note is the primary analytical product.
- The five-minute readout is a faithful presentation layer over the same
  validated result, not a separate assessment.
- The review is priority-led and integrated, not a pathway-by-pathway report,
  scorecard, or collection of detached recommendation cards.
- The RRA is an analytical baseline when available, not the ceiling of the
  assessment.
- Current-country research is mandatory for every review.
- FCV Strategy pillars are named when materially relevant and explained in
  plain language.
- Evidence remains traceable without interrupting the main prose with internal
  IDs or application mechanics.
- A thin evidence base produces qualified analysis or, below the minimum
  research threshold, a blocked review. It never produces invented detail.
- Blocking occurs only after bounded, authorized recovery routes have been
  exhausted.

## 3. User flow and visual direction

### 3.1 Intake page

Use the approved screener-aligned visual direction: institutional top bar,
navy-gradient explanatory hero, strong typographic hierarchy, cyan accents,
generous guidance, and three prominent upload cards.

The upload cards are:

1. **Draft CPF / CEN** — required. The principal country engagement document
   to review.
2. **Accompanying CPF package documents** — optional. For example, results
   frameworks, completion reviews, diagnostics, annexes, or other package
   material.
3. **RRA and supporting analytics** — optional in the public prototype. This
   may include an RRA, equivalent FCV diagnostic, or other relevant analysis.

The intake page includes a collapsed **Additional guidance** field. There is no
Brief / Standard / In-depth selector. Selecting **Generate CPF review note**
starts one comprehensive review.

The interface must explain that the result includes a five-minute readout and a
full detailed note, and that the application is advisory rather than a
clearance or policy-determination mechanism.

### 3.2 Progress experience

The progress view uses the reference screener's level of clarity without
copying its operational logic. It shows meaningful stages, elapsed time or an
honest activity state, keepalives, and named recovery states.

Research progress should expose safe, content-free milestones such as:

- establishing the research mode;
- searching authoritative sources;
- checking developments since the RRA, when applicable;
- assessing structural and current dynamics;
- checking source coverage and diversity;
- filling material evidence gaps; and
- completing the current-country evidence baseline.

Progress and logs must not contain uploaded text, research prompts, source
extracts, generated prose, credentials, or sensitive filenames.

### 3.3 Separate results view

After successful generation, the application moves to a dedicated results
view rather than appending the note beneath the intake form. The result may be
implemented as a separate client view or route, but it must behave as a distinct
page with an obvious path back to start a new review.

The result header shows the country and document type, a restrained review
status, document coverage metadata, and a prominent **Download full detailed
note** action.

Two accessible tabs appear below the header:

- **Five-minute readout** — selected by default.
- **Detailed analysis** — the complete authoritative note.

Switching tabs is client-side and makes no additional model or research call.
The tab component must support semantic tab roles, roving tabindex, and
Left/Right, Home, and End keyboard behavior.

The download always uses the complete detailed result, regardless of the
currently selected tab.

## 4. Analytical output

### 4.1 One canonical result

One validated result contract supplies both views and the DOCX. The detailed
analysis is authoritative. The five-minute readout selects and compresses
fields from that result without changing the judgment, evidence, priority
order, or recommendations.

No second model request is made when the user changes views. Web and DOCX
outputs preserve the same substantive wording and priority order.

### 4.2 Five-minute readout

The summary contains three sections:

1. **Overall assessment**
2. **How the draft responds to the RRA, current FCV dynamics, and the FCV
   Strategy**
3. **Three to five priority measures to strengthen the CPF / CEN**

The second section is not a generic strengths list. It provides a balanced,
plain-language synthesis of where the draft already reflects relevant
diagnostic and Strategy considerations, where alignment is partial, and which
material dynamics remain insufficiently addressed.

The priority measures use the same order and substantive direction as the
detailed note. They are concise signposts rather than substitute analysis.

### 4.3 Detailed note structure

The complete note follows this order:

1. **Overall assessment** — normally one or two substantive paragraphs that
   state the bottom-line judgment, recognize genuine strengths, and identify
   the central opportunity or weakness.
2. **Three to five priority areas for strengthening** — coherent thematic
   sections in priority order.
3. **Limitations and document coverage** — a brief factual closing explaining
   missing, unreadable, dated, disputed, or otherwise limiting evidence.

The output should have the depth of a full peer-review note, normally around
three pages when the evidence supports it. Length is a consequence of adequate
analysis, not a quota: thin evidence should lead to a shorter qualified note,
not padding.

Each priority section integrates:

- what the CPF or CEN currently does well, does incompletely, or does not yet
  address;
- the relevant RRA or equivalent-diagnostic finding, if available;
- whether later evidence corroborates, qualifies, contradicts, or supersedes
  that finding;
- relevant structural and current country FCV dynamics;
- the applicable approved FCV Strategy pillar or shift, where material;
- why the issue matters for strategy, selectivity, implementation, risk, or
  results;
- a concrete, stage-appropriate strengthening measure;
- the target document and, where available, section, paragraph, table,
  indicator, or package component; and
- attached evidence references.

The Strategy pillar should be named only when there is a substantive
connection. The note must then explain that connection in plain language rather
than relying on institutional terminology.

Recommendations remain embedded in their analytical sections. There is no
detached recommendation-card section in the detailed note.

## 5. Mandatory current-country research

### 5.1 Research modes

Current-country public-web research runs for every review.

**RRA or accepted equivalent available:**

- treat the diagnostic as a historical and structural baseline;
- identify its publication or effective date;
- test whether its material structural findings remain supported;
- focus current research on developments from that date to the review date;
- identify dynamics that have emerged, changed, intensified, diminished, or
  become contested; and
- do not repeat dated diagnostic conclusions as current facts without
  corroboration.

**No RRA or accepted equivalent available:**

- build a holistic, bounded account of structural FCV drivers, sources of
  resilience, institutional and spatial dynamics, and relevant trajectory
  factors; and
- separately establish material recent developments and their implications for
  the CPF or CEN.

The absence of an RRA must be stated as a coverage limitation, but the review
must not describe a public-web synthesis as an RRA or equivalent official
diagnostic.

### 5.2 Source hierarchy

Research uses public sources only in the Render prototype. Priority is given
to:

1. World Bank and other relevant multilateral development-bank publications;
2. UN reporting and other authoritative intergovernmental sources;
3. International Crisis Group and comparable reputable specialist research;
4. public analytical products from established research organizations and
   think tanks; and
5. trusted media for recent developments that are not yet covered by slower
   institutional reporting.

Public analytical publications from providers such as ACLED may be used when
available without a licence. Licensed event-level data and other restricted
sources remain prohibited in the public prototype.

Research should seek multiple independent sources and represent credible
disagreement. A media report should not displace a more authoritative source
when both address the same established fact, but it may supply timely evidence
about a recent development.

### 5.3 Research sufficiency gate

The research controller validates the result before the review model can run.
The gate checks:

- retained claims have a public URL, publication date, source type, relevance,
  and relationship to the question being assessed;
- evidence covers both structural and current dynamics unless the RRA already
  supplies the structural baseline;
- at least one sufficiently recent source addresses the applicable research
  window;
- material themes are supported by more than one source where feasible;
- source types and publishers are not needlessly concentrated in one outlet;
- licensed or non-public material has been excluded;
- duplicate, malformed, or unsupported claims have been rejected; and
- disagreements, thin coverage, and unresolved questions are preserved as
  limitations rather than resolved by inference.

Exact numeric thresholds should be configurable and tested, not embedded in
prompt prose. The gate should evaluate material coverage rather than rewarding
an arbitrary volume of low-value claims.

### 5.4 Reliability cascade

The initial implementation uses one approved provider through multiple bounded
query routes:

1. primary country research covering authoritative sources and the applicable
   RRA/no-RRA mode;
2. structured parsing and claim validation;
3. one narrower retry when the response is empty, malformed, or materially
   incomplete;
4. one final source-emphasis search directed at missing themes and trusted
   source families; and
5. blocking with a safe research-unavailable category only if the evidence
   gate remains unmet.

Transient transport, rate-limit, and provider-server errors may be retried with
bounded exponential backoff and jitter. Authentication, configuration, policy,
or prohibited-source errors must fail without blind retry.

Each provider attempt has an application-level timeout. The research stage has
an overall configurable time budget below the deployment's request and worker
limits. Retries are not open-ended, and a successful sufficient attempt stops
the cascade.

The existing provider protocol should be strengthened so research execution,
structured parsing, and reliability policy are testable independently. The
design does not add a second provider to the public prototype. It preserves an
adapter boundary so an approved fallback provider can be added later without
changing the review contract.

### 5.5 Blocking and recovery

A completed review cannot be produced without a sufficient current-country
evidence baseline. If all authorized research routes fail, the application:

- does not expose a partial result as complete;
- preserves the assessment and uploaded package within the existing volatile
  session lifetime;
- shows a clear explanation that current-country research could not be
  established;
- offers **Retry research** without requiring the user to upload the package
  again; and
- records only a stable error category and safe operational metadata.

The user may reset the review. A document-only provisional note is not offered
because it could be mistaken for the intended complete assessment.

## 6. Deployment-specific source architecture

### 6.1 Public Render prototype

The public prototype has no SharePoint or internal corpus access. It uses:

- user-uploaded CPF/CEN and package documents;
- an optional user-uploaded RRA or supporting analysis;
- approved, versioned, non-confidential registry summaries; and
- mandatory public-web research.

It must not retrieve, bundle, expose, or infer access to the confidential RRA
corpus. It remains non-production, volatile, and advisory.

### 6.2 Future ITS implementation

The ITS implementation may add a permission-aware source adapter for a known
SharePoint repository containing RRAs and accepted equivalents. After country
detection, it should retrieve candidate diagnostics and retain:

- document title and country;
- authoritative-source identity;
- version or publication date;
- retrieval date;
- permission and access metadata; and
- an immutable reference or checksum suitable for reproducibility.

SharePoint retrieval does not replace current-country research. It supplies the
diagnostic baseline and determines the time window that research must update.

If SharePoint contains no suitable diagnostic, the ITS implementation uses the
same no-RRA holistic research mode. If the available diagnostic is old,
incomplete, or superseded by material developments, the research scope expands
accordingly.

### 6.3 Source precedence and conflicts

When ITS retrieves an authoritative SharePoint diagnostic and the user also
uploads a candidate version:

1. compare country, title, publication/effective date, version markers, and
   source authority;
2. use the newest verified authoritative version as the primary diagnostic;
3. retain the other version as supporting evidence when it is relevant and
   permitted; and
4. pause for user confirmation when date, version, country, or authority
   conflicts cannot be resolved deterministically.

The application must never silently choose between materially conflicting
diagnostics.

Both deployments use the same source-candidate and evidence-pack interfaces.
The difference is which adapters are enabled and authorized.

## 7. Data flow

The revised high-level pipeline is:

1. validate and extract uploads;
2. detect and, when necessary, confirm the country;
3. resolve diagnostic candidates and establish RRA/no-RRA research mode;
4. conduct mandatory current-country research through the reliability cascade;
5. validate research sufficiency and convert retained claims into traceable
   current-context evidence items;
6. combine uploaded, registry, correction, and current-context evidence in the
   reproducible evidence pack;
7. create the diagnostic and Strategy map;
8. generate one priority-led canonical review result;
9. validate evidence fidelity, stage realism, Strategy claims, structure, and
   summary/detail consistency;
10. perform the existing bounded repair only when eligible;
11. render the five-minute readout and detailed view; and
12. export the same detailed result to DOCX.

The current production gap, in which the `research` step only attaches a
gateway object without conducting a search or adding research evidence, must be
closed before the redesign can be considered functional.

## 8. Error handling and observability

Research failures need stable categories distinct from general review failure,
including at least:

- transient provider failure;
- provider timeout;
- malformed research response;
- insufficient current evidence;
- prohibited or non-public source rejection; and
- research configuration failure.

User-facing messages remain concise and actionable. Application and Render logs
may record:

- assessment-safe identifier;
- stage and attempt number;
- duration;
- retained and rejected claim counts;
- source-type diversity count;
- retry or terminal category; and
- final success or failure state.

Logs must not record document content, generated prose, claim text, prompts,
raw provider responses, source extracts, credentials, or sensitive filenames.

## 9. Verification and acceptance

### 9.1 Automated verification

Use test-driven implementation. Add deterministic tests for:

- production runtime execution of mandatory research;
- RRA-present and RRA-absent research prompts and windows;
- structured claim parsing, rejection, and evidence-pack inclusion;
- source hierarchy and sufficiency behavior;
- malformed, empty, thin, contradictory, prohibited, and licensed results;
- transient retry, backoff, timeout, final fallback, and stop-on-success;
- no retry for authentication, configuration, or policy failures;
- blocked-state preservation and retry-research behavior;
- truthful safe progress events and stable failure categories;
- log redaction;
- canonical-result consistency across summary, detailed web view, and DOCX;
- accessible tabs and keyboard behavior;
- dedicated intake/results page state; and
- responsive layout at desktop and narrow-mobile widths.

The existing policy, evidence, source-security, extraction, session-isolation,
and output-safety tests must continue to pass.

### 9.2 Reference-based output evaluation

Run representative approved CPF material, including the approved Benin sample,
through the real configured research and review path. Synthetic adapters remain
useful for deterministic tests but do not establish output quality.

Evaluate the detailed note for:

- defensible overall judgment;
- CPF/CEN and country specificity;
- appropriate use and dating of RRA findings;
- adequate treatment of current structural and recent FCV dynamics;
- accurate and material FCV Strategy alignment;
- prioritization;
- actionable and precisely targeted recommendations;
- stage realism;
- evidence fidelity and source traceability;
- coherent peer-review-note prose; and
- absence of generic pathway-by-pathway output.

The established rubric target remains an average of at least 1.5 out of 2 with
no zero score on any material criterion.

### 9.3 Browser, export, and Render validation

Before completion:

- test the intake, progress, blocked/retry, summary, detailed, correction,
  reset, and download flows in a real browser;
- verify desktop and mobile layouts and keyboard operation;
- inspect the approved Benin five-minute readout and complete detailed note as
  rendered text;
- download the DOCX, confirm substantive parity, and visually render it when
  the document-rendering runtime is available;
- deploy only with explicit user authorization;
- run the approved Benin case against the deployed Render service; and
- inspect Render logs for research attempts, stage completion, retry behavior,
  timeouts, safe failures, and absence of sensitive content.

Passing a synthetic browser fixture is not sufficient evidence that the
detailed-note product works as intended.

## 10. Completion criteria

The redesign is complete only when:

- the intake experience closely follows the approved screener-aligned visual
  direction;
- successful generation opens a dedicated results view;
- the five-minute readout is the default and the full note remains one click
  away;
- downloads always contain the full detailed note;
- every run conducts and validates current-country research;
- RRA-present research covers the RRA-to-present gap;
- no-RRA research covers structural and current FCV dynamics holistically;
- the detailed result is priority-led, integrated, evidence-linked, and of
  peer-review-note quality;
- FCV Strategy pillars are named only where material and explained plainly;
- the public and ITS source boundaries are documented and enforced;
- insufficient research blocks only after bounded recovery attempts;
- approved-material output evaluation meets the rubric;
- browser, DOCX, and Render validation pass; and
- no restricted corpus, secret, document content, or generated note text is
  exposed through the repository or logs.
