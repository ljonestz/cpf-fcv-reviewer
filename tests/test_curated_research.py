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
    CuratedResearchGateway,
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

    with pytest.raises(ValueError) as error:
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

    with pytest.raises(ValueError):
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


def test_reliefweb_uses_v2_appname_country_date_and_minimum_fields():
    def handler(_method: str, url: str, kwargs: dict[str, object]) -> StubResponse:
        assert url == "https://api.reliefweb.int/v2/reports"
        params = kwargs["params"]
        assert isinstance(params, list)
        assert ("appname", "approved.example") in params
        assert ("query[value]", "Benin") in params
        assert ("filter[conditions][0][field]", "primary_country") in params
        assert ("filter[conditions][0][value]", "Benin") in params
        assert ("filter[conditions][1][field]", "date.created") in params
        assert ("fields[include][]", "title") in params
        assert ("fields[include][]", "url") in params
        assert ("fields[include][]", "date.created") in params
        assert ("fields[include][]", "source.name") in params
        return json_response(
            {
                "data": [
                    {
                        "fields": {
                            "title": "Benin humanitarian update",
                            "url": "https://reliefweb.int/report/benin/update",
                            "date": {"created": "2026-08-01T00:00:00+00:00"},
                            "source": [{"name": "UN OCHA"}],
                            "body": "do not ingest this body",
                        }
                    }
                ]
            }
        )

    transport = StubClient(handler)
    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(client=transport), reliefweb_app_name="  approved.example "
    )

    claims = gateway.reliefweb.search(request())

    assert len(claims) == 1
    claim = claims[0]
    assert claim.publisher == "ReliefWeb"
    assert claim.source_title == "Benin humanitarian update"
    assert claim.source_date == date(2026, 8, 1)
    assert "do not ingest" not in claim.text
    assert urlsplit(claim.source_url or "").hostname in {"reliefweb.int", "api.reliefweb.int"}


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


def test_gateway_combines_deduplicates_and_sorts_independent_adapter_outputs():
    def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
        if "worldbank.org" in url:
            if urlsplit(url).path.endswith("/country"):
                return json_response([{}, [{"id": "BEN", "name": "Benin", "region": {"id": "AFR", "value": "Africa"}}]])
            indicator = urlsplit(url).path.rsplit("/", 1)[-1]
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
        return json_response({"data": [{"fields": {"title": "RW", "url": "https://reliefweb.int/rw", "date": {"created": "2026-08-01"}, "source": [{"name": "UN"}]}}]})

    transport = StubClient(handler)
    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(client=transport), reliefweb_app_name="app"
    )

    claims = gateway.search(request())

    assert tuple(claim.claim_id for claim in claims) == tuple(sorted({claim.claim_id for claim in claims}))
    assert len(claims) == len({claim.claim_id for claim in claims})
    assert {claim.publisher for claim in claims} == {"World Bank", "ReliefWeb"}


def test_gateway_duplicate_winner_is_stable_when_payload_order_is_reversed():
    def run(values: tuple[int, int]):
        def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
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
                            "value": value,
                        }
                        for value in values
                    ],
                ]
            )

        gateway = CuratedResearchGateway(
            BoundedInstitutionalClient(client=StubClient(handler))
        )
        return gateway.search(request())

    forward = run((2, 1))
    reverse = run((1, 2))

    assert forward == reverse
    assert forward
    assert all(": 1 (2025)." in claim.text for claim in forward)


def test_gateway_preserves_distinct_dated_world_bank_observations():
    indicator_id = WORLDBANK_INDICATORS[0][0]

    def run(observations: tuple[tuple[str, int], ...]):
        def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
            path = urlsplit(url).path
            if path.endswith("/country"):
                return json_response(
                    [{}, [{"id": "BEN", "name": "Benin", "region": {"id": "AFR"}}]]
                )
            requested_indicator = path.rsplit("/", 1)[-1]
            if requested_indicator != indicator_id:
                return json_response([{}, []])
            return json_response(
                [
                    {},
                    [
                        {
                            "indicator": {"id": indicator_id, "value": indicator_id},
                            "countryiso3code": "BEN",
                            "date": observation_year,
                            "value": value,
                        }
                        for observation_year, value in observations
                    ],
                ]
            )

        gateway = CuratedResearchGateway(
            BoundedInstitutionalClient(client=StubClient(handler))
        )
        return gateway.search(request())

    observations = (("2025", 2), ("2024", 1), ("2025", 2))
    forward = run(observations)
    reverse = run(tuple(reversed(observations)))

    assert forward == reverse
    assert [claim.source_date for claim in forward] == [date(2024, 1, 1), date(2025, 1, 1)]
    assert len({claim.claim_id for claim in forward}) == 2
    assert len({claim.source_url for claim in forward}) == 2
    assert {
        parse_qs(urlsplit(claim.source_url or "").query)["date"][0]
        for claim in forward
    } == {"2024", "2025"}
    assert all(urlsplit(claim.source_url or "").scheme == "https" for claim in forward)
    assert all(
        urlsplit(claim.source_url or "").hostname == "api.worldbank.org"
        for claim in forward
    )
    assert any(
        claim.source_date == date(2025, 1, 1) and ": 2 (2025)." in claim.text
        for claim in forward
    )


def test_gateway_continues_when_one_adapter_times_out():
    def handler(_method: str, url: str, _kwargs: dict[str, object]) -> StubResponse:
        if "worldbank.org" in url:
            raise httpx.ReadTimeout("secret provider detail")
        return json_response({"data": [{"fields": {"title": "RW", "url": "https://reliefweb.int/rw", "date": {"created": "2026-08-01"}, "source": [{"name": "UN"}]}}]})

    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(client=StubClient(handler)), reliefweb_app_name="app"
    )

    claims = gateway.search(request())

    assert len(claims) == 1
    assert claims[0].publisher == "ReliefWeb"


def test_gateway_returns_empty_when_both_adapters_fail():
    transport = StubClient(lambda *_args: (_ for _ in ()).throw(httpx.ConnectError("secret")))
    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(client=transport), reliefweb_app_name="app"
    )

    assert gateway.search(request()) == ()


def test_gateway_does_not_swallow_programming_errors():
    gateway = CuratedResearchGateway(
        BoundedInstitutionalClient(client=StubClient(lambda *_args: json_response({})))
    )
    gateway.world_bank.search = lambda _request: (_ for _ in ()).throw(
        RuntimeError("programming defect")
    )

    with pytest.raises(RuntimeError, match="programming defect"):
        gateway.search(request())
