"""Exercise real mount-aware HTML/API responses and browser requests."""
import json
from io import BytesIO

import pytest

from cpf_fcv_reviewer.app import create_app
from test_frontend_download import COMMON_HARNESS, run_node


@pytest.mark.parametrize("prefix", ["", "/content/cpf-preview"])
def test_html_and_submission_links_stay_inside_mount(prefix):
    app = create_app(
        {"TESTING": True, "START_BACKGROUND_RUNS": False},
        services={}, use_environment=False,
    )
    client = app.test_client()
    environ = {"SCRIPT_NAME": prefix}
    html = client.get("/", environ_overrides=environ).get_data(as_text=True)
    assert f'href="{prefix}/static/styles.css"' in html
    assert f'src="{prefix}/static/app.js"' in html
    assert f'data-app-root="{prefix}"' in html
    response = client.post("/api/reviews", environ_overrides=environ, data={
        "country": "Benin", "review_stage": "concept_review",
        "cpf": (BytesIO(b"Readable synthetic CPF text " * 20), "cpf.txt"),
    })
    assert response.status_code == 201
    payload = response.get_json()
    base = f"{prefix}/api/reviews/{payload['assessment_id']}"
    assert payload["event_url"] == base + "/events"
    assert payload["result_url"] == base + "/result"


@pytest.mark.parametrize("prefix", ["", "/content/cpf-preview"])
def test_browser_restore_and_download_use_mount_and_isolated_storage(prefix):
    script = COMMON_HARNESS + "\nconst mount = " + json.dumps(prefix) + ";\n" + r'''
    (async () => {
      document.body.dataset.appRoot = mount;
      const storageReads = [];
      global.sessionStorage.getItem = (key) => {storageReads.push(key); return "";};
      const requests = [];
      global.fetch = async (url) => {
        requests.push(url);
        return {ok: false, status: 503};
      };
      require(process.argv[1]);
      const hooks = window.__cpfFcvReviewerTestHooks;
      hooks.setAssessmentId("synthetic-review");
      await hooks.restoreSavedReview();
      await nodes["#export-docx"].trigger("click");
      await nodes["#export-readout-docx"].trigger("click");
      for (const suffix of ["result", "export.docx", "export.docx?view=summary"]) {
        if (!requests.includes(`${mount}/api/reviews/synthetic-review/${suffix}`)) {
          throw Error(`Request escaped mount: ${JSON.stringify(requests)}`);
        }
      }
      for (const key of ["cpf_fcv_assessment_id", "cpf_fcv_country"]) {
        if (!storageReads.includes(key + mount)) throw Error("Storage crosses app mounts");
      }
    })().catch(error => { console.error(error); process.exit(1); });
    '''
    completed = run_node(script)
    assert completed.returncode == 0, completed.stderr
