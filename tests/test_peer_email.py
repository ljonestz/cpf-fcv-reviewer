"""Email drafting uses validated findings and cannot add signatures or priorities."""
import importlib
import importlib.util

import pytest

from cpf_fcv_reviewer import contracts


def module():
    assert importlib.util.find_spec("cpf_fcv_reviewer.email_draft"), "Email drafting is missing"
    return importlib.import_module("cpf_fcv_reviewer.email_draft")


def draft(**overrides):
    assert hasattr(contracts, "PeerEmailDraft"), "Email contract is missing"
    return contracts.PeerEmailDraft(
        opening="Thank you for sharing the draft.",
        comments=(contracts.PeerEmailComment(
            heading="Delivery arrangements",
            text="Clarify the causal link.",
            priority_area_ids=("pa-1",),
        ),),
        **overrides,
    )


def test_renderer_is_unsigned():
    text = module().render_peer_email(draft())
    assert text.startswith("Dear colleagues,")
    assert "Delivery arrangements" in text
    assert "Shubham" not in text
    assert "on behalf" not in text


@pytest.mark.parametrize("text", [
    "The CPF complies with PC14.",
    "The CPF meets PC14.",
    "PC14: Partly meets.",
    "The country is on the FCS list.",
    "The response is appropriate.\nShubham",
    "Allocate 987654 additional grants.",
])
def test_generator_rejects_added_determinations_signatures_and_numbers(make_valid_result, text):
    result, _ = make_valid_result
    mod = module()
    candidate = draft()
    candidate = candidate.model_copy(update={
        "comments": (candidate.comments[0].model_copy(update={"text": text}),),
    })

    class Gateway:
        def generate(self, **kwargs):
            return candidate

    with pytest.raises(ValueError):
        mod.generate_peer_email(result, Gateway())


def test_generator_rejects_unknown_priority(make_valid_result):
    result, _ = make_valid_result
    mod = module()
    candidate = draft()
    candidate = candidate.model_copy(update={
        "comments": (candidate.comments[0].model_copy(update={"priority_area_ids": ("invented",)}),)
    })

    class Gateway:
        def generate(self, **kwargs):
            return candidate

    with pytest.raises(ValueError):
        mod.generate_peer_email(result, Gateway())


def test_generator_preserves_stage_and_separate_questions(make_valid_result):
    result, _ = make_valid_result
    mod = module()

    class Gateway:
        def generate(self, **kwargs):
            self.payload = kwargs["payload"]
            return draft()

    gateway = Gateway()
    generated = mod.generate_peer_email(
        result, gateway, review_questions="Is the results chain clear?",
    )
    assert gateway.payload["review_stage"] == result.metadata.review_stage
    assert gateway.payload["review_questions"] == "Is the results chain clear?"
    assert "evidence_pack" not in gateway.payload
    assert generated == draft()


def test_email_opening_obeys_finalization_stage(make_valid_result):
    result, _ = make_valid_result
    result = result.model_copy(update={"metadata": result.metadata.model_copy(update={
        "review_stage": "finalization",
    })})

    class Gateway:
        def generate(self, **kwargs):
            return draft().model_copy(update={
                "opening": "Replace all objectives and rebuild the entire delivery model.",
            })

    with pytest.raises(ValueError, match="stage"):
        module().generate_peer_email(result, Gateway())


def test_email_rejects_new_unsupported_present_day_claim(make_valid_result):
    result, evidence = make_valid_result

    class Gateway:
        def generate(self, **kwargs):
            return draft().model_copy(update={
                "opening": "Conflict has intensified across Benin and displacement is rising.",
            })

    with pytest.raises(ValueError, match="current-context"):
        module().generate_peer_email(result, Gateway(), evidence=evidence)


@pytest.mark.parametrize("fail_email", [False, True])
def test_single_run_drafts_email_and_keeps_note_on_draft_failure(monkeypatch, fail_email):
    from io import BytesIO
    from pathlib import Path

    from cpf_fcv_reviewer.app import create_smoke_app
    from cpf_fcv_reviewer.routes import run_assessment
    from cpf_fcv_reviewer.smoke import SmokeModelGateway

    generate = SmokeModelGateway.generate

    def checked_generate(self, **kwargs):
        if fail_email and kwargs["prompt_name"] == "peer_email":
            raise ValueError("Invalid email output.")
        return generate(self, **kwargs)

    monkeypatch.setattr(SmokeModelGateway, "generate", checked_generate)
    app = create_smoke_app(start_background_runs=False)
    client = app.test_client()
    primary = (Path(__file__).parent / "fixtures" / "synthetic_en.txt").read_bytes()
    response = client.post("/api/reviews", data={
        "cpf": (BytesIO(primary), "Benin CPF.txt"),
        "country": "Benin", "review_stage": "roc_oc",
    })
    assessment_id = response.json["assessment_id"]
    app.extensions["session_store"].update(assessment_id, coordinator_review_version=2)
    run_assessment(app, assessment_id)
    payload = app.extensions["session_store"].get(assessment_id).payload
    assert payload["status"] == "complete"
    assert len(payload["result"]["core_findings"]) == 4
    if fail_email:
        assert payload["peer_email"] is None
        assert payload["email_error"] == "email_draft_unavailable"
    else:
        assert payload["peer_email"]["comments"]
        assert "signature" not in payload["peer_email"]
