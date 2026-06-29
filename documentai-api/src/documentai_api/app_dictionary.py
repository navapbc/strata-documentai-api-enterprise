"""Dictionary endpoints (schemas, fields, response codes, document categories)."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from documentai_api.annotations import AuthUserWithFallback, OutputFormat
from documentai_api.config.constants import (
    ApiVisualizationTag,
    DictionaryBlueprintField,
    DictionaryBlueprintSchema,
    OutputFormatType,
)
from documentai_api.logging import get_logger
from documentai_api.models.dictionary import (
    DictionaryDocumentCategoriesResponse,
    DictionaryFieldsResponse,
    DictionaryResponseCodesResponse,
    DictionarySchemaDetailResponse,
    DictionarySchemaListResponse,
    DictionarySearchResponse,
)
from documentai_api.utils.auth import get_user_context_with_fallback
from documentai_api.utils.response_builder import build_csv_response
from documentai_api.utils.schemas import get_all_fields, get_all_schemas, get_document_schema

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(get_user_context_with_fallback)])

_CSV_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {
        "content": {
            "application/json": {},
            "text/csv": {"schema": {"type": "string"}},
        }
    }
}


@router.get(
    "/v1/dictionary/schemas",
    tags=[ApiVisualizationTag.DICTIONARY_SCHEMAS],
)
async def list_schemas(
    user: AuthUserWithFallback,
) -> DictionarySchemaListResponse:
    """List all supported document types."""
    try:
        schemas = get_all_schemas()
    except Exception:
        logger.exception("Failed to retrieve schemas")
        raise HTTPException(
            status_code=503, detail="Unable to retrieve dictionary schemas"
        ) from None
    return DictionarySchemaListResponse(schemas=sorted(schemas.keys()))


@router.get(
    "/v1/dictionary/schemas/{document_type}",
    response_model=None,
    responses=_CSV_RESPONSES,
    tags=[ApiVisualizationTag.DICTIONARY_SCHEMAS],
)
async def get_schema_detail(
    document_type: str,
    user: AuthUserWithFallback,
    output_format: OutputFormat = OutputFormatType.JSON,
) -> DictionarySchemaDetailResponse | Response:
    """Get field schema for a specific document type."""
    try:
        schema = get_document_schema(document_type)
    except Exception:
        logger.exception(f"Failed to retrieve schema for {document_type}")
        raise HTTPException(
            status_code=503, detail="Unable to retrieve dictionary schema detail"
        ) from None

    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema not found: {document_type}")

    data = schema.get(DictionaryBlueprintSchema.FIELDS)
    if data is None:
        logger.error(f"Schema for {document_type} missing 'fields' key")
        raise HTTPException(status_code=500, detail="Schema data is malformed")

    if output_format == OutputFormatType.CSV:
        return build_csv_response(data)

    return DictionarySchemaDetailResponse(
        document_type=document_type,
        fields=data,
        blueprint_arn=schema.get("blueprintArn"),
        category=schema.get("category"),
    )


@router.get(
    "/v1/dictionary/fields",
    response_model=None,
    responses=_CSV_RESPONSES,
    tags=[ApiVisualizationTag.DICTIONARY_FIELDS],
)
async def get_all_schema_fields(
    user: AuthUserWithFallback,
    output_format: OutputFormat = OutputFormatType.JSON,
) -> DictionaryFieldsResponse | Response:
    """Get all fields across all document types."""
    try:
        data = get_all_fields()
    except Exception:
        logger.exception("Failed to retrieve fields")
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve dictionary fields",
        ) from None

    if output_format == OutputFormatType.CSV:
        return build_csv_response(data)

    return DictionaryFieldsResponse(fields=data)


@router.get(
    "/v1/dictionary/search",
    response_model=None,
    responses=_CSV_RESPONSES,
    tags=[ApiVisualizationTag.DICTIONARY_FIELDS],
)
async def search_schema_fields(
    user: AuthUserWithFallback,
    q: str | None = None,
    field: DictionaryBlueprintField | None = None,
    output_format: OutputFormat = OutputFormatType.JSON,
) -> DictionarySearchResponse | Response:
    """Search fields across all blueprints."""
    try:
        data = get_all_fields()
    except Exception:
        logger.exception("Failed to retrieve fields for search")
        raise HTTPException(
            status_code=503,
            detail="Unable to search dictionary fields",
        ) from None

    if q:
        query = q.lower()
        if field:
            data = [f for f in data if query in str(f.get(field, "")).lower()]
        else:
            data = [f for f in data if any(query in str(v).lower() for v in f.values())]

    if output_format == OutputFormatType.CSV:
        return build_csv_response(data)

    return DictionarySearchResponse(fields=data)


@router.get(
    "/v1/dictionary/response-codes",
    response_model=None,
    responses=_CSV_RESPONSES,
    tags=[ApiVisualizationTag.DICTIONARY_REFERENCE],
)
async def get_response_codes(
    user: AuthUserWithFallback,
    output_format: OutputFormat = OutputFormatType.JSON,
) -> DictionaryResponseCodesResponse | Response:
    """Get list of response codes and their meanings."""
    try:
        from documentai_api.utils.response_codes import ResponseCodes

        data = ResponseCodes.get_all()
    except Exception:
        logger.exception("Failed to retrieve response codes")
        raise HTTPException(status_code=503, detail="Unable to retrieve response codes") from None

    if output_format == OutputFormatType.CSV:
        return build_csv_response(data)

    return DictionaryResponseCodesResponse(response_codes=data)


@router.get(
    "/v1/dictionary/document-categories",
    response_model=None,
    responses=_CSV_RESPONSES,
    tags=[ApiVisualizationTag.DICTIONARY_REFERENCE],
)
async def get_document_categories(
    user: AuthUserWithFallback,
    output_format: OutputFormat = OutputFormatType.JSON,
) -> DictionaryDocumentCategoriesResponse | Response:
    """Get list of supported document categories (derived from BDA project config)."""
    import json
    import os

    project_arns_json = os.environ.get("BDA_PROJECT_ARNS")
    if not project_arns_json:
        raise HTTPException(status_code=503, detail="BDA_PROJECT_ARNS not configured")

    categories = sorted(json.loads(project_arns_json).keys())
    data = [{"category": c} for c in categories]

    if output_format == OutputFormatType.CSV:
        return build_csv_response(data)

    return DictionaryDocumentCategoriesResponse(document_categories=categories)
