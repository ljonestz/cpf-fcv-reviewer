from __future__ import annotations

import json
import unicodedata
from collections.abc import Mapping
from datetime import UTC, datetime
from io import BytesIO
from ipaddress import ip_address
from threading import RLock
from time import monotonic, sleep
from uuid import uuid4

from flask import (
    Blueprint, Response, current_app, jsonify, request, send_file, stream_with_context, url_for,
)

from .admission import AdmissionDenied
from .background import AssessmentQueueFull
from .contracts import DetailLevel, EvidenceItem, ReviewResult
from .country_detection import (
    COUNTRY_DETECTION_MAX_ARCHIVE_MEMBERS,
    COUNTRY_DETECTION_MAX_CHARACTERS,
    COUNTRY_DETECTION_MAX_PDF_PAGES,
    COUNTRY_DETECTION_MAX_SEGMENTS,
    COUNTRY_DETECTION_MAX_UNCOMPRESSED_BYTES,
    COUNTRY_DETECTION_MAX_UPLOAD_BYTES,
    detect_country,
)
from .export_docx import (
    EvidenceCompletenessError,
    build_docx,
    validate_evidence_completeness,
)
from .extraction import extract_document, require_readable_primary
from .orchestrator import safe_failure_code, safe_failure_data
from .session_store import SessionExpired
from .review_profiles import STAGE_PROFILES
from .validators import validate_reproducibility_metadata

bp = Blueprint("reviews", __name__)

CORRECTION_TEXT_MAX_LENGTH = 2000
CORRECTION_PRIORITY_AREA_MAX_LENGTH = 200
CORRECTION_RATIONALE_MAX_LENGTH = 1000
RETRYABLE_RESEARCH_CODES = {
    "research_provider_failed",
    "research_timeout",
    "research_malformed",
    "research_insufficient",
}
LEGACY_REVIEW_RESULT_ERROR = (
    "This review was created by an earlier version. Start a new review."
)
EVENT_STREAM_KEEPALIVE_SECONDS = 5
ASSISTANT_MESSAGE_MAX_LENGTH = 10_000
ASSISTANT_HISTORY_MAX_MESSAGES = 20
ASSISTANT_RETRY_MESSAGE = "The assistant could not complete that response. Please try again."
ASSISTANT_PROCESS_OWNER = uuid4().hex
_ASSISTANT_REQUEST_LOCK = RLock()


def _reject_legacy_result(result_payload):
    if isinstance(result_payload, Mapping) and "strategy_readout" not in result_payload:
        return jsonify(error=LEGACY_REVIEW_RESULT_ERROR), 409
    return None


def store():
    return current_app.extensions["session_store"]


def admission():
    return current_app.extensions["public_admission"]


def client_address():
    # Only enable behind Render's Cloudflare edge, which overwrites this header.
    if current_app.config["TRUST_RENDER_PROXY"]:
        try:
            return str(ip_address(request.headers.get("CF-Connecting-IP", "")))
        except ValueError:
            pass
    return request.remote_addr or "unknown"


@bp.errorhandler(AdmissionDenied)
def admission_denied(error):
    response = jsonify(error=error.message, code=error.code)
    response.status_code = error.status
    response.headers["Retry-After"] = str(error.retry_after)
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.before_request
def limit_upload_requests():
    if request.method == "POST":
        admission().check_and_record("request", client_address())


def _release_once(slot):
    lock, released = RLock(), False
    def release():
        nonlocal released
        with lock:
            if not released:
                released = True
                slot.release()
    return release


def _submit_payload(payload):
    guard = admission()
    session_store = store()
    with guard.lock:
        guard.require_capacity(session_store)
        guard.check_and_record("review", client_address())
        assessment_id = session_store.create(payload() if callable(payload) else payload)
        try:
            current_app.extensions["assessment_queue"].enqueue(assessment_id)
        except AssessmentQueueFull:
            session_store.discard_one(assessment_id)
            raise AdmissionDenied("assessment_queue_full", "The assessment queue is full. Try later.",
                                  status=503) from None
        return assessment_id


def _partial_research_keys(payload: dict) -> tuple[str, ...]:
    return tuple(
        key
        for key in payload
        if key.startswith("research_") or key.endswith("_research")
    )


def _assistant_context(payload: dict):
    if payload.get("status") != "complete":
        raise ValueError("Review is not complete.")
    result_payload = payload.get("result")
    if not isinstance(result_payload, Mapping) or "strategy_readout" not in result_payload:
        raise ValueError("Review result is unavailable.")
    evidence_payload = payload.get("evidence_by_id")
    if not isinstance(evidence_payload, dict):
        raise ValueError("Traceable evidence is unavailable.")

    result = ReviewResult.model_validate(result_payload)
    evidence = {
        evidence_id: EvidenceItem.model_validate(item)
        for evidence_id, item in evidence_payload.items()
    }
    if any(
        evidence_id != item.evidence_id
        for evidence_id, item in evidence.items()
    ):
        raise ValueError("Traceable evidence is invalid.")
    referenced_ids = {
        evidence_id
        for assessment in (
            *result.priority_areas,
            *result.rra_driver_assessments,
            *result.fcv_strategy_assessments,
        )
        for evidence_id in assessment.evidence_ids
    }
    if not referenced_ids <= set(evidence):
        raise ValueError("Traceable evidence is incomplete.")

    history_payload = payload.get("assistant_history", [])
    if not isinstance(history_payload, list):
        raise ValueError("Assistant history is invalid.")
    history = []
    for item in history_payload[-ASSISTANT_HISTORY_MAX_MESSAGES:]:
        if (
            not isinstance(item, dict)
            or item.get("role") not in {"user", "assistant"}
            or not isinstance(item.get("content"), str)
        ):
            raise ValueError("Assistant history is invalid.")
        history.append({"role": item["role"], "content": item["content"]})

    relevant_evidence = {
        evidence_id: evidence[evidence_id].model_dump(mode="json")
        for evidence_id in sorted(referenced_ids)
    }
    return (
        result.model_dump(mode="json"),
        relevant_evidence,
        tuple(history),
    )


@bp.get("/api/reviews/<assessment_id>/assistant")
def assistant_history(assessment_id):
    try:
        state = store().get(assessment_id)
        _, _, history = _assistant_context(state.payload)
    except SessionExpired:
        return jsonify(error="Assessment expired."), 410
    except ValueError:
        return jsonify(error="Assistant is available after a completed review."), 409
    response = jsonify(list(history))
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.post("/api/reviews/<assessment_id>/assistant")
def assistant_response(assessment_id):
    body = request.get_json(silent=True)
    message = body.get("message") if isinstance(body, dict) else None
    if not isinstance(message, str) or not message.strip():
        return jsonify(error="Assistant message is required."), 400
    message = message.strip()
    if len(message) > ASSISTANT_MESSAGE_MAX_LENGTH:
        return jsonify(error="Assistant message is too long."), 400

    session_store = store()
    application = current_app._get_current_object()
    with _ASSISTANT_REQUEST_LOCK:
        try:
            state = session_store.get(assessment_id)
            review, evidence, history = _assistant_context(state.payload)
        except SessionExpired:
            return jsonify(error="Assessment expired."), 410
        except ValueError:
            return jsonify(error="Assistant is available after a completed review."), 409
        if (
            state.payload.get("assistant_active") is True
            and state.payload.get("assistant_active_owner") == ASSISTANT_PROCESS_OWNER
        ):
            return jsonify(error="An assistant response is already in progress."), 409
        gateway = current_app.extensions.get("follow_on_gateway")
        if gateway is None:
            return jsonify(error="Assistant is temporarily unavailable."), 503
        slot = admission().assistant_slots
        if not slot.acquire(blocking=False):
            raise AdmissionDenied("assistant_busy", "The assistant is busy. Try again shortly.", status=503)
        release_slot = _release_once(slot)
        try:
            admission().check_and_record("assistant", client_address(),
                                         assessment_id=assessment_id)
        except Exception:
            release_slot()
            raise
        cleanup_lock = RLock()
        cleaned_up = False

        def cleanup():
            nonlocal cleaned_up
            with cleanup_lock:
                if cleaned_up:
                    return
                cleaned_up = True
            release_slot()
            try:
                session_store.update(
                    assessment_id,
                    assistant_active=False,
                    assistant_active_owner=None,
                )
            except Exception as error:
                application.logger.error(
                    "assistant_state_cleanup_failed error_type=%s",
                    type(error).__name__,
                )

        try:
            session_store.update(
                assessment_id,
                assistant_active=True,
                assistant_active_owner=ASSISTANT_PROCESS_OWNER,
            )
        except Exception as error:
            cleanup()
            application.logger.error(
                "assistant_state_start_failed error_type=%s",
                type(error).__name__,
            )
            return jsonify(error="Assistant is temporarily unavailable."), 503

    def generate():
        chunks = []
        try:
            for chunk in gateway.stream(
                review=review,
                evidence=evidence,
                history=history,
                message=message,
            ):
                if not isinstance(chunk, str) or not chunk:
                    continue
                chunks.append(chunk)
                yield f"event: chunk\ndata: {json.dumps({'text': chunk})}\n\n"
            response_text = "".join(chunks)
            if not response_text:
                raise RuntimeError("Assistant returned an empty response.")
            updated_history = [
                *history,
                {"role": "user", "content": message},
                {"role": "assistant", "content": response_text},
            ][-ASSISTANT_HISTORY_MAX_MESSAGES:]
            session_store.update(assessment_id, assistant_history=updated_history)
            yield "event: done\ndata: {}\n\n"
        except SessionExpired:
            expired_payload = {
                "error": "This review expired before the response was saved.",
                "retryable": False,
            }
            yield (
                "event: error\ndata: "
                f"{json.dumps(expired_payload)}\n\n"
            )
        except Exception as error:
            application.logger.error(
                "follow_on_assistant_failed error_type=%s", type(error).__name__
            )
            yield (
                "event: error\ndata: "
                f"{json.dumps({'error': ASSISTANT_RETRY_MESSAGE, 'retryable': True})}\n\n"
            )
        finally:
            cleanup()

    response = Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-store"},
    )
    response.call_on_close(cleanup)
    return response


@bp.post("/api/reviews/<assessment_id>/retry-research")
def retry_research(assessment_id):
    guard = admission()
    session_store = store()
    with guard.lock:
        try:
            state = session_store.get(assessment_id)
            if (state.payload.get("status") != "failed"
                    or state.payload.get("failure_code") not in RETRYABLE_RESEARCH_CODES):
                return jsonify(error="Research retry is unavailable."), 409
            guard.require_capacity(session_store)
            guard.check_and_record("review", client_address())
            session_store.reset_failed_research(assessment_id, RETRYABLE_RESEARCH_CODES)
        except SessionExpired:
            return jsonify(error="Assessment expired."), 410
        try:
            current_app.extensions["assessment_queue"].enqueue(assessment_id)
        except AssessmentQueueFull:
            failure_code = state.payload["failure_code"]
            try:
                session_store.update(assessment_id, **state.payload)
                session_store.emit(
                    assessment_id, "run_failed", {"error": failure_code}
                )
            except Exception as error:
                current_app.logger.error(
                    "research_retry_restore_failed error_type=%s",
                    type(error).__name__,
                )
            raise AdmissionDenied(
                "assessment_queue_full",
                "The assessment queue is full. Try later.",
                status=503,
            ) from None

    return (
        jsonify(
            assessment_id=assessment_id,
            event_url=url_for(".review_events", assessment_id=assessment_id),
            result_url=url_for(".review_result", assessment_id=assessment_id),
        ),
        202,
    )


@bp.post("/api/detect-country")
def detect_country_from_upload():
    cpf = request.files.get("cpf")
    if cpf is None or not cpf.filename:
        return jsonify(error="A readable primary CPF/CEN is required."), 400

    try:
        data = cpf.read(COUNTRY_DETECTION_MAX_UPLOAD_BYTES + 1)
        if len(data) > COUNTRY_DETECTION_MAX_UPLOAD_BYTES:
            raise ValueError("Country detector upload budget exceeded.")
        document = extract_document(
            data,
            cpf.filename,
            max_pdf_pages=COUNTRY_DETECTION_MAX_PDF_PAGES,
            max_segments=COUNTRY_DETECTION_MAX_SEGMENTS,
            max_characters=COUNTRY_DETECTION_MAX_CHARACTERS,
            max_uncompressed_bytes=COUNTRY_DETECTION_MAX_UNCOMPRESSED_BYTES,
            max_archive_members=COUNTRY_DETECTION_MAX_ARCHIVE_MEMBERS,
        )
        require_readable_primary(document)
    except Exception:
        return jsonify(error="A readable primary CPF/CEN is required."), 400

    detection = detect_country(document)
    return jsonify(
        country=detection.country,
        requires_confirmation=detection.confidence != "high",
    )


@bp.post("/api/reviews")
def create_review():
    cpf = request.files.get("cpf")
    if cpf is None:
        return jsonify(error="A primary CPF/CEN is required."), 400
    country = request.form.get("country", "").strip()
    if not country:
        return jsonify(error="Country is required."), 400
    if len(country) > 100 or any(
        unicodedata.category(character).startswith("C") for character in country
    ):
        return jsonify(error="Country is invalid."), 400

    try:
        detail_level = DetailLevel(
            request.form.get("detail_level", DetailLevel.STANDARD)
        )
    except ValueError:
        return jsonify(error="Unsupported detail level."), 400
    review_stage = request.form.get("review_stage", "").strip()
    if review_stage not in STAGE_PROFILES:
        return jsonify(error="Unsupported review stage."), 400

    def uploaded_files(field_name: str) -> list[dict[str, object]]:
        return [
            {"name": item.filename, "bytes": item.read()}
            for item in request.files.getlist(field_name)
            if item.filename
        ]

    def payload():
        return {
            "country": country,
            "review_stage": review_stage,
            "detail_level": detail_level.value,
            "cpf": {"name": cpf.filename, "bytes": cpf.read()},
            "package_documents": uploaded_files("package_documents"),
            "context_documents": uploaded_files("context_documents"),
            "review_focus": request.form.get("review_focus", "").strip()[:4000],
            "corrections": [],
            "status": "created",
        }
    assessment_id = _submit_payload(payload)

    return (
        jsonify(
            assessment_id=assessment_id,
            event_url=url_for(".review_events", assessment_id=assessment_id),
            result_url=url_for(".review_result", assessment_id=assessment_id),
        ),
        201,
    )


@bp.get("/api/reviews/<assessment_id>/events")
def review_events(assessment_id):
    slot = admission().stream_slots
    if not slot.acquire(blocking=False):
        raise AdmissionDenied("event_stream_limit", "Too many active review connections. Try shortly.",
                              status=503, retry_after=5)
    release_slot = _release_once(slot)
    raw_cursor = request.headers.get("Last-Event-ID") or request.args.get("after", "0")
    try:
        initial_cursor = max(0, int(raw_cursor))
    except (TypeError, ValueError):
        initial_cursor = 0

    deadline = monotonic() + current_app.config["EVENT_STREAM_MAX_SECONDS"]

    def generate():
        cursor = initial_cursor
        while True:
            try:
                events = store().read_events(assessment_id, after=cursor)
            except SessionExpired:
                yield "event: expired\ndata: {}\n\n"
                return
            if events:
                for sequence, event in events:
                    cursor = sequence
                    yield (
                        f"id: {sequence}\nevent: {event['type']}\n"
                        f"data: {json.dumps(event['data'])}\n\n"
                    )
                    if event["type"] in {"run_complete", "run_failed"}:
                        return
            else:
                yield "event: keepalive\ndata: {}\n\n"
                if monotonic() + EVENT_STREAM_KEEPALIVE_SECONDS > deadline:
                    return
                sleep(EVENT_STREAM_KEEPALIVE_SECONDS)

    def leased_events():
        try:
            yield from generate()
        finally:
            release_slot()

    response = Response(
        stream_with_context(leased_events()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
    response.call_on_close(release_slot)
    return response


@bp.get("/api/reviews/<assessment_id>/result")
def review_result(assessment_id):
    try:
        state = store().get(assessment_id)
    except SessionExpired:
        return jsonify(error="Assessment expired."), 410
    result = state.payload.get("result")
    if result is None:
        return jsonify(status=state.payload.get("status", "created")), 202
    legacy_response = _reject_legacy_result(result)
    if legacy_response is not None:
        return legacy_response
    try:
        validated_result = ReviewResult.model_validate(result)
    except ValueError:
        return jsonify(error="Review result is invalid."), 409
    if validate_reproducibility_metadata(validated_result.metadata):
        return jsonify(error="Reproducibility metadata is incomplete."), 409
    evidence_payload = state.payload.get("evidence_by_id", {})
    if not isinstance(evidence_payload, dict):
        return jsonify(error="Traceable evidence is invalid."), 409
    try:
        validated_evidence = {
            evidence_id: EvidenceItem.model_validate(item).model_dump(mode="json")
            for evidence_id, item in evidence_payload.items()
        }
    except ValueError:
        return jsonify(error="Traceable evidence is invalid."), 409
    if any(
        evidence_id != item["evidence_id"]
        for evidence_id, item in validated_evidence.items()
    ):
        return jsonify(error="Traceable evidence is invalid."), 409
    evidence_ids = set(validated_evidence)
    if any(
        evidence_id not in evidence_ids
        for area in validated_result.priority_areas
        for evidence_id in area.evidence_ids
    ):
        return jsonify(error="Traceable evidence is invalid."), 409

    response_payload = validated_result.model_dump(mode="json")
    response_payload["evidence_by_id"] = validated_evidence
    suggestions = state.payload.get("research_search_suggestions")
    if isinstance(suggestions, str) and 0 < len(suggestions) <= 30_000:
        response_payload["research_search_suggestions"] = suggestions
    return jsonify(response_payload)


@bp.get("/api/reviews/<assessment_id>/export.docx")
def export_review(assessment_id):
    view = request.args.get("view", "detailed")
    if view not in {"detailed", "summary"}:
        return jsonify(error="Unknown export view."), 400
    try:
        state = store().get(assessment_id)
    except SessionExpired:
        return jsonify(error="Assessment expired."), 410
    result_payload = state.payload.get("result")
    if result_payload is None:
        return jsonify(status=state.payload.get("status", "created")), 202
    legacy_response = _reject_legacy_result(result_payload)
    if legacy_response is not None:
        return legacy_response
    evidence_payload = state.payload.get("evidence_by_id")
    if not isinstance(evidence_payload, dict):
        return jsonify(error="Traceable evidence is unavailable."), 409

    try:
        result = ReviewResult.model_validate(result_payload)
    except ValueError:
        return jsonify(error="Review result is invalid."), 409
    if validate_reproducibility_metadata(result.metadata):
        return jsonify(error="Reproducibility metadata is incomplete."), 409
    try:
        evidence = {
            evidence_id: EvidenceItem.model_validate(item)
            for evidence_id, item in evidence_payload.items()
        }
        validate_evidence_completeness(result, evidence)
    except ValueError:
        return jsonify(error="Traceable evidence is invalid."), 409
    try:
        data = build_docx(
            result,
            evidence=evidence,
            hydrated_referrals=(),
            summary=view == "summary",
        )
    except EvidenceCompletenessError:
        return jsonify(error="Traceable evidence is invalid."), 409
    except Exception as error:
        current_app.logger.error("docx_export_failed error_type=%s", type(error).__name__)
        return jsonify(error="DOCX export failed."), 500
    return send_file(
        BytesIO(data),
        mimetype=("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        as_attachment=True,
        download_name=(
            "CPF-FCV-Five-Minute-Readout.docx" if view == "summary" else "CPF-FCV-Review.docx"
        ),
    )


@bp.post("/api/reviews/<assessment_id>/corrections")
def add_correction(assessment_id):
    try:
        parent = store().get(assessment_id)
    except SessionExpired:
        return jsonify(error="Assessment expired."), 410

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(error="Correction request is invalid."), 400
    if "affected_finding_id" in body:
        return jsonify(error="Legacy correction fields are not supported."), 400

    text = body.get("text", "")
    if not isinstance(text, str) or not text.strip():
        return jsonify(error="Correction text is required."), 400
    text = text.strip()
    if len(text) > CORRECTION_TEXT_MAX_LENGTH:
        return jsonify(error="Correction text is too long."), 400

    affected_priority_area_id = body.get("affected_priority_area_id")
    rationale = body.get("rationale")
    if affected_priority_area_id is not None and not isinstance(
        affected_priority_area_id, str
    ):
        return jsonify(error="Correction details are invalid."), 400
    if rationale is not None and not isinstance(rationale, str):
        return jsonify(error="Correction details are invalid."), 400
    if (
        isinstance(affected_priority_area_id, str)
        and len(affected_priority_area_id.strip()) > CORRECTION_PRIORITY_AREA_MAX_LENGTH
    ):
        return jsonify(error="Correction details are invalid."), 400
    if isinstance(rationale, str) and len(rationale.strip()) > CORRECTION_RATIONALE_MAX_LENGTH:
        return jsonify(error="Correction details are invalid."), 400
    if isinstance(affected_priority_area_id, str):
        affected_priority_area_id = affected_priority_area_id.strip()
    if isinstance(rationale, str):
        rationale = rationale.strip()

    child_payload = dict(parent.payload)
    child_payload["corrections"] = list(parent.payload.get("corrections", ()))
    child_payload["corrections"].append(
        {
            "correction_id": uuid4().hex,
            "created_at": datetime.now(UTC).isoformat(),
            "label": "User-provided correction",
            "text": text,
            "affected_priority_area_id": affected_priority_area_id,
            "rationale": rationale,
            "independently_supported": False,
        }
    )
    child_payload["parent_assessment_id"] = assessment_id
    child_payload["status"] = "created"
    child_payload.pop("result", None)
    child_payload.pop("research_search_suggestions", None)
    child_payload.pop("evidence_by_id", None)
    child_payload.pop("assistant_history", None)
    child_payload.pop("assistant_active", None)
    child_payload.pop("assistant_active_owner", None)

    child_id = _submit_payload(child_payload)
    return (
        jsonify(
            assessment_id=child_id,
            parent_assessment_id=assessment_id,
            event_url=url_for(".review_events", assessment_id=child_id),
            result_url=url_for(".review_result", assessment_id=child_id),
        ),
        201,
    )


@bp.delete("/api/reviews/<assessment_id>")
def reset_review(assessment_id):
    store().delete(assessment_id)
    return "", 204


def run_assessment(app, assessment_id):
    terminal_events = []

    def emit(kind, data):
        if kind in {"run_complete", "run_failed"}:
            terminal_events.append((kind, data))
            return
        store().emit(assessment_id, kind, data)

    with app.app_context():
        try:
            state = store().get(assessment_id)
            store().update(assessment_id, status="running")
            orchestrator = current_app.extensions["review_orchestrator"]
            result_context = orchestrator.run(
                {"assessment_id": assessment_id, "payload": state.payload},
                emit,
            )
            evidence_by_id = result_context.get("evidence_by_id")
            if evidence_by_id is None:
                evidence_pack = result_context.get("evidence_pack")
                if evidence_pack is not None:
                    evidence_by_id = {
                        item.evidence_id: item.model_dump(mode="json")
                        for item in evidence_pack.evidence
                    }
                else:
                    evidence_by_id = {}
            store().update(
                assessment_id,
                result=result_context["result"].model_dump(mode="json"),
                evidence_by_id=evidence_by_id,
                **({"research_search_suggestions": result_context["research_search_suggestions"]}
                   if result_context.get("research_search_suggestions") else {}),
                status="complete",
            )
            for kind, data in terminal_events:
                if kind == "run_complete":
                    store().emit(assessment_id, kind, data)
        except SessionExpired:
            return
        except Exception as exc:
            terminal_events.clear()
            failure_code = safe_failure_code(exc)
            failure_data = safe_failure_data(exc)
            schema_diagnostics = failure_data.get("schema_diagnostics")
            serialized_schema_diagnostics = (
                json.dumps(schema_diagnostics, separators=(",", ":"), sort_keys=True)
                if isinstance(schema_diagnostics, dict)
                else "none"
            )
            status_code = getattr(exc, "status_code", None)
            cause_types = []
            cause = exc.__cause__
            while cause is not None and len(cause_types) < 3:
                cause_types.append(type(cause).__name__)
                cause = cause.__cause__
            current_app.logger.error(
                "review_run_failed error_type=%s status_code=%s cause_chain=%s "
                "failure_code=%s schema_diagnostics=%s",
                type(exc).__name__,
                status_code if isinstance(status_code, int) else "none",
                ">".join(cause_types) or "none",
                failure_code,
                serialized_schema_diagnostics,
            )
            try:
                state = store().get(assessment_id)
                stale_keys = {
                    "result",
                    "evidence_by_id",
                    "research_search_suggestions",
                    "validation_issues",
                    *_partial_research_keys(state.payload),
                }
                store().remove_keys(assessment_id, *stale_keys)
                store().update(
                    assessment_id,
                    status="failed",
                    failure_code=failure_code,
                )
                store().emit(
                    assessment_id,
                    "run_failed",
                    failure_data,
                )
            except SessionExpired:
                return
