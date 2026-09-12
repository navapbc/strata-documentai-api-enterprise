"""BDA pipeline: calls processor, dispatches to classification."""

from typing import Any

from documentai_api.classifiers.document_classification import (
    classify_as_no_custom_blueprint_matched,
    classify_as_no_document_detected,
    classify_extraction_result,
)
from documentai_api.dtos.processing import ProcessorResult
from documentai_api.logging import get_logger
from documentai_api.processors.bda import process_bda_result

logger = get_logger(__name__)


def run_bda_pipeline(
    bda_output_bucket_name: str,
    bda_output_object_key: str,
    result_processor_started_at: str | None = None,
) -> dict[str, Any]:
    """Process BDA output and classify. Returns internal API response dict."""
    result = process_bda_result(
        bda_output_bucket_name,
        bda_output_object_key,
        result_processor_started_at=result_processor_started_at,
    )
    return _classify(result)


def _classify(result: ProcessorResult) -> dict[str, Any]:
    if result.extraction_result is not None:
        return classify_extraction_result(
            ddb_key=result.object_key,
            result=result.extraction_result,
            output_uri=result.output_uri,
            tenant_id=result.tenant_id,
            batch_id=result.batch_id,
            result_processor_started_at=result.result_processor_started_at,
        )

    if result.status is not None and result.classification_data is not None:
        from documentai_api.config.constants import ProcessStatus

        if result.status == ProcessStatus.NO_CUSTOM_BLUEPRINT_MATCHED:
            return classify_as_no_custom_blueprint_matched(
                object_key=result.object_key,
                data=result.classification_data,
                result_processor_started_at=result.result_processor_started_at,
                batch_id=result.batch_id,
            )

        return classify_as_no_document_detected(
            object_key=result.object_key,
            data=result.classification_data,
            result_processor_started_at=result.result_processor_started_at,
            batch_id=result.batch_id,
        )

    raise ValueError(f"ProcessorResult has no extraction_result or status: {result}")
