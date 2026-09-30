from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from hashlib import sha256

from .contracts import CurrentEvidenceTier, DetailLevel, DiagnosticMode, RunMetadata


def sha256_bytes(value: bytes) -> str:
    """Return the SHA-256 digest of a byte sequence."""
    return sha256(value).hexdigest()


def _registry_bundle_version(registry_bundle: bytes) -> str:
    try:
        bundle = json.loads(registry_bundle)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return "unknown"
    version = bundle.get("version") if isinstance(bundle, dict) else None
    return version.strip() if isinstance(version, str) and version.strip() else "unknown"


def _prompt_bundle_version(prompt_bytes: Mapping[str, bytes]) -> str:
    versions = []
    for name, content in sorted(prompt_bytes.items()):
        header = content.partition(b"\n")[0].decode("utf-8", errors="replace").strip()
        declared = header.partition(":")[2].strip() if header.startswith("Version:") else ""
        version = declared or f"sha256:{sha256_bytes(content)}"
        versions.append(f"{name}:{version}")
    return ";".join(versions) if versions else "none"


def build_run_metadata(
    *,
    run_id: str,
    created_at: datetime,
    review_stage: str,
    detail_level: DetailLevel | str = DetailLevel.STANDARD,
    diagnostic_mode: DiagnosticMode | str,
    current_evidence_tier: CurrentEvidenceTier | str = CurrentEvidenceTier.FULL,
    current_evidence_limitation: str | None = None,
    app_release: str | None = None,
    prompt_bundle_version: str | None = None,
    registry_bundle_version: str | None = None,
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
        detail_level=detail_level,
        diagnostic_mode=diagnostic_mode,
        app_release=app_release or "dev",
        schema_version="1.0.0",
        rubric_version="1.0.0",
        prompt_bundle_version=prompt_bundle_version or _prompt_bundle_version(prompt_bytes),
        registry_versions={
            "bundle": registry_bundle_version or _registry_bundle_version(registry_bundle)
        },
        model_id=model_id,
        current_evidence_tier=current_evidence_tier,
        current_evidence_limitation=current_evidence_limitation,
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
