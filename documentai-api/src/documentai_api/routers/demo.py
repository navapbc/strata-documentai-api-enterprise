"""Demo router - JWT-authenticated document upload and read."""

import asyncio
import uuid
from typing import Annotated

from boto3.dynamodb.conditions import Attr
from fastapi import APIRouter, Depends, Form, HTTPException, Response, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from documentai_api.config.env import get_app_config, get_env_config
from documentai_api.constants.defaults import SystemDefaults
from documentai_api.constants.file_validation import FileValidation
from documentai_api.constants.processing import ProcessStatus, UploadMethod
from documentai_api.logging import get_logger
from documentai_api.models.admin_document import (
    DocumentDetail,
    DocumentListResponse,
    DocumentPreviewResponse,
)
from documentai_api.models.document_record import DocumentRecord
from documentai_api.models.job_status import UploadAsyncResponse
from documentai_api.models.presigned import PresignedUploadResponse
from documentai_api.pipeline.document_lifecycle import insert_minimal_ddb_record
from documentai_api.routers.admin_documents import (
    _record_to_detail,
    _record_to_item,
)
from documentai_api.routers.documents import upload_document
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.services import s3 as s3_service
from documentai_api.utils.auth import UserContext, get_user_context_with_fallback
from documentai_api.utils.document_metadata_table import DocumentMetadataTable
from documentai_api.utils.pagination import decode_cursor, encode_cursor
from documentai_api.utils.s3 import (
    assert_object_exists,
    build_s3_key,
    get_bucket_and_key,
    parse_s3_uri,
    sanitize_for_s3_metadata,
)
from documentai_api.utils.uploads import generate_unique_filename

router = APIRouter(prefix="/v1/demo")

logger = get_logger(__name__)
_bearer_scheme = HTTPBearer(auto_error=False)
_table = DocumentMetadataTable()

# Auth types live here (not annotations.py) to avoid circular imports -
# _resolve_demo_context depends on app-level logic that annotations can't import.
_FallbackAuth = Annotated[UserContext, Depends(get_user_context_with_fallback)]
_BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)]


async def _resolve_demo_context(
    auth: _FallbackAuth,
    credentials: _BearerCredentials = None,
) -> UserContext:
    """Reuse standard auth verification, then override tenant_id to demo-{sub}."""
    from documentai_api.utils.jwt_auth import _decode_and_verify

    # auth is already verified by get_user_context_with_fallback.
    # Extract sub from the raw token for the per-user demo tenant.
    sub = None
    if credentials:
        try:
            claims = _decode_and_verify(credentials.credentials)
            sub = claims.get("sub")
        except Exception:
            pass

    if not sub:
        raise HTTPException(status_code=401, detail="Bearer token with sub claim required")

    return UserContext(
        tenant_id=f"demo-{sub}",
        api_key_name=sub,
        auth_method=auth.auth_method,
    )


DemoAuth = Annotated[UserContext, Depends(_resolve_demo_context)]


def _get_demo_input_location() -> str:
    location = get_env_config().documentai_demo_input_location
    if not location:
        raise HTTPException(status_code=500, detail="Demo storage not configured")
    return location


# =============================================================================
# Upload
# =============================================================================


@router.post("/documents/presigned-url")
async def create_demo_presigned_upload_url(
    auth: DemoAuth,
    filename: Annotated[str, Form(description="Original filename", max_length=255)],
    content_type: Annotated[str, Form(description="MIME type of the file")],
) -> PresignedUploadResponse:
    """Generate a presigned POST URL for direct S3 upload from the demo UI."""
    if content_type not in FileValidation.NO_CONVERSION_NEEDED:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Presigned uploads only support: {', '.join(FileValidation.NO_CONVERSION_NEEDED)}. "
                f"For '{content_type}', use the direct upload endpoint."
            ),
        )

    input_location = get_env_config().documentai_demo_input_location
    if not input_location:
        raise HTTPException(status_code=500, detail="Demo storage not configured")

    try:
        bucket_name, prefix = parse_s3_uri(input_location)
    except Exception:
        raise HTTPException(status_code=500, detail="Demo storage misconfigured") from None

    job_id = str(uuid.uuid4())
    unique_file_name = generate_unique_filename(filename, job_id)
    object_key = build_s3_key(prefix, auth.tenant_id, unique_file_name)
    safe_filename = sanitize_for_s3_metadata(filename)

    metadata = {
        "job-id": job_id,
        "original-file-name": safe_filename,
    }

    try:
        post_data = s3_service.generate_presigned_post(
            bucket=bucket_name,
            key=object_key,
            content_type=content_type,
            max_size_bytes=SystemDefaults.BDA_MAX_DOCUMENT_FILE_SIZE_BYTES,
            metadata=metadata,
            expiration=get_app_config().presigned_url_expiry_seconds,
        )
    except Exception:
        logger.exception("Failed to generate demo presigned POST")
        raise HTTPException(status_code=500, detail="Failed to generate upload URL") from None

    try:
        record = DocumentRecord(
            ddb_key=unique_file_name,
            original_file_name=filename,
            job_id=job_id,
            system_document_id=job_id,
            process_status=ProcessStatus.PENDING_UPLOAD,
            content_type=content_type,
            upload_method=UploadMethod.PRESIGNED,
            tenant_id=auth.tenant_id,
            api_key_name=auth.api_key_name,
            is_demo=True,
        )
        await asyncio.to_thread(insert_minimal_ddb_record, record)
    except Exception:
        logger.exception("Failed to create demo tracking record")
        raise HTTPException(status_code=500, detail="Failed to create upload record") from None

    logger.info(
        "Demo presigned POST generated",
        extra={"job_id": job_id, "tenant_id": auth.tenant_id, "content_type": content_type},
    )
    return PresignedUploadResponse(
        upload_url=post_data["url"],
        fields=post_data["fields"],
        job_id=job_id,
        expires_in=get_app_config().presigned_url_expiry_seconds,
        max_size_bytes=SystemDefaults.BDA_MAX_DOCUMENT_FILE_SIZE_BYTES,
    )


@router.post("/documents", status_code=status.HTTP_202_ACCEPTED)
async def create_demo_document(
    response: Response,
    file: UploadFile,
    auth: DemoAuth,
) -> UploadAsyncResponse:
    """Upload a document via the demo pipeline."""
    result = await upload_document(response, file, auth, is_demo=True)
    return UploadAsyncResponse(
        job_id=result.job_id,
        job_status=result.job_status,
        message=result.message,
    )


# =============================================================================
# List
# =============================================================================


@router.get("/documents")
async def list_demo_documents(
    auth: DemoAuth,
    limit: int = 50,
    cursor: str | None = None,
) -> DocumentListResponse:
    """List demo documents for the authenticated user."""
    logger.info("Demo list", extra={"tenant_id": auth.tenant_id})
    start_key = decode_cursor(cursor) if cursor else None

    documents_raw, last_key = _table.query_by_tenant(
        auth.tenant_id,
        filter_expression=Attr(DocumentMetadata.IS_DEMO).eq(True),
        limit=limit,
        start_key=start_key,
    )

    documents = [_record_to_item(r) for r in documents_raw]
    return DocumentListResponse(
        documents=documents,
        count=len(documents),
        next_cursor=encode_cursor(last_key) if last_key else None,
    )


# =============================================================================
# Get
# =============================================================================


@router.get("/documents/{job_id}")
async def get_demo_document(
    job_id: str,
    auth: DemoAuth,
    include_extracted_data: bool = False,
    include_bounding_box: bool = False,
) -> DocumentDetail:
    """Get demo document detail by job ID."""
    if include_bounding_box:
        include_extracted_data = True

    record = _table.query_by_job_id(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")
    if record.get(DocumentMetadata.TENANT_ID) != auth.tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")

    logger.info("Demo document viewed", extra={"tenant_id": auth.tenant_id, "job_id": job_id})
    return _record_to_detail(record, include_extracted_data, include_bounding_box)


# =============================================================================
# Preview
# =============================================================================


@router.get("/documents/{job_id}/preview")
async def get_demo_document_preview(
    job_id: str,
    auth: DemoAuth,
) -> DocumentPreviewResponse:
    """Get presigned URL for previewing a demo document."""
    record = _table.query_by_job_id(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")
    if record.get(DocumentMetadata.TENANT_ID) != auth.tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")

    content_type = record.get(DocumentMetadata.CONTENT_TYPE, "")
    if content_type not in FileValidation.PREVIEWABLE_TYPES:
        raise HTTPException(status_code=422, detail=f"Preview not available for: {content_type}")

    file_name = record.get(DocumentMetadata.FILE_NAME, "")
    if not file_name:
        raise HTTPException(status_code=500, detail="Incomplete document record")

    bucket, object_key = get_bucket_and_key(_get_demo_input_location(), auth.tenant_id, file_name)

    try:
        assert_object_exists(bucket, object_key)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate demo preview URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate preview URL") from e

    url = s3_service.generate_presigned_get_url(
        bucket=bucket,
        key=object_key,
        content_type=content_type,
        expiration=SystemDefaults.PRESIGNED_PREVIEW_EXPIRY_SECONDS,
    )

    logger.info("Demo preview generated", extra={"tenant_id": auth.tenant_id, "job_id": job_id})
    return DocumentPreviewResponse(
        url=url,
        content_type=content_type,
        expires_in=SystemDefaults.PRESIGNED_PREVIEW_EXPIRY_SECONDS,
    )
