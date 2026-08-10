# CPF FCV Review Prototype Design

**Date:** 10 August 2026  
**Status:** Revised product and technical specification for user approval  
**Primary user:** Country teams drafting or revising a Country Partnership Framework (CPF) or Country Engagement Note (CEN)  
**Secondary future user:** FCV and corporate reviewers  
**Purpose:** Define a lean standalone web prototype and an implementation-ready design that ITS can later use to build a production application.

## 1. Product decision

Build a standalone, country-team-first CPF FCV review prototype. It should borrow proven interaction and utility patterns from the FCV Project Screener without copying that product's project-specific analytical stages, rating gauges, instrument routing, or monolithic implementation. The prototype must be deployed, tested, and governed separately and must not modify or share mutable state with the existing stable FCV Project Screener service.

The prototype is a reference implementation and design-validation tool. It is not the production application, a formal FCV review mechanism, a source of institutional determinations, or a policy-clearance system. ITS may later implement the product within approved WBG infrastructure and integrate it alongside the FCV Project Screener.

## 2. Product objective

The product helps a country team understand how well a draft CPF or CEN:

1. reflects and responds to the country's principal FCV drivers, sources of resilience, and trajectory-shifting priorities identified in the Risk and Resilience Assessment (RRA) or equivalent diagnostic; and
2. operationalizes the WBG FCV Strategy 2026-2030, including its four strategic shifts and emphasis on trajectory-shifting action.

It then translates those judgments into a small number of specific, stage-appropriate improvements tied to relevant sections of the CPF package.

The product is developmental and advisory. It supports informed country teams as peers and does not explain routine Bank processes unnecessarily. A completed run is not FCV clearance, OPCS or legal advice, policy concurrence, management approval, an official country classification, or an eligibility, compliance, applicability, or process-trigger determination.

### 2.1 Key design guardrails

- Findings must be traceable to uploaded or permission-aware retrieved documents, retained public current-context sources, approved institutional registry language, labelled user input, or clearly labelled analytical inference.
- The model must not determine that a policy or guidance provision applies, is triggered, is satisfied, or is breached. It must not determine PC14 or IDA21 FCV Policy Commitment status, FCV Envelope eligibility or readiness, PRA/RECA/TAA status, OP 7.30 applicability, an official FCV classification, or any equivalent institutional outcome.
- A policy-sensitive topic may be named only through approved registry-controlled language. If the registry does not support the statement and its applicability conditions, the output must omit the claim and may use only an approved generic prompt to consult the relevant policy owner.
- The product may identify strategic strengths, gaps, risks, questions, and practical options. User-facing wording should remain collegial and improvement-oriented, even when internal validation uses sharper analytical labels.
- Suggested drafting is optional, location-specific, labelled as suggested text, and never presented as approved institutional wording.
- Politically or institutionally sensitive content must carry a sensitivity-handling category before display or export.

## 3. Users and use cases

### 3.1 Primary user

The first release is for country teams, including CPF/CEN authors, country management units, Country Directors' offices, Operations Managers, country coordinators, and relevant technical colleagues.

The primary job is:

> Help us see whether our country strategy reflects the main FCV diagnostic and the refreshed FCV Strategy, what important issues remain weak or missing, and what practical changes are still feasible at this stage.

### 3.2 Secondary future user

FCV, OPCS, regional Development Effectiveness, and other authorized corporate reviewers may later use the same evidence and analytical engine to prepare structured review comments. The prototype does not provide a separate reviewer lane. A future reviewer output should be generated from the validated Review Result rather than through a second analysis.

### 3.3 Review stages

One workflow supports early drafting, concept review, decision review, Regional Operations Committee (ROC) or Operations Committee (OC) review, finalization, and response to prior comments. The selected stage does not change the underlying analytical questions, but it changes how findings are prioritized, framed, and translated into feasible actions.

| Selected stage | Recommendation behavior |
|---|---|
| Early drafting | May challenge strategic framing, selectivity, causal logic, outcome structure, trajectory-shifting priorities, and the theory of change. |
| Concept review | Prioritizes diagnostic alignment, strategic choices, outcome architecture, One WBG roles, partnerships, and the emerging results logic. |
| Decision review / ROC / OC | Focuses on specific revisions to objectives, results, risks, implementation arrangements, program calibration, and management-ready decisions. It should not reopen settled architecture without a material FCV reason. |
| Finalization | Limits advice to targeted, high-value edits, factual corrections, caveats, indicator refinements, and issues that genuinely require confirmation. |
| Response to comments | Links each option to the relevant prior comment and document location, distinguishes accept / partially accept / explain / verify options, and avoids inventing agreement or clearance. |

## 4. Success criteria

The prototype is ready for ITS handoff when:

- country-team users understand the two core judgments without explanation from the product owner;
- users can identify the most important actions, why they matter, and where to apply them;
- recommendations are specific, evidence-grounded, and realistic for the selected review stage;
- confirmed user questions receive substantive, traceable responses in a dedicated section;
- prose is understandable to a non-FCV specialist and reads like a concise WBG technical note;
- FCV reviewer testing identifies no unresolved material factual error, dangerous omission, or seriously miscalibrated recommendation in the approved test cases;
- no factual error concerning OPCS policy or guidance appears in displayed or exported output, enforced by registry-controlled language, applicability rules, and a prohibition on unsupported policy claims;
- the Word export is usable with limited editing; and
- missing inputs, weak evidence, and processing failures are visible rather than concealed.

## 5. Deliberate scope

### 5.1 Included in the prototype

- CPF/CEN and supporting-document upload
- Compact review-stage and intended-use intake
- Free-text qualitative context, constraints, sensitivities, and priority questions
- Detection and confirmation of priority questions
- Document-readiness and extraction checks
- Bounded public current-context research as a recency and plausibility check
- Two-tier CPF FCV assessment
- Developed prose results in a technical-note format
- A prioritized action plan
- Dedicated responses to priority questions
- Evidence, limitations, and specialist-confirmation views
- Optional targeted draft language
- Correction-and-rerun capability
- Word export
- Optional post-analysis transformations as later extensions
- Reproducibility metadata sufficient to explain the inputs, sources, registry versions, model configuration, and analysis version used for a run

### 5.2 Excluded from the prototype

- A separate reviewer lane
- Headline FCV score or sensitivity/responsiveness gauges
- Formal PC14, FCV Envelope, PRA/RECA/TAA, OP 7.30, or other policy determinations
- Automatic internal Bank retrieval in the Render prototype
- User accounts, collaboration, workflow routing, approvals, or database-backed persistence
- Production authentication, hosting, document retention, audit logging, and WBG access controls
- Direct email creation or sending
- Full integration into the FCV Project Screener

These exclusions keep the prototype focused. They do not preclude later ITS implementation.

### 5.3 Delivery phasing

The design separates proof of value from institutional production controls.

| Phase | Purpose | Included capabilities | Explicit boundary |
|---|---|---|---|
| MVP reference prototype | Validate the country-team user journey and the analytical method. | Upload and extraction; document-role assignment; grouped diagnostic and CPF mapping; the two core reviews where evidence permits; priority-question responses; stage-calibrated options; traceable technical-note result; correction and rerun; Word export. | Runs only in the isolated prototype environment with approved historical, synthetic, or non-sensitive packages. No internal retrieval, user accounts, database, durable document storage, formal reviewer lane, or policy determination. |
| Validation layer | Establish that the method is reliable, policy-safe, and useful before ITS handoff. | Structured schemas; traceability, policy-language, coverage, sensitivity, and output-parity validators; historical evaluations; adversarial and failure-mode tests; country-team pilots; controlled registry-summary updates. | Does not convert the Render prototype into an operational WBG system or authorize sensitive CPF material. |
| ITS production implementation | Rebuild or adapt the validated design within approved WBG infrastructure. | WBG identity and permissions; authoritative SharePoint retrieval; approved model and web-search controls; retention, deletion, audit, monitoring, support, and incident processes; governed registries; optional authorized reviewer workflows. | Requires ITS, information-security, data-governance, OPCS, FCV methodology, and other relevant approvals before operational use. |

## 6. User journey

### Step 1. Set the scene

The user provides:

- country and CPF/CEN period;
- review stage and intended use;
- one CPF/CEN draft as the required primary document;
- optional RRA, results framework, theory of change, annexes, prior comments, or other relevant material;
- optional qualitative context, known constraints, sensitivities, or decisions already taken; and
- optional questions on which the user wants explicit feedback.

The intake remains compact. The application infers document roles and relevant analysis from the package.

### Step 2. Read and build context

The application performs one user-visible run with these internal steps:

1. intake, file validation, extraction, structural referencing, and document-role assignment;
2. source resolution, including the authoritative RRA route available to the deployment;
3. Evidence Pack construction from documents, user guidance, public current-context sources, and approved registries;
4. grouped diagnostic mapping and CPF strategy mapping;
5. core and supporting review generation, priority-question responses, and recommendation prioritization;
6. deterministic validation of traceability, registry-controlled language, sensitivity handling, stage calibration, and schema integrity;
7. one bounded model repair when a repairable validation failure occurs; and
8. rendering of the same validated Review Result to the browser and Word.

These are real orchestration steps within one visible run, not separate user-facing analytical stages. The interface shows accurate progress labels, keepalives during long operations, and a named failure state when a step cannot complete. It does not imply success while validation or rendering is still pending and does not require a strategy-map confirmation checkpoint before completing the analysis.

### Step 3. Review the results

The result page presents:

1. a short executive judgment;
2. Core Review 1, either RRA/equivalent diagnostic alignment or, when no suitable diagnostic is available, a clearly downgraded limited diagnostic-framing assessment;
3. Core Review 2, WBG FCV Strategy alignment;
4. dedicated responses to the user's priority questions;
5. Tier 1 core recommendations;
6. Tier 2 additional considerations;
7. questions, evidence gaps, and matters for confirmation; and
8. a collapsible summary of what the application understood from the package.

### Step 4. Act

The user can:

- inspect the evidence behind a finding;
- request practical options;
- request targeted draft language for a named CPF section;
- add a labelled user correction or contextual qualification and rerun the analysis; or
- export the complete technical note to Word.

Future follow-ons may transform the validated result into a reviewer email, management brief, meeting intervention, or other format without rerunning the core analysis.

## 7. Output style and information hierarchy

The default output is prose-led and should read like a concise WBG technical note, not a dashboard, checklist, or collection of thin cards.

- Lead each paragraph with a clear point and develop the explanation in accessible prose.
- Use headings, status labels, and compact metadata for navigation, not as substitutes for analysis.
- Explain why a finding matters, how the evidence supports it, and what practical change follows.
- Avoid generic FCV language, unexplained jargon, and superficial bullet lists.
- Distinguish facts reported by documents, current external evidence, analytical inferences, and drafting suggestions.
- Do not automatically rewrite large CPF sections.

The output does not display a headline score. It may use restrained status labels such as `Aligned`, `Partially aligned`, `Not reflected`, `Strong foundation`, `Needs strengthening`, or `Material gap` at the level of specific findings.

### 7.1 Language behavior

English is the default and the only fully validated output language for the MVP. The prototype may accept English documents and limited French-language or mixed English-French text where extraction quality is adequate. It should preserve the original excerpt, provide an English analytical paraphrase, and label any machine-translated wording. It must not imply full French-language quality assurance. Other input or output languages are outside the MVP unless separately approved and tested.

### 7.2 Sensitivity handling

Each material finding and drafting option carries one user-facing handling category:

1. `Suitable to state directly`.
2. `Frame cautiously`.
3. `Confirm with country team or FCV specialist`.
4. `Do not suggest for inclusion without guidance`.

The category controls display wording and export treatment. It is not an information-classification decision and does not override WBG access, disclosure, records, or confidentiality rules. Content in the fourth category is shown as a matter for consultation, not as ready-to-paste CPF text.

## 8. Analytical hierarchy

### 8.1 Tier 1. Core alignment

Tier 1 is mandatory and leads every review.

#### Core Review 1. Diagnostic-CPF alignment

When a current RRA or accepted equivalent FCV diagnostic is available, assess whether the CPF reflects and responds to its material findings. The diagnostic map first groups and prioritizes source findings rather than treating every sentence or issue as an equal programming requirement:

1. **Principal FCV drivers and trajectory-shifting priorities** that should shape CPF objectives, selectivity, or strategic causal logic.
2. **Delivery and implementation risks** that should shape access, partnerships, targeting, supervision, sequencing, or adaptive arrangements.
3. **Contextual conditions** that are relevant to interpretation but do not necessarily require direct CPF programming.
4. **Sources of resilience and opportunities** that can support prevention, recovery, institutional legitimacy, inclusion, or trajectory-shifting action.

Within each group, entries are ordered by materiality and retain their relationship to the original diagnostic wording. The application must not over-penalize a CPF for not repeating the whole RRA or convert background conditions into spurious programming requirements.

For each prioritized entry, distinguish:

- adequately reflected and operationalized;
- recognized but weakly translated into objectives, programming, partnerships, implementation, or results;
- omitted without a documented rationale;
- legitimately updated or superseded by newer evidence; and
- contextual only, with no direct CPF response expected.

The analysis considers prominence. Treatment in the CPF's main narrative carries different strategic weight from a reference buried in an annex. Each entry identifies where it appears in the diagnostic and CPF, how it was grouped, its priority basis, and any uncertainty in the mapping.

When the RRA is old, the public current-context scan tests whether material elements appear outdated, contradicted, or incomplete. It does not replace or silently rewrite the diagnostic. The result explains whether the CPF updates the diagnostic credibly, overlooks a still-material issue, or responds to a different but well-supported risk.

If no current RRA or accepted equivalent diagnostic is available after the deployment-specific retrieval and upload fallback, Core Review 1 is renamed `Limited FCV diagnostic-framing assessment`. It may compare the CPF's framing with uploaded supporting material and retained public current-context evidence, but it must not claim or rate RRA alignment, completeness against an RRA, or diagnostic compliance. The limitation is prominent in the executive judgment, detailed result, recommendations, and export metadata.

#### Core Review 2. WBG FCV Strategy 2026-2030 alignment

Assess the CPF against the Strategy's four shifts:

1. **Anticipate better.** Does the CPF adopt a proactive risk posture and identify how the program will adjust as conditions change?
2. **Adopt a differentiated approach.** Is the program selective and calibrated to the country's FCV trajectory and potential for lasting development impact, including government commitment and viable delivery pathways?
3. **Deliver as One WBG on the jobs agenda.** Does the CPF articulate relevant jobs objectives and the roles of IDA/IBRD, IFC, and MIGA, including attention to micro, small, and medium enterprises and the domestic private sector?
4. **Enhance knowledge, toolkit, partnerships, and staffing.** Does the CPF use diagnostic knowledge, operational flexibilities, adaptive delivery, partnerships, and suitable capabilities to deliver in the FCV context?

The Strategy analysis must also:

- identify the trajectory-shifting actions named by the CPF itself;
- assess how the program supports each action;
- consider government commitment and program-level calibration;
- distinguish actions with potential to change the FCV trajectory from routine sector activity; and
- remain analytical rather than tick-box based.

Tier 1 normally produces no more than three core recommendations. Fewer are acceptable when the evidence does not justify three.

### 8.2 Tier 2. Supporting CPF considerations

Tier 2 deepens or qualifies the two core judgments. It covers:

- current security, political-economy, and regional dynamics;
- strategic causal logic and reform appetite;
- selectivity and program calibration;
- delivery feasibility and adaptive arrangements;
- conflict sensitivity and Do No Harm;
- geographic and distributional choices;
- partnerships and One WBG roles;
- results, monitoring, and adaptation;
- continuity with the previous CPF/CEN and relevant lessons; and
- feasibility of changes at the selected review stage.

A Tier 2 issue is promoted to Tier 1 only when it materially changes the RRA or FCV Strategy judgment. Tier 2 normally produces no more than five additional improvements.

### 8.3 Recommendation hierarchy

The application distinguishes:

1. **Core priorities:** usually two or three material changes derived from Tier 1.
2. **Additional improvements:** selected Tier 2 recommendations.
3. **Questions and verification needs:** uncertainties or matters for country knowledge and specialist confirmation. These are not disguised as recommendations.
4. **Optional drafting support:** generated only when the user requests it for a specific finding or document location.

Each recommendation includes developed prose covering the finding, why it matters, evidence basis, practical implication, relevant document location, review-stage timing, and whether specialist confirmation is advisable.

## 9. Qualitative inputs and priority questions

The intake includes an `Analysis Guidance` field following the proven Project Screener pattern. The application detects likely questions or priority points, shows them to the user, and lets the user confirm which require dedicated responses.

Every confirmed question receives a separate result containing:

- a direct answer;
- a developed explanation;
- the evidence basis;
- links to relevant core or supporting findings;
- confidence or an explicit evidence gap; and
- any practical implication.

Priority-question responses are included in the Word export. If available evidence cannot answer a question, the application states that directly.

## 10. Evidence model

### 10.1 Source hierarchy

Material findings distinguish among:

1. uploaded CPF/CEN package evidence;
2. uploaded or internally retrieved RRA/diagnostic evidence;
3. current trusted-source evidence;
4. curated institutional strategy, policy, and guidance; and
5. analytical inference.

Every Tier 1 finding retains source references in the structured result. Inferences must be labelled and cannot be presented as document facts.

### 10.2 Public current-context recency and plausibility check

The application conducts a bounded public web scan only to test the recency and plausibility of issues material to the review. It is not a new country diagnostic, does not recreate the RRA, and does not add background that has no bearing on a CPF judgment.

The scan prioritizes dated, attributable, publicly accessible material from sources such as:

- United Nations agencies and relevant mission reporting;
- International Crisis Group;
- ACAPS;
- IMF Article IV and country reports;
- OECD States of Fragility or governance analysis;
- public World Bank country material; and
- reputable specialist media, research organizations, and think tanks where directly relevant.

There is no dependency on licensed ACLED data or any other licensed conflict-event dataset. Publicly accessible ACLED analysis may be considered like any other public source, but the prototype must not require, query, reproduce, or imply access to licensed event-level data.

Queries are driven by material uncertainties, normally three to five, rather than a fixed quota. A retained current-context claim must:

- be dated and linked to a public source;
- identify the source type;
- be directly relevant to a diagnostic or CPF judgment;
- distinguish fact from interpretation;
- be framed cautiously when politically sensitive; and
- record whether it corroborates, qualifies, contradicts, or cannot resolve the package's framing.

Where credible sources disagree, the Evidence Pack retains the discrepancy. The tool presents it as uncertainty or a question and does not automatically privilege the newest source. Failure of the public scan does not block review of the uploaded package, but the lack of a recency check is visible.

### 10.3 Authoritative RRA source and fallback

The source route depends on the deployment phase. An `accepted equivalent FCV diagnostic` is one identified by the governed FCV methodology rules, not one inferred ad hoc by the model. For prototype test cases, the approved test-case manifest records whether an uploaded document is an accepted equivalent.


**Render reference prototype.** The prototype uses user uploads or approved non-confidential, versioned summaries. It has no internal SharePoint retrieval. If no suitable RRA or equivalent is uploaded, the user is invited to provide one and may proceed only with the downgraded limited diagnostic-framing assessment defined in Section 8.1.

**ITS production implementation.** A permission-aware backend service retrieves current RRAs or accepted equivalent diagnostics from the authoritative SharePoint folder designated for this purpose. Retrieval is performed by the application layer under the current user's permissions, not by asking the model to search internal systems. The backend must:

- retrieve and parse the direct SharePoint original in preference to a derived Markdown or other transformed copy;
- record the exact title, date, version, source URL or stable item identifier, file hash where permitted, and retrieval time;
- verify the country, diagnostic type, status, and version;
- apply an approved rule for identifying the current authoritative version;
- preserve the user's upload as an explicit fallback when retrieval fails, access is denied, or the user identifies a more appropriate document;
- display which diagnostic was used before or with the result; and
- avoid silently substituting an uncertain, superseded, or cross-country result.

When a direct SharePoint original and a derived summary conflict, the original controls. The discrepancy is logged for registry or source-owner follow-up. If no suitable diagnostic is found, Core Review 1 is downgraded rather than inferred.

### 10.4 Finding-level traceability

Every material finding, priority-question response, and recommendation retains a structured evidence locator. For uploaded or retrieved documents it includes:

- source document title and version;
- page number where the source format provides a stable page;
- section label or heading;
- paragraph, table, figure, annex, or other locator where available;
- a short excerpt in the source language or a clearly marked paraphrase;
- evidence type: document fact, current-context claim, institutional registry language, labelled user input, or analytical inference; and
- confidence, extraction limitation, and any conflicting source.

If a page number is unavailable or unstable, the heading plus paragraph/table/figure locator is mandatory. The application must never invent a page number. Recommendations also identify the target CPF page, section, heading, or annex where the proposed change would be made.

### 10.5 Labelled user corrections

A user may add context, dispute a finding, or correct an extracted fact and rerun the review. Each correction is retained in the active session as `User-provided correction` with its time, affected finding, and optional rationale. A correction does not become an independently verified fact unless supported by an uploaded, retrieved, or public source. The rerun must preserve visible provenance and may note unresolved disagreement rather than allowing user input to erase contrary evidence.

## 11. OPCS and institutional accuracy

The acceptance requirement is that no factual error concerning OPCS policy or guidance appears in displayed or exported output. The design implements this as a controlled-language and source-governance requirement, not as a request for the generative model to remember or interpret policy correctly.

### 11.1 Authoritative ownership and runtime sources

OPCS owns the authoritative policy and guidance registry in a designated SharePoint location. Each registry entry contains:

- authoritative title, identifier, document type, owner, and source link;
- effective, verified, superseded, and review dates where applicable;
- version and change record;
- narrowly defined applicability conditions that the application is allowed to test;
- approved user-facing summary language and approved generic referral language;
- prohibited claims, unsafe inferences, and terms that must not be generated;
- permitted sensitivity category and export behavior; and
- required policy-owner or specialist confirmation.

The FCV Strategy analytical registry is separately versioned and owned by the designated FCV methodology owner. It cannot override or restate OPCS policy or guidance.

The ITS production application retrieves current registry entries from the authoritative SharePoint sources through a permission-aware backend service. The Render prototype never retrieves or embeds the confidential source corpus. It uses only approved, versioned, non-confidential summaries exported through the registry change-control process.

### 11.2 Runtime enforcement

The model receives approved registry summaries, not open-ended instructions to interpret policy. Policy-sensitive output is constrained as follows:

1. Named policy or guidance wording must match an approved registry statement and registry identifier.
2. The application applies deterministic post-generation checks for unsupported policy names, requirements, thresholds, triggers, determinations, and outdated identifiers.
3. A policy-sensitive statement that is not supported by the active registry version is removed from display and export. It is not rescued by a generic confidence caveat.
4. When an issue warrants consultation but the registry does not authorize a substantive statement, the application may use only the approved generic referral language.
5. The output must never state or imply that criteria are met, a process is triggered, a package is compliant, an allocation is warranted, or a policy owner has concurred.
6. The validator records the registry entry and exact approved language used. Tier 1 fails closed if an unsupported policy claim remains.

Country teams are presumed to understand routine institutional processes. The product should not produce a quasi-clearance checklist or name a policy pathway merely because user guidance asks it to do so.

### 11.3 Versioning and change control

Every registry release has an owner, semantic version, approval date, effective date, change summary, deprecated entries, and regression-test results. A change requires:

1. a proposed update tied to an authoritative source;
2. review and approval by the registry owner;
3. policy-sensitive regression and adversarial tests;
4. publication of an immutable approved release;
5. controlled promotion to the prototype summary bundle and, separately, production; and
6. rollback instructions.

Each review records the registry versions used. A superseded or expired registry version cannot start a new run. Registry unavailability disables named policy and guidance statements rather than falling back to model knowledge.

Before ITS handoff, an authorized process validates the registry summaries and policy-sensitive regression cases against the internal source corpus. Prototype release is blocked by any unresolved OPCS factual error or unsupported policy claim.

## 12. Technical architecture

### 12.1 Reference prototype stack and orchestration

Use a small Flask backend and vanilla JavaScript frontend to remain close to the proven Project Screener stack and keep the reference implementation easy to inspect. Keep the architecture interface-oriented so ITS can reproduce it in another approved stack.

The prototype uses one visible analysis run with an assessment-scoped identifier and multiple explicit internal operations:

1. validation and extraction;
2. deployment-aware source resolution;
3. Evidence Pack construction;
4. diagnostic and CPF mapping;
5. review and recommendation generation;
6. deterministic validation and, where safe, one bounded repair;
7. Review Result finalization; and
8. browser and Word rendering.

The backend streams truthful step-start, progress, keepalive, completion, warning, and failure events. Server-side time limits sit below browser or proxy abort limits so the user receives a named application error rather than an indefinite loading state. Partial internal outputs are not represented as a completed review.

Optional drafting and later transformations are separate follow-on calls against the immutable validated Review Result. They do not rerun or silently alter the core review.

### 12.2 Components

#### Frontend

Owns intake, uploads, qualitative guidance, progress display, technical-note results, correction-and-rerun, optional follow-ons, and export actions.

#### Intake and document service

Validates file types and sizes, extracts supported formats, identifies document roles, captures page/heading/table/figure locators, and reports unreadable or missing inputs.

#### Source adapters

Expose a common interface for prototype uploads, approved summary bundles, public web research, the production RRA SharePoint folder, and the production OPCS and FCV Strategy registries. The model never receives credentials and never searches SharePoint directly. Adapters return content plus authoritative-source, version, permission, and retrieval metadata.

#### Evidence builder

Combines uploaded evidence, current-context research, user guidance, and the versioned institutional registry into one Evidence Pack.

#### Review engine

Applies Tier 1 and Tier 2 analysis to the Evidence Pack, answers confirmed priority questions, prioritizes recommendations, and produces one Review Result.

#### Quality validators

Check evidence locators, excerpt fidelity, policy-language allowlisting, unsupported determination language, required analytical coverage, diagnostic-mode accuracy, recommendation stage calibration, sensitivity handling, user-correction labels, prose depth, priority-question completeness, allowed status values, reproducibility metadata, and structural consistency. Tier 1 does not display when a material validation failure remains.

#### Output service

Renders the same validated Review Result to the browser and Word. This prevents the web and exported outputs from diverging.

#### Optional follow-on service

Uses the validated Review Result to create targeted draft language or later transformations. It cannot silently alter the core assessment.

#### Volatile session state

The MVP has no database, durable server file store, or browser localStorage for review contents. Uploaded bytes, extracted text, Evidence Packs, Review Results, and corrections exist only in assessment-scoped volatile server memory for the active run and bounded reruns. Browser sessionStorage may hold only the assessment identifier, non-sensitive navigation state, and server-issued status needed to recover the active tab.

State is isolated by assessment identifier, unavailable to other tabs or users, and purged on explicit reset, expiry, process restart, or completion of the configured short session window. The prototype does not promise recovery after restart. Word files are generated in memory and returned directly. Filenames, excerpts, document text, and user guidance are excluded from application logs. Production retention and audit behavior must be defined separately by ITS and data-governance owners.

### 12.3 Reuse boundary with the Project Screener

Reuse or adapt:

- document extraction helpers;
- upload validation and warnings;
- processing status, keepalives, and timeout handling;
- qualitative-question detection and confirmation;
- evidence and parsing-warning patterns;
- per-assessment isolation, keepalive, timeout, and best-effort volatile-state patterns, adapted to prohibit durable browser storage; and
- true DOCX export patterns.

Do not carry over:

- project-instrument routing;
- three visible project-analysis stages;
- sensitivity/responsiveness gauges;
- project lifecycle and instrument vocabulary logic;
- project-specific prompts and policy rules; or
- the large monolithic backend and single-page files as the new module structure.

## 13. Data contracts

### 13.1 Evidence Pack

The Evidence Pack contains:

- assessment identifier, run metadata, selected review stage, intended use, and active diagnostic mode;
- user guidance, confirmed priority questions, and labelled user corrections;
- document inventory with role, authoritative-source status, version, retrieval route, extraction status, language, and available structural locators;
- CPF strategy map, including objectives, outcome areas, program choices, partnerships, implementation assumptions, results, prominence, and evidence locators;
- grouped and prioritized diagnostic map, including principal drivers, delivery risks, contextual conditions, resilience factors, trajectory-shifting priorities, grouping rationale, materiality, diagnostic date, and source locators;
- public current-context claims with dates, URLs, source types, relevance, sensitivity, and corroborate / qualify / contradict / unresolved status;
- exact institutional registry entries and approved language made available to the run;
- readiness warnings, extraction limitations, source conflicts, and unresolved questions; and
- evidence objects containing page, section, heading, paragraph/table/figure locator, excerpt or marked paraphrase, evidence type, and confidence.

### 13.2 Review Result

The Review Result contains:

- metadata, package-understanding summary, active diagnostic mode, and prominent limitations;
- executive judgment;
- either the diagnostic-CPF alignment narrative and prioritized mapping entries or the explicitly downgraded limited diagnostic-framing assessment;
- treatment of legitimate updates beyond an older diagnostic;
- FCV Strategy alignment narrative;
- one developed assessment for each of the four shifts;
- trajectory-shifting actions and program-support analysis;
- Tier 2 supporting findings;
- priority-question responses;
- core priorities and additional improvements with stage-specific behavior;
- questions and verification needs;
- finding and target-document locators;
- evidence, confidence, correction, and sensitivity references;
- matters for country-team, FCV specialist, OPCS, legal, or other relevant confirmation without implied determinations;
- exact source and registry references; and
- export and reproducibility metadata.

The browser and DOCX must consume this contract rather than independently interpreting raw model prose.

### 13.3 Reproducibility metadata

Every completed run and Word export records, without retaining document contents:

- run date and time;
- application release, schema version, analytical rubric version, and prompt bundle version;
- model provider, model identifier, and available model configuration fields;
- registry names and immutable versions;
- public source scan time and retained URLs;
- uploaded or retrieved document names, source versions, timestamps, and hashes where permitted;
- selected review stage, intended use, output language, and diagnostic mode;
- confirmed priority questions and a hash or safe structured record of analysis guidance;
- labelled corrections and rerun parent identifier; and
- validation results, repair count, and known limitations.

The metadata supports comparison of reruns. It does not promise identical generative wording across model or source changes. A rerun should identify material changes in documents, registries, public sources, corrections, or application versions.

## 14. Failure handling

### 14.1 Missing or unreadable material

- If the primary CPF/CEN is unreadable, stop because a valid review is impossible.
- If the RRA is missing, use the platform-aware fallback in Section 10.3 and record the limitation.
- If the results framework or annex is missing, continue where possible and identify the judgments affected.
- If a scanned or partially extracted file matters to the analysis, name the file and invite a readable replacement.

### 14.2 Weak or conflicting external evidence

- If current-context research fails, continue using uploaded material and state that conditions were not independently updated.
- If sources conflict, retain the dated discrepancy and present it as an uncertainty or question.
- Do not force a false resolution or automatically privilege newer evidence without assessing credibility and relevance.

### 14.3 Model and structured-output failures

- Validate the Evidence Pack and Review Result before display.
- Retry a malformed model response once using the same Evidence Pack.
- If an optional section fails, preserve the valid core review and label the affected section unavailable.
- If Tier 1 fails validation, do not display a misleading partial judgment.
- Preserve only the active volatile assessment state long enough for a bounded retry without re-upload. If the state has expired or the process restarted, require a new upload and explain why.

## 15. Privacy and deployment boundary

The reference prototype is not approved for operational, confidential, or otherwise sensitive CPF material. The isolated Render service may use only approved historical packages, synthetic packages, or non-sensitive test packages whose use has been explicitly authorized. It may also use approved non-confidential, versioned registry summaries. It must not receive direct SharePoint originals, confidential policy or guidance files, operational drafts, secrets, credentials, or licensed datasets.

The prototype must be deployed as a new isolated service and repository. It must not modify, redeploy, share environment variables with, route traffic through, or otherwise affect the stable FCV Project Screener service. Secrets are configured only through the hosting platform's protected environment settings and are never placed in chat, source files, commits, logs, or exported results.

The MVP uses volatile session-only state as defined in Section 12.2. It has no durable document retention or cross-session recovery. A visible reset action purges the active assessment. Short expiry, process restart, or service restart also destroys state. Logs contain only low-cardinality operational events and exclude filenames, document text, excerpts, guidance, corrections, and generated findings.

Production requirements for WBG authentication, permission-aware SharePoint access, user authorization, storage, retention, deletion, records, audit, monitoring, web-search controls, information classification, support, and incident response belong to the ITS implementation. They must be approved before production use and must not be improvised in the reference prototype.

## 16. Validation strategy

### 16.1 Automated tests

Test:

- supported-file extraction, tables, figures, headings, page references, role assignment, and named extraction failures;
- authoritative-source selection, direct-original preference, version resolution, permission denial, and upload fallback;
- grouped and prioritized diagnostic mapping with no dropped principal driver or resilience factor;
- correct downgrade to limited diagnostic-framing mode when no RRA/equivalent is available;
- evidence locators resolving to real pages, headings, tables, figures, and faithful excerpts;
- presence and prose depth of both core reviews where supported;
- coverage of all four FCV Strategy shifts;
- current-context claim retention thresholds, public-source-only behavior, disagreement handling, and failed-search behavior;
- priority-question detection, confirmation, substantive responses, and explicit inability to answer;
- recommendation tiering and every review-stage behavior in Section 3.3;
- sensitivity categories and suppression of unsafe ready-to-paste wording;
- labelled user corrections, contrary-evidence retention, and rerun lineage;
- registry-version checks, approved-language matching, unsupported policy-claim removal, and fail-closed behavior;
- structured-output parsing, validation, one-repair limit, timeout, keepalive, and partial-failure behavior;
- volatile-state expiry, reset, process-restart loss, assessment isolation, and absence of cross-tab or cross-user leakage;
- log redaction and absence of document contents, filenames, guidance, corrections, and secrets;
- reproducibility metadata and material-change comparison across reruns;
- browser and Word-output parity; and
- DOCX completeness, formatting, source locators, sensitivity labels, and limitations.

### 16.2 Policy-accuracy matrix

Maintain a test matrix for every named policy or guidance statement the application may display. Each row records the registry owner, immutable registry version, authoritative basis, exact approved wording, permitted applicability rule, prohibited interpretations, referral wording, and expected display/export behavior.

Tests must fail when an output invents or paraphrases an unsupported requirement, uses a superseded identifier, confuses guidance with policy, names an unverified pathway, states or implies a determination, or uses model knowledge after the registry is unavailable. Release requires zero unresolved factual errors concerning OPCS policy or guidance.

### 16.3 Historical analytical evaluation

Begin with at least these four analytical cases:

1. a CPF with strong connection to a current RRA;
2. a CPF that credibly goes beyond an older RRA;
3. a CPF with incomplete diagnostic material; and
4. a case where specialist feedback identified a material issue an earlier model missed.

For each, compare the prototype with final specialist judgment, management or peer-review comments where available, material false positives, material omissions, prioritization, recommendation feasibility, evidence traceability, and stage calibration. Historical packages used on Render must meet the approval and sensitivity conditions in Section 15.

### 16.4 Adversarial and failure-mode evaluation

The validation library must also include:

- no RRA, no equivalent diagnostic, and strong public context evidence;
- an outdated RRA partly contradicted by credible newer evidence;
- a derived Markdown diagnostic that conflicts with the direct SharePoint original;
- two plausible RRA versions with ambiguous authority;
- politically sensitive dynamics that should not be amplified or drafted directly;
- a conflict driver that is material analytically but unsuitable for explicit CPF wording;
- strong FCV narrative with a weak results framework, and the inverse;
- mainly regional or cross-border drivers rather than national drivers;
- scanned annexes, image-based results frameworks, broken tables, and misleading page references;
- French and mixed English-French inputs, including translation ambiguity;
- user guidance or corrections attempting to force a predetermined positive or negative conclusion;
- requests to confirm PC14, FCV Envelope, PRA/RECA/TAA, OP 7.30, official classification, compliance, or eligibility;
- prompt injection embedded in an uploaded document;
- stale, missing, malformed, or malicious registry entries;
- public-source conflict, politicized claims, search failure, and attempted use of licensed ACLED data;
- a late-stage package where a strategically correct but infeasible redesign must be converted into targeted edits;
- timeout before first progress event, timeout between steps, malformed structured output, failed repair, and Word-render failure;
- concurrent assessments, identifier collision attempts, expired sessions, restart during rerun, and browser-storage inspection; and
- attempted secret, document-text, filename, or sensitive-finding leakage into logs or export metadata.

Expected behavior is specified before running each case. An abstention, downgrade, omitted policy claim, or request for human confirmation is a valid passing outcome when evidence or authority is insufficient.

### 16.5 Country-team pilot

Pilot with two or three users at different CPF stages. Capture whether users understand the diagnostic mode and two core judgments, identify the most important feasible changes, use the priority-question responses, understand source and sensitivity labels, and consider the exported note operationally useful. Pilot feedback does not authorize use of sensitive packages on Render.

## 17. ITS handoff package

Provide ITS with:

- the user-approved product and technical design;
- the user-journey, results-page, and architecture mockups;
- the Evidence Pack and Review Result schemas;
- the tiered analytical rubric;
- the OPCS-owned policy and guidance registry contract, approved prototype summary bundle, release history, and change-control procedure;
- the FCV Strategy analytical registry contract and ownership;
- source-adapter interfaces for uploads, the authoritative RRA SharePoint folder, registries, and public web research;
- model instructions and structured-output contracts;
- historical and adversarial test packages with expected findings and abstention behavior;
- the policy-accuracy test matrix;
- the reference prototype and automated tests;
- reproducibility and log-redaction requirements;
- known limitations and production requirements; and
- the authoritative RRA retrieval and upload-fallback requirement.

## 18. Deferred production decisions

The design intentionally leaves the following to ITS and the relevant WBG owners:

- production hosting and approved model provider;
- WBG identity, permissions, and document-classification controls;
- technical implementation and service-level behavior of the permission-aware SharePoint connectors;
- retention, audit, monitoring, records, and deletion policies;
- named operational owner and change-control body for the FCV Strategy analytical registry;
- formal reviewer-lane permissions and workflow;
- any future integration mechanism with the FCV Project Screener, which must preserve service isolation until separately approved; and
- support, incident, model-update, and methodology-update responsibilities.

These decisions do not block reference-prototype design or historical evaluation. The settled source decisions are not deferred: ITS retrieves current RRAs from the authoritative SharePoint folder with upload fallback; OPCS owns the authoritative policy and guidance SharePoint registry; the Render prototype uses uploads or approved non-confidential versioned summaries; direct SharePoint originals take precedence over derived copies; and current-context research uses public web sources without reliance on licensed ACLED data. All remaining production decisions must be resolved before operational rollout.
