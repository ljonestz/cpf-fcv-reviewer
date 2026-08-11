from pathlib import Path

HTML = Path("src/cpf_fcv_reviewer/templates/index.html")
JS = Path("src/cpf_fcv_reviewer/static/app.js")
CSS = Path("src/cpf_fcv_reviewer/static/styles.css")


def test_priority_question_confirmation_controls_are_wired():
    html = HTML.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")

    assert 'id="priority-questions"' in html
    assert 'id="priority-question-list"' in html
    assert "Questions requiring a dedicated response" in html
    assert "function detectedQuestions" in javascript
    assert 'checkbox.name = "priority_questions"' in javascript
    assert 'guidance.addEventListener("input", renderPriorityQuestions)' in javascript
    assert "toLocaleLowerCase()" in javascript
    assert "#priority-question-list label" in css
    assert "#priority-question-list input" in css


def test_correction_handler_switches_to_child_run_and_watches_it():
    javascript = JS.read_text(encoding="utf-8")

    assert "assessmentId = child.assessment_id" in javascript
    assert 'sessionStorage.setItem("cpf_fcv_assessment_id", assessmentId)' in javascript
    assert "watchEvents(child.event_url, child.result_url)" in javascript
