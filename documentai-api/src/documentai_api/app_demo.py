"""Demo router - JWT-authenticated document upload and read."""

from typing import Annotated

from boto3.dynamodb.conditions import Attr
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from documentai_api.app_admin_documents import (
    _record_to_detail,
    _record_to_item,
)
from documentai_api.app_documents import upload_document
from documentai_api.config.constants import ConfigDefaults, FileValidation
from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.models.admin_document import (
    DocumentDetail,
    DocumentListResponse,
    DocumentPreviewResponse,
)
from documentai_api.models.api_responses import UploadAsyncResponse
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.services import s3 as s3_service
from documentai_api.utils.auth import UserContext, get_user_context_with_fallback
from documentai_api.utils.document_metadata_table import DocumentMetadataTable
from documentai_api.utils.pagination import decode_cursor, encode_cursor
from documentai_api.utils.s3 import get_bucket_and_key

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
    location = get_aws_config().documentai_demo_input_location
    if not location:
        raise HTTPException(status_code=500, detail="Demo storage not configured")
    return location


# =============================================================================
# Upload
# =============================================================================


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

    url = s3_service.generate_presigned_get_url(
        bucket=bucket,
        key=object_key,
        content_type=content_type,
        expiration=ConfigDefaults.PRESIGNED_PREVIEW_EXPIRY_SECONDS,
    )

    logger.info("Demo preview generated", extra={"tenant_id": auth.tenant_id, "job_id": job_id})
    return DocumentPreviewResponse(
        url=url,
        content_type=content_type,
        expires_in=ConfigDefaults.PRESIGNED_PREVIEW_EXPIRY_SECONDS,
    )
