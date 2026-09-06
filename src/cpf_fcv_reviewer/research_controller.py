from __future__ import annotations

import logging
import re

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from math import isfinite
from numbers import Real
from random import uniform
from time import monotonic as default_monotonic
from time import sleep as default_sleep
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

from .contracts import CurrentEvidenceTier
from .public_research import (
    MAX_RETAINED_FINDINGS,
    MAX_RETAINED_SOURCES,
    MAX_SOURCE_BUNDLE_CHARACTERS,
    CurrentContextClaim,
    load_research_prompt,
    retain_public_claims,
)

# The gateway owns per-attempt network timeouts; this controller only bounds work between calls.

_CURRENT_FCV_PATTERN = re.compile(
    r"\b(?:conflicts?|violence|violent|elections?|coup|attacks?|fighting|"
    r"militants?|clashes?|armed (?:groups?|conflict|actors?|attacks?|clashes?)|"
    r"unrest|repression|political (?:transition|instability|crisis|tensions?)|"
    r"governance (?:crisis|failure|breakdown|risk)|"
    r"security (?:incidents?|crisis|deterioration|forces?|threats?)|"
    r"military (?:rule|takeover|forces?|operations?)|"
    r"displacement|displaced|refugees?|humanitarian (?:crisis|needs?|emergency|access)|"
    r"land (?:conflict|dispute|tenure)|resource conflict|social cohesion|peacebuilding)\b",
    re.IGNORECASE,
)
_GENERIC_INDICATOR_PATTERN = re.compile(
    r"\b(?:gdp(?: per capita)?|life expectancy|population(?:,? total| growth| estimate)|"
    r"solar capacity)\b",
    re.IGNORECASE,
)
_FCV_CONDITION_PATTERN = re.compile(
    r"\b(?:affect(?:s|ed|ing)?|caus(?:e|es|ed|ing)|delay(?:s|ed|ing)?|"
    r"disrupt(?:s|ed|ing)?|expos(?:e|es|ed|ing)|increas(?:e|es|ed|ing)|"
    r"worsen(?:s|ed|ing)?|(?:conflict|violence|fighting|attacks?)\s+"
    r"(?:(?:has|have|had)\s+)?displaced|(?:was|were|are|have been) displaced|"
    r"threatens?|threatened|escalates?|escalated|deteriorates?|deteriorated|"
    r"declin(?:e|es|ed|ing)|fell|rose|remains?|remained high|continued|intensified|"
    r"erupt(?:s|ed|ing)?|persist(?:s|ed|ing)?|broke out|spread|surged|flared|"
    r"forc(?:e|es|ed|ing)|block(?:s|ed|ing)?|destroy(?:s|ed|ing)?|"
    r"(?:is|are|was|were) widespread|killed|injured|attacked|fled)\b",
    re.IGNORECASE,
)
_GATEWAY_DIAGNOSTIC_KEYS = (
    "source_candidates",
    "source_linked_excerpts",
    "missing_publication_date",
    "untrusted_host_publisher",
    "country_mismatch",
    "normalization_failure",
)

AMBIGUOUS_COUNTRY_QUALIFIERS = {
    "guinea": "Guinea (Conakry) — not Guinea-Bissau, not Equatorial Guinea, not Papua New Guinea",
    "congo": "Republic of the Congo (Brazzaville) — not the Democratic Republic of the Congo",
    "niger": "Niger (Niamey) — not Nigeria",
}

logger = logging.getLogger(__name__)


class ResearchMode(StrEnum):
    RRA_UPDATE = "rra_update"
    HOLISTIC = "holistic"


@dataclass(frozen=True)
class ResearchRequest:
    country: str
    review_date: date
    mode: ResearchMode
    diagnostic_title: str | None = None
    diagnostic_date: date | None = None
    diagnostic_summary: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.country, str) or not self.country.strip():
            raise ValueError("Research country must be nonblank.")
        if type(self.review_date) is not date:
            raise ValueError("Research review date must be a date.")
        if not isinstance(self.mode, ResearchMode):
            raise ValueError("Research mode is invalid.")
        if self.diagnostic_title is not None and not self.diagnostic_title.strip():
            raise ValueError("Diagnostic title must be nonblank when provided.")
        if self.mode is ResearchMode.RRA_UPDATE and (
            self.diagnostic_title is None or self.diagnostic_date is None
        ):
            raise ValueError("RRA update mode requires a diagnostic title and date.")
        if self.mode is ResearchMode.HOLISTIC and (
            self.diagnostic_title is not None or self.diagnostic_date is not None
        ):
            raise ValueError("Holistic mode cannot include RRA metadata.")
        if self.diagnostic_date is not None and type(self.diagnostic_date) is not date:
            raise ValueError("diagnostic date must be a date.")
        if self.diagnostic_date is not None and self.diagnostic_date > self.review_date:
            raise ValueError("Diagnostic date cannot be after the review date.")


@dataclass(frozen=True)
class ResearchResult:
    claims: tuple[CurrentContextClaim, ...]
    rejected: dict[str, str]
    attempts: int
    tier: CurrentEvidenceTier
    limitation: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.tier, CurrentEvidenceTier):
            raise ValueError("Research result tier is invalid.")
        if self.tier is CurrentEvidenceTier.FULL:
            if self.limitation is not None:
                raise ValueError("Full research results cannot include a limitation.")
        elif not isinstance(self.limitation, str) or not self.limitation.strip():
            raise ValueError("Non-full research results require a nonblank limitation.")

    @property
    def sufficient(self) -> bool:
        """Compatibility view for consumers that only need the full-evidence gate."""

        return self.tier is CurrentEvidenceTier.FULL


class ResearchFailure(RuntimeError):
    failure_code = "research_failed"


class ResearchProviderFailure(ResearchFailure):
    failure_code = "research_provider_failed"


class ResearchTimeout(ResearchFailure):
    failure_code = "research_timeout"


class MalformedResearch(ResearchFailure):
    failure_code = "research_malformed"


class ResearchConfigurationError(ResearchFailure):
    failure_code = "research_configuration"


class ResearchSourceRejected(ResearchFailure):
    failure_code = "research_source_rejected"


class InsufficientResearch(ResearchFailure):
    failure_code = "research_insufficient"


class ResearchGateway(Protocol):
    def search(self, prompt: str) -> tuple[CurrentContextClaim, ...]: ...


class RecoveryGateway(Protocol):
    def search(
        self,
        request: ResearchRequest,
        *,
        timeout_seconds: float,
    ) -> tuple[CurrentContextClaim, ...]: ...


Emitter = Callable[[str, dict[str, object]], None]


def _default_jitter(delay: float) -> float:
    return uniform(delay * 0.9, delay * 1.1)


class ResearchController:
    def __init__(
        self,
        gateway: ResearchGateway,
        *,
        recovery_gateway: RecoveryGateway | None = None,
        max_attempts: int = 3,
        minimum_claims: int = 4,
        minimum_publishers: int = 2,
        total_budget_seconds: float = 300.0,
        retry_backoff_seconds: float | Sequence[float] = 1.0,
        monotonic: Callable[[], float] = default_monotonic,
        sleep: Callable[[float], None] = default_sleep,
        jitter: Callable[[float], float] | None = None,
    ) -> None:
        _require_positive_int(max_attempts, "max_attempts")
        _require_positive_int(minimum_claims, "minimum_claims")
        _require_positive_int(minimum_publishers, "minimum_publishers")
        _require_finite_number(total_budget_seconds, "total_budget_seconds", positive=True)
        if isinstance(retry_backoff_seconds, Sequence) and not isinstance(
            retry_backoff_seconds, (str, bytes)
        ):
            backoff = tuple(float(value) for value in retry_backoff_seconds)
            for value in backoff:
                _require_finite_number(value, "retry_backoff_seconds", positive=False)
            self._backoff = backoff or (0.0,)
        else:
            _require_finite_number(retry_backoff_seconds, "retry_backoff_seconds", positive=False)
            self._backoff = (float(retry_backoff_seconds),)
        self.gateway = gateway
        self.recovery_gateway = recovery_gateway
        self.max_attempts = max_attempts
        self.minimum_claims = minimum_claims
        self.minimum_publishers = minimum_publishers
        self.total_budget_seconds = total_budget_seconds
        self.monotonic = monotonic
        self.sleep = sleep
        if jitter is not None and not callable(jitter):
            raise ValueError("jitter must be callable when provided.")
        self.jitter = jitter or _default_jitter

    def run(
        self,
        request: ResearchRequest,
        emit: Emitter,
        *,
        allow_document_led: bool = False,
    ) -> ResearchResult:
        if type(allow_document_led) is not bool:
            raise ValueError("allow_document_led must be a boolean.")
        started = self.monotonic()
        accepted: dict[str, CurrentContextClaim] = {}
        rejected: dict[str, str] = {}
        last_missing: tuple[str, ...] = ()
        last_failure: ResearchFailure | None = None
        budget_exhausted = False
        diagnostics = {key: 0 for key in _GATEWAY_DIAGNOSTIC_KEYS}

        primary_attempts = 0
        for attempt in range(1, self.max_attempts + 1):
            elapsed = self.monotonic() - started
            if attempt > 1 and elapsed >= self.total_budget_seconds:
                budget_exhausted = True
                break
            prompt = self._prompt(request, attempt, last_missing)
            emit(
                "research_attempt",
                self._event_data(attempt, accepted, rejected, elapsed),
            )
            try:
                primary_attempts += 1
                claims = self.gateway.search(prompt)
            except Exception as exc:
                failure = self._classify_exception(exc)
                if isinstance(failure, ResearchConfigurationError):
                    raise failure from None
                last_failure = failure
                if attempt >= self.max_attempts:
                    break
                last_missing = ("provider response",)
                if not self._prepare_retry(attempt, started, last_missing, emit):
                    budget_exhausted = True
                    break
                continue
            finally:
                self._merge_gateway_diagnostics(diagnostics, self.gateway)

            self._merge_claims(claims, accepted, rejected)

            qualifying = self._qualifying_claims(tuple(accepted.values()), request)
            last_missing = self._missing_coverage(qualifying, request)
            elapsed = self.monotonic() - started
            if not last_missing:
                return self._finish(
                    started=started,
                    claims=qualifying,
                    rejected=rejected,
                    attempts=primary_attempts,
                    tier=CurrentEvidenceTier.FULL,
                    limitation=None,
                    route="research_primary" if attempt == 1 else "research_salvaged",
                    emit=emit,
                    event_data=self._event_data(attempt, accepted, rejected, elapsed),
                )
            if qualifying:
                return self._finish(
                    started=started,
                    claims=qualifying,
                    rejected=rejected,
                    attempts=primary_attempts,
                    tier=CurrentEvidenceTier.REDUCED,
                    limitation=self._reduced_limitation(
                        qualifying, last_missing, request
                    ),
                    route="research_reduced",
                    emit=emit,
                    event_data={"missing_coverage": last_missing},
                )
            if attempt < self.max_attempts:
                if not self._prepare_retry(attempt, started, last_missing, emit):
                    budget_exhausted = True
                    break

        remaining = self.total_budget_seconds - (self.monotonic() - started)
        if self.recovery_gateway is not None and remaining > 0:
            recovery_succeeded = False
            try:
                recovery_claims = self.recovery_gateway.search(
                    request, timeout_seconds=remaining
                )
                recovery_succeeded = (
                    self.monotonic() - started < self.total_budget_seconds
                )
            except Exception as exc:
                failure = self._classify_exception(exc)
                if isinstance(failure, ResearchConfigurationError):
                    raise failure from None
                last_failure = failure
            else:
                if recovery_succeeded:
                    self._merge_claims(
                        recovery_claims, accepted, rejected
                    )
            finally:
                budget_exhausted = budget_exhausted or (
                    self.monotonic() - started >= self.total_budget_seconds
                )
            if recovery_succeeded:
                qualifying = self._qualifying_claims(tuple(accepted.values()), request)
                last_missing = self._missing_coverage(qualifying, request)
                emit("research_curated_recovery", {"accepted_count": len(accepted)})
                if not last_missing:
                    return self._finish(
                        started=started,
                        claims=qualifying,
                        rejected=rejected,
                        attempts=primary_attempts,
                        tier=CurrentEvidenceTier.FULL,
                        limitation=None,
                        route="research_curated_recovery",
                        emit=emit,
                        event_data=self._event_data(
                            primary_attempts,
                            accepted,
                            rejected,
                            self.monotonic() - started,
                        ),
                    )

        accepted_claims = self._qualifying_claims(tuple(accepted.values()), request)
        if accepted_claims:
            last_missing = self._missing_coverage(accepted_claims, request)
        budget_exhausted = budget_exhausted or (
            self.monotonic() - started >= self.total_budget_seconds
        )
        if accepted_claims and self._recent_claim_count(accepted_claims, request):
            limitation = self._reduced_limitation(accepted_claims, last_missing, request)
            return self._finish(
                started=started,
                claims=accepted_claims,
                rejected=rejected,
                attempts=primary_attempts,
                tier=CurrentEvidenceTier.REDUCED,
                limitation=limitation,
                route="research_reduced",
                emit=emit,
                event_data={"missing_coverage": last_missing},
            )
        reason = self._document_led_reason(
            budget_exhausted=budget_exhausted,
            last_failure=last_failure,
            rejected=rejected,
        )
        if allow_document_led and not accepted_claims:
            self._emit_diagnostics(
                emit,
                reason=reason,
                diagnostics=diagnostics,
                accepted=accepted,
                rejected=rejected,
            )
            return self._finish(
                started=started,
                claims=(),
                rejected=rejected,
                attempts=primary_attempts,
                tier=CurrentEvidenceTier.DOCUMENT_LED,
                limitation=(
                    "Independent current-country research could not be established; "
                    "review is based primarily on submitted documents."
                ),
                route="research_document_led",
                emit=emit,
                event_data={"reason": reason},
            )
        self._emit_diagnostics(
            emit,
            reason=reason,
            diagnostics=diagnostics,
            accepted=accepted,
            rejected=rejected,
        )
        if budget_exhausted:
            raise ResearchTimeout("Research total budget was exhausted.")
        if last_failure is not None:
            raise last_failure
        if not accepted and rejected:
            raise ResearchSourceRejected("All public research claims were rejected.")
        raise InsufficientResearch("Public research did not meet the sufficiency threshold.")

    def _prepare_retry(
        self,
        attempt: int,
        started: float,
        missing: tuple[str, ...],
        emit: Emitter,
    ) -> bool:
        configured_delay = self._backoff[min(attempt - 1, len(self._backoff) - 1)]
        delay = self.jitter(configured_delay)
        _require_finite_number(delay, "jitter result", positive=False)
        elapsed = self.monotonic() - started
        remaining = self.total_budget_seconds - elapsed
        if remaining <= 0:
            return False
        delay = min(delay, remaining)
        emit(
            "research_retry",
            {"attempt": attempt, "next_attempt": attempt + 1, "missing_coverage": missing},
        )
        self.sleep(delay)
        return True

    @staticmethod
    def _merge_claims(
        claims: tuple[CurrentContextClaim, ...],
        accepted: dict[str, CurrentContextClaim],
        rejected: dict[str, str],
    ) -> None:
        retained, source_rejections = retain_public_claims(tuple(claims))
        rejected.update(source_rejections)
        for item in retained:
            claim_key = item.claim_id.casefold()
            if claim_key in accepted:
                rejected[f"duplicate_id:{item.claim_id}"] = "duplicate claim ID"
            else:
                accepted[claim_key] = item

    def _finish(
        self,
        *,
        started: float,
        claims: tuple[CurrentContextClaim, ...],
        rejected: dict[str, str],
        attempts: int,
        tier: CurrentEvidenceTier,
        limitation: str | None,
        route: str,
        emit: Emitter,
        event_data: dict[str, object],
    ) -> ResearchResult:
        elapsed = self.monotonic() - started
        result = ResearchResult(claims, rejected, attempts, tier, limitation)
        logger.info(
            "research_terminal route=%s duration_seconds=%.3f accepted_count=%d "
            "rejected_count=%d attempts=%d",
            route,
            elapsed,
            len(claims),
            len(rejected),
            attempts,
        )
        if tier is CurrentEvidenceTier.FULL:
            emit("research_sufficient", event_data)
        elif tier is CurrentEvidenceTier.REDUCED:
            emit("research_reduced", event_data)
        else:
            emit("research_document_led", event_data)
        return result

    @staticmethod
    def _merge_gateway_diagnostics(
        diagnostics: dict[str, int],
        gateway: ResearchGateway,
    ) -> None:
        snapshot = getattr(gateway, "last_diagnostics", None)
        if not isinstance(snapshot, Mapping):
            return
        for key in _GATEWAY_DIAGNOSTIC_KEYS:
            value = snapshot.get(key)
            if type(value) is int and value >= 0:
                diagnostics[key] += value

    @classmethod
    def _emit_diagnostics(
        cls,
        emit: Emitter,
        *,
        reason: str,
        diagnostics: dict[str, int],
        accepted: dict[str, CurrentContextClaim],
        rejected: dict[str, str],
    ) -> None:
        counts = dict(diagnostics)
        counts["untrusted_host_publisher"] = max(
            counts["untrusted_host_publisher"],
            sum(
                value == "permitted institutional public source is required"
                for value in rejected.values()
            ),
        )
        counts["non_fcv_background"] = sum(
            not cls._is_substantive_fcv(claim) for claim in accepted.values()
        )
        counts["accepted_sources"] = len(
            {
                _normalize_source_url(claim.source_url or "")
                for claim in accepted.values()
                if _normalize_source_url(claim.source_url or "")
            }
        )
        emit("research_diagnostics", {"reason": reason, "counts": counts})

    @staticmethod
    def _document_led_reason(
        *,
        budget_exhausted: bool,
        last_failure: ResearchFailure | None,
        rejected: dict[str, str],
    ) -> str:
        if budget_exhausted:
            return "budget_exhausted"
        if isinstance(last_failure, ResearchTimeout):
            return "provider_timeout"
        if isinstance(last_failure, MalformedResearch):
            return "malformed_response"
        if last_failure is not None and not isinstance(last_failure, ResearchSourceRejected):
            return "provider_failure"
        if isinstance(last_failure, ResearchSourceRejected) or rejected:
            return "source_rejected"
        return "insufficient_coverage"

    def _qualifying_claims(
        self,
        claims: tuple[CurrentContextClaim, ...],
        request: ResearchRequest,
    ) -> tuple[CurrentContextClaim, ...]:
        graded = tuple(
            claim.model_copy(
                update={
                    "verification": _cap_verification_by_recency(
                        claim.verification,
                        is_recent=self._is_recent(claim, request),
                    )
                }
            )
            for claim in claims
        )
        qualifying = sorted(
            (
                claim
                for claim in graded
                if self._is_recent(claim, request)
                and self._is_substantive_fcv(claim)
            ),
            key=lambda claim: (-claim.source_date.toordinal(), claim.claim_id),
        )
        retained: list[CurrentContextClaim] = []
        source_urls: set[str] = set()
        bundle_characters = 0
        for claim in qualifying:
            source_url = _normalize_source_url(claim.source_url or "")
            if source_url not in source_urls and len(source_urls) >= MAX_RETAINED_SOURCES:
                continue
            claim_characters = len(claim.model_dump_json())
            if bundle_characters + claim_characters > MAX_SOURCE_BUNDLE_CHARACTERS:
                continue
            retained.append(claim)
            source_urls.add(source_url)
            bundle_characters += claim_characters
            if len(retained) >= MAX_RETAINED_FINDINGS:
                break
        return tuple(retained)

    @staticmethod
    def _is_substantive_fcv(claim: CurrentContextClaim) -> bool:
        grounded_text = claim.supporting_quote or ""
        return bool(
            _CURRENT_FCV_PATTERN.search(grounded_text)
            and _FCV_CONDITION_PATTERN.search(grounded_text)
            and _GENERIC_INDICATOR_PATTERN.search(grounded_text) is None
        )

    def _recent_claim_count(
        self,
        claims: tuple[CurrentContextClaim, ...],
        request: ResearchRequest,
    ) -> int:
        return sum(1 for claim in claims if self._is_recent(claim, request))

    def _reduced_limitation(
        self,
        claims: tuple[CurrentContextClaim, ...],
        missing: tuple[str, ...],
        request: ResearchRequest,
    ) -> str:
        recent_claims = tuple(
            claim for claim in claims if self._is_recent(claim, request)
        )
        recent_count = len(recent_claims)
        source_count = len(
            {
                _normalize_source_url(claim.source_url)
                for claim in recent_claims
                if claim.source_url
            }
        )
        publisher_count = len(
            {claim.publisher.strip().casefold() for claim in recent_claims}
        )
        observation_word = "observation" if recent_count == 1 else "observations"
        url_word = "URL" if source_count == 1 else "URLs"
        publisher_word = "publisher" if publisher_count == 1 else "publishers"
        recent_count_word = "one" if recent_count == 1 else str(recent_count)
        source_count_word = "one" if source_count == 1 else str(source_count)
        publisher_count_word = "one" if publisher_count == 1 else str(publisher_count)
        verb = "was" if recent_count == 1 else "were"
        labels = {
            "claims": "the minimum number of claims",
            "publishers": "publisher diversity",
            "structural_dynamic": "structural dynamics",
            "current_development": "current developments",
            "recent": "recent evidence",
        }
        gaps = ", ".join(labels.get(item, item) for item in missing)
        return (
            f"{recent_count_word} recent {observation_word} across {source_count_word} "
            f"distinct {url_word} and {publisher_count_word} originating "
            f"{publisher_word} {verb} established; "
            "this is sufficient for a reduced current update, while broader "
            f"coverage remains unavailable for {gaps}."
        )

    def _prompt(
        self,
        request: ResearchRequest,
        attempt: int,
        missing: tuple[str, ...],
    ) -> str:
        lines = [
            load_research_prompt().strip(),
            f"research_mode: {request.mode.value}",
            f"country: {request.country.strip()}",
            *(
                [f"country_disambiguation: {qualifier}"]
                if (
                    qualifier := AMBIGUOUS_COUNTRY_QUALIFIERS.get(
                        " ".join(request.country.casefold().split())
                    )
                )
                else []
            ),
            f"review_date: {request.review_date.isoformat()}",
        ]
        if request.mode is ResearchMode.RRA_UPDATE:
            if attempt == 1:
                lines.append("diagnostic_target: the named RRA or diagnostic")
            lines.extend(
                (
                    f"diagnostic_date: {request.diagnostic_date.isoformat()}",
                    (
                        "Focus on the diagnostic date-to-review date gap and re-test "
                        "material structural findings."
                    ),
                    f"diagnostic_summary: {request.diagnostic_summary.strip()}",
                )
            )
        else:
            lines.append("Cover structural dynamics and current developments separately.")
            lines.append("Use a bounded recent window of 24 months through the review date.")
        if attempt > 1:
            labels = ", ".join(missing)
            lines.append(f"Retry attempt {attempt}: missing coverage: {labels}.")
            lines.append("Shift source emphasis toward authoritative sources not yet represented.")
            if {"structural_dynamic", "current_development"}.intersection(missing):
                if request.mode is ResearchMode.RRA_UPDATE:
                    target = "the named RRA or diagnostic"
                else:
                    target = "the current-country question"
                lines.append(
                    "Seek missing non-economic governance, conflict, institutional, "
                    f"security, social, or service-delivery evidence relevant to {target}."
                )
                lines.append(
                    "Do not return additional evidence focused on already-covered "
                    "economic themes."
                )
        return "\n".join(lines)

    def _missing_coverage(
        self,
        claims: tuple[CurrentContextClaim, ...],
        request: ResearchRequest,
    ) -> tuple[str, ...]:
        claims = tuple(
            claim for claim in claims if claim.verification != "unverified"
        )
        missing: list[str] = []
        if len(claims) < self.minimum_claims:
            missing.append("claims")
        publishers = {
            claim.publisher.strip().casefold()
            for claim in claims
            if claim.publisher.strip()
        }
        if len(publishers) < self.minimum_publishers:
            missing.append("publishers")
        kinds = {claim.context_kind for claim in claims}
        if "structural_dynamic" not in kinds:
            missing.append("structural_dynamic")
        if "current_development" not in kinds:
            missing.append("current_development")
        if not any(self._is_recent(claim, request) for claim in claims):
            missing.append("recent")
        return tuple(missing)

    @staticmethod
    def _is_recent(claim: CurrentContextClaim, request: ResearchRequest) -> bool:
        if claim.source_date is None:
            return False
        window_start = _subtract_calendar_years(request.review_date, 2)
        if not window_start <= claim.source_date <= request.review_date:
            return False
        return bool(
            request.mode is not ResearchMode.RRA_UPDATE
            or request.diagnostic_date < claim.source_date
        )

    @staticmethod
    def _event_data(
        attempt: int,
        accepted: dict[str, CurrentContextClaim],
        rejected: dict[str, str],
        elapsed: float,
    ) -> dict[str, object]:
        kinds = {claim.context_kind for claim in accepted.values()}
        publishers = {
            claim.publisher.strip().casefold()
            for claim in accepted.values()
            if claim.publisher.strip()
        }
        return {
            "attempt": attempt,
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "publisher_count": len(publishers),
            "missing_coverage": tuple(
                label
                for label, present in (
                    ("structural_dynamic", "structural_dynamic" in kinds),
                    ("current_development", "current_development" in kinds),
                )
                if not present
            ),
            "elapsed_seconds": round(elapsed, 3),
        }

    @staticmethod
    def _classify_exception(exc: Exception) -> ResearchFailure:
        if isinstance(
            exc,
            (
                ArithmeticError,
                AssertionError,
                AttributeError,
                LookupError,
                NameError,
                NotImplementedError,
                TypeError,
            ),
        ):
            raise exc
        if isinstance(exc, ResearchFailure):
            return exc
        # Surface the real provider error (swallowed until now) so live-web
        # research failures are diagnosable from logs instead of only appearing
        # as an opaque terminal "provider_failure".
        logger.warning(
            "research_provider_exception error_type=%s status_code=%s detail=%s",
            type(exc).__name__,
            getattr(exc, "status_code", None),
            str(exc)[:400],
        )
        if getattr(exc, "status_code", None) in {401, 403}:
            return ResearchConfigurationError("Public research configuration failed.")
        if isinstance(exc, TimeoutError):
            return ResearchTimeout("Public research timed out.")
        if isinstance(exc, ValueError):
            return MalformedResearch("Public research response was malformed.")
        if isinstance(exc, (OSError, RuntimeError)) or getattr(exc, "status_code", None):
            return ResearchProviderFailure("Public research provider failed.")
        raise exc


def _require_positive_int(value: object, name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer.")


def _require_finite_number(value: object, name: str, *, positive: bool) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number.")
    if value < 0 or (positive and value <= 0):
        requirement = "positive" if positive else "nonnegative"
        raise ValueError(f"{name} must be {requirement}.")


def _normalize_source_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.casefold()
    hostname = (parsed.hostname or "").rstrip(".").casefold()
    try:
        port = parsed.port
    except ValueError:
        return url.strip().casefold()
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = hostname if not port or default_port else f"{hostname}:{port}"
    path = parsed.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def _cap_verification_by_recency(verification: str, *, is_recent: bool) -> str:
    if not is_recent:
        return "unverified"
    return verification


def _subtract_calendar_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        return value.replace(year=value.year - years, day=28)
