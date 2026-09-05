from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Event, Lock
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from cpf_fcv_reviewer.curated_research import (
    BoundedInstitutionalClient,
    CrisisGroupAdapter,
    CuratedResearchGateway,
    InstitutionalClientError,
    WORLDBANK_INDICATORS,
    WorldBankAdapter,
)
from cpf_fcv_reviewer.research_controller import ResearchMode, ResearchRequest


class StubResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        chunks: tuple[bytes, ...] = (b"{}",),
    ) -> None:
        self.status_code = status_code
        self.headers = headers or {"content-type": "application/json"}
        self._chunks = chunks

    def __enter__(self) -> StubResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def iter_bytes(self):
        yield from self._chunks


class StubClient:
    def __init__(self, handler):
        self.handler = handler
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    def stream(self, method: str, url: str, **kwargs: object) -> StubResponse:
        self.calls.append((method, url, kwargs))
        return self.handler(method, url, kwargs)


def request(country: str = "Benin") -> ResearchRequest:
    return ResearchRequest(country, date(2026, 8, 14), ResearchMode.HOLISTIC)


def json_response(value: object, *, content_length: int | None = None) -> StubResponse:
    body = json.dumps(value).encode("utf-8")
    headers = {"content-type": "application/json"}
    if content_length is not None:
        headers["content-length"] = str(content_length)
    return StubResponse(headers=headers, chunks=(body,))


@pytest.mark.parametrize(
    "url",
    [
        "http://api.worldbank.org/v2/country",
        "https://api.worldbank.org:444/v2/country",
        "https://user:pass@api.worldbank.org/v2/country",
        "https://api.worldbank.org/v2/country#fragment",
        "https://api.worldbank.org.evil.example/v2/country",
        "https://127.0.0.1/v2/country",
        "https://[::1]/v2/country",
        "https://api.worldbank.org:bad/v2/country",
        "https://api.worldbank.org./v2/country",
    ],
)
def test_bounded_client_rejects_unsafe_urls_before_transport(url):
    transport = StubClient(lambda *_args: pytest.fail("transport should not be called"))
    client = BoundedInstitutionalClient(client=transport)

    with pytest.raises(ValueError):
        client.get_json(url)

    assert transport.calls == []


def test_bounded_client_allows_only_exact_https_hosts():
    transport = StubClient(lambda *_args: json_response({"ok": True}))
    client = BoundedInstitutionalClient(client=transport)

    assert client.get_json("https://api.worldbank.org/v2/country") == {"ok": True}

    assert transport.calls[0][0] == "GET"
    assert transport.calls[0][2]["follow_redirects"] is False
    timeout = transport.calls[0][2]["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == timeout.read == timeout.write == timeout.pool == 8.0


def test_bounded_client_caps_each_call_timeout_to_remaining_deadline():
    now = [10.0]
    transport = StubClient(lambda *_args: json_response({"ok": True}))
    client = BoundedInstitutionalClient(
        client=transport,
        timeout_seconds=8.0,
        monotonic=lambda: now[0],
    )

    assert client.get_json(
        "https://api.worldbank.org/v2/country", deadline=12.5
    ) == {"ok": True}

    timeout = transport.calls[0][2]["timeout"]
    assert timeout.connect == timeout.read == timeout.write == timeout.pool == 2.5


def test_bounded_client_does_not_swallow_programming_errors():
    def fail(*_args):
        raise KeyError("programming defect")

    client = BoundedInstitutionalClient(client=StubClient(fail))

    with pytest.raises(KeyError, match="programming defect"):
        client.get_json("https://api.worldbank.org/v2/country")


def test_bounded_client_does_not_swallow_iterator_programming_errors():
    class BrokenIteratorResponse(StubResponse):
        def iter_bytes(self):
            yield b"{"
            raise KeyError("iterator programming defect")

    client = BoundedInstitutionalClient(
        client=StubClient(lambda *_args: BrokenIteratorResponse())
    )

    with pytest.raises(KeyError, match="iterator programming defect"):
        client.get_json("https://api.worldbank.org/v2/country")


@pytest.mark.parametrize(
    ("transport_error", "expected_error"),
    [
        (httpx.ReadTimeout("secret timeout"), TimeoutError),
        (httpx.ConnectError("secret provider failure"), InstitutionalClientError),
    ],
)
def test_bounded_client_preserves_safe_timeout_and_provider_categories(
    transport_error, expected_error
):
    client = BoundedInstitutionalClient(
        client=StubClient(lambda *_args: (_ for _ in ()).throw(transport_error))
    )

    with pytest.raises(expected_error) as error:
        client.get_json("https://api.worldbank.org/v2/country")

    assert "secret" not in str(error.value)


def test_bounded_client_raises_timeout_for_expired_deadline():
    client = BoundedInstitutionalClient(
        client=StubClient(lambda *_args: pytest.fail("transport should not be called")),
        monotonic=lambda: 10.0,
    )

    with pytest.raises(TimeoutError):
        client.get_json("https://api.worldbank.org/v2/country", deadline=10.0)


def test_curated_gateway_uses_one_deadline_across_adapter_calls():
    now = [10.0]

    def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
        now[0] += 0.25
        assert urlsplit(url).path.endswith("/reports")
        return json_response({"data": []})

    transport = StubClient(handler)
    client = BoundedInstitutionalClient(client=transport, monotonic=lambda: now[0])
    gateway = CuratedResearchGateway(client, reliefweb_app_name="app")

    gateway.search(request(), timeout_seconds=1.0)

    timeouts = [call[2]["timeout"].connect for call in transport.calls]
    assert timeouts[0] == 1.0
    assert all(0 < timeout <= 1.0 for timeout in timeouts)
    assert timeouts == sorted(timeouts, reverse=True)


@pytest.mark.parametrize(
    "response",
    [
        StubResponse(status_code=302, headers={"location": "https://evil.example"}),
        StubResponse(status_code=500, chunks=(b"provider secret body",)),
        StubResponse(headers={"content-type": "text/html"}),
        StubResponse(headers={"content-type": "application/json", "content-length": "bad"}),
        StubResponse(headers={"content-type": "application/json", "content-length": "10001"}, chunks=(b"{}",)),
    ],
)
def test_bounded_client_rejects_redirects_status_content_type_and_bad_length(response):
    transport = StubClient(lambda *_args: response)
    client = BoundedInstitutionalClient(client=transport, max_bytes=10_000)

    with pytest.raises(InstitutionalClientError) as error:
        client.get_json("https://api.worldbank.org/v2/country?token=secret-token")

    assert "secret-token" not in str(error.value)
    assert "provider secret body" not in str(error.value)


def test_bounded_client_rejects_incremental_body_over_cap_without_content_length():
    transport = StubClient(
        lambda *_args: StubResponse(
            headers={"content-type": "application/json"},
            chunks=(b"{" + b"a" * 10_000, b"}"),
        )
    )
    client = BoundedInstitutionalClient(client=transport, max_bytes=10_000)

    with pytest.raises(InstitutionalClientError):
        client.get_json("https://api.worldbank.org/v2/country")


def test_world_bank_country_mapping_is_cached_and_claims_are_stable():
    def handler(_method: str, url: str, kwargs: dict[str, object]) -> StubResponse:
        path = urlsplit(url).path
        if path.endswith("/country"):
            return json_response([{}, [{"id": "BEN", "name": "Benin", "region": {"id": "AFR", "value": "Africa"}}]])
        indicator = path.rsplit("/", 1)[-1]
        return json_response(
            [
                {},
                [
                    {
                        "indicator": {"id": indicator, "value": indicator},
                        "countryiso3code": "BEN",
                        "date": "2025",
                        "value": 12.5,
                    }
                ],
            ]
        )

    transport = StubClient(handler)
    bounded = BoundedInstitutionalClient(client=transport)
    adapter = WorldBankAdapter(bounded)

    first = adapter.search(request("  benin "))
    second = adapter.search(request("Benin"))

    assert first == second
    assert first
    assert all(claim.publisher == "World Bank" for claim in first)
    assert all(claim.source_type == "institutional public data" for claim in first)
    assert all(claim.licensed_data_required is False for claim in first)
    assert all(urlsplit(claim.source_url or "").netloc == "api.worldbank.org" for claim in first)
    assert len([call for call in transport.calls if call[1].endswith("/country")]) == 1
    assert [claim.claim_id for claim in first] == [claim.claim_id for claim in second]

    country_query = parse_qs(urlsplit(transport.calls[0][1]).query)
    assert country_query == {}
    assert transport.calls[0][2]["params"] == {"format": "json", "per_page": "400"}
    assert all(call[2]["params"] == {"format": "json", "per_page": "5"} for call in transport.calls[1:])


def test_world_bank_official_id_resolves_and_fetches_indicator_claims():
    def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
        path = urlsplit(url).path
        if path.endswith("/country"):
            return json_response(
                [
                    {},
                    [
                        {
                            "id": "BEN",
                            "name": "Benin",
                            "region": {"id": "AFR", "value": "Africa"},
                        }
                    ],
                ]
            )
        indicator = path.rsplit("/", 1)[-1]
        return json_response(
            [
                {},
                [
                    {
                        "indicator": {"id": indicator, "value": indicator},
                        "countryiso3code": "BEN",
                        "date": "2025",
                        "value": 0,
                    }
                ],
            ]
        )

    transport = StubClient(handler)
    adapter = WorldBankAdapter(BoundedInstitutionalClient(client=transport))

    claims = adapter.search(request("Benin"))

    assert claims
    assert any("/country/BEN/indicator/" in call[1] for call in transport.calls)
    assert all(claim.publisher == "World Bank" for claim in claims)


@pytest.mark.parametrize(
    ("failed_indicator", "failure_kind"),
    [
        (WORLDBANK_INDICATORS[0][0], "timeout"),
        (WORLDBANK_INDICATORS[1][0], "malformed"),
    ],
)
def test_world_bank_indicator_failures_preserve_other_indicator_claims(
    failed_indicator: str,
    failure_kind: str,
):
    def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
        path = urlsplit(url).path
        if path.endswith("/country"):
            return json_response(
                [{}, [{"id": "BEN", "name": "Benin", "region": {"id": "AFR"}}]]
            )
        indicator = path.rsplit("/", 1)[-1]
        if indicator == failed_indicator:
            if failure_kind == "timeout":
                raise httpx.ReadTimeout("provider detail")
            return json_response({"unexpected": "shape"})
        return json_response(
            [
                {},
                [
                    {
                        "indicator": {"id": indicator, "value": indicator},
                        "countryiso3code": "BEN",
                        "date": "2025",
                        "value": 1,
                    }
                ],
            ]
        )

    adapter = WorldBankAdapter(BoundedInstitutionalClient(client=StubClient(handler)))

    claims = adapter.search(request())

    assert [claim.claim_id for claim in claims] == [
        f"worldbank:BEN:{indicator_id}:2025-01-01"
        for indicator_id, _label, _context_kind in WORLDBANK_INDICATORS
        if indicator_id != failed_indicator
    ]


@pytest.mark.parametrize(
    ("failure_kind", "expected_error"),
    [("timeout", TimeoutError), ("provider", InstitutionalClientError)],
)
def test_world_bank_raises_safe_category_when_every_indicator_query_fails(
    failure_kind, expected_error
):
    def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
        path = urlsplit(url).path
        if path.endswith("/country"):
            return json_response(
                [{}, [{"id": "BEN", "name": "Benin", "region": {"id": "AFR"}}]]
            )
        if failure_kind == "timeout":
            raise httpx.ReadTimeout("secret timeout")
        raise httpx.ConnectError("secret provider failure")

    adapter = WorldBankAdapter(BoundedInstitutionalClient(client=StubClient(handler)))

    with pytest.raises(expected_error) as error:
        adapter.search(request())

    assert "secret" not in str(error.value)


def test_world_bank_does_not_swallow_programming_errors_during_indicator_fetch():
    class ProgrammingErrorClient:
        def get_json(self, url: str, *, params: object = None) -> object:
            if urlsplit(url).path.endswith("/country"):
                return [{}, [{"id": "BEN", "name": "Benin", "region": {"id": "AFR"}}]]
            raise RuntimeError("programming defect")

    adapter = WorldBankAdapter(ProgrammingErrorClient())

    with pytest.raises(RuntimeError, match="programming defect"):
        adapter.search(request())


def test_world_bank_country_mapping_initializes_once_during_concurrent_first_use():
    first_load_started = Event()
    release_first_load = Event()
    duplicate_load_started = Event()
    counter_lock = Lock()
    load_count = 0

    class BlockingWorldBankAdapter(WorldBankAdapter):
        def _load_country_mapping(self) -> dict[str, str]:
            nonlocal load_count
            with counter_lock:
                load_count += 1
                current_load = load_count
            if current_load == 1:
                first_load_started.set()
                assert release_first_load.wait(timeout=2)
            else:
                duplicate_load_started.set()
            return {"benin": "BEN"}

    adapter = BlockingWorldBankAdapter(
        BoundedInstitutionalClient(
            client=StubClient(lambda *_args: pytest.fail("transport should not be called"))
        )
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(adapter._resolve_country, "Benin")
        assert first_load_started.wait(timeout=2)
        second = pool.submit(adapter._resolve_country, "Benin")
        duplicate_started = duplicate_load_started.wait(timeout=0.5)
        release_first_load.set()

        assert first.result(timeout=2) == "BEN"
        assert second.result(timeout=2) == "BEN"

    assert duplicate_started is False
    assert load_count == 1


def test_world_bank_country_mapping_excludes_same_name_aggregate_rows():
    def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
        path = urlsplit(url).path
        if path.endswith("/country"):
            return json_response(
                [
                    {},
                    [
                        {
                            "name": "Same-name country",
                            "id": "AGG",
                            "region": {"id": "NA", "value": "Aggregates"},
                        },
                        {
                            "name": "Same-name country",
                            "id": "VLD",
                            "region": {"id": "AFR", "value": "Africa"},
                        },
                    ],
                ]
            )
        indicator = path.rsplit("/", 1)[-1]
        return json_response(
            [
                {},
                [
                    {
                        "indicator": {"id": indicator, "value": indicator},
                        "countryiso3code": "VLD",
                        "date": "2025",
                        "value": 0,
                    }
                ],
            ]
        )

    adapter = WorldBankAdapter(BoundedInstitutionalClient(client=StubClient(handler)))

    claims = adapter.search(request("Same-name country"))

    assert claims
    assert all("/country/VLD/" in claim.source_url for claim in claims)


def test_world_bank_requires_matching_indicator_id_and_finite_numeric_values():
    def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
        if urlsplit(url).path.endswith("/country"):
            return json_response([{}, [{"id": "BEN", "name": "Benin", "region": {"id": "AFR", "value": "Africa"}}]])
        indicator = urlsplit(url).path.rsplit("/", 1)[-1]
        invalid_rows = [
            {"indicator": {"id": indicator, "value": indicator}, "date": "2025", "value": "0"},
            {"indicator": {"id": indicator, "value": indicator}, "date": "2025", "value": True},
            {"indicator": {"id": indicator, "value": indicator}, "date": "2025", "value": float("nan")},
            {"indicator": {"id": indicator, "value": indicator}, "date": "2025", "value": float("inf")},
            {"indicator": {"id": indicator, "value": indicator}, "date": "2025", "value": {"value": 0}},
            {"indicator": {"id": indicator, "value": indicator}, "date": "2025", "value": [0]},
            {"indicator": {"id": "OTHER", "value": "Other"}, "date": "2025", "value": 0},
        ]
        return json_response(
            [
                {},
                [
                    *invalid_rows,
                    {
                        "indicator": {"id": indicator, "value": indicator},
                        "countryiso3code": "BEN",
                        "date": "2025",
                        "value": 0,
                    },
                ],
            ]
        )

    adapter = WorldBankAdapter(BoundedInstitutionalClient(client=StubClient(handler)))

    claims = adapter.search(request())

    assert len(claims) == len(WORLDBANK_INDICATORS)
    assert all(": 0 (2025)." in claim.text for claim in claims)


def test_world_bank_skips_null_malformed_and_undated_rows():
    def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
        if urlsplit(url).path.endswith("/country"):
            return json_response([{}, [{"id": "BEN", "name": "Benin", "region": {"id": "AFR", "value": "Africa"}}]])
        return json_response(
            [
                {},
                [
                    {"date": "2025", "value": None},
                    {"date": "not-a-date", "value": 1},
                    {"value": 1},
                    {"date": "2025", "value": {"unexpected": True}},
                    {"date": "2025", "value": 1, "countryiso3code": "B"},
                    {"indicator": {"id": "OTHER", "value": "Other"}, "date": "2025", "value": 1},
                ],
            ]
        )

    adapter = WorldBankAdapter(BoundedInstitutionalClient(client=StubClient(handler)))

    assert adapter.search(request()) == ()


def test_world_bank_rejects_observation_without_country_identity():
    def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
        path = urlsplit(url).path
        if path.endswith("/country"):
            return json_response(
                [{}, [{"id": "BEN", "name": "Benin", "region": {"id": "AFR"}}]]
            )
        indicator = path.rsplit("/", 1)[-1]
        return json_response(
            [
                {},
                [{"indicator": {"id": indicator}, "date": "2025", "value": 1}],
            ]
        )

    adapter = WorldBankAdapter(BoundedInstitutionalClient(client=StubClient(handler)))

    assert adapter.search(request()) == ()


def test_world_bank_rejects_observation_with_malformed_country_identity():
    def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
        path = urlsplit(url).path
        if path.endswith("/country"):
            return json_response(
                [{}, [{"id": "BEN", "name": "Benin", "region": {"id": "AFR"}}]]
            )
        indicator = path.rsplit("/", 1)[-1]
        return json_response(
            [
                {},
                [
                    {
                        "indicator": {"id": indicator},
                        "countryiso3code": "BEN ",
                        "date": "2025",
                        "value": 1,
                    }
                ],
            ]
        )

    adapter = WorldBankAdapter(BoundedInstitutionalClient(client=StubClient(handler)))

    assert adapter.search(request()) == ()


def test_world_bank_rejects_observation_with_mismatched_country_identity():
    def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
        path = urlsplit(url).path
        if path.endswith("/country"):
            return json_response(
                [{}, [{"id": "BEN", "name": "Benin", "region": {"id": "AFR"}}]]
            )
        indicator = path.rsplit("/", 1)[-1]
        return json_response(
            [
                {},
                [
                    {
                        "indicator": {"id": indicator},
                        "countryiso3code": "TGO",
                        "date": "2025",
                        "value": 1,
                    }
                ],
            ]
        )

    adapter = WorldBankAdapter(BoundedInstitutionalClient(client=StubClient(handler)))

    assert adapter.search(request()) == ()


def test_world_bank_accepts_observation_on_review_date_boundary():
    def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
        path = urlsplit(url).path
        if path.endswith("/country"):
            return json_response(
                [{}, [{"id": "BEN", "name": "Benin", "region": {"id": "AFR"}}]]
            )
        indicator = path.rsplit("/", 1)[-1]
        return json_response(
            [
                {},
                [
                    {
                        "indicator": {"id": indicator},
                        "countryiso3code": "ben",
                        "date": "2026",
                        "value": 1,
                    }
                ],
            ]
        )

    adapter = WorldBankAdapter(BoundedInstitutionalClient(client=StubClient(handler)))
    boundary_request = ResearchRequest("Benin", date(2026, 1, 1), ResearchMode.HOLISTIC)

    assert len(adapter.search(boundary_request)) == len(WORLDBANK_INDICATORS)


def test_world_bank_rejects_observation_after_review_date():
    def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
        path = urlsplit(url).path
        if path.endswith("/country"):
            return json_response(
                [{}, [{"id": "BEN", "name": "Benin", "region": {"id": "AFR"}}]]
            )
        indicator = path.rsplit("/", 1)[-1]
        return json_response(
            [
                {},
                [
                    {
                        "indicator": {"id": indicator},
                        "countryiso3code": "BEN",
                        "date": "2027",
                        "value": 1,
                    }
                ],
            ]
        )

    adapter = WorldBankAdapter(BoundedInstitutionalClient(client=StubClient(handler)))
    review_request = ResearchRequest("Benin", date(2026, 12, 31), ResearchMode.HOLISTIC)

    assert adapter.search(review_request) == ()


def test_reliefweb_is_skipped_without_trimmed_app_name():
    transport = StubClient(lambda *_args: pytest.fail("ReliefWeb should be skipped"))
    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(client=transport), reliefweb_app_name="   "
    )

    assert gateway.reliefweb.search(request()) == ()
    assert transport.calls == []


def test_reliefweb_trims_approved_app_name():
    def handler(_method: str, url: str, kwargs: dict[str, object]) -> StubResponse:
        assert url == "https://api.reliefweb.int/v2/reports"
        assert ("appname", "approved.example") in kwargs["params"]
        return json_response({"data": []})

    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(client=StubClient(handler)),
        reliefweb_app_name="  approved.example ",
    )

    assert gateway.reliefweb.search(request()) == ()


def test_reliefweb_skips_rows_without_explicit_valid_fields():
    def handler(_method: str, _url: str, _kwargs: dict[str, object]) -> StubResponse:
        return json_response(
            {
                "data": [
                    {"fields": {"title": "No date", "url": "https://reliefweb.int/a"}},
                    {"fields": {"url": "https://reliefweb.int/b", "date": {"created": "2026-08-01"}}},
                    {"fields": {"title": "Bad URL", "url": "https://evil.example/b", "date": {"created": "2026-08-01"}}},
                    {"fields": {"title": "Bad date", "url": "https://reliefweb.int/c", "date": {"created": "not-a-date"}}},
                    {"fields": {"title": "No source", "url": "https://reliefweb.int/d", "date": {"created": "2026-08-01"}, "source": []}},
                    {"fields": {"title": "Original only", "url": "https://reliefweb.int/g", "date": {"original": "2026-08-01"}, "source": [{"name": "UN"}]}},
                    {"fields": {"title": "Date string", "url": "https://reliefweb.int/h", "date": "2026-08-01", "source": [{"name": "UN"}]}},
                    {"fields": {"title": "Too old", "url": "https://reliefweb.int/e", "date": {"created": "2023-08-01"}, "source": [{"name": "UN"}]}},
                    {"fields": {"title": "Too new", "url": "https://reliefweb.int/f", "date": {"created": "2026-08-15"}, "source": [{"name": "UN"}]}},
                ]
            }
        )

    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(client=StubClient(handler)), reliefweb_app_name="app"
    )

    assert gateway.reliefweb.search(request()) == ()


def test_gateway_uses_reliefweb_without_world_bank_indicators():
    def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
        assert "worldbank.org" not in url
        return json_response({"data": [{"fields": {
            "title": "Benin conflict update",
            "origin": "https://www.unocha.org/benin",
            "date": {"original": "2026-08-01"},
            "primary_country": {"name": "Benin"},
            "source": [{"name": "OCHA"}],
            "body": "Violence displaced families in Benin.",
        }}]})

    transport = StubClient(handler)
    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(client=transport), reliefweb_app_name="app"
    )

    claims = gateway.search(request())

    assert len(claims) == 1
    assert claims[0].publisher == "OCHA"
    assert all("worldbank.org" not in call[1] for call in transport.calls)


def test_reliefweb_rejects_generic_non_fcv_reports():
    def handler(_method: str, _url: str, _kwargs: dict[str, object]) -> StubResponse:
        common = {
            "date": {"original": "2026-08-01"},
            "primary_country": {"name": "Benin"},
            "source": [{"name": "OCHA"}],
        }
        return json_response({"data": [
            {"fields": {**common, "title": "Population estimate",
                        "origin": "https://www.unocha.org/population",
                        "body": "The population estimate was revised."}},
            {"fields": {**common, "title": "Energy update",
                        "origin": "https://www.unocha.org/energy",
                        "body": "Solar capacity increased."}},
            {"fields": {**common, "title": "Political transition",
                        "origin": "https://www.unocha.org/fcv",
                        "body": "Political violence disrupted local services in Benin."}},
        ]})

    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(client=StubClient(handler)), reliefweb_app_name="app"
    )

    claims = gateway.search(request())

    assert [claim.source_title for claim in claims] == ["Political transition"]


def test_gateway_raises_provider_failure_when_all_enabled_adapters_fail():
    transport = StubClient(lambda *_args: (_ for _ in ()).throw(httpx.ConnectError("secret")))
    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(client=transport), reliefweb_app_name="app"
    )

    with pytest.raises(InstitutionalClientError):
        gateway.search(request())


def test_gateway_raises_timeout_when_all_enabled_adapters_time_out():
    transport = StubClient(lambda *_args: (_ for _ in ()).throw(httpx.ReadTimeout("secret")))
    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(client=transport), reliefweb_app_name="app"
    )

    with pytest.raises(TimeoutError):
        gateway.search(request())


def test_gateway_does_not_swallow_programming_errors():
    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(client=StubClient(lambda *_args: json_response({}))),
        reliefweb_app_name="app",
    )
    gateway.reliefweb.search = lambda _request: (_ for _ in ()).throw(
        RuntimeError("programming defect")
    )

    with pytest.raises(RuntimeError, match="programming defect"):
        gateway.search(request())


def rss_response(value: str) -> StubResponse:
    return StubResponse(
        headers={"content-type": "application/rss+xml; charset=utf-8"},
        chunks=(value.encode("utf-8"),),
    )


def test_crisis_group_country_feed_returns_recent_dated_fcv_claim():
    payload = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0"><channel><item>
      <title>Guinea's Call to Elections Exposes Military Bid to Cling to Power</title>
      <link>https://www.crisisgroup.org/alr/africa/guinea/elections</link>
      <pubDate>Friday, October 3, 2025 - 12:26</pubDate>
      <guid>26736</guid>
    </item></channel></rss>"""
    transport = StubClient(lambda *_args: rss_response(payload))
    adapter = CrisisGroupAdapter(BoundedInstitutionalClient(client=transport))

    claims = adapter.search(
        ResearchRequest("Guinea", date(2026, 9, 4), ResearchMode.HOLISTIC)
    )

    assert len(claims) == 1
    assert claims[0].publisher == "International Crisis Group"
    assert claims[0].source_date == date(2025, 10, 3)
    assert claims[0].source_url == (
        "https://www.crisisgroup.org/alr/africa/guinea/elections"
    )
    assert transport.calls[0][1] == "https://www.crisisgroup.org/rss/23"


def test_crisis_group_rejects_unknown_country_old_generic_and_malformed_items():
    payload = """<rss version="2.0"><channel>
      <item><title>Guinea economic outlook</title>
        <link>https://www.crisisgroup.org/africa/guinea/outlook</link>
        <pubDate>Friday, October 3, 2025 - 12:26</pubDate></item>
      <item><title>Guinea conflict update</title>
        <link>https://www.crisisgroup.org/africa/guinea/old</link>
        <pubDate>Friday, October 3, 2020 - 12:26</pubDate></item>
      <item><title>Guinea violence update</title>
        <link>https://evil.example/guinea</link>
        <pubDate>Friday, October 3, 2025 - 12:26</pubDate></item>
      <item><title>Guinea political update</title>
        <link>https://www.crisisgroup.org/africa/guinea/no-date</link></item>
    </channel></rss>"""
    transport = StubClient(lambda *_args: rss_response(payload))
    adapter = CrisisGroupAdapter(BoundedInstitutionalClient(client=transport))

    assert adapter.search(
        ResearchRequest("Unknownland", date(2026, 9, 4), ResearchMode.HOLISTIC)
    ) == ()
    assert transport.calls == []
    assert adapter.search(
        ResearchRequest("Guinea", date(2026, 9, 4), ResearchMode.HOLISTIC)
    ) == ()


def test_gateway_uses_crisis_group_without_reliefweb_appname():
    payload = """<rss version="2.0"><channel><item>
      <title>Guinea military leaders delayed political transition</title>
      <link>https://www.crisisgroup.org/africa/guinea/transition</link>
      <pubDate>Friday, October 3, 2025 - 12:26</pubDate>
    </item></channel></rss>"""
    transport = StubClient(lambda *_args: rss_response(payload))
    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(client=transport), reliefweb_app_name=""
    )

    claims = gateway.search(
        ResearchRequest("Guinea", date(2026, 9, 4), ResearchMode.HOLISTIC)
    )

    assert [claim.publisher for claim in claims] == ["International Crisis Group"]


def test_crisis_group_rejects_wrong_content_type_and_malformed_xml():
    wrong_type = CrisisGroupAdapter(
        BoundedInstitutionalClient(client=StubClient(lambda *_args: json_response({})))
    )
    with pytest.raises(InstitutionalClientError):
        wrong_type.search(
            ResearchRequest("Guinea", date(2026, 9, 4), ResearchMode.HOLISTIC)
        )

    malformed = CrisisGroupAdapter(
        BoundedInstitutionalClient(
            client=StubClient(lambda *_args: rss_response("<rss>"))
        )
    )
    with pytest.raises(ValueError, match="response shape"):
        malformed.search(
            ResearchRequest("Guinea", date(2026, 9, 4), ResearchMode.HOLISTIC)
        )


def test_gateway_keeps_crisis_group_claim_when_reliefweb_is_unavailable():
    payload = """<rss version="2.0"><channel><item>
      <title>Guinea military leaders delayed political transition</title>
      <link>https://www.crisisgroup.org/africa/guinea/transition</link>
      <pubDate>Friday, October 3, 2025 - 12:26</pubDate>
    </item></channel></rss>"""

    def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
        if url == "https://www.crisisgroup.org/rss/23":
            return rss_response(payload)
        return StubResponse(status_code=403)

    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(client=StubClient(handler)),
        reliefweb_app_name="unapproved-app",
    )

    claims = gateway.search(
        ResearchRequest("Guinea", date(2026, 9, 4), ResearchMode.HOLISTIC)
    )

    assert [claim.publisher for claim in claims] == ["International Crisis Group"]
def test_crisis_group_recovery_uses_summary_and_verified_country_feeds():
    payload = """<rss><channel><item>
      <title>Somalia humanitarian update</title>
      <link>https://www.crisisgroup.org/africa/somalia/update</link>
      <pubDate>Friday, October 3, 2025 - 12:26</pubDate>
      <description><![CDATA[<p>Armed conflict displaced communities in Somalia.</p>]]></description>
    </item></channel></rss>"""
    transport = StubClient(lambda *_args: rss_response(payload))
    claims = CrisisGroupAdapter(
        BoundedInstitutionalClient(client=transport)
    ).search(ResearchRequest("Somalia", date(2026, 9, 4), ResearchMode.HOLISTIC))

    assert transport.calls[0][1] == "https://www.crisisgroup.org/rss/12"
    assert claims[0].text == "Armed conflict displaced communities in Somalia."
    assert claims[0].supporting_quote == claims[0].text
    assert claims[0].publication_date_basis == "provider_metadata"



def test_crisis_group_uses_substantive_headline_when_summary_omits_country():
    title = "Guinea's Call to Elections Exposes Military Bid to Cling to Power"
    summary = (
        "Crisis Group expert analyses the general's plans to secure victory in "
        "presidential polls despite an earlier promise not to seek a mandate."
    )
    payload = f"""<rss><channel><item>
      <title>{title}</title>
      <link>https://www.crisisgroup.org/alr/africa/guinea/elections</link>
      <pubDate>Friday, October 3, 2025 - 12:26</pubDate>
      <description><![CDATA[<p>{summary}</p>]]></description>
    </item></channel></rss>"""
    transport = StubClient(lambda *_args: rss_response(payload))

    claims = CrisisGroupAdapter(
        BoundedInstitutionalClient(client=transport)
    ).search(ResearchRequest("Guinea", date(2026, 9, 4), ResearchMode.HOLISTIC))

    assert len(claims) == 1
    assert claims[0].text == title
    assert claims[0].supporting_quote == title
    assert claims[0].publisher == "International Crisis Group"
    assert claims[0].source_date == date(2025, 10, 3)


def test_crisis_group_keeps_usable_summary_without_narrow_assertion_verb():
    summary = "Violence and political tensions persist in Guinea."
    payload = f"""<rss><channel><item>
      <title>Guinea conflict update</title>
      <link>https://www.crisisgroup.org/africa/guinea/conflict-update</link>
      <pubDate>Friday, October 3, 2025 - 12:26</pubDate>
      <description><![CDATA[<p>{summary}</p>]]></description>
    </item></channel></rss>"""

    claims = CrisisGroupAdapter(
        BoundedInstitutionalClient(client=StubClient(lambda *_args: rss_response(payload)))
    ).search(ResearchRequest("Guinea", date(2026, 9, 4), ResearchMode.HOLISTIC))

    assert len(claims) == 1
    assert claims[0].text == summary
    assert claims[0].supporting_quote == summary


def test_crisis_group_headline_fallback_rejects_compound_country_mismatch():
    payload = """<rss><channel><item>
      <title>Guinea-Bissau Elections Expose Military Tensions</title>
      <link>https://www.crisisgroup.org/africa/guinea-bissau/elections</link>
      <pubDate>Friday, October 3, 2025 - 12:26</pubDate>
      <description>Expert analysis of the transition.</description>
    </item></channel></rss>"""

    claims = CrisisGroupAdapter(
        BoundedInstitutionalClient(client=StubClient(lambda *_args: rss_response(payload)))
    ).search(ResearchRequest("Guinea", date(2026, 9, 4), ResearchMode.HOLISTIC))

    assert claims == ()


@pytest.mark.parametrize(
    ("country", "feed"),
    [
        ("Democratic Republic of the Congo", "7"),
        ("Congo", "115"),
        ("West Bank and Gaza", "91"),
        ("Kosovo", "68"),
        ("Türkiye", "58"),
        ("Cote d'Ivoire", "22"),
        ("Sao Tome and Principe", "154"),
        ("India", "123"),
        ("Indonesia", "44"),
        ("Kenya", "11"),
        ("Brazil", "176"),
    ],
)
def test_crisis_group_recovery_uses_checked_in_feed_catalogue(country, feed):
    transport = StubClient(lambda *_args: rss_response("<rss><channel/></rss>"))
    assert CrisisGroupAdapter(
        BoundedInstitutionalClient(client=transport)
    ).search(request(country)) == ()
    assert transport.calls[0][1] == f"https://www.crisisgroup.org/rss/{feed}"


def test_reliefweb_recovery_uses_original_report_provenance_and_exact_country():
    def handler(_method: str, _url: str, kwargs: dict[str, object]) -> StubResponse:
        params = kwargs["params"]
        assert ("filter[conditions][0][value]", "occupied Palestinian territory") in params
        assert ("filter[conditions][1][field]", "date.original") in params
        assert ("fields[include][]", "origin") in params
        assert ("fields[include][]", "body") in params
        assert ("fields[include][]", "primary_country.name") in params
        assert not any(value == "date.created" for _, value in params)
        assert not any(key.endswith("[2][field]") for key, _ in params)
        return json_response({"data": [{"fields": {
            "title": "Humanitarian update",
            "url": "https://reliefweb.int/report/occupied-palestinian-territory/update",
            "origin": "https://www.unocha.org/news/displacement-update",
            "date": {"original": "2026-08-01", "created": "2026-09-01"},
            "primary_country": {"name": "occupied Palestinian territory"},
            "source": [{"name": "OCHA"}, {"name": "Partner"}],
            "body": "<p>Violence displaced communities in the occupied Palestinian territory.</p>",
        }}]})

    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(client=StubClient(handler)), reliefweb_app_name="app"
    )
    claims = gateway.reliefweb.search(request("West Bank and Gaza"))

    assert len(claims) == 1
    assert claims[0].publisher == "OCHA"
    assert claims[0].source_url == "https://www.unocha.org/news/displacement-update"
    assert claims[0].source_date == date(2026, 8, 1)
    assert claims[0].text == (
        "Violence displaced communities in the occupied Palestinian territory."
    )
    assert claims[0].supporting_quote == claims[0].text
    assert claims[0].publication_date_basis == "provider_metadata"


def test_reliefweb_recovery_rejects_created_date_wrong_country_and_unknown_origin():
    rows = [
        {"fields": {
            "title": "Old conflict report",
            "origin": "https://www.unocha.org/old",
            "date": {"original": "2023-08-01", "created": "2026-08-01"},
            "primary_country": {"name": "Benin"},
            "source": [{"name": "OCHA"}],
            "body": "Violence displaced communities in Benin.",
        }},
        {"fields": {
            "title": "Wrong-country conflict report",
            "origin": "https://www.unocha.org/togo",
            "date": {"original": "2026-08-01"},
            "primary_country": {"name": "Togo"},
            "source": [{"name": "OCHA"}],
            "body": "Violence displaced communities in Togo.",
        }},
        {"fields": {
            "title": "Unknown-origin conflict report",
            "origin": "https://unknown.example/benin",
            "date": {"original": "2026-08-01"},
            "primary_country": {"name": "Benin"},
            "source": [{"name": "Unknown"}],
            "body": "Violence displaced communities in Benin.",
        }},
        {"fields": {
            "title": "Generic report",
            "origin": "https://www.unocha.org/generic",
            "date": {"original": "2026-08-01"},
            "primary_country": {"name": "Benin"},
            "source": [{"name": "OCHA"}],
        }},
    ]
    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(
            client=StubClient(lambda *_args: json_response({"data": rows}))
        ),
        reliefweb_app_name="app",
    )

    assert gateway.reliefweb.search(request()) == ()
def test_crisis_group_rejects_regional_feed_item_about_another_country():
    payload = """<rss><channel><item>
      <title>Regional conflict update</title>
      <link>https://www.crisisgroup.org/africa/congo/regional-update</link>
      <pubDate>Friday, October 3, 2025 - 12:26</pubDate>
      <description>Violence displaced people in Somalia.</description>
    </item></channel></rss>"""
    adapter = CrisisGroupAdapter(
        BoundedInstitutionalClient(
            client=StubClient(lambda *_args: rss_response(payload))
        )
    )

    assert adapter.search(request("Congo")) == ()
def test_reliefweb_maps_cote_divoire_to_provider_country_name():
    def handler(_method: str, _url: str, kwargs: dict[str, object]) -> StubResponse:
        assert ("filter[conditions][0][value]", "Côte d'Ivoire") in kwargs["params"]
        return json_response({"data": []})

    adapter = CuratedResearchGateway(
        BoundedInstitutionalClient(client=StubClient(handler)), reliefweb_app_name="app"
    ).reliefweb

    assert adapter.search(request("Cote d'Ivoire")) == ()

def test_curated_gateway_preserves_candidates_for_controller_qualification():
    items = "".join(
        (
            "<item>"
            f"<title>Somalia violence update {index}</title>"
            f"<link>https://www.crisisgroup.org/africa/somalia/update-{index}</link>"
            "<pubDate>Friday, August 1, 2026 - 12:00</pubDate>"
            f"<description>Political violence increased in Somalia district {index}.</description>"
            "</item>"
        )
        for index in range(8)
    )
    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(
            client=StubClient(
                lambda *_args: rss_response(f"<rss><channel>{items}</channel></rss>")
            )
        )
    )

    claims = gateway.search(request("Somalia"))

    assert len(claims) == 8


def test_reliefweb_copy_url_is_not_treated_as_originating_publisher():
    payload = {
        "data": [
            {
                "fields": {
                    "title": "Guinea conflict update",
                    "origin": "https://reliefweb.int/report/guinea/conflict-update",
                    "date": {"created": "2026-08-01"},
                    "body": "Political violence increased in Guinea.",
                    "primary_country": [{"name": "Guinea"}],
                    "source": [{"name": "United Nations"}],
                }
            }
        ]
    }

    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(
            client=StubClient(lambda *_args: json_response(payload))
        ),
        reliefweb_app_name="app",
    )

    assert gateway.reliefweb.search(request()) == ()


def test_gateway_keeps_later_finding_from_same_source():
    payload = """<rss version="2.0"><channel>
    <item><title>Guinea conflict increased locally</title>
      <link>https://www.crisisgroup.org/africa/guinea/update</link>
      <pubDate>Friday, October 3, 2025 - 12:26</pubDate></item>
    <item><title>Guinea political violence increased</title>
      <link>https://www.crisisgroup.org/africa/guinea/update</link>
      <pubDate>Saturday, October 4, 2025 - 12:26</pubDate></item>
    </channel></rss>"""
    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(
            client=StubClient(lambda *_args: rss_response(payload))
        )
    )

    claims = gateway.search(request("Guinea"))

    assert len(claims) == 2
    assert {claim.source_date for claim in claims} == {
        date(2025, 10, 3),
        date(2025, 10, 4),
    }
