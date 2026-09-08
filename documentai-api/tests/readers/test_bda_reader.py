import json
from pathlib import Path

from documentai_api.readers.bda import extract_field_values_from_bda_results

FIXTURES_DIR = Path(__file__).parent / ".." / "helpers" / "fixtures" / "bda"


def test_extract_field_values_from_bda_results():
    bda_result = {
        "explainability_info": [
            {
                "name": {"confidence": 0.95, "value": "John"},
                "email": {"confidence": 0.85, "value": "john@example.com"},
            }
        ]
    }
    metadata, field_values, _ = extract_field_values_from_bda_results(bda_result)

    assert len(metadata.confidence_scores) == 2
    assert len(metadata.empty_fields) == 0
    assert field_values["name"] == "John"
    assert field_values["email"] == "john@example.com"


def test_extract_field_values_with_geometry(bda_result_with_geometry):
    _, field_values, geometry = extract_field_values_from_bda_results(
        bda_result_with_geometry, include_geometry=True
    )

    assert field_values["tenant_name"] == "Jane Smith"
    assert field_values["amount"] == "100.00"
    assert "tenant_name" in geometry
    assert geometry["tenant_name"]["type"] == "string"
    assert geometry["tenant_name"]["geometry"][0]["boundingBox"]["top"] == 0.31
    # amount has no geometry key in the source
    assert "amount" not in geometry


def test_extract_field_values_geometry_not_included_by_default(bda_result_with_geometry):
    _, _, geometry = extract_field_values_from_bda_results(bda_result_with_geometry)
    # geometry dict is empty when include_geometry is False (default)
    assert geometry == {}


def test_extract_field_values_with_geometry_nested(bda_result_with_geometry):
    """Nested fields carry geometry with the full dotted field name as key."""
    _, field_values, geometry = extract_field_values_from_bda_results(
        bda_result_with_geometry, include_geometry=True
    )

    assert field_values["payment_details.base_rent"] == "1200"
    assert "payment_details.base_rent" in geometry
    assert geometry["payment_details.base_rent"]["type"] == "currency"
    assert geometry["payment_details.base_rent"]["geometry"][0]["boundingBox"]["left"] == 0.3
    # fees has no geometry
    assert "payment_details.fees" not in geometry


def test_extract_fields_identifies_missing_geometry_from_fixture(monkeypatch):
    """Fields without geometry and below threshold are flagged as missing."""
    monkeypatch.setattr("documentai_api.readers.bda._get_missing_geometry_threshold", lambda: 0.25)

    fixture_path = FIXTURES_DIR / "payslip_missing_geometry.json"
    bda_result = json.loads(fixture_path.read_text())

    metadata, _, _ = extract_field_values_from_bda_results(bda_result)

    assert metadata.fields_missing_geometry is not None
    # These fields have values but no geometry and confidence < 0.25
    assert "PayPeriodStartDate" in metadata.fields_missing_geometry
    assert "PayPeriodEndDate" in metadata.fields_missing_geometry
    assert "are_field_names_sufficient" in metadata.fields_missing_geometry

    # Fields WITH geometry should NOT be in the missing list
    assert "CurrentGrossPay" not in metadata.fields_missing_geometry
    assert "RegularHourlyRate" not in metadata.fields_missing_geometry
    assert "EmployeeNumber" not in metadata.fields_missing_geometry

    # Empty fields should be in empty_fields, not missing_geometry
    assert "YTDNetPay" in metadata.empty_fields
    assert "YTDNetPay" not in metadata.fields_missing_geometry

    # Missing geometry fields should NOT be in confidence_scores
    for score_map in metadata.field_confidence_map_list:
        field_name = next(iter(score_map.keys()))
        if field_name in metadata.fields_missing_geometry:
            assert score_map[field_name] not in metadata.confidence_scores
