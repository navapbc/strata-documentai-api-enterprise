from documentai_api.dtos.extraction import ExtractionResult
from documentai_api.dtos.processing import ProcessorResult
from documentai_api.processors.textract import process_textract_result


def test_process_textract_result_returns_processor_result(mocker):
    mocker.patch(
        "documentai_api.processors.textract.get_ddb_record", return_value={"tenantId": "t1"}
    )
    mocker.patch(
        "documentai_api.processors.textract.write_extraction_output",
        return_value="s3://bucket/t1/test-key/textract/result.json",
    )

    result = ExtractionResult(
        document_type="US-drivers-licenses",
        field_confidence_scores=[{"NAME_DETAILS.FIRST_NAME": 0.99}],
        field_empty_list=["ENDORSEMENTS"],
        body=b"{}",
    )

    processor_result = process_textract_result("test-key", result, batch_id="b1")

    assert isinstance(processor_result, ProcessorResult)
    assert processor_result.object_key == "test-key"
    assert processor_result.tenant_id == "t1"
    assert processor_result.batch_id == "b1"
    assert processor_result.extraction_result is result
    assert processor_result.output_uri == "s3://bucket/t1/test-key/textract/result.json"


def test_process_textract_result_handles_missing_ddb_record(mocker):
    mocker.patch("documentai_api.processors.textract.get_ddb_record", return_value=None)

    result = ExtractionResult(document_type="US-drivers-licenses")

    processor_result = process_textract_result("test-key", result)

    assert processor_result.tenant_id is None
    assert processor_result.output_uri is None
    assert processor_result.extraction_result is result
