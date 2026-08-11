from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ImmutableRegistryVersions(dict[str, str]):
    def __init__(self, values: dict[str, str]) -> None:
        dict.__init__(self, values)

    @staticmethod
    def _immutable(*args: object, **kwargs: object) -> None:
        raise TypeError("Registry versions are immutable.")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable


class DiagnosticMode(StrEnum):
    RRA_ALIGNMENT = "rra_alignment"
    LIMITED_FRAMING = "limited_framing"


class SensitivityCategory(StrEnum):
    DIRECT = "direct"
    CAUTIOUS = "cautious"
    CONFIRM = "confirm"
    WITHHOLD = "withhold"


class EvidenceLocator(FrozenModel):
    document_title: str
    document_version: str | None = None
    page: int | None = Field(default=None, ge=1)
    heading: str | None = None
    element: str | None = None
    excerpt: str
    is_paraphrase: bool = False

    @field_validator("document_title", "excerpt")
    @classmethod
    def requires_nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Document locator text fields cannot be blank.")
        return value

    @field_validator("heading", "element")
    @classmethod
    def rejects_blank_structural_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Document locator structural text cannot be blank.")
        return value

    @model_validator(mode="after")
    def requires_document_coordinate(self) -> EvidenceLocator:
        if self.page is None and not self.heading and not self.element:
            raise ValueError("Document evidence requires page, heading, or element.")
        return self


class EvidenceItem(FrozenModel):
    evidence_id: str
    evidence_type: Literal[
        "document_fact",
        "current_context",
        "registry_language",
        "user_correction",
        "analytical_inference",
    ]
    text: str
    locator: EvidenceLocator | None = None
    confidence: Literal["high", "medium", "low"]
    source_url: str | None = None

    @model_validator(mode="after")
    def requires_evidence_source(self) -> EvidenceItem:
        if self.evidence_type == "document_fact" and self.locator is None:
            raise ValueError("Document facts require a document locator.")
        if self.evidence_type == "current_context" and (
            self.source_url is None or not self.source_url.strip()
        ):
            raise ValueError("Current-context evidence requires a source URL.")
        return self


class UserCorrection(FrozenModel):
    correction_id: str
    created_at: datetime
    affected_finding_id: str | None = None
    text: str
    rationale: str | None = None
    independently_supported: bool = False


class DiagnosticEntry(FrozenModel):
    entry_id: str
    short_name: str
    group: Literal[
        "principal_driver",
        "delivery_risk",
        "contextual_condition",
        "resilience_opportunity",
    ]
    materiality: Literal["high", "medium", "low"]
    source_evidence_ids: tuple[str, ...]
    grouping_rationale: str


class Finding(FrozenModel):
    finding_id: str
    title: str
    narrative: str
    status: Literal[
        "aligned",
        "partially_aligned",
        "not_reflected",
        "strong_foundation",
        "needs_strengthening",
        "material_gap",
    ]
    evidence_ids: tuple[str, ...]
    sensitivity: SensitivityCategory


class Recommendation(FrozenModel):
    recommendation_id: str
    finding_id: str
    priority_tier: Literal["core", "additional"]
    action: str
    why_it_matters: str
    target_locator: EvidenceLocator
    stage_behavior: str
    sensitivity: SensitivityCategory


class RunMetadata(FrozenModel):
    run_id: str
    created_at: datetime
    review_stage: str
    diagnostic_mode: DiagnosticMode
    app_release: str
    schema_version: str
    rubric_version: str
    prompt_bundle_version: str
    registry_versions: dict[str, str]
    model_id: str
    source_scan_at: datetime | None = None
    output_language: Literal["en"] = "en"
    document_fingerprints: dict[str, str] = Field(
        default_factory=lambda: ImmutableRegistryVersions({})
    )
    registry_bundle_hash: str = ""
    guidance_hash: str = ""
    prompt_hashes: dict[str, str] = Field(default_factory=lambda: ImmutableRegistryVersions({}))
    validation_outcomes: tuple[str, ...] = ()
    correction_ids: tuple[str, ...] = ()
    parent_run_id: str | None = None
    repair_count: int = Field(default=0, ge=0, le=1)

    @field_validator("document_fingerprints", "prompt_hashes")
    @classmethod
    def freezes_content_hashes(cls, value: dict[str, str]) -> dict[str, str]:
        return ImmutableRegistryVersions(value)

    @field_validator("registry_versions")
    @classmethod
    def freezes_registry_versions(cls, value: dict[str, str]) -> dict[str, str]:
        return ImmutableRegistryVersions(value)


class EvidencePack(FrozenModel):
    metadata: RunMetadata
    evidence: tuple[EvidenceItem, ...]
    diagnostic_entries: tuple[DiagnosticEntry, ...]
    user_corrections: tuple[UserCorrection, ...] = ()
    warnings: tuple[str, ...] = ()


class PriorityQuestionResponse(FrozenModel):
    question_id: str
    question: str
    direct_answer: str
    evidence_ids: tuple[str, ...]
    confidence: Literal["high", "medium", "low"]
    limitation: str | None = None


class ReviewResult(FrozenModel):
    metadata: RunMetadata
    executive_judgment: str
    diagnostic_title: str
    findings: tuple[Finding, ...]
    recommendations: tuple[Recommendation, ...]
    institutional_referral_ids: tuple[str, ...] = ()
    priority_question_responses: tuple[PriorityQuestionResponse, ...] = ()
    limitations: tuple[str, ...] = ()


class ReviewDraft(FrozenModel):
    """Model-authored review content; authoritative run metadata is attached locally."""

    executive_judgment: str
    diagnostic_title: str
    findings: tuple[Finding, ...]
    recommendations: tuple[Recommendation, ...]
    institutional_referral_ids: tuple[str, ...]
    priority_question_responses: tuple[PriorityQuestionResponse, ...]
    limitations: tuple[str, ...]
