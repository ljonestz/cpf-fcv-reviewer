const form = document.querySelector("#review-form");
const landingView = document.querySelector("#landing-view");
const landingNotice = document.querySelector("#landing-notice");
const reviewWorkspace = document.querySelector("#review-workspace");
const progress = document.querySelector("#progress");
const results = document.querySelector("#results");
const corrections = document.querySelector("#corrections");
const actions = document.querySelector("#actions");
const returnToIntake = document.querySelector("#return-to-intake");
const primaryFileInput = document.querySelector("#cpf");
const countryInput = document.querySelector("#country");
const countryDetection = document.querySelector("#country-detection");
const submitButton = document.querySelector("#submit-review");
const processDialog = document.querySelector("#process-dialog");
const openProcessDialog = document.querySelector("#open-process-dialog");
const closeProcessDialog = document.querySelector("#close-process-dialog");
const submitCorrection = document.querySelector("#submit-correction");
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

const failureLabels = {
  model_timeout: "The model timed out. Try the review again.",
  registry_unavailable: "The approved registry is unavailable.",
  document_unreadable: "The primary document could not be read.",
  review_failed: "The review could not be completed.",
};

function showLanding(notice = "") {
  landingView.hidden = false;
  reviewWorkspace.hidden = true;
  returnToIntake.hidden = true;
  landingNotice.textContent = notice;
  landingNotice.hidden = !notice;
}

function showProgress() {
  landingView.hidden = true;
  landingNotice.hidden = true;
  reviewWorkspace.hidden = false;
  progress.hidden = false;
  results.hidden = true;
  corrections.hidden = true;
  actions.hidden = true;
  returnToIntake.hidden = true;
}

function showResults() {
  landingView.hidden = true;
  reviewWorkspace.hidden = false;
  progress.hidden = true;
  results.hidden = false;
  corrections.hidden = false;
  actions.hidden = false;
  returnToIntake.hidden = true;
  submitCorrection.disabled = false;
}

function showRecoverableFailure(message) {
  showProgress();
  progress.textContent = message;
  returnToIntake.hidden = false;
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
  return [
    locator.document_title,
    locator.page ? `page ${locator.page}` : "",
    locator.heading || "",
    locator.element || "",
  ].filter(Boolean).join(" | ");
}

function renderEvidenceGroup(result, evidenceIds) {
  const details = document.createElement("details");
  details.className = "evidence-group";
  details.append(text("summary", "Evidence and document locations"));
  for (const evidenceId of evidenceIds) {
    const item = result.evidence_by_id?.[evidenceId];
    if (!item) continue;
    const excerpt = item.locator && item.locator.excerpt || item.text;
    details.append(
      text("p", locatorLabel(item.locator), "evidence-locator"),
      text("p", excerpt, "evidence-excerpt"),
    );
  }
  return details;
}

function renderResult(result) {
  results.replaceChildren();
  results.append(text("h2", "Overall read"), text("p", result.overall_read, "overall-read"));

  const summary = document.createElement("ol");
  for (const item of result.revision_summary) {
    const link = document.createElement("a");
    link.href = `#${item.priority_area_id}`;
    link.textContent = item.action;
    const row = document.createElement("li");
    row.append(link);
    summary.append(row);
  }
  results.append(text("h2", "What to revise"), summary);

  results.append(text("h2", "Priority areas for strengthening"));
  for (const area of result.priority_areas) {
    const section = document.createElement("section");
    section.id = area.priority_area_id;
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
    results.append(section);
  }

  results.append(text("h2", "Limitations and document coverage"));
  if (result.limitations.length) {
    const list = document.createElement("ul");
    for (const limitation of result.limitations) {
      list.append(text("li", limitation));
    }
    results.append(list);
  }
  const coverage = result.document_coverage;
  if (coverage) {
    results.append(
      labelledParagraph("Primary document", coverage.primary_document, "coverage-primary"),
      labelledParagraph("Package documents", coverage.package_documents.join(", ") || "None supplied", "coverage-package"),
      labelledParagraph("Context documents", coverage.context_documents.join(", ") || "None supplied", "coverage-context"),
      labelledParagraph("Coverage note", coverage.coverage_note, "coverage-note"),
    );
  }
  showResults();
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
    const data = JSON.parse(event.data);
    progress.textContent = `Working: ${data.step}`;
  });
  source.addEventListener("run_complete", async () => {
    if (!isCurrentOperation(operation) || !closeActiveSource(source)) return;
    progress.textContent = "Review complete";
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
    showRecoverableFailure(`Review stopped: ${label}`);
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
  progress.textContent = "Uploading and validating";
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
    progress.textContent = "User-provided correction saved; rerun requested.";
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

document.querySelector("#reset-review").addEventListener("click", async () => {
  const resetEpoch = ++operationEpoch;
  const assessmentToPurge = assessmentId;
  resetPending = true;
  activeEventSource?.close();
  activeEventSource = undefined;
  sessionStorage.removeItem("cpf_fcv_assessment_id");
  assessmentId = "";
  results.replaceChildren();
  progress.replaceChildren();
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
      resetPending = false;
    }
  }
});

returnToIntake.addEventListener("click", () => {
  showLanding();
});

if (window.__CPF_FCV_REVIEWER_TEST__) {
  window.__cpfFcvReviewerTestHooks = {
    getActiveSource: () => activeEventSource,
    setAssessmentId: (value) => { assessmentId = value; },
    watchEvents,
  };
}
