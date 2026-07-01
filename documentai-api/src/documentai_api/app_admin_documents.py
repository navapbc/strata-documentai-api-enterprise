"""Admin documents router - read-only access to processed documents."""

import json
from typing import Any

from boto3.dynamodb.conditions import Attr
from fastapi import APIRouter, Depends, HTTPException, status

from documentai_api.annotations import AdminClaims, PageLimit, verify_jwt_with_role
from documentai_api.config.constants import ApiVisualizationTag, ConfigDefaults, FileValidation
from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.models.admin_document import (
    DocumentDetail,
    DocumentListItem,
    DocumentListResponse,
    DocumentPreviewResponse,
)
from documentai_api.schemas.audit_event import AuditAction, AuditTargetType
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.services import s3 as s3_service
from documentai_api.utils.audit import log_event
from documentai_api.utils.document_metadata_table import DocumentMetadataTable
from documentai_api.utils.jwt_auth import tenant_scope
from documentai_api.utils.pagination import decode_cursor, encode_cursor
from documentai_api.utils.response_builder import _extract_field_values, nest_fields
from documentai_api.utils.s3 import get_bucket_and_key

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/admin/documents",
    tags=[ApiVisualizationTag.ADMIN_DOCUMENTS],
    dependencies=[Depends(verify_jwt_with_role)],
)

_table = DocumentMetadataTable()


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


def _record_to_detail(
    record: dict[str, Any],
    include_extracted_data: bool = False,
    include_bounding_box: bool = False,
) -> DocumentDetail:
    """Convert a DDB record to a full detail response."""
    fields = (
        nest_fields(
            _extract_field_values(
                record,
                True,
                include_bounding_box,
                document_type=record.get(DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS),
            )
        )
        if include_extracted_data
        else _parse_extracted_data(record)
    )
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
        # Coalesce: new records write extractionProcessingTimeSeconds; legacy have bdaProcessingTimeSeconds
        bda_processing_time_seconds=record.get(DocumentMetadata.EXTRACTION_PROCESSING_TIME_SECONDS)
        or record.get(DocumentMetadata.BDA_PROCESSING_TIME_SECONDS),
        bda_region_used=record.get(DocumentMetadata.BDA_REGION_USED, ""),
        retry_count=record.get(DocumentMetadata.RETRY_COUNT, 0),
        field_confidence_scores=_parse_confidence_scores(record),
        external_document_id=record.get(DocumentMetadata.EXTERNAL_DOCUMENT_ID, ""),
        batch_id=record.get(DocumentMetadata.BATCH_ID, ""),
        fields=fields,
    )


def _parse_confidence_scores(record: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Parse field confidence scores - stored as JSON string in DDB."""
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
        fields: dict[str, Any] | None = parsed.get("fields")
        # Stored fields are flat/dotted; nest + camelCase at the presentation boundary.
        return nest_fields(fields) if isinstance(fields, dict) else fields
    except (json.JSONDecodeError, AttributeError):
        logger.warning(f"Failed to parse extracted data for {record.get(DocumentMetadata.JOB_ID)}")
        return None


@router.get("")
async def list_documents(
    claims: AdminClaims,
    tenant_id: str | None = None,
    status_filter: str | None = None,
    is_demo: bool | None = None,
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
        filter_parts = []
        if status_filter:
            filter_parts.append(Attr(DocumentMetadata.PROCESS_STATUS).eq(status_filter))
        if is_demo is not None:
            filter_parts.append(Attr(DocumentMetadata.IS_DEMO).eq(is_demo))

        filter_expr = None
        if filter_parts:
            filter_expr = filter_parts[0]
            for part in filter_parts[1:]:
                filter_expr = filter_expr & part

        documents_raw, last_key = _table.query_by_tenant(
            tenant_id,
            filter_expression=filter_expr,
            limit=limit,
            start_key=exclusive_start_key,
        )

        documents = [_record_to_item(item) for item in documents_raw]
        next_cursor = encode_cursor(last_key) if last_key else None

        log_event(
            claims,
            action=AuditAction.DOCUMENT_LIST,
            target_type=AuditTargetType.DOCUMENT,
            target_id=tenant_id,
            tenant_id=tenant_id,
            metadata={"count": len(documents), "status_filter": status_filter},
        )

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
    include_extracted_data: bool = False,
    include_bounding_box: bool = False,
) -> DocumentDetail:
    """Get full document detail by job ID.

    Super-admins can view any document. Tenant-admins can only view their own.
    """
    if include_bounding_box:
        include_extracted_data = True
    scope = tenant_scope(claims)

    log_event(
        claims,
        action=AuditAction.DOCUMENT_SEARCH,
        target_type=AuditTargetType.DOCUMENT,
        target_id=job_id,
    )

    try:
        record = _table.query_by_job_id(job_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        # Tenant-admin scoping - returns 404 to avoid existence disclosure.
        if scope is not None and record.get(DocumentMetadata.TENANT_ID) != scope:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        # jobId is unique by design (UUID generated upstream); first match is safe.
        detail = _record_to_detail(record, include_extracted_data, include_bounding_box)

        action = (
            AuditAction.DOCUMENT_VIEW_EXTRACTED_DATA
            if include_extracted_data
            else AuditAction.DOCUMENT_VIEW
        )
        log_event(
            claims,
            action=action,
            target_type=AuditTargetType.DOCUMENT,
            target_id=job_id,
            tenant_id=record.get(DocumentMetadata.TENANT_ID),
        )

        return detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document",
        ) from e


@router.get("/{job_id}/preview")
async def get_document_preview(
    job_id: str,
    claims: AdminClaims,
) -> DocumentPreviewResponse:
    """Get a short-lived presigned URL for previewing the original document.

    Returns a URL valid for 5 minutes. Only supports PDF and image files.
    """
    scope = tenant_scope(claims)

    try:
        record = _table.query_by_job_id(job_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        if scope is not None and record.get(DocumentMetadata.TENANT_ID) != scope:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        content_type = record.get(DocumentMetadata.CONTENT_TYPE, "")
        if content_type not in FileValidation.PREVIEWABLE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Preview not available for content type: {content_type}",
            )

        file_name = record.get(DocumentMetadata.FILE_NAME, "")
        tenant_id = record.get(DocumentMetadata.TENANT_ID, "")
        if not file_name or not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Incomplete document record",
            )

        input_location = get_aws_config().documentai_input_location
        if not input_location:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Storage not configured",
            )

        bucket, object_key = get_bucket_and_key(input_location, tenant_id, file_name)

        url = s3_service.generate_presigned_get_url(
            bucket=bucket,
            key=object_key,
            content_type=content_type,
            expiration=ConfigDefaults.PRESIGNED_PREVIEW_EXPIRY_SECONDS,
        )

        log_event(
            claims,
            action=AuditAction.DOCUMENT_PREVIEW,
            target_type=AuditTargetType.DOCUMENT,
            target_id=job_id,
            tenant_id=tenant_id,
        )

        return DocumentPreviewResponse(
            url=url,
            content_type=content_type,
            expires_in=ConfigDefaults.PRESIGNED_PREVIEW_EXPIRY_SECONDS,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate preview URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate preview URL",
        ) from e
