from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from math import isfinite
from numbers import Real
from typing import Any
from urllib.parse import urlsplit

import httpx

from .public_research import CurrentContextClaim
from .research_controller import ResearchRequest


_ALLOWED_HOSTS = frozenset({"api.worldbank.org", "api.reliefweb.int"})
_RELIEFWEB_RESULT_HOSTS = frozenset({"reliefweb.int", "api.reliefweb.int"})

# Keep this table explicit and small. The labels and context kinds are metadata for
# observations, not interpretations of the returned values.
WORLDBANK_INDICATORS = (
    ("SP.POP.TOTL", "Population, total", "structural_dynamic"),
    ("NY.GDP.PCAP.CD", "GDP per capita (current US$)", "current_development"),
    ("SP.DYN.LE00.IN", "Life expectancy at birth, total (years)", "current_development"),
)


class InstitutionalClientError(ValueError):
    """Safe, provider-neutral error for bounded institutional HTTP requests."""


class BoundedInstitutionalClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 8.0,
        max_bytes: int = 500_000,
        client: Any | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, Real)
            or not isfinite(timeout_seconds)
        ):
            raise ValueError("Institutional timeout must be a finite positive number.")
        if timeout_seconds <= 0:
            raise ValueError("Institutional timeout must be a finite positive number.")
        if type(max_bytes) is not int or not 10_000 <= max_bytes <= 2_000_000:
            raise ValueError("Institutional response cap is outside the allowed range.")
        if client is not None and transport is not None:
            raise ValueError("Provide an institutional client or transport, not both.")

        self.timeout_seconds = float(timeout_seconds)
        self.max_bytes = max_bytes
        self.timeout = httpx.Timeout(
            connect=self.timeout_seconds,
            read=self.timeout_seconds,
            write=self.timeout_seconds,
            pool=self.timeout_seconds,
        )
        self._client = (
            client
            if client is not None
            else httpx.Client(
                transport=transport,
                timeout=self.timeout,
                follow_redirects=False,
            )
        )

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, object] | Sequence[tuple[str, object]] | None = None,
    ) -> object:
        _validate_institutional_url(url)
        try:
            with self._client.stream(
                "GET",
                url,
                params=params,
                timeout=self.timeout,
                follow_redirects=False,
            ) as response:
                if not 200 <= response.status_code < 300:
                    raise InstitutionalClientError("Institutional response status was not acceptable.")
                content_type = str(_header(response.headers, "content-type") or "").split(";", 1)[0]
                if content_type.strip().casefold() not in {"application/json", "text/json"}:
                    raise InstitutionalClientError("Institutional response content was not JSON.")
                _check_content_length(_header(response.headers, "content-length"), self.max_bytes)
                body = _read_bounded_body(response, self.max_bytes)
        except InstitutionalClientError:
            raise
        except (httpx.HTTPError, TimeoutError):
            raise InstitutionalClientError("Institutional request failed.") from None
        except Exception:
            raise InstitutionalClientError("Institutional request failed.") from None

        try:
            return json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise InstitutionalClientError("Institutional response was not valid JSON.") from None

    def close(self) -> None:
        close = getattr(self._client, "close", None)
        if callable(close):
            close()


class WorldBankAdapter:
    def __init__(self, client: BoundedInstitutionalClient) -> None:
        self.client = client
        self._country_name_to_iso3: dict[str, str] | None = None

    def search(self, request: ResearchRequest) -> tuple[CurrentContextClaim, ...]:
        iso3 = self._resolve_country(request.country)
        if iso3 is None:
            return ()

        claims: list[CurrentContextClaim] = []
        for indicator_id, label, context_kind in WORLDBANK_INDICATORS:
            payload = self.client.get_json(
                f"https://api.worldbank.org/v2/country/{iso3}/indicator/{indicator_id}",
                params={"format": "json", "per_page": "5"},
            )
            claims.extend(
                _world_bank_claims(
                    payload,
                    request=request,
                    iso3=iso3,
                    indicator_id=indicator_id,
                    fallback_label=label,
                    context_kind=context_kind,
                )
            )
        return tuple(claims)

    def _resolve_country(self, country: str) -> str | None:
        key = _country_key(country)
        if self._country_name_to_iso3 is None:
            self._country_name_to_iso3 = self._load_country_mapping()
        return self._country_name_to_iso3.get(key)

    def _load_country_mapping(self) -> dict[str, str]:
        payload = self.client.get_json(
            "https://api.worldbank.org/v2/country",
            params={"format": "json", "per_page": "400"},
        )
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
            raise ValueError("Institutional response shape was invalid.")

        mapping: dict[str, str] = {}
        for row in payload[1]:
            if not isinstance(row, Mapping):
                continue
            name = _nonblank_string(row.get("name"))
            iso3 = _iso3(row.get("iso3Code")) or _iso3(row.get("id"))
            if name is None or iso3 is None:
                continue
            mapping.setdefault(_country_key(name), iso3)
        return mapping


class ReliefWebAdapter:
    def __init__(self, client: BoundedInstitutionalClient, app_name: str | None) -> None:
        self.client = client
        self.app_name = (app_name or "").strip()

    def search(self, request: ResearchRequest) -> tuple[CurrentContextClaim, ...]:
        if not self.app_name:
            return ()
        if _has_control_character(self.app_name):
            raise ValueError("ReliefWeb app name is invalid.")

        start_date = _subtract_years(request.review_date, 2)
        country = request.country.strip()
        params = [
            ("appname", self.app_name),
            ("preset", "minimal"),
            ("query[value]", country),
            ("query[fields][]", "primary_country"),
            ("filter[operator]", "AND"),
            ("filter[conditions][0][field]", "primary_country"),
            ("filter[conditions][0][value]", country),
            ("filter[conditions][1][field]", "date.created"),
            ("filter[conditions][1][value][from]", f"{start_date.isoformat()}T00:00:00+00:00"),
            ("filter[conditions][1][value][to]", f"{request.review_date.isoformat()}T23:59:59+00:00"),
            ("filter[conditions][2][field]", "source"),
            ("fields[include][]", "title"),
            ("fields[include][]", "url"),
            ("fields[include][]", "date.created"),
            ("fields[include][]", "source.name"),
            ("limit", "20"),
            ("sort[]", "date.created:desc"),
        ]
        payload = self.client.get_json("https://api.reliefweb.int/v2/reports", params=params)
        if not isinstance(payload, Mapping) or not isinstance(payload.get("data"), list):
            raise ValueError("Institutional response shape was invalid.")

        claims: list[CurrentContextClaim] = []
        for row in payload["data"]:
            claim = _reliefweb_claim(
                row,
                start_date=start_date,
                end_date=request.review_date,
            )
            if claim is not None:
                claims.append(claim)
        return tuple(claims)


class CuratedResearchGateway:
    def __init__(
        self,
        client: BoundedInstitutionalClient,
        *,
        reliefweb_app_name: str | None = None,
    ) -> None:
        self.world_bank = WorldBankAdapter(client)
        self.reliefweb = ReliefWebAdapter(client, reliefweb_app_name)

    def search(self, request: ResearchRequest) -> tuple[CurrentContextClaim, ...]:
        by_id: dict[str, CurrentContextClaim] = {}
        for adapter in (self.world_bank, self.reliefweb):
            try:
                claims = adapter.search(request)
            except Exception:
                continue
            for claim in claims:
                by_id.setdefault(claim.claim_id, claim)
        return tuple(
            sorted(
                by_id.values(),
                key=lambda claim: (
                    claim.claim_id,
                    claim.source_date,
                    claim.source_url or "",
                    claim.text,
                ),
            )
        )


def _validate_institutional_url(url: str) -> None:
    if not isinstance(url, str) or _has_control_character(url):
        raise ValueError("Institutional URL is not allowed.")
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        raise ValueError("Institutional URL is not allowed.") from None
    if (
        parsed.scheme.casefold() != "https"
        or hostname is None
        or hostname.casefold() not in _ALLOWED_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or port not in (None, 443)
    ):
        raise ValueError("Institutional URL is not allowed.")


def _check_content_length(raw_length: object, max_bytes: int) -> None:
    if raw_length is None:
        return
    try:
        content_length = int(str(raw_length).strip())
    except (TypeError, ValueError):
        raise InstitutionalClientError("Institutional response length was invalid.") from None
    if content_length < 0 or content_length > max_bytes:
        raise InstitutionalClientError("Institutional response exceeded the configured size.")


def _header(headers: Any, name: str) -> object | None:
    try:
        value = headers.get(name)
    except Exception:
        value = None
    if value is not None:
        return value
    try:
        for key, value in headers.items():
            if str(key).casefold() == name.casefold():
                return value
    except Exception:
        return None
    return None


def _read_bounded_body(response: Any, max_bytes: int) -> bytes:
    body = bytearray()
    try:
        chunks = response.iter_bytes()
        for chunk in chunks:
            if not isinstance(chunk, (bytes, bytearray, memoryview)):
                raise InstitutionalClientError("Institutional response body was invalid.")
            if len(body) + len(chunk) > max_bytes:
                raise InstitutionalClientError("Institutional response exceeded the configured size.")
            body.extend(chunk)
    except InstitutionalClientError:
        raise
    except (httpx.HTTPError, TimeoutError):
        raise InstitutionalClientError("Institutional request failed.") from None
    except Exception:
        raise InstitutionalClientError("Institutional response body was invalid.") from None
    return bytes(body)


def _world_bank_claims(
    payload: object,
    *,
    request: ResearchRequest,
    iso3: str,
    indicator_id: str,
    fallback_label: str,
    context_kind: str,
) -> tuple[CurrentContextClaim, ...]:
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
        raise ValueError("Institutional response shape was invalid.")

    claims: list[CurrentContextClaim] = []
    source_url = f"https://api.worldbank.org/v2/country/{iso3}/indicator/{indicator_id}"
    for row in payload[1]:
        if not isinstance(row, Mapping):
            continue
        value = _explicit_value(row.get("value"))
        observation_date = _world_bank_date(row.get("date"))
        if value is None or observation_date is None:
            continue
        response_indicator = row.get("indicator")
        response_label = (
            _nonblank_string(response_indicator.get("value"))
            if isinstance(response_indicator, Mapping)
            else None
        )
        label = response_label or fallback_label
        raw_iso3 = row.get("countryiso3code")
        if raw_iso3 is not None:
            row_iso3 = _iso3(raw_iso3)
            if row_iso3 is None or row_iso3 != iso3:
                continue
        claims.append(
            CurrentContextClaim(
                claim_id=f"worldbank:{iso3}:{indicator_id}:{observation_date.isoformat()}",
                text=f"{label}: {value} ({row['date']}).",
                publisher="World Bank",
                source_title=label,
                source_url=source_url,
                source_date=observation_date,
                source_type="institutional public data",
                relevance="Explicit World Bank indicator observation.",
                context_kind=context_kind,
                relationship="establishes",
                licensed_data_required=False,
            )
        )
    return tuple(claims)


def _reliefweb_claim(
    row: object,
    *,
    start_date: date,
    end_date: date,
) -> CurrentContextClaim | None:
    if not isinstance(row, Mapping) or not isinstance(row.get("fields"), Mapping):
        return None
    fields = row["fields"]
    title = _nonblank_string(fields.get("title"))
    source_url = _nonblank_string(fields.get("url"))
    source_name = _reliefweb_source_name(fields.get("source"))
    source_date = _reliefweb_date(fields.get("date"))
    if (
        title is None
        or source_url is None
        or source_name is None
        or source_date is None
        or not _is_reliefweb_result_url(source_url)
        or not start_date <= source_date <= end_date
    ):
        return None

    digest = hashlib.sha256(f"{source_url}|{source_date.isoformat()}".encode()).hexdigest()
    return CurrentContextClaim(
        claim_id=f"reliefweb:{digest}",
        text=f"{title}.",
        publisher="ReliefWeb",
        source_title=title,
        source_url=source_url,
        source_date=source_date,
        source_type="institutional public report",
        relevance=f"ReliefWeb report explicitly attributed to {source_name}.",
        context_kind="current_development",
        relationship="establishes",
        licensed_data_required=False,
    )


def _country_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def _iso3(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip().upper()
    return value if len(value) == 3 and value.isascii() and value.isalpha() else None


def _nonblank_string(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _explicit_value(value: object) -> str | int | float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Real):
        return value if value == value and value not in (float("inf"), float("-inf")) else None
    return None


def _world_bank_date(value: object) -> date | None:
    if not isinstance(value, str) or len(value.strip()) != 4 or not value.strip().isdigit():
        return None
    try:
        return date(int(value), 1, 1)
    except ValueError:
        return None


def _reliefweb_date(value: object) -> date | None:
    if isinstance(value, Mapping):
        value = value.get("created") or value.get("original")
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None


def _reliefweb_source_name(value: object) -> str | None:
    if isinstance(value, Mapping):
        return _nonblank_string(value.get("name"))
    if isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                name = _nonblank_string(item.get("name"))
                if name is not None:
                    return name
    return None


def _is_reliefweb_result_url(url: str) -> bool:
    if _has_control_character(url):
        return False
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return False
    return bool(
        parsed.scheme.casefold() == "https"
        and hostname in _RELIEFWEB_RESULT_HOSTS
        and parsed.username is None
        and parsed.password is None
        and not parsed.fragment
        and port in (None, 443)
    )


def _has_control_character(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _subtract_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        return value.replace(year=value.year - years, day=28)
