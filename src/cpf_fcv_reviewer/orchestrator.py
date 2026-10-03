from __future__ import annotations

from collections import Counter
from collections.abc import Callable

from .extraction import (
    DiagnosticCoverageUnavailable,
    DocumentTooLarge,
    DocumentUnreadable,
    PackageCoverageUnavailable,
    ReviewCoverageUnavailable,
)
from .model_gateway import ModelOutputUnavailable
from .registry import RegistryUnavailable
from .research_controller import ResearchFailure
from .review_engine import ReviewSchemaUnavailable
from .source_grounding import LOCATOR_FAILURE_REASONS, QUOTE_FAILURE_REASONS

Emitter = Callable[[str, dict], None]
Step = Callable[[dict], dict]
Repair = Callable[[dict, list], dict]

SAFE_FAILURES = {
    TimeoutError: "model_timeout",
    DiagnosticCoverageUnavailable: "diagnostic_coverage_unavailable",
    ReviewCoverageUnavailable: "review_coverage_unavailable",
    PackageCoverageUnavailable: "package_coverage_unavailable",
    RegistryUnavailable: "registry_unavailable",
    DocumentUnreadable: "document_unreadable",
    DocumentTooLarge: "document_too_large",
}


def safe_failure_code(error: Exception) -> str:
    if isinstance(error, ModelOutputUnavailable):
        return error.failure_code
    if isinstance(error, ReviewSchemaUnavailable):
        return error.failure_code
    if isinstance(error, ResearchFailure):
        return error.failure_code
    for error_type, code in SAFE_FAILURES.items():
        if isinstance(error, error_type):
            return code
    return "review_failed"


def safe_failure_data(error: Exception) -> dict[str, object]:
    data: dict[str, object] = {"error": safe_failure_code(error)}
    if isinstance(error, ReviewSchemaUnavailable):
        data["schema_diagnostics"] = error.safe_diagnostics
    return data


class ReviewOrchestrator:
    def __init__(
        self,
        *,
        steps: tuple[tuple[str, Step], ...],
        repair: Repair,
    ) -> None:
        self.steps = steps
        self.repair = repair

    def run(self, context: dict, emit: Emitter) -> dict:
        repaired = False
        original_context = context
        context["_emit"] = emit
        try:
            for name, step in self.steps:
                emit("step_start", {"step": name})
                context = step(context)
                if name == "validate" and context.get("validation_issues"):
                    def is_advisory(issue):
                        return (
                            isinstance(issue, dict)
                            and issue.get("severity") == "advisory"
                        )

                    def codes_of(issues):
                        return list(
                            dict.fromkeys(
                                issue["code"]
                                for issue in issues
                                if isinstance(issue, dict)
                                and isinstance(issue.get("code"), str)
                            )
                        )

                    def validation_data(issues):
                        data = {"issue_count": len(issues), "codes": codes_of(issues)}
                        reasons = Counter(
                            issue["locator_reason"]
                            for issue in issues
                            if isinstance(issue, dict)
                            and issue.get("code") == "target_locator_mismatch"
                            and isinstance(issue.get("locator_reason"), str)
                            and issue["locator_reason"] in LOCATOR_FAILURE_REASONS
                        )
                        if reasons:
                            data["locator_diagnostics"] = [
                                {"reason": reason, "count": count}
                                for reason, count in sorted(reasons.items())
                            ]
                        quote_reasons = Counter(
                            issue["quote_reason"] for issue in issues
                            if isinstance(issue, dict)
                            and issue.get("code") == "unsupported_cpf_response"
                            and isinstance(issue.get("quote_reason"), str)
                            and issue["quote_reason"] in QUOTE_FAILURE_REASONS
                        )
                        if quote_reasons:
                            data["quote_diagnostics"] = [
                                {"reason": reason, "count": count}
                                for reason, count in sorted(quote_reasons.items())
                            ]
                        return data

                    all_issues = list(context["validation_issues"])
                    fatal_issues = [i for i in all_issues if not is_advisory(i)]
                    advisory_issues = [i for i in all_issues if is_advisory(i)]
                    if advisory_issues:
                        emit(
                            "advisory_notice",
                            {
                                "issue_count": len(advisory_issues),
                                "codes": codes_of(advisory_issues),
                            },
                        )
                    if fatal_issues:
                        if repaired:
                            raise ValueError("Validation failed after the only repair.")
                        emit(
                            "repair_start",
                            validation_data(fatal_issues),
                        )
                        context = self.repair(context, fatal_issues)
                        repaired = True
                        remaining_fatal = [
                            i
                            for i in context.get("validation_issues", [])
                            if not is_advisory(i)
                        ]
                        if remaining_fatal:
                            emit(
                                "repair_failed",
                                validation_data(remaining_fatal),
                            )
                            raise ValueError("Validation failed after the only repair.")
                emit("step_complete", {"step": name})
            emit("run_complete", {"repair_count": int(repaired)})
            return context
        except Exception as exc:
            context.clear()
            context["status"] = "failed"
            emit("run_failed", safe_failure_data(exc))
            raise
        finally:
            original_context.pop("_emit", None)
            context.pop("_emit", None)
