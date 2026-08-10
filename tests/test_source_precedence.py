import pytest

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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_id", "  "),
        ("title", "  "),
        ("version", "  "),
        ("source_kind", "unapproved_kind"),
        ("is_current", "true"),
    ],
)
def test_source_candidate_rejects_invalid_runtime_values(field, value):
    candidate = {
        "source_id": "source-1",
        "title": "Country RRA.docx",
        "version": "3",
        "source_kind": "upload",
        "is_current": True,
    }
    candidate[field] = value

    with pytest.raises(ValueError):
        SourceCandidate(**candidate)


def test_current_upload_is_used_when_no_current_original_exists():
    upload = SourceCandidate("up-1", "Country RRA.docx", "3", "upload", True)

    assert choose_authoritative_source((upload,)) == upload


def test_ambiguous_current_uploads_require_user_fallback():
    first = SourceCandidate("up-1", "Country RRA A.docx", "3", "upload", True)
    second = SourceCandidate("up-2", "Country RRA B.docx", "4", "upload", True)

    assert choose_authoritative_source((first, second)) is None


def test_stale_candidates_are_not_selected():
    stale_original = SourceCandidate("sp-1", "Country RRA.docx", "3", "sharepoint_original", False)
    stale_upload = SourceCandidate("up-1", "Country RRA.docx", "3", "upload", False)

    assert choose_authoritative_source((stale_original, stale_upload)) is None
