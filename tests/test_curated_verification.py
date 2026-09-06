from __future__ import annotations

from datetime import date

import pytest

from cpf_fcv_reviewer.curated_research import (
    BoundedInstitutionalClient,
    CrisisGroupAdapter,
    _curated_verification,
)
from cpf_fcv_reviewer.research_controller import ResearchMode, ResearchRequest


class StubResponse:
    def __init__(self, *, chunks: tuple[bytes, ...]) -> None:
        self.status_code = 200
        self.headers = {"content-type": "application/rss+xml"}
        self._chunks = chunks

    def __enter__(self) -> "StubResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def iter_bytes(self):
        yield from self._chunks


class StubClient:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def stream(self, _method: str, _url: str, **_kwargs: object) -> StubResponse:
        return StubResponse(chunks=(self._payload,))


def test_curated_verification_grades_by_date_and_quote():
    assert _curated_verification(source_date=date(2026, 1, 1), supporting_quote="q") == "verified"
    assert _curated_verification(source_date=date(2026, 1, 1), supporting_quote=None) == "partially_verified"
    assert _curated_verification(source_date=date(2026, 1, 1), supporting_quote="  ") == "partially_verified"
    assert _curated_verification(source_date=None, supporting_quote="q") == "unverified"


def test_crisis_group_claim_is_verified():
    """A Crisis Group claim with a description (supporting_quote=text) must be 'verified'."""
    payload = b"""<rss><channel><item>
      <title>Somalia humanitarian update</title>
      <link>https://www.crisisgroup.org/africa/somalia/update</link>
      <pubDate>Friday, October 3, 2025 - 12:26</pubDate>
      <description><![CDATA[<p>Armed conflict displaced communities in Somalia.</p>]]></description>
    </item></channel></rss>"""
    adapter = CrisisGroupAdapter(
        BoundedInstitutionalClient(client=StubClient(payload))
    )
    claims = adapter.search(
        ResearchRequest("Somalia", date(2026, 9, 4), ResearchMode.HOLISTIC)
    )

    assert len(claims) == 1
    assert claims[0].verification == "verified"


