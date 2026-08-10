from cpf_fcv_reviewer.sources import SourceCandidate, choose_authoritative_source


def test_direct_sharepoint_original_beats_derived_markdown():
    original = SourceCandidate(
        source_id="sp-1",
        title="Country RRA.docx",
        version="3",
        source_kind="sharepoint_original",
        is_current=True,
    )
    derived = SourceCandidate(
        source_id="md-1",
        title="Country RRA.md",
        version="3",
        source_kind="derived_copy",
        is_current=True,
    )

    assert choose_authoritative_source((derived, original)) == original


def test_ambiguous_current_originals_require_user_fallback():
    first = SourceCandidate("sp-1", "RRA A.docx", "3", "sharepoint_original", True)
    second = SourceCandidate("sp-2", "RRA B.docx", "4", "sharepoint_original", True)

    assert choose_authoritative_source((first, second)) is None
