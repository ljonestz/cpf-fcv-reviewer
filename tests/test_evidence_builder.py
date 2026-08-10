from cpf_fcv_reviewer.contracts import DiagnosticMode
from cpf_fcv_reviewer.evidence_builder import DocumentRole, select_diagnostic_mode


def test_current_rra_enables_alignment_mode():
    documents = (
        DocumentRole("cpf", "CPF.docx", True, False),
        DocumentRole("rra", "RRA.docx", True, True),
    )
    assert select_diagnostic_mode(documents) == DiagnosticMode.RRA_ALIGNMENT


def test_missing_or_unapproved_diagnostic_forces_limited_mode():
    only_cpf = (DocumentRole("cpf", "CPF.docx", True, False),)
    unapproved = (
        DocumentRole("cpf", "CPF.docx", True, False),
        DocumentRole("diagnostic", "Context.docx", True, False),
    )
    assert select_diagnostic_mode(only_cpf) == DiagnosticMode.LIMITED_FRAMING
    assert select_diagnostic_mode(unapproved) == DiagnosticMode.LIMITED_FRAMING
