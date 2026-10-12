"""The three reader views preserve concise findings, priority order and editing."""
import json
from io import BytesIO
from pathlib import Path

import pytest
from docx import Document
from test_frontend_download import COMMON_HARNESS, run_node

from cpf_fcv_reviewer.contracts import CoreFinding, CoreQuestion, RevisionSummaryItem
from cpf_fcv_reviewer.export_docx import build_docx

LABELS = (
    "Drivers and priorities", "Critical actions and commitment",
    "Program implications", "If/Then calibration",
)


@pytest.mark.parametrize("save_ok", [False, True])
def test_correction_preserves_unsaved_wording_or_stops(make_valid_result, save_ok):
    result, _ = make_valid_result
    payload = result.model_dump(mode="json") | {"email_text": "Original wording"}
    harness = COMMON_HARNESS + "\nconst complete = " + json.dumps(payload) + ";\n"
    harness += "const saveOk = " + json.dumps(save_ok) + ";\n" + r'''
    (async () => {
      for (const id of ["#peer-email-editor", "#email-status", "#email-warning"])
        nodes[id] = node();
      global.EventSource = class { addEventListener() {} close() {} };
      const writes = [];
      global.fetch = async (url, options) => {
        if (options?.method) writes.push([url, options]);
        return {
          ok: !(url.endsWith("/email") && !saveOk), status: 200,
          json: async () => url.endsWith("/result") ? complete : {
            messages: [], assessment_id: "child", event_url: "events", result_url: "result",
          },
        };
      };
      require(process.argv[1]);
      const hooks = window.__cpfFcvReviewerTestHooks;
      hooks.setAssessmentId("parent");
      await hooks.restoreSavedReview();
      await hooks.loadAssistantHistory();
      nodes["#peer-email-editor"].value = "Unsaved coordinator wording";
      await hooks.updateAssessment("Qualify the finding");
      if (!writes[0]?.[0].endsWith("/email")) throw Error("Wording not saved first");
      if (JSON.parse(writes[0][1].body).text !== "Unsaved coordinator wording")
        throw Error("Wrong wording saved");
      const corrected = writes.some(([url]) => url.endsWith("/corrections"));
      if (corrected !== saveOk) throw Error("Correction proceeded without preserving wording");
      if (!saveOk && nodes["#peer-email-editor"].value !== "Unsaved coordinator wording")
        throw Error("Failed save lost wording");
    })().catch(error => { console.error(error); process.exit(1); });
    '''
    completed = run_node(harness)
    assert completed.returncode == 0, completed.stderr


def test_full_export_has_four_concise_findings(completed_coordinator_review):
    _, client, assessment_id = completed_coordinator_review
    response = client.get(f"/api/reviews/{assessment_id}/export.docx")
    paragraphs = [p.text for p in Document(BytesIO(response.data)).paragraphs]
    for label in LABELS:
        assert paragraphs.count(label) == 1
    assert "RRA driver-to-response assessment" not in paragraphs
    assert any("Where to act" in value for value in paragraphs)


def test_summary_does_not_drop_selected_priorities(make_valid_result):
    result, evidence = make_valid_result
    areas = tuple(
        result.priority_areas[0].model_copy(update={
            "priority_area_id": f"pa-{index}", "heading": f"Priority issue {index}",
        })
        for index in range(1, 6)
    )
    result = result.model_copy(update={
        "priority_areas": areas,
        "revision_summary": tuple(
            RevisionSummaryItem(priority_area_id=a.priority_area_id, title=a.heading)
            for a in areas
        ),
        "core_findings": tuple(
            CoreFinding(
                question=q, assessment="Limited evidence for this question.", basis="limited",
            )
            for q in CoreQuestion
        ),
    })
    doc = Document(BytesIO(build_docx(
        result, evidence=evidence, hydrated_referrals=(), summary=True,
    )))
    headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
    assert [a.heading for a in areas] == [
        text for text in headings if text.startswith("Priority issue")
    ]


def test_intake_and_email_controls_are_optional_and_accessible():
    html = Path("src/cpf_fcv_reviewer/templates/index.html").read_text(encoding="utf-8")
    for element in [
        'id="review-questions"', 'id="previous-comments"', 'id="framing-override"',
        'id="result-tab-email"', 'id="email-panel"', 'id="peer-email-editor"',
        'id="copy-peer-email"', 'id="assistant-input"', 'data-assistant-prompt=',
    ]:
        assert element in html
    assert 'aria-controls="email-panel"' in html
    assert 'aria-labelledby="result-tab-email"' in html
    assert 'value="" disabled selected>Select review stage' in html
    for line in html.splitlines():
        if any(f'id="{name}"' in line for name in (
            "review-questions", "previous-comments",
        )):
            assert "required" not in line
