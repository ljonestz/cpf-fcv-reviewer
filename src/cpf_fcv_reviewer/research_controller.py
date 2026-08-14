from __future__ import annotations

import logging

from collections.abc import Callable, Sequence
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
    CurrentContextClaim,
    load_research_prompt,
    retain_public_claims,
)

# The gateway owns per-attempt network timeouts; this controller only bounds work between calls.


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
    def search(self, request: ResearchRequest) -> tuple[CurrentContextClaim, ...]: ...


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
        accepted_urls: set[str] = set()
        rejected: dict[str, str] = {}
        last_missing: tuple[str, ...] = ()
        last_failure: ResearchFailure | None = None

        primary_attempts = 0
        for attempt in range(1, self.max_attempts + 1):
            primary_attempts = attempt
            elapsed = self.monotonic() - started
            if attempt > 1 and elapsed >= self.total_budget_seconds:
                raise ResearchTimeout("Research total budget was exhausted.")
            prompt = self._prompt(request, attempt, last_missing)
            emit(
                "research_attempt",
                self._event_data(attempt, accepted, rejected, elapsed),
            )
            try:
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
                    raise ResearchTimeout("Research total budget was exhausted.") from None
                continue

            self._merge_claims(claims, accepted, accepted_urls, rejected)

            last_missing = self._missing_coverage(tuple(accepted.values()), request)
            elapsed = self.monotonic() - started
            if not last_missing:
                return self._finish(
                    started=started,
                    claims=tuple(accepted.values()),
                    rejected=rejected,
                    attempts=attempt,
                    tier=CurrentEvidenceTier.FULL,
                    limitation=None,
                    route="research_primary" if attempt == 1 else "research_salvaged",
                    emit=emit,
                    event_data=self._event_data(attempt, accepted, rejected, elapsed),
                )
            if attempt < self.max_attempts:
                if not self._prepare_retry(attempt, started, last_missing, emit):
                    raise ResearchTimeout("Research total budget was exhausted.")

        if (
            self.recovery_gateway is not None
            and self.monotonic() - started < self.total_budget_seconds
        ):
            recovery_succeeded = False
            try:
                recovery_claims = self.recovery_gateway.search(request)
                recovery_succeeded = True
            except Exception as exc:
                failure = self._classify_exception(exc)
                if isinstance(failure, ResearchConfigurationError):
                    raise failure from None
            else:
                self._merge_claims(recovery_claims, accepted, accepted_urls, rejected)
            if recovery_succeeded:
                last_missing = self._missing_coverage(tuple(accepted.values()), request)
                emit("research_curated_recovery", {"accepted_count": len(accepted)})
                if not last_missing:
                    return self._finish(
                        started=started,
                        claims=tuple(accepted.values()),
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

        if accepted:
            accepted_claims = tuple(accepted.values())
            last_missing = self._missing_coverage(accepted_claims, request)
        else:
            accepted_claims = ()
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
        if allow_document_led and not accepted:
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
                event_data={"reason": "independent_evidence_unavailable"},
            )
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
        accepted_urls: set[str],
        rejected: dict[str, str],
    ) -> None:
        retained, source_rejections = retain_public_claims(tuple(claims))
        rejected.update(source_rejections)
        for item in retained:
            claim_key = item.claim_id.casefold()
            url_key = _normalize_source_url(item.source_url or "")
            if claim_key in accepted:
                rejected[f"duplicate_id:{item.claim_id}"] = "duplicate claim ID"
            elif url_key in accepted_urls:
                rejected["duplicate_url"] = "duplicate source URL"
            else:
                accepted[claim_key] = item
                accepted_urls.add(url_key)

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
        recent_count = self._recent_claim_count(claims, request)
        source_word = "source" if recent_count == 1 else "sources"
        count_word = "one" if recent_count == 1 else str(recent_count)
        labels = {
            "claims": "the minimum number of claims",
            "publishers": "publisher diversity",
            "structural_dynamic": "structural dynamics",
            "current_development": "current developments",
            "recent": "recent evidence",
        }
        gaps = ", ".join(labels.get(item, item) for item in missing)
        return (
            f"Only {count_word} public {source_word} was established recently; "
            f"current-country coverage remains incomplete for {gaps}."
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
            f"review_date: {request.review_date.isoformat()}",
        ]
        if request.mode is ResearchMode.RRA_UPDATE:
            lines.extend(
                (
                    f"diagnostic_title: {request.diagnostic_title}",
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
        return "\n".join(lines)

    def _missing_coverage(
        self,
        claims: tuple[CurrentContextClaim, ...],
        request: ResearchRequest,
    ) -> tuple[str, ...]:
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
        if request.mode is ResearchMode.RRA_UPDATE:
            return request.diagnostic_date < claim.source_date <= request.review_date
        window_start = _subtract_calendar_years(request.review_date, 2)
        return window_start <= claim.source_date <= request.review_date

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
        if isinstance(exc, (AssertionError, AttributeError, NameError, TypeError)):
            raise exc
        if isinstance(exc, ResearchConfigurationError):
            return exc
        if getattr(exc, "status_code", None) in {401, 403}:
            return ResearchConfigurationError("Public research configuration failed.")
        if isinstance(exc, TimeoutError):
            return ResearchTimeout("Public research timed out.")
        if isinstance(exc, ValueError):
            return MalformedResearch("Public research response was malformed.")
        return ResearchProviderFailure("Public research provider failed.")


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
    hostname = (parsed.hostname or "").casefold()
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


def _subtract_calendar_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        return value.replace(year=value.year - years, day=28)
