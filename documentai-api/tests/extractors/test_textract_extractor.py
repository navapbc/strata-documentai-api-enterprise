import json
from pathlib import Path

import pytest

from documentai_api.extractors.textract import extract_textract_identity

FIXTURE_DIR = Path(__file__).parent.parent / "helpers" / "fixtures" / "textract"


@pytest.fixture
def analyze_id_passport_response():
    return json.loads((FIXTURE_DIR / "analyze_id_passport.json").read_text())


@pytest.mark.parametrize(
    ("content_type", "flag_on"),
    [
        ("image/jpeg", False),  # flag off
        ("image/tiff", True),  # unsupported content type
    ],
)
def test_extract_textract_identity_returns_none_early(mocker, content_type, flag_on):
    mocker.patch(
        "documentai_api.extractors.textract.is_textract_identity_enabled",
        return_value=flag_on,
    )
    result = extract_textract_identity(content_type, b"bytes", "key")
    assert result is None


def test_extract_textract_identity_returns_result_on_success(mocker, monkeypatch):
    from documentai_api.config.constants import ExtractMethod
    from documentai_api.config.env import EnvVars

    monkeypatch.setenv(EnvVars.DOCUMENTAI_OUTPUT_LOCATION, "s3://test-bucket/output")

    mocker.patch(
        "documentai_api.extractors.textract.is_textract_identity_enabled",
        return_value=True,
    )
    mocker.patch(
        "documentai_api.extractors.textract.analyze_id",
        return_value=json.loads(
            (FIXTURE_DIR / "analyze_id_drivers_license_fields_only.json").read_text()
        ),
    )
    mocker.patch("documentai_api.extractors.textract.s3_service.put_object")
    mock_set_method = mocker.patch("documentai_api.extractors.textract.set_extract_method")

    result = extract_textract_identity("image/jpeg", b"bytes", "test-key")

    assert result is not None
    assert result.document_type == "US-drivers-licenses"
    assert result.output_s3_uri == "s3://test-bucket/output/textract/test-key.json"
    assert len(result.field_confidence_scores) > 0
    assert result.extract_started_at is not None
    assert result.extract_completed_at is not None

    mock_set_method.assert_called_once()
    call_args = mock_set_method.call_args[0]
    assert call_args[0] == "test-key"
    assert call_args[1] == ExtractMethod.TEXTRACT


def test_extract_textract_identity_returns_none_on_textract_failure(mocker, monkeypatch):
    from documentai_api.config.env import EnvVars

    monkeypatch.setenv(EnvVars.DOCUMENTAI_OUTPUT_LOCATION, "s3://test-bucket/output")

    mocker.patch(
        "documentai_api.extractors.textract.is_textract_identity_enabled",
        return_value=True,
    )
    mocker.patch(
        "documentai_api.extractors.textract.analyze_id",
        side_effect=Exception("Textract down"),
    )

    result = extract_textract_identity("image/jpeg", b"bytes", "test-key")
    assert result is None


def test_extract_textract_identity_duplicate_dates_falls_back_despite_supplemental(
    mocker, monkeypatch, analyze_id_passport_response
):
    """Duplicate dates trigger BDA fallback even when Nova supplemental would add fields."""
    from documentai_api.config.env import EnvVars

    monkeypatch.setenv(EnvVars.DOCUMENTAI_OUTPUT_LOCATION, "s3://test-bucket/output")

    mocker.patch(
        "documentai_api.extractors.textract.is_textract_identity_enabled",
        return_value=True,
    )

    for field in analyze_id_passport_response["IdentityDocuments"][0]["IdentityDocumentFields"]:
        if field["Type"]["Text"] in ("DATE_OF_ISSUE", "EXPIRATION_DATE"):
            field["ValueDetection"]["Text"] = "07 AUG 2016"
            field["ValueDetection"]["NormalizedValue"] = {
                "Value": "2016-08-07T00:00:00",
                "ValueType": "Date",
            }

    mocker.patch(
        "documentai_api.extractors.textract.analyze_id",
        return_value=analyze_id_passport_response,
    )
    mocker.patch(
        "documentai_api.utils.textract._call_nova_supplemental",
        return_value=[{"field_name": "sex", "value": "F", "block_index": 0}],
    )

    result = extract_textract_identity("image/jpeg", b"bytes", "test-key")
    assert result is None
