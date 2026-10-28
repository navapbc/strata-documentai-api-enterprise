"""Tests for processors/ocr_mapping.py."""

import pytest

from documentai_api.dtos.extraction import ExtractionResult
from documentai_api.dtos.processing import OcrMappingMessage, ProcessorResult
from documentai_api.processors.ocr_mapping import process_ocr_mapping_result

_MODULE = "documentai_api.processors.ocr_mapping"


@pytest.fixture
def msg():
    return OcrMappingMessage(
        ddb_key="doc.json",
        document_type="w2",
        ocr_blocks_uri="s3://bucket/ocr-mapping/ocr/doc.json",
        tenant_id="test-tenant-id",
        batch_id="test-batch-id",
    )


def test_process_ocr_mapping_result_returns_processor_result(msg, mocker):
    extraction = ExtractionResult(document_type="w2", body=b"{}")
    mocker.patch(f"{_MODULE}.read_json_from_s3", return_value=[])
    mocker.patch(f"{_MODULE}.run_ocr_mapping_extraction", return_value=extraction)
    mocker.patch(
        f"{_MODULE}.write_extraction_output",
        return_value="s3://bucket/processed/test-tenant-id/doc.json/ocr-mapping/result.json",
    )

    result = process_ocr_mapping_result(msg)

    assert isinstance(result, ProcessorResult)
    assert result.object_key == "doc.json"
    assert result.tenant_id == "test-tenant-id"
    assert result.batch_id == "test-batch-id"
    assert result.extraction_result is extraction
    assert (
        result.output_uri == "s3://bucket/processed/test-tenant-id/doc.json/ocr-mapping/result.json"
    )


def test_process_ocr_mapping_result_raises_without_tenant_id(mocker):
    from documentai_api.processors.ocr_mapping import process_ocr_mapping_result

    msg_no_tenant = OcrMappingMessage(
        ddb_key="doc.json",
        document_type="w2",
        ocr_blocks_uri="s3://bucket/ocr-mapping/ocr/doc.json",
        tenant_id=None,
        batch_id=None,
    )

    with pytest.raises(ValueError, match="tenant_id is required"):
        process_ocr_mapping_result(msg_no_tenant)
