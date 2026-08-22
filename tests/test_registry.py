import copy
import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from cpf_fcv_reviewer.registry import (
    RegistryUnavailable,
    hydrate_referrals,
    load_registry_bundle,
)

FIXTURE = Path("tests/fixtures/registry_bundle.synthetic.json")
PUBLIC_BUNDLE = Path("registry_bundles/cpf_fcv_reviewer_public_guardrails_v1.1.0.json")
PUBLIC_BUNDLE_HASH = Path(
    "registry_bundles/cpf_fcv_reviewer_public_guardrails_v1.1.0.sha256"
)


def registry_data() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def write_bundle(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_synthetic_bundle_is_allowed_only_in_tests():
    bundle = load_registry_bundle(FIXTURE, allow_synthetic=True)
    assert bundle.owner == "Synthetic OPCS Test Owner"

    with pytest.raises(RegistryUnavailable, match="Synthetic registry"):
        load_registry_bundle(FIXTURE, allow_synthetic=False)


def test_referral_language_is_hydrated_exactly_from_registry():
    bundle = load_registry_bundle(FIXTURE, allow_synthetic=True)
    hydrated = hydrate_referrals(("SYN-REF-001",), bundle)

    assert hydrated == (
        {
            "entry_id": "SYN-REF-001",
            "approved_text": "Consult the designated policy owner.",
            "version": "1.0.0-test",
        },
    )


def test_unknown_registry_id_fails_closed():
    bundle = load_registry_bundle(FIXTURE, allow_synthetic=True)
    with pytest.raises(RegistryUnavailable, match="Unknown registry entry"):
        hydrate_referrals(("MISSING",), bundle)


def test_duplicate_registry_entry_ids_are_rejected(tmp_path):
    data = registry_data()
    data["entries"].append(data["entries"][0].copy())

    with pytest.raises(RegistryUnavailable, match="Approved registry bundle is invalid"):
        load_registry_bundle(write_bundle(tmp_path, data), allow_synthetic=True)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("bundle_id", "  "),
        ("version", "  "),
        ("owner", "  "),
        ("entry_id", "  "),
        ("approved_text", "  "),
        ("prohibited_terms", ["  "]),
    ],
)
def test_registry_rejects_whitespace_only_required_text(tmp_path, field, value):
    data = registry_data()
    target = (
        data["entries"][0] if field in {"entry_id", "approved_text", "prohibited_terms"} else data
    )
    target[field] = value

    with pytest.raises(RegistryUnavailable, match="Approved registry bundle is invalid"):
        load_registry_bundle(write_bundle(tmp_path, data), allow_synthetic=True)


def test_registry_preserves_meaningful_approved_text_exactly(tmp_path):
    data = registry_data()
    approved_text = "  Consult the designated policy owner.  "
    data["entries"][0]["approved_text"] = approved_text

    bundle = load_registry_bundle(write_bundle(tmp_path, data), allow_synthetic=True)

    assert bundle.entries[0].approved_text == approved_text
    assert hydrate_referrals(("SYN-REF-001",), bundle)[0]["approved_text"] == approved_text


@pytest.mark.parametrize(
    "content",
    [
        b'{"bundle_id":',
        b'{"bundle_id": "synthetic-opcs-test"}',
        b"\xff\xfe\x00",
    ],
)
def test_registry_normalizes_unreadable_or_invalid_bundle_content(tmp_path, content):
    path = tmp_path / "registry.json"
    path.write_bytes(content)

    with pytest.raises(RegistryUnavailable, match="^Approved registry bundle is invalid\\.$"):
        load_registry_bundle(path, allow_synthetic=True)


def test_registry_normalizes_directory_read_error(tmp_path):
    with pytest.raises(RegistryUnavailable, match="^Approved registry bundle is invalid\\.$"):
        load_registry_bundle(tmp_path, allow_synthetic=True)


@pytest.mark.parametrize(
    ("approved_at", "expires_at"),
    [
        ("2026-08-10T00:00:00", "2099-01-01T00:00:00Z"),
        ("2026-08-10T00:00:00Z", "2099-01-01T00:00:00"),
        ("2099-01-01T00:00:00Z", "2026-08-10T00:00:00Z"),
        ("2026-08-10T00:00:00Z", "2026-08-10T00:00:00Z"),
    ],
)
def test_registry_requires_ordered_timezone_aware_approval_dates(tmp_path, approved_at, expires_at):
    data = registry_data()
    data["approved_at"] = approved_at
    data["expires_at"] = expires_at

    with pytest.raises(RegistryUnavailable, match="Approved registry bundle is invalid"):
        load_registry_bundle(write_bundle(tmp_path, data), allow_synthetic=True)


def test_hydrated_referrals_are_immutable_dict_compatible_and_json_serializable():
    bundle = load_registry_bundle(FIXTURE, allow_synthetic=True)
    referral = hydrate_referrals(("SYN-REF-001",), bundle)[0]

    assert referral == {
        "entry_id": "SYN-REF-001",
        "approved_text": "Consult the designated policy owner.",
        "version": "1.0.0-test",
    }
    with pytest.raises(TypeError):
        referral["approved_text"] = "Replacement"
    assert json.loads(json.dumps(referral)) == dict(referral)
    assert copy.deepcopy(referral) == referral


def test_registry_rejects_string_synthetic_flag(tmp_path):
    data = registry_data()
    data["synthetic"] = "false"

    with pytest.raises(RegistryUnavailable, match="^Approved registry bundle is invalid\\.$"):
        load_registry_bundle(write_bundle(tmp_path, data), allow_synthetic=True)


@pytest.mark.parametrize("allow_synthetic", ["false", 0, None])
def test_registry_rejects_non_bool_synthetic_permission(tmp_path, allow_synthetic):
    with pytest.raises(RegistryUnavailable, match="^Approved registry bundle is invalid\\.$"):
        load_registry_bundle(
            write_bundle(tmp_path, registry_data()), allow_synthetic=allow_synthetic
        )


def test_registry_rejects_naive_now(tmp_path):
    with pytest.raises(RegistryUnavailable, match="^Approved registry bundle is invalid\\.$"):
        load_registry_bundle(
            write_bundle(tmp_path, registry_data()),
            allow_synthetic=True,
            now=datetime(2026, 8, 10),
        )


def test_registry_normalizes_existence_check_error(monkeypatch):
    def raising_exists(self):
        raise OSError("unavailable path")

    monkeypatch.setattr(Path, "exists", raising_exists)

    with pytest.raises(RegistryUnavailable, match="^Approved registry bundle is invalid\\.$"):
        load_registry_bundle(FIXTURE, allow_synthetic=True)


def test_checked_in_public_guardrail_bundle_is_valid_and_hash_pinned():
    expected_hash = PUBLIC_BUNDLE_HASH.read_text(encoding="utf-8").strip()
    assert sha256(PUBLIC_BUNDLE.read_bytes()).hexdigest() == expected_hash

    bundle = load_registry_bundle(
        PUBLIC_BUNDLE,
        allow_synthetic=False,
        now=datetime(2026, 8, 12, tzinfo=UTC),
        expected_hash=expected_hash,
    )

    assert bundle.bundle_id == "cpf-fcv-reviewer-public-guardrails"
    assert bundle.version == "1.1.0"
    assert bundle.synthetic is False
    assert tuple(entry.entry_id for entry in bundle.entries) == (
        "PUB-GUARD-001",
        "PUB-GUARD-002",
        "PUB-GUARD-003",
        "PUB-GUARD-004",
        "PUB-FCV-STRAT-001",
        "PUB-FCV-STRAT-002",
        "PUB-FCV-STRAT-003",
        "PUB-FCV-STRAT-004",
    )
