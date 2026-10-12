"""Prior comments must be separated before research, digestion and fresh review."""
import importlib
import importlib.util
from dataclasses import replace

import pytest

from cpf_fcv_reviewer.extraction import ExtractedDocument, ExtractedSegment


def module():
    assert importlib.util.find_spec("cpf_fcv_reviewer.prior_comments"), (
        "Prior-comment isolation is missing"
    )
    return importlib.import_module("cpf_fcv_reviewer.prior_comments")


def document(name, text):
    return ExtractedDocument(
        name, (ExtractedSegment(text, 1, None, "page 1"),), (),
    )


def test_dedicated_prior_comments_are_excluded():
    current, prior = module().partition_document(
        document("Previous FCV comments.txt", "SENTINEL_ONLY_PRIOR_COMMENT"),
    )
    assert current is None
    assert "SENTINEL_ONLY_PRIOR_COMMENT" in prior.segments[0].text


def test_mixed_document_keeps_current_evidence_and_separates_comments():
    current, prior = module().partition_document(document(
        "Package.txt",
        "Current program evidence.\nPrevious FCV comments\nSENTINEL_PRIOR\n"
        "Annex 2: Results framework\nCurrent indicator evidence.",
    ))
    assert "SENTINEL_PRIOR" not in " ".join(s.text for s in current.segments)
    assert "Current indicator" in " ".join(s.text for s in current.segments)
    assert "SENTINEL_PRIOR" in " ".join(s.text for s in prior.segments)
    assert current.segments[0].page == 1


def test_ordinary_reference_to_prior_decisions_is_current_evidence():
    original = document("CLR.txt", "The program responds to previous FCV comments and decisions.")
    current, prior = module().partition_document(original)
    assert current == original
    assert prior is None


def test_prior_section_can_span_segments():
    original = document("Package.docx", "Current approach.")
    original = replace(original, segments=(
        *original.segments,
        ExtractedSegment("Earlier FCV comments", None, "Earlier FCV comments", "paragraph 2"),
        ExtractedSegment("SENTINEL_PRIOR", None, None, "paragraph 3"),
        ExtractedSegment("Annex 3: Current risks", None, None, "paragraph 4"),
    ))
    current, prior = module().partition_document(original)
    assert "SENTINEL_PRIOR" not in " ".join(s.text for s in current.segments)
    assert "Annex 3" in " ".join(s.text for s in current.segments)
    assert prior.segments[-1].element == "paragraph 3"


def test_follow_through_rejects_unknown_current_evidence(make_valid_result):
    result, evidence = make_valid_result
    mod = module()

    class Gateway:
        def generate(self, **kwargs):
            prior_id = kwargs["payload"]["prior_evidence"][0]["evidence_id"]
            return mod.PriorCommentReport(
                checks=(mod.PriorCommentCheck(
                    comment_label="Earlier selectivity comment",
                    assessment="The change was made.",
                    status="addressed",
                    prior_evidence_ids=(prior_id,),
                    current_evidence_ids=("invented-current",),
                ),),
                coverage_note="One earlier comment considered.",
            )

    with pytest.raises(ValueError):
        mod.check_prior_comments(
            result, evidence, (document("Previous comments.txt", "Clarify selectivity."),),
            Gateway(), prohibited_terms=set(),
        )


def test_runtime_separates_prior_text_before_digest_and_review(monkeypatch):
    import json
    from io import BytesIO
    from pathlib import Path

    from cpf_fcv_reviewer import runtime
    from cpf_fcv_reviewer.app import create_smoke_app
    from cpf_fcv_reviewer.routes import run_assessment
    from cpf_fcv_reviewer.smoke import SmokeModelGateway

    calls = []
    generate = SmokeModelGateway.generate

    def capture(self, **kwargs):
        calls.append((kwargs["prompt_name"], json.dumps(kwargs["payload"])))
        if kwargs["prompt_name"] == "prior_comments":
            mod = module()
            payload = kwargs["payload"]
            return mod.PriorCommentReport(
                checks=(mod.PriorCommentCheck(
                    comment_label="Earlier delivery point",
                    assessment="The current draft addresses delivery in part.",
                    status="partly_addressed",
                    prior_evidence_ids=(payload["prior_evidence"][0]["evidence_id"],),
                    current_evidence_ids=(payload["current_evidence"][0]["evidence_id"],),
                ),),
                coverage_note="Earlier comments considered after independent analysis.",
            )
        return generate(self, **kwargs)

    monkeypatch.setattr(SmokeModelGateway, "generate", capture)
    monkeypatch.setattr(runtime, "PACKAGE_DIRECT_MAX_CHARACTERS", 50)
    app = create_smoke_app(start_background_runs=False)
    primary = (Path(__file__).parent / "fixtures" / "synthetic_en.txt").read_bytes()
    with app.test_client() as client:
        response = client.post("/api/reviews", data={
            "cpf": (BytesIO(primary), "Benin CPF.txt"),
            "country": "Benin", "review_stage": "roc_oc",
            "package_documents": [
                (BytesIO(b"Clarify delivery. SENTINEL_PRIOR"), "Previous FCV comments.txt"),
                (BytesIO(
                    b"Current implementation evidence.\n" * 20
                    + b"Previous FCV comments\nSENTINEL_MIXED\n"
                    + b"Annex 2: Results\nCurrent indicator evidence."
                ), "Supporting package.txt"),
            ],
        })
        assert response.status_code == 201
        assessment_id = response.json["assessment_id"]
        run_assessment(app, assessment_id)
        state = app.extensions["session_store"].get(assessment_id)
        assert state.payload["status"] == "complete"
        fresh = [text for name, text in calls if name in {"review", "document_digest"}]
        assert fresh
        assert all("SENTINEL_" not in text for text in fresh)
        follow = [text for name, text in calls if name == "prior_comments"]
        assert len(follow) == 1
        assert "SENTINEL_PRIOR" in follow[0] and "SENTINEL_MIXED" in follow[0]
        assert state.payload["prior_comment_report"]["checks"][0]["status"] == "partly_addressed"
