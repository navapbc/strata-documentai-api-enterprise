"""Terminal classification state transitions for processed documents."""

from typing import Any

from documentai_api.config.constants import ProcessStatus
from documentai_api.dtos.classification import ClassificationData
from documentai_api.dtos.ddb import UpdateDdbRecord
from documentai_api.dtos.processing import InternalApiResponse
from documentai_api.utils.ddb import update_ddb
from documentai_api.utils.response_builder import get_internal_api_response
from documentai_api.utils.response_codes import ResponseCodes


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
) -> dict[str, Any]:
    """Mark file processing as completed."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=response_code,
        matched_document_class=data.matched_document_class,
    )

    update_ddb(
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
        )
    )

    # convert dataclass to dict for JSON serialization
    return internal_api_response.__dict__


def classify_as_failed(
    object_key: str,
    error_message: str,
    data: ClassificationData,
    result_processor_started_at: str | None = None,
) -> dict[str, Any]:
    """Mark file processing as failed with error message."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.INTERNAL_PROCESSING_ERROR,
        matched_document_class=None,
    )

    update_ddb(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.FAILED,
            internal_api_response=internal_api_response,
            error_message=error_message,
            data=data,
            result_processor_started_at=result_processor_started_at,
        )
    )

    # convert dataclass to dict for JSON serialization
    return internal_api_response.__dict__


def classify_as_not_implemented(object_key: str, data: ClassificationData) -> dict[str, Any]:
    """Mark file processing as not implemented."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.NO_BLUEPRINT_MATCHED,
        matched_document_class=None,
    )

    update_ddb(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.SUCCESS,
            internal_api_response=internal_api_response,
            data=data,
        )
    )

    # convert dataclass to dict for JSON serialization
    return internal_api_response.__dict__


def classify_as_no_document_detected(
    object_key: str, data: ClassificationData, result_processor_started_at: str | None = None
) -> dict[str, Any]:
    """Mark file processing as no document detected."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.NO_DOCUMENT_DETECTED,
        matched_document_class=None,
    )

    update_ddb(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.NO_DOCUMENT_DETECTED,
            internal_api_response=internal_api_response,
            data=data,
            result_processor_started_at=result_processor_started_at,
        )
    )

    # convert dataclass to dict for JSON serialization
    return internal_api_response.__dict__


def classify_as_ai_consent_declined(object_key: str) -> dict[str, Any]:
    """Mark file as not processed due to AI consent not provided."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.AI_CONSENT_DECLINED,
        matched_document_class=None,
    )

    update_ddb(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.AI_CONSENT_DECLINED,
            internal_api_response=internal_api_response,
        )
    )

    return internal_api_response.__dict__


def classify_as_conversion_failed(object_key: str, error_message: str) -> dict[str, Any]:
    """Mark file as failed due to image format conversion error."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.INTERNAL_PROCESSING_ERROR,
        matched_document_class=None,
    )

    update_ddb(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.CONVERSION_FAILED,
            internal_api_response=internal_api_response,
            error_message=error_message,
        )
    )

    return internal_api_response.__dict__


def classify_as_no_custom_blueprint_matched(
    object_key: str,
    data: ClassificationData,
    result_processor_started_at: str | None = None,
) -> dict[str, Any]:
    """Mark file as sent to BDA with no matching blueprint (005)."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.NO_BLUEPRINT_MATCHED,
        matched_document_class=None,
    )

    update_ddb(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.NO_CUSTOM_BLUEPRINT_MATCHED,
            internal_api_response=internal_api_response,
            data=data,
            result_processor_started_at=result_processor_started_at,
        )
    )

    return internal_api_response.__dict__


def classify_as_extraction_not_configured(
    object_key: str,
    data: ClassificationData,
) -> dict[str, Any]:
    """Mark file as excluded because preclassification returned no known document class (002)."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.SKIPPED_PER_PRECLASSIFICATION,
        matched_document_class=None,
    )

    update_ddb(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.EXCLUDED_PER_PRECLASSIFICATION,
            internal_api_response=internal_api_response,
            data=data,
        )
    )

    return internal_api_response.__dict__


def classify_as_multiple_documents_on_page(
    object_key: str, data: ClassificationData
) -> dict[str, Any]:
    """Mark file processing as multiple documents detected on single page."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
        matched_document_class=None,
    )

    update_ddb(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
            internal_api_response=internal_api_response,
            data=data,
        )
    )

    # convert dataclass to dict for JSON serialization
    return internal_api_response.__dict__


def classify_as_multiple_documents_in_multipage(
    object_key: str, data: ClassificationData
) -> dict[str, Any]:
    """Mark file processing as multiple distinct document types detected across pages."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
        matched_document_class=None,
    )

    update_ddb(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
            internal_api_response=internal_api_response,
            data=data,
        )
    )

    return internal_api_response.__dict__
