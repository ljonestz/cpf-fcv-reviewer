from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

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

ReviewNarrative = Annotated[str, Field(description="Must contain non-whitespace text.")]


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


class AssessmentStatus(StrEnum):
    ALIGNED = "aligned"
    PARTIALLY_ALIGNED = "partially_aligned"
    NOT_EVIDENCED = "not_evidenced"
    NOT_ASSESSABLE = "not_assessable"


class AssessmentConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GapLocus(StrEnum):
    CPF_NARRATIVE = "cpf_narrative"
    RESULTS_FRAMEWORK = "results_framework"
    DELIVERY_ARRANGEMENTS = "delivery_arrangements"
    MONITORING_ADAPTATION = "monitoring_adaptation"
    DOWNSTREAM_OPERATIONALIZATION = "downstream_operationalization"


class FCVStrategicShift(StrEnum):
    ANTICIPATE_BETTER = "anticipate_better"
    DIFFERENTIATED_APPROACH = "differentiated_approach"
    ONE_WBG_JOBS = "one_wbg_jobs"
    TOOLKIT_PARTNERSHIPS_STAFFING = "toolkit_partnerships_staffing"


class CurrentEvidenceTier(StrEnum):
    FULL = "full"
    REDUCED = "reduced"
    DOCUMENT_LED = "document_led"


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
    """
    A real document locator with at least one page, heading, or element coordinate.
    """

    document_title: ReviewNarrative
    document_version: str | None = None
    page: int | None = Field(default=None, ge=1)
    heading: str | None = Field(
        default=None,
        description="When supplied, must contain non-whitespace text.",
    )
    element: str | None = Field(
        default=None,
        description="When supplied, must contain non-whitespace text.",
    )
    excerpt: ReviewNarrative
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


class DiagnosticMap(FrozenModel):
    entries: tuple[DiagnosticEntry, ...] = Field(min_length=1, max_length=20)


class RRADriverAssessment(FrozenModel):
    assessment_id: ReviewNarrative
    driver: ReviewNarrative
    cpf_response: ReviewNarrative
    delivery_mechanism: ReviewNarrative
    result_or_indicator: ReviewNarrative
    remaining_gap: ReviewNarrative
    status: AssessmentStatus
    confidence: AssessmentConfidence
    gap_locus: GapLocus | None = Field(
        default=None,
        description="Required when status is partially_aligned or not_evidenced.",
    )
    evidence_ids: tuple[ReviewNarrative, ...] = Field(
        description="Must contain at least one identifier unless status is not_assessable."
    )

    @field_validator(
        "assessment_id",
        "driver",
        "cpf_response",
        "delivery_mechanism",
        "result_or_indicator",
        "remaining_gap",
    )
    @classmethod
    def requires_nonblank_narrative(cls, value: str) -> str:
        return _requires_nonblank_text(value, "Assessment narrative fields")

    @field_validator("evidence_ids")
    @classmethod
    def requires_nonblank_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _requires_nonblank_items(value, "Assessment evidence identifiers")

    @model_validator(mode="after")
    def validates_assessment_requirements(self) -> RRADriverAssessment:
        if self.status in {
            AssessmentStatus.PARTIALLY_ALIGNED,
            AssessmentStatus.NOT_EVIDENCED,
        } and self.gap_locus is None:
            raise ValueError(
                "gap_locus is required for partially_aligned and not_evidenced assessments."
            )
        if self.status is not AssessmentStatus.NOT_ASSESSABLE and not self.evidence_ids:
            raise ValueError(
                "evidence_ids must contain at least one identifier unless status is "
                "not_assessable."
            )
        return self


class FCVStrategyAssessment(FrozenModel):
    assessment_id: ReviewNarrative
    strategic_shift: FCVStrategicShift
    assessment: ReviewNarrative
    status: AssessmentStatus
    confidence: AssessmentConfidence
    gap_locus: GapLocus | None = Field(
        default=None,
        description="Required when status is partially_aligned or not_evidenced.",
    )
    evidence_ids: tuple[ReviewNarrative, ...] = Field(
        description="Must contain at least one identifier unless status is not_assessable."
    )

    @field_validator("assessment_id", "assessment")
    @classmethod
    def requires_nonblank_narrative(cls, value: str) -> str:
        return _requires_nonblank_text(value, "Assessment narrative fields")

    @field_validator("evidence_ids")
    @classmethod
    def requires_nonblank_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _requires_nonblank_items(value, "Assessment evidence identifiers")

    @model_validator(mode="after")
    def validates_assessment_requirements(self) -> FCVStrategyAssessment:
        if self.status in {
            AssessmentStatus.PARTIALLY_ALIGNED,
            AssessmentStatus.NOT_EVIDENCED,
        } and self.gap_locus is None:
            raise ValueError(
                "gap_locus is required for partially_aligned and not_evidenced assessments."
            )
        if self.status is not AssessmentStatus.NOT_ASSESSABLE and not self.evidence_ids:
            raise ValueError(
                "evidence_ids must contain at least one identifier unless status is "
                "not_assessable."
            )
        return self


class RecommendationScale(StrEnum):
    PREPARATION_PRIORITY = "preparation_priority"
    SUBSTANTIVE_REVISION = "substantive_revision"
    TARGETED_EDIT = "targeted_edit"
    FINE_TUNING = "fine_tuning"
    COMMENT_RESPONSE = "comment_response"


class RevisionSummaryItem(FrozenModel):
    priority_area_id: ReviewNarrative
    title: ReviewNarrative = Field(max_length=100)

    @field_validator("priority_area_id", "title")
    @classmethod
    def requires_nonblank_summary_text(cls, value: str) -> str:
        return _requires_nonblank_text(value, "Revision summary fields")


class PriorityArea(FrozenModel):
    priority_area_id: ReviewNarrative
    heading: ReviewNarrative
    assessment: ReviewNarrative
    why_it_matters: ReviewNarrative = Field(
        description=(
            "The first sentence must state the evidenced direct or indirect FCV "
            "causal pathway for why this priority matters."
        )
    )
    recommended_action: ReviewNarrative
    target_locator: EvidenceLocator
    recommendation_scale: RecommendationScale
    evidence_ids: tuple[ReviewNarrative, ...] = Field(min_length=1)
    sensitivity: SensitivityCategory
    gap_locus: GapLocus
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
    current_evidence_tier: CurrentEvidenceTier = CurrentEvidenceTier.FULL
    current_evidence_limitation: str | None = None
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

    @model_validator(mode="after")
    def validates_current_evidence_status(self) -> RunMetadata:
        if self.current_evidence_tier is CurrentEvidenceTier.FULL:
            if self.current_evidence_limitation is not None:
                raise ValueError(
                    "current_evidence_limitation must be None for full current evidence."
                )
        elif self.current_evidence_limitation is None or not self.current_evidence_limitation.strip():
            raise ValueError(
                "current_evidence_limitation must be nonblank for reduced or document-led evidence."
            )
        return self


class EvidencePack(FrozenModel):
    metadata: RunMetadata
    evidence: tuple[EvidenceItem, ...]
    diagnostic_entries: tuple[DiagnosticEntry, ...]
    user_corrections: tuple[UserCorrection, ...] = ()
    warnings: tuple[str, ...] = ()


class ReviewResult(FrozenModel):
    metadata: RunMetadata
    overall_read: str
    alignment_readout: str
    strategy_readout: str
    revision_summary: tuple[RevisionSummaryItem, ...]
    priority_areas: tuple[PriorityArea, ...]
    rra_driver_assessments: tuple[RRADriverAssessment, ...] = ()
    fcv_strategy_assessments: tuple[FCVStrategyAssessment, ...]
    institutional_referral_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    document_coverage: DocumentCoverage

    @field_validator("overall_read")
    @classmethod
    def requires_nonblank_overall_read(cls, value: str) -> str:
        return _requires_nonblank_text(value, "Overall read")

    @field_validator("alignment_readout", "strategy_readout")
    @classmethod
    def requires_nonblank_readout(cls, value: str) -> str:
        return _requires_nonblank_text(value, "Review readout")


class ReviewDraft(FrozenModel):
    """Model-authored review content; authoritative run metadata is attached locally."""

    overall_read: ReviewNarrative
    alignment_readout: ReviewNarrative
    strategy_readout: ReviewNarrative
    revision_summary: tuple[RevisionSummaryItem, ...]
    priority_areas: tuple[PriorityArea, ...]
    rra_driver_assessments: tuple[RRADriverAssessment, ...] = ()
    fcv_strategy_assessments: tuple[FCVStrategyAssessment, ...]
    institutional_referral_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    coverage_note: ReviewNarrative

    @field_validator("overall_read", "coverage_note")
    @classmethod
    def requires_nonblank_draft_text(cls, value: str) -> str:
        return _requires_nonblank_text(value, "Review draft text")

    @field_validator("alignment_readout", "strategy_readout")
    @classmethod
    def requires_nonblank_readout(cls, value: str) -> str:
        return _requires_nonblank_text(value, "Review readout")
