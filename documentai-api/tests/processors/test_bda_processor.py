from unittest.mock import patch

import pytest

from documentai_api.config.constants import ProcessStatus
from documentai_api.dtos.processing import ProcessorResult
from documentai_api.processors import bda as bda_processor

MOCK_S3_URI = "s3://test-bucket/processed/input/test-tenant/file-name.pdf/de8464af-d53e-44dc-a9f7-ad5360530210/0/custom_output/0/result.json"
MOCK_DDB_RECORD = {"fileName": "input/test-tenant/file-name.pdf", "tenantId": "test-tenant"}

BDA_OUTPUT_BUCKET = "output-bucket"
BDA_OUTPUT_KEY = "processed/input/test-tenant/file-name.pdf/de8464af-d53e-44dc-a9f7-ad5360530210/0/custom_output/job_metadata.json"


def test_process_bda_result_blueprint_matched_returns_extraction_result():
    """Matched blueprint returns ProcessorResult with extraction_result set."""
    with (
        patch("documentai_api.processors.bda.extract_bda_output_s3_uri") as mock_extract_uri,
        patch("documentai_api.processors.bda.get_bda_result_json") as mock_get_json,
        patch(
            "documentai_api.processors.bda.get_ddb_record_from_bda_output",
            return_value=MOCK_DDB_RECORD,
        ),
        patch("documentai_api.processors.bda.extract_bda_result") as mock_extract,
    ):
        mock_extract_uri.return_value = MOCK_S3_URI
        mock_get_json.return_value = {
            "matched_blueprint": {"name": "invoice_blueprint", "confidence": "0.95"},
            "document_class": {"type": "invoice"},
            "explainability_info": [{"field": {"confidence": 0.9, "value": "test"}}],
        }
        from documentai_api.dtos.extraction import ExtractionResult
        from documentai_api.utils.bda import MatchedBlueprintInfo

        extraction_result = ExtractionResult(document_type="invoice")
        mock_extract.return_value = (
            extraction_result,
            MatchedBlueprintInfo(name="invoice_blueprint", confidence=0.95),
        )

        result = bda_processor.process_bda_result(BDA_OUTPUT_BUCKET, BDA_OUTPUT_KEY)

        assert isinstance(result, ProcessorResult)
        assert result.extraction_result is extraction_result
        assert result.status is None
        assert result.tenant_id == "test-tenant"
        assert result.object_key == "input/test-tenant/file-name.pdf"


@pytest.mark.parametrize(
    ("text", "expected_status"),
    [
        ("a" * 100, ProcessStatus.NO_CUSTOM_BLUEPRINT_MATCHED),
        ("abc", ProcessStatus.NO_DOCUMENT_DETECTED),
    ],
)
def test_process_bda_result_no_matching_blueprint(text, expected_status):
    """No matching blueprint returns ProcessorResult with appropriate status."""
    with (
        patch("documentai_api.processors.bda.extract_bda_output_s3_uri") as mock_extract_uri,
        patch("documentai_api.processors.bda.get_bda_result_json") as mock_get_json,
        patch("documentai_api.processors.bda.get_text_from_standard_blueprint") as mock_get_text,
        patch(
            "documentai_api.processors.bda.get_ddb_record_from_bda_output",
            return_value=MOCK_DDB_RECORD,
        ),
        patch("documentai_api.processors.bda.extract_bda_result") as mock_extract,
    ):
        mock_extract_uri.return_value = MOCK_S3_URI
        mock_get_json.return_value = {
            "matched_blueprint": {},
            "document_class": {"type": "unknown"},
        }
        mock_get_text.return_value = text
        from documentai_api.utils.bda import MatchedBlueprintInfo

        mock_extract.return_value = (None, MatchedBlueprintInfo(name="unknown", confidence=0.1))

        result = bda_processor.process_bda_result(BDA_OUTPUT_BUCKET, BDA_OUTPUT_KEY)

        assert isinstance(result, ProcessorResult)
        assert result.extraction_result is None
        assert result.status == expected_status
        assert result.classification_data is not None


# =============================================================================
# Extraction confidence floor (tests classify_extraction_result directly)
# =============================================================================


@pytest.mark.parametrize(
    ("field_confidence_map_list", "empty_fields", "floor", "expected_below"),
    [
        ([{"a": 0.5}, {"b": 0.6}], [], 0.7, True),
        ([{"a": 0.8}, {"b": 0.9}], [], 0.7, False),
        ([{"a": 0.7}], [], 0.7, False),
        ([{"a": 0.9}, {"b": 0.1}], ["b"], 0.7, False),
        ([], [], 0.7, False),
        ([{"a": 0.1}], ["a"], 0.7, False),
    ],
)
def test_classify_extraction_result_below_floor(
    field_confidence_map_list, empty_fields, floor, expected_below
):
    from documentai_api.classifiers.document_classification import classify_extraction_result
    from documentai_api.dtos.extraction import ExtractionResult

    result = ExtractionResult(
        document_type="invoice",
        field_confidence_scores=field_confidence_map_list,
        field_empty_list=empty_fields,
    )

    with (
        patch(
            "documentai_api.classifiers.document_classification.get_ddb_record",
            return_value={},
        ),
        patch(
            "documentai_api.classifiers.document_classification.classify_as_success"
        ) as mock_classify,
        patch(
            "documentai_api.classifiers.document_classification.get_extraction_confidence_floor",
            return_value=floor,
        ),
        patch(
            "documentai_api.classifiers.document_classification.tenant_has_confidence_floor",
            return_value=True,
        ),
        patch(
            "documentai_api.classifiers.document_classification.get_missing_required_fields",
            return_value=None,
        ),
    ):
        mock_classify.return_value = {}
        classify_extraction_result(
            "key", result, output_uri="s3://bucket/output.json", tenant_id="tenant"
        )

        call_kwargs = mock_classify.call_args[1]
        assert call_kwargs["below_extraction_confidence_floor"] is expected_below
