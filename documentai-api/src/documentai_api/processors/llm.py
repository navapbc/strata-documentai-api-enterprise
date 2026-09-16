"""LLM processor: fetch OCR blocks from S3, run extraction, write output. Returns ProcessorResult."""

from documentai_api.config.constants import ExtractMethod
from documentai_api.dtos.processing import LlmExtractionMessage, ProcessorResult
from documentai_api.extractors.llm import run_llm_extraction
from documentai_api.utils.s3 import read_json_from_s3, write_extraction_output


def process_llm_result(msg: LlmExtractionMessage) -> ProcessorResult:
    """Fetch OCR blocks, run LLM extraction, and write the tenant-scoped output."""
    if not msg.tenant_id:
        raise ValueError(f"tenant_id is required for LLM extraction of {msg.ddb_key}")

    ocr_blocks = list(read_json_from_s3(msg.ocr_blocks_uri))
    result = run_llm_extraction(msg.ddb_key, msg.document_type, ocr_blocks)
    output_uri = write_extraction_output(
        msg.tenant_id,
        ExtractMethod.LLM,
        msg.ddb_key,
        result.body or b"",
        content_type="application/json",
    )
    result.output_uri = output_uri
    return ProcessorResult(
        object_key=msg.ddb_key,
        tenant_id=msg.tenant_id,
        batch_id=msg.batch_id,
        extraction_result=result,
        output_uri=output_uri,
    )
