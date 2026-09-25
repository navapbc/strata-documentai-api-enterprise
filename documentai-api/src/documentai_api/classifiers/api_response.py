"""Build the v1 API response dict from a DDB record and extraction results."""

import json
from typing import Any

from documentai_api.config.constants import ProcessStatus
from documentai_api.dtos.classification import ClassificationData
from documentai_api.logging import get_logger
from documentai_api.readers.extraction import read_output
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.ddb import _execute_ddb_update, get_ddb_record
from documentai_api.utils.field_labels import get_field_label
from documentai_api.utils.response_codes import ResponseCodes

logger = get_logger(__name__)

_TERMINAL_STATUS_RESPONSES: dict[str, dict[str, Any]] = {
    ProcessStatus.NO_CUSTOM_BLUEPRINT_MATCHED.value: {
        "jobStatus": "completed",
        "message": "No matching blueprint found",
        "fields": {},
        "responseCode": ResponseCodes.NO_BLUEPRINT_MATCHED,
        "responseMessage": ResponseCodes.get_message(ResponseCodes.NO_BLUEPRINT_MATCHED),
    },
    ProcessStatus.FAILED.value: {
        "jobStatus": "failed",
        "message": "Processing failed",
        "error": "Processing failed",
        "responseCode": ResponseCodes.INTERNAL_PROCESSING_ERROR,
        "responseMessage": ResponseCodes.get_message(ResponseCodes.INTERNAL_PROCESSING_ERROR),
    },
    ProcessStatus.NO_DOCUMENT_DETECTED.value: {
        "jobStatus": "completed",
        "message": "Unable to extract meaningful document content",
        "responseCode": ResponseCodes.NO_DOCUMENT_DETECTED,
        "responseMessage": ResponseCodes.get_message(ResponseCodes.NO_DOCUMENT_DETECTED),
    },
    ProcessStatus.BLURRY_DOCUMENT_DETECTED.value: {
        "jobStatus": "completed",
        "message": "Document is blurry",
        "responseCode": ResponseCodes.BLURRY_DOCUMENT_DETECTED,
        "responseMessage": ResponseCodes.get_message(ResponseCodes.BLURRY_DOCUMENT_DETECTED),
    },
    ProcessStatus.AI_CONSENT_DECLINED.value: {
        "jobStatus": "ai_consent_declined",
        "message": "Document not processed - AI consent not provided",
        "responseCode": ResponseCodes.AI_CONSENT_DECLINED,
        "responseMessage": ResponseCodes.get_message(ResponseCodes.AI_CONSENT_DECLINED),
    },
    ProcessStatus.DELETED.value: {
        "jobStatus": "deleted",
        "message": "Document has been deleted",
    },
    ProcessStatus.CONVERSION_FAILED.value: {
        "jobStatus": "conversion_failed",
        "message": "Image format conversion failed",
        "responseCode": ResponseCodes.INTERNAL_PROCESSING_ERROR,
        "responseMessage": ResponseCodes.get_message(ResponseCodes.INTERNAL_PROCESSING_ERROR),
    },
    ProcessStatus.PASSWORD_PROTECTED.value: {
        "jobStatus": "completed",
        "message": "Document type not supported",
        "responseCode": ResponseCodes.PASSWORD_PROTECTED,
        "responseMessage": ResponseCodes.get_message(ResponseCodes.PASSWORD_PROTECTED),
    },
    ProcessStatus.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE.value: {
        "jobStatus": "completed",
        "message": "Document type not supported",
        "responseCode": ResponseCodes.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
        "responseMessage": ResponseCodes.get_message(
            ResponseCodes.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE
        ),
    },
    ProcessStatus.MULTIPLE_DOCUMENTS_IN_MULTIPAGE.value: {
        "jobStatus": "completed",
        "message": "Document type not supported",
        "responseCode": ResponseCodes.MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
        "responseMessage": ResponseCodes.get_message(ResponseCodes.MULTIPLE_DOCUMENTS_IN_MULTIPAGE),
    },
    ProcessStatus.PROCESSING_EXCLUDED.value: {
        "jobStatus": "completed",
        "message": "Document not chosen for extraction",
        "responseCode": ResponseCodes.PROCESSING_EXCLUDED,
        "responseMessage": ResponseCodes.get_message(ResponseCodes.PROCESSING_EXCLUDED),
    },
}


def _build_field_map(
    field_confidence_map_list: list[dict[str, Any]],
    field_values: dict[str, Any],
    field_geometry: dict[str, Any],
    include_extracted_data: bool,
    include_bounding_box: bool = False,
    *,
    document_type: str | None = None,
) -> dict[str, Any]:
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


def extract_field_values(
    ddb_record: dict[str, Any],
    include_extracted_data: bool,
    include_bounding_box: bool = False,
    *,
    document_type: str | None = None,
) -> dict[str, Any]:
    """Extract field data for API response."""
    if not ddb_record:
        return {}

    result = read_output(ddb_record, include_extracted_data, include_bounding_box)

    return _build_field_map(
        result.field_confidence_map_list,
        result.field_values,
        result.field_geometry,
        include_extracted_data,
        include_bounding_box,
        document_type=document_type,
    )


def _apply_extraction_rules(
    ddb_record: dict[str, Any],
    fields: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    tenant_id = ddb_record.get("tenantId")
    document_type = ddb_record.get(DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS)
    if not tenant_id or not document_type or not fields:
        return fields, []
    try:
        from documentai_api.utils.extraction_rules import apply_extraction_rules
        from documentai_api.utils.ssm import is_missing_geo_included_with_missing_fields

        missing_fields: list[str] = []
        if is_missing_geo_included_with_missing_fields():
            for key in (
                DocumentMetadata.BDA_MATCHED_BLUEPRINT_FIELD_MISSING_GEOMETRY_LIST,
                DocumentMetadata.BDA_MATCHED_BLUEPRINT_FIELD_EMPTY_LIST,
            ):
                raw = ddb_record.get(key)
                if raw:
                    missing_fields.extend(json.loads(raw) if isinstance(raw, str) else raw)

        rule_result = apply_extraction_rules(
            tenant_id, document_type, fields, missing_fields=missing_fields or None
        )
        return rule_result.fields, rule_result.missing_required_field_list or []
    except Exception as e:
        logger.warning(f"Failed to apply extraction rules for {document_type}: {e}")
        return fields, []


def _resolve_response_code(
    job_status: str,
    ddb_record: dict[str, Any],
    missing_required: list[str] | None = None,
) -> tuple[str | None, bool]:
    category_match = ddb_record.get(DocumentMetadata.PRECLASSIFICATION_CATEGORY_MATCH)

    if job_status == ProcessStatus.SUCCESS.value:
        below_floor = bool(ddb_record.get(DocumentMetadata.BELOW_EXTRACTION_CONFIDENCE_FLOOR))

        if missing_required:
            return ResponseCodes.MISSING_FIELDS, below_floor

        if category_match is False:
            return ResponseCodes.MISCATEGORIZED, below_floor

        if below_floor:
            return ResponseCodes.LOW_EXTRACTION_CONFIDENCE, below_floor

        return ResponseCodes.SUCCESS, below_floor

    if job_status == ProcessStatus.NO_CUSTOM_BLUEPRINT_MATCHED.value and category_match is False:
        return ResponseCodes.MISCATEGORIZED, False

    if terminal := _TERMINAL_STATUS_RESPONSES.get(job_status):
        return terminal.get("responseCode"), False

    return None, False


def finalize_v1_response(
    object_key: str,
    status: str,
    data: ClassificationData | None = None,
    error_message: str | None = None,
) -> None:
    """Build and persist the v1 API response and sync responseCode.

    Single authority for v1 response finalization - called after update_ddb
    (extraction completion) and upsert_ddb (terminal pre-extraction statuses).
    Does NOT enqueue metrics; callers own that policy.
    """
    v1_response = build_v1_api_response(object_key, status, data, error_message=error_message)

    update_expr = f"SET {DocumentMetadata.V1_API_RESPONSE_JSON} = :v1ResponseJson"
    expr_values: dict[str, Any] = {":v1ResponseJson": json.dumps(v1_response)}
    if "responseCode" in v1_response:
        update_expr += f", {DocumentMetadata.RESPONSE_CODE} = :responseCode"
        expr_values[":responseCode"] = v1_response["responseCode"]
    _execute_ddb_update(object_key, update_expr, expr_values)


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

    ddb_record = get_ddb_record(object_key)
    if ddb_record is None:
        raise ValueError(f"DDB record not found for file: {object_key}")

    job_id = ddb_record.get(DocumentMetadata.JOB_ID)
    matched_document_class = ddb_record.get(DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS)
    total_time = ddb_record.get(DocumentMetadata.TOTAL_PROCESSING_TIME_SECONDS)
    created_at = ddb_record.get(DocumentMetadata.CREATED_AT)
    completed_at = ddb_record.get(DocumentMetadata.EXTRACTION_COMPLETED_AT) or ddb_record.get(
        DocumentMetadata.BDA_COMPLETED_AT
    )

    base_response = {"jobId": job_id, "jobStatus": job_status, "createdAt": created_at}

    if completed_at:
        base_response["completedAt"] = completed_at

    if total_time:
        base_response["totalProcessingTimeSeconds"] = float(total_time)

    if matched_document_class:
        base_response["matchedDocumentClass"] = matched_document_class

    user_category = ddb_record.get(DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY)

    if user_category:
        base_response["userProvidedDocumentCategory"] = user_category

    if job_status == ProcessStatus.SUCCESS.value:
        fields = extract_field_values(
            ddb_record,
            include_extracted_data,
            include_bounding_box,
            document_type=matched_document_class,
        )

        fields, missing_required = _apply_extraction_rules(ddb_record, fields)
        base_response["fields"] = fields

        if missing_required:
            base_response["missingRequiredFieldList"] = missing_required

        response_code, below_floor = _resolve_response_code(
            job_status, ddb_record, missing_required
        )

        if response_code is None:
            raise ValueError("_resolve_response_code returned no code for a SUCCESS job_status")

        base_response["jobStatus"] = "completed"
        base_response["message"] = "Document processed successfully"
        base_response["responseCode"] = response_code
        base_response["responseMessage"] = ResponseCodes.get_message(response_code)
        base_response["inferredDocumentType"] = ddb_record.get(
            DocumentMetadata.PRECLASSIFICATION_CATEGORY
        )

        if below_floor:
            base_response["belowExtractionConfidenceFloor"] = True

    elif terminal := _TERMINAL_STATUS_RESPONSES.get(job_status):
        base_response.update(terminal)

        response_code, _ = _resolve_response_code(job_status, ddb_record)
        if response_code:
            base_response["responseCode"] = response_code
            base_response["responseMessage"] = ResponseCodes.get_message(response_code)

        if data and data.additional_info:
            base_response["additionalInfo"] = data.additional_info

        if job_status == ProcessStatus.FAILED.value and error_message:
            base_response["error"] = error_message

    else:
        base_response.update(
            {"jobStatus": "processing", "message": "Document processing in progress"}
        )

    return {k: v for k, v in base_response.items() if v is not None}


__all__ = [
    "build_v1_api_response",
    "extract_field_values",
    "finalize_v1_response",
]
