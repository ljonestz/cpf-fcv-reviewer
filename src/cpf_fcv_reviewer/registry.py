from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator


class RegistryUnavailable(RuntimeError):
    pass


class ImmutableReferral(dict[str, str]):
    @staticmethod
    def _immutable(*args: object, **kwargs: object) -> None:
        raise TypeError("Hydrated referrals are immutable.")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable

    def copy(self) -> ImmutableReferral:
        return self

    def __copy__(self) -> ImmutableReferral:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> ImmutableReferral:
        return self


class RegistryEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    entry_id: str
    approved_text: str
    prohibited_terms: tuple[str, ...] = ()

    @field_validator("entry_id", "approved_text")
    @classmethod
    def requires_nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Registry text cannot be blank.")
        return value

    @field_validator("prohibited_terms")
    @classmethod
    def requires_nonblank_prohibited_terms(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not term.strip() for term in value):
            raise ValueError("Registry prohibited terms cannot be blank.")
        return value


class RegistryBundle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    bundle_id: str
    version: str
    owner: str
    approved_at: datetime
    expires_at: datetime
    synthetic: bool
    entries: tuple[RegistryEntry, ...]

    @field_validator("bundle_id", "version", "owner")
    @classmethod
    def requires_nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Registry bundle text cannot be blank.")
        return value

    @model_validator(mode="after")
    def requires_valid_entries_and_dates(self) -> RegistryBundle:
        if self.approved_at.tzinfo is None or self.approved_at.utcoffset() is None:
            raise ValueError("Registry approval time must be timezone-aware.")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise ValueError("Registry expiry time must be timezone-aware.")
        if self.approved_at >= self.expires_at:
            raise ValueError("Registry approval time must precede expiry time.")
        entry_ids = tuple(entry.entry_id for entry in self.entries)
        if len(entry_ids) != len(set(entry_ids)):
            raise ValueError("Registry entry IDs must be unique.")
        return self

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
    try:
        bundle = RegistryBundle.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValidationError):
        raise RegistryUnavailable("Approved registry bundle is invalid.") from None
    if bundle.synthetic and not allow_synthetic:
        raise RegistryUnavailable("Synthetic registry bundles are test-only.")
    if bundle.expires_at <= (now or datetime.now(UTC)):
        raise RegistryUnavailable("Registry bundle has expired.")
    return bundle


def hydrate_referrals(
    entry_ids: tuple[str, ...],
    bundle: RegistryBundle,
) -> tuple[ImmutableReferral, ...]:
    entries = bundle.by_id()
    hydrated: list[ImmutableReferral] = []
    for entry_id in entry_ids:
        if entry_id not in entries:
            raise RegistryUnavailable(f"Unknown registry entry: {entry_id}")
        entry = entries[entry_id]
        hydrated.append(
            ImmutableReferral(
                {
                    "entry_id": entry.entry_id,
                    "approved_text": entry.approved_text,
                    "version": bundle.version,
                }
            )
        )
    return tuple(hydrated)
