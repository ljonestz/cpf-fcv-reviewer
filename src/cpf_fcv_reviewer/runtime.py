from __future__ import annotations

from datetime import UTC, date, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path, PurePosixPath
from secrets import compare_digest
from urllib.parse import unquote, urlsplit
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile
from zlib import error as ZlibError

from docx.opc.exceptions import PackageNotFoundError
from lxml.etree import XMLParser, XMLSyntaxError, fromstring
from pypdf.errors import PdfReadError

from .contracts import (
    DetailLevel,
    DiagnosticMode,
    DocumentRole,
    EvidenceItem,
    EvidenceLocator,
    UserCorrection,
)
from .diagnostic_sources import identify_uploaded_diagnostic
from .evidence_builder import build_reproducible_evidence_pack
from .extraction import (
    ExtractionLimitExceeded,
    extract_document,
    require_readable_primary,
)
from .model_gateway import AnthropicModelGateway
from .orchestrator import ReviewOrchestrator
from .prompts import load_prompt
from .public_research import AnthropicPublicResearchGateway, load_research_prompt
from .registry import RegistryUnavailable, load_registry_bundle
from .research_controller import ResearchController, ResearchMode, ResearchRequest
from .review_engine import ReviewEngine
from .sources import choose_authoritative_source
from .validators import (
    matched_prohibited_policy_phrases,
    result_text,
    validate_reproducibility_metadata,
    validate_review,
)

STEP_NAMES = (
    "extract",
    "resolve_sources",
    "research",
    "build_evidence",
    "map",
    "review",
    "validate",
    "render",
)

OPTIONAL_UPLOAD_EXCLUDED_WARNING = (
    "An optional uploaded document could not be read and was excluded."
)
SUPPORTED_UPLOAD_SUFFIXES = frozenset({".pdf", ".docx", ".txt", ".md"})
EXPECTED_OPTIONAL_EXTRACTION_ERRORS = (
    BadZipFile,
    ExtractionLimitExceeded,
    PackageNotFoundError,
    PdfReadError,
    UnicodeDecodeError,
    XMLSyntaxError,
)
REQUIRED_DOCX_ROOT_PARTS = frozenset({"[Content_Types].xml", "_rels/.rels"})
SUPPORTED_DOCX_COMPRESSION_TYPES = frozenset({ZIP_STORED, ZIP_DEFLATED})
CONTENT_TYPES_NAMESPACE = (
    "http://schemas.openxmlformats.org/package/2006/content-types"
)
CONTENT_TYPES_TAG = f"{{{CONTENT_TYPES_NAMESPACE}}}Types"
CONTENT_TYPE_OVERRIDE_TAG = f"{{{CONTENT_TYPES_NAMESPACE}}}Override"
MAIN_DOCUMENT_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml."
    "document.main+xml"
)
RELATIONSHIPS_NAMESPACE = (
    "http://schemas.openxmlformats.org/package/2006/relationships"
)
RELATIONSHIPS_TAG = f"{{{RELATIONSHIPS_NAMESPACE}}}Relationships"
RELATIONSHIP_TAG = f"{{{RELATIONSHIPS_NAMESPACE}}}Relationship"
OFFICE_DOCUMENT_RELATIONSHIP_TYPES = frozenset(
    {
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
        "officeDocument",
        "http://purl.oclc.org/ooxml/officeDocument/relationships/officeDocument",
    }
)
HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


PACKAGE_SECTION_MARKERS = (
    "results framework",
    "results matrix",
    "intervention logic",
    "implementation arrangement",
    "delivery arrangement",
    "adaptive management",
    "risk monitoring",
    "partnership",
    "fragility",
    "conflict",
    "rra",
)
PACKAGE_MIN_SEGMENTS_PER_DOCUMENT = 3
PACKAGE_MAX_SEGMENTS = 16


def _select_package_segments(
    documents: tuple,
) -> list[tuple[object, object, DocumentRole]]:
    """Select bounded, material package coverage in deterministic round-robin order."""
    if not documents:
        return []

    candidates = []
    for document in documents:
        indexed_segments = tuple(enumerate(document.segments))
        ordered_indices = []
        matching_indices = set()
        seen_indices = set()

        def add_index(index: int) -> None:
            if index not in seen_indices:
                seen_indices.add(index)
                ordered_indices.append(index)

        if indexed_segments:
            add_index(0)
        for index, segment in indexed_segments:
            if any(
                marker in segment.text.casefold()
                for marker in PACKAGE_SECTION_MARKERS
            ):
                matching_indices.add(index)
                add_index(index)
        for index, _ in indexed_segments:
            add_index(index)
        candidates.append(
            tuple(
                (
                    index,
                    indexed_segments[index][1],
                    index in matching_indices,
                )
                for index in ordered_indices
            )
        )

    selected = []
    offsets = [0] * len(documents)
    phase_one_counts = [0] * len(documents)

    while len(selected) < PACKAGE_MAX_SEGMENTS:
        added_this_round = False
        for index, document in enumerate(documents):
            if phase_one_counts[index] >= min(
                PACKAGE_MIN_SEGMENTS_PER_DOCUMENT,
                len(candidates[index]),
            ):
                continue
            _, segment, _ = candidates[index][offsets[index]]
            offsets[index] += 1
            phase_one_counts[index] += 1
            selected.append((document, segment, DocumentRole.PACKAGE))
            added_this_round = True
            if len(selected) >= PACKAGE_MAX_SEGMENTS:
                break
        if not added_this_round:
            break

    while len(selected) < PACKAGE_MAX_SEGMENTS:
        added_this_round = False
        for index, document in enumerate(documents):
            while offsets[index] < len(candidates[index]):
                _, segment, is_marker = candidates[index][offsets[index]]
                offsets[index] += 1
                if not is_marker:
                    continue
                selected.append((document, segment, DocumentRole.PACKAGE))
                added_this_round = True
                break
            if len(selected) >= PACKAGE_MAX_SEGMENTS:
                break
        if not added_this_round:
            break
    return selected


def _select_role_segments(
    document_role: DocumentRole,
    documents: tuple,
    budget: int,
) -> list[tuple[object, object, DocumentRole]]:
    """Select a bounded, deterministic, round-robin sample for one document role."""
    if not documents or budget <= 0:
        return []

    if document_role is DocumentRole.PRIMARY and len(documents) == 1:
        document = documents[0]
        segment_count = len(document.segments)
        if segment_count <= budget:
            indices = range(segment_count)
        elif budget == 1:
            indices = (0,)
        else:
            indices = tuple(
                round(index * (segment_count - 1) / (budget - 1))
                for index in range(budget)
            )
        return [
            (document, document.segments[index], document_role)
            for index in indices
        ]

    selected: list[tuple[object, object, DocumentRole]] = []
    offsets = [0] * len(documents)
    while len(selected) < budget:
        added_this_round = False
        for index, document in enumerate(documents):
            offset = offsets[index]
            if offset >= len(document.segments):
                continue
            selected.append((document, document.segments[offset], document_role))
            offsets[index] += 1
            added_this_round = True
            if len(selected) >= budget:
                break
        if not added_this_round:
            break
    return selected


def _is_explicit_authoritative_claim(claim) -> bool:
    authority_text = f"{claim.publisher} {claim.source_type}".casefold()
    return any(
        marker in authority_text
        for marker in (
            "world bank",
            "multilateral",
            "united nations",
            "un agency",
            " mdb",
            "mdb ",
        )
    )


def _truncate_at_word_boundary(text: str, maximum: int) -> str:
    """Keep bounded evidence readable by not cutting the final word."""
    if len(text) <= maximum:
        return text
    truncated = text[:maximum]
    if truncated[-1].isspace():
        return truncated.rstrip()
    parts = truncated.rsplit(maxsplit=1)
    return parts[0].rstrip() if len(parts) == 2 else truncated


def _has_usable_uploaded_document(document) -> bool:
    return document is not None and any(
        isinstance(segment.text, str) and segment.text.strip()
        for segment in document.segments
    )


def _relationship_source_directory(relationship_part: str) -> PurePosixPath | None:
    if relationship_part == "_rels/.rels":
        return PurePosixPath()
    path = PurePosixPath(relationship_part)
    if path.parent.name != "_rels" or not path.name.endswith(".rels"):
        return None
    source_part = path.parent.parent / path.name.removesuffix(".rels")
    return source_part.parent


def _resolve_internal_relationship_target(
    relationship_part: str,
    target: str,
) -> str | None:
    try:
        parsed = urlsplit(target)
    except ValueError:
        return None
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        return None
    if not parsed.path or parsed.path.startswith("/") or "\\" in parsed.path:
        return None
    source_directory = _relationship_source_directory(relationship_part)
    if source_directory is None:
        return None
    resolved_parts = list(source_directory.parts)
    for raw_part in parsed.path.split("/"):
        if not raw_part:
            return None
        for index, character in enumerate(raw_part):
            if character == "%" and (
                index + 2 >= len(raw_part)
                or raw_part[index + 1] not in HEX_DIGITS
                or raw_part[index + 2] not in HEX_DIGITS
            ):
                return None
        decoded_part = unquote(raw_part)
        if "/" in decoded_part or "\\" in decoded_part:
            return None
        if decoded_part in {".", ".."} and decoded_part != raw_part:
            return None
        if decoded_part == ".":
            return None
        if decoded_part == "..":
            if not resolved_parts:
                return None
            resolved_parts.pop()
            continue
        if not decoded_part:
            return None
        resolved_parts.append(decoded_part)
    return "/".join(resolved_parts)


def _parse_relationship_part(data: bytes) -> tuple[dict[str, str], ...] | None:
    parser = XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    try:
        root = fromstring(data, parser=parser)
    except XMLSyntaxError:
        return None
    if root.tag != RELATIONSHIPS_TAG or root.getroottree().docinfo.doctype:
        return None
    relationships = []
    for child in root:
        if not isinstance(child.tag, str):
            continue
        if child.tag != RELATIONSHIP_TAG:
            return None
        attributes = {
            name: child.get(name)
            for name in ("Id", "Type", "Target", "TargetMode")
            if child.get(name) is not None
        }
        if not all(
            attributes.get(name, "").strip() for name in ("Id", "Type", "Target")
        ):
            return None
        if attributes.get("TargetMode") not in {None, "External"}:
            return None
        relationships.append(attributes)
    return tuple(relationships)


def _read_docx_part(archive: ZipFile, part_name: str) -> bytes | None:
    try:
        return archive.read(part_name)
    except (BadZipFile, NotImplementedError, RuntimeError, ZlibError, OSError):
        return None


def _has_valid_main_content_type(data: bytes, main_part: str) -> bool:
    parser = XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    try:
        root = fromstring(data, parser=parser)
    except XMLSyntaxError:
        return False
    if root.tag != CONTENT_TYPES_TAG or root.getroottree().docinfo.doctype:
        return False
    matching_overrides = []
    for child in root:
        if not isinstance(child.tag, str):
            continue
        if child.tag != CONTENT_TYPE_OVERRIDE_TAG:
            continue
        part_name = child.get("PartName")
        content_type = child.get("ContentType")
        if not part_name or not content_type:
            return False
        if part_name == f"/{main_part}":
            matching_overrides.append(content_type)
    return matching_overrides == [MAIN_DOCUMENT_CONTENT_TYPE]


def _has_valid_docx_container(data: bytes) -> bool:
    try:
        with ZipFile(BytesIO(data)) as archive:
            archive_entries = archive.infolist()
            if any(
                entry.flag_bits & 0x1
                or entry.compress_type not in SUPPORTED_DOCX_COMPRESSION_TYPES
                for entry in archive_entries
            ):
                return False
            archive_names = [entry.filename for entry in archive_entries]
            archive_name_set = frozenset(archive_names)
            if len(archive_names) != len(archive_name_set) or not (
                REQUIRED_DOCX_ROOT_PARTS <= archive_name_set
            ):
                return False
            content_types = _read_docx_part(archive, "[Content_Types].xml")
            if content_types is None:
                return False
            relationship_parts = tuple(
                name
                for name in archive_names
                if name == "_rels/.rels"
                or (
                    PurePosixPath(name).parent.name == "_rels"
                    and PurePosixPath(name).name.endswith(".rels")
                )
            )
            office_document_targets = []
            for relationship_part in relationship_parts:
                relationship_data = _read_docx_part(archive, relationship_part)
                if relationship_data is None:
                    return False
                relationships = _parse_relationship_part(relationship_data)
                if relationships is None:
                    return False
                for relationship in relationships:
                    is_external = relationship.get("TargetMode") == "External"
                    is_office_document = (
                        relationship_part == "_rels/.rels"
                        and relationship["Type"] in OFFICE_DOCUMENT_RELATIONSHIP_TYPES
                    )
                    if is_office_document and is_external:
                        return False
                    if is_external:
                        continue
                    resolved_target = _resolve_internal_relationship_target(
                        relationship_part,
                        relationship["Target"],
                    )
                    if resolved_target not in archive_name_set:
                        return False
                    if is_office_document:
                        office_document_targets.append(resolved_target)
            return len(office_document_targets) == 1 and _has_valid_main_content_type(
                content_types,
                office_document_targets[0],
            )
    except BadZipFile:
        return False


def _has_valid_optional_container(data: bytes, suffix: str) -> bool:
    if suffix == ".pdf":
        return (
            len(data) >= 8
            and data.startswith(b"%PDF-")
            and data[5:6].isdigit()
            and data[6:7] == b"."
            and data[7:8].isdigit()
        )
    if suffix == ".docx":
        return _has_valid_docx_container(data)
    return True


def _extract_optional_uploads(items: tuple | list) -> tuple[tuple, tuple, tuple[str, ...]]:
    documents = []
    retained_uploads = []
    warnings = []
    for index, item in enumerate(items, start=1):
        name = item["name"]
        data = item["bytes"]
        suffix = Path(name).suffix.lower()
        if suffix not in SUPPORTED_UPLOAD_SUFFIXES or not _has_valid_optional_container(
            data, suffix
        ):
            warnings.append(OPTIONAL_UPLOAD_EXCLUDED_WARNING)
            continue
        try:
            document = extract_document(data, name, max_pdf_pages=2)
        except EXPECTED_OPTIONAL_EXTRACTION_ERRORS:
            warnings.append(OPTIONAL_UPLOAD_EXCLUDED_WARNING)
            continue
        if not _has_usable_uploaded_document(document):
            warnings.append(OPTIONAL_UPLOAD_EXCLUDED_WARNING)
            continue
        documents.append(document)
        retained_uploads.append((index, item))
        warnings.extend(document.warnings)
    return tuple(documents), tuple(retained_uploads), tuple(warnings)


def _allow_document_led(context: dict) -> bool:
    if _has_usable_uploaded_document(context.get("primary_document")):
        return True
    return any(
        _has_usable_uploaded_document(document)
        for document in context.get("context_documents", ())
    )


def _normalize_limitation(limitation: str | None) -> str | None:
    if not isinstance(limitation, str):
        return None
    normalized = " ".join(limitation.split())
    return normalized or None


def _append_limitation_once(
    values: tuple[str, ...], limitation: str | None
) -> tuple[str, ...]:
    normalized = _normalize_limitation(limitation)
    if normalized is None:
        return values
    return tuple(
        value for value in values if _normalize_limitation(value) != normalized
    ) + (normalized,)


def _preserve_research_limitation(context: dict):
    result = context.get("result")
    research_result = context.get("research_result")
    if result is None or research_result is None:
        return result
    return result.model_copy(
        update={
            "limitations": _append_limitation_once(
                result.limitations,
                research_result.limitation,
            )
        }
    )


def build_runtime_services(
    config: dict,
    *,
    model_gateway=None,
    research_gateway=None,
    research_controller=None,
    review_date_provider=date.today,
) -> dict:
    path = Path(config.get("REGISTRY_BUNDLE_PATH", ""))
    expected_hash = str(config.get("REGISTRY_BUNDLE_SHA256", "")).strip().lower()
    if not expected_hash:
        raise RuntimeError("Approved registry bundle hash is required.")
    try:
        actual_hash = sha256(path.read_bytes()).hexdigest()
    except OSError:
        raise RuntimeError("Approved registry bundle is unavailable or invalid.") from None
    if not compare_digest(actual_hash, expected_hash):
        raise RuntimeError("Approved registry bundle hash mismatch.")
    try:
        bundle = load_registry_bundle(
            path,
            allow_synthetic=config.get("ALLOW_SYNTHETIC_REGISTRY", False),
        )
    except RegistryUnavailable as exc:
        raise RuntimeError(str(exc)) from exc

    if model_gateway is None:
        model_gateway = AnthropicModelGateway(
            config["ANTHROPIC_API_KEY"],
            config["ANTHROPIC_MODEL_ID"],
        )
    if research_controller is None:
        if research_gateway is None:
            research_gateway = AnthropicPublicResearchGateway(
                config["ANTHROPIC_API_KEY"],
                config["ANTHROPIC_MODEL_ID"],
                timeout_seconds=config["RESEARCH_ATTEMPT_TIMEOUT_SECONDS"],
            )
        research_controller = ResearchController(
            research_gateway,
            max_attempts=config["RESEARCH_MAX_ATTEMPTS"],
            minimum_claims=config["RESEARCH_MINIMUM_CLAIMS"],
            minimum_publishers=config["RESEARCH_MINIMUM_PUBLISHERS"],
            total_budget_seconds=config["RESEARCH_TOTAL_BUDGET_SECONDS"],
            retry_backoff_seconds=config["RESEARCH_RETRY_BACKOFF_SECONDS"],
        )
    review_engine = ReviewEngine(model_gateway)

    prohibited_terms = {term for entry in bundle.entries for term in entry.prohibited_terms}

    def extract_uploaded_documents(context):
        payload = context.get("payload")
        if not payload or "cpf" not in payload:
            return context
        primary = payload["cpf"]
        primary_document = extract_document(primary["bytes"], primary["name"])
        require_readable_primary(primary_document)
        package_documents, package_uploads, package_warnings = _extract_optional_uploads(
            payload.get("package_documents", ())
        )
        context_documents, context_uploads, context_warnings = _extract_optional_uploads(
            payload.get("context_documents", ())
        )
        context["primary_document"] = primary_document
        context["package_documents"] = package_documents
        context["context_documents"] = context_documents
        context["package_document_uploads"] = package_uploads
        context["context_document_uploads"] = context_uploads
        context["extraction_warnings"] = (
            *primary_document.warnings,
            *package_warnings,
            *context_warnings,
        )
        return context

    def build_uploaded_evidence(context):
        payload = context.get("payload")
        primary_document = context.get("primary_document")
        if not payload or primary_document is None:
            return context
        review_focus = payload.get("review_focus", "")
        if not isinstance(review_focus, str):
            review_focus = ""
        review_focus = review_focus.strip()[:4000]

        document_groups = (
            (DocumentRole.PRIMARY, (primary_document,), 12),
            (
                DocumentRole.PACKAGE,
                tuple(context.get("package_documents", ())),
                PACKAGE_MAX_SEGMENTS,
            ),
            (DocumentRole.CONTEXT, tuple(context.get("context_documents", ())), 4),
        )
        selected_segments = []
        for document_role, documents, per_document_limit in document_groups:
            if document_role is DocumentRole.PACKAGE:
                selected_segments.extend(_select_package_segments(documents))
            else:
                selected_segments.extend(
                    _select_role_segments(document_role, documents, per_document_limit)
                )

        role_counts = {role: 0 for role, _, _ in document_groups}
        evidence = []
        for document, segment, document_role in selected_segments:
            role_counts[document_role] += 1
            evidence.append(
                EvidenceItem(
                    evidence_id=(
                        f"{document_role.value}-"
                        f"{role_counts[document_role]:03d}"
                    ),
                    evidence_type="document_fact",
                    text=_truncate_at_word_boundary(segment.text, 1600),
                    locator=EvidenceLocator(
                        document_title=document.name,
                        page=segment.page,
                        heading=segment.heading,
                        element=segment.element,
                        excerpt=_truncate_at_word_boundary(segment.text, 600),
                    ),
                    confidence="high",
                    document_role=document_role,
                )
            )

        correction_payloads = tuple(payload.get("corrections", ()))
        corrections = tuple(
            UserCorrection(
                correction_id=item["correction_id"],
                created_at=datetime.fromisoformat(item["created_at"]),
                affected_priority_area_id=item.get("affected_priority_area_id"),
                text=item["text"][:2000],
                rationale=(item.get("rationale") or "")[:1000] or None,
                independently_supported=item.get("independently_supported", False),
            )
            for item in correction_payloads[-20:]
        )
        evidence.extend(
            EvidenceItem(
                evidence_id=f"correction-{item.correction_id}",
                evidence_type="user_correction",
                text=item.text,
                confidence="medium" if item.independently_supported else "low",
            )
            for item in corrections
        )

        used_evidence_ids = {item.evidence_id for item in evidence}
        current_index = 1
        for claim in context["research_result"].claims:
            evidence_id = f"current-{current_index:03d}"
            while evidence_id in used_evidence_ids:
                current_index += 1
                evidence_id = f"current-{current_index:03d}"
            evidence.append(
                EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type="current_context",
                    text=claim.text,
                    source_url=claim.source_url,
                    confidence=(
                        "high"
                        if _is_explicit_authoritative_claim(claim)
                        else "medium"
                    ),
                )
            )
            used_evidence_ids.add(evidence_id)
            current_index += 1

        registry_evidence = tuple(
            EvidenceItem(
                evidence_id=f"registry-{entry.entry_id}",
                evidence_type="registry_language",
                text=entry.approved_text,
                confidence="high",
            )
            for entry in bundle.entries
        )
        if used_evidence_ids.intersection(
            item.evidence_id for item in registry_evidence
        ):
            raise RuntimeError("Evidence ID collision.")
        evidence.extend(registry_evidence)

        document_bytes = {
            f"primary:{payload['cpf']['name']}": payload["cpf"]["bytes"]
        }
        package_uploads = context.get("package_document_uploads")
        if package_uploads is None:
            package_uploads = tuple(
                enumerate(payload.get("package_documents", ()), start=1)
            )
        context_uploads = context.get("context_document_uploads")
        if context_uploads is None:
            context_uploads = tuple(
                enumerate(payload.get("context_documents", ()), start=1)
            )
        document_bytes.update(
            {
                f"package:{index}:{item['name']}": item["bytes"]
                for index, item in package_uploads
            }
        )
        document_bytes.update(
            {
                f"context:{index}:{item['name']}": item["bytes"]
                for index, item in context_uploads
            }
        )
        prompt_bytes = {
            "diagnostic_map": load_prompt("diagnostic_map").encode("utf-8"),
            "public_research": load_research_prompt().encode("utf-8"),
            "review": load_prompt("review").encode("utf-8"),
            "repair": load_prompt("repair").encode("utf-8"),
        }
        context["evidence_pack"] = build_reproducible_evidence_pack(
            run_id=context["assessment_id"],
            created_at=datetime.now(UTC),
            review_stage=payload["review_stage"],
            diagnostic_mode=(
                DiagnosticMode.RRA_ALIGNMENT
                if context.get("uploaded_diagnostic") is not None
                else DiagnosticMode.LIMITED_FRAMING
            ),
            documents=document_bytes,
            registry_bundle=path.read_bytes(),
            detail_level=payload.get("detail_level", DetailLevel.STANDARD),
            current_evidence_tier=context["research_result"].tier,
            current_evidence_limitation=_normalize_limitation(
                context["research_result"].limitation
            ),
            guidance=review_focus,
            prompt_bytes=prompt_bytes,
            model_id=config["ANTHROPIC_MODEL_ID"],
            source_scan_at=datetime.now(UTC),
            output_language="en",
            evidence=tuple(evidence),
            diagnostic_entries=(),
            material_diagnostic_ids=(),
            corrections=corrections,
            warnings=_append_limitation_once(
                tuple(context.get("extraction_warnings", ())),
                context["research_result"].limitation,
            ),
            correction_ids=tuple(item["correction_id"] for item in correction_payloads),
            parent_run_id=payload.get("parent_assessment_id"),
        )
        return context

    def review_validation_issues(context):
        evidence_ids = {item.evidence_id for item in context["evidence_pack"].evidence}
        issues = list(
            validate_review(
                context["result"],
                evidence_ids=evidence_ids,
                prohibited_terms=prohibited_terms,
            )
        )
        issues.extend(validate_reproducibility_metadata(context["result"].metadata))
        return [{"code": issue.code, "message": issue.message} for issue in issues]

    def mark_step(name):
        def step(context):
            context.setdefault("completed_steps", []).append(name)
            if name == "extract":
                return extract_uploaded_documents(context)
            if name == "resolve_sources" and "source_candidates" in context:
                context["authoritative_source"] = choose_authoritative_source(
                    context["source_candidates"]
                )
            if name == "review" and "evidence_pack" in context:
                review_focus = context.get("payload", {}).get("review_focus", "")
                if not isinstance(review_focus, str):
                    review_focus = ""
                review_focus = review_focus.strip()[:4000]
                context["result"] = review_engine.review(
                    context["evidence_pack"],
                    review_focus=review_focus,
                )
                context["result"] = _preserve_research_limitation(context)
            if name == "research":
                payload = context.get("payload", {})
                uploaded_diagnostic = identify_uploaded_diagnostic(
                    tuple(context.get("package_documents", ()))
                    + tuple(context.get("context_documents", ())),
                    country=payload.get("country", ""),
                )
                context["uploaded_diagnostic"] = uploaded_diagnostic
                review_date = review_date_provider()
                dated_diagnostic = (
                    uploaded_diagnostic
                    if uploaded_diagnostic is not None
                    and uploaded_diagnostic.publication_date is not None
                    else None
                )
                request = ResearchRequest(
                    country=payload["country"],
                    review_date=review_date,
                    mode=(
                        ResearchMode.RRA_UPDATE
                        if dated_diagnostic is not None
                        else ResearchMode.HOLISTIC
                    ),
                    diagnostic_title=(
                        dated_diagnostic.name if dated_diagnostic is not None else None
                    ),
                    diagnostic_date=(
                        dated_diagnostic.publication_date
                        if dated_diagnostic is not None
                        else None
                    ),
                    diagnostic_summary=(
                        " ".join(
                            segment.text
                            for document in (
                                *tuple(context.get("package_documents", ())),
                                *tuple(context.get("context_documents", ())),
                            )
                            if dated_diagnostic is not None
                            and document.name == dated_diagnostic.name
                            for segment in document.segments[:3]
                        )[:1200]
                        if dated_diagnostic is not None
                        else ""
                    ),
                )
                context["research_result"] = research_controller.run(
                    request,
                    context["_emit"],
                    allow_document_led=_allow_document_led(context),
                )
            if name == "build_evidence":
                return build_uploaded_evidence(context)
            if name == "validate" and {
                "result",
                "evidence_pack",
            }.issubset(context):
                context["validation_issues"] = review_validation_issues(context)
            if name == "render" and "result" not in context:
                raise RuntimeError("Review result is unavailable.")
            return context

        return step

    def repair(context, issues):
        if "result" not in context:
            return context
        context["result"] = review_engine.repair(
            context["result"],
            issues,
            forbidden_phrases=matched_prohibited_policy_phrases(
                result_text(context["result"]),
                prohibited_terms,
            ),
        )
        context["result"] = _preserve_research_limitation(context)
        context["validation_issues"] = review_validation_issues(context)
        return context

    orchestrator = ReviewOrchestrator(
        steps=tuple((name, mark_step(name)) for name in STEP_NAMES),
        repair=repair,
    )
    return {
        "review_orchestrator": orchestrator,
        "registry_bundle": bundle,
        "research_controller": research_controller,
    }
