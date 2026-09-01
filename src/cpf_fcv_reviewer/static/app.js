const form = document.querySelector("#review-form");
const landingView = document.querySelector("#landing-view");
const landingNotice = document.querySelector("#landing-notice");
const reviewWorkspace = document.querySelector("#review-workspace");
const progress = document.querySelector("#progress");
const progressTitle = document.querySelector("#progress-title") || document.createElement("h2");
const progressFill = document.querySelector("#progress-fill") || document.createElement("span");
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
let downloadError;
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
const progressPercent = {documents: 18, research: 58, note: 88};
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
const COUNTRY_DETECTION_MAX_BYTES = 2 * 1024 * 1024;

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

function formatRemainingTime(minimumMinutes, maximumMinutes) {
  if (minimumMinutes === 1 && maximumMinutes === 1) {
    return "About 1 minute remaining";
  }
  return `About ${minimumMinutes}-${maximumMinutes} minutes remaining`;
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
  remainingTime.textContent = formatRemainingTime(minimumMinutes, maximumMinutes);
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

function setProgressStages(activeIndex, complete = false) {
  for (const [index, item] of progressSteps.entries()) {
    const isComplete = complete || index < activeIndex;
    const isActive = !complete && index === activeIndex;
    item.classList.toggle("is-complete", isComplete);
    item.classList.toggle("is-active", isActive);
    if (isActive) item.setAttribute("aria-current", "step");
    else item.removeAttribute("aria-current");
    const status = progressStatusSlots[index];
    if (status) status.textContent = isComplete ? "Complete" : isActive ? "In progress" : "Waiting";
  }
}

function updateProgress(stage) {
  const group = sseStageMap[stage];
  if (!group) return;
  if (journeyCurrentStage !== group) {
    journeyCurrentStage = group;
    journeyStageStartedAt = performance.now();
  }
  const activeIndex = stageOrder.indexOf(group);
  setProgressStages(activeIndex);
  if (progressFill.style) progressFill.style.width = `${progressPercent[group] || 0}%`;
  progressMessage.textContent = progressLabels[stage] || "Building the review";
  updateJourneyClock();
}

function resetProgress() {
  stopJourneyClock();
  progressMessage.textContent = "";
  if (progressFill.style) progressFill.style.width = "0%";
  setProgressStages(-1);
  elapsedTime.textContent = "0:00 elapsed";
  remainingTime.textContent = "About 4-11 minutes remaining";
}

const failureLabels = {
  model_timeout: "The model timed out. Try the review again.",
  registry_unavailable: "The approved registry is unavailable.",
  document_unreadable: "The primary document could not be read.",
  diagnostic_coverage_unavailable: "The uploaded diagnostic could not be assessed in full. Upload a shorter or text-searchable version, or start a new review without it.",
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
  progressTitle.focus({preventScroll: true});
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

  if (file.size > COUNTRY_DETECTION_MAX_BYTES) {
    countryDetection.textContent = "This primary document exceeds the 2 MiB automatic detector budget. Enter the country manually to continue.";
    countryRequiresConfirmation = true;
    showCountryCorrection("");
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

function splitNarrativeIntoChunks(value) {
  const source = String(value || "").trim();
  if (!source) return [];
  let sentences = [];
  if (typeof Intl !== "undefined" && Intl.Segmenter) {
    const segmenter = new Intl.Segmenter(undefined, {granularity: "sentence"});
    sentences = Array.from(segmenter.segment(source), ({segment}) => segment.trim()).filter(Boolean);
  }
  if (!sentences.length) {
    sentences = (source.match(/[^.!?]+(?:[.!?]+(?=\s|$)|$)/g) || [source])
      .map((sentence) => sentence.trim())
      .filter(Boolean);
  }
  const chunks = [];
  for (let index = 0; index < sentences.length; index += 4) {
    chunks.push(sentences.slice(index, index + 4));
  }
  return chunks;
}

function renderNarrative(value, className = "") {
  const fragment = document.createDocumentFragment?.() || document.createElement("div");
  for (const sentences of splitNarrativeIntoChunks(value)) {
    const paragraph = document.createElement("p");
    paragraph.className = className ? "narrative-chunk " + className : "narrative-chunk";
    const activeSentence = text("strong", sentences[0]);
    const remainingSentences = sentences.slice(1).join(" ");
    paragraph.append(
      activeSentence,
      document.createTextNode(remainingSentences ? " " + remainingSentences : ""),
    );
    fragment.append(paragraph);
  }
  return fragment;
}

function renderDisclosure(label, className, content) {
  const details = document.createElement("details");
  details.className = className;
  details.append(text("summary", label));
  if (content) details.append(content);
  return details;
}

function renderReadoutPanel(title, value, className) {
  const panel = document.createElement("section");
  panel.className = "readout-panel " + className;
  panel.append(text("h2", title), renderNarrative(value, "readout-prose"));
  return panel;
}

function firstNarrativeSentence(value) {
  return splitNarrativeIntoChunks(value)[0]?.[0] || String(value || "").trim();
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
  return renderTraceability(result, evidenceIds);
}

function renderTraceability(result) {
  return renderTraceabilityForEvidence(result, arguments[1]);
}

function renderTraceabilityForEvidence(result, evidenceIds) {
  const resolvedItems = (evidenceIds || [])
    .map((evidenceId) => result.evidence_by_id?.[evidenceId])
    .filter(Boolean);
  if (!resolvedItems.length) {
    return text("p", "No supporting evidence was recorded for this assessment.", "empty-state");
  }
  const summary = text("summary", "Evidence and document locations");
  const traceabilityLabel = text("summary", "Traceability");
  summary.textContent = traceabilityLabel.textContent;
  summary.setAttribute?.("aria-label", "Traceability - Evidence and document locations");
  const details = renderDisclosure("Traceability", "evidence-group traceability-panel");
  details.replaceChildren(summary, text("p", "Evidence and document locations", "traceability-caption"));
  for (const item of resolvedItems) {
    const excerpt = item.locator && item.locator.excerpt || item.text;
    details.append(
      text("p", evidenceSourceLabel(item), "evidence-locator"),
      text("p", excerpt, "evidence-excerpt"),
    );
  }
  return details;
}

function renderEvidenceStatusDisclosure(result) {
  const content = document.createDocumentFragment?.() || document.createElement("div");
  const label = evidenceStatusLabels[result.metadata?.current_evidence_tier]
    || "Evidence status is not available.";
  content.append(text("p", label, "evidence-status-label"));
  const limitation = result.metadata?.current_evidence_limitation;
  if (limitation) content.append(renderNarrative(limitation, "evidence-status-limitation"));
  const details = document.createElement("details");
  details.className = "evidence-status-panel";
  details.append(text("summary", "Evidence status"), content);
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
  description.append(renderNarrative(value || "Not specified", "assessment-narrative"));
  definitions.append(term, description);
}

function appendAssessmentStatus(definitions, status) {
  const badge = text(
    "span",
    assessmentStatusLabel(status),
    `assessment-status status-badge status-${status.replaceAll("_", "-")}`,
  );
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

function appendAssessmentStanding(definitions, status, confidence) {
  const normalizedStatus = status || "not_assessable";
  const badge = text(
    "span",
    assessmentStatusLabel(normalizedStatus) + " - " + assessmentValueLabel(confidence) + " confidence",
    "assessment-status status-badge status-" + normalizedStatus.replaceAll("_", "-"),
  );
  const description = document.createElement("dd");
  description.className = "assessment-standing";
  description.append(badge);
  definitions.append(text("dt", "Status and confidence"), description);
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
    appendAssessmentField(definitions, "Remaining gap", assessment.remaining_gap);
    appendAssessmentStanding(definitions, assessment.status, assessment.confidence);
    card.append(definitions);
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
    appendAssessmentStanding(definitions, assessment.status, assessment.confidence);
    card.append(definitions);
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
  const summary = document.createElement("div");
  summary.className = "priority-summary-grid";
  const summaryItems = result.revision_summary
    .filter((item) => result.priority_areas.some((area) => area.priority_area_id === item.priority_area_id))
    .slice(0, 3);
  if (!summaryItems.length) {
    summary.append(text("p", "No revision summary was returned for this review.", "empty-state"));
    return summary;
  }
  for (const item of summaryItems) {
    const priorityAreaIndex = result.priority_areas.findIndex(
      (area) => area.priority_area_id === item.priority_area_id,
    );
    const area = result.priority_areas[priorityAreaIndex];
    const anchorId = anchorIds.get(String(priorityAreaIndex));
    const card = document.createElement("section");
    card.className = "priority-area";
    card.append(
      text("h3", item.title),
      renderNarrative(firstNarrativeSentence(area?.assessment), "priority-assessment"),
      labelledNarrative(
        "Recommended response",
        firstNarrativeSentence(area?.recommended_action),
        "recommended-action",
      ),
    );
    const link = document.createElement("a");
    link.href = anchorId ? "#" + anchorId : "#";
    link.textContent = "View detailed recommendation";
    link.setAttribute?.("aria-label", "View detailed recommendation: " + item.title);
    if (anchorId) {
      link.addEventListener("click", (event) => {
        event?.preventDefault();
        setResultView("detailed");
        document.getElementById(anchorId)?.focus();
      });
    }
    card.append(link);
    summary.append(card);
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
      renderNarrative(area.assessment, "priority-assessment"),
      renderNarrative(area.why_it_matters, "priority-why-it-matters"),
      labelledNarrative("Recommended action", area.recommended_action, "recommended-action"),
      labelledParagraph("Target", locatorLabel(area.target_locator), "target-location"),
    );
    if (area.comment_reference) {
      section.append(
        labelledParagraph("Comment addressed", area.comment_reference, "comment-reference"),
      );
    }
    fragment.append(section);
  }
  if (!result.priority_areas.length) {
    fragment.append(text("p", "No priority areas were returned for this review.", "empty-state"));
  }
  return fragment;
}

function labelledNarrative(label, value, className) {
  const wrapper = document.createElement("div");
  wrapper.className = className;
  wrapper.append(text("strong", label + "."), renderNarrative(value));
  return wrapper;
}

function renderCoverage(result) {
  return renderCoverageView(result, arguments[1]);
}

function renderCoverageView(result, collapsible = true) {
  const content = document.createDocumentFragment?.() || document.createElement("div");
  if (collapsible) content.append(text("h3", "Limitations and document coverage"));
  else content.append(text("h2", "Limitations and document coverage"));
  const limitations = result.limitations || [];
  if (limitations.length) {
    const list = document.createElement("ul");
    for (const limitation of limitations) {
      const item = document.createElement("li");
      item.append(renderNarrative(limitation));
      list.append(item);
    }
    content.append(list);
  }
  const coverage = result.document_coverage;
  if (coverage) {
    content.append(
      labelledParagraph("Primary document", coverage.primary_document, "coverage-primary"),
      labelledParagraph("Package documents", coverage.package_documents.join(", ") || "None supplied", "coverage-package"),
      labelledParagraph("Context documents", coverage.context_documents.join(", ") || "None supplied", "coverage-context"),
      labelledNarrative("Coverage note", coverage.coverage_note, "coverage-note"),
    );
  }
  if (!collapsible) return content;
  const details = document.createElement("details");
  details.className = "coverage-panel";
  details.append(text("summary", "Coverage and limitations"), content);
  return details;
}

function renderFiveMinuteReadout(result) {
  const anchorIds = priorityAreaAnchorIds(result);
  const fragment = document.createDocumentFragment?.() || document.createElement("div");
  fragment.append(
    text("p", "Five-minute readout", "read-time"),
    text("h2", "Overall assessment"),
    renderNarrative(result.overall_read, "overall-read"),
    renderReadoutPanel(
      "How well does the CPF respond to the RRA and current FCV dynamics?",
      result.alignment_readout,
      "readout-panel-rra",
    ),
    renderReadoutPanel(
      "How does the CPF contribute to current FCV Strategy priorities?",
      result.strategy_readout,
      "readout-panel-strategy",
    ),
    text("h2", "Priority measures to strengthen the CPF / CEN"),
    renderRevisionSummary(result, anchorIds),
  );
  return fragment;
}
function renderBasisAndLimitations(result) {
  const limitations = [...(result.limitations || [])];
  const currentLimitation = result.metadata?.current_evidence_limitation;
  if (currentLimitation && !limitations.includes(currentLimitation)) limitations.push(currentLimitation);
  if (!limitations.length) limitations.push("Findings are advisory and bounded by the material available for review.");
  const list = document.createElement("ul");
  for (const limitation of limitations) {
    const item = document.createElement("li");
    item.append(renderNarrative(limitation));
    list.append(item);
  }
  return renderDisclosure("Basis and important limitations", "basis-limitations-panel", list);
}

function renderDetailedAnalysis(result) {
  return renderDetailedAnalysisView(result, true);
}

function renderDetailedAnalysisView(result, includeDisclosurePanels = true) {
  const anchorIds = priorityAreaAnchorIds(result);
  const fragment = document.createDocumentFragment?.() || document.createElement("div");
  fragment.append(
    text("h2", "Overall assessment"),
    renderNarrative(result.overall_read, "overall-read"),
    renderReadoutPanel(
      "How well does the CPF respond to the RRA and current FCV dynamics?",
      result.alignment_readout,
      "readout-panel-rra",
    ),
    renderRraAssessments(result),
    renderReadoutPanel(
      "How does the CPF contribute to current FCV Strategy priorities?",
      result.strategy_readout,
      "readout-panel-strategy",
    ),
    renderStrategyAssessments(result),
    renderPriorityAreas(result, anchorIds),
  );
  if (includeDisclosurePanels) fragment.append(renderBasisAndLimitations(result));
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
    results.replaceChildren(renderFiveMinuteReadout(result), renderDetailedAnalysisView(result, true));
  } else {
    summaryPanel.replaceChildren(renderFiveMinuteReadout(result));
    detailedPanel.replaceChildren(renderDetailedAnalysisView(result, true));
  }
  const country = countryInput.value.trim();
  const documentType = inferDocumentType(result.document_coverage.primary_document);
  const reviewStage = result.metadata?.review_stage;
  const stage = reviewStage ? " - " + reviewStage.replaceAll("_", " ") : "";
  resultTitle.textContent = `${country} ${documentType} FCV review`;
  resultContext.textContent = `${result.document_coverage.primary_document}${stage}`;
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
    stopJourneyClock();
    setProgressStages(stageOrder.length, true);
    if (progressFill.style) progressFill.style.width = "100%";
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

function clearDownloadError() {
  if (!downloadError) return;
  downloadError.textContent = "";
  downloadError.hidden = true;
}

function showDownloadError(message) {
  if (!downloadError) {
    downloadError = document.createElement("p");
    downloadError.className = "download-error";
    downloadError.setAttribute("role", "status");
    downloadError.setAttribute("aria-live", "polite");
    actions.append(downloadError);
  }
  downloadError.textContent = message;
  downloadError.hidden = false;
}

function downloadErrorMessage(status) {
  if (status === 409) {
    return "The detailed note is not ready for download yet. The results page remains available; try again in a moment.";
  }
  if (status === 410) {
    return "This review session has expired, so the detailed note cannot be downloaded. The results page remains available; start a new review to try again.";
  }
  if (status === 500) {
    return "The detailed note could not be generated for download. The results page remains available; try again.";
  }
  return "The detailed note could not be downloaded. The results page remains available; try again.";
}

async function downloadDocx() {
  if (!assessmentId) return;
  clearDownloadError();
  try {
    const response = await fetch(`/api/reviews/${assessmentId}/export.docx`);
    if (!response.ok) {
      showDownloadError(downloadErrorMessage(response.status));
      return;
    }
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const downloadLink = document.createElement("a");
    downloadLink.href = objectUrl;
    downloadLink.download = "CPF-FCV-Review.docx";
    document.body.append(downloadLink);
    try {
      downloadLink.click();
    } finally {
      downloadLink.remove();
      URL.revokeObjectURL(objectUrl);
    }
  } catch (_error) {
    showDownloadError(downloadErrorMessage(0));
  }
}

document.querySelector("#export-docx").addEventListener("click", downloadDocx);

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
    showProgress,
    watchEvents,
    updateProgress,
    resetProgress,
    appendAssessmentStatus,
    appendAssessmentStanding,
    renderFiveMinuteReadout,
    renderDetailedAnalysis,
    splitNarrativeIntoChunks,
  };
}
