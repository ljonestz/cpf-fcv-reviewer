from cpf_fcv_reviewer.country_detection import detect_country
from cpf_fcv_reviewer.extraction import ExtractedDocument, ExtractedSegment


def document(text: str, name: str = "cpf.txt") -> ExtractedDocument:
    return ExtractedDocument(
        name,
        (ExtractedSegment(text, None, None, "full text"),),
        (),
    )


def test_detects_country_from_cpf_title():
    result = detect_country(
        document("Country Partnership Framework for the Republic of Chad for FY26-FY30")
    )

    assert result.country == "Chad"
    assert result.confidence == "high"
    assert result.evidence is not None
    assert result.evidence.startswith(
        "Country Partnership Framework for the Republic of Chad"
    )
    assert len(result.evidence) <= 240


def test_detects_country_from_cen_title():
    result = detect_country(
        document("Country Engagement Note for the Federal Republic of Nigeria, FY25")
    )

    assert result.country == "Nigeria"
    assert result.confidence == "high"


def test_normalizes_the_republic_prefix_case_insensitively():
    result = detect_country(
        document("Country Partnership Framework for The Republic of The Gambia for FY26")
    )

    assert result.country == "The Gambia"


def test_ambiguous_title_requires_confirmation():
    result = detect_country(document("Regional country partnership discussion draft"))

    assert result.country is None
    assert result.confidence == "low"
    assert result.evidence is None


def test_country_like_text_outside_a_supported_title_is_not_detected():
    result = detect_country(
        document("The Republic of Chad is discussed in the regional context note.")
    )

    assert result.country is None
    assert result.confidence == "low"


def test_detection_evidence_is_bounded_to_the_title():
    result = detect_country(
        document(
            "Country Partnership Framework for Chad for FY26-FY30\n"
            + "Sensitive supporting text " * 1000
        )
    )

    assert result.country == "Chad"
    assert result.evidence is not None
    assert len(result.evidence) <= 240
