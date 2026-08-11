const form = document.querySelector("#review-form");
const progress = document.querySelector("#progress");
const results = document.querySelector("#results");
const corrections = document.querySelector("#corrections");
const actions = document.querySelector("#actions");
const guidance = document.querySelector("#guidance");
const questionPanel = document.querySelector("#priority-questions");
const questionList = document.querySelector("#priority-question-list");
let assessmentId = sessionStorage.getItem("cpf_fcv_assessment_id") || "";

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
  results.hidden = false;
  corrections.hidden = false;
  actions.hidden = false;
}

async function loadResult(resultUrl) {
  const response = await fetch(resultUrl);
  if (response.status === 202) return;
  if (!response.ok) throw new Error("Review result is unavailable.");
  renderResult(await response.json());
}

function watchEvents(eventUrl, resultUrl) {
  const source = new EventSource(eventUrl);
  source.addEventListener("step_start", (event) => {
    const data = JSON.parse(event.data);
    progress.textContent = `Working: ${data.step}`;
  });
  source.addEventListener("run_complete", async () => {
    source.close();
    progress.textContent = "Review complete";
    await loadResult(resultUrl);
  });
  source.addEventListener("run_failed", (event) => {
    source.close();
    const data = JSON.parse(event.data);
    const label = failureLabels[data.error] || failureLabels.review_failed;
    progress.textContent = `Review stopped: ${label}`;
  });
  source.addEventListener("expired", () => {
    source.close();
    progress.textContent = "This volatile review session expired. Upload again.";
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  progress.hidden = false;
  progress.textContent = "Uploading and validating";
  const response = await fetch("/api/reviews", {
    method: "POST",
    body: new FormData(form),
  });
  if (!response.ok) {
    progress.textContent = "The review could not start.";
    return;
  }
  const created = await response.json();
  assessmentId = created.assessment_id;
  sessionStorage.setItem("cpf_fcv_assessment_id", assessmentId);
  watchEvents(created.event_url, created.result_url);
});

document.querySelector("#submit-correction").addEventListener("click", async () => {
  const correction = document.querySelector("#correction-text").value.trim();
  if (!correction || !assessmentId) return;
  const response = await fetch(`/api/reviews/${assessmentId}/corrections`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({text: correction}),
  });
  if (response.ok) {
    const child = await response.json();
    assessmentId = child.assessment_id;
    sessionStorage.setItem("cpf_fcv_assessment_id", assessmentId);
    progress.hidden = false;
    progress.textContent = "User-provided correction saved; rerun requested.";
    watchEvents(child.event_url, child.result_url);
  }
});

document.querySelector("#export-docx").addEventListener("click", () => {
  if (assessmentId) window.location.assign(`/api/reviews/${assessmentId}/export.docx`);
});

document.querySelector("#reset-review").addEventListener("click", async () => {
  if (assessmentId) await fetch(`/api/reviews/${assessmentId}`, {method: "DELETE"});
  sessionStorage.removeItem("cpf_fcv_assessment_id");
  assessmentId = "";
  results.replaceChildren();
  results.hidden = true;
  corrections.hidden = true;
  actions.hidden = true;
  progress.hidden = true;
  form.reset();
});
