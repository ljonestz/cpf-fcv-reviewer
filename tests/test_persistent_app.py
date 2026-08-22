from cpf_fcv_reviewer.app import create_app


def test_two_app_instances_share_persisted_assessment(tmp_path):
    database = tmp_path / "reviews.sqlite3"
    config = {
        "TESTING": True,
        "START_BACKGROUND_RUNS": False,
        "PERSISTENCE_PATH": str(database),
    }
    first = create_app(config)
    assessment_id = first.extensions["session_store"].create(
        {"status": "complete", "country": "Haiti", "result": {"saved": True}}
    )

    second = create_app(config)

    assert second.extensions["session_store"].get(assessment_id).payload == {
        "status": "complete",
        "country": "Haiti",
        "result": {"saved": True},
    }
    assert second.test_client().get("/health").get_json() == {
        "status": "ok",
        "release": "dev",
        "storage": "persistent",
        "queue": "in_process",
    }
