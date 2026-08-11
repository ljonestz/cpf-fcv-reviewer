const form = document.querySelector("#review-form");
const progress = document.querySelector("#progress");
const results = document.querySelector("#results");
const corrections = document.querySelector("#corrections");
const actions = document.querySelector("#actions");
let assessmentId = sessionStorage.getItem("cpf_fcv_assessment_id") || "";

const sensitivityLabels = {
  direct: "Suitable to state directly",
  cautious: "Frame cautiously",
  confirm: "Confirm with country team or FCV specialist",
  withhold: "Do not suggest for inclusion without guidance",
};

function text(tag, value, className = "") {
  const node = document.createElement(tag);
  node.textContent = value;
  if (className) node.className = className;
  return node;
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
      text("p", `Evidence: ${finding.evidence_ids.join(", ")}`, "evidence"),
    );
    results.append(article);
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
    progress.textContent = `Review stopped: ${data.message}`;
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
    progress.hidden = false;
    progress.textContent = "User-provided correction saved; rerun requested.";
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
