from dataclasses import dataclass, field
from typing import Any

from opentelemetry import trace
from opentelemetry.propagate import extract

from documentai_api.config.constants import BdaResponseFields, ConfigDefaults
from documentai_api.dtos.classification import ClassificationData
from documentai_api.logging import get_logger
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.services.bda import extract_bda_output_s3_uri, get_bda_result_json
from documentai_api.utils.bda import (
    BdaFieldProcessingData,
    calculate_average_non_empty_confidence,
    extract_field_metadata_from_bda_results,
    extract_field_values_from_bda_results,
    get_ddb_record_from_bda_output,
    get_text_from_standard_blueprint,
)
from documentai_api.utils.document_classification import (
    classify_as_no_custom_blueprint_matched,
    classify_as_no_document_detected,
    classify_as_success,
)
from documentai_api.utils.extraction_rules import (
    apply_extraction_rules,
    get_missing_required_fields,
)
from documentai_api.utils.response_codes import ResponseCodes
from documentai_api.utils.tenants import (
    get_extraction_confidence_floor,
    tenant_has_confidence_floor,
)

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class MatchedBlueprintInfo:
    """Timing data calculated during BDA processing completion."""

    name: str
    confidence: float | None


@dataclass
class BdaProcessingResults:
    """Data elements derrived from BDA output."""

    empty_field_list: list[str] = field(default_factory=list)
    fields_missing_geometry: list[str] = field(default_factory=list)
    field_confidence_map_list: list[dict[str, float]] = field(default_factory=list)
    response_code: str | None = None


@dataclass
class BdaExtractionResult:
    """Parsed BDA output — blueprint match, field values, and applied rules."""

    matched_blueprint: MatchedBlueprintInfo
    document_type: str | None
    field_values: dict[str, Any]
    field_confidences: dict[str, float]
    filtered_fields: dict[str, Any]
    missing_required: list[str]
    has_rules: bool


def get_bda_processing_results(bda_result_json: dict[str, Any]) -> BdaProcessingResults:
    """Extract field processing results from BDA output."""
    if BdaResponseFields.EXPLAINABILITY_INFO not in bda_result_json:
        return BdaProcessingResults(response_code=ResponseCodes.INTERNAL_PROCESSING_ERROR)

    field_data = extract_field_metadata_from_bda_results(bda_result_json)
    response_code = _determine_response_code(field_data)

    return BdaProcessingResults(
        field_confidence_map_list=field_data.field_confidence_map_list,
        empty_field_list=field_data.empty_fields,
        fields_missing_geometry=field_data.fields_missing_geometry or [],
        response_code=response_code,
    )


def _determine_response_code(field_data: BdaFieldProcessingData) -> str:
    """Determine response code based on field results."""
    # add logic here if response code should be derived from field data
    # returning success as default
    return ResponseCodes.SUCCESS


def get_matched_blueprint(bda_result_json: dict[str, Any]) -> MatchedBlueprintInfo:
    """Extract matched blueprint name and confidence from BDA result JSON."""
    matched_blueprint = bda_result_json.get(BdaResponseFields.MATCHED_BLUEPRINT, {})
    matched_blueprint_name = matched_blueprint.get(BdaResponseFields.MATCHED_BLUEPRINT_NAME)
    matched_blueprint_confidence = matched_blueprint.get(
        BdaResponseFields.MATCHED_BLUEPRINT_CONFIDENCE
    )

    return MatchedBlueprintInfo(matched_blueprint_name, matched_blueprint_confidence)


def process_bda_output(
    bda_output_bucket_name: str,
    bda_output_object_key: str,
    result_processor_started_at: str | None = None,
) -> dict[str, Any]:
    bda_output_s3_uri = extract_bda_output_s3_uri(bda_output_bucket_name, bda_output_object_key)

    if not bda_output_s3_uri:
        raise ValueError("No BDA output S3 URI found")

    ddb_record = get_ddb_record_from_bda_output(bda_output_bucket_name, bda_output_object_key)
    if not ddb_record:
        raise ValueError(f"No DDB record found for BDA output: {bda_output_s3_uri}")

    # Extract traceparent written by document-processor to restore the parent
    # trace context across the async S3-triggered Lambda boundary.
    carrier = {"traceparent": ddb_record.get(DocumentMetadata.TRACEPARENT, "")}
    ctx = extract(carrier)

    with tracer.start_as_current_span("bda.result_process", context=ctx) as span:
        span.set_attribute("document.key", ddb_record.get(DocumentMetadata.FILE_NAME, ""))
        return _process_bda_output_inner(bda_output_s3_uri, ddb_record, result_processor_started_at)


def extract_bda_result(
    bda_result_json: dict[str, Any],
    tenant_id: str | None,
    document_type: str | None = None,
) -> BdaExtractionResult:
    """Parse BDA result JSON into a structured extraction result."""
    matched_blueprint = get_matched_blueprint(bda_result_json)
    document_class = bda_result_json.get(BdaResponseFields.DOCUMENT_CLASS, {}).get(
        BdaResponseFields.DOCUMENT_TYPE
    )
    effective_doc_type = document_type or document_class or matched_blueprint.name

    _, field_values, _ = extract_field_values_from_bda_results(bda_result_json)
    bda_metadata = get_bda_processing_results(bda_result_json)
    field_confidences: dict[str, float] = {}

    for conf_map in bda_metadata.field_confidence_map_list:
        field_confidences.update(conf_map)

    has_rules = False
    filtered_fields = field_values
    missing_required: list[str] = []

    if effective_doc_type and tenant_id:
        rule_result = apply_extraction_rules(tenant_id, effective_doc_type, field_values)

        if rule_result.fields != field_values:
            has_rules = True
            filtered_fields = rule_result.fields
            missing_required = rule_result.missing_required_field_list

    return BdaExtractionResult(
        matched_blueprint=matched_blueprint,
        document_type=effective_doc_type,
        field_values=field_values,
        field_confidences=field_confidences,
        filtered_fields=filtered_fields,
        missing_required=missing_required,
        has_rules=has_rules,
    )


def _process_bda_output_inner(
    bda_output_s3_uri: str,
    ddb_record: dict[str, Any],
    result_processor_started_at: str | None,
) -> dict[str, Any]:
    file_name: str = ddb_record[DocumentMetadata.FILE_NAME]

    bda_result_json = get_bda_result_json(bda_output_s3_uri)
    if not bda_result_json:
        raise ValueError("No BDA result JSON found")

    matched_blueprint = get_matched_blueprint(bda_result_json)
    document_class = bda_result_json.get(BdaResponseFields.DOCUMENT_CLASS, {}).get(
        BdaResponseFields.DOCUMENT_TYPE
    )

    classification_data = ClassificationData(
        bda_output_s3_uri=bda_output_s3_uri,
        matched_document_class=document_class,
        matched_blueprint_name=matched_blueprint.name,
        matched_blueprint_confidence=matched_blueprint.confidence,
    )

    logger.debug(f"Matched blueprint: {matched_blueprint.name}")

    if matched_blueprint.name is None:
        msg = "No matching custom blueprint found. "
        text = get_text_from_standard_blueprint(bda_result_json)

        if text and len([c for c in text if c.isalnum()]) > int(
            ConfigDefaults.BDA_DOCUMENT_DETECTION_MIN_CHAR_LENGTH
        ):
            msg += "Document detected, but not implemented."
            logger.info(msg)
            classification_data.additional_info = msg
            return classify_as_no_custom_blueprint_matched(
                object_key=file_name,
                data=classification_data,
                result_processor_started_at=result_processor_started_at,
            )
        else:
            msg += "Unable to extract meaningful document content."
            logger.info(msg)
            classification_data.additional_info = msg
            return classify_as_no_document_detected(
                object_key=file_name,
                data=classification_data,
                result_processor_started_at=result_processor_started_at,
            )

    msg = "Custom matching blueprint found, and document type matches. Success."
    logger.info(msg)
    results = get_bda_processing_results(bda_result_json)

    classification_data.field_confidence_scores = results.field_confidence_map_list
    classification_data.field_empty_list = results.empty_field_list
    classification_data.field_missing_geometry_list = results.fields_missing_geometry
    classification_data.additional_info = msg

    tenant_id = ddb_record.get(DocumentMetadata.TENANT_ID)
    response_code = results.response_code or ResponseCodes.SUCCESS
    confidence_floor = get_extraction_confidence_floor(tenant_id)
    used_default_floor = not tenant_has_confidence_floor(tenant_id)
    below_floor = _is_below_extraction_confidence_floor(results, confidence_floor)
    rule_fields = get_missing_required_fields(
        tenant_id, document_class, results.empty_field_list, results.fields_missing_geometry
    )
    missing_required_field_list, required_field_list = rule_fields or (None, None)

    return classify_as_success(
        object_key=file_name,
        response_code=response_code,
        data=classification_data,
        below_extraction_confidence_floor=below_floor,
        extraction_rules_configured=rule_fields is not None,
        missing_required_field_list=missing_required_field_list,
        required_field_list=required_field_list,
        applied_extraction_confidence_floor=confidence_floor,
        used_default_confidence_floor=used_default_floor,
        result_processor_started_at=result_processor_started_at,
    )


def _is_below_extraction_confidence_floor(
    results: BdaProcessingResults,
    confidence_floor: float,
) -> bool:
    """Check if average non-empty field confidence is below the tenant's floor."""
    avg_confidence = calculate_average_non_empty_confidence(
        results.field_confidence_map_list, results.empty_field_list, results.fields_missing_geometry
    )
    if avg_confidence is None:
        return False

    return avg_confidence < confidence_floor


__all__ = ["extract_bda_result", "process_bda_output"]
