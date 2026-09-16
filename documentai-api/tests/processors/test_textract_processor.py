import pytest

from documentai_api.config.constants import ExtractMethod
from documentai_api.dtos.extraction import ExtractionResult
from documentai_api.dtos.processing import ProcessorResult
from documentai_api.processors.textract import process_textract_result


def test_process_textract_result_returns_processor_result(mocker):
    mocker.patch(
        "documentai_api.processors.textract.get_ddb_record",
        return_value={"tenantId": "test-tenant-id"},
    )
    mock_write = mocker.patch(
        "documentai_api.processors.textract.write_extraction_output",
        return_value="s3://bucket/test-tenant-id/test-object-key/textract/result.json",
    )

    result = ExtractionResult(
        document_type="US-drivers-licenses",
        field_confidence_scores=[{"NAME_DETAILS.FIRST_NAME": 0.99}],
        field_empty_list=["ENDORSEMENTS"],
        body=b"{}",
    )

    processor_result = process_textract_result("test-object-key", result, batch_id="test-batch-id")

    assert isinstance(processor_result, ProcessorResult)
    assert processor_result.object_key == "test-object-key"
    assert processor_result.tenant_id == "test-tenant-id"
    assert processor_result.batch_id == "test-batch-id"
    assert processor_result.extraction_result is result
    assert (
        processor_result.output_uri
        == "s3://bucket/test-tenant-id/test-object-key/textract/result.json"
    )
    mock_write.assert_called_once_with(
        "test-tenant-id",
        ExtractMethod.TEXTRACT,
        "test-object-key",
        b"{}",
        content_type="application/json",
    )


def test_process_textract_result_raises_on_missing_tenant(mocker):
    mocker.patch("documentai_api.processors.textract.get_ddb_record", return_value=None)

    result = ExtractionResult(document_type="US-drivers-licenses")

    with pytest.raises(
        ValueError, match="tenant_id is required for Textract extraction of test-object-key"
    ):
        process_textract_result("test-object-key", result)
