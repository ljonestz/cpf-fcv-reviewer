"""Deterministic, provider-free services for local browser smoke testing."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from .contracts import (
    AssessmentConfidence,
    AssessmentStatus,
    DiagnosticEntry,
    DiagnosticMap,
    DiagnosticMode,
    EvidenceLocator,
    FCVStrategicShift,
    FCVStrategyAssessment,
    GapLocus,
    PriorityArea,
    RecommendationScale,
    RRADriverAssessment,
    ReviewDraft,
    RevisionSummaryItem,
    SensitivityCategory,
)
from .research_controller import ResearchMode, ResearchRequest
from .runtime import build_runtime_services

SMOKE_REVIEW_DATE = date(2026, 8, 14)
SMOKE_MARKER = "[SYNTHETIC SMOKE]"
SMOKE_STRATEGY_ENTRY_IDS = {
    FCVStrategicShift.ANTICIPATE_BETTER: "registry-SYN-PUB-FCV-STRAT-001",
    FCVStrategicShift.DIFFERENTIATED_APPROACH: "registry-SYN-PUB-FCV-STRAT-002",
    FCVStrategicShift.ONE_WBG_JOBS: "registry-SYN-PUB-FCV-STRAT-003",
    FCVStrategicShift.TOOLKIT_PARTNERSHIPS_STAFFING: (
        "registry-SYN-PUB-FCV-STRAT-004"
    ),
}


def _country_slug(country: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", country.casefold()).strip("-")
    return slug or "country"


def _prompt_date(prompt: str, label: str, fallback: date) -> date:
    match = re.search(rf"^{label}:\s*(\d{{4}}-\d{{2}}-\d{{2}})\s*$", prompt, re.MULTILINE)
    if match is None:
        return fallback
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return fallback


class SmokeFollowOnGateway:
    """Stream a clearly labelled provider-free response for local UI QA."""

    def stream(self, *, review, evidence, history, message):
        del review, evidence, history, message
        yield f"{SMOKE_MARKER} Draft follow-on response. "
        yield "Use the completed review and cited evidence when refining this text."


class SmokeResearchGateway:
    """Return only clearly labelled synthetic claims for local QA."""

    def search(self, request_or_prompt: ResearchRequest | str):
        if isinstance(request_or_prompt, ResearchRequest):
            country = request_or_prompt.country.strip()
            review_date = request_or_prompt.review_date
            mode = request_or_prompt.mode
            diagnostic_date = request_or_prompt.diagnostic_date
        elif isinstance(request_or_prompt, str):
            country_match = re.search(r"^country:\s*(.+?)\s*$", request_or_prompt, re.MULTILINE)
            country = country_match.group(1).strip() if country_match else "Benin"
            review_date = _prompt_date(request_or_prompt, "review_date", SMOKE_REVIEW_DATE)
            diagnostic_date = _prompt_date(request_or_prompt, "diagnostic_date", date.min)
            mode = (
                ResearchMode.RRA_UPDATE
                if "research_mode: rra_update" in request_or_prompt
                else ResearchMode.HOLISTIC
            )
        else:
            raise TypeError("Smoke research requires a ResearchRequest or prompt string.")

        offsets = (180, 90, 30, 7)
        if mode is ResearchMode.RRA_UPDATE and diagnostic_date != date.min:
            dates = tuple(
                max(diagnostic_date + timedelta(days=1), review_date - timedelta(days=offset))
                for offset in offsets
            )
        else:
            dates = tuple(review_date - timedelta(days=offset) for offset in offsets)

        slug = _country_slug(country)
        publishers = ("World Bank", "World Bank", "United Nations", "United Nations")
        kinds = (
            "structural_dynamic",
            "structural_dynamic",
            "current_development",
            "current_development",
        )
        hosts = ("www.worldbank.org", "www.worldbank.org", "www.un.org", "www.un.org")
        claims = []
        for index, (source_date, publisher, context_kind, host) in enumerate(
            zip(dates, publishers, kinds, hosts, strict=True),
            start=1,
        ):
            claims.append(
                self._claim(
                    index=index,
                    country=country,
                    slug=slug,
                    source_date=source_date,
                    publisher=publisher,
                    context_kind=context_kind,
                    host=host,
                )
            )
        return tuple(claims)

    @staticmethod
    def _claim(
        *,
        index: int,
        country: str,
        slug: str,
        source_date: date,
        publisher: str,
        context_kind: str,
        host: str,
    ):
        from .public_research import CurrentContextClaim

        text = (
            f"{SMOKE_MARKER} Synthetic fixture {index} reports increased political "
            f"violence and conflict conditions in {country} as {context_kind} context; "
            "it is not real evidence."
        )
        return CurrentContextClaim(
            claim_id=f"smoke-{index:03d}",
            text=text,
            publisher=publisher,
            source_title=f"{SMOKE_MARKER} {publisher} local-QA fixture {index}",
            source_url=f"https://{host}/synthetic-smoke/{slug}/claim-{min(index, 3)}",
            source_date=source_date,
            supporting_quote=text,
            source_type="public synthetic smoke fixture",
            relevance="Synthetic local-QA fixture only; not a production research source.",
            context_kind=context_kind,
            relationship="establishes",
            licensed_data_required=False,
            verification="verified",
        )


class SmokeModelGateway:
    """Build deterministic review drafts from evidence IDs supplied by the app."""

    def generate(self, *, prompt_name: str, payload: dict, output_type: type[Any]):
        if output_type is DiagnosticMap:
            if prompt_name != "diagnostic_map":
                raise ValueError("Smoke diagnostic mapping requires the diagnostic_map prompt.")
            evidence = payload.get("evidence", ())
            evidence_ids = tuple(
                item["evidence_id"]
                for item in evidence
                if isinstance(item, dict)
                and isinstance(item.get("evidence_id"), str)
            )
            if not evidence_ids:
                raise ValueError("Smoke diagnostic mapping requires supplied page IDs.")
            return DiagnosticMap(
                entries=(
                    DiagnosticEntry(
                        entry_id="smoke-diagnostic-map",
                        short_name=f"{SMOKE_MARKER} Uploaded diagnostic map",
                        group="principal_driver",
                        materiality="high",
                        source_evidence_ids=evidence_ids,
                        grouping_rationale=(
                            f"{SMOKE_MARKER} Synthetic mapping covers every supplied "
                            "extractable diagnostic page."
                        ),
                    ),
                )
            )
        if output_type is not ReviewDraft:
            raise ValueError("Smoke model only supports ReviewDraft output.")
        if prompt_name == "repair":
            # Deterministic repair validates and preserves the supplied draft
            # while exercising the provider-free repair path.
            draft = payload.get("draft")
            if not isinstance(draft, dict):
                raise ValueError("Smoke repair requires a supplied draft.")
            return ReviewDraft.model_validate(draft)

        evidence_ids, target_locator = self._evidence_inputs(payload)
        if not evidence_ids or target_locator is None:
            raise ValueError("Smoke model requires supplied evidence IDs and a target locator.")

        current_id = next(
            (evidence_id for evidence_id in evidence_ids if evidence_id.startswith("current-")),
            None,
        )
        cited_ids = tuple(dict.fromkeys((evidence_ids[0], current_id or evidence_ids[0])))
        allowed_scales = payload.get("stage_profile", {}).get("allowed_scales", ())
        scale_value = (
            allowed_scales[0]
            if allowed_scales
            else RecommendationScale.TARGETED_EDIT.value
        )
        scale = RecommendationScale(scale_value)
        locator = EvidenceLocator.model_validate(target_locator)
        comment_reference = (
            f"{SMOKE_MARKER} Synthetic comment fixture"
            if scale is RecommendationScale.COMMENT_RESPONSE
            else None
        )
        registry_ids = tuple(
            evidence_id
            for evidence_id in evidence_ids
            if "PUB-FCV-STRAT-" in evidence_id
        )
        expected_registry_ids = tuple(SMOKE_STRATEGY_ENTRY_IDS.values())
        if (
            len(registry_ids) != len(expected_registry_ids)
            or set(registry_ids) != set(expected_registry_ids)
        ):
            raise ValueError("Smoke model requires all four synthetic Strategy entries.")
        pack = payload.get("evidence_pack", {})
        metadata = pack.get("metadata", {}) if isinstance(pack, dict) else {}
        diagnostic_mode = DiagnosticMode(
            metadata.get("diagnostic_mode", DiagnosticMode.LIMITED_FRAMING.value)
        )
        rra_assessments = (
            (
                RRADriverAssessment(
                    assessment_id="smoke-rra-1",
                    driver=f"{SMOKE_MARKER} Synthetic territorial exclusion driver",
                    cpf_response=f"{SMOKE_MARKER} Synthetic CPF response",
                    delivery_mechanism=f"{SMOKE_MARKER} Synthetic delivery mechanism",
                    result_or_indicator=f"{SMOKE_MARKER} Synthetic access indicator",
                    remaining_gap=f"{SMOKE_MARKER} Synthetic adaptation trigger gap",
                    status=AssessmentStatus.PARTIALLY_ALIGNED,
                    confidence=AssessmentConfidence.MEDIUM,
                    gap_locus=GapLocus.MONITORING_ADAPTATION,
                    evidence_ids=cited_ids,
                ),
            )
            if diagnostic_mode is DiagnosticMode.RRA_ALIGNMENT
            else ()
        )
        strategy_assessments = tuple(
            FCVStrategyAssessment(
                assessment_id=f"smoke-strategy-{shift.value}",
                strategic_shift=shift,
                assessment=(
                    f"{SMOKE_MARKER} Synthetic assessment of the {shift.value} "
                    "strategic shift."
                ),
                status=AssessmentStatus.NOT_ASSESSABLE,
                confidence=AssessmentConfidence.MEDIUM,
                gap_locus=None,
                evidence_ids=tuple(
                    dict.fromkeys((registry_id, *cited_ids))
                ),
            )
            for shift, registry_id in SMOKE_STRATEGY_ENTRY_IDS.items()
        )

        return ReviewDraft(
            overall_read=(
                f"{SMOKE_MARKER} The synthetic review completed using only the "
                "supplied evidence identifiers and synthetic fixture metadata."
            ),
            alignment_readout=(
                f"{SMOKE_MARKER} The submitted draft can be tested against the supplied "
                "synthetic context without relying on an external provider."
            ),
            strategy_readout=(
                f"{SMOKE_MARKER} The CPF advances prevention and jobs. "
                "Operational differentiation remains incomplete."
            ),
            revision_summary=(
                RevisionSummaryItem(
                    priority_area_id="smoke-pa-1",
                    title=f"{SMOKE_MARKER} Clarify the delivery logic",
                ),
            ),
            priority_areas=(
                PriorityArea(
                    priority_area_id="smoke-pa-1",
                    heading=f"{SMOKE_MARKER} Strengthen the delivery logic",
                    assessment=(
                        f"{SMOKE_MARKER} Political violence creates a direct risk of "
                        "service disruption, while the synthetic delivery logic remains "
                        "implicit in the supplied primary evidence."
                    ),
                    why_it_matters=(
                        f"{SMOKE_MARKER} This direct FCV pathway demonstrates evidence-linked "
                        "review output and why adaptive delivery matters."
                    ),
                    recommended_action=f"{SMOKE_MARKER} Clarify the delivery logic.",
                    target_locator=locator,
                    recommendation_scale=scale,
                    evidence_ids=cited_ids,
                    sensitivity=SensitivityCategory.CAUTIOUS,
                    gap_locus=GapLocus.DELIVERY_ARRANGEMENTS,
                    comment_reference=comment_reference,
                ),
            ),
            rra_driver_assessments=rra_assessments,
            fcv_strategy_assessments=strategy_assessments,
            institutional_referral_ids=(),
            limitations=(
                f"{SMOKE_MARKER} Output is synthetic local-QA content and is not real evidence.",
            ),
            coverage_note=(
                f"{SMOKE_MARKER} Coverage is limited to the supplied synthetic primary "
                "document and synthetic current-context claims."
            ),
        )

    @staticmethod
    def _evidence_inputs(payload: dict) -> tuple[tuple[str, ...], dict | None]:
        pack = payload.get("evidence_pack")
        if isinstance(pack, dict):
            entries = pack.get("evidence", ())
            ids = tuple(
                item["evidence_id"]
                for item in entries
                if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
            )
            primary = next(
                (
                    item
                    for item in entries
                    if isinstance(item, dict)
                    and item.get("document_role") == "primary"
                    and isinstance(item.get("locator"), dict)
                ),
                None,
            )
            return ids, primary.get("locator") if primary else None

        draft = payload.get("draft")
        if not isinstance(draft, dict):
            return (), None
        areas = draft.get("priority_areas", ())
        if not areas or not isinstance(areas[0], dict):
            return (), None
        area = areas[0]
        ids = tuple(item for item in area.get("evidence_ids", ()) if isinstance(item, str))
        locator = area.get("target_locator")
        return ids, locator if isinstance(locator, dict) else None


def build_smoke_services(config: dict) -> dict:
    """Build the smoke app's isolated gateway/controller/orchestrator services."""
    return build_runtime_services(
        config,
        model_gateway=SmokeModelGateway(),
        research_gateway=SmokeResearchGateway(),
        follow_on_gateway=SmokeFollowOnGateway(),
        review_date_provider=lambda: SMOKE_REVIEW_DATE,
    )
