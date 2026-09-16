"""Tests for pipeline/textract.py."""

from documentai_api.dtos.extraction import ExtractionResult
from documentai_api.dtos.processing import ProcessorResult
from documentai_api.pipeline.textract import run_textract_pipeline

_MODULE = "documentai_api.pipeline.textract"


def test_run_textract_pipeline_returns_true_and_classifies(mocker):
    """When extraction succeeds, classify is called and True is returned."""
    extraction = ExtractionResult(document_type="US-drivers-licenses", body=b"{}")
    processor_result = ProcessorResult(
        object_key="id.jpg",
        tenant_id="tenant-1",
        batch_id="batch-1",
        extraction_result=extraction,
        output_uri="s3://bucket/tenant-1/id.jpg/textract/result.json",
    )
    mocker.patch(f"{_MODULE}.extract_textract_identity", return_value=extraction)
    mocker.patch(f"{_MODULE}.process_textract_result", return_value=processor_result)
    mock_classify = mocker.patch(f"{_MODULE}.classify_extraction_result")

    result = run_textract_pipeline("id.jpg", "image/jpeg", b"bytes", "tenant-1", "batch-1")

    assert result is True
    mock_classify.assert_called_once_with(
        ddb_key="id.jpg",
        result=extraction,
        output_uri="s3://bucket/tenant-1/id.jpg/textract/result.json",
        tenant_id="tenant-1",
        batch_id="batch-1",
        extraction_method=mocker.ANY,
    )


def test_run_textract_pipeline_returns_false_when_extractor_returns_none(mocker):
    """When extract_textract_identity returns None, pipeline returns False."""
    mocker.patch(f"{_MODULE}.extract_textract_identity", return_value=None)
    mock_classify = mocker.patch(f"{_MODULE}.classify_extraction_result")

    result = run_textract_pipeline("id.jpg", "image/jpeg", b"bytes", "tenant-1")

    assert result is False
    mock_classify.assert_not_called()


def test_run_textract_pipeline_returns_false_when_processor_has_no_extraction_result(mocker):
    """When processor returns no extraction_result, pipeline returns False."""
    extraction = ExtractionResult(document_type="US-drivers-licenses", body=b"{}")
    mocker.patch(f"{_MODULE}.extract_textract_identity", return_value=extraction)
    mocker.patch(
        f"{_MODULE}.process_textract_result",
        return_value=ProcessorResult(object_key="id.jpg", extraction_result=None),
    )
    mock_classify = mocker.patch(f"{_MODULE}.classify_extraction_result")

    result = run_textract_pipeline("id.jpg", "image/jpeg", b"bytes", "tenant-1")

    assert result is False
    mock_classify.assert_not_called()
