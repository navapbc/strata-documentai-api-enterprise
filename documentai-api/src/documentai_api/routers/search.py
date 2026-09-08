"""Admin document search endpoint."""

from typing import Any

from boto3.dynamodb.conditions import Attr
from fastapi import APIRouter, Depends, HTTPException, status

from documentai_api.annotations import AdminClaims, PageLimit, verify_jwt_with_role
from documentai_api.config.constants import ApiVisualizationTag
from documentai_api.logging import get_logger
from documentai_api.models.admin_document import DocumentListItem, DocumentListResponse
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.document_metadata_table import DocumentMetadataTable
from documentai_api.utils.jwt_auth import tenant_scope
from documentai_api.utils.pagination import decode_cursor, encode_cursor

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/admin/search",
    tags=[ApiVisualizationTag.ADMIN_DOCUMENTS],
    dependencies=[Depends(verify_jwt_with_role)],
)

_table = DocumentMetadataTable()


@router.get("/documents")
async def search_documents(
    claims: AdminClaims,
    tenant_id: str | None = None,
    filename: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    user_provided_document_type: str | None = None,
    matched_blueprint_name: str | None = None,
    limit: PageLimit = 50,
    cursor: str | None = None,
) -> DocumentListResponse:
    """Search documents by filename, date range, or document type.

    Super-admins can search any tenant. Tenant-admins are locked to their own.
    All filters are ANDed together.
    """
    scope = tenant_scope(claims)

    if scope is not None:
        if tenant_id and tenant_id != scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant's documents.",
            )
        tenant_id = scope

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required.",
        )

    filter_parts: list[Any] = []

    if filename:
        filter_parts.append(
            Attr(DocumentMetadata.ORIGINAL_FILE_NAME_LOWER).contains(filename.lower())
        )

    if user_provided_document_type:
        filter_parts.append(
            Attr(DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY).eq(user_provided_document_type)
        )

    if matched_blueprint_name:
        filter_parts.append(
            Attr(DocumentMetadata.BDA_MATCHED_BLUEPRINT_NAME).eq(matched_blueprint_name)
        )

    filter_expr = None

    for part in filter_parts:
        filter_expr = part if filter_expr is None else filter_expr & part

    try:
        start_key = decode_cursor(cursor) if cursor else None
        records, last_key = _table.query_by_tenant(
            tenant_id,
            filter_expression=filter_expr,
            date_from=date_from,
            date_to=date_to
            if "T" in (date_to or "")
            else (f"{date_to}T23:59:59.999999+00:00" if date_to else None),
            limit=limit,
            start_key=start_key,
        )

        documents = [
            DocumentListItem(
                job_id=r.get(DocumentMetadata.JOB_ID, ""),
                file_name=r.get(DocumentMetadata.ORIGINAL_FILE_NAME, ""),
                tenant_id=r.get(DocumentMetadata.TENANT_ID, ""),
                api_key_name=r.get(DocumentMetadata.API_KEY_NAME, ""),
                process_status=r.get(DocumentMetadata.PROCESS_STATUS, ""),
                document_category=r.get(DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY, ""),
                matched_blueprint=r.get(DocumentMetadata.BDA_MATCHED_BLUEPRINT_NAME, ""),
                created_at=r.get(DocumentMetadata.CREATED_AT, ""),
                processed_date=r.get(DocumentMetadata.PROCESSED_DATE, ""),
            )
            for r in records
        ]

        return DocumentListResponse(
            documents=documents,
            count=len(documents),
            next_cursor=encode_cursor(last_key) if last_key else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search documents",
        ) from e
