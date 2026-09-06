from cpf_fcv_reviewer.public_research import (
    ResearchSource,
    _grade_claim,
)


def _source(*, published, excerpt):
    return ResearchSource(
        title="Guinea security update",
        url="https://www.crisisgroup.org/guinea-update",
        publisher="International Crisis Group",
        published_at=published,
        excerpt=excerpt,
    )


def test_dated_source_with_verbatim_quote_grades_verified():
    from datetime import date

    source = _source(published=date(2025, 4, 30), excerpt="Armed clashes displaced thousands.")
    assert _grade_claim(source, "Armed clashes displaced thousands.") == "verified"


def test_dated_source_with_paraphrased_quote_grades_partial():
    from datetime import date

    source = _source(published=date(2025, 4, 30), excerpt="Armed clashes displaced thousands.")
    assert _grade_claim(source, "Thousands were displaced by clashes.") == "partially_verified"


def test_undated_source_with_verbatim_quote_grades_partial():
    source = _source(published=None, excerpt="Armed clashes displaced thousands.")
    assert _grade_claim(source, "Armed clashes displaced thousands.") == "partially_verified"


def test_undated_source_with_paraphrased_quote_grades_unverified():
    source = _source(published=None, excerpt="Armed clashes displaced thousands.")
    assert _grade_claim(source, "Thousands were displaced by clashes.") == "unverified"


def test_missing_quote_grades_unverified_when_undated():
    source = _source(published=None, excerpt="Armed clashes displaced thousands.")
    assert _grade_claim(source, None) == "unverified"


def test_dated_source_with_no_quote_grades_partial():
    from datetime import date

    source = _source(published=date(2025, 4, 30), excerpt="Armed clashes displaced thousands.")
    assert _grade_claim(source, None) == "partially_verified"


def test_salvage_undated_source_has_null_source_date():
    from cpf_fcv_reviewer.public_research import ResearchSource, _salvage_grounded_segments

    undated = ResearchSource(
        title="Guinea update B",
        url="https://www.crisisgroup.org/guinea-b",
        publisher="International Crisis Group",
        published_at=None,
        excerpt="Security incidents were reported across Guinea.",
    )
    claims = _salvage_grounded_segments(
        (("Security incidents were reported across Guinea.", (undated,)),),
        selected_country="Guinea",
    )
    assert len(claims) == 1
    assert claims[0].source_date is None
    assert claims[0].verification == "partially_verified"


def test_validate_normalized_keeps_and_grades_undated_and_paraphrased():
    from datetime import date
    from cpf_fcv_reviewer import public_research
    from cpf_fcv_reviewer.public_research import SearchArtifact, ResearchSource

    dated = ResearchSource(
        title="Guinea dated",
        url="https://www.crisisgroup.org/guinea-dated",
        publisher="International Crisis Group",
        published_at=date(2026, 8, 30),
        excerpt="Armed clashes displaced thousands in Guinea.",
    )
    undated = ResearchSource(
        title="Guinea undated",
        url="https://www.crisisgroup.org/guinea-undated",
        publisher="International Crisis Group",
        published_at=None,
        excerpt="Security incidents were reported across Guinea.",
    )
    artifact = SearchArtifact(narrative="Synthesis.", sources=(dated, undated))

    def _mk(claim_id, url, quote):
        return public_research.CurrentContextClaim(
            claim_id=claim_id,
            text=quote,
            publisher="International Crisis Group",
            source_title="t",
            source_url=url,
            source_date=date(2026, 8, 30),
            source_type="public institutional source",
            relevance="r",
            context_kind="current_development",
            relationship="establishes",
            licensed_data_required=False,
            supporting_quote=quote,
        )

    dated_exact = _mk("dated-exact", dated.url, "Armed clashes displaced thousands in Guinea.")
    dated_paraphrase = _mk("dated-paraphrase", dated.url, "Thousands were displaced in Guinea.")
    undated_exact = _mk("undated-exact", undated.url, "Security incidents were reported across Guinea.")

    retained = public_research._validate_normalized_claims(
        (dated_exact, dated_paraphrase, undated_exact),
        artifact,
        selected_country="Guinea",
    )
    grades = {claim.claim_id: claim.verification for claim in retained}
    assert grades["dated-exact"] == "verified"
    assert grades["dated-paraphrase"] == "partially_verified"
    assert grades["undated-exact"] == "partially_verified"
    # undated source keeps a null date
    undated_claim = next(c for c in retained if c.claim_id == "undated-exact")
    assert undated_claim.source_date is None
