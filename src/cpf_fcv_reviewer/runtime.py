from __future__ import annotations

import json
import logging
import re
from dataclasses import replace
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
from pydantic import ValidationError
from pypdf.errors import PdfReadError

from . import diagnostic_sources
from .contracts import (
    CurrentEvidenceTier,
    DetailLevel,
    DiagnosticMap,
    DiagnosticMode,
    DocumentRole,
    EvidenceItem,
    EvidenceLocator,
    UserCorrection,
)
from .diagnostic_map import validate_diagnostic_references
from .diagnostic_sources import identify_uploaded_diagnostic
from .evidence_builder import build_evidence_pack, build_reproducible_evidence_pack
from .extraction import (
    PDF_SAMPLING_WARNING_SUFFIX,
    DiagnosticCoverageUnavailable,
    DocumentTooLarge,
    DocumentUnreadable,
    ExtractionLimitExceeded,
    PackageCoverageUnavailable,
    extract_document,
    require_readable_primary,
)
from .fcv_readout import (
    generate_fcv_readout,
    readout_caveat_limitation,
    readout_payload,
)
from .follow_on import AnthropicFollowOnGateway
from .model_gateway import AnthropicModelGateway
from .orchestrator import ReviewOrchestrator
from .prompts import load_prompt
from .public_research import AnthropicPublicResearchGateway, load_research_prompt
from .registry import RegistryUnavailable, load_registry_bundle
from .research_controller import (
    MAX_PRIMARY_CPF_CONTEXT_CHARACTERS,
    MAX_REVIEW_FOCUS_CHARACTERS,
    ResearchController,
    ResearchMode,
    ResearchRequest,
)
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

REQUIRED_PRODUCTION_STRATEGY_REGISTRY_ENTRY_IDS = frozenset(
    f"PUB-FCV-STRAT-{index:03d}" for index in range(1, 5)
)
MECHANICAL_REPAIR_RETRY_CODES = frozenset(
    {
        "raw_evidence_id_in_narrative",
        "stage_length_overreach",
        "prohibited_policy_language",
        "missing_registry_support",
    }
)

OPTIONAL_UPLOAD_EXCLUDED_WARNING = (
    "An optional uploaded document could not be read and was excluded."
)
SUPPORTED_UPLOAD_SUFFIXES = frozenset({".pdf", ".docx", ".txt", ".md"})
OPTIONAL_PDF_SAMPLE_PAGES = 16
DIAGNOSTIC_MAX_PAGES = 250
DIAGNOSTIC_MAX_CHARACTERS = 600_000
DIAGNOSTIC_MAX_UNCOMPRESSED_BYTES = 50_000_000
DIAGNOSTIC_MAX_ARCHIVE_MEMBERS = 512
# The primary CPF/CEN is the principal lens and is never sampled, so its budgets are
# generous. They are also role-appropriate: a PDF segment is a page, but a DOCX segment
# is a single paragraph or table row, so one page-sized budget cannot serve both.
PRIMARY_MAX_PDF_PAGES = 400
PRIMARY_MAX_SEGMENTS = 10_000
PRIMARY_MAX_CHARACTERS = 600_000
PRIMARY_MAX_UNCOMPRESSED_BYTES = 50_000_000
PRIMARY_MAX_ARCHIVE_MEMBERS = 512
PACKAGE_MAX_DOCUMENTS = 10
PACKAGE_MAX_SEGMENTS_TOTAL = 400
PACKAGE_MAX_CHARACTERS_TOTAL = 300_000
DIAGNOSTIC_MAP_MAX_ESTIMATED_INPUT_TOKENS = 160_000
_DIAGNOSTIC_MAP_SCHEMA_FIELDS = frozenset(
    {
        "entries",
        "entry_id",
        "short_name",
        "group",
        "materiality",
        "source_evidence_ids",
        "grouping_rationale",
    }
)
_MAX_DIAGNOSTIC_MAP_SCHEMA_RETRY_ISSUES = 25
_MAX_SCHEMA_LOCATION_DEPTH = 8
DIAGNOSTIC_FILENAME_MARKERS = (
    "risk and resilience assessment",
    "risk & resilience assessment",
    "accepted equivalent diagnostic",
    "fcv risk assessment",
)
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


def _can_retry_mechanical_repair(issues: list[dict]) -> bool:
    return bool(issues) and all(
        isinstance(issue, dict)
        and issue.get("code") in MECHANICAL_REPAIR_RETRY_CODES
        for issue in issues
    )


def _safe_diagnostic_map_schema_issues(
    error: ValidationError,
) -> list[dict[str, object]]:
    issues = []
    for item in error.errors(
        include_url=False,
        include_context=False,
        include_input=False,
    )[:_MAX_DIAGNOSTIC_MAP_SCHEMA_RETRY_ISSUES]:
        location = []
        for part in item.get("loc", ())[:_MAX_SCHEMA_LOCATION_DEPTH]:
            if type(part) is int and 0 <= part <= 9999:
                location.append(part)
            elif isinstance(part, str) and part in _DIAGNOSTIC_MAP_SCHEMA_FIELDS:
                location.append(part)
            else:
                location.append("unrecognized_field")
        issue_type = str(item.get("type", "validation_error"))
        if not re.fullmatch(r"[a-z0-9_]{1,64}", issue_type):
            issue_type = "validation_error"
        issues.append({"loc": location, "type": issue_type})
    return issues


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


def _is_incomplete_coverage_warning(document_name: str, warning: object) -> bool:
    if not isinstance(warning, str):
        return False
    pattern = (
        rf"{re.escape(document_name)}: sampled \d+ of \d+ PDF pages; "
        rf"{re.escape(PDF_SAMPLING_WARNING_SUFFIX)}"
    )
    return re.fullmatch(pattern, warning) is not None


def _incomplete_document_roles(context: dict) -> frozenset[DocumentRole]:
    """Return optional roles whose retained documents were sampled incompletely."""
    incomplete_roles: set[DocumentRole] = set()
    for role, context_key in (
        (DocumentRole.PACKAGE, "package_documents"),
        (DocumentRole.CONTEXT, "context_documents"),
    ):
        if any(
            _is_incomplete_coverage_warning(document.name, warning)
            for document in context.get(context_key, ())
            for warning in getattr(document, "warnings", ())
        ):
            incomplete_roles.add(role)
    return frozenset(incomplete_roles)


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
            # Validating the container means decompressing [Content_Types].xml and the
            # relationship parts, so the archive's declared size must be checked first,
            # from the central directory, before anything is inflated.
            if len(archive_entries) > PRIMARY_MAX_ARCHIVE_MEMBERS or sum(
                entry.file_size for entry in archive_entries
            ) > PRIMARY_MAX_UNCOMPRESSED_BYTES:
                return False
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


def _filename_suggests_diagnostic(name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9&]+", " ", name.casefold())
    return bool(
        re.search(r"(?<![a-z0-9])rra(?![a-z0-9])", normalized)
        or any(marker in normalized for marker in DIAGNOSTIC_FILENAME_MARKERS)
    )


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


def _docx_archive_exceeds_budget(data: bytes) -> bool:
    """Read the zip central directory only; nothing is inflated to answer this."""
    try:
        with ZipFile(BytesIO(data)) as archive:
            entries = archive.infolist()
    except (BadZipFile, OSError):
        return False
    return len(entries) > PRIMARY_MAX_ARCHIVE_MEMBERS or sum(
        entry.file_size for entry in entries
    ) > PRIMARY_MAX_UNCOMPRESSED_BYTES


def _extract_primary_document(data: bytes, name: str):
    """Extract the primary CPF/CEN under the same bounds as full diagnostic extraction.

    The primary document is the principal review lens, so it is never sampled. It is
    still bounded: an unusable container or an upload that exceeds the extraction
    budget fails closed as an unreadable primary rather than being extracted.
    """
    suffix = Path(name).suffix.lower()
    # An oversized archive and a malformed one are different failures, and the reader
    # is told which. This runs before container validation because validating a DOCX
    # decompresses its metadata parts.
    if suffix == ".docx" and _docx_archive_exceeds_budget(data):
        raise DocumentTooLarge("Primary CPF/CEN exceeds the safe extraction budget.")
    if suffix not in SUPPORTED_UPLOAD_SUFFIXES or not _has_valid_optional_container(
        data, suffix
    ):
        raise DocumentUnreadable("Primary CPF/CEN is unreadable or unsupported.")
    if suffix == ".pdf":
        # Equal page and segment budgets: an unequal pair makes extract_pdf_bytes
        # silently truncate to max_pdf_pages instead of failing closed.
        bounds = {
            "max_pdf_pages": PRIMARY_MAX_PDF_PAGES,
            "max_segments": PRIMARY_MAX_PDF_PAGES,
        }
    else:
        bounds = {"max_segments": PRIMARY_MAX_SEGMENTS}
    try:
        return extract_document(
            data,
            name,
            **bounds,
            max_characters=PRIMARY_MAX_CHARACTERS,
            max_uncompressed_bytes=PRIMARY_MAX_UNCOMPRESSED_BYTES,
            max_archive_members=PRIMARY_MAX_ARCHIVE_MEMBERS,
        )
    except ExtractionLimitExceeded as exc:
        raise DocumentTooLarge(
            "Primary CPF/CEN exceeds the safe extraction budget."
        ) from exc


def _extract_optional_uploads(
    items: tuple | list,
    *,
    strict_package: bool = False,
) -> tuple[tuple, tuple, tuple[str, ...]]:
    if strict_package and len(items) > PACKAGE_MAX_DOCUMENTS:
        raise PackageCoverageUnavailable("Package document-count budget exceeded.")
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
            if strict_package:
                raise PackageCoverageUnavailable("A package document is unreadable.")
            warnings.append(OPTIONAL_UPLOAD_EXCLUDED_WARNING)
            continue
        try:
            if suffix == ".pdf":
                document = extract_document(
                    data,
                    name,
                    max_pdf_pages=OPTIONAL_PDF_SAMPLE_PAGES,
                    sample_pdf_across_document=True,
                    max_segments=DIAGNOSTIC_MAX_PAGES,
                    max_characters=DIAGNOSTIC_MAX_CHARACTERS,
                    max_uncompressed_bytes=DIAGNOSTIC_MAX_UNCOMPRESSED_BYTES,
                )
            else:
                document = extract_document(
                    data,
                    name,
                    max_segments=DIAGNOSTIC_MAX_PAGES,
                    max_characters=DIAGNOSTIC_MAX_CHARACTERS,
                    max_uncompressed_bytes=DIAGNOSTIC_MAX_UNCOMPRESSED_BYTES,
                )
        except ExtractionLimitExceeded as exc:
            if strict_package:
                raise PackageCoverageUnavailable(
                    "A package document could not be extracted in full."
                ) from exc
            if _filename_suggests_diagnostic(name):
                raise DiagnosticCoverageUnavailable(
                    "named uploaded diagnostic exceeded a safe extraction bound."
                ) from exc
            warnings.append(OPTIONAL_UPLOAD_EXCLUDED_WARNING)
            continue
        except EXPECTED_OPTIONAL_EXTRACTION_ERRORS as exc:
            if strict_package:
                raise PackageCoverageUnavailable(
                    "A package document could not be extracted in full."
                ) from exc
            warnings.append(OPTIONAL_UPLOAD_EXCLUDED_WARNING)
            continue
        if not _has_usable_uploaded_document(document):
            if strict_package:
                raise PackageCoverageUnavailable("A package document is unreadable.")
            warnings.append(OPTIONAL_UPLOAD_EXCLUDED_WARNING)
            continue
        documents.append(document)
        retained_uploads.append((index, item))
        warnings.extend(document.warnings)
    return tuple(documents), tuple(retained_uploads), tuple(warnings)


def _validate_full_package_documents(documents: tuple) -> None:
    segment_count = sum(len(document.segments) for document in documents)
    character_count = sum(
        len(segment.text)
        for document in documents
        for segment in document.segments
    )
    if segment_count > PACKAGE_MAX_SEGMENTS_TOTAL:
        raise PackageCoverageUnavailable("Package segment budget exceeded.")
    if character_count > PACKAGE_MAX_CHARACTERS_TOTAL:
        raise PackageCoverageUnavailable("Package character budget exceeded.")


def _reextract_full_package_documents(context: dict) -> None:
    documents = list(context.get("package_documents", ()))
    uploads = tuple(context.get("package_document_uploads", ()))
    diagnostic_position = (
        context.get("diagnostic_document_position")
        if context.get("diagnostic_document_role") is DocumentRole.PACKAGE
        else None
    )
    for position, (_upload_index, upload) in enumerate(uploads):
        if position == diagnostic_position:
            continue
        try:
            document = extract_document(
                upload["bytes"],
                upload["name"],
                max_pdf_pages=DIAGNOSTIC_MAX_PAGES,
                sample_pdf_across_document=False,
                max_segments=DIAGNOSTIC_MAX_PAGES,
                max_characters=DIAGNOSTIC_MAX_CHARACTERS,
                max_uncompressed_bytes=DIAGNOSTIC_MAX_UNCOMPRESSED_BYTES,
            )
        except EXPECTED_OPTIONAL_EXTRACTION_ERRORS as exc:
            raise PackageCoverageUnavailable(
                "A package document could not be extracted in full."
            ) from exc
        if not _has_usable_uploaded_document(document):
            raise PackageCoverageUnavailable("A package document is unreadable.")
        context["extraction_warnings"] = (
            _remove_warning_multiset(
                tuple(context.get("extraction_warnings", ())),
                documents[position].warnings,
            )
            + document.warnings
        )
        documents[position] = document
    full_package = tuple(
        document
        for position, document in enumerate(documents)
        if position != diagnostic_position
    )
    _validate_full_package_documents(full_package)
    context["package_documents"] = tuple(documents)


def _resolve_uploaded_diagnostic_source(
    context: dict,
    source_index: int,
) -> tuple[DocumentRole, int, object, dict] | None:
    package_documents = tuple(context.get("package_documents", ()))
    context_documents = tuple(context.get("context_documents", ()))
    if source_index < len(package_documents):
        role = DocumentRole.PACKAGE
        position = source_index
        documents = package_documents
        uploads = context.get("package_document_uploads", ())
    else:
        position = source_index - len(package_documents)
        if position >= len(context_documents):
            return None
        role = DocumentRole.CONTEXT
        documents = context_documents
        uploads = context.get("context_document_uploads", ())
    if position < 0 or position >= len(documents) or position >= len(uploads):
        return None
    _upload_index, upload = uploads[position]
    return role, position, documents[position], upload


def _replace_document_with_full_diagnostic(
    context: dict,
    *,
    role: DocumentRole,
    position: int,
    full_document,
) -> None:
    key = "package_documents" if role is DocumentRole.PACKAGE else "context_documents"
    documents = tuple(context.get(key, ()))
    if position < 0 or position >= len(documents):
        raise ValueError("Selected uploaded diagnostic position is unavailable.")
    context[key] = tuple(
        full_document if index == position else document
        for index, document in enumerate(documents)
    )


def _remove_warning_multiset(
    values: tuple[str, ...],
    removals: tuple[str, ...],
) -> tuple[str, ...]:
    remaining = list(values)
    for warning in removals:
        try:
            remaining.remove(warning)
        except ValueError:
            pass
    return tuple(remaining)


def _diagnostic_page_items(
    document,
    *,
    document_role: DocumentRole,
) -> tuple[EvidenceItem, ...]:
    items = []
    for index, segment in enumerate(document.segments, start=1):
        evidence_id = (
            f"diagnostic-page-{segment.page:03d}"
            if segment.page is not None
            else f"diagnostic-segment-{index:03d}"
        )
        items.append(
            EvidenceItem(
                evidence_id=evidence_id,
                evidence_type="document_fact",
                text=segment.text,
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
    return tuple(items)


def _diagnostic_coverage_warning(document) -> str:
    page_numbers = [
        segment.page for segment in document.segments if segment.page is not None
    ]
    warning_pages = [
        int(match.group(1))
        for warning in document.warnings
        if (match := re.search(r"page (\d+) extracted no text", warning))
    ]
    attempted = max((*page_numbers, *warning_pages), default=len(document.segments))
    extractable = len(page_numbers) if page_numbers else len(document.segments)
    return (
        f"{document.name}: {attempted} pages attempted; "
        f"{extractable} pages with extractable text; "
        "thematic diagnostic synthesis complete."
    )


def _downgrade_to_limited_framing(context: dict, reason: str) -> dict:
    """Proceed without RRA alignment when an uploaded diagnostic cannot be mapped.

    A failed diagnostic mapping is an enrichment failure, not a fatal one. Rather than
    aborting the whole review with ``DiagnosticCoverageUnavailable``, the run continues
    in limited-framing mode (which must not claim RRA alignment). The downgrade reason is
    surfaced as an evidence-pack warning and a review limitation so the caveat is visible
    to the reader.
    """
    base_pack = context["evidence_pack"]
    downgrade_warning = (
        "The uploaded diagnostic could not be mapped in full; the review proceeds in "
        f"limited-framing mode. RRA alignment was not assessed. {reason}"
    ).strip()
    context["diagnostic_coverage_warning"] = downgrade_warning
    context.pop("diagnostic_map", None)
    context.pop("diagnostic_page_evidence", None)
    context["diagnostic_downgraded_to_limited_framing"] = True
    context["evidence_pack"] = build_evidence_pack(
        metadata=base_pack.metadata.model_copy(
            update={"diagnostic_mode": DiagnosticMode.LIMITED_FRAMING}
        ),
        evidence=base_pack.evidence,
        diagnostic_entries=(),
        material_diagnostic_ids=(),
        corrections=base_pack.user_corrections,
        warnings=(*base_pack.warnings, downgrade_warning),
    )
    return context


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
    limitations = _append_limitation_once(
        result.limitations,
        research_result.limitation,
    )
    limitations = _append_limitation_once(
        limitations,
        context.get("diagnostic_coverage_warning"),
    )
    readout = context.get("fcv_readout")
    if readout is not None:
        limitations = _append_limitation_once(
            limitations,
            readout_caveat_limitation(readout),
        )
    return result.model_copy(update={"limitations": limitations})


def build_runtime_services(
    config: dict,
    *,
    model_gateway=None,
    research_gateway=None,
    research_controller=None,
    follow_on_gateway=None,
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
    if not bundle.synthetic:
        missing_strategy_entries = (
            REQUIRED_PRODUCTION_STRATEGY_REGISTRY_ENTRY_IDS
            - {entry.entry_id for entry in bundle.entries}
        )
        if missing_strategy_entries:
            missing = ", ".join(sorted(missing_strategy_entries))
            raise RuntimeError(
                "Approved production registry bundle is missing required FCV Strategy "
                f"registry entries: {missing}."
            )

    if model_gateway is None:
        model_gateway = AnthropicModelGateway(
            config["ANTHROPIC_API_KEY"],
            config["ANTHROPIC_MODEL_ID"],
        )
    if follow_on_gateway is None:
        follow_on_gateway = AnthropicFollowOnGateway(
            config["ANTHROPIC_API_KEY"],
            config["ANTHROPIC_MODEL_ID"],
        )
    if research_controller is None:
        recovery_gateway = None
        if research_gateway is None:
            from .curated_research import (
                BoundedInstitutionalClient,
                CuratedResearchGateway,
            )

            recovery_gateway = CuratedResearchGateway(
                BoundedInstitutionalClient(
                    timeout_seconds=config["RESEARCH_ATTEMPT_TIMEOUT_SECONDS"]
                ),
                reliefweb_app_name=config.get("RELIEFWEB_APP_NAME", ""),
            )
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
            recovery_gateway=recovery_gateway,
        )
    review_engine = ReviewEngine(model_gateway)

    prohibited_terms = {term for entry in bundle.entries for term in entry.prohibited_terms}
    registry_entry_ids = {entry.entry_id for entry in bundle.entries}

    def extract_uploaded_documents(context):
        payload = context.get("payload")
        if not payload or "cpf" not in payload:
            return context
        primary = payload["cpf"]
        primary_document = _extract_primary_document(primary["bytes"], primary["name"])
        require_readable_primary(primary_document)
        package_documents, package_uploads, package_warnings = _extract_optional_uploads(
            payload.get("package_documents", ()),
            strict_package=True,
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

        package_documents = tuple(context.get("package_documents", ()))
        context_documents = tuple(context.get("context_documents", ()))
        diagnostic_role = context.get("diagnostic_document_role")
        diagnostic_position = context.get("diagnostic_document_position")
        if (
            context.get("full_diagnostic_document") is not None
            and isinstance(diagnostic_position, int)
        ):
            if diagnostic_role is DocumentRole.PACKAGE:
                package_documents = tuple(
                    document
                    for index, document in enumerate(package_documents)
                    if index != diagnostic_position
                )
            elif diagnostic_role is DocumentRole.CONTEXT:
                context_documents = tuple(
                    document
                    for index, document in enumerate(context_documents)
                    if index != diagnostic_position
                )
        selected_segments = _select_role_segments(
            DocumentRole.PRIMARY, (primary_document,), 12
        )
        context_segments = _select_role_segments(
            DocumentRole.CONTEXT, context_documents, 16
        )
        role_counts = {DocumentRole.PRIMARY: 0, DocumentRole.CONTEXT: 0}
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
        for document_index, document in enumerate(package_documents, start=1):
            for segment_index, segment in enumerate(document.segments, start=1):
                evidence.append(
                    EvidenceItem(
                        evidence_id=(
                            f"package-doc-{document_index:03d}-"
                            f"segment-{segment_index:03d}"
                        ),
                        evidence_type="document_fact",
                        text=segment.text,
                        locator=EvidenceLocator(
                            document_title=document.name,
                            page=segment.page,
                            heading=segment.heading,
                            element=segment.element,
                            excerpt=_truncate_at_word_boundary(segment.text, 600),
                        ),
                        confidence="high",
                        document_role=DocumentRole.PACKAGE,
                    )
                )
        for document, segment, document_role in context_segments:
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
                    source_title=claim.source_title,
                    source_publisher=claim.publisher,
                    source_date=claim.source_date,
                    supporting_quote=claim.supporting_quote,
                    source_relevance=claim.relevance,
                    publication_date_basis=claim.publication_date_basis,
                    confidence=(
                        "high"
                        if _is_explicit_authoritative_claim(claim)
                        else "medium"
                    ),
                    verification=claim.verification,
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
        pack = context["evidence_pack"]
        context["evidence_pack"] = pack.model_copy(update={
            "metadata": pack.metadata.model_copy(update={
                "diagnostic_provenance": context.get("diagnostic_provenance"),
            }),
        })
        return context

    def map_uploaded_diagnostic(context):
        full_diagnostic = context.get("full_diagnostic_document")
        if full_diagnostic is None:
            return context
        diagnostic_role = context.get(
            "diagnostic_document_role",
            DocumentRole.PACKAGE,
        )
        page_items = _diagnostic_page_items(
            full_diagnostic,
            document_role=diagnostic_role,
        )
        if not page_items:
            return _downgrade_to_limited_framing(
                context,
                "The selected diagnostic contained no extractable text.",
            )
        material_ids = tuple(item.evidence_id for item in page_items)
        mapping_evidence = []
        for item in page_items:
            item_payload = item.model_dump(mode="json")
            item_payload["locator"].pop("excerpt", None)
            mapping_evidence.append(item_payload)
        mapping_payload = {
            "diagnostic_title": full_diagnostic.name,
            "material_evidence_ids": list(material_ids),
            "evidence": mapping_evidence,
        }
        serialized_mapping_payload = json.dumps(
            mapping_payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        estimated_input_tokens = (
            max(
                len(serialized_mapping_payload),
                len(serialized_mapping_payload.encode("utf-8")),
            )
            + 2
        ) // 3
        if estimated_input_tokens > DIAGNOSTIC_MAP_MAX_ESTIMATED_INPUT_TOKENS:
            return _downgrade_to_limited_framing(
                context,
                "The diagnostic was too large to map within the safe input budget.",
            )
        try:
            diagnostic_map = model_gateway.generate(
                prompt_name="diagnostic_map",
                payload=mapping_payload,
                output_type=DiagnosticMap,
            )
        except ValidationError as error:
            try:
                diagnostic_map = model_gateway.generate(
                    prompt_name="diagnostic_map",
                    payload={
                        **mapping_payload,
                        "schema_retry": {
                            "issues": _safe_diagnostic_map_schema_issues(error),
                        },
                    },
                    output_type=DiagnosticMap,
                )
            except ValidationError as retry_error:
                # Log schema structure only; never rejected values or exception text.
                logging.getLogger(__name__).warning(
                    "diagnostic_map_schema_invalid attempt=2 schema_diagnostics=%s",
                    json.dumps(_safe_diagnostic_map_schema_issues(retry_error)),
                )
                return _downgrade_to_limited_framing(
                    context,
                    "The diagnostic mapping did not satisfy the required schema.",
                )
        try:
            validate_diagnostic_references(material_ids, diagnostic_map.entries)
        except ValueError:
            return _downgrade_to_limited_framing(
                context,
                "The diagnostic mapping did not cover the material evidence.",
            )

        base_pack = context["evidence_pack"]
        referenced_ids = {
            evidence_id
            for entry in diagnostic_map.entries
            for evidence_id in entry.source_evidence_ids
        }
        page_excerpts = tuple(
            item.model_copy(
                update={
                    "text": _truncate_at_word_boundary(item.text, 600),
                }
            )
            for item in page_items
            if item.evidence_id in referenced_ids
        )
        base_evidence = base_pack.evidence
        context["diagnostic_map"] = diagnostic_map
        context["diagnostic_page_evidence"] = page_items
        context["evidence_pack"] = build_evidence_pack(
            metadata=base_pack.metadata,
            evidence=base_evidence + page_excerpts,
            diagnostic_entries=diagnostic_map.entries,
            material_diagnostic_ids=material_ids,
            corrections=base_pack.user_corrections,
            warnings=(
                *base_pack.warnings,
                context["diagnostic_coverage_warning"],
            ),
        )
        return context

    def review_validation_issues(context):
        evidence = {
            item.evidence_id: item for item in context["evidence_pack"].evidence
        }
        issues = list(
            validate_review(
                context["result"],
                evidence_ids=set(evidence),
                evidence=evidence,
                prohibited_terms=prohibited_terms,
                incomplete_document_roles=_incomplete_document_roles(context),
                registry_entry_ids=registry_entry_ids,
            )
        )
        issues.extend(validate_reproducibility_metadata(context["result"].metadata))
        return [
            {
                "code": issue.code,
                "message": issue.message,
                "severity": getattr(issue, "severity", "fatal"),
            }
            for issue in issues
        ]

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
                readout = context.get("fcv_readout")
                context["result"] = review_engine.review(
                    context["evidence_pack"],
                    review_focus=review_focus,
                    current_context_readout=(
                        readout_payload(readout) if readout is not None else None
                    ),
                )
                context["result"] = _preserve_research_limitation(context)
            if name == "research":
                payload = context.get("payload", {})
                diagnostic_documents = (
                    tuple(context.get("package_documents", ()))
                    + tuple(context.get("context_documents", ()))
                )
                uploaded_diagnostic = identify_uploaded_diagnostic(
                    diagnostic_documents,
                    country=payload.get("country", ""),
                )
                context["uploaded_diagnostic"] = uploaded_diagnostic
                if uploaded_diagnostic is not None:
                    resolved = _resolve_uploaded_diagnostic_source(
                        context,
                        uploaded_diagnostic.source_index,
                    )
                    if resolved is None:
                        raise ValueError(
                            "Selected uploaded diagnostic bytes were not retained."
                        )
                    (
                        diagnostic_role,
                        diagnostic_position,
                        sampled_document,
                        upload,
                    ) = resolved
                    try:
                        full_diagnostic = extract_document(
                            upload["bytes"],
                            upload["name"],
                            max_pdf_pages=DIAGNOSTIC_MAX_PAGES,
                            max_segments=DIAGNOSTIC_MAX_PAGES,
                            max_characters=DIAGNOSTIC_MAX_CHARACTERS,
                            max_uncompressed_bytes=DIAGNOSTIC_MAX_UNCOMPRESSED_BYTES,
                        )
                    except ExtractionLimitExceeded as exc:
                        raise DiagnosticCoverageUnavailable(
                            "Selected uploaded diagnostic could not be extracted in full."
                        ) from exc
                    provenance = diagnostic_sources.diagnostic_provenance(full_diagnostic)
                    context["diagnostic_provenance"] = provenance
                    # Research and review share the same date from the fully extracted
                    # document, not a date inferred from the identification sample.
                    uploaded_diagnostic = replace(
                        uploaded_diagnostic, publication_date=provenance.publication_date,
                    )
                    context["uploaded_diagnostic"] = uploaded_diagnostic
                    context["full_diagnostic_document"] = full_diagnostic
                    context["diagnostic_document_role"] = diagnostic_role
                    context["diagnostic_document_position"] = diagnostic_position
                    _replace_document_with_full_diagnostic(
                        context,
                        role=diagnostic_role,
                        position=diagnostic_position,
                        full_document=full_diagnostic,
                    )
                    context["diagnostic_coverage_warning"] = (
                        _diagnostic_coverage_warning(full_diagnostic)
                    )
                    context["extraction_warnings"] = (
                        _remove_warning_multiset(
                            tuple(context.get("extraction_warnings", ())),
                            sampled_document.warnings,
                        )
                        + full_diagnostic.warnings
                    )
                _reextract_full_package_documents(context)
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
                    primary_cpf_context=" ".join(
                        segment.text for segment in context["primary_document"].segments
                    )[:MAX_PRIMARY_CPF_CONTEXT_CHARACTERS],
                    review_focus=(
                        payload.get("review_focus", "")[:MAX_REVIEW_FOCUS_CHARACTERS]
                        if isinstance(payload.get("review_focus", ""), str) else ""
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
                            for segment in context["full_diagnostic_document"].segments[:3]
                        )[:1200]
                        if uploaded_diagnostic is not None
                        and context.get("full_diagnostic_document") is not None
                        else ""
                    ),
                )
                context["research_result"] = research_controller.run(
                    request,
                    context["_emit"],
                    allow_document_led=_allow_document_led(context),
                )
                if (
                    context["research_result"].tier
                    is CurrentEvidenceTier.DOCUMENT_LED
                ):
                    # No external current sources were established. Fall back to a
                    # bounded, knowledge-based readout so the review still has current
                    # context (clearly caveated). Best-effort: never fail the run.
                    readout_error = None
                    try:
                        readout = generate_fcv_readout(
                            model_gateway,
                            country=payload["country"],
                            review_date=review_date,
                            reference_start_date=(
                                dated_diagnostic.publication_date
                                if dated_diagnostic is not None
                                else None
                            ),
                        )
                    except Exception as exc:  # noqa: BLE001 - readout is best-effort
                        readout = None
                        readout_error = type(exc).__name__
                    if readout is not None:
                        context["fcv_readout"] = readout
                        context["_emit"](
                            "fcv_readout_generated",
                            {"theme_count": len(readout.key_themes)},
                        )
                    else:
                        context["_emit"](
                            "fcv_readout_unavailable", {"error": readout_error}
                        )
            if name == "build_evidence":
                return build_uploaded_evidence(context)
            if name == "map":
                return map_uploaded_diagnostic(context)
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
        evidence_by_id = (
            {item.evidence_id: item for item in context["evidence_pack"].evidence}
            if "evidence_pack" in context
            else None
        )
        evidence_ids = (
            set(evidence_by_id) if evidence_by_id is not None else None
        )

        def repair_once(current_issues):
            context["result"] = review_engine.repair(
                context["result"],
                current_issues,
                forbidden_phrases=matched_prohibited_policy_phrases(
                    result_text(context["result"]),
                    prohibited_terms,
                ),
                evidence_ids=evidence_ids,
                evidence=evidence_by_id,
            )
            context["result"] = _preserve_research_limitation(context)
            return review_validation_issues(context)

        remaining_issues = repair_once(issues)
        remaining_fatal = [
            issue for issue in remaining_issues if issue.get("severity") != "advisory"
        ]
        if _can_retry_mechanical_repair(remaining_fatal):
            remaining_issues = repair_once(remaining_fatal)
        context["validation_issues"] = remaining_issues
        return context

    orchestrator = ReviewOrchestrator(
        steps=tuple((name, mark_step(name)) for name in STEP_NAMES),
        repair=repair,
    )
    return {
        "follow_on_gateway": follow_on_gateway,
        "review_orchestrator": orchestrator,
        "registry_bundle": bundle,
        "research_controller": research_controller,
    }
