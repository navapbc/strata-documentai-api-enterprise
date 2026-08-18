"""Tests for documentai_api.utils.field_labels."""

import json

import pytest

from documentai_api.utils.field_labels import (
    _load_labels,
    _to_human_label,
    get_field_label,
    get_valid_fields,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    _load_labels.cache_clear()
    yield
    _load_labels.cache_clear()


@pytest.mark.parametrize(
    ("field_name", "expected"),
    [
        ("first_name", "First Name"),
        ("employer_info.employer_name", "Employer Info Employer Name"),
        ("employer_info.ein", "Employer Info EIN"),
        ("employee_general_info.ssn", "Employee General Info SSN"),
        ("other", "Other"),
        ("firstName", "First Name"),
        ("ssn", "SSN"),
        ("filing_info.omb_number", "Filing Info OMB Number"),
        # digit boundaries split out
        ("MiscellaneousIncome.Box1", "Miscellaneous Income Box 1"),
        ("StatePayerStateNo.Box17Row0", "State Payer State No Box 17 Row 0"),
        ("EmployeeAddress.Line2", "Employee Address Line 2"),
        ("ProprietorInformation.Form1099Required", "Proprietor Information Form 1099 Required"),
        # added acronyms
        ("InterestIncomeReporting.TaxExemptCUSIP", "Interest Income Reporting Tax Exempt CUSIP"),
        ("mrz_code", "MRZ Code"),
    ],
)
def test_to_human_label(field_name, expected):
    assert _to_human_label(field_name) == expected


def test_get_field_label_returns_curated_label(tmp_path, monkeypatch):
    labels = {"employer_info.ein": "EIN"}
    (tmp_path / "w2.json").write_text(json.dumps(labels))
    monkeypatch.setattr("documentai_api.utils.field_labels.LABELS_DIR", tmp_path)

    assert get_field_label("W2", "employer_info.ein") == "EIN"


def test_get_field_label_falls_back_when_field_missing(tmp_path, monkeypatch):
    labels = {"employer_info.ein": "EIN"}
    (tmp_path / "w2.json").write_text(json.dumps(labels))
    monkeypatch.setattr("documentai_api.utils.field_labels.LABELS_DIR", tmp_path)

    assert get_field_label("W2", "unknown_field") == "Unknown Field"


def test_get_field_label_falls_back_when_no_label_file(tmp_path, monkeypatch):
    monkeypatch.setattr("documentai_api.utils.field_labels.LABELS_DIR", tmp_path)

    assert get_field_label("NonExistentType", "some_field") == "Some Field"


def test_get_field_label_falls_back_when_document_type_none():
    assert get_field_label(None, "employer_info.ein") == "Employer Info EIN"


def test_get_field_label_case_insensitive_file_lookup(tmp_path, monkeypatch):
    labels = {"wages": "Total Wages"}
    (tmp_path / "w2.json").write_text(json.dumps(labels))
    monkeypatch.setattr("documentai_api.utils.field_labels.LABELS_DIR", tmp_path)

    assert get_field_label("W2", "wages") == "Total Wages"
    _load_labels.cache_clear()
    assert get_field_label("w2", "wages") == "Total Wages"


def test_get_valid_fields_returns_lowercase_to_normalized_dict(tmp_path, monkeypatch):
    labels = {"EmployeeName.FirstName": "Employee First Name", "GrossPay": "Gross Pay"}
    (tmp_path / "payslip.json").write_text(json.dumps(labels))
    monkeypatch.setattr("documentai_api.utils.field_labels.LABELS_DIR", tmp_path)

    result = get_valid_fields("payslip")

    assert result == {"employeename.firstname": "EmployeeName.FirstName", "grosspay": "GrossPay"}


def test_get_valid_fields_returns_none_for_unknown_type(tmp_path, monkeypatch):
    monkeypatch.setattr("documentai_api.utils.field_labels.LABELS_DIR", tmp_path)

    assert get_valid_fields("unknown-type") is None


def test_get_valid_fields_last_wins_on_case_collision(tmp_path, monkeypatch):
    """If two keys differ only by case, the last one in JSON iteration order wins."""
    import json

    # dict preserves insertion order in Python 3.7+
    labels = {"SSN": "SSN Label", "ssn": "ssn label"}
    (tmp_path / "w2.json").write_text(json.dumps(labels))
    monkeypatch.setattr("documentai_api.utils.field_labels.LABELS_DIR", tmp_path)

    result = get_valid_fields("w2")

    assert result == {"ssn": "ssn"}
