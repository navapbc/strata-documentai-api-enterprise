"""LLM pipeline: calls processor, dispatches to classification."""

from documentai_api.classifiers.document_classification import classify_extraction_result
from documentai_api.config.constants import ExtractMethod
from documentai_api.dtos.processing import LlmExtractionMessage
from documentai_api.processors.llm import process_llm_result


def run_llm_pipeline(msg: LlmExtractionMessage) -> None:
    """Process an LLM extraction message and classify the result."""
    result = process_llm_result(msg)
    if result.extraction_result is None:
        raise ValueError(f"LLM processor returned no extraction_result for {msg.ddb_key}")
    classify_extraction_result(
        ddb_key=result.object_key,
        result=result.extraction_result,
        output_uri=result.output_uri,
        tenant_id=result.tenant_id,
        batch_id=result.batch_id,
        extraction_method=ExtractMethod.LLM,
    )
