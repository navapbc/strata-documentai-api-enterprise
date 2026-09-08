"""Utility to build standardized API responses for document processing results."""

from typing import Any

from fastapi import Response

from documentai_api.dtos.processing import InternalApiResponse
from documentai_api.logging import get_logger
from documentai_api.utils.response_codes import ResponseCodes

logger = get_logger(__name__)


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
        document_category=user_provided_document_category,
        matched_document_class=matched_document_class,
        response_code=response_code,
        response_message=ResponseCodes.get_message(response_code),
    )


def build_flat_file(field_names: list[str], data: list[dict[str, Any]], delim: str = ",") -> str:
    def escape_value(s: str) -> str:
        if s is None:
            return '""'

        escaped = str(s).replace('"', '""')
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
    "get_internal_api_response",
    "nest_fields",
    "present_v1_response",
]
