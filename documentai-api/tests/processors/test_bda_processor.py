from unittest.mock import patch

import pytest

from documentai_api.processors import bda as bda_processor

MOCK_S3_URI = "s3://test-bucket/processed/input/test-tenant/file-name.pdf/de8464af-d53e-44dc-a9f7-ad5360530210/0/custom_output/0/result.json"
MOCK_DDB_RECORD = {"fileName": "input/test-tenant/file-name.pdf", "tenantId": "test-tenant"}

# Realistic BDA output key (matches EventBridge suffix filter)
BDA_OUTPUT_BUCKET = "output-bucket"
BDA_OUTPUT_KEY = "processed/input/test-tenant/file-name.pdf/de8464af-d53e-44dc-a9f7-ad5360530210/0/custom_output/job_metadata.json"


def test_process_bda_output_blueprint_matched_without_user_category():
    """Even with no user-provided category, a matched BDA blueprint produces success + fields."""
    with (
        patch("documentai_api.processors.bda.extract_bda_output_s3_uri") as mock_extract_uri,
        patch("documentai_api.processors.bda.get_bda_result_json") as mock_get_json,
        patch(
            "documentai_api.utils.document_classification.classify_as_success"
        ) as mock_classify_as_success,
        patch(
            "documentai_api.processors.bda.get_ddb_record_from_bda_output",
            return_value=MOCK_DDB_RECORD,
        ),
        patch(
            "documentai_api.utils.document_classification.get_extraction_confidence_floor",
            return_value=0.7,
        ),
        patch(
            "documentai_api.utils.document_classification.tenant_has_confidence_floor",
            return_value=False,
        ),
        patch(
            "documentai_api.utils.document_classification.get_missing_required_fields",
            return_value=None,
        ),
    ):
        mock_extract_uri.return_value = MOCK_S3_URI
        mock_get_json.return_value = {
            "matched_blueprint": {"name": "invoice_blueprint", "confidence": "0.95"},
            "document_class": {"type": "invoice"},
            "explainability_info": [{"field": {"confidence": 0.9, "value": "test"}}],
        }
        mock_classify_as_success.return_value = {"status": "success"}

        result = bda_processor.process_bda_result(BDA_OUTPUT_BUCKET, BDA_OUTPUT_KEY)

        mock_classify_as_success.assert_called_once()
        assert result == {"status": "success"}


def test_process_bda_output_blueprint_matched():
    with (
        patch("documentai_api.processors.bda.extract_bda_output_s3_uri") as mock_extract_uri,
        patch("documentai_api.processors.bda.get_bda_result_json") as mock_get_json,
        patch(
            "documentai_api.utils.document_classification.classify_as_success"
        ) as mock_classify_as_success,
        patch(
            "documentai_api.processors.bda.get_ddb_record_from_bda_output",
            return_value=MOCK_DDB_RECORD,
        ),
        patch(
            "documentai_api.utils.document_classification.get_extraction_confidence_floor",
            return_value=0.7,
        ),
        patch(
            "documentai_api.utils.document_classification.tenant_has_confidence_floor",
            return_value=False,
        ),
        patch(
            "documentai_api.utils.document_classification.get_missing_required_fields",
            return_value=None,
        ),
    ):
        mock_extract_uri.return_value = MOCK_S3_URI
        mock_get_json.return_value = {
            "matched_blueprint": {"name": "invoice_blueprint", "confidence": "0.95"},
            "document_class": {"type": "invoice"},
            "explainability_info": [{"field": {"confidence": 0.9, "value": "test"}}],
        }
        mock_classify_as_success.return_value = {"status": "success"}

        result = bda_processor.process_bda_result(BDA_OUTPUT_BUCKET, BDA_OUTPUT_KEY)

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
        patch("documentai_api.processors.bda.extract_bda_output_s3_uri") as mock_extract_uri,
        patch("documentai_api.processors.bda.get_bda_result_json") as mock_get_json,
        patch("documentai_api.processors.bda.get_text_from_standard_blueprint") as mock_get_text,
        patch(f"documentai_api.processors.bda.{expected_classify_method}") as mock_classify_method,
        patch(
            "documentai_api.processors.bda.get_ddb_record_from_bda_output",
            return_value=MOCK_DDB_RECORD,
        ),
    ):
        mock_extract_uri.return_value = MOCK_S3_URI
        mock_get_json.return_value = {
            "matched_blueprint": {},
            "document_class": {"type": "unknown"},
        }
        mock_get_text.return_value = text
        mock_classify_method.return_value = expected_status

        result = bda_processor.process_bda_result(BDA_OUTPUT_BUCKET, BDA_OUTPUT_KEY)

        mock_classify_method.assert_called_once()
        assert result == expected_status


# =============================================================================
# Extraction confidence floor
# =============================================================================


@pytest.mark.parametrize(
    ("field_confidence_map_list", "empty_fields", "floor", "expected_below"),
    [
        # avg of non-empty fields below floor -> True
        ([{"a": 0.5}, {"b": 0.6}], [], 0.7, True),
        # avg of non-empty fields at/above floor -> False
        ([{"a": 0.8}, {"b": 0.9}], [], 0.7, False),
        ([{"a": 0.7}], [], 0.7, False),  # exactly at floor is not "below"
        # empty fields are excluded from the average
        ([{"a": 0.9}, {"b": 0.1}], ["b"], 0.7, False),
        # no fields extracted -> not below floor
        ([], [], 0.7, False),
        # every field empty -> no scores -> not below floor
        ([{"a": 0.1}], ["a"], 0.7, False),
    ],
)
def test_classify_extraction_result_below_floor(
    field_confidence_map_list, empty_fields, floor, expected_below
):
    from documentai_api.dtos.extraction import ExtractionResult
    from documentai_api.utils.document_classification import classify_extraction_result

    result = ExtractionResult(
        document_type="invoice",
        output_s3_uri="s3://bucket/output.json",
        field_confidence_scores=field_confidence_map_list,
        field_empty_list=empty_fields,
    )

    with (
        patch("documentai_api.utils.document_classification.classify_as_success") as mock_classify,
        patch(
            "documentai_api.utils.document_classification.get_extraction_confidence_floor",
            return_value=floor,
        ),
        patch(
            "documentai_api.utils.document_classification.tenant_has_confidence_floor",
            return_value=True,
        ),
        patch(
            "documentai_api.utils.document_classification.get_missing_required_fields",
            return_value=None,
        ),
    ):
        mock_classify.return_value = {}
        classify_extraction_result("key", result, "tenant")

        call_kwargs = mock_classify.call_args[1]
        assert call_kwargs["below_extraction_confidence_floor"] is expected_below
