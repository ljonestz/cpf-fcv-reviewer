from __future__ import annotations

from collections.abc import Callable

from .extraction import (
    DiagnosticCoverageUnavailable,
    DocumentUnreadable,
    PackageCoverageUnavailable,
)
from .review_engine import ReviewSchemaUnavailable
from .registry import RegistryUnavailable
from .research_controller import ResearchFailure

Emitter = Callable[[str, dict], None]
Step = Callable[[dict], dict]
Repair = Callable[[dict, list], dict]

SAFE_FAILURES = {
    TimeoutError: "model_timeout",
    DiagnosticCoverageUnavailable: "diagnostic_coverage_unavailable",
    PackageCoverageUnavailable: "package_coverage_unavailable",
    RegistryUnavailable: "registry_unavailable",
    DocumentUnreadable: "document_unreadable",
}


def safe_failure_code(error: Exception) -> str:
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
                    all_issues = list(context["validation_issues"])
                    fatal_issues = [
                        issue
                        for issue in all_issues
                        if not (
                            isinstance(issue, dict)
                            and issue.get("severity") == "advisory"
                        )
                    ]
                    advisory_issues = [
                        issue
                        for issue in all_issues
                        if isinstance(issue, dict)
                        and issue.get("severity") == "advisory"
                    ]
                    if advisory_issues:
                        emit(
                            "advisory_notice",
                            {
                                "issue_count": len(advisory_issues),
                                "codes": list(
                                    dict.fromkeys(
                                        issue["code"]
                                        for issue in advisory_issues
                                        if isinstance(issue, dict)
                                        and isinstance(issue.get("code"), str)
                                    )
                                ),
                            },
                        )
                    if fatal_issues:
                        if repaired:
                            raise ValueError("Validation failed after the only repair.")
                        emit(
                            "repair_start",
                            {
                                "issue_count": len(fatal_issues),
                                "codes": list(
                                    dict.fromkeys(
                                        issue["code"]
                                        for issue in fatal_issues
                                        if isinstance(issue, dict)
                                        and isinstance(issue.get("code"), str)
                                    )
                                ),
                            },
                        )
                        context = self.repair(context, fatal_issues)
                        repaired = True
                        remaining_fatal = [
                            issue
                            for issue in context.get("validation_issues", [])
                            if not (
                                isinstance(issue, dict)
                                and issue.get("severity") == "advisory"
                            )
                        ]
                        if remaining_fatal:
                            emit(
                                "repair_failed",
                                {
                                    "issue_count": len(remaining_fatal),
                                    "codes": list(
                                        dict.fromkeys(
                                            issue["code"]
                                            for issue in remaining_fatal
                                            if isinstance(issue, dict)
                                            and isinstance(issue.get("code"), str)
                                        )
                                    ),
                                },
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
