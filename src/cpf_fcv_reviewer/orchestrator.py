from __future__ import annotations

from collections.abc import Callable

from .extraction import DocumentUnreadable
from .registry import RegistryUnavailable

Emitter = Callable[[str, dict], None]
Step = Callable[[dict], dict]
Repair = Callable[[dict, list], dict]

SAFE_FAILURES = {
    TimeoutError: "model_timeout",
    RegistryUnavailable: "registry_unavailable",
    DocumentUnreadable: "document_unreadable",
}


def safe_failure_code(error: Exception) -> str:
    for error_type, code in SAFE_FAILURES.items():
        if isinstance(error, error_type):
            return code
    return "review_failed"


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
                    if repaired:
                        raise ValueError("Validation failed after the only repair.")
                    issues = list(context["validation_issues"])
                    emit("repair_start", {"issues": issues})
                    context = self.repair(context, issues)
                    repaired = True
                    if context.get("validation_issues"):
                        raise ValueError("Validation failed after the only repair.")
                emit("step_complete", {"step": name})
            emit("run_complete", {"repair_count": int(repaired)})
            return context
        except Exception as exc:
            context.clear()
            context["status"] = "failed"
            emit("run_failed", {"error": safe_failure_code(exc)})
            raise
        finally:
            original_context.pop("_emit", None)
            context.pop("_emit", None)
