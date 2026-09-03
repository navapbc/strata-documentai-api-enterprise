"""Terminal classification state transitions for processed documents."""

from typing import Any

from botocore.exceptions import ClientError

from documentai_api.config.constants import ProcessStatus
from documentai_api.dtos.classification import ClassificationData
from documentai_api.dtos.ddb import UpdateDdbRecord
from documentai_api.dtos.processing import InternalApiResponse
from documentai_api.logging import get_logger
from documentai_api.utils.batch_operations import increment_resolved_count
from documentai_api.utils.bda import calculate_average_non_empty_confidence
from documentai_api.utils.ddb import update_ddb
from documentai_api.utils.extraction_rules import get_missing_required_fields
from documentai_api.utils.response_builder import get_internal_api_response
from documentai_api.utils.response_codes import ResponseCodes
from documentai_api.utils.tenants import (
    get_extraction_confidence_floor,
    tenant_has_confidence_floor,
)

logger = get_logger(__name__)


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

        if batch_id:
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


def classify_extraction_result(
    ddb_key: str,
    data: ClassificationData,
    tenant_id: str | None,
    batch_id: str | None = None,
    response_code: str = ResponseCodes.SUCCESS,
    result_processor_started_at: str | None = None,
) -> dict[str, Any]:
    """Apply confidence floor and extraction rules, then call classify_as_success."""
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
        response_code=response_code,
        data=data,
        below_extraction_confidence_floor=below_floor,
        extraction_rules_configured=rule_fields is not None,
        missing_required_field_list=missing_required_field_list,
        required_field_list=required_field_list,
        applied_extraction_confidence_floor=confidence_floor,
        used_default_confidence_floor=used_default_floor,
        result_processor_started_at=result_processor_started_at,
        batch_id=batch_id,
    )
