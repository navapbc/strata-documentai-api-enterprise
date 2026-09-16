"""Tests for pipeline/llm.py."""

import pytest

from documentai_api.dtos.extraction import ExtractionResult
from documentai_api.dtos.processing import LlmExtractionMessage, ProcessorResult
from documentai_api.pipeline.llm import run_llm_pipeline

_MODULE = "documentai_api.pipeline.llm"


@pytest.fixture
def extraction_msg():
    return LlmExtractionMessage(
        ddb_key="doc.json",
        document_type="w2",
        ocr_blocks_uri="s3://bucket/llm/ocr/doc.json",
        tenant_id="test-tenant-id",
        batch_id="test-batch-id",
    )


def test_run_llm_pipeline_calls_classify(extraction_msg, mocker):
    extraction = ExtractionResult(document_type="w2")
    processor_result = ProcessorResult(
        object_key="doc.json",
        tenant_id="test-tenant-id",
        batch_id="test-batch-id",
        extraction_result=extraction,
        output_uri="s3://bucket/output.json",
    )
    mocker.patch(f"{_MODULE}.process_llm_result", return_value=processor_result)
    mock_classify = mocker.patch(f"{_MODULE}.classify_extraction_result")

    run_llm_pipeline(extraction_msg)

    mock_classify.assert_called_once_with(
        ddb_key="doc.json",
        result=extraction,
        output_uri="s3://bucket/output.json",
        tenant_id="test-tenant-id",
        batch_id="test-batch-id",
        extraction_method=mocker.ANY,
    )


def test_run_llm_pipeline_raises_when_no_extraction_result(extraction_msg, mocker):
    mocker.patch(
        f"{_MODULE}.process_llm_result",
        return_value=ProcessorResult(object_key="doc.json"),
    )

    with pytest.raises(ValueError, match="no extraction_result"):
        run_llm_pipeline(extraction_msg)
