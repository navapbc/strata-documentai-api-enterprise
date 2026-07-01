"""Tests for utils/textract.py."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from documentai_api.mappings.textract.us_drivers_licenses import FIELD_MAP as DL_FIELD_MAP
from documentai_api.utils.textract import (
    extract_field_values_from_textract_results,
    extract_fields_from_analyze_id,
    finalize_textract_result,
    get_id_type,
    try_textract_identity,
)

# =============================================================================
# Fixtures
# =============================================================================

FIXTURE_DIR = Path(__file__).parent.parent / "helpers" / "fixtures" / "textract"


@pytest.fixture
def analyze_id_response():
    return json.loads((FIXTURE_DIR / "analyze_id_drivers_license.json").read_text())


@pytest.fixture
def analyze_id_response_fields_only():
    return json.loads((FIXTURE_DIR / "analyze_id_drivers_license_fields_only.json").read_text())


# =============================================================================
# extract_fields_from_analyze_id
# =============================================================================


def test_extract_fields_from_analyze_id_maps_to_bda_names(analyze_id_response_fields_only):
    fields = extract_fields_from_analyze_id(analyze_id_response_fields_only, DL_FIELD_MAP)

    assert "NAME_DETAILS.FIRST_NAME" in fields
    assert fields["NAME_DETAILS.FIRST_NAME"]["value"] == "ANDREW"
    assert fields["NAME_DETAILS.FIRST_NAME"]["confidence"] == 0.98

    assert "NAME_DETAILS.LAST_NAME" in fields
    assert fields["NAME_DETAILS.LAST_NAME"]["value"] == "SAMPLE"

    assert "ID_NUMBER" in fields
    assert fields["ID_NUMBER"]["value"] == "99999999"


def test_extract_fields_from_analyze_id_uses_normalized_date(analyze_id_response_fields_only):
    fields = extract_fields_from_analyze_id(analyze_id_response_fields_only, DL_FIELD_MAP)
    # T00:00:00 stripped to date-only
    assert fields["DATE_OF_BIRTH"]["value"] == "1973-01-07"
    assert fields["EXPIRATION_DATE"]["value"] == "2026-01-08"
    assert fields["DATE_OF_ISSUE"]["value"] == "2022-01-07"


def test_extract_fields_from_analyze_id_skips_unmapped_fields(analyze_id_response_fields_only):
    """Fields not in the map (e.g. ID_TYPE) are excluded from output."""
    fields = extract_fields_from_analyze_id(analyze_id_response_fields_only, DL_FIELD_MAP)
    # ID_TYPE is in the response but not in DL_FIELD_MAP
    for bda_name in fields:
        assert "idType" not in bda_name
        assert "ID_TYPE" not in bda_name


def test_extract_fields_from_analyze_id_empty_response():
    fields = extract_fields_from_analyze_id({}, DL_FIELD_MAP)
    assert fields == {}


def test_extract_fields_from_analyze_id_empty_field_map(analyze_id_response_fields_only):
    fields = extract_fields_from_analyze_id(analyze_id_response_fields_only, {})
    assert fields == {}


def test_extract_fields_from_analyze_id_geometry(analyze_id_response):
    """Fields matched to Blocks get bounding box geometry."""
    fields = extract_fields_from_analyze_id(analyze_id_response, DL_FIELD_MAP)

    # GARCIA (FIRST_NAME) -- exact match to WORD block
    assert "geometry" in fields["NAME_DETAILS.FIRST_NAME"]
    bbox = fields["NAME_DETAILS.FIRST_NAME"]["geometry"][0]["boundingBox"]
    assert bbox["Left"] == pytest.approx(0.4058, abs=0.01)

    # MARIA (LAST_NAME) -- exact match to LINE block
    assert "geometry" in fields["NAME_DETAILS.LAST_NAME"]

    # 736HDV7874JSB -- exact match to LINE block
    assert "geometry" in fields["ID_NUMBER"]
    bbox = fields["ID_NUMBER"]["geometry"][0]["boundingBox"]
    assert bbox["Width"] == pytest.approx(0.2097, abs=0.001)

    # D (CLASS) -- exact match to WORD block
    assert "geometry" in fields["CLASS"]

    # 02801 (ZIP) -- exact match to WORD block
    assert "geometry" in fields["ADDRESS_DETAILS.ZIP_CODE"]

    # BIGTOWN (CITY) -- cleaned fallback: "bigtown" == clean("BIGTOWN,")
    assert "geometry" in fields["ADDRESS_DETAILS.CITY"]

    # MA (STATE) -- cleaned fallback: "ma" == clean("MA,")
    assert "geometry" in fields["ADDRESS_DETAILS.STATE"]


# =============================================================================
# get_id_type
# =============================================================================


def test_get_id_type_returns_type(analyze_id_response_fields_only):
    assert get_id_type(analyze_id_response_fields_only) == "DRIVER LICENSE FRONT"


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
            "NAME_DETAILS.FIRST_NAME": {
                "confidence": 0.99,
                "value": "John",
                "geometry": [
                    {"boundingBox": {"Width": 0.1, "Height": 0.05, "Left": 0.4, "Top": 0.5}}
                ],
            },
            "NAME_DETAILS.LAST_NAME": {"confidence": 0.98, "value": "Doe"},
            "ID_NUMBER": {"confidence": 0.97, "value": ""},
        },
    }
    metadata, field_values, field_geometry = extract_field_values_from_textract_results(stored)

    assert len(metadata["field_confidence_map_list"]) == 3
    assert "ID_NUMBER" in metadata["empty_fields"]
    assert field_values["NAME_DETAILS.FIRST_NAME"] == "John"
    assert field_values["ID_NUMBER"] == ""

    # geometry present for fields that have it, absent for those that don't
    assert "NAME_DETAILS.FIRST_NAME" in field_geometry
    assert field_geometry["NAME_DETAILS.FIRST_NAME"]["geometry"] == [
        {"boundingBox": {"Width": 0.1, "Height": 0.05, "Left": 0.4, "Top": 0.5}}
    ]
    assert "NAME_DETAILS.LAST_NAME" not in field_geometry
    assert "ID_NUMBER" not in field_geometry


def test_extract_field_values_from_textract_results_empty():
    metadata, field_values, field_geometry = extract_field_values_from_textract_results(
        {"fields": {}}
    )
    assert metadata["field_confidence_map_list"] == []
    assert metadata["empty_fields"] == []
    assert field_values == {}
    assert field_geometry == {}


# =============================================================================
# try_textract_identity
# =============================================================================


@pytest.mark.parametrize(
    ("category", "content_type", "flag_on"),
    [
        ("identity_verification", "image/jpeg", False),  # flag off
        ("tax_documents", "image/jpeg", True),  # incorrect category
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
        return_value=json.loads(
            (FIXTURE_DIR / "analyze_id_drivers_license_fields_only.json").read_text()
        ),
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


# =============================================================================
# Supplemental Nova extraction pipeline
# =============================================================================


def test_extract_supplemental_fields_via_nova(analyze_id_response, mocker):
    """Nova supplemental extraction identifies physical descriptor fields from Blocks."""
    from documentai_api.utils.textract import extract_supplemental_fields_via_nova

    # Simulate Nova returning identified fields with block_index references
    nova_response = {
        "output": {
            "message": {
                "content": [
                    {
                        "text": json.dumps(
                            {
                                "fields": [
                                    {
                                        "field_name": "PERSONAL_DETAILS.SEX",
                                        "value": "F",
                                        "block_index": 42,
                                    },
                                    {
                                        "field_name": "PERSONAL_DETAILS.EYE_COLOR",
                                        "value": "BLK",
                                        "block_index": 37,
                                    },
                                ]
                            }
                        )
                    }
                ]
            }
        }
    }
    mocker.patch("documentai_api.services.bedrock.invoke_model", return_value=nova_response)

    all_blocks = analyze_id_response["IdentityDocuments"][0]["Blocks"]
    fields = extract_supplemental_fields_via_nova(all_blocks)

    # SEX field extracted with geometry from the "F" WORD block
    assert "PERSONAL_DETAILS.SEX" in fields
    assert fields["PERSONAL_DETAILS.SEX"]["value"] == "F"
    assert "geometry" in fields["PERSONAL_DETAILS.SEX"]
    # confidence from the Textract WORD block for "F"
    assert fields["PERSONAL_DETAILS.SEX"]["confidence"] == pytest.approx(1.0, abs=0.01)

    # EYE_COLOR extracted with geometry from the "BLK" WORD block
    assert "PERSONAL_DETAILS.EYE_COLOR" in fields
    assert fields["PERSONAL_DETAILS.EYE_COLOR"]["value"] == "BLK"
    assert "geometry" in fields["PERSONAL_DETAILS.EYE_COLOR"]


def test_full_textract_pipeline_with_nova_supplemental(analyze_id_response, mocker, monkeypatch):
    """Full pipeline: AnalyzeID fields + Nova supplemental merged into single result."""
    from documentai_api.utils.textract import (
        extract_fields_from_analyze_id,
        extract_supplemental_fields_via_nova,
    )

    # Nova returns physical descriptors
    nova_response = {
        "output": {
            "message": {
                "content": [
                    {
                        "text": json.dumps(
                            {
                                "fields": [
                                    {
                                        "field_name": "PERSONAL_DETAILS.SEX",
                                        "value": "F",
                                        "block_index": 42,
                                    },
                                    {
                                        "field_name": "PERSONAL_DETAILS.HEIGHT",
                                        "value": "4-6",
                                        "block_index": 45,
                                    },
                                ]
                            }
                        )
                    }
                ]
            }
        }
    }
    mocker.patch("documentai_api.services.bedrock.invoke_model", return_value=nova_response)

    # Step 1: AnalyzeID extraction
    fields = extract_fields_from_analyze_id(analyze_id_response, DL_FIELD_MAP)

    # Step 2: Nova supplemental
    all_blocks = analyze_id_response["IdentityDocuments"][0]["Blocks"]
    supplemental = extract_supplemental_fields_via_nova(all_blocks)
    fields.update(supplemental)

    # AnalyzeID fields present
    assert "NAME_DETAILS.FIRST_NAME" in fields
    assert fields["NAME_DETAILS.FIRST_NAME"]["value"] == "GARCIA"
    assert "ID_NUMBER" in fields
    assert fields["EXPIRATION_DATE"]["value"] == "2028-01-20"

    # Nova supplemental fields merged in
    assert "PERSONAL_DETAILS.SEX" in fields
    assert fields["PERSONAL_DETAILS.SEX"]["value"] == "F"
    assert "PERSONAL_DETAILS.HEIGHT" in fields
    assert fields["PERSONAL_DETAILS.HEIGHT"]["value"] == "4-6"

    # Both have geometry
    assert "geometry" in fields["NAME_DETAILS.FIRST_NAME"]
    assert "geometry" in fields["PERSONAL_DETAILS.SEX"]


def test_extract_supplemental_fields_nova_failure_returns_empty(analyze_id_response, mocker):
    """Nova failure gracefully returns empty dict -- doesn't break the pipeline."""
    from documentai_api.utils.textract import extract_supplemental_fields_via_nova

    mocker.patch(
        "documentai_api.services.bedrock.invoke_model",
        side_effect=Exception("Bedrock timeout"),
    )

    all_blocks = analyze_id_response["IdentityDocuments"][0]["Blocks"]
    fields = extract_supplemental_fields_via_nova(all_blocks)

    assert fields == {}


def test_extract_supplemental_fields_unmatched_block_omits_field(analyze_id_response, mocker):
    """When Nova returns an invalid block_index, the field is omitted."""
    from documentai_api.utils.textract import extract_supplemental_fields_via_nova

    nova_response = {
        "output": {
            "message": {
                "content": [
                    {
                        "text": json.dumps(
                            {
                                "fields": [
                                    {
                                        "field_name": "PERSONAL_DETAILS.SEX",
                                        "value": "M",
                                        "block_index": 9999,
                                    },
                                ]
                            }
                        )
                    }
                ]
            }
        }
    }
    mocker.patch("documentai_api.services.bedrock.invoke_model", return_value=nova_response)

    all_blocks = analyze_id_response["IdentityDocuments"][0]["Blocks"]
    fields = extract_supplemental_fields_via_nova(all_blocks)

    # out-of-bounds block_index = field omitted entirely
    assert "PERSONAL_DETAILS.SEX" not in fields


# =============================================================================
# Integration: Nova Micro supplemental extraction (requires AWS credentials)
# Run with: uv run pytest tests/utils/test_textract_util.py -m integration
# =============================================================================


@pytest.mark.integration
def test_nova_extracts_physical_descriptors_from_real_dl(analyze_id_response, monkeypatch):
    """Hit real Nova Micro and verify it identifies physical descriptor fields."""
    from documentai_api.utils.aws_client_factory import AWSClientFactory
    from documentai_api.utils.textract import extract_supplemental_fields_via_nova

    # Clear cached clients so the profile env var takes effect
    AWSClientFactory._session = None
    AWSClientFactory.get_bedrock_runtime_client.cache_clear()

    monkeypatch.setenv("AWS_PROFILE", "nava-sandbox")
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    # Re-clear after monkeypatch sets the env
    AWSClientFactory._session = None
    AWSClientFactory.get_bedrock_runtime_client.cache_clear()

    all_blocks = analyze_id_response["IdentityDocuments"][0]["Blocks"]
    fields = extract_supplemental_fields_via_nova(all_blocks)

    # Should find at least sex and eye color from the fixture DL
    assert len(fields) >= 2, f"Expected at least 2 fields, got: {list(fields.keys())}"

    # SEX should be "F" (from the fixture DL)
    if "PERSONAL_DETAILS.SEX" in fields:
        assert fields["PERSONAL_DETAILS.SEX"]["value"] == "F"
        assert "geometry" in fields["PERSONAL_DETAILS.SEX"]
        # "F" WORD block is at Left ~0.44, Top ~0.84 on the fixture DL
        bbox = fields["PERSONAL_DETAILS.SEX"]["geometry"][0]["boundingBox"]
        assert bbox["Left"] == pytest.approx(0.44, abs=0.02)
        assert bbox["Top"] == pytest.approx(0.84, abs=0.02)
        assert fields["PERSONAL_DETAILS.SEX"]["confidence"] > 0.9

    # EYE_COLOR should be "BLK" (from "18 EYES BLK" on the fixture DL)
    if "PERSONAL_DETAILS.EYE_COLOR" in fields:
        assert fields["PERSONAL_DETAILS.EYE_COLOR"]["value"] == "BLK"
        assert "geometry" in fields["PERSONAL_DETAILS.EYE_COLOR"]
        # "BLK" WORD block is at Left ~0.45, Top ~0.79
        bbox = fields["PERSONAL_DETAILS.EYE_COLOR"]["geometry"][0]["boundingBox"]
        assert bbox["Left"] == pytest.approx(0.45, abs=0.02)
        assert bbox["Top"] == pytest.approx(0.79, abs=0.02)

    # Print results for manual inspection
    for name, data in fields.items():
        print(
            f"  {name}: value={data['value']}, confidence={data['confidence']}, has_geometry={'geometry' in data}"
        )
