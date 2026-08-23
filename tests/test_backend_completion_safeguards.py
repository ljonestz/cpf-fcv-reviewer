from cpf_fcv_reviewer.app import create_app
from cpf_fcv_reviewer.session_store import VolatileSessionStore
from cpf_fcv_reviewer.routes import run_assessment


class RecordingStore(VolatileSessionStore):
    def __init__(self):
        super().__init__(ttl_seconds=60)
        self.operations = []

    def update(self, session_id, **values):
        self.operations.append(("update", values.copy()))
        return super().update(session_id, **values)

    def emit(self, session_id, event_type, data):
        self.operations.append(("emit", event_type, data.copy()))
        return super().emit(session_id, event_type, data)


class NoopQueue:
    mode = "noop"

    def enqueue(self, assessment_id):
        return None


class FakeResult:
    def model_dump(self, mode):
        assert mode == "json"
        return {"overall_read": "complete"}


class CompletingOrchestrator:
    def run(self, context, emit):
        emit("step_start", {"step": "review"})
        emit("step_complete", {"step": "review"})
        emit("run_complete", {"repair_count": 0})
        return {"result": FakeResult(), "evidence_by_id": {}}


def test_production_requires_persistence_without_an_injected_store():
    try:
        create_app(
            {
                "APP_ENV": "production",
                "TESTING": False,
                "ANTHROPIC_API_KEY": "test-key",
                "PERSISTENCE_PATH": "",
            },
            services={},
        )
    except RuntimeError as exc:
        assert str(exc) == (
            "Production requires PERSISTENCE_PATH or an explicitly injected session_store."
        )
    else:
        raise AssertionError("production app must fail without durable session storage")

def test_production_allows_explicit_volatile_prototype_mode():
    app = create_app(
        {
            "APP_ENV": "production",
            "TESTING": False,
            "ANTHROPIC_API_KEY": "test-key",
            "PERSISTENCE_PATH": "",
            "ALLOW_VOLATILE_PROTOTYPE": True,
            "START_BACKGROUND_RUNS": False,
        },
        services={},
    )

    assert isinstance(app.extensions["session_store"], VolatileSessionStore)
    assert app.extensions["assessment_queue"].mode == "in_process"


def test_production_accepts_an_explicitly_injected_test_store_without_a_path():
    injected_store = VolatileSessionStore(ttl_seconds=60)
    app = create_app(
        {
            "APP_ENV": "production",
            "TESTING": False,
            "ANTHROPIC_API_KEY": "test-key",
            "PERSISTENCE_PATH": "",
            "START_BACKGROUND_RUNS": False,
        },
        services={"session_store": injected_store},
    )

    assert app.extensions["session_store"] is injected_store


def test_run_complete_is_emitted_only_after_complete_state_is_durable():
    store = RecordingStore()
    app = create_app(
        {"TESTING": True, "START_BACKGROUND_RUNS": False},
        services={"session_store": store, "assessment_queue": NoopQueue()},
    )
    app.extensions["review_orchestrator"] = CompletingOrchestrator()
    assessment_id = store.create({"status": "created"})

    run_assessment(app, assessment_id)

    complete_index = next(
        index
        for index, operation in enumerate(store.operations)
        if operation[0] == "update" and operation[1].get("status") == "complete"
    )
    terminal_index = next(
        index
        for index, operation in enumerate(store.operations)
        if operation[0] == "emit" and operation[1] == "run_complete"
    )

    assert complete_index < terminal_index
    assert store.get(assessment_id).payload == {
        "status": "complete",
        "result": {"overall_read": "complete"},
        "evidence_by_id": {},
    }
