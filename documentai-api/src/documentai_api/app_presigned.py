"""Presigned URL endpoints."""

import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Response

from documentai_api.annotations import (
    AuthUser,
    CategoryField,
    ExternalDocumentId,
    ExternalSystemId,
    TraceId,
)
from documentai_api.config.constants import (
    ApiVisualizationTag,
    ConfigDefaults,
    FileValidation,
    ProcessStatus,
    UploadMethod,
)
from documentai_api.config.env import get_app_env_config, get_aws_config
from documentai_api.logging import get_logger
from documentai_api.models.api_responses import PresignedUploadResponse
from documentai_api.models.document_record import DocumentRecord
from documentai_api.services import s3 as s3_service
from documentai_api.utils.auth import get_user_context_from_api_key
from documentai_api.utils.document_lifecycle import insert_minimal_ddb_record
from documentai_api.utils.s3 import build_s3_key, parse_s3_uri, sanitize_for_s3_metadata
from documentai_api.utils.uploads import generate_unique_filename

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(get_user_context_from_api_key)])

MAX_UPLOAD_SIZE_BYTES = ConfigDefaults.BDA_MAX_DOCUMENT_FILE_SIZE_BYTES
MAX_FILENAME_LENGTH = 255


def _validate_trace_id(trace_id: str | None) -> str:
    """Validate trace_id is a UUID or generate one."""
    if not trace_id:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(trace_id))
    except ValueError:
        return str(uuid.uuid4())


@router.post(
    "/v1/documents/presigned-url",
    tags=[ApiVisualizationTag.DOCUMENTS_UPLOAD],
)
async def create_presigned_upload_url(
    response: Response,
    auth: AuthUser,
    filename: Annotated[str, Form(description="Original filename", max_length=MAX_FILENAME_LENGTH)],
    content_type: Annotated[str, Form(description="MIME type of the file")],
    category: CategoryField = None,
    trace_id: TraceId = None,
    external_document_id: ExternalDocumentId = None,
    # ai_consent_flag is not accepted here - presigned URLs are only generated
    # when the caller intends to upload for processing. If consent is declined,
    # use POST /v1/documents with ai_consent_flag=false instead (stores metadata
    # without uploading to S3).
    external_system_id: ExternalSystemId = None,
) -> PresignedUploadResponse:
    """Generate a presigned POST URL for direct S3 upload.

    The returned URL and fields should be used to construct a multipart/form-data
    POST request to S3. S3 enforces content-type and size limits via the POST policy.
    """
    if content_type not in FileValidation.NO_CONVERSION_NEEDED:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Presigned uploads only support BDA-native formats: "
                f"{', '.join(FileValidation.NO_CONVERSION_NEEDED)}. "
                f"For '{content_type}', use the direct upload endpoint (POST /v1/documents) "
                f"which handles format conversion automatically."
            ),
        )

    trace_id = _validate_trace_id(trace_id)
    expiry = get_app_env_config().presigned_url_expiry_seconds

    input_location = get_aws_config().documentai_input_location
    if not input_location:
        raise HTTPException(status_code=500, detail="Upload location not configured")

    try:
        bucket_name, prefix = parse_s3_uri(input_location)
    except Exception:
        raise HTTPException(status_code=500, detail="Upload location misconfigured") from None

    job_id = str(uuid.uuid4())
    unique_file_name = generate_unique_filename(filename, job_id)
    ddb_key = unique_file_name
    object_key = build_s3_key(prefix, auth.tenant_id, unique_file_name)

    # Sanitize filename for S3 metadata (ASCII-only, 2KB total limit)
    safe_filename = sanitize_for_s3_metadata(filename)

    metadata = {
        "job-id": job_id,
        "trace-id": trace_id,
        "original-file-name": safe_filename,
    }
    if category:
        metadata["user-provided-document-category"] = category.value

    # Generate the presigned POST before writing to DDB.
    # Signing is local CPU work (no network call), so failure is unlikely -
    # but if it does fail, we avoid orphaning a PENDING_UPLOAD DDB row.
    try:
        post_data = s3_service.generate_presigned_post(
            bucket=bucket_name,
            key=object_key,
            content_type=content_type,
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            metadata=metadata,
            expiration=expiry,
        )
    except Exception:
        logger.exception("Failed to generate presigned POST")
        raise HTTPException(status_code=500, detail="Failed to generate upload URL") from None

    try:
        record = DocumentRecord(
            ddb_key=ddb_key,
            original_file_name=filename,
            job_id=job_id,
            process_status=ProcessStatus.PENDING_UPLOAD,
            category=category,
            trace_id=trace_id,
            content_type=content_type,
            external_document_id=external_document_id,
            external_system_id=external_system_id,
            upload_method=UploadMethod.PRESIGNED,
            tenant_id=auth.tenant_id,
            api_key_name=auth.api_key_name,
        )
        await asyncio.to_thread(insert_minimal_ddb_record, record)
    except Exception:
        logger.exception("Failed to create tracking record")
        raise HTTPException(status_code=500, detail="Failed to create upload record") from None

    logger.info(
        "Presigned POST generated",
        extra={
            "job_id": job_id,
            "tenant_id": auth.tenant_id,
            "content_type": content_type,
            "upload_filename": filename,
        },
    )

    response.headers["X-Trace-ID"] = trace_id
    return PresignedUploadResponse(
        upload_url=post_data["url"],
        fields=post_data["fields"],
        job_id=job_id,
        expires_in=expiry,
        max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
    )
