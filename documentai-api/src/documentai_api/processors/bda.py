"""BDA processor: tracing, DDB lookup, and classification dispatch."""

from typing import Any

from opentelemetry import trace
from opentelemetry.propagate import extract as otel_extract

from documentai_api.logging import get_logger
from documentai_api.schemas.document_metadata import DocumentMetadata

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)


def process_bda_result(
    bda_output_bucket_name: str,
    bda_output_object_key: str,
    result_processor_started_at: str | None = None,
) -> dict[str, Any]:
    """Handle BDA S3 completion event. Returns the internal API response dict."""
    from documentai_api.services.bda import extract_bda_output_s3_uri
    from documentai_api.utils.bda import get_ddb_record_from_bda_output

    bda_output_s3_uri = extract_bda_output_s3_uri(bda_output_bucket_name, bda_output_object_key)
    if not bda_output_s3_uri:
        raise ValueError("No BDA output S3 URI found")

    ddb_record = get_ddb_record_from_bda_output(bda_output_bucket_name, bda_output_object_key)
    if not ddb_record:
        raise ValueError(f"No DDB record found for BDA output: {bda_output_s3_uri}")

    carrier = {"traceparent": ddb_record.get(DocumentMetadata.TRACEPARENT, "")}
    ctx = otel_extract(carrier)

    with tracer.start_as_current_span("bda.result_process", context=ctx) as span:
        span.set_attribute("document.key", ddb_record.get(DocumentMetadata.FILE_NAME, ""))
        return _process_bda_result(bda_output_s3_uri, ddb_record, result_processor_started_at)


def _process_bda_result(
    bda_output_s3_uri: str,
    ddb_record: dict[str, Any],
    result_processor_started_at: str | None,
) -> dict[str, Any]:
    from documentai_api.config.constants import BdaResponseFields, ConfigDefaults
    from documentai_api.dtos.classification import ClassificationData
    from documentai_api.extractors.bda import extract_bda_result
    from documentai_api.services.bda import get_bda_result_json
    from documentai_api.utils.bda import get_matched_blueprint, get_text_from_standard_blueprint
    from documentai_api.utils.document_classification import (
        classify_as_no_custom_blueprint_matched,
        classify_as_no_document_detected,
        classify_extraction_result,
    )

    file_name: str = ddb_record[DocumentMetadata.FILE_NAME]
    batch_id: str | None = ddb_record.get(DocumentMetadata.BATCH_ID)
    tenant_id: str | None = ddb_record.get(DocumentMetadata.TENANT_ID)

    bda_result_json = get_bda_result_json(bda_output_s3_uri)
    if not bda_result_json:
        raise ValueError("No BDA result JSON found")

    matched_blueprint = get_matched_blueprint(bda_result_json)
    document_class = bda_result_json.get(BdaResponseFields.DOCUMENT_CLASS, {}).get(
        BdaResponseFields.DOCUMENT_TYPE
    )

    result = extract_bda_result(bda_result_json, bda_output_s3_uri)

    if result is not None:
        logger.info("Custom matching blueprint found, and document type matches. Success.")
        return classify_extraction_result(
            ddb_key=file_name,
            result=result,
            tenant_id=tenant_id,
            batch_id=batch_id,
            result_processor_started_at=result_processor_started_at,
        )

    no_match_data = ClassificationData(
        bda_output_s3_uri=bda_output_s3_uri,
        matched_document_class=document_class,
        matched_blueprint_name=matched_blueprint.name,
        matched_blueprint_confidence=matched_blueprint.confidence,
    )

    text = get_text_from_standard_blueprint(bda_result_json)
    if text and len([c for c in text if c.isalnum()]) > int(
        ConfigDefaults.BDA_DOCUMENT_DETECTION_MIN_CHAR_LENGTH
    ):
        msg = "No matching custom blueprint found. Document detected, but not implemented."
        logger.info(msg)
        return classify_as_no_custom_blueprint_matched(
            object_key=file_name,
            data=ClassificationData(**{**no_match_data.__dict__, "additional_info": msg}),
            result_processor_started_at=result_processor_started_at,
            batch_id=batch_id,
        )

    msg = "No matching custom blueprint found. Unable to extract meaningful document content."
    logger.info(msg)
    return classify_as_no_document_detected(
        object_key=file_name,
        data=ClassificationData(**{**no_match_data.__dict__, "additional_info": msg}),
        result_processor_started_at=result_processor_started_at,
        batch_id=batch_id,
    )
