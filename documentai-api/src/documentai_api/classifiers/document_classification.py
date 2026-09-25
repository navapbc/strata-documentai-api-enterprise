"""Terminal classification state transitions for processed documents."""

import json
from typing import Any

from botocore.exceptions import ClientError

from documentai_api.classifiers.api_response import build_v1_api_response, finalize_v1_response
from documentai_api.config.constants import ExtractMethod, ProcessStatus
from documentai_api.dtos.classification import ClassificationData
from documentai_api.dtos.ddb import UpdateDdbRecord
from documentai_api.dtos.extraction import ExtractionResult
from documentai_api.dtos.processing import InternalApiResponse
from documentai_api.logging import get_logger
from documentai_api.readers.extraction import read_output
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.batch_operations import increment_resolved_count
from documentai_api.utils.bda import calculate_average_non_empty_confidence
from documentai_api.utils.ddb import _execute_ddb_update, get_ddb_record, update_ddb
from documentai_api.utils.extraction_rules import get_missing_required_fields
from documentai_api.utils.response_builder import get_internal_api_response
from documentai_api.utils.response_codes import ResponseCodes
from documentai_api.utils.tenants import (
    get_extraction_confidence_floor,
    tenant_has_confidence_floor,
)

logger = get_logger(__name__)


def _is_compare(object_key: str) -> bool:
    record = get_ddb_record(object_key)
    return bool(record and record.get(DocumentMetadata.IS_COMPARE))


def _write_terminal_status(record: UpdateDdbRecord, batch_id: str | None) -> None:
    """Write a terminal status to DDB and increment the batch counter if the write landed.

    Conditions the write on the document not already being terminal - if it is,
    ConditionalCheckFailedException is swallowed and the batch counter is not incremented.
    This prevents double-counting from re-raising callers (e.g. invoke_bda + handler
    crash-catch) or Lambda retries classifying the same document twice.
    """
    condition, extra_values = ProcessStatus.build_ddb_non_terminal_condition()

    try:
        update_ddb(record, condition_expression=condition, extra_expression_values=extra_values)
        finalize_v1_response(record.object_key, record.status, record.data, record.error_message)

        if batch_id and not _is_compare(record.object_key):
            increment_resolved_count(batch_id)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.info(
                f"Skipping reclassification of already-terminal record: {record.object_key}"
            )
            return
        raise


def classify_as_success(
    object_key: str,
    response_code: str,
    data: ClassificationData,
    extraction_method: ExtractMethod,
    below_extraction_confidence_floor: bool = False,
    extraction_rules_configured: bool | None = None,
    missing_required_field_list: list[str] | None = None,
    required_field_list: list[str] | None = None,
    applied_extraction_confidence_floor: float | None = None,
    used_default_confidence_floor: bool | None = None,
    result_processor_started_at: str | None = None,
    batch_id: str | None = None,
) -> dict[str, Any]:
    """Mark file processing as completed."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=response_code,
        matched_document_class=data.matched_document_class,
    )

    _write_terminal_status(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.SUCCESS,
            internal_api_response=internal_api_response,
            data=data,
            extraction_method=extraction_method,
            below_extraction_confidence_floor=below_extraction_confidence_floor,
            extraction_rules_configured=extraction_rules_configured,
            missing_required_field_list=missing_required_field_list,
            required_field_list=required_field_list,
            applied_extraction_confidence_floor=applied_extraction_confidence_floor,
            used_default_confidence_floor=used_default_confidence_floor,
            result_processor_started_at=result_processor_started_at,
        ),
        batch_id,
    )
    return internal_api_response.__dict__


def classify_as_failed(
    object_key: str,
    error_message: str,
    data: ClassificationData,
    result_processor_started_at: str | None = None,
    batch_id: str | None = None,
) -> dict[str, Any]:
    """Mark file processing as failed with error message."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.INTERNAL_PROCESSING_ERROR,
        matched_document_class=None,
    )

    _write_terminal_status(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.FAILED,
            internal_api_response=internal_api_response,
            error_message=error_message,
            data=data,
            result_processor_started_at=result_processor_started_at,
        ),
        batch_id,
    )
    return internal_api_response.__dict__


def classify_as_not_implemented(
    object_key: str, data: ClassificationData, batch_id: str | None = None
) -> dict[str, Any]:
    """Mark file processing as not implemented."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.NO_BLUEPRINT_MATCHED,
        matched_document_class=None,
    )

    _write_terminal_status(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.SUCCESS,
            internal_api_response=internal_api_response,
            data=data,
        ),
        batch_id,
    )
    return internal_api_response.__dict__


def classify_as_no_document_detected(
    object_key: str,
    data: ClassificationData,
    result_processor_started_at: str | None = None,
    batch_id: str | None = None,
) -> dict[str, Any]:
    """Mark file processing as no document detected."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.NO_DOCUMENT_DETECTED,
        matched_document_class=None,
    )

    if _is_compare(object_key):
        _write_compare_empty_response(object_key, ProcessStatus.NO_DOCUMENT_DETECTED)

    _write_terminal_status(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.NO_DOCUMENT_DETECTED,
            internal_api_response=internal_api_response,
            data=data,
            result_processor_started_at=result_processor_started_at,
        ),
        batch_id,
    )
    return internal_api_response.__dict__


def classify_as_ai_consent_declined(object_key: str, batch_id: str | None = None) -> dict[str, Any]:
    """Mark file as not processed due to AI consent not provided."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.AI_CONSENT_DECLINED,
        matched_document_class=None,
    )

    _write_terminal_status(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.AI_CONSENT_DECLINED,
            internal_api_response=internal_api_response,
        ),
        batch_id,
    )
    return internal_api_response.__dict__


def classify_as_conversion_failed(
    object_key: str, error_message: str, batch_id: str | None = None
) -> dict[str, Any]:
    """Mark file as failed due to image format conversion error."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.INTERNAL_PROCESSING_ERROR,
        matched_document_class=None,
    )

    _write_terminal_status(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.CONVERSION_FAILED,
            internal_api_response=internal_api_response,
            error_message=error_message,
        ),
        batch_id,
    )
    return internal_api_response.__dict__


def classify_as_no_custom_blueprint_matched(
    object_key: str,
    data: ClassificationData,
    result_processor_started_at: str | None = None,
    batch_id: str | None = None,
) -> dict[str, Any]:
    """Mark file as sent to BDA with no matching blueprint (005)."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.NO_BLUEPRINT_MATCHED,
        matched_document_class=None,
    )

    if _is_compare(object_key):
        _write_compare_empty_response(object_key, ProcessStatus.NO_CUSTOM_BLUEPRINT_MATCHED)

    _write_terminal_status(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.NO_CUSTOM_BLUEPRINT_MATCHED,
            internal_api_response=internal_api_response,
            data=data,
            result_processor_started_at=result_processor_started_at,
        ),
        batch_id,
    )
    return internal_api_response.__dict__


def classify_as_extraction_not_configured(
    object_key: str,
    data: ClassificationData,
    batch_id: str | None = None,
) -> dict[str, Any]:
    """Mark file as excluded because preclassification returned no known document class (002)."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.SKIPPED_PER_PRECLASSIFICATION,
        matched_document_class=None,
    )

    _write_terminal_status(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.EXCLUDED_PER_PRECLASSIFICATION,
            internal_api_response=internal_api_response,
            data=data,
        ),
        batch_id,
    )
    return internal_api_response.__dict__


def classify_as_multiple_documents_on_page(
    object_key: str, data: ClassificationData, batch_id: str | None = None
) -> dict[str, Any]:
    """Mark file processing as multiple documents detected on single page."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
        matched_document_class=None,
    )

    _write_terminal_status(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
            internal_api_response=internal_api_response,
            data=data,
        ),
        batch_id,
    )
    return internal_api_response.__dict__


def classify_as_multiple_documents_in_multipage(
    object_key: str, data: ClassificationData, batch_id: str | None = None
) -> dict[str, Any]:
    """Mark file processing as multiple distinct document types detected across pages."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
        matched_document_class=None,
    )

    _write_terminal_status(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
            internal_api_response=internal_api_response,
            data=data,
        ),
        batch_id,
    )
    return internal_api_response.__dict__


def _write_compare_v1_response(
    ddb_key: str,
    ddb_record: dict[str, Any],
    result: ExtractionResult,
    output_uri: str,
    extraction_method: ExtractMethod,
) -> None:
    """Build and store a v1 response for one extraction method into apiResponsesByMethod."""
    reader_result = read_output(
        ddb_record,
        include_extracted_data=True,
        include_bounding_box=True,
        output_uri=output_uri,
        extract_method=extraction_method,
    )

    v1_response = build_v1_api_response(ddb_key, ProcessStatus.SUCCESS)
    v1_response["fields"] = {
        name: {
            "confidence": round(conf, 2),
            "value": reader_result.field_values.get(name),
            **(
                {"geometry": reader_result.field_geometry[name]["geometry"]}
                if name in reader_result.field_geometry
                else {}
            ),
        }
        for field_item in reader_result.field_confidence_map_list
        for name, conf in field_item.items()
    }

    method_key = (
        extraction_method.value
        if isinstance(extraction_method, ExtractMethod)
        else extraction_method
    )

    _execute_ddb_update(
        ddb_key,
        f"SET {DocumentMetadata.API_RESPONSES_BY_METHOD}.#method = :response",
        {":response": json.dumps(v1_response)},
        expression_names={"#method": method_key},
    )

    if result.processing_duration_seconds is not None:
        duration_entry: dict[str, Any] = {
            DocumentMetadata.EXTRACTION_DURATION_SECONDS: result.processing_duration_seconds
        }

        if result.processing_started_at is not None:
            duration_entry[DocumentMetadata.PROCESSING_STARTED_AT] = (
                result.processing_started_at.isoformat()
            )

        if result.processing_completed_at is not None:
            duration_entry[DocumentMetadata.PROCESSING_COMPLETED_AT] = (
                result.processing_completed_at.isoformat()
            )

        _execute_ddb_update(
            ddb_key,
            f"SET {DocumentMetadata.DURATIONS_BY_METHOD}.#method = :durationEntry",
            {":durationEntry": duration_entry},
            expression_names={"#method": method_key},
        )


def _write_compare_empty_response(
    ddb_key: str,
    status: ProcessStatus,
    extraction_method: ExtractMethod = ExtractMethod.BDA,
) -> None:
    """Record an empty (no-fields) v1 response for a non-success outcome under compare mode.

    Lets the compare poll see this method's key populated even when nothing was
    extracted (e.g. BDA found no matching blueprint), instead of waiting forever
    for a "bda"/"llm" key that a success-only write would never produce.
    """
    v1_response = build_v1_api_response(ddb_key, status)
    v1_response["fields"] = {}

    method_key = (
        extraction_method.value
        if isinstance(extraction_method, ExtractMethod)
        else extraction_method
    )

    _execute_ddb_update(
        ddb_key,
        f"SET {DocumentMetadata.API_RESPONSES_BY_METHOD}.#method = :response",
        {":response": json.dumps(v1_response)},
        expression_names={"#method": method_key},
    )


def classify_extraction_result(
    ddb_key: str,
    result: ExtractionResult,
    output_uri: str | None,
    tenant_id: str | None,
    batch_id: str | None = None,
    result_processor_started_at: str | None = None,
    extraction_method: ExtractMethod = ExtractMethod.BDA,
) -> dict[str, Any]:
    """Apply confidence floor and extraction rules, then call classify_as_success."""
    if output_uri is None:
        raise ValueError(f"output_uri missing for {ddb_key} on success path ({extraction_method})")

    ddb_record = get_ddb_record(ddb_key) or {}

    if ddb_record.get(DocumentMetadata.IS_COMPARE):
        _write_compare_v1_response(ddb_key, ddb_record, result, output_uri, extraction_method)

    data = ClassificationData.from_extraction_result(result, output_uri=output_uri)

    confidence_floor = get_extraction_confidence_floor(tenant_id)
    used_default_floor = not tenant_has_confidence_floor(tenant_id)

    avg = calculate_average_non_empty_confidence(
        data.field_confidence_scores or [],
        data.field_empty_list,
        data.field_missing_geometry_list or [],
    )
    below_floor = avg is not None and avg < confidence_floor

    rule_fields = get_missing_required_fields(
        tenant_id,
        data.matched_document_class,
        data.field_empty_list or [],
        data.field_missing_geometry_list or [],
    )
    missing_required_field_list, required_field_list = rule_fields or (None, None)

    return classify_as_success(
        object_key=ddb_key,
        response_code=ResponseCodes.SUCCESS,
        data=data,
        extraction_method=extraction_method,
        below_extraction_confidence_floor=below_floor,
        extraction_rules_configured=rule_fields is not None,
        missing_required_field_list=missing_required_field_list,
        required_field_list=required_field_list,
        applied_extraction_confidence_floor=confidence_floor,
        used_default_confidence_floor=used_default_floor,
        result_processor_started_at=result_processor_started_at,
        batch_id=batch_id,
    )
