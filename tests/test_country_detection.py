import pytest

from cpf_fcv_reviewer.country_detection import COUNTRY_ALIASES, detect_country
from cpf_fcv_reviewer.extraction import (
    ExtractedDocument,
    ExtractedSegment,
    ExtractionLimitExceeded,
    extract_document,
)


def document(text: str, name: str = "cpf.txt") -> ExtractedDocument:
    return ExtractedDocument(
        name,
        (ExtractedSegment(text, None, None, "full text"),),
        (),
    )



FY27_PUBLIC_FCV_COUNTRIES = frozenset(
    {
        "Afghanistan",
        "Burkina Faso",
        "Cameroon",
        "Central African Republic",
        "Democratic Republic of the Congo",
        "Ethiopia",
        "Haiti",
        "Iran",
        "Iraq",
        "Lebanon",
        "Libya",
        "Mali",
        "Mozambique",
        "Myanmar",
        "Niger",
        "Nigeria",
        "Papua New Guinea",
        "Somalia",
        "South Sudan",
        "Sudan",
        "Syria",
        "Ukraine",
        "West Bank and Gaza",
        "Yemen",
    }
)
FY27_INSTITUTIONAL_FRAGILITY_COUNTRIES = frozenset(
    {
        "Afghanistan",
        "Central African Republic",
        "Chad",
        "Comoros",
        "Congo",
        "Eritrea",
        "Guinea-Bissau",
        "Haiti",
        "Kiribati",
        "Malawi",
        "Maldives",
        "Marshall Islands",
        "Micronesia",
        "Mozambique",
        "Myanmar",
        "Papua New Guinea",
        "São Tomé and Príncipe",
        "Solomon Islands",
        "Somalia",
        "South Sudan",
        "Sudan",
        "Syria",
        "Timor-Leste",
        "Tuvalu",
        "Yemen",
    }
)


def test_current_public_fragility_lists_are_offline_coverage_inputs_not_gates():
    # World Bank FY2027 lists, effective 2026-07-01. Every listed context uses
    # the same primary selected-country research route as every other registry entry.
    covered = set(COUNTRY_ALIASES)

    assert FY27_PUBLIC_FCV_COUNTRIES <= covered
    assert FY27_INSTITUTIONAL_FRAGILITY_COUNTRIES <= covered


@pytest.mark.parametrize(
    ("title", "country"),
    [
        ("Country Partnership Framework for Somalia for FY27", "Somalia"),
        ("Country Partnership Framework for Guinea for FY27", "Guinea"),
        ("Country Partnership Framework for DRC for FY27", "Democratic Republic of the Congo"),
        ("Country Partnership Framework for Republic of Congo for FY27", "Congo"),
        ("Country Partnership Framework for West Bank & Gaza for FY27", "West Bank and Gaza"),
        ("Country Partnership Framework for Kosovo for FY27", "Kosovo"),
        ("Country Partnership Framework for Turkey for FY27", "Türkiye"),
        ("Country Partnership Framework for Ivory Coast for FY27", "Cote d'Ivoire"),
        ("Country Partnership Framework for Sao Tome and Principe for FY27", "São Tomé and Príncipe"),
        ("Country Partnership Framework for India for FY27", "India"),
        ("Country Partnership Framework for Indonesia for FY27", "Indonesia"),
        ("Country Partnership Framework for Viet Nam for FY27", "Vietnam"),
        ("Country Partnership Framework for Kenya for FY27", "Kenya"),
        ("Country Partnership Framework for Brazil for FY27", "Brazil"),
    ],
)
def test_selected_country_matrix_canonicalizes_without_classification_gate(title, country):
    result = detect_country(document(title))

    assert result.country == country
    assert result.confidence == "high"

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


@pytest.mark.parametrize(
    ("title", "country"),
    [
        (
            "Country Partnership Framework for the Republic of Côte d'Ivoire for FY25-FY29",
            "Cote d'Ivoire",
        ),
        (
            "Country Engagement Note for the Federal Republic of Nigeria, FY25",
            "Nigeria",
        ),
        ("Country Partnership Framework for Viet Nam for FY26", "Vietnam"),
        (
            "Country Partnership Framework for Democratic Republic of Congo for FY26",
            "Democratic Republic of the Congo",
        ),
        (
            "Country Partnership Framework for the Democratic Republic of the Congo for FY26",
            "Democratic Republic of the Congo",
        ),
        (
            "Country Partnership Framework for Republic of Congo for FY26",
            "Congo",
        ),
        (
            "Country Partnership Framework for Republic of the Congo for FY26",
            "Congo",
        ),
        ("Country Partnership Framework for Republic of Korea for FY26", "South Korea"),
        ("Country Partnership Framework for the Republic of Türkiye for FY26", "Türkiye"),
    ],
)
def test_supported_official_and_common_country_names_are_canonicalized(title, country):
    result = detect_country(document(title))

    assert result.country == country
    assert result.confidence == "high"


@pytest.mark.parametrize(
    ("title", "country"),
    [
        ("Country Partnership Framework for Kosovo for FY27", "Kosovo"),
        (
            "Country Engagement Note for West Bank and Gaza for FY27",
            "West Bank and Gaza",
        ),
        (
            "Country Partnership Framework for Palestinian Territories for FY27",
            "West Bank and Gaza",
        ),
    ],
)
def test_supported_territories_are_canonicalized(title, country):
    result = detect_country(document(title))

    assert result.country == country
    assert result.confidence == "high"

@pytest.mark.parametrize(
    "title",
    [
        "Country Partnership Framework for West Africa for FY26",
        "Country Partnership Framework for Chad 2026 for FY26",
        "Country Partnership Framework for Atlantis for FY26",
        "Country Partnership Framework for Chad\x00 for FY26",
        "Country Partnership Framework for Chad_1 for FY26",
    ],
)
def test_untrusted_or_malformed_title_candidates_require_confirmation(title):
    result = detect_country(document(title))

    assert result.country is None
    assert result.confidence == "low"
    assert result.evidence is None


def test_detector_extraction_limits_bound_text_content():
    with pytest.raises(ExtractionLimitExceeded):
        extract_document(b"x" * 101, "cpf.txt", max_characters=100)
