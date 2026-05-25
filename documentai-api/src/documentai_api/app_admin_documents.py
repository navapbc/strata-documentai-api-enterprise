"""Admin documents router — read-only access to processed documents."""

import json
from typing import Any

from boto3.dynamodb.conditions import Attr, Key
from fastapi import APIRouter, Depends, HTTPException, status

from documentai_api.annotations import AdminClaims, PageLimit, verify_jwt_with_role
from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.models.admin_document import (
    DocumentDetail,
    DocumentListItem,
    DocumentListResponse,
)
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.base_readonly_table import ReadOnlyTable
from documentai_api.utils.jwt_auth import tenant_scope
from documentai_api.utils.pagination import decode_cursor, encode_cursor

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/admin/documents",
    tags=["admin-documents"],
    dependencies=[Depends(verify_jwt_with_role)],
)


class _DocumentMetadataTable(ReadOnlyTable):
    table_name_env = "documentai_document_metadata_table_name"
    pk_field = "fileName"

    def _get_index(self, attr: str) -> str:
        name: str | None = getattr(get_aws_config(), attr, None)
        if not name:
            raise ValueError(f"{attr} not configured")
        return name

    def query_by_tenant(
        self,
        tenant_id: str,
        *,
        filter_expression: Any | None = None,
        limit: int = 50,
        scan_forward: bool = False,
        start_key: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        return self.query(
            key_condition=Key(DocumentMetadata.TENANT_ID).eq(tenant_id),
            filter_expression=filter_expression,
            index_name=self._get_index("documentai_document_metadata_tenant_index_name"),
            limit=limit,
            scan_forward=scan_forward,
            start_key=start_key,
        )

    def query_by_job_id(self, job_id: str) -> dict[str, Any] | None:
        items, _ = self.query(
            key_condition=Key(DocumentMetadata.JOB_ID).eq(job_id),
            index_name=self._get_index("documentai_document_metadata_job_id_index_name"),
            limit=1,
        )
        return items[0] if items else None


_table = _DocumentMetadataTable()


def _record_to_item(record: dict[str, Any]) -> DocumentListItem:
    """Convert a DDB record to a list item."""
    return DocumentListItem(
        job_id=record.get(DocumentMetadata.JOB_ID, ""),
        file_name=record.get(DocumentMetadata.ORIGINAL_FILE_NAME, ""),
        tenant_id=record.get(DocumentMetadata.TENANT_ID, ""),
        api_key_name=record.get(DocumentMetadata.API_KEY_NAME, ""),
        process_status=record.get(DocumentMetadata.PROCESS_STATUS, ""),
        document_category=record.get(DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY, ""),
        matched_blueprint=record.get(DocumentMetadata.BDA_MATCHED_BLUEPRINT_NAME, ""),
        created_at=record.get(DocumentMetadata.CREATED_AT, ""),
        processed_date=record.get(DocumentMetadata.PROCESSED_DATE, ""),
    )


def _record_to_detail(record: dict[str, Any]) -> DocumentDetail:
    """Convert a DDB record to a full detail response."""
    return DocumentDetail(
        job_id=record.get(DocumentMetadata.JOB_ID, ""),
        file_name=record.get(DocumentMetadata.ORIGINAL_FILE_NAME, ""),
        tenant_id=record.get(DocumentMetadata.TENANT_ID, ""),
        api_key_name=record.get(DocumentMetadata.API_KEY_NAME, ""),
        process_status=record.get(DocumentMetadata.PROCESS_STATUS, ""),
        document_category=record.get(DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY, ""),
        matched_blueprint=record.get(DocumentMetadata.BDA_MATCHED_BLUEPRINT_NAME, ""),
        matched_blueprint_confidence=record.get(DocumentMetadata.BDA_MATCHED_BLUEPRINT_CONFIDENCE),
        matched_document_class=record.get(DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS, ""),
        created_at=record.get(DocumentMetadata.CREATED_AT, ""),
        processed_date=record.get(DocumentMetadata.PROCESSED_DATE, ""),
        error_message=record.get(DocumentMetadata.ERROR_MESSAGE),
        content_type=record.get(DocumentMetadata.CONTENT_TYPE, ""),
        file_size_bytes=record.get(DocumentMetadata.FILE_SIZE_BYTES),
        pages_detected=record.get(DocumentMetadata.PAGES_DETECTED),
        total_processing_time_seconds=record.get(DocumentMetadata.TOTAL_PROCESSING_TIME_SECONDS),
        bda_processing_time_seconds=record.get(DocumentMetadata.BDA_PROCESSING_TIME_SECONDS),
        bda_region_used=record.get(DocumentMetadata.BDA_REGION_USED, ""),
        retry_count=record.get(DocumentMetadata.RETRY_COUNT, 0),
        field_confidence_scores=_parse_confidence_scores(record),
        external_document_id=record.get(DocumentMetadata.EXTERNAL_DOCUMENT_ID, ""),
        batch_id=record.get(DocumentMetadata.BATCH_ID, ""),
        fields=_parse_extracted_data(record),
    )


def _parse_confidence_scores(record: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Parse field confidence scores — stored as JSON string in DDB."""
    raw = record.get(DocumentMetadata.FIELD_CONFIDENCE_SCORES)
    if not raw:
        return None
    if isinstance(raw, str):
        try:
            result: list[dict[str, Any]] = json.loads(raw)
            return result
        except json.JSONDecodeError:
            return None
    result_raw: list[dict[str, Any]] = raw
    return result_raw


def _parse_extracted_data(record: dict[str, Any]) -> dict[str, Any] | None:
    """Parse the v1 API response JSON to extract field values."""
    raw = record.get(DocumentMetadata.V1_API_RESPONSE_JSON)
    if not raw:
        return None
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        result: dict[str, Any] | None = parsed.get("fields")
        return result
    except (json.JSONDecodeError, AttributeError):
        logger.warning(f"Failed to parse extracted data for {record.get(DocumentMetadata.JOB_ID)}")
        return None


@router.get("")
async def list_documents(
    claims: AdminClaims,
    tenant_id: str | None = None,
    status_filter: str | None = None,
    limit: PageLimit = 50,
    cursor: str | None = None,
) -> DocumentListResponse:
    """List documents by tenant, paginated by createdAt descending.

    Super-admins can query any tenant. Tenant-admins are locked to their own.

    Note: when status_filter is set, DDB applies Limit before FilterExpression,
    so a page may return fewer than `limit` items. Use next_cursor to fetch more.
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

    try:
        exclusive_start_key = decode_cursor(cursor) if cursor else None
        filter_expr = (
            Attr(DocumentMetadata.PROCESS_STATUS).eq(status_filter) if status_filter else None
        )

        documents_raw, last_key = _table.query_by_tenant(
            tenant_id,
            filter_expression=filter_expr,
            limit=limit,
            start_key=exclusive_start_key,
        )

        documents = [_record_to_item(item) for item in documents_raw]
        next_cursor = encode_cursor(last_key) if last_key else None

        return DocumentListResponse(
            documents=documents, count=len(documents), next_cursor=next_cursor
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list documents",
        ) from e


@router.get("/{job_id}")
async def get_document(
    job_id: str,
    claims: AdminClaims,
) -> DocumentDetail:
    """Get full document detail by job ID.

    Super-admins can view any document. Tenant-admins can only view their own.
    """
    scope = tenant_scope(claims)

    try:
        record = _table.query_by_job_id(job_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        # Tenant-admin scoping — returns 404 to avoid existence disclosure.
        if scope is not None and record.get(DocumentMetadata.TENANT_ID) != scope:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        # jobId is unique by design (UUID generated upstream); first match is safe.
        return _record_to_detail(record)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document",
        ) from e
