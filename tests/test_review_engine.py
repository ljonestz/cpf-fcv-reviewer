import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from cpf_fcv_reviewer import model_gateway
from cpf_fcv_reviewer.contracts import (
    DiagnosticMode,
    EvidencePack,
    PriorityQuestionResponse,
    ReviewDraft,
    ReviewResult,
    RunMetadata,
)
from cpf_fcv_reviewer.model_gateway import AnthropicModelGateway
from cpf_fcv_reviewer.review_engine import STAGE_RULES, ReviewEngine


class FakeGateway:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def generate(self, *, prompt_name, payload, output_type):
        self.calls.append((prompt_name, payload, output_type))
        return self.result


def metadata(
    mode: DiagnosticMode = DiagnosticMode.LIMITED_FRAMING,
    stage: str = "finalization",
) -> RunMetadata:
    return RunMetadata(
        run_id="run-1",
        created_at=datetime.now(UTC),
        review_stage=stage,
        diagnostic_mode=mode,
        app_release="0.1.0",
        schema_version="1.0.0",
        rubric_version="1.0.0",
        prompt_bundle_version="1.0.0",
        registry_versions={"fcv_strategy": "1.0.0"},
        model_id="fake",
    )


def result_for(meta: RunMetadata) -> ReviewResult:
    return ReviewResult(
        metadata=meta,
        executive_judgment="Evidence is limited.",
        diagnostic_title="Limited FCV diagnostic-framing assessment",
        findings=(),
        recommendations=(),
        limitations=("No RRA or accepted equivalent was available.",),
    )


def draft_for(meta: RunMetadata) -> ReviewDraft:
    return ReviewDraft.model_validate(result_for(meta).model_dump(exclude={"metadata"}))


def test_limited_mode_has_non_alignment_title_and_uses_review_prompt():
    meta = metadata()
    gateway = FakeGateway(draft_for(meta))

    result = ReviewEngine(gateway).review(
        EvidencePack(metadata=meta, evidence=(), diagnostic_entries=())
    )

    assert result.diagnostic_title == "Limited FCV diagnostic-framing assessment"
    assert gateway.calls[0][0] == "review"
    assert gateway.calls[0][2] is ReviewDraft


def test_model_output_schema_excludes_authoritative_run_metadata():
    meta = metadata()
    gateway = FakeGateway(draft_for(meta))

    ReviewEngine(gateway).review(
        EvidencePack(metadata=meta, evidence=(), diagnostic_entries=())
    )

    assert gateway.calls[0][2].__name__ == "ReviewDraft"


def test_finalization_stage_rule_and_serialized_evidence_pack_are_injected():
    meta = metadata()
    evidence_pack = EvidencePack(metadata=meta, evidence=(), diagnostic_entries=())
    gateway = FakeGateway(draft_for(meta))

    ReviewEngine(gateway).review(evidence_pack)

    payload = gateway.calls[0][1]
    assert "targeted, high-value edits" in payload["stage_rule"]
    assert payload["evidence_pack"] == evidence_pack.model_dump(mode="json")
    assert payload["evidence_pack"]["metadata"]["diagnostic_mode"] == "limited_framing"


@pytest.mark.parametrize("stage", sorted(STAGE_RULES))
def test_every_supported_review_stage_injects_its_rule(stage):
    meta = metadata(stage=stage)
    gateway = FakeGateway(draft_for(meta))

    ReviewEngine(gateway).review(
        EvidencePack(metadata=meta, evidence=(), diagnostic_entries=())
    )

    assert gateway.calls[0][1]["stage_rule"] == STAGE_RULES[stage]


def test_unsupported_review_stage_is_rejected_before_gateway_call():
    meta = metadata(stage="unsupported")
    gateway = FakeGateway(result_for(meta))

    with pytest.raises(ValueError, match="Unsupported review stage: unsupported"):
        ReviewEngine(gateway).review(
            EvidencePack(metadata=meta, evidence=(), diagnostic_entries=())
        )

    assert gateway.calls == []


def test_each_confirmed_priority_question_has_one_direct_or_limited_response():
    meta = metadata()
    questions = (
        "Is the implementation assumption confirmed?",
        "Is the partnership logic credible?",
    )
    responses = (
        PriorityQuestionResponse(
            question_id="pq-1",
            question=questions[0],
            direct_answer="The supplied evidence confirms the stated assumption.",
            evidence_ids=(),
            confidence="medium",
        ),
        PriorityQuestionResponse(
            question_id="pq-2",
            question=questions[1],
            direct_answer="The supplied evidence does not confirm it.",
            evidence_ids=(),
            confidence="low",
            limitation="Confirmation is needed from the country team.",
        ),
    )
    expected = draft_for(meta).model_copy(
        update={"priority_question_responses": responses}
    )
    gateway = FakeGateway(expected)

    actual = ReviewEngine(gateway).review(
        EvidencePack(metadata=meta, evidence=(), diagnostic_entries=()),
        priority_questions=questions,
    )

    assert actual.priority_question_responses == responses
    assert responses[1].limitation == "Confirmation is needed from the country team."


def test_repair_keeps_authoritative_metadata_out_of_the_model_schema_and_payload():
    meta = metadata()
    gateway = FakeGateway(draft_for(meta))

    repaired = ReviewEngine(gateway).repair(
        result_for(meta),
        [{"code": "example", "message": "Repair the draft."}],
    )

    prompt_name, payload, output_type = gateway.calls[0]
    assert prompt_name == "repair"
    assert output_type is ReviewDraft
    assert "metadata" not in payload["draft"]
    assert repaired.metadata.repair_count == 1
    assert repaired.metadata.run_id == meta.run_id


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeAnthropicClient:
    def __init__(self, response):
        self.messages = FakeMessages(response)


def test_anthropic_gateway_sends_json_and_validates_model_response(monkeypatch):
    meta = metadata()
    expected = result_for(meta)
    response = SimpleNamespace(parsed_output=expected)
    client = FakeAnthropicClient(response)
    monkeypatch.setattr(model_gateway.anthropic, "Anthropic", lambda api_key: client)
    gateway = AnthropicModelGateway("test-key", "test-model")

    actual = gateway.generate(
        prompt_name="review",
        payload={"accented": "Résilience"},
        output_type=ReviewResult,
    )

    assert actual == expected
    call = client.messages.calls[0]
    assert call["model"] == "test-model"
    assert call["max_tokens"] == 12000
    assert call["system"].startswith("Version: 1.0.0")
    assert call["output_format"] is ReviewResult
    assert json.loads(call["messages"][0]["content"]) == {"accented": "Résilience"}


def test_anthropic_gateway_rejects_missing_parsed_output(monkeypatch):
    client = FakeAnthropicClient(SimpleNamespace(parsed_output=None))
    monkeypatch.setattr(model_gateway.anthropic, "Anthropic", lambda api_key: client)
    gateway = AnthropicModelGateway("test-key", "test-model")

    with pytest.raises(ValueError, match="no parsed output"):
        gateway.generate(
            prompt_name="review",
            payload={"input": "bounded"},
            output_type=ReviewResult,
        )


def test_confirmed_priority_questions_are_injected_into_review_payload():
    meta = metadata()
    gateway = FakeGateway(draft_for(meta))
    questions = (
        "Does the results framework track geographic distribution?",
        "Is the partnership logic credible?",
    )

    ReviewEngine(gateway).review(
        EvidencePack(metadata=meta, evidence=(), diagnostic_entries=()),
        priority_questions=questions,
    )

    assert gateway.calls[0][1]["priority_questions"] == questions
