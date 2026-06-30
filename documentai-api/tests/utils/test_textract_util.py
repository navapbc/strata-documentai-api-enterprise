"""Tests for utils/textract.py."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from documentai_api.utils.textract import (
    extract_field_values_from_textract_results,
    extract_fields_from_analyze_id,
    finalize_textract_result,
    get_id_type,
    try_textract_identity,
)

# =============================================================================
# extract_fields_from_analyze_id
# =============================================================================

SAMPLE_ANALYZE_ID_RESPONSE = {
    "IdentityDocuments": [
        {
            "IdentityDocumentFields": [
                {
                    "Type": {"Text": "FIRST_NAME"},
                    "ValueDetection": {"Text": "ANDREW", "Confidence": 98.0},
                },
                {
                    "Type": {"Text": "LAST_NAME"},
                    "ValueDetection": {"Text": "SAMPLE", "Confidence": 80.0},
                },
                {
                    "Type": {"Text": "MIDDLE_NAME"},
                    "ValueDetection": {"Text": "JASON", "Confidence": 98.0},
                },
                {
                    "Type": {"Text": "SUFFIX"},
                    "ValueDetection": {"Text": "", "Confidence": 99.0},
                },
                {
                    "Type": {"Text": "CITY_IN_ADDRESS"},
                    "ValueDetection": {"Text": "HARRISBURG", "Confidence": 98.0},
                },
                {
                    "Type": {"Text": "ZIP_CODE_IN_ADDRESS"},
                    "ValueDetection": {"Text": "171010000", "Confidence": 98.0},
                },
                {
                    "Type": {"Text": "STATE_IN_ADDRESS"},
                    "ValueDetection": {"Text": "PA", "Confidence": 85.0},
                },
                {
                    "Type": {"Text": "STATE_NAME"},
                    "ValueDetection": {"Text": "PENNSYLVANIA", "Confidence": 96.0},
                },
                {
                    "Type": {"Text": "DOCUMENT_NUMBER"},
                    "ValueDetection": {"Text": "99999999", "Confidence": 97.0},
                },
                {
                    "Type": {"Text": "EXPIRATION_DATE"},
                    "ValueDetection": {
                        "Text": "01/08/2026",
                        "Confidence": 97.0,
                        "NormalizedValue": {"Value": "2026-01-08T00:00:00"},
                    },
                },
                {
                    "Type": {"Text": "DATE_OF_BIRTH"},
                    "ValueDetection": {
                        "Text": "01/07/1973",
                        "Confidence": 96.0,
                        "NormalizedValue": {"Value": "1973-01-07T00:00:00"},
                    },
                },
                {
                    "Type": {"Text": "DATE_OF_ISSUE"},
                    "ValueDetection": {
                        "Text": "01/07/2022",
                        "Confidence": 97.0,
                        "NormalizedValue": {"Value": "2022-01-07T00:00:00"},
                    },
                },
                {
                    "Type": {"Text": "ENDORSEMENTS"},
                    "ValueDetection": {"Text": "NONE", "Confidence": 98.0},
                },
                {
                    "Type": {"Text": "RESTRICTIONS"},
                    "ValueDetection": {"Text": "NONE", "Confidence": 98.0},
                },
                {
                    "Type": {"Text": "CLASS"},
                    "ValueDetection": {"Text": "D", "Confidence": 59.0},
                },
                {
                    "Type": {"Text": "ADDRESS"},
                    "ValueDetection": {"Text": "123 MAIN STREET APT", "Confidence": 94.0},
                },
                {
                    "Type": {"Text": "COUNTY"},
                    "ValueDetection": {"Text": "", "Confidence": 99.0},
                },
                {
                    "Type": {"Text": "ID_TYPE"},
                    "ValueDetection": {"Text": "DRIVER LICENSE FRONT", "Confidence": 99.0},
                },
            ]
        }
    ]
}

DL_FIELD_MAP = {
    "FIRST_NAME": "NAME_DETAILS.FIRST_NAME",
    "LAST_NAME": "NAME_DETAILS.LAST_NAME",
    "MIDDLE_NAME": "NAME_DETAILS.MIDDLE_NAME",
    "SUFFIX": "NAME_DETAILS.SUFFIX",
    "ADDRESS": "ADDRESS_DETAILS.STREET_ADDRESS",
    "CITY_IN_ADDRESS": "ADDRESS_DETAILS.CITY",
    "ZIP_CODE_IN_ADDRESS": "ADDRESS_DETAILS.ZIP_CODE",
    "STATE_IN_ADDRESS": "ADDRESS_DETAILS.STATE",
    "COUNTY": "COUNTY",
    "DOCUMENT_NUMBER": "ID_NUMBER",
    "EXPIRATION_DATE": "EXPIRATION_DATE",
    "DATE_OF_BIRTH": "DATE_OF_BIRTH",
    "STATE_NAME": "STATE_NAME",
    "DATE_OF_ISSUE": "DATE_OF_ISSUE",
    "CLASS": "CLASS",
    "RESTRICTIONS": "RESTRICTIONS",
    "ENDORSEMENTS": "ENDORSEMENTS",
    "SEX": "PERSONAL_DETAILS.SEX",
}


def test_extract_fields_from_analyze_id_maps_to_bda_names():
    fields = extract_fields_from_analyze_id(SAMPLE_ANALYZE_ID_RESPONSE, DL_FIELD_MAP)

    assert "NAME_DETAILS.FIRST_NAME" in fields
    assert fields["NAME_DETAILS.FIRST_NAME"]["value"] == "ANDREW"
    assert fields["NAME_DETAILS.FIRST_NAME"]["confidence"] == 0.98

    assert "NAME_DETAILS.LAST_NAME" in fields
    assert fields["NAME_DETAILS.LAST_NAME"]["value"] == "SAMPLE"

    assert "ID_NUMBER" in fields
    assert fields["ID_NUMBER"]["value"] == "99999999"


def test_extract_fields_from_analyze_id_uses_normalized_date():
    fields = extract_fields_from_analyze_id(SAMPLE_ANALYZE_ID_RESPONSE, DL_FIELD_MAP)
    # T00:00:00 stripped to date-only
    assert fields["DATE_OF_BIRTH"]["value"] == "1973-01-07"
    assert fields["EXPIRATION_DATE"]["value"] == "2026-01-08"
    assert fields["DATE_OF_ISSUE"]["value"] == "2022-01-07"


def test_extract_fields_from_analyze_id_skips_unmapped_fields():
    """Fields not in the map (e.g. ID_TYPE) are excluded from output."""
    fields = extract_fields_from_analyze_id(SAMPLE_ANALYZE_ID_RESPONSE, DL_FIELD_MAP)
    # ID_TYPE is in the response but not in DL_FIELD_MAP
    for bda_name in fields:
        assert "idType" not in bda_name
        assert "ID_TYPE" not in bda_name


def test_extract_fields_from_analyze_id_empty_response():
    fields = extract_fields_from_analyze_id({}, DL_FIELD_MAP)
    assert fields == {}


def test_extract_fields_from_analyze_id_empty_field_map():
    fields = extract_fields_from_analyze_id(SAMPLE_ANALYZE_ID_RESPONSE, {})
    assert fields == {}


# =============================================================================
# get_id_type
# =============================================================================


def test_get_id_type_returns_type():
    assert get_id_type(SAMPLE_ANALYZE_ID_RESPONSE) == "DRIVER LICENSE FRONT"


def test_get_id_type_returns_none_when_missing():
    response = {"IdentityDocuments": [{"IdentityDocumentFields": []}]}
    assert get_id_type(response) is None


def test_get_id_type_empty_response():
    assert get_id_type({}) is None


# =============================================================================
# extract_field_values_from_textract_results (reading stored S3 results)
# =============================================================================


def test_extract_field_values_from_textract_results():
    stored = {
        "source": "textract",
        "fields": {
            "NAME_DETAILS.FIRST_NAME": {"confidence": 0.99, "value": "John"},
            "NAME_DETAILS.LAST_NAME": {"confidence": 0.98, "value": "Doe"},
            "ID_NUMBER": {"confidence": 0.97, "value": ""},
        },
    }
    metadata, field_values = extract_field_values_from_textract_results(stored)

    assert len(metadata["field_confidence_map_list"]) == 3
    assert "ID_NUMBER" in metadata["empty_fields"]
    assert field_values["NAME_DETAILS.FIRST_NAME"] == "John"
    assert field_values["ID_NUMBER"] == ""


def test_extract_field_values_from_textract_results_empty():
    metadata, field_values = extract_field_values_from_textract_results({"fields": {}})
    assert metadata["field_confidence_map_list"] == []
    assert metadata["empty_fields"] == []
    assert field_values == {}


# =============================================================================
# try_textract_identity
# =============================================================================


@pytest.mark.parametrize(
    ("category", "content_type", "flag_on"),
    [
        ("identity_verification", "image/jpeg", False),  # flag off
        ("tax_documents", "image/jpeg", True),  # wrong category
        ("identity_verification", "image/tiff", True),  # unsupported content type
    ],
)
def test_try_textract_identity_returns_none_early(mocker, category, content_type, flag_on):
    mocker.patch(
        "documentai_api.utils.ssm.is_textract_identity_enabled",
        return_value=flag_on,
    )
    result = try_textract_identity(category, content_type, b"bytes", "key")
    assert result is None


def test_try_textract_identity_returns_result_on_success(mocker, monkeypatch):
    from documentai_api.config.constants import ExtractMethod
    from documentai_api.config.env import EnvVars

    monkeypatch.setenv(EnvVars.DOCUMENTAI_OUTPUT_LOCATION, "s3://test-bucket/output")

    mocker.patch(
        "documentai_api.utils.ssm.is_textract_identity_enabled",
        return_value=True,
    )
    mocker.patch(
        "documentai_api.services.textract.analyze_id",
        return_value=SAMPLE_ANALYZE_ID_RESPONSE,
    )
    mocker.patch("documentai_api.services.s3.put_object")
    mock_set_method = mocker.patch("documentai_api.utils.ddb.set_extract_method")

    result = try_textract_identity("identity_verification", "image/jpeg", b"bytes", "test-key")

    assert result is not None
    assert result["matched_document_class"] == "US-drivers-licenses"
    assert result["textract_s3_uri"] == "s3://test-bucket/output/textract/test-key.json"
    assert len(result["field_confidence_scores"]) > 0
    assert result["extract_started_at"] is not None
    assert result["extract_completed_at"] is not None

    # set_extract_method called before analyze_id
    mock_set_method.assert_called_once()
    call_args = mock_set_method.call_args[0]
    assert call_args[0] == "test-key"
    assert call_args[1] == ExtractMethod.TEXTRACT


def test_try_textract_identity_returns_none_on_textract_failure(mocker, monkeypatch):
    from documentai_api.config.env import EnvVars

    monkeypatch.setenv(EnvVars.DOCUMENTAI_OUTPUT_LOCATION, "s3://test-bucket/output")

    mocker.patch(
        "documentai_api.utils.ssm.is_textract_identity_enabled",
        return_value=True,
    )
    mocker.patch(
        "documentai_api.services.textract.analyze_id",
        side_effect=Exception("Textract down"),
    )

    result = try_textract_identity("identity_verification", "image/jpeg", b"bytes", "test-key")
    assert result is None


# =============================================================================
# finalize_textract_result
# =============================================================================


def test_finalize_textract_result_calls_classify_as_success(mocker):
    mock_classify = mocker.patch("documentai_api.utils.document_lifecycle.classify_as_success")
    mocker.patch("documentai_api.utils.ddb.get_ddb_record", return_value={"tenantId": "t1"})
    mocker.patch("documentai_api.utils.tenants.get_extraction_confidence_floor", return_value=0.65)

    started = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    completed = datetime(2025, 1, 1, 12, 0, 2, tzinfo=UTC)

    textract_result = {
        "matched_document_class": "US-drivers-licenses",
        "field_confidence_scores": [{"NAME_DETAILS.FIRST_NAME": 0.99}],
        "field_empty_list": ["ENDORSEMENTS"],
        "textract_s3_uri": "s3://bucket/output/textract/key.json",
        "extract_started_at": started,
        "extract_completed_at": completed,
        "extract_time": Decimal("2.00"),
    }

    finalize_textract_result("test-key", textract_result, "identity")

    mock_classify.assert_called_once()
    call_kwargs = mock_classify.call_args[1]
    assert call_kwargs["object_key"] == "test-key"
    assert call_kwargs["data"].matched_document_class == "US-drivers-licenses"
    assert call_kwargs["data"].field_empty_list == ["ENDORSEMENTS"]
    assert call_kwargs["data"].bda_output_s3_uri == "s3://bucket/output/textract/key.json"
    assert call_kwargs["below_extraction_confidence_floor"] is False  # 0.99 > 0.65


def test_finalize_textract_result_sets_below_floor_when_low_confidence(mocker):
    mock_classify = mocker.patch("documentai_api.utils.document_lifecycle.classify_as_success")
    mocker.patch("documentai_api.utils.ddb.get_ddb_record", return_value={"tenantId": "t1"})
    mocker.patch("documentai_api.utils.tenants.get_extraction_confidence_floor", return_value=0.90)

    started = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    completed = datetime(2025, 1, 1, 12, 0, 2, tzinfo=UTC)

    textract_result = {
        "matched_document_class": "US-drivers-licenses",
        "field_confidence_scores": [{"NAME_DETAILS.FIRST_NAME": 0.70}],
        "field_empty_list": [],
        "textract_s3_uri": "s3://bucket/output/textract/key.json",
        "extract_started_at": started,
        "extract_completed_at": completed,
        "extract_time": Decimal("2.00"),
    }

    finalize_textract_result("test-key", textract_result, "identity")

    call_kwargs = mock_classify.call_args[1]
    assert call_kwargs["below_extraction_confidence_floor"] is True  # 0.70 < 0.90
