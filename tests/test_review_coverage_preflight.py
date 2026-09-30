"""Oversized complete documents fail before paid context research."""
import pytest
from cpf_fcv_reviewer.extraction import ExtractedDocument, ExtractedSegment, ReviewCoverageUnavailable
from cpf_fcv_reviewer.runtime import _require_review_input_budget


def document(text):
    return ExtractedDocument("primary.txt", (ExtractedSegment(text, 1, None, "page 1"),), ())


def test_raw_full_document_overflow_is_rejected():
    with pytest.raises(ReviewCoverageUnavailable):
        _require_review_input_budget({"primary_document": document("x" * 480_001)})


def test_combined_primary_and_package_overflow_is_rejected():
    with pytest.raises(ReviewCoverageUnavailable):
        _require_review_input_budget({"primary_document": document("x" * 300_000),
                                      "package_documents": (document("y" * 200_000),)})


def test_small_full_documents_remain_available():
    _require_review_input_budget({"primary_document": document("Evidence."),
                                 "package_documents": ()})
