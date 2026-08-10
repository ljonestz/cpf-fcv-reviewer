from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class RegistryUnavailable(RuntimeError):
    pass


class RegistryEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    entry_id: str
    approved_text: str
    prohibited_terms: tuple[str, ...] = ()


class RegistryBundle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    bundle_id: str
    version: str
    owner: str
    approved_at: datetime
    expires_at: datetime
    synthetic: bool
    entries: tuple[RegistryEntry, ...]

    def by_id(self) -> dict[str, RegistryEntry]:
        return {entry.entry_id: entry for entry in self.entries}


def load_registry_bundle(
    path: Path,
    *,
    allow_synthetic: bool,
    now: datetime | None = None,
) -> RegistryBundle:
    if not path.exists():
        raise RegistryUnavailable("Approved registry bundle is unavailable.")
    bundle = RegistryBundle.model_validate_json(path.read_text(encoding="utf-8"))
    if bundle.synthetic and not allow_synthetic:
        raise RegistryUnavailable("Synthetic registry bundles are test-only.")
    if bundle.expires_at <= (now or datetime.now(UTC)):
        raise RegistryUnavailable("Registry bundle has expired.")
    return bundle


def hydrate_referrals(
    entry_ids: tuple[str, ...],
    bundle: RegistryBundle,
) -> tuple[dict[str, str], ...]:
    entries = bundle.by_id()
    hydrated: list[dict[str, str]] = []
    for entry_id in entry_ids:
        if entry_id not in entries:
            raise RegistryUnavailable(f"Unknown registry entry: {entry_id}")
        entry = entries[entry_id]
        hydrated.append(
            {
                "entry_id": entry.entry_id,
                "approved_text": entry.approved_text,
                "version": bundle.version,
            }
        )
    return tuple(hydrated)
