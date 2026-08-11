from __future__ import annotations

import json
from datetime import UTC, datetime
from io import BytesIO
from threading import Thread
from time import sleep
from uuid import uuid4

from flask import Blueprint, Response, current_app, jsonify, request, send_file, stream_with_context

from .contracts import EvidenceItem, ReviewResult
from .export_docx import build_docx
from .priority_questions import detect_priority_questions
from .registry import hydrate_referrals
from .session_store import SessionExpired
from .validators import validate_reproducibility_metadata

bp = Blueprint("reviews", __name__)


def store():
    return current_app.extensions["session_store"]


@bp.post("/api/reviews")
def create_review():
    cpf = request.files.get("cpf")
    if cpf is None:
        return jsonify(error="A primary CPF/CEN is required."), 400
    payload = {
        "country": request.form.get("country", "").strip(),
        "review_stage": request.form.get("review_stage", "").strip(),
        "cpf": {"name": cpf.filename, "bytes": cpf.read()},
        "supporting": [
            {"name": item.filename, "bytes": item.read()}
            for item in request.files.getlist("supporting")
        ],
        "guidance": request.form.get("guidance", "").strip(),
        "priority_questions": detect_priority_questions(
            "\n".join(request.form.getlist("priority_questions"))
        ),
        "corrections": [],
        "status": "created",
    }
    assessment_id = store().create(payload)
    base = f"/api/reviews/{assessment_id}"

    if current_app.config["START_BACKGROUND_RUNS"]:
        app = current_app._get_current_object()
        Thread(
            target=run_assessment,
            args=(app, assessment_id),
            daemon=True,
        ).start()

    return (
        jsonify(
            assessment_id=assessment_id,
            event_url=f"{base}/events",
            result_url=f"{base}/result",
        ),
        201,
    )


@bp.get("/api/reviews/<assessment_id>/events")
def review_events(assessment_id):
    def generate():
        while True:
            try:
                event = store().next_event(assessment_id)
            except SessionExpired:
                yield "event: expired\ndata: {}\n\n"
                return
            if event:
                yield (f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n")
                if event["type"] in {"run_complete", "run_failed"}:
                    return
            else:
                yield "event: keepalive\ndata: {}\n\n"
                sleep(15)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@bp.get("/api/reviews/<assessment_id>/result")
def review_result(assessment_id):
    try:
        state = store().get(assessment_id)
    except SessionExpired:
        return jsonify(error="Assessment expired."), 410
    result = state.payload.get("result")
    if result is None:
        return jsonify(status=state.payload.get("status", "created")), 202
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
        for finding in validated_result.findings
        for evidence_id in finding.evidence_ids
    ):
        return jsonify(error="Traceable evidence is invalid."), 409

    response_payload = validated_result.model_dump(mode="json")
    response_payload["evidence_by_id"] = validated_evidence
    return jsonify(response_payload)


@bp.get("/api/reviews/<assessment_id>/export.docx")
def export_review(assessment_id):
    try:
        state = store().get(assessment_id)
    except SessionExpired:
        return jsonify(error="Assessment expired."), 410
    result_payload = state.payload.get("result")
    if result_payload is None:
        return jsonify(status=state.payload.get("status", "created")), 202
    evidence_payload = state.payload.get("evidence_by_id")
    if not isinstance(evidence_payload, dict):
        return jsonify(error="Traceable evidence is unavailable."), 409

    try:
        result = ReviewResult.model_validate(result_payload)
    except ValueError:
        return jsonify(error="Review result is invalid."), 409
    if validate_reproducibility_metadata(result.metadata):
        return jsonify(error="Reproducibility metadata is incomplete."), 409
    evidence = {
        evidence_id: EvidenceItem.model_validate(item)
        for evidence_id, item in evidence_payload.items()
    }
    bundle = current_app.extensions["registry_bundle"]
    try:
        data = build_docx(
            result,
            evidence=evidence,
            hydrated_referrals=hydrate_referrals(
                result.institutional_referral_ids,
                bundle,
            ),
        )
    except Exception:
        return jsonify(error="DOCX export failed."), 500
    return send_file(
        BytesIO(data),
        mimetype=("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        as_attachment=True,
        download_name="CPF-FCV-Review.docx",
    )


@bp.post("/api/reviews/<assessment_id>/corrections")
def add_correction(assessment_id):
    try:
        parent = store().get(assessment_id)
    except SessionExpired:
        return jsonify(error="Assessment expired."), 410

    body = request.get_json(silent=True) or {}
    text = body.get("text", "")
    if not isinstance(text, str) or not text.strip():
        return jsonify(error="Correction text is required."), 400

    child_payload = dict(parent.payload)
    child_payload["corrections"] = list(parent.payload.get("corrections", ()))
    child_payload["corrections"].append(
        {
            "correction_id": uuid4().hex,
            "created_at": datetime.now(UTC).isoformat(),
            "label": "User-provided correction",
            "text": text.strip(),
            "affected_finding_id": body.get("affected_finding_id"),
            "rationale": body.get("rationale"),
            "independently_supported": False,
        }
    )
    child_payload["parent_assessment_id"] = assessment_id
    child_payload["status"] = "created"
    child_payload.pop("result", None)
    child_payload.pop("evidence_by_id", None)

    child_id = store().create(child_payload)
    if current_app.config["START_BACKGROUND_RUNS"]:
        app = current_app._get_current_object()
        Thread(target=run_assessment, args=(app, child_id), daemon=True).start()
    base = f"/api/reviews/{child_id}"
    return (
        jsonify(
            assessment_id=child_id,
            parent_assessment_id=assessment_id,
            event_url=f"{base}/events",
            result_url=f"{base}/result",
        ),
        201,
    )


@bp.delete("/api/reviews/<assessment_id>")
def reset_review(assessment_id):
    store().delete(assessment_id)
    return "", 204


def run_assessment(app, assessment_id):
    with app.app_context():
        try:
            state = store().get(assessment_id)
            orchestrator = current_app.extensions["review_orchestrator"]
            result_context = orchestrator.run(
                {"assessment_id": assessment_id, "payload": state.payload},
                lambda kind, data: store().emit(assessment_id, kind, data),
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
                status="complete",
            )
        except SessionExpired:
            return
        except Exception:
            try:
                store().update(assessment_id, status="failed")
            except SessionExpired:
                return
