const form = document.querySelector("#review-form");
const landingView = document.querySelector("#landing-view");
const landingNotice = document.querySelector("#landing-notice");
const reviewWorkspace = document.querySelector("#review-workspace");
const progress = document.querySelector("#progress");
const progressMessage = document.querySelector("#progress-message") || progress;
const progressSteps = Array.from(document.querySelectorAll?.("[data-progress-step]") || []);
const progressStatusSlots = Array.from(document.querySelectorAll?.("[data-progress-status]") || []);
const progressCountry = document.querySelector("#progress-country") || document.createElement("p");
const elapsedTime = document.querySelector("#elapsed-time") || document.createElement("span");
const remainingTime = document.querySelector("#remaining-time") || document.createElement("span");
const guidanceCard = document.querySelector("#guidance-card") || document.createElement("p");
const results = document.querySelector("#results");
const resultTitle = document.querySelector("#result-title") || document.createElement("h2");
const resultContext = document.querySelector("#result-context") || document.createElement("p");
const summaryPanel = document.querySelector("#summary-panel") || results;
const detailedPanel = document.querySelector("#detailed-panel") || results;
const resultTabs = Array.from(document.querySelectorAll?.('[role="tab"][data-result-view]') || []);
const corrections = document.querySelector("#corrections");
const actions = document.querySelector("#actions");
const returnToIntake = document.querySelector("#return-to-intake");
const researchRecovery = document.querySelector("#research-recovery") || document.createElement("section");
const researchRecoveryHeading = document.querySelector("#research-recovery-heading") || document.createElement("h2");
const researchRecoveryMessage = document.querySelector("#research-recovery-message") || document.createElement("p");
const retryResearchButton = document.querySelector("#retry-research") || document.createElement("button");
const primaryFileInput = document.querySelector("#cpf");
const countryInput = document.querySelector("#country");
const countryDetection = document.querySelector("#country-detection");
const submitButton = document.querySelector("#submit-review");
const processDialog = document.querySelector("#process-dialog");
const openProcessDialog = document.querySelector("#open-process-dialog");
const closeProcessDialog = document.querySelector("#close-process-dialog");
const submitCorrection = document.querySelector("#submit-correction");
const resetReviewButton = document.querySelector("#reset-review");
const evidenceStatus = document.querySelector("#evidence-status") || document.createElement("aside");
const evidenceStatusLabel = document.querySelector("#evidence-status-label") || document.createElement("strong");
const evidenceStatusLimitation = document.querySelector("#evidence-status-limitation") || document.createElement("span");
let assessmentId = sessionStorage.getItem("cpf_fcv_assessment_id") || "";
let activeEventSource;
let operationEpoch = 0;
let resetPending = false;
let detectionPending = false;
let countryRequiresConfirmation = false;
let countryCorrection;
let detectionEpoch = 0;
const RESULT_RETRY_LIMIT = 3;
const RESULT_RETRY_DELAY_MS = 250;
const SOURCE_ERROR_LIMIT = 2;
const retryableResearchCodes = new Set([
  "research_provider_failed",
  "research_timeout",
  "research_malformed",
  "research_insufficient",
]);

const stageOrder = ["documents", "research", "note"];
const stageEstimates = {
  documents: [45, 120],
  research: [90, 300],
  note: [90, 240],
};
const guidanceCards = [
  "Strong FCV reviews connect context, design choices, delivery arrangements, and results.",
  "A useful recommendation identifies both the change and where it belongs in the draft.",
  "Uploaded diagnostics and independently retrieved evidence remain clearly separated.",
];

const progressLabels = {
  extract: "Reading the submitted documents",
  resolve_sources: "Selecting the submitted evidence",
  research: "Checking recent public country evidence",
  build_evidence: "Cross-checking evidence across institutional sources",
  map: "Connecting evidence to the review focus",
  review: "Drafting findings and practical options",
  validate: "Validating the review and evidence links",
  render: "Preparing the final readout",
  research_attempt: "Checking recent public country evidence",
  research_retry: "Working from available country evidence",
  research_sufficient: "Current country evidence established",
  research_reduced: "Current country evidence partially established",
  research_document_led: "Working from the submitted evidence",
  research_curated_recovery: "Cross-checking available institutional evidence",
};

const sseStageMap = {
  extract: "documents",
  resolve_sources: "documents",
  research: "research",
  research_attempt: "research",
  research_retry: "research",
  research_sufficient: "research",
  research_reduced: "research",
  research_document_led: "research",
  research_curated_recovery: "research",
  build_evidence: "note",
  map: "note",
  review: "note",
  validate: "note",
  render: "note",
};

const evidenceStatusLabels = {
  full: "Current evidence established",
  reduced: "Current evidence partially established",
  document_led: "Review based primarily on submitted documents",
};

const assessmentStatusLabels = {
  aligned: "Aligned",
  partially_aligned: "Partially aligned",
  not_evidenced: "Not evidenced",
  not_assessable: "Not assessable",
};

const strategyShiftLabels = {
  anticipate_better: "Anticipate better",
  differentiated_approach: "Differentiated approach",
  one_wbg_jobs: "One WBG approach to jobs",
  toolkit_partnerships_staffing: "Toolkit, partnerships, and staffing",
};

const gapLocusLabels = {
  cpf_narrative: "CPF narrative",
  results_framework: "Results framework",
  delivery_arrangements: "Delivery arrangements",
  monitoring_adaptation: "Monitoring and adaptation",
  downstream_operationalization: "Downstream operationalization",
};

let journeyStartedAt;
let journeyStageStartedAt;
let journeyCurrentStage = "documents";
let journeyClock;
let guidanceRotation;
let guidanceIndex = 0;

function formatElapsed(seconds) {
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${minutes}:${remainder}`;
}

function approximateMinutes(seconds) {
  return Math.max(1, Math.ceil(seconds / 60));
}

function updateJourneyClock() {
  if (!journeyStartedAt) return;
  const currentTime = performance.now();
  const elapsedSeconds = Math.max(0, (currentTime - journeyStartedAt) / 1000);
  const stageIndex = stageOrder.indexOf(journeyCurrentStage);
  const currentStageElapsed = Math.max(0, (currentTime - journeyStageStartedAt) / 1000);
  const remaining = stageOrder.slice(Math.max(0, stageIndex)).reduce(
    (range, stage, index) => {
      const [minimum, maximum] = stageEstimates[stage];
      if (index === 0) {
        return [
          range[0] + Math.max(1, minimum - currentStageElapsed),
          range[1] + Math.max(1, maximum - currentStageElapsed),
        ];
      }
      return [range[0] + minimum, range[1] + maximum];
    },
    [0, 0],
  );
  const minimumMinutes = approximateMinutes(remaining[0]);
  const maximumMinutes = Math.max(minimumMinutes, approximateMinutes(remaining[1]));
  elapsedTime.textContent = `${formatElapsed(elapsedSeconds)} elapsed`;
  remainingTime.textContent = `About ${minimumMinutes}-${maximumMinutes} minutes remaining`;
}

function rotateGuidanceCard() {
  guidanceCard.textContent = guidanceCards[guidanceIndex % guidanceCards.length];
  guidanceIndex += 1;
}

function prefersReducedMotion() {
  return typeof window.matchMedia === "function"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function startJourneyClock() {
  stopJourneyClock();
  journeyStartedAt = performance.now();
  journeyStageStartedAt = journeyStartedAt;
  journeyCurrentStage = "documents";
  guidanceIndex = 0;
  rotateGuidanceCard();
  updateJourneyClock();
  if (!prefersReducedMotion()) {
    guidanceRotation = window.setInterval?.(rotateGuidanceCard, 8000);
  }
  journeyClock = window.setInterval?.(updateJourneyClock, 1000);
}

function stopJourneyClock() {
  if (journeyClock !== undefined) window.clearInterval?.(journeyClock);
  if (guidanceRotation !== undefined) window.clearInterval?.(guidanceRotation);
  journeyClock = undefined;
  guidanceRotation = undefined;
  journeyStartedAt = undefined;
  journeyStageStartedAt = undefined;
}

function updateProgress(stage) {
  const group = sseStageMap[stage];
  if (!group) return;
  if (journeyCurrentStage !== group) {
    journeyCurrentStage = group;
    journeyStageStartedAt = performance.now();
  }
  const activeIndex = stageOrder.indexOf(group);
  for (const [index, item] of progressSteps.entries()) {
    const isComplete = index < activeIndex;
    const isActive = index === activeIndex;
    item.classList.toggle("is-complete", isComplete);
    item.classList.toggle("is-active", isActive);
    if (isActive) item.setAttribute("aria-current", "step");
    else item.removeAttribute("aria-current");
    const status = progressStatusSlots[index];
    if (status) status.textContent = isComplete ? "Complete" : isActive ? "In progress" : "Waiting";
  }
  progressMessage.textContent = progressLabels[stage] || "Building the review";
  updateJourneyClock();
}

function resetProgress() {
  stopJourneyClock();
  progressMessage.textContent = "";
  for (const [index, item] of progressSteps.entries()) {
    item.classList.remove("is-active", "is-complete");
    item.removeAttribute("aria-current");
    const status = progressStatusSlots[index];
    if (status) status.textContent = "Waiting";
  }
  elapsedTime.textContent = "0:00 elapsed";
  remainingTime.textContent = "About 4-11 minutes remaining";
}

const failureLabels = {
  model_timeout: "The model timed out. Try the review again.",
  registry_unavailable: "The approved registry is unavailable.",
  document_unreadable: "The primary document could not be read.",
  review_failed: "The review could not be completed.",
};

function showLanding(notice = "") {
  stopJourneyClock();
  landingView.hidden = false;
  reviewWorkspace.hidden = true;
  returnToIntake.hidden = true;
  researchRecovery.hidden = true;
  retryResearchButton.hidden = true;
  landingNotice.textContent = notice;
  landingNotice.hidden = !notice;
}

function showProgress() {
  stopJourneyClock();
  landingView.hidden = true;
  landingNotice.hidden = true;
  reviewWorkspace.hidden = false;
  progress.hidden = false;
  results.hidden = true;
  corrections.hidden = true;
  actions.hidden = true;
  returnToIntake.hidden = true;
  researchRecovery.hidden = true;
  retryResearchButton.hidden = true;
  progressCountry.textContent = countryInput?.value?.trim()
    ? `For ${countryInput.value.trim()}`
    : "For the selected country";
  startJourneyClock();
  updateProgress("extract");
}

function showResults() {
  stopJourneyClock();
  landingView.hidden = true;
  reviewWorkspace.hidden = false;
  progress.hidden = true;
  results.hidden = false;
  corrections.hidden = false;
  actions.hidden = false;
  returnToIntake.hidden = true;
  researchRecovery.hidden = true;
  retryResearchButton.hidden = true;
  submitCorrection.disabled = false;
}

function showRecoverableFailure(message) {
  showProgress();
  stopJourneyClock();
  resetProgress();
  progressMessage.textContent = message;
  retryResearchButton.hidden = true;
  researchRecovery.hidden = true;
  returnToIntake.hidden = false;
}

function showResearchFailure(message) {
  showProgress();
  stopJourneyClock();
  resetProgress();
  progress.hidden = true;
  researchRecoveryMessage.textContent = message;
  researchRecovery.hidden = false;
  retryResearchButton.hidden = false;
  retryResearchButton.disabled = false;
  returnToIntake.hidden = false;
  researchRecoveryHeading.focus({preventScroll: true});
}

function text(tag, value, className = "") {
  const node = document.createElement(tag);
  node.textContent = value;
  if (className) node.className = className;
  return node;
}

function updateSubmitState() {
  const hasPrimaryFile = Boolean(primaryFileInput?.files?.length);
  submitButton.disabled = detectionPending
    || countryRequiresConfirmation
    || !countryInput.value.trim()
    || !hasPrimaryFile;
}

function clearCountryCorrection() {
  countryCorrection?.remove();
  countryCorrection = undefined;
}

function showCountryCorrection(suggestedCountry) {
  const normalizedSuggestion = suggestedCountry.trim();
  const wrapper = document.createElement("div");
  wrapper.className = "country-confirmation";
  const label = document.createElement("label");
  label.textContent = normalizedSuggestion
    ? `We detected ${normalizedSuggestion}. Confirm or correct the country.`
    : "We could not identify the country. Enter it to continue.";
  countryCorrection = document.createElement("input");
  countryCorrection.type = "text";
  countryCorrection.value = normalizedSuggestion;
  countryCorrection.autocomplete = "country-name";
  countryCorrection.addEventListener("input", () => {
    countryInput.value = countryCorrection.value.trim();
    countryRequiresConfirmation = !countryInput.value;
    updateSubmitState();
  });
  label.append(countryCorrection);
  wrapper.append(label);
  if (normalizedSuggestion) {
    const acceptSuggested = document.createElement("button");
    acceptSuggested.type = "button";
    acceptSuggested.textContent = "Use detected country";
    acceptSuggested.addEventListener("click", () => {
      countryInput.value = normalizedSuggestion;
      countryRequiresConfirmation = false;
      clearCountryCorrection();
      countryDetection.textContent = `Country confirmed: ${countryInput.value}`;
      updateSubmitState();
      submitButton.focus();
    });
    wrapper.append(acceptSuggested);
  }
  countryDetection.append(wrapper);
}

async function detectCountry() {
  const file = primaryFileInput.files?.[0];
  const requestEpoch = ++detectionEpoch;
  clearCountryCorrection();
  countryInput.value = "";
  countryRequiresConfirmation = false;
  countryDetection.textContent = "";
  countryDetection.className = "country-detection";
  if (!file) {
    detectionPending = false;
    updateSubmitState();
    return;
  }

  detectionPending = true;
  countryDetection.textContent = "Identifying the country from the primary document…";
  updateSubmitState();
  try {
    const body = new FormData();
    body.append("cpf", file);
    const response = await fetch("/api/detect-country", {method: "POST", body});
    if (requestEpoch !== detectionEpoch) return;
    if (!response.ok) throw new Error("Country detection failed.");
    const detection = await response.json();
    if (requestEpoch !== detectionEpoch) return;
    countryInput.value = detection.country || "";
    if (detection.requires_confirmation) {
      countryRequiresConfirmation = true;
      showCountryCorrection(detection.country || "");
      countryDetection.firstChild?.remove();
    } else {
      countryDetection.textContent = `Country detected: ${countryInput.value}`;
    }
  } catch (_error) {
    if (requestEpoch !== detectionEpoch) return;
    countryDetection.textContent = "Country detection was unavailable. Enter the country to continue.";
    countryDetection.className = "country-detection is-error";
    countryRequiresConfirmation = true;
    showCountryCorrection("");
  } finally {
    if (requestEpoch === detectionEpoch) {
      detectionPending = false;
      updateSubmitState();
    }
  }
}

primaryFileInput.addEventListener("change", detectCountry);

if (typeof processDialog.showModal === "function") processDialog.hidden = false;

openProcessDialog.addEventListener("click", () => {
  if (typeof processDialog.showModal === "function") processDialog.showModal();
  else processDialog.hidden = false;
});

closeProcessDialog.addEventListener("click", () => {
  if (typeof processDialog.close === "function") processDialog.close();
  else processDialog.hidden = true;
});

processDialog.addEventListener("click", (event) => {
  if (event.target === processDialog && typeof processDialog.close === "function") {
    processDialog.close();
  }
});

function labelledParagraph(label, value, className) {
  const paragraph = document.createElement("p");
  paragraph.className = className;
  const lead = document.createElement("strong");
  lead.textContent = `${label}. `;
  paragraph.append(lead, document.createTextNode(value));
  return paragraph;
}

function locatorLabel(locator) {
  if (!locator) return "";
  return [
    locator.document_title,
    locator.page ? `page ${locator.page}` : "",
    locator.heading || "",
    locator.element || "",
  ].filter(Boolean).join(" | ");
}

function evidenceTypeLabel(evidenceType) {
  const labels = {
    current_context: "Current context",
    registry_language: "Registry language",
    supporting_evidence: "Supporting evidence",
  };
  if (labels[evidenceType]) return labels[evidenceType];
  if (!evidenceType) return "Supporting evidence";
  return evidenceType
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function evidenceSourceLabel(item) {
  const location = locatorLabel(item.locator);
  if (location) return location;
  const type = evidenceTypeLabel(item.evidence_type);
  if (item.source_url) return `${type} | ${item.source_url}`;
  return type;
}

function renderEvidenceGroup(result, evidenceIds) {
  const resolvedItems = (evidenceIds || [])
    .map((evidenceId) => result.evidence_by_id?.[evidenceId])
    .filter(Boolean);
  if (!resolvedItems.length) {
    return text("p", "No supporting evidence was recorded for this assessment.", "empty-state");
  }
  const details = document.createElement("details");
  details.className = "evidence-group";
  details.append(text("summary", "Evidence and document locations"));
  for (const item of resolvedItems) {
    const excerpt = item.locator && item.locator.excerpt || item.text;
    details.append(
      text("p", evidenceSourceLabel(item), "evidence-locator"),
      text("p", excerpt, "evidence-excerpt"),
    );
  }
  return details;
}

function assessmentValueLabel(value) {
  if (!value) return "Not specified";
  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function appendAssessmentField(definitions, label, value, className = "") {
  const term = document.createElement("dt");
  term.textContent = label;
  const description = document.createElement("dd");
  description.className = className;
  description.textContent = value || "Not specified";
  definitions.append(term, description);
}

function appendAssessmentStatus(definitions, status) {
  const badge = text("span", assessmentStatusLabel(status), "assessment-status status-badge");
  const description = document.createElement("dd");
  description.append(badge);
  definitions.append(text("dt", "Status"), description);
}

function appendAssessmentConfidence(definitions, confidence) {
  const description = document.createElement("dd");
  description.className = "assessment-confidence";
  description.textContent = assessmentValueLabel(confidence);
  definitions.append(text("dt", "Confidence"), description);
}

function assessmentStatusLabel(status) {
  return assessmentStatusLabels[status] || assessmentValueLabel(status);
}

function assessmentLocusLabel(locus) {
  return gapLocusLabels[locus] || assessmentValueLabel(locus);
}

function strategyShiftLabel(shift) {
  return strategyShiftLabels[shift] || assessmentValueLabel(shift);
}

function renderRraAssessments(result) {
  const section = document.createElement("section");
  section.className = "assessment-section";
  section.append(text("h3", "RRA driver-to-response assessment"));
  const assessments = result.rra_driver_assessments || [];
  const limitedFraming = result.metadata?.diagnostic_mode === "limited_framing";
  if (!assessments.length) {
    section.append(
      text(
        "p",
        limitedFraming
          ? "No current RRA was supplied; RRA alignment was not assessed."
          : "No RRA driver assessments were returned for this review.",
        "empty-state",
      ),
    );
    return section;
  }
  const list = document.createElement("ul");
  list.className = "assessment-list";
  for (const assessment of assessments) {
    const card = document.createElement("li");
    card.className = "assessment-card";
    const definitions = document.createElement("dl");
    definitions.className = "assessment-definitions";
    appendAssessmentField(definitions, "Driver", assessment.driver);
    appendAssessmentField(definitions, "CPF response", assessment.cpf_response);
    appendAssessmentField(definitions, "Delivery mechanism", assessment.delivery_mechanism);
    appendAssessmentField(definitions, "Result / indicator", assessment.result_or_indicator);
    appendAssessmentField(definitions, "Remaining gap", assessment.remaining_gap);
    appendAssessmentStatus(definitions, assessment.status);
    appendAssessmentConfidence(definitions, assessment.confidence);
    appendAssessmentField(definitions, "Gap locus", assessmentLocusLabel(assessment.gap_locus));
    card.append(definitions, renderEvidenceGroup(result, assessment.evidence_ids));
    list.append(card);
  }
  section.append(list);
  return section;
}

function renderStrategyAssessments(result) {
  const section = document.createElement("section");
  section.className = "assessment-section";
  section.append(text("h3", "2026-2030 FCV Strategy alignment"));
  const assessments = result.fcv_strategy_assessments || [];
  if (!assessments.length) {
    section.append(
      text("p", "No FCV Strategy alignment assessments were returned for this review.", "empty-state"),
    );
    return section;
  }
  const list = document.createElement("ul");
  list.className = "assessment-list";
  for (const assessment of assessments) {
    const card = document.createElement("li");
    card.className = "assessment-card";
    const definitions = document.createElement("dl");
    definitions.className = "assessment-definitions";
    appendAssessmentField(definitions, "Strategic shift", strategyShiftLabel(assessment.strategic_shift));
    appendAssessmentField(definitions, "Assessment", assessment.assessment);
    appendAssessmentStatus(definitions, assessment.status);
    appendAssessmentConfidence(definitions, assessment.confidence);
    appendAssessmentField(definitions, "Gap locus", assessmentLocusLabel(assessment.gap_locus));
    card.append(definitions, renderEvidenceGroup(result, assessment.evidence_ids));
    list.append(card);
  }
  section.append(list);
  return section;
}

function priorityAreaAnchorIds(result) {
  return new Map(
    result.priority_areas.map((_, index) => [`${index}`, `cpf-priority-area-${index + 1}`]),
  );
}

function renderRevisionSummary(result, anchorIds) {
  if (!result.revision_summary.length) {
    return text("p", "No revision summary was returned for this review.", "empty-state");
  }
  const summary = document.createElement("ol");
  for (const item of result.revision_summary) {
    const link = document.createElement("a");
    const priorityAreaIndex = result.priority_areas.findIndex(
      (area) => area.priority_area_id === item.priority_area_id,
    );
    const anchorId = anchorIds.get(`${priorityAreaIndex}`);
    link.href = anchorId ? `#${anchorId}` : "#";
    link.textContent = item.title;
    if (anchorId) {
      link.addEventListener("click", (event) => {
        event?.preventDefault();
        setResultView("detailed");
        document.getElementById(anchorId)?.focus();
      });
    }
    const row = document.createElement("li");
    row.append(link);
    summary.append(row);
  }
  return summary;
}

function renderPriorityAreas(result, anchorIds) {
  const fragment = document.createDocumentFragment?.() || document.createElement("div");
  fragment.append(text("h2", "Priority areas for strengthening"));
  for (const [index, area] of result.priority_areas.entries()) {
    const section = document.createElement("section");
    section.id = anchorIds.get(`${index}`);
    section.tabIndex = -1;
    section.className = "priority-area";
    section.append(
      text("h3", area.heading),
      text("p", area.assessment),
      text("p", area.why_it_matters),
      labelledParagraph("Recommended action", area.recommended_action, "recommended-action"),
      labelledParagraph("Target", locatorLabel(area.target_locator), "target-location"),
    );
    if (area.comment_reference) {
      section.append(
        labelledParagraph("Comment addressed", area.comment_reference, "comment-reference"),
      );
    }
    section.append(renderEvidenceGroup(result, area.evidence_ids));
    fragment.append(section);
  }
  if (!result.priority_areas.length) {
    fragment.append(text("p", "No priority areas were returned for this review.", "empty-state"));
  }
  return fragment;
}

function renderCoverage(result) {
  const fragment = document.createDocumentFragment?.() || document.createElement("div");
  fragment.append(text("h2", "Limitations and document coverage"));
  if (result.limitations.length) {
    const list = document.createElement("ul");
    for (const limitation of result.limitations) list.append(text("li", limitation));
    fragment.append(list);
  }
  const coverage = result.document_coverage;
  if (coverage) {
    fragment.append(
      labelledParagraph("Primary document", coverage.primary_document, "coverage-primary"),
      labelledParagraph("Package documents", coverage.package_documents.join(", ") || "None supplied", "coverage-package"),
      labelledParagraph("Context documents", coverage.context_documents.join(", ") || "None supplied", "coverage-context"),
      labelledParagraph("Coverage note", coverage.coverage_note, "coverage-note"),
    );
  }
  return fragment;
}

function renderFiveMinuteReadout(result) {
  const anchorIds = priorityAreaAnchorIds(result);
  const fragment = document.createDocumentFragment?.() || document.createElement("div");
  fragment.append(
    text("p", "Five-minute readout", "read-time"),
    text("h2", "Overall assessment"),
    text("p", result.overall_read, "overall-read"),
    text("h2", "How the draft responds to the RRA, current FCV dynamics, and the FCV Strategy"),
    text("p", result.alignment_readout, "alignment-readout"),
    text("h2", "Priority measures to strengthen the CPF / CEN"),
    renderRevisionSummary(result, anchorIds),
  );
  return fragment;
}

function renderDetailedAnalysis(result) {
  const anchorIds = priorityAreaAnchorIds(result);
  const fragment = document.createDocumentFragment?.() || document.createElement("div");
  fragment.append(text("h2", "Overall assessment"));
  fragment.append(text("p", result.overall_read, "overall-read"));
  fragment.append(text("h2", "How the draft responds to the RRA, current FCV dynamics, and the FCV Strategy"));
  fragment.append(text("p", result.alignment_readout, "alignment-readout"));
  fragment.append(renderRraAssessments(result));
  fragment.append(renderStrategyAssessments(result));
  fragment.append(renderPriorityAreas(result, anchorIds));
  fragment.append(renderCoverage(result));
  return fragment;
}

function inferDocumentType(primaryDocumentName) {
  const name = primaryDocumentName || "";
  const hasCen = /(^|[^a-z0-9])cen([^a-z0-9]|$)/i.test(name);
  const hasCpf = /(^|[^a-z0-9])cpf([^a-z0-9]|$)/i.test(name);
  if (hasCen !== hasCpf) return hasCen ? "CEN" : "CPF";
  return "CPF / CEN";
}

function setResultView(view) {
  const panels = {summary: summaryPanel, detailed: detailedPanel};
  for (const tab of resultTabs) {
    const isSelected = tab.dataset.resultView === view;
    const panel = panels[tab.dataset.resultView];
    tab.setAttribute("aria-selected", String(isSelected));
    tab.tabIndex = isSelected ? 0 : -1;
    tab.classList.toggle("is-active", isSelected);
    panel.hidden = !isSelected;
  }
}

function handleResultTabKeydown(event) {
  const currentIndex = resultTabs.indexOf(event.currentTarget);
  let nextIndex;
  switch (event.key) {
    case "ArrowLeft":
      nextIndex = (currentIndex - 1 + resultTabs.length) % resultTabs.length;
      break;
    case "ArrowRight":
      nextIndex = (currentIndex + 1) % resultTabs.length;
      break;
    case "Home":
      nextIndex = 0;
      break;
    case "End":
      nextIndex = resultTabs.length - 1;
      break;
    default:
      return;
  }
  event.preventDefault();
  const nextTab = resultTabs[nextIndex];
  setResultView(nextTab.dataset.resultView);
  nextTab.focus();
}

for (const tab of resultTabs) {
  tab.addEventListener("click", () => setResultView(tab.dataset.resultView));
  tab.addEventListener("keydown", handleResultTabKeydown);
}

function renderEvidenceStatus(result) {
  const label = evidenceStatusLabels[result.metadata?.current_evidence_tier];
  const limitation = result.metadata?.current_evidence_limitation;
  evidenceStatusLabel.textContent = label || "";
  evidenceStatusLimitation.textContent = limitation || "";
  evidenceStatusLimitation.hidden = !limitation;
  evidenceStatus.hidden = !label;
}

function renderResult(result) {
  if (summaryPanel === detailedPanel) {
    results.replaceChildren(renderFiveMinuteReadout(result), renderDetailedAnalysis(result));
  } else {
    summaryPanel.replaceChildren(renderFiveMinuteReadout(result));
    detailedPanel.replaceChildren(renderDetailedAnalysis(result));
  }
  const country = countryInput.value.trim();
  const documentType = inferDocumentType(result.document_coverage.primary_document);
  const reviewStage = result.metadata?.review_stage;
  const stage = reviewStage ? ` · ${reviewStage.replaceAll("_", " ")}` : "";
  resultTitle.textContent = `${country} ${documentType} FCV review`;
  resultContext.textContent = `${result.document_coverage.primary_document}${stage}`;
  renderEvidenceStatus(result);
  setResultView("summary");
  showResults();
  resultTitle.focus({preventScroll: true});
}

function isActiveSource(source) {
  return activeEventSource === source;
}

function isCurrentOperation(operation) {
  return operation === operationEpoch;
}

function closeActiveSource(source) {
  if (!isActiveSource(source)) return false;
  source.close();
  activeEventSource = undefined;
  return true;
}

function delay(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

async function loadResult(resultUrl, operation, attempt = 1) {
  const response = await fetch(resultUrl);
  if (!isCurrentOperation(operation)) return null;
  if (response.status === 202) {
    if (attempt >= RESULT_RETRY_LIMIT) throw new Error("Review result is unavailable.");
    await delay(RESULT_RETRY_DELAY_MS);
    if (!isCurrentOperation(operation)) return null;
    return loadResult(resultUrl, operation, attempt + 1);
  }
  if (!response.ok) throw new Error("Review result is unavailable.");
  const result = await response.json();
  return isCurrentOperation(operation) ? result : null;
}

function watchEvents(eventUrl, resultUrl, operation = operationEpoch) {
  activeEventSource?.close();
  const source = new EventSource(eventUrl);
  activeEventSource = source;
  let sourceErrors = 0;
  source.addEventListener("step_start", (event) => {
    if (!isCurrentOperation(operation) || !isActiveSource(source)) return;
    const step = JSON.parse(event.data).step;
    if (typeof step === "string" && sseStageMap[step]) updateProgress(step);
  });
  for (const eventName of ["research_attempt", "research_retry", "research_sufficient"]) {
    source.addEventListener(eventName, () => {
      if (!isCurrentOperation(operation) || !isActiveSource(source)) return;
      updateProgress(eventName);
    });
  }
  for (const eventName of ["research_reduced", "research_document_led", "research_curated_recovery"]) {
    source.addEventListener(eventName, () => {
      if (!isCurrentOperation(operation) || !isActiveSource(source)) return;
      updateProgress(eventName);
    });
  }
  source.addEventListener("run_complete", async () => {
    if (!isCurrentOperation(operation) || !closeActiveSource(source)) return;
    progressMessage.textContent = "Review complete";
    try {
      const result = await loadResult(resultUrl, operation);
      if (!isCurrentOperation(operation) || !result) return;
      renderResult(result);
    } catch (_error) {
      if (isCurrentOperation(operation)) {
        showRecoverableFailure("The review result is unavailable. Return to intake and try again.");
      }
    }
  });
  source.addEventListener("run_failed", (event) => {
    if (!isCurrentOperation(operation) || !closeActiveSource(source)) return;
    const data = JSON.parse(event.data);
    const label = failureLabels[data.error] || failureLabels.review_failed;
    if (retryableResearchCodes.has(data.error)) {
      showResearchFailure(
        "The available research routes could not establish a sufficient current-country evidence baseline. Retry research using the uploaded package still held in this temporary session.",
      );
    } else {
      showRecoverableFailure(`Review stopped: ${label}`);
    }
  });
  source.addEventListener("expired", () => {
    if (!isCurrentOperation(operation) || !closeActiveSource(source)) return;
    showRecoverableFailure("This volatile review session expired. Upload again.");
  });
  source.onerror = () => {
    if (!isCurrentOperation(operation) || !isActiveSource(source)) return;
    sourceErrors += 1;
    if (sourceErrors >= SOURCE_ERROR_LIMIT && closeActiveSource(source)) {
      showRecoverableFailure("The review connection was interrupted. Return to intake and try again.");
    }
  };
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (submitButton.disabled || detectionPending || countryRequiresConfirmation) {
    countryCorrection?.focus();
    return;
  }
  resetPending = false;
  const operation = ++operationEpoch;
  showProgress();
  progressMessage.textContent = "Uploading and validating";
  try {
    const response = await fetch("/api/reviews", {
      method: "POST",
      body: new FormData(form),
    });
    if (!isCurrentOperation(operation)) return;
    if (!response.ok) {
      showRecoverableFailure("The review could not start. Return to intake and try again.");
      return;
    }
    const created = await response.json();
    if (!isCurrentOperation(operation)) return;
    assessmentId = created.assessment_id;
    sessionStorage.setItem("cpf_fcv_assessment_id", assessmentId);
    watchEvents(created.event_url, created.result_url, operation);
  } catch (_error) {
    if (!isCurrentOperation(operation)) return;
    showRecoverableFailure("The review could not start. Return to intake and try again.");
  }
});

async function retryResearch() {
  if (!assessmentId || resetPending || retryResearchButton.disabled) return;
  const operation = ++operationEpoch;
  retryResearchButton.disabled = true;
  researchRecoveryMessage.textContent = "Restarting current-country research using the uploaded package held in this temporary session.";
  try {
    const response = await fetch(`/api/reviews/${assessmentId}/retry-research`, {
      method: "POST",
    });
    if (!isCurrentOperation(operation)) return;
    if (!response.ok) {
      if (response.status === 410) {
        showRecoverableFailure("This volatile review session expired. Upload again.");
      } else {
        showResearchFailure("Research could not restart. Retry research, or start a new review.");
      }
      return;
    }
    const retry = await response.json();
    if (!isCurrentOperation(operation)) return;
    showProgress();
    progressMessage.textContent = "Restarting the review with current-country research";
    watchEvents(retry.event_url, retry.result_url, operation);
  } catch (_error) {
    if (!isCurrentOperation(operation)) return;
    showResearchFailure("Research could not restart. Retry research, or start a new review.");
  }
}

retryResearchButton.addEventListener("click", retryResearch);

submitCorrection.addEventListener("click", async () => {
  const correction = document.querySelector("#correction-text").value.trim();
  if (!correction || !assessmentId || resetPending || submitCorrection.disabled) return;
  const operation = ++operationEpoch;
  submitCorrection.disabled = true;
  try {
    const response = await fetch(`/api/reviews/${assessmentId}/corrections`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text: correction}),
    });
    if (!isCurrentOperation(operation)) return;
    if (!response.ok) {
      showRecoverableFailure("The correction could not be applied. Return to intake and try again.");
      return;
    }
    const child = await response.json();
    if (!isCurrentOperation(operation)) return;
    assessmentId = child.assessment_id;
    sessionStorage.setItem("cpf_fcv_assessment_id", assessmentId);
    showProgress();
    progressMessage.textContent = "User-provided correction saved; rerun requested.";
    watchEvents(child.event_url, child.result_url, operation);
  } catch (_error) {
    if (!isCurrentOperation(operation)) return;
    showRecoverableFailure("The correction could not be applied. Return to intake and try again.");
  } finally {
    if (!corrections.hidden) submitCorrection.disabled = false;
  }
});

document.querySelector("#export-docx").addEventListener("click", () => {
  if (assessmentId) window.location.assign(`/api/reviews/${assessmentId}/export.docx`);
});

async function resetReview() {
  if (resetPending) return;
  const resetEpoch = ++operationEpoch;
  const assessmentToPurge = assessmentId;
  resetPending = true;
  activeEventSource?.close();
  activeEventSource = undefined;
  sessionStorage.removeItem("cpf_fcv_assessment_id");
  assessmentId = "";
  if (summaryPanel === detailedPanel) {
    results.replaceChildren();
  } else {
    summaryPanel.replaceChildren();
    detailedPanel.replaceChildren();
  }
  resultContext.textContent = "";
  resultTitle.textContent = "CPF / CEN FCV review";
  evidenceStatusLabel.textContent = "";
  evidenceStatusLimitation.textContent = "";
  evidenceStatus.hidden = true;
  stopJourneyClock();
  resetProgress();
  form.reset();
  clearCountryCorrection();
  countryInput.value = "";
  countryDetection.textContent = "";
  countryDetection.className = "country-detection";
  detectionPending = false;
  countryRequiresConfirmation = false;
  updateSubmitState();
  document.querySelector("#correction-text").value = "";
  corrections.hidden = true;
  actions.hidden = true;
  submitCorrection.disabled = true;
  showLanding();
  let purgeConfirmed = !assessmentToPurge;
  try {
    if (assessmentToPurge) {
      const response = await fetch(`/api/reviews/${assessmentToPurge}`, {method: "DELETE"});
      purgeConfirmed = response.ok;
    }
  } catch (_error) {
    purgeConfirmed = false;
  } finally {
    if (isCurrentOperation(resetEpoch)) {
      const notice = purgeConfirmed
        ? ""
        : "The review was cleared from this browser, but server purge was not confirmed. Any remaining volatile state will expire.";
      showLanding(notice);
    }
    resetPending = false;
  }
}

resetReviewButton.addEventListener("click", resetReview);
returnToIntake.addEventListener("click", resetReview);

if (window.__CPF_FCV_REVIEWER_TEST__) {
  window.__cpfFcvReviewerTestHooks = {
    getActiveSource: () => activeEventSource,
    setAssessmentId: (value) => { assessmentId = value; },
    watchEvents,
  };
}
