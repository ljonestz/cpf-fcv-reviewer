from __future__ import annotations

import json
from threading import Thread
from time import sleep

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

from .session_store import SessionExpired

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
    return jsonify(result)


@bp.post("/api/reviews/<assessment_id>/corrections")
def add_correction(assessment_id):
    body = request.get_json(silent=True) or {}
    text = body.get("text", "")
    if not isinstance(text, str) or not text.strip():
        return jsonify(error="Correction text is required."), 400
    correction = {
        "label": "User-provided correction",
        "text": text.strip(),
        "affected_finding_id": body.get("affected_finding_id"),
        "rationale": body.get("rationale"),
    }
    try:
        state = store().get(assessment_id)
    except SessionExpired:
        return jsonify(error="Assessment expired."), 410
    corrections = [*state.payload.get("corrections", ()), correction]
    store().update(
        assessment_id,
        corrections=corrections,
        status="rerun_requested",
    )
    return jsonify(correction), 201


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
            store().update(
                assessment_id,
                result=result_context["result"].model_dump(mode="json"),
                status="complete",
            )
        except SessionExpired:
            return
        except Exception:
            try:
                store().update(assessment_id, status="failed")
            except SessionExpired:
                return
