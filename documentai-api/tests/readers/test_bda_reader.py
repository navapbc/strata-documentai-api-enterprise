import json
from pathlib import Path

from documentai_api.readers.bda import read_bda_output

FIXTURES_DIR = Path(__file__).parent / ".." / "helpers" / "fixtures" / "bda"


def test_read_bda_output():
    bda_result = {
        "explainability_info": [
            {
                "name": {"confidence": 0.95, "value": "John"},
                "email": {"confidence": 0.85, "value": "john@example.com"},
            }
        ]
    }
    result = read_bda_output(bda_result)

    assert len(result.field_confidence_map_list) == 2
    assert len(result.empty_fields) == 0
    assert result.field_values["name"] == "John"
    assert result.field_values["email"] == "john@example.com"


def test_read_bda_output_with_geometry(bda_result_with_geometry):
    result = read_bda_output(bda_result_with_geometry, include_geometry=True)

    assert result.field_values["tenant_name"] == "Jane Smith"
    assert result.field_values["amount"] == "100.00"
    assert "tenant_name" in result.field_geometry
    assert result.field_geometry["tenant_name"]["type"] == "string"
    assert result.field_geometry["tenant_name"]["geometry"][0]["boundingBox"]["top"] == 0.31
    # amount has no geometry key in the source
    assert "amount" not in result.field_geometry


def test_read_bda_output_geometry_not_included_by_default(bda_result_with_geometry):
    result = read_bda_output(bda_result_with_geometry)
    assert result.field_geometry == {}


def test_read_bda_output_with_geometry_nested(bda_result_with_geometry):
    """Nested fields carry geometry with the full dotted field name as key."""
    result = read_bda_output(bda_result_with_geometry, include_geometry=True)

    assert result.field_values["payment_details.base_rent"] == "1200"
    assert "payment_details.base_rent" in result.field_geometry
    assert result.field_geometry["payment_details.base_rent"]["type"] == "currency"
    assert (
        result.field_geometry["payment_details.base_rent"]["geometry"][0]["boundingBox"]["left"]
        == 0.3
    )
    assert "payment_details.fees" not in result.field_geometry


def test_read_bda_output_identifies_missing_geometry_from_fixture(monkeypatch):
    """Fields without geometry and below threshold are flagged as missing."""
    monkeypatch.setattr("documentai_api.readers.bda._get_missing_geometry_threshold", lambda: 0.25)

    fixture_path = FIXTURES_DIR / "payslip_missing_geometry.json"
    bda_result = json.loads(fixture_path.read_text())

    result = read_bda_output(bda_result)

    assert result.fields_missing_geometry is not None
    assert "PayPeriodStartDate" in result.fields_missing_geometry
    assert "PayPeriodEndDate" in result.fields_missing_geometry
    assert "are_field_names_sufficient" in result.fields_missing_geometry

    assert "CurrentGrossPay" not in result.fields_missing_geometry
    assert "RegularHourlyRate" not in result.fields_missing_geometry
    assert "EmployeeNumber" not in result.fields_missing_geometry

    assert "YTDNetPay" in result.empty_fields
    assert "YTDNetPay" not in result.fields_missing_geometry

    confidence_map_field_names = {next(iter(m.keys())) for m in result.field_confidence_map_list}
    for field in result.fields_missing_geometry:
        assert field in confidence_map_field_names

    expected_score_count = (
        len(result.field_confidence_map_list)
        - len(result.empty_fields)
        - len(result.fields_missing_geometry)
    )
    assert len(result.confidence_scores) == expected_score_count
