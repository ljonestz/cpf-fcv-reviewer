from hashlib import sha256
from pathlib import Path

import pytest

from cpf_fcv_reviewer.registry import RegistryUnavailable, load_registry_bundle
from cpf_fcv_reviewer.security import redact_log_value, reject_source, select_output_language

FIXTURE_ROOT = Path("tests/fixtures")
REGISTRY = FIXTURE_ROOT / "registry_bundle.synthetic.json"


@pytest.mark.parametrize("input_language", ["en", "fr", "mixed", "unknown"])
def test_review_output_is_always_english(input_language):
    assert select_output_language(input_language) == "en"


@pytest.mark.parametrize(
    "source",
    [
        {
            "provider": "ACLED",
            "license": "licensed",
            "url": "https://acleddata.com/report",
            "publication_date": "2026-08-01",
            "relevance": "Material to the named assumption.",
        },
        {
            "provider": "Public source",
            "license": "public",
            "url": "https://example.org/report",
            "publication_date": "",
            "relevance": "Material to the named assumption.",
        },
        {
            "provider": "Public source",
            "license": "public",
            "url": "https://example.org/report",
            "publication_date": "2026-08-01",
            "relevance": "  ",
        },
        {
            "provider": "Public source",
            "license": "public",
            "url": "http://127.0.0.1/report",
            "publication_date": "2026-08-01",
            "relevance": "Material to the named assumption.",
        },
    ],
)
def test_unsafe_or_incomplete_current_context_sources_are_rejected(source):
    assert reject_source(source)


def test_complete_public_source_is_not_rejected():
    assert not reject_source(
        {
            "provider": "Public source",
            "license": "public",
            "url": "https://example.org/report",
            "publication_date": "2026-08-01",
            "relevance": "Material to the named assumption.",
        }
    )


def test_log_redaction_never_returns_content():
    raw = "uploaded excerpt and user correction"
    assert redact_log_value(raw) == "[content omitted]"
    assert raw not in redact_log_value(raw)


def test_registry_loader_rejects_a_tampered_or_wrong_expected_hash():
    actual_hash = sha256(REGISTRY.read_bytes()).hexdigest()
    bundle = load_registry_bundle(
        REGISTRY,
        allow_synthetic=True,
        expected_hash=actual_hash,
    )
    assert bundle.bundle_id

    with pytest.raises(RegistryUnavailable, match="hash"):
        load_registry_bundle(
            REGISTRY,
            allow_synthetic=True,
            expected_hash="0" * 64,
        )
