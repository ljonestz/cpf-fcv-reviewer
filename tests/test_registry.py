from pathlib import Path

import pytest

from cpf_fcv_reviewer.registry import (
    RegistryUnavailable,
    hydrate_referrals,
    load_registry_bundle,
)

FIXTURE = Path("tests/fixtures/registry_bundle.synthetic.json")


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
