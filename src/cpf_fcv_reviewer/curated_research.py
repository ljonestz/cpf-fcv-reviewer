from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from html.parser import HTMLParser
from math import isfinite
from numbers import Real
from threading import Lock
from time import monotonic as default_monotonic
from typing import Any
from urllib.parse import urlencode, urlsplit
from xml.etree import ElementTree

import httpx

from .public_research import (
    MAX_SOURCE_EXCERPT_CHARACTERS,
    CurrentContextClaim,
    ResearchSource,
    _is_public_http_url,
    _publisher_for_source_url,
    _source_mentions_country,
)
from .research_controller import ResearchRequest


_ALLOWED_HOSTS = frozenset(
    {"api.worldbank.org", "api.reliefweb.int", "www.crisisgroup.org"}
)
_CRISIS_GROUP_FEEDS = {
    "brazil": "https://www.crisisgroup.org/rss/176",
    "congo": "https://www.crisisgroup.org/rss/115",
    "cote d'ivoire": "https://www.crisisgroup.org/rss/22",
    "democratic republic of congo": "https://www.crisisgroup.org/rss/7",
    "democratic republic of the congo": "https://www.crisisgroup.org/rss/7",
    "guinea": "https://www.crisisgroup.org/rss/23",
    "india": "https://www.crisisgroup.org/rss/123",
    "indonesia": "https://www.crisisgroup.org/rss/44",
    "kenya": "https://www.crisisgroup.org/rss/11",
    "kosovo": "https://www.crisisgroup.org/rss/68",
    "sao tome and principe": "https://www.crisisgroup.org/rss/154",
    "são tomé and príncipe": "https://www.crisisgroup.org/rss/154",
    "somalia": "https://www.crisisgroup.org/rss/12",
    "türkiye": "https://www.crisisgroup.org/rss/58",
    "turkey": "https://www.crisisgroup.org/rss/58",
    "west bank and gaza": "https://www.crisisgroup.org/rss/91",
}
_RELIEFWEB_COUNTRIES = {
    "democratic republic of congo": "Democratic Republic of the Congo",
    "democratic republic of the congo": "Democratic Republic of the Congo",
    "palestinian territories": "occupied Palestinian territory",
    "west bank and gaza": "occupied Palestinian territory",
    "west bank & gaza": "occupied Palestinian territory",
    "são tomé and príncipe": "Sao Tome and Principe",
    "sao tome and principe": "Sao Tome and Principe",
}
_FCV_TITLE_PATTERN = re.compile(
    r"\b(?:conflicts?|violence|violent|political|governance|government|elections?|coup|"
    r"humanitarian|displacement|displaced|refugees?|protection|peace|peacebuilding|"
    r"insecurity)\b|\bland (?:conflict|dispute|tenure)\b|\bsocial cohesion\b|"
    r"\bsecurity (?:update|situation|incident|threat|forces?|sector|crisis|risk)\b",
    re.IGNORECASE,
)
_FCV_ASSERTION_PATTERN = re.compile(
    r"\b(?:affects?|affected|causes?|caused|delays?|delayed|disrupts?|disrupted|exposes?|"
    r"increases?|increased|worsens?|worsened|displaces?|displaced|threatens?|threatened)\b",
    re.IGNORECASE,
)

# Keep this table explicit and small. The labels and context kinds are metadata for
# observations, not interpretations of the returned values.
WORLDBANK_INDICATORS = (
    ("SP.POP.TOTL", "Population, total", "structural_dynamic"),
    ("NY.GDP.PCAP.CD", "GDP per capita (current US$)", "current_development"),
    ("SP.DYN.LE00.IN", "Life expectancy at birth, total (years)", "current_development"),
)


class InstitutionalClientError(RuntimeError):
    """Safe, provider-neutral error for bounded institutional HTTP requests."""


class _InstitutionalResponseShapeError(ValueError):
    """Expected failure for malformed institutional response structures."""


class BoundedInstitutionalClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 8.0,
        max_bytes: int = 500_000,
        client: Any | None = None,
        transport: httpx.BaseTransport | None = None,
        monotonic: Any = default_monotonic,
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
        if not callable(monotonic):
            raise ValueError("monotonic must be callable.")
        self.monotonic = monotonic
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
        deadline: float | None = None,
    ) -> object:
        _validate_institutional_url(url)
        timeout = self._timeout_for(deadline)
        try:
            with self._client.stream(
                "GET",
                url,
                params=params,
                timeout=timeout,
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
        except (httpx.TimeoutException, TimeoutError):
            raise TimeoutError("Institutional request timed out.") from None
        except (httpx.HTTPError, OSError):
            raise InstitutionalClientError("Institutional request failed.") from None

        try:
            return json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise InstitutionalClientError("Institutional response was not valid JSON.") from None

    def get_bytes(
        self,
        url: str,
        *,
        params: Mapping[str, object] | Sequence[tuple[str, object]] | None = None,
        deadline: float | None = None,
        content_types: frozenset[str],
    ) -> bytes:
        _validate_institutional_url(url)
        timeout = self._timeout_for(deadline)
        try:
            with self._client.stream(
                "GET",
                url,
                params=params,
                timeout=timeout,
                follow_redirects=False,
            ) as response:
                if not 200 <= response.status_code < 300:
                    raise InstitutionalClientError(
                        "Institutional response status was not acceptable."
                    )
                content_type = str(
                    _header(response.headers, "content-type") or ""
                ).split(";", 1)[0]
                if content_type.strip().casefold() not in content_types:
                    raise InstitutionalClientError(
                        "Institutional response content type was not acceptable."
                    )
                _check_content_length(
                    _header(response.headers, "content-length"), self.max_bytes
                )
                return _read_bounded_body(response, self.max_bytes)
        except InstitutionalClientError:
            raise
        except (httpx.TimeoutException, TimeoutError):
            raise TimeoutError("Institutional request timed out.") from None
        except (httpx.HTTPError, OSError):
            raise InstitutionalClientError("Institutional request failed.") from None

    def _timeout_for(self, deadline: float | None) -> httpx.Timeout:
        if deadline is None:
            return self.timeout
        if isinstance(deadline, bool) or not isinstance(deadline, Real) or not isfinite(deadline):
            raise ValueError("Institutional deadline must be finite.")
        remaining = float(deadline) - self.monotonic()
        if remaining <= 0:
            raise TimeoutError("Institutional request deadline expired.")
        seconds = min(self.timeout_seconds, remaining)
        return httpx.Timeout(connect=seconds, read=seconds, write=seconds, pool=seconds)

    def close(self) -> None:
        close = getattr(self._client, "close", None)
        if callable(close):
            close()


class WorldBankAdapter:
    def __init__(self, client: BoundedInstitutionalClient) -> None:
        self.client = client
        self._country_name_to_iso3: dict[str, str] | None = None
        self._country_mapping_lock = Lock()

    def search(
        self, request: ResearchRequest, *, deadline: float | None = None
    ) -> tuple[CurrentContextClaim, ...]:
        iso3 = self._resolve_country(request.country, deadline=deadline)
        if iso3 is None:
            return ()

        claims: list[CurrentContextClaim] = []
        indicator_failures: list[BaseException] = []
        successful_indicator_queries = 0
        for indicator_id, label, context_kind in WORLDBANK_INDICATORS:
            try:
                payload = _get_json(
                    self.client,
                    f"https://api.worldbank.org/v2/country/{iso3}/indicator/{indicator_id}",
                    params={"format": "json", "per_page": "5"},
                    deadline=deadline,
                )
                indicator_claims = _world_bank_claims(
                    payload,
                    request=request,
                    iso3=iso3,
                    indicator_id=indicator_id,
                    fallback_label=label,
                    context_kind=context_kind,
                )
            except (
                InstitutionalClientError,
                TimeoutError,
                _InstitutionalResponseShapeError,
            ) as exc:
                indicator_failures.append(exc)
                continue
            successful_indicator_queries += 1
            claims.extend(indicator_claims)
        if indicator_failures and successful_indicator_queries == 0:
            if all(isinstance(error, TimeoutError) for error in indicator_failures):
                raise TimeoutError("World Bank indicator queries timed out.")
            raise InstitutionalClientError("World Bank indicator queries failed.")
        return tuple(claims)

    def _resolve_country(self, country: str, *, deadline: float | None = None) -> str | None:
        key = _country_key(country)
        if self._country_name_to_iso3 is None:
            with self._country_mapping_lock:
                if self._country_name_to_iso3 is None:
                    if deadline is None:
                        self._country_name_to_iso3 = self._load_country_mapping()
                    else:
                        self._country_name_to_iso3 = self._load_country_mapping(
                            deadline=deadline
                        )
        return self._country_name_to_iso3.get(key)

    def _load_country_mapping(self, *, deadline: float | None = None) -> dict[str, str]:
        payload = _get_json(
            self.client,
            "https://api.worldbank.org/v2/country",
            params={"format": "json", "per_page": "400"},
            deadline=deadline,
        )
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
            raise _InstitutionalResponseShapeError("Institutional response shape was invalid.")

        mapping: dict[str, str] = {}
        for row in payload[1]:
            if not isinstance(row, Mapping):
                continue
            name = _nonblank_string(row.get("name"))
            iso3 = _iso3(row.get("id"))
            region = row.get("region")
            region_id = (
                _nonblank_string(region.get("id"))
                if isinstance(region, Mapping)
                else None
            )
            region_value = (
                _nonblank_string(region.get("value"))
                if isinstance(region, Mapping)
                else None
            )
            if (
                name is None
                or iso3 is None
                or region_id is None
                or region_id.casefold() == "na"
                or (region_value is not None and region_value.casefold() == "aggregates")
            ):
                continue
            mapping.setdefault(_country_key(name), iso3)
        return mapping


class CrisisGroupAdapter:
    def __init__(self, client: BoundedInstitutionalClient) -> None:
        self.client = client

    def supports(self, country: str) -> bool:
        return _country_key(country) in _CRISIS_GROUP_FEEDS

    def search(
        self, request: ResearchRequest, *, deadline: float | None = None
    ) -> tuple[CurrentContextClaim, ...]:
        feed_url = _CRISIS_GROUP_FEEDS.get(_country_key(request.country))
        if feed_url is None:
            return ()
        payload = self.client.get_bytes(
            feed_url,
            deadline=deadline,
            content_types=frozenset(
                {"application/rss+xml", "application/xml", "text/xml"}
            ),
        )
        try:
            root = ElementTree.fromstring(payload)
        except ElementTree.ParseError:
            raise _InstitutionalResponseShapeError(
                "Institutional response shape was invalid."
            ) from None

        start_date = _subtract_years(request.review_date, 2)
        claims: list[CurrentContextClaim] = []
        for item in root.findall("./channel/item"):
            claim = _crisis_group_claim(
                item,
                expected_country=request.country,
                start_date=start_date,
                end_date=request.review_date,
            )
            if claim is not None:
                claims.append(claim)
        return tuple(claims)


class ReliefWebAdapter:
    def __init__(self, client: BoundedInstitutionalClient, app_name: str | None) -> None:
        self.client = client
        self.app_name = (app_name or "").strip()

    def search(
        self, request: ResearchRequest, *, deadline: float | None = None
    ) -> tuple[CurrentContextClaim, ...]:
        if not self.app_name:
            return ()
        if _has_control_character(self.app_name):
            raise ValueError("ReliefWeb app name is invalid.")

        start_date = _subtract_years(request.review_date, 2)
        country = _reliefweb_country_name(request.country)
        params = [
            ("appname", self.app_name),
            ("preset", "minimal"),
            ("query[value]", country),
            ("query[fields][]", "primary_country"),
            ("filter[operator]", "AND"),
            ("filter[conditions][0][field]", "primary_country"),
            ("filter[conditions][0][value]", country),
            ("filter[conditions][1][field]", "date.original"),
            ("filter[conditions][1][value][from]", f"{start_date.isoformat()}T00:00:00+00:00"),
            ("filter[conditions][1][value][to]", f"{request.review_date.isoformat()}T23:59:59+00:00"),
            ("fields[include][]", "title"),
            ("fields[include][]", "url"),
            ("fields[include][]", "date.original"),
            ("fields[include][]", "primary_country.name"),
            ("fields[include][]", "source.name"),
            ("fields[include][]", "origin"),
            ("fields[include][]", "body"),
            ("limit", "20"),
            ("sort[]", "date.original:desc"),
        ]
        payload = _get_json(
            self.client,
            "https://api.reliefweb.int/v2/reports", params=params, deadline=deadline
        )
        if not isinstance(payload, Mapping) or not isinstance(payload.get("data"), list):
            raise _InstitutionalResponseShapeError("Institutional response shape was invalid.")

        claims: list[CurrentContextClaim] = []
        for row in payload["data"]:
            claim = _reliefweb_claim(
                row,
                expected_country=country,
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
        self.client = client
        self.crisis_group = CrisisGroupAdapter(client)
        self.reliefweb = ReliefWebAdapter(client, reliefweb_app_name)

    def search(
        self,
        request: ResearchRequest,
        *,
        timeout_seconds: float | None = None,
    ) -> tuple[CurrentContextClaim, ...]:
        deadline = None
        if timeout_seconds is not None:
            if (
                isinstance(timeout_seconds, bool)
                or not isinstance(timeout_seconds, Real)
                or not isfinite(timeout_seconds)
                or timeout_seconds <= 0
            ):
                raise ValueError("Recovery timeout must be a finite positive number.")
            deadline = self.client.monotonic() + float(timeout_seconds)
        candidates: list[CurrentContextClaim] = []
        adapters = (
            [self.crisis_group]
            if self.crisis_group.supports(request.country)
            else []
        )
        if self.reliefweb.app_name:
            adapters.append(self.reliefweb)
        adapter_failures: list[BaseException] = []
        for adapter in adapters:
            try:
                if deadline is None:
                    claims = adapter.search(request)
                else:
                    claims = adapter.search(request, deadline=deadline)
            except (
                InstitutionalClientError,
                TimeoutError,
                _InstitutionalResponseShapeError,
            ) as exc:
                adapter_failures.append(exc)
                continue
            candidates.extend(claims)

        if (
            not candidates
            and adapter_failures
            and len(adapter_failures) == len(adapters)
        ):
            if all(isinstance(error, TimeoutError) for error in adapter_failures):
                raise TimeoutError("Curated institutional research timed out.")
            raise InstitutionalClientError("Curated institutional research failed.")

        by_id: dict[str, CurrentContextClaim] = {}
        by_source_url: dict[str, CurrentContextClaim] = {}
        # The lexicographically smallest complete claim key is the deterministic winner.
        for claim in sorted(candidates, key=_claim_stable_key):
            if claim.claim_id in by_id:
                continue
            if claim.source_url is not None and claim.source_url in by_source_url:
                continue
            by_id[claim.claim_id] = claim
            if claim.source_url is not None:
                by_source_url[claim.source_url] = claim
        return tuple(
            sorted(
                by_id.values(),
                key=_claim_stable_key,
            )
        )


def _get_json(
    client: Any,
    url: str,
    *,
    params: Mapping[str, object] | Sequence[tuple[str, object]] | None,
    deadline: float | None,
) -> object:
    if deadline is None:
        return client.get_json(url, params=params)
    return client.get_json(url, params=params, deadline=deadline)


def _claim_stable_key(claim: CurrentContextClaim) -> tuple[object, ...]:
    """Return every claim field in a total, deterministic ordering key."""

    return (
        claim.claim_id,
        claim.text,
        claim.publisher,
        claim.source_title,
        claim.source_url or "",
        claim.source_date.isoformat(),
        claim.supporting_quote or "",
        claim.publication_date_basis or "",
        claim.source_type,
        claim.relevance,
        claim.context_kind,
        claim.relationship,
        claim.licensed_data_required,
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
    except (httpx.TimeoutException, TimeoutError):
        raise TimeoutError("Institutional request timed out.") from None
    except (httpx.HTTPError, OSError):
        raise InstitutionalClientError("Institutional request failed.") from None
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
        raise _InstitutionalResponseShapeError("Institutional response shape was invalid.")

    claims: list[CurrentContextClaim] = []
    source_url_base = f"https://api.worldbank.org/v2/country/{iso3}/indicator/{indicator_id}"
    for row in payload[1]:
        if not isinstance(row, Mapping):
            continue
        value = _explicit_value(row.get("value"))
        observation_date = _world_bank_date(row.get("date"))
        if (
            value is None
            or observation_date is None
            or observation_date > request.review_date
        ):
            continue
        response_indicator = row.get("indicator")
        if (
            not isinstance(response_indicator, Mapping)
            or response_indicator.get("id") != indicator_id
        ):
            continue
        response_label = _nonblank_string(response_indicator.get("value"))
        label = response_label or fallback_label
        row_iso3 = _iso3(row.get("countryiso3code"))
        if row_iso3 != iso3:
            continue
        source_url = f"{source_url_base}?{urlencode({'date': observation_date.year})}"
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
    expected_country: str,
    start_date: date,
    end_date: date,
) -> CurrentContextClaim | None:
    if not isinstance(row, Mapping) or not isinstance(row.get("fields"), Mapping):
        return None
    fields = row["fields"]
    title = _nonblank_string(fields.get("title"))
    source_url = _nonblank_string(fields.get("origin"))
    source_date = _reliefweb_date(fields.get("date"))
    summary = _bounded_report_text(fields.get("body"))
    country_names = _reliefweb_country_names(fields.get("primary_country"))
    source_names = _reliefweb_source_names(fields.get("source"))
    publisher = (
        _publisher_for_source_url(source_url)
        if source_url is not None and _is_public_http_url(source_url)
        else None
    )
    if (
        title is None
        or source_url is None
        or source_date is None
        or summary is None
        or _FCV_TITLE_PATTERN.search(summary) is None
        or expected_country.casefold()
        not in {country.casefold() for country in country_names}
        or not source_names
        or publisher is None
        or not start_date <= source_date <= end_date
    ):
        return None

    digest = hashlib.sha256(f"{source_url}|{source_date.isoformat()}".encode()).hexdigest()
    attribution = ", ".join(source_names)
    return CurrentContextClaim(
        claim_id=f"reliefweb:{digest}",
        text=summary,
        publisher=publisher,
        source_title=title,
        source_url=source_url,
        source_date=source_date,
        supporting_quote=summary,
        publication_date_basis="provider_metadata",
        source_type="institutional public report",
        relevance=f"Original report attributed to {attribution}; distributed by ReliefWeb.",
        context_kind="current_development",
        relationship="establishes",
        licensed_data_required=False,
    )


def _crisis_group_claim(
    item: ElementTree.Element,
    *,
    expected_country: str,
    start_date: date,
    end_date: date,
) -> CurrentContextClaim | None:
    title = _nonblank_string(item.findtext("title"))
    source_url = _nonblank_string(item.findtext("link"))
    source_date = _crisis_group_date(item.findtext("pubDate"))
    summary = _bounded_report_text(item.findtext("description"))
    text = summary or (f"{title}." if title is not None else None)
    if (
        title is None
        or source_url is None
        or not _is_crisis_group_result_url(source_url)
        or source_date is None
        or text is None
        or not _source_mentions_country(
            ResearchSource(
                title=title,
                url=source_url,
                excerpt=text,
            ),
            expected_country,
        )
        or _FCV_TITLE_PATTERN.search(text) is None
        or (summary is None and _FCV_ASSERTION_PATTERN.search(title) is None)
        or not start_date <= source_date <= end_date
    ):
        return None

    digest = hashlib.sha256(
        f"{source_url}|{source_date.isoformat()}".encode()
    ).hexdigest()
    return CurrentContextClaim(
        claim_id=f"crisisgroup:{digest}",
        text=text,
        publisher="International Crisis Group",
        source_title=title,
        source_url=source_url,
        source_date=source_date,
        supporting_quote=text,
        publication_date_basis="provider_metadata",
        source_type="think tank analysis",
        relevance="Country-specific conflict and political analysis.",
        context_kind="current_development",
        relationship="establishes",
        licensed_data_required=False,
    )


def _crisis_group_date(value: object) -> date | None:
    text = _nonblank_string(value)
    if text is None:
        return None
    try:
        return datetime.strptime(text, "%A, %B %d, %Y - %H:%M").date()
    except ValueError:
        return None


def _is_crisis_group_result_url(url: str) -> bool:
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
        and hostname == "www.crisisgroup.org"
        and parsed.username is None
        and parsed.password is None
        and not parsed.fragment
        and port in (None, 443)
    )


def _country_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def _iso3(value: object) -> str | None:
    if not isinstance(value, str) or len(value) != 3:
        return None
    return value.upper() if value.isascii() and value.isalpha() else None


def _nonblank_string(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _explicit_value(value: object) -> int | float | None:
    if type(value) not in (int, float) or not isfinite(value):
        return None
    return value


def _world_bank_date(value: object) -> date | None:
    if not isinstance(value, str) or len(value.strip()) != 4 or not value.strip().isdigit():
        return None
    try:
        return date(int(value), 1, 1)
    except ValueError:
        return None


def _reliefweb_country_name(country: str) -> str:
    normalized = _country_key(country)
    return _RELIEFWEB_COUNTRIES.get(normalized, country.strip())


def _reliefweb_date(value: object) -> date | None:
    if not isinstance(value, Mapping):
        return None
    value = value.get("original")
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


def _reliefweb_country_names(value: object) -> tuple[str, ...]:
    items = value if isinstance(value, list) else [value]
    return tuple(
        name
        for item in items
        if isinstance(item, Mapping)
        if (name := _nonblank_string(item.get("name"))) is not None
    )


def _reliefweb_source_names(value: object) -> tuple[str, ...]:
    items = value if isinstance(value, list) else [value]
    names = (
        name
        for item in items
        if isinstance(item, Mapping)
        if (name := _nonblank_string(item.get("name"))) is not None
    )
    return tuple(dict.fromkeys(names))


class _ReportTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in {"script", "style"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def _bounded_report_text(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    parser = _ReportTextParser()
    parser.feed(value)
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    if not text:
        return None
    if len(text) <= MAX_SOURCE_EXCERPT_CHARACTERS:
        return text
    sentence_ends = tuple(
        match.end()
        for match in re.finditer(
            r"[.!?](?=\s|$)", text[:MAX_SOURCE_EXCERPT_CHARACTERS]
        )
    )
    return text[: sentence_ends[-1]].strip() if sentence_ends else None


def _has_control_character(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _subtract_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        return value.replace(year=value.year - years, day=28)
