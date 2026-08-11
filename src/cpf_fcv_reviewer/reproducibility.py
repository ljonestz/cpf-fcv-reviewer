from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from hashlib import sha256

from .contracts import DiagnosticMode, RunMetadata


def sha256_bytes(value: bytes) -> str:
    """Return the SHA-256 digest of a byte sequence."""
    return sha256(value).hexdigest()


def build_run_metadata(
    *,
    run_id: str,
    created_at: datetime,
    review_stage: str,
    diagnostic_mode: DiagnosticMode | str,
    documents: Mapping[str, bytes],
    registry_bundle: bytes,
    guidance: str,
    prompt_bytes: Mapping[str, bytes],
    model_id: str,
    source_scan_at: datetime,
    output_language: str,
    validation_outcomes: tuple[str, ...] = (),
    correction_ids: tuple[str, ...] = (),
    parent_run_id: str | None = None,
    repair_count: int = 0,
) -> RunMetadata:
    """Build reproducibility metadata using hashes rather than raw content."""
    return RunMetadata(
        run_id=run_id,
        created_at=created_at,
        review_stage=review_stage,
        diagnostic_mode=diagnostic_mode,
        app_release="0.1.0",
        schema_version="1.0.0",
        rubric_version="1.0.0",
        prompt_bundle_version="1.0.0",
        registry_versions={"bundle": "2026.08"},
        model_id=model_id,
        source_scan_at=source_scan_at,
        output_language=output_language,
        document_fingerprints={
            name: sha256_bytes(content) for name, content in sorted(documents.items())
        },
        registry_bundle_hash=sha256_bytes(registry_bundle),
        guidance_hash=sha256_bytes(guidance.encode("utf-8")),
        prompt_hashes={
            name: sha256_bytes(content) for name, content in sorted(prompt_bytes.items())
        },
        validation_outcomes=validation_outcomes,
        correction_ids=correction_ids,
        parent_run_id=parent_run_id,
        repair_count=repair_count,
    )
