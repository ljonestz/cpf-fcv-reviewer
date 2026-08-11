from __future__ import annotations

from collections.abc import Callable

Emitter = Callable[[str, dict], None]
Step = Callable[[dict], dict]
Repair = Callable[[dict, list], dict]


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
            emit(
                "run_failed",
                {"error_type": type(exc).__name__, "message": str(exc)},
            )
            raise
