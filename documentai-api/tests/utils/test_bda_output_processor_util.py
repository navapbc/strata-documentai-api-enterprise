from unittest.mock import patch

import pytest

from documentai_api.utils import bda_output_processor as bda_output_processor_util
from documentai_api.utils.response_codes import ResponseCodes

MOCK_S3_URI = "s3://test-bucket/processed/input/file-name/de8464af-d53e-44dc-a9f7-ad5360530210/0/custom_output/0/result.json"
MOCK_DDB_RECORD = {"fileName": "test.pdf"}


@pytest.mark.parametrize(
    ("bda_result", "expected_response_code", "expected_has_confidence_map"),
    [
        (
            {"explainability_info": [{"field1": {"confidence": 0.9, "value": "data"}}]},
            ResponseCodes.SUCCESS,
            True,
        ),
        ({}, ResponseCodes.INTERNAL_PROCESSING_ERROR, False),
    ],
)
def test_get_bda_processing_results(
    bda_result, expected_response_code, expected_has_confidence_map
):
    result = bda_output_processor_util.get_bda_processing_results(bda_result)

    assert result.response_code == expected_response_code
    if expected_has_confidence_map:
        assert len(result.field_confidence_map_list) > 0
    else:
        assert result.empty_field_list == []
        assert result.field_confidence_map_list == []


@pytest.mark.parametrize(
    ("bda_result", "expected_name", "expected_confidence"),
    [
        (
            {"matched_blueprint": {"name": "invoice_blueprint", "confidence": "0.95"}},
            "invoice_blueprint",
            "0.95",
        ),
        ({}, None, None),
    ],
)
def test_get_matched_blueprint(bda_result, expected_name, expected_confidence):
    result = bda_output_processor_util.get_matched_blueprint(bda_result)

    assert result.name == expected_name
    assert result.confidence == expected_confidence


def test_process_bda_output_blueprint_matched_without_user_category():
    """Even with no user-provided category, a matched BDA blueprint produces success + fields."""
    with (
        patch(
            "documentai_api.utils.bda_output_processor.extract_bda_output_s3_uri"
        ) as mock_extract_uri,
        patch("documentai_api.utils.bda_output_processor.get_bda_result_json") as mock_get_json,
        patch(
            "documentai_api.utils.bda_output_processor.classify_as_success"
        ) as mock_classify_as_success,
        patch("documentai_api.utils.bda_output_processor.get_required_env", return_value="x"),
        patch("documentai_api.services.ddb.query_by_key", return_value=[MOCK_DDB_RECORD]),
    ):
        mock_extract_uri.return_value = MOCK_S3_URI
        mock_get_json.return_value = {
            "matched_blueprint": {"name": "invoice_blueprint", "confidence": "0.95"},
            "document_class": {"type": "invoice"},
            "explainability_info": [{"field": {"confidence": 0.9, "value": "test"}}],
        }
        mock_classify_as_success.return_value = {"status": "success"}

        result = bda_output_processor_util.process_bda_output("bucket", "key")

        mock_classify_as_success.assert_called_once()
        assert result == {"status": "success"}


def test_process_bda_output_blueprint_matched():
    with (
        patch(
            "documentai_api.utils.bda_output_processor.extract_bda_output_s3_uri"
        ) as mock_extract_uri,
        patch("documentai_api.utils.bda_output_processor.get_bda_result_json") as mock_get_json,
        patch(
            "documentai_api.utils.bda_output_processor.classify_as_success"
        ) as mock_classify_as_success,
        patch("documentai_api.utils.bda_output_processor.get_required_env", return_value="x"),
        patch("documentai_api.services.ddb.query_by_key", return_value=[MOCK_DDB_RECORD]),
    ):
        mock_extract_uri.return_value = MOCK_S3_URI
        mock_get_json.return_value = {
            "matched_blueprint": {"name": "invoice_blueprint", "confidence": "0.95"},
            "document_class": {"type": "invoice"},
            "explainability_info": [{"field": {"confidence": 0.9, "value": "test"}}],
        }
        mock_classify_as_success.return_value = {"status": "success"}

        result = bda_output_processor_util.process_bda_output("bucket", "key")

        mock_classify_as_success.assert_called_once()
        assert result == {"status": "success"}


@pytest.mark.parametrize(
    ("text", "expected_status", "expected_classify_method"),
    [
        ("a" * 100, "success", "classify_as_no_custom_blueprint_matched"),
        ("abc", "failure", "classify_as_no_document_detected"),
    ],
)
def test_process_bda_output_no_matching_blueprint(text, expected_status, expected_classify_method):
    with (
        patch(
            "documentai_api.utils.bda_output_processor.extract_bda_output_s3_uri"
        ) as mock_extract_uri,
        patch("documentai_api.utils.bda_output_processor.get_bda_result_json") as mock_get_json,
        patch(
            "documentai_api.utils.bda_output_processor.get_text_from_standard_blueprint"
        ) as mock_get_text,
        patch(
            f"documentai_api.utils.bda_output_processor.{expected_classify_method}"
        ) as mock_classify_method,
        patch("documentai_api.utils.bda_output_processor.get_required_env", return_value="x"),
        patch("documentai_api.services.ddb.query_by_key", return_value=[MOCK_DDB_RECORD]),
    ):
        mock_extract_uri.return_value = MOCK_S3_URI
        mock_get_json.return_value = {
            "matched_blueprint": {},
            "document_class": {"type": "unknown"},
        }
        mock_get_text.return_value = text
        mock_classify_method.return_value = expected_status

        result = bda_output_processor_util.process_bda_output("bucket", "key")

        mock_classify_method.assert_called_once()
        assert result == expected_status
