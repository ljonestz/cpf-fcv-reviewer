const form = document.querySelector("#review-form");
const landingView = document.querySelector("#landing-view");
const landingNotice = document.querySelector("#landing-notice");
const reviewWorkspace = document.querySelector("#review-workspace");
const progress = document.querySelector("#progress");
const results = document.querySelector("#results");
const corrections = document.querySelector("#corrections");
const actions = document.querySelector("#actions");
const returnToIntake = document.querySelector("#return-to-intake");
const guidance = document.querySelector("#guidance");
const questionPanel = document.querySelector("#priority-questions");
const questionList = document.querySelector("#priority-question-list");
const submitCorrection = document.querySelector("#submit-correction");
let assessmentId = sessionStorage.getItem("cpf_fcv_assessment_id") || "";
let activeEventSource;
let operationEpoch = 0;
let resetPending = false;
const RESULT_RETRY_LIMIT = 3;
const RESULT_RETRY_DELAY_MS = 250;
const SOURCE_ERROR_LIMIT = 2;

const sensitivityLabels = {
  direct: "Suitable to state directly",
  cautious: "Frame cautiously",
  confirm: "Confirm with country team or FCV specialist",
  withhold: "Do not suggest for inclusion without guidance",
};

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

function detectedQuestions(value) {
  const questions = new Map();
  for (const line of value.split(/\r?\n/)) {
    const clean = line.trim().replace(/^[-*]\s*/, "").trim();
    if (!clean.endsWith("?")) continue;
    const key = clean.toLocaleLowerCase();
    if (!questions.has(key)) questions.set(key, clean);
  }
  return [...questions.values()];
}

function renderPriorityQuestions() {
  questionList.replaceChildren();
  for (const question of detectedQuestions(guidance.value)) {
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "priority_questions";
    checkbox.value = question;
    checkbox.checked = true;
    label.append(checkbox, document.createTextNode(question));
    questionList.append(label);
  }
  questionPanel.hidden = questionList.children.length === 0;
}

guidance.addEventListener("input", renderPriorityQuestions);

function renderEvidence(result, evidenceId) {
  const details = document.createElement("details");
  details.append(text("summary", `Evidence: ${evidenceId}`));
  const item = result.evidence_by_id?.[evidenceId];
  const locator = item?.locator;
  if (!locator) {
    details.append(text("p", "Traceable evidence detail is unavailable."));
    return details;
  }
  const coordinate = [
    locator.document_title,
    locator.page ? `page ${locator.page}` : "",
    locator.heading || "",
    locator.element || "",
  ].filter(Boolean).join(" | ");
  details.append(
    text("p", coordinate, "evidence-locator"),
    text("p", locator.excerpt, "evidence-excerpt"),
  );
  return details;
}

function renderResult(result) {
  results.replaceChildren();
  results.append(
    text("h2", result.executive_judgment),
    text("h3", result.diagnostic_title),
  );
  for (const finding of result.findings) {
    const article = document.createElement("article");
    article.append(
      text("h3", finding.title),
      text("p", finding.narrative),
      text("p", sensitivityLabels[finding.sensitivity], "sensitivity"),
    );
    for (const evidenceId of finding.evidence_ids) {
      article.append(renderEvidence(result, evidenceId));
    }
    results.append(article);
  }
  if (result.recommendations.length) {
    results.append(text("h2", "Practical options"));
    for (const recommendation of result.recommendations) {
      const article = document.createElement("article");
      const locator = recommendation.target_locator;
      const target = [
        locator.document_title,
        locator.page ? `page ${locator.page}` : "",
        locator.heading || "",
        locator.element || "",
      ].filter(Boolean).join(" | ");
      article.append(
        text("h3", recommendation.action),
        text("p", recommendation.why_it_matters),
        text("p", `Target: ${target}`, "evidence-locator"),
        text("p", sensitivityLabels[recommendation.sensitivity], "sensitivity"),
      );
      results.append(article);
    }
  }
  if (result.priority_question_responses.length) {
    results.append(text("h2", "Priority questions"));
    for (const response of result.priority_question_responses) {
      const article = document.createElement("article");
      article.append(
        text("h3", response.question),
        text("p", response.direct_answer),
      );
      if (response.limitation) {
        article.append(text("p", `Limitation: ${response.limitation}`, "sensitivity"));
      }
      results.append(article);
    }
  }
  if (result.limitations.length) {
    results.append(text("h2", "Limitations"));
    const list = document.createElement("ul");
    for (const limitation of result.limitations) {
      list.append(text("li", limitation));
    }
    results.append(list);
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
