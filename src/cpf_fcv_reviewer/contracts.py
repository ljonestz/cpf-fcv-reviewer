from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _requires_nonblank_text(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be blank.")
    return value


def _requires_nonblank_items(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if any(not value.strip() for value in values):
        raise ValueError(f"{field_name} cannot contain blank entries.")
    return values


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


class DetailLevel(StrEnum):
    BRIEF = "brief"
    STANDARD = "standard"
    IN_DEPTH = "in_depth"


class DocumentRole(StrEnum):
    PRIMARY = "primary"
    PACKAGE = "package"
    CONTEXT = "context"


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
    document_role: DocumentRole | None = None

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
    affected_priority_area_id: str | None = None
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


class RecommendationScale(StrEnum):
    PREPARATION_PRIORITY = "preparation_priority"
    SUBSTANTIVE_REVISION = "substantive_revision"
    TARGETED_EDIT = "targeted_edit"
    FINE_TUNING = "fine_tuning"
    COMMENT_RESPONSE = "comment_response"


class RevisionSummaryItem(FrozenModel):
    priority_area_id: str
    action: str

    @field_validator("priority_area_id", "action")
    @classmethod
    def requires_nonblank_summary_text(cls, value: str) -> str:
        return _requires_nonblank_text(value, "Revision summary fields")


class PriorityArea(FrozenModel):
    priority_area_id: str
    heading: str
    assessment: str
    why_it_matters: str
    recommended_action: str
    target_locator: EvidenceLocator
    recommendation_scale: RecommendationScale
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    sensitivity: SensitivityCategory
    comment_reference: str | None = None

    @field_validator(
        "priority_area_id",
        "heading",
        "assessment",
        "why_it_matters",
        "recommended_action",
    )
    @classmethod
    def requires_nonblank_narrative(cls, value: str) -> str:
        return _requires_nonblank_text(value, "Narrative review fields")

    @field_validator("evidence_ids")
    @classmethod
    def requires_nonblank_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _requires_nonblank_items(value, "Evidence identifiers")

    @field_validator("comment_reference")
    @classmethod
    def rejects_blank_comment_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _requires_nonblank_text(value, "Comment reference")


class DocumentCoverage(FrozenModel):
    primary_document: str
    package_documents: tuple[str, ...] = ()
    context_documents: tuple[str, ...] = ()
    coverage_note: str

    @field_validator("primary_document", "coverage_note")
    @classmethod
    def requires_nonblank_coverage_text(cls, value: str) -> str:
        return _requires_nonblank_text(value, "Document coverage fields")

    @field_validator("package_documents", "context_documents")
    @classmethod
    def rejects_blank_document_entries(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _requires_nonblank_items(value, "Document coverage entries")


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
    detail_level: DetailLevel = DetailLevel.STANDARD
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


class ReviewResult(FrozenModel):
    metadata: RunMetadata
    overall_read: str
    revision_summary: tuple[RevisionSummaryItem, ...]
    priority_areas: tuple[PriorityArea, ...]
    institutional_referral_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    document_coverage: DocumentCoverage

    @field_validator("overall_read")
    @classmethod
    def requires_nonblank_overall_read(cls, value: str) -> str:
        return _requires_nonblank_text(value, "Overall read")


class ReviewDraft(FrozenModel):
    """Model-authored review content; authoritative run metadata is attached locally."""

    overall_read: str
    revision_summary: tuple[RevisionSummaryItem, ...]
    priority_areas: tuple[PriorityArea, ...]
    institutional_referral_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    coverage_note: str

    @field_validator("overall_read")
    @classmethod
    def requires_nonblank_overall_read(cls, value: str) -> str:
        return _requires_nonblank_text(value, "Overall read")
