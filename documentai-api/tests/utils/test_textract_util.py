import json
from pathlib import Path

import pytest

from documentai_api.mappings.textract.us_drivers_licenses import FIELD_MAP as DL_FIELD_MAP
from documentai_api.mappings.textract.us_drivers_licenses import (
    NON_NORMALIZED_ANALYZE_ID_FIELDS as DL_SUPPLEMENTAL_FIELDS,
)
from documentai_api.mappings.textract.us_drivers_licenses import (
    NOVA_SUPPLEMENTAL_PROMPT as DL_SUPPLEMENTAL_PROMPT,
)
from documentai_api.mappings.textract.us_passports import FIELD_MAP as PASSPORT_FIELD_MAP
from documentai_api.mappings.textract.us_passports import (
    NON_NORMALIZED_ANALYZE_ID_FIELDS as PASSPORT_SUPPLEMENTAL_FIELDS,
)
from documentai_api.mappings.textract.us_passports import (
    NOVA_SUPPLEMENTAL_PROMPT as PASSPORT_SUPPLEMENTAL_PROMPT,
)
from documentai_api.utils.textract import (
    extract_fields_from_analyze_id,
    get_id_type,
)

FIXTURE_DIR = Path(__file__).parent.parent / "helpers" / "fixtures" / "textract"


@pytest.fixture
def analyze_id_response():
    return json.loads((FIXTURE_DIR / "analyze_id_drivers_license.json").read_text())


@pytest.fixture
def analyze_id_response_fields_only():
    return json.loads((FIXTURE_DIR / "analyze_id_drivers_license_fields_only.json").read_text())


@pytest.fixture
def analyze_id_passport_response():
    return json.loads((FIXTURE_DIR / "analyze_id_passport.json").read_text())


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
    assert fields["DATE_OF_BIRTH"]["value"] == "1973-01-07"
    assert fields["EXPIRATION_DATE"]["value"] == "2026-01-08"
    assert fields["DATE_OF_ISSUE"]["value"] == "2022-01-07"


def test_extract_fields_from_analyze_id_skips_unmapped_fields(analyze_id_response_fields_only):
    fields = extract_fields_from_analyze_id(analyze_id_response_fields_only, DL_FIELD_MAP)
    for bda_name in fields:
        assert "idType" not in bda_name
        assert "ID_TYPE" not in bda_name


def test_extract_fields_from_analyze_id_empty_response():
    assert extract_fields_from_analyze_id({}, DL_FIELD_MAP) == {}


def test_extract_fields_from_analyze_id_empty_field_map(analyze_id_response_fields_only):
    assert extract_fields_from_analyze_id(analyze_id_response_fields_only, {}) == {}


def test_extract_fields_from_analyze_id_geometry(analyze_id_response):
    fields = extract_fields_from_analyze_id(analyze_id_response, DL_FIELD_MAP)

    assert "geometry" in fields["NAME_DETAILS.FIRST_NAME"]
    bbox = fields["NAME_DETAILS.FIRST_NAME"]["geometry"][0]["boundingBox"]
    assert bbox["left"] == pytest.approx(0.4058, abs=0.01)

    assert "geometry" in fields["NAME_DETAILS.LAST_NAME"]
    assert "geometry" in fields["ID_NUMBER"]
    bbox = fields["ID_NUMBER"]["geometry"][0]["boundingBox"]
    assert bbox["width"] == pytest.approx(0.2097, abs=0.001)

    assert "geometry" in fields["CLASS"]
    assert "geometry" in fields["ADDRESS_DETAILS.ZIP_CODE"]
    assert "geometry" in fields["ADDRESS_DETAILS.CITY"]
    assert "geometry" in fields["ADDRESS_DETAILS.STATE"]


# =============================================================================
# get_id_type
# =============================================================================


def test_get_id_type_returns_type(analyze_id_response_fields_only):
    assert get_id_type(analyze_id_response_fields_only) == "DRIVER LICENSE FRONT"


def test_get_id_type_returns_none_when_missing():
    assert get_id_type({"IdentityDocuments": [{"IdentityDocumentFields": []}]}) is None


def test_get_id_type_empty_response():
    assert get_id_type({}) is None


# =============================================================================
# extract_supplemental_fields_via_nova
# =============================================================================


def test_extract_supplemental_fields_via_nova(analyze_id_response, mocker):
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
    fields = extract_supplemental_fields_via_nova(
        all_blocks, DL_SUPPLEMENTAL_FIELDS, DL_SUPPLEMENTAL_PROMPT
    )

    assert "PERSONAL_DETAILS.SEX" in fields
    assert fields["PERSONAL_DETAILS.SEX"]["value"] == "F"
    assert "geometry" in fields["PERSONAL_DETAILS.SEX"]
    assert fields["PERSONAL_DETAILS.SEX"]["confidence"] == pytest.approx(1.0, abs=0.01)

    assert "PERSONAL_DETAILS.EYE_COLOR" in fields
    assert fields["PERSONAL_DETAILS.EYE_COLOR"]["value"] == "BLK"
    assert "geometry" in fields["PERSONAL_DETAILS.EYE_COLOR"]


def test_full_textract_pipeline_with_nova_supplemental(analyze_id_response, mocker):
    from documentai_api.utils.textract import (
        extract_fields_from_analyze_id,
        extract_supplemental_fields_via_nova,
    )

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

    fields = extract_fields_from_analyze_id(analyze_id_response, DL_FIELD_MAP)
    all_blocks = analyze_id_response["IdentityDocuments"][0]["Blocks"]
    supplemental = extract_supplemental_fields_via_nova(
        all_blocks, DL_SUPPLEMENTAL_FIELDS, DL_SUPPLEMENTAL_PROMPT
    )
    fields.update(supplemental)

    assert fields["NAME_DETAILS.FIRST_NAME"]["value"] == "GARCIA"
    assert fields["EXPIRATION_DATE"]["value"] == "2028-01-20"
    assert fields["PERSONAL_DETAILS.SEX"]["value"] == "F"
    assert fields["PERSONAL_DETAILS.HEIGHT"]["value"] == "4-6"
    assert "geometry" in fields["NAME_DETAILS.FIRST_NAME"]
    assert "geometry" in fields["PERSONAL_DETAILS.SEX"]


def test_extract_supplemental_fields_nova_failure_returns_empty(analyze_id_response, mocker):
    from documentai_api.utils.textract import extract_supplemental_fields_via_nova

    mocker.patch(
        "documentai_api.services.bedrock.invoke_model", side_effect=Exception("Bedrock timeout")
    )

    all_blocks = analyze_id_response["IdentityDocuments"][0]["Blocks"]
    assert (
        extract_supplemental_fields_via_nova(
            all_blocks, DL_SUPPLEMENTAL_FIELDS, DL_SUPPLEMENTAL_PROMPT
        )
        == {}
    )


def test_extract_supplemental_fields_unmatched_block_omits_field(analyze_id_response, mocker):
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
                                    }
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
    fields = extract_supplemental_fields_via_nova(
        all_blocks, DL_SUPPLEMENTAL_FIELDS, DL_SUPPLEMENTAL_PROMPT
    )
    assert "PERSONAL_DETAILS.SEX" not in fields


# =============================================================================
# Passport
# =============================================================================


def test_extract_fields_from_analyze_id_passport(analyze_id_passport_response):
    fields = extract_fields_from_analyze_id(analyze_id_passport_response, PASSPORT_FIELD_MAP)

    assert fields["name.given_name"]["value"] == "LI"
    assert fields["name.last_name"]["value"] == "JUAN"
    assert fields["document_number"]["value"] == "0002028373"
    assert fields["expiration_date"]["value"] == "2029-05-09"
    assert fields["date_of_birth"]["value"] == "1982-05-01"
    assert fields["date_of_issue"]["value"] == "2019-05-09"
    assert fields["place_of_birth"]["value"] == "NEW YORK CITY"
    assert "mrz_code" in fields


def test_extract_fields_from_analyze_id_passport_geometry(analyze_id_passport_response):
    fields = extract_fields_from_analyze_id(analyze_id_passport_response, PASSPORT_FIELD_MAP)

    assert "geometry" in fields["name.last_name"]
    assert "geometry" in fields["name.given_name"]
    assert "geometry" in fields["document_number"]


def test_get_id_type_passport(analyze_id_passport_response):
    assert get_id_type(analyze_id_passport_response) == "PASSPORT"


def test_passport_supplemental_fields_via_nova(analyze_id_passport_response, mocker):
    from documentai_api.utils.textract import extract_supplemental_fields_via_nova

    nova_response = {
        "output": {
            "message": {
                "content": [
                    {
                        "text": json.dumps(
                            {
                                "fields": [
                                    {"field_name": "sex", "value": "F", "block_index": 7},
                                    {"field_name": "passport_type", "value": "P", "block_index": 2},
                                ]
                            }
                        )
                    }
                ]
            }
        }
    }
    mocker.patch("documentai_api.services.bedrock.invoke_model", return_value=nova_response)

    all_blocks = analyze_id_passport_response["IdentityDocuments"][0]["Blocks"]
    fields = extract_supplemental_fields_via_nova(
        all_blocks, PASSPORT_SUPPLEMENTAL_FIELDS, PASSPORT_SUPPLEMENTAL_PROMPT
    )

    assert fields["sex"]["value"] == "F"
    assert fields["sex"]["confidence"] == pytest.approx(0.97, abs=0.01)
    assert "geometry" in fields["sex"]
    assert fields["passport_type"]["value"] == "P"
    assert "geometry" in fields["passport_type"]


def test_passport_nova_supplemental_skips_unrecognized_fields(analyze_id_passport_response, mocker):
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
                                        "field_name": "PERSONAL_DETAILS.HEIGHT",
                                        "value": "5-11",
                                        "block_index": 0,
                                    }
                                ]
                            }
                        )
                    }
                ]
            }
        }
    }
    mocker.patch("documentai_api.services.bedrock.invoke_model", return_value=nova_response)

    all_blocks = analyze_id_passport_response["IdentityDocuments"][0]["Blocks"]
    fields = extract_supplemental_fields_via_nova(
        all_blocks, PASSPORT_SUPPLEMENTAL_FIELDS, PASSPORT_SUPPLEMENTAL_PROMPT
    )
    assert fields == {}


# =============================================================================
# Duplicate date resolution
# =============================================================================


def test_duplicate_dates_returns_empty(analyze_id_passport_response):
    for field in analyze_id_passport_response["IdentityDocuments"][0]["IdentityDocumentFields"]:
        if field["Type"]["Text"] in ("DATE_OF_ISSUE", "EXPIRATION_DATE"):
            field["ValueDetection"]["Text"] = "07 AUG 2016"
            field["ValueDetection"]["NormalizedValue"] = {
                "Value": "2016-08-07T00:00:00",
                "ValueType": "Date",
            }

    assert extract_fields_from_analyze_id(analyze_id_passport_response, PASSPORT_FIELD_MAP) == {}


def test_duplicate_dates_noop_when_correct(analyze_id_passport_response):
    fields = extract_fields_from_analyze_id(analyze_id_passport_response, PASSPORT_FIELD_MAP)
    assert fields["date_of_issue"]["value"] == "2019-05-09"
    assert fields["expiration_date"]["value"] == "2029-05-09"


@pytest.mark.integration
@pytest.mark.parametrize("rotation", [0, 37, 90, 143, 180, 270])
def test_duplicate_dates_fall_back_to_bda_at_any_rotation(rotation, monkeypatch):
    """When AnalyzeID returns duplicate dates, return empty to fall through to BDA."""
    import io

    import boto3
    from PIL import Image

    img_path = FIXTURE_DIR.parent / "test-documents" / "synthetic-passport.jpg"
    img = Image.open(img_path)
    if rotation:
        img = img.rotate(-rotation, expand=True)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")

    session = boto3.Session(profile_name="nava-sandbox", region_name="us-east-1")
    client = session.client("textract")
    response = client.analyze_id(DocumentPages=[{"Bytes": buf.getvalue()}])

    fields = extract_fields_from_analyze_id(response, PASSPORT_FIELD_MAP)

    if fields:
        issue_val = fields.get("date_of_issue", {}).get("value", "")
        exp_val = fields.get("expiration_date", {}).get("value", "")
        if issue_val and exp_val:
            assert issue_val != exp_val, (
                f"At {rotation}: duplicate dates should have triggered BDA fallback"
            )


@pytest.mark.integration
def test_nova_extracts_physical_descriptors_from_real_dl(analyze_id_response, monkeypatch):
    """Hit real Nova Micro and verify it identifies physical descriptor fields."""
    from documentai_api.services.aws_client_factory import AWSClientFactory
    from documentai_api.utils.textract import extract_supplemental_fields_via_nova

    AWSClientFactory._session = None
    AWSClientFactory.get_bedrock_runtime_client.cache_clear()

    monkeypatch.setenv("AWS_PROFILE", "nava-sandbox")
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    AWSClientFactory._session = None
    AWSClientFactory.get_bedrock_runtime_client.cache_clear()

    all_blocks = analyze_id_response["IdentityDocuments"][0]["Blocks"]
    fields = extract_supplemental_fields_via_nova(
        all_blocks, DL_SUPPLEMENTAL_FIELDS, DL_SUPPLEMENTAL_PROMPT
    )

    assert len(fields) >= 2, f"Expected at least 2 fields, got: {list(fields.keys())}"

    if "PERSONAL_DETAILS.SEX" in fields:
        assert fields["PERSONAL_DETAILS.SEX"]["value"] == "F"
        assert "geometry" in fields["PERSONAL_DETAILS.SEX"]
        bbox = fields["PERSONAL_DETAILS.SEX"]["geometry"][0]["boundingBox"]
        assert bbox["left"] == pytest.approx(0.44, abs=0.02)
        assert bbox["top"] == pytest.approx(0.84, abs=0.02)
        assert fields["PERSONAL_DETAILS.SEX"]["confidence"] > 0.9

    if "PERSONAL_DETAILS.EYE_COLOR" in fields:
        assert fields["PERSONAL_DETAILS.EYE_COLOR"]["value"] == "BLK"
        assert "geometry" in fields["PERSONAL_DETAILS.EYE_COLOR"]
        bbox = fields["PERSONAL_DETAILS.EYE_COLOR"]["geometry"][0]["boundingBox"]
        assert bbox["left"] == pytest.approx(0.45, abs=0.02)
        assert bbox["top"] == pytest.approx(0.79, abs=0.02)
