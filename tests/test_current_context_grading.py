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
