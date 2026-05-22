"""Document endpoints (upload, query, delete, search)."""

import asyncio
import json
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)

from documentai_api.annotations import (
    AiConsentFlag,
    AuthUser,
    CategoryField,
    ExternalDocumentId,
    ExternalSystemId,
    TraceId,
)
from documentai_api.config.constants import (
    MAX_SEARCH_JOB_IDS,
    ApiVisualizationTag,
    ConfigDefaults,
    ProcessStatus,
    UploadMethod,
)
from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.models.api_responses import (
    DocumentSearchRequest,
    DocumentSearchResponse,
    JobStatusResponse,
    UploadAsyncResponse,
)
from documentai_api.models.document_record import DocumentRecord
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.auth import get_user_context
from documentai_api.utils.ddb import (
    classify_as_ai_consent_declined,
    insert_minimal_ddb_record,
)
from documentai_api.utils.jobs import JobStatus, get_job_status, poll_for_completion
from documentai_api.utils.response_builder import build_v1_api_response
from documentai_api.utils.tenant import validate_document_tenant_access
from documentai_api.utils.uploads import (
    ImageConversionError,
    dispatch_upload,
    generate_unique_filename,
    validate_upload,
)

logger = get_logger(__name__)

# Router-level dep enforces auth on every route even if a handler forgets to inject `auth`.
# FastAPI caches the call within a request, so the per-handler `Depends(get_user_context)` is free.
router = APIRouter(dependencies=[Depends(get_user_context)])


# =============================================================================
# Endpoints
# =============================================================================


class _UploadResult:
    """Result of _upload_document: job_id + status/message."""

    __slots__ = ("job_id", "job_status", "message")

    def __init__(self, job_id: str, job_status: str, message: str) -> None:
        self.job_id = job_id
        self.job_status = job_status
        self.message = message


async def _upload_document(
    response: Response,
    file: UploadFile,
    auth: AuthUser,
    category: CategoryField = None,
    trace_id: TraceId = None,
    external_document_id: ExternalDocumentId = None,
    external_system_id: ExternalSystemId = None,
    ai_consent_flag: AiConsentFlag = True,
) -> _UploadResult:
    """Shared upload logic. Returns an _UploadResult with job_id, status, and message."""
    if not trace_id:
        trace_id = str(uuid.uuid4())

    response.headers["X-Trace-ID"] = trace_id

    actual_content_type = await validate_upload(file)
    filename: str = file.filename  # type: ignore[assignment]

    logger.info(
        "Processing document",
        extra={
            "upload_filename": filename,
            "category": category.value if category else None,
            "content_type": actual_content_type,
        },
    )

    job_id = str(uuid.uuid4())
    unique_file_name = generate_unique_filename(filename, job_id)
    ddb_key = unique_file_name

    input_location = get_aws_config().documentai_input_location
    dest_path = f"{input_location}/{unique_file_name}"

    try:
        record = DocumentRecord(
            ddb_key=ddb_key,
            original_file_name=filename,
            job_id=job_id,
            category=category,
            trace_id=trace_id,
            content_type=actual_content_type,
            external_document_id=external_document_id,
            external_system_id=external_system_id,
            ai_consent_flag=ai_consent_flag,
            upload_method=UploadMethod.DIRECT,
            tenant_id=auth.tenant_id,
            client_name=auth.client_name,
        )
        await asyncio.to_thread(insert_minimal_ddb_record, record)
    except Exception:
        logger.exception("Failed to create tracking record")
        raise HTTPException(status_code=500, detail="Failed to create upload record") from None

    if ai_consent_flag is False:
        await asyncio.to_thread(classify_as_ai_consent_declined, object_key=ddb_key)
        return _UploadResult(
            job_id=job_id,
            job_status=ProcessStatus.AI_CONSENT_DECLINED.value,
            message="Document not processed - AI consent not provided",
        )

    try:
        await dispatch_upload(
            src_file=file.file,
            dest_path=dest_path,
            original_file_name=filename,
            content_type=actual_content_type,
            category=category,
            job_id=job_id,
            trace_id=trace_id,
            ddb_key=ddb_key,
        )
    except ImageConversionError:
        return _UploadResult(
            job_id=job_id,
            job_status=ProcessStatus.CONVERSION_FAILED.value,
            message="Image conversion failed",
        )

    return _UploadResult(
        job_id=job_id,
        job_status=ProcessStatus.NOT_STARTED.value,
        message="Document uploaded successfully",
    )


@router.post(
    "/v1/documents",
    name="postUpload",
    status_code=status.HTTP_202_ACCEPTED,
    tags=[ApiVisualizationTag.DOCUMENTS_UPLOAD],
)
async def create_document(
    response: Response,
    file: UploadFile,
    auth: AuthUser,
    category: CategoryField = None,
    trace_id: TraceId = None,
    external_document_id: ExternalDocumentId = None,
    external_system_id: ExternalSystemId = None,
    ai_consent_flag: AiConsentFlag = True,
) -> UploadAsyncResponse:
    """Upload a document for processing (fire-and-forget)."""
    result = await _upload_document(
        response,
        file,
        auth,
        category,
        trace_id,
        external_document_id,
        external_system_id,
        ai_consent_flag,
    )
    return UploadAsyncResponse(
        job_id=result.job_id,
        job_status=result.job_status,
        message=result.message,
    )


@router.post(
    "/v1/documents/wait",
    name="postUploadWait",
    tags=[ApiVisualizationTag.DOCUMENTS_UPLOAD],
)
async def create_document_wait(
    request: Request,
    response: Response,
    file: UploadFile,
    auth: AuthUser,
    category: CategoryField = None,
    trace_id: TraceId = None,
    external_document_id: ExternalDocumentId = None,
    external_system_id: ExternalSystemId = None,
    ai_consent_flag: AiConsentFlag = True,
    include_extracted_data: bool = False,
    timeout: Annotated[int, Query(ge=1)] = ConfigDefaults.MAX_WAIT_SECONDS
    - ConfigDefaults.ALB_TIMEOUT_BUFFER_SECONDS,
) -> JobStatusResponse:
    """Upload a document and poll until processing completes or timeout."""
    result = await _upload_document(
        response,
        file,
        auth,
        category,
        trace_id,
        external_document_id,
        external_system_id,
        ai_consent_flag,
    )
    # Terminal states (consent declined, conversion failed) — return immediately.
    if ProcessStatus.is_classified(result.job_status):
        return JobStatusResponse(
            job_id=result.job_id,
            job_status=result.job_status,
            message=result.message,
        )
    safe_timeout = min(
        timeout, ConfigDefaults.MAX_WAIT_SECONDS - ConfigDefaults.ALB_TIMEOUT_BUFFER_SECONDS
    )
    return await poll_for_completion(
        result.job_id, safe_timeout, request=request, include_extracted_data=include_extracted_data
    )


@router.get(
    "/v1/documents/{job_id}",
    tags=[ApiVisualizationTag.DOCUMENTS_QUERY],
)
async def get_document_results(
    job_id: uuid.UUID,
    response: Response,
    auth: AuthUser,
    include_extracted_data: bool = False,
    trace_id: TraceId = None,
) -> JobStatusResponse:
    """Get processing results by job ID."""
    if not trace_id:
        trace_id = str(uuid.uuid4())
    response.headers["X-Trace-ID"] = trace_id

    try:
        job_status = await asyncio.to_thread(get_job_status, str(job_id))

        validate_document_tenant_access(job_status.ddb_record, auth.tenant_id, str(job_id))

        # SECURITY: This must return the same 404 as validate_document_tenant_access
        # to prevent job_id enumeration across tenants.
        if job_status.process_status == ProcessStatus.DELETED.value:
            raise HTTPException(status_code=404, detail=f"Job ID {job_id} not found")

        if not job_status.v1_response_json:
            return JobStatusResponse(
                job_id=str(job_id),
                job_status=job_status.process_status or ProcessStatus.NOT_STARTED.value,
                message="Processing in progress",
            )

        # TODO: Terminal states are immutable - add Cache-Control + ETag headers
        # to reduce DDB reads from repeated client polls after completion.
        # processing complete
        if include_extracted_data:
            if not job_status.object_key or not job_status.process_status:
                raise HTTPException(status_code=500, detail=f"Incomplete record for job {job_id}")

            result = await asyncio.to_thread(
                build_v1_api_response,
                object_key=job_status.object_key,
                job_status=job_status.process_status,
                include_extracted_data=True,
            )
            return JobStatusResponse(**result)
        else:
            return JobStatusResponse(**json.loads(job_status.v1_response_json))

    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "get_document_results failed", extra={"job_id": str(job_id), "trace_id": trace_id}
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve results") from None


@router.delete(
    "/v1/documents/{job_id}",
    name="deleteDocument",
    tags=[ApiVisualizationTag.DOCUMENTS_DELETE],
)
async def delete_document(job_id: uuid.UUID, auth: AuthUser) -> Response:
    """Delete a document by job ID. Removes S3 file and marks DDB record as deleted."""
    from documentai_api.services import s3 as s3_service
    from documentai_api.utils.s3 import parse_s3_uri

    job_status = await asyncio.to_thread(get_job_status, str(job_id))

    validate_document_tenant_access(job_status.ddb_record, auth.tenant_id, str(job_id))

    current_status = job_status.process_status
    if current_status == ProcessStatus.DELETED.value:
        raise HTTPException(status_code=404, detail=f"Job ID {job_id} not found")

    if not current_status or not ProcessStatus.is_classified(current_status):
        raise HTTPException(
            status_code=400, detail="Cannot delete a document that is still processing"
        )

    # delete S3 file
    if job_status.object_key:
        try:
            input_location = get_aws_config().documentai_input_location
            if input_location:
                bucket, prefix = parse_s3_uri(input_location)
                s3_key = f"{prefix}/{job_status.object_key}" if prefix else job_status.object_key
                await asyncio.to_thread(s3_service.delete_object, bucket, s3_key)
        except Exception as e:
            logger.warning(f"Failed to delete S3 object for job {job_id}: {e}")

    # mark DDB record as deleted
    from documentai_api.utils.ddb import update_ddb

    if not job_status.object_key:
        raise HTTPException(status_code=500, detail=f"Incomplete record for job {job_id}")

    await asyncio.to_thread(
        update_ddb, object_key=job_status.object_key, status=ProcessStatus.DELETED
    )

    return Response(status_code=204)


@router.post(
    "/v1/documents/search",
    name="searchDocuments",
    tags=[ApiVisualizationTag.DOCUMENTS_QUERY],
)
async def search_documents(body: DocumentSearchRequest, auth: AuthUser) -> DocumentSearchResponse:
    """Search for multiple documents by job IDs."""
    if not body.job_ids:
        raise HTTPException(status_code=400, detail="job_ids must not be empty")
    if len(body.job_ids) > MAX_SEARCH_JOB_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum of {MAX_SEARCH_JOB_IDS} job_ids per request",
        )

    results: list[JobStatusResponse] = []
    job_statuses = await asyncio.gather(
        *[asyncio.to_thread(get_job_status, job_id) for job_id in body.job_ids],
        return_exceptions=True,
    )

    for job_id, job_status in zip(body.job_ids, job_statuses, strict=True):
        try:
            if isinstance(job_status, BaseException):
                raise job_status
            assert isinstance(job_status, JobStatus)

            if (
                not job_status.ddb_record
                or job_status.ddb_record.get(DocumentMetadata.TENANT_ID) != auth.tenant_id
            ):
                results.append(
                    JobStatusResponse(
                        job_id=job_id,
                        job_status="not_found",
                        message="Job ID not found",
                    )
                )
            elif not job_status.v1_response_json:
                results.append(
                    JobStatusResponse(
                        job_id=job_id,
                        job_status=job_status.process_status or ProcessStatus.NOT_STARTED.value,
                        message="Processing in progress",
                    )
                )
            elif body.include_extracted_data:
                if not job_status.object_key or not job_status.process_status:
                    results.append(
                        JobStatusResponse(
                            job_id=job_id,
                            job_status="error",
                            message="Incomplete record",
                        )
                    )
                else:
                    result = await asyncio.to_thread(
                        build_v1_api_response,
                        object_key=job_status.object_key,
                        job_status=job_status.process_status,
                        include_extracted_data=True,
                    )
                    results.append(JobStatusResponse(**result))
            else:
                results.append(JobStatusResponse(**json.loads(job_status.v1_response_json)))
        except Exception:
            logger.exception("Error retrieving job in search", extra={"job_id": job_id})
            results.append(
                JobStatusResponse(
                    job_id=job_id,
                    job_status="error",
                    message="Failed to retrieve results",
                )
            )

    return DocumentSearchResponse(results=results)
