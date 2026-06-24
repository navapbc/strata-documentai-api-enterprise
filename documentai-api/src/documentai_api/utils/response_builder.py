"""Utility to build standardized API responses for document processing results."""

import json
from typing import Any

from fastapi import Response

from documentai_api.config.constants import (
    DocumentCategory,
    ProcessStatus,
)
from documentai_api.logging import get_logger
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.services.bda import get_bda_result_json
from documentai_api.utils.bda import extract_field_values_from_bda_results
from documentai_api.utils.dto import ClassificationData, InternalApiResponse
from documentai_api.utils.field_labels import get_field_label
from documentai_api.utils.response_codes import ResponseCodes

logger = get_logger(__name__)


# TODO: Refactor to improve testability - consider making public along with
# restructuring to reduce mocking in tests
def _extract_field_values(
    ddb_record: dict[str, Any],
    include_extracted_data: bool,
    include_bounding_box: bool = False,
    *,
    document_type: str | None = None,
) -> dict[str, Any]:
    """Extract field data for API response."""
    if not ddb_record:
        return {}

    # get confidence scores and extracted values if requested
    if include_extracted_data:
        s3_uri = ddb_record.get(DocumentMetadata.BDA_OUTPUT_S3_URI)

        if not s3_uri:
            return {}

        bda_results = get_bda_result_json(s3_uri)

        if not bda_results:
            return {}

        metadata, field_values, field_geometry = extract_field_values_from_bda_results(
            bda_results, include_geometry=include_bounding_box
        )
        field_confidence_map_list = metadata.field_confidence_map_list
    else:
        field_confidence_map_list = json.loads(
            ddb_record.get(DocumentMetadata.FIELD_CONFIDENCE_SCORES, "[]")
        )
        field_values = {}
        field_geometry = {}

    # Flat map keyed by verbatim blueprint names - matches FIELD_CONFIDENCE_SCORES
    # and extraction rules. Nesting is deferred to present_v1_response.
    fields: dict[str, Any] = {}
    for field_item in field_confidence_map_list:
        for field_name, confidence in field_item.items():
            entry: dict[str, Any] = {
                "confidence": round(confidence, 2),
                "value": field_values.get(field_name) if include_extracted_data else "<redacted>",
                "displayName": get_field_label(document_type, field_name),
            }
            if include_bounding_box and field_name in field_geometry:
                geo_data = field_geometry[field_name]
                entry["geometry"] = geo_data["geometry"]
                if geo_data.get("type"):
                    entry["fieldType"] = geo_data["type"]

            fields[field_name] = entry

    return fields


def nest_fields(flat_fields: dict[str, Any]) -> dict[str, Any]:
    """Split dot-separated field names into a nested dict."""
    nested: dict[str, Any] = {}
    for field_name, entry in flat_fields.items():
        parts = field_name.split(".")
        target = nested
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = entry
    return nested


def present_v1_response(v1_response: dict[str, Any]) -> dict[str, Any]:
    """Nest the 'fields' block for client presentation."""
    fields = v1_response.get("fields")
    if isinstance(fields, dict):
        return {**v1_response, "fields": nest_fields(fields)}
    return v1_response


def get_internal_api_response(
    object_key: str,
    response_code: str,
    matched_document_class: str | None,
    user_provided_document_category: str | None = None,
) -> InternalApiResponse:
    """Get API response object for internal use.

    Args:
        object_key: S3 file key
        response_code: Processing result code
        document_type: Detected document type
        user_provided_document_category: Document category provided by user at upload time
    Returns:
        InternalApiResponse: Response object for API endpoints
    """
    # import here to avoid circular dependency
    if not user_provided_document_category:
        from documentai_api.utils.ddb import get_user_provided_document_category

        user_provided_document_category = get_user_provided_document_category(object_key)

    return InternalApiResponse(
        validation_passed=ResponseCodes.is_success_response_code(response_code),
        document_category=DocumentCategory(user_provided_document_category)
        if user_provided_document_category
        else None,
        matched_document_class=matched_document_class,
        response_code=response_code,
        response_message=ResponseCodes.get_message(response_code),
    )


def build_v1_api_response(
    object_key: str,
    job_status: str,
    data: ClassificationData | None = None,
    error_message: str | None = None,
    include_extracted_data: bool = False,
    include_bounding_box: bool = False,
) -> dict[str, Any]:
    """Build API response dict for DDB storage."""
    job_status = job_status.value if isinstance(job_status, ProcessStatus) else job_status
    from documentai_api.utils.ddb import get_ddb_record

    ddb_record = get_ddb_record(object_key)
    if ddb_record is None:
        raise ValueError(f"DDB record not found for file: {object_key}")

    job_id = ddb_record.get(DocumentMetadata.JOB_ID)
    matched_document_class = ddb_record.get(DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS)
    total_time = ddb_record.get(DocumentMetadata.TOTAL_PROCESSING_TIME_SECONDS)
    created_at = ddb_record.get(DocumentMetadata.CREATED_AT)
    completed_at = ddb_record.get(DocumentMetadata.BDA_COMPLETED_AT)

    base_response = {"jobId": job_id, "jobStatus": job_status, "createdAt": created_at}

    if completed_at:
        base_response["completedAt"] = completed_at

    if total_time:
        base_response["totalProcessingTimeSeconds"] = float(total_time)

    if matched_document_class:
        base_response["matchedDocumentClass"] = matched_document_class

    # success response with full results
    if ProcessStatus.is_successful(job_status):
        base_response["jobStatus"] = "completed"

        if job_status == ProcessStatus.SUCCESS.value:
            base_response["message"] = "Document processed successfully"

            fields = _extract_field_values(
                ddb_record, include_extracted_data, include_bounding_box,
                document_type=matched_document_class,
            )

            tenant_id = ddb_record.get("tenantId")
            document_type = ddb_record.get(DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS)

            if tenant_id and document_type and fields:
                try:
                    from documentai_api.utils.extraction_rules import apply_extraction_rules

                    rule_result = apply_extraction_rules(tenant_id, document_type, fields)
                    fields = rule_result.fields

                    if rule_result.missing_required_field_list:
                        base_response["missingRequiredFieldList"] = (
                            rule_result.missing_required_field_list
                        )
                        base_response["responseCode"] = ResponseCodes.MISSING_FIELDS
                        base_response["responseMessage"] = ResponseCodes.get_message(
                            ResponseCodes.MISSING_FIELDS
                        )
                except Exception as e:
                    logger.warning(f"Failed to apply extraction rules for {document_type}: {e}")

            base_response["fields"] = fields

            # Surface the confidence floor flag, but let missing required fields
            # take precedence over low confidence as the reported response code.
            if ddb_record.get(DocumentMetadata.BELOW_EXTRACTION_CONFIDENCE_FLOOR):
                base_response["belowExtractionConfidenceFloor"] = True
                if base_response.get("responseCode") != ResponseCodes.MISSING_FIELDS:
                    base_response["responseCode"] = ResponseCodes.LOW_EXTRACTION_CONFIDENCE
                    base_response["responseMessage"] = ResponseCodes.get_message(
                        ResponseCodes.LOW_EXTRACTION_CONFIDENCE
                    )

        elif job_status == ProcessStatus.NO_CUSTOM_BLUEPRINT_MATCHED.value:
            base_response["message"] = "Document processed but no matching template found"
            base_response["fields"] = {}

    # error responses
    elif job_status == ProcessStatus.FAILED.value:
        base_response.update(
            {
                "jobStatus": "failed",
                "error": error_message or "Processing failed",
                "additionalInfo": data.additional_info if data else None,
            }
        )

    elif job_status == ProcessStatus.NO_DOCUMENT_DETECTED.value:
        base_response.update(
            {
                "jobStatus": "not_supported",
                "message": "Unable to extract meaningful document content",
                "additionalInfo": data.additional_info if data else None,
            }
        )

    elif job_status == ProcessStatus.AI_CONSENT_DECLINED.value:
        base_response.update(
            {
                "jobStatus": "ai_consent_declined",
                "message": "Document not processed - AI consent not provided",
            }
        )

    elif job_status == ProcessStatus.DELETED.value:
        base_response.update(
            {
                "jobStatus": "deleted",
                "message": "Document has been deleted",
            }
        )

    elif job_status == ProcessStatus.CONVERSION_FAILED.value:
        base_response.update(
            {
                "jobStatus": "conversion_failed",
                "message": "Image format conversion failed",
            }
        )

    elif ProcessStatus.is_not_supported(job_status):
        base_response.update(
            {
                "jobStatus": "not_supported",
                "message": "Document type not supported",
                "additionalInfo": data.additional_info if data else None,
            }
        )

    else:
        base_response.update(
            {"jobStatus": "processing", "message": "Document processing in progress"}
        )

    # Remove None values for cleaner response
    return {k: v for k, v in base_response.items() if v is not None}


def build_flat_file(field_names: list[str], data: list[dict[str, Any]], delim: str = ",") -> str:
    def escape_value(s: str) -> str:
        if s is None:
            return '""'

        escaped = s.replace('"', '""')
        return f'"{escaped}"'

    header = delim.join(escape_value(name) for name in field_names)

    rows = [delim.join(escape_value(row.get(col, "")) for col in field_names) for row in data]

    return "\r\n".join([header, *rows])


def build_csv_response(data: list[dict[str, Any]]) -> Response:
    """Build CSV response from list of dicts."""
    field_names = list(dict.fromkeys(k for row in data for k in row)) if data else []
    return Response(content=build_flat_file(field_names, data), media_type="text/csv")


__all__ = [
    "build_csv_response",
    "build_flat_file",
    "build_v1_api_response",
    "get_internal_api_response",
    "nest_fields",
    "present_v1_response",
]
