from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


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
    parent_run_id: str | None = None
    repair_count: int = Field(default=0, ge=0, le=1)


class EvidencePack(FrozenModel):
    metadata: RunMetadata
    evidence: tuple[EvidenceItem, ...]
    diagnostic_entries: tuple[DiagnosticEntry, ...]
    user_corrections: tuple[UserCorrection, ...] = ()
    warnings: tuple[str, ...] = ()


class ReviewResult(FrozenModel):
    metadata: RunMetadata
    executive_judgment: str
    diagnostic_title: str
    findings: tuple[Finding, ...]
    recommendations: tuple[Recommendation, ...]
    institutional_referral_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
