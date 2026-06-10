"""Batch upload endpoints.

Three routes:
- POST /v1/documents/batch       - multi-file upload
- POST /v1/documents/batch/zip   - ZIP archive upload
- GET  /v1/batches/{batch_id}    - aggregate status with per-job list
"""

import asyncio
import uuid
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Response,
    UploadFile,
)

from documentai_api.annotations import (
    AiConsentFlag,
    AuthUser,
    TraceId,
)
from documentai_api.config.constants import (
    DEFAULT_DDB_ERROR_MESSAGE,
    MAX_BATCH_SIZE,
    ApiVisualizationTag,
    BatchStatus,
    DocumentCategory,
    ProcessStatus,
    UploadMethod,
)
from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.models.api_responses import (
    BatchJobItem,
    BatchStatusJobItem,
    BatchStatusResponse,
    BatchUploadResponse,
)
from documentai_api.models.document_record import DocumentRecord
from documentai_api.schemas.document_batches import DocumentBatches
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.auth import UserContext, get_user_context_from_api_key
from documentai_api.utils.ddb import (
    classify_as_ai_consent_declined,
    classify_as_conversion_failed,
    classify_as_failed,
    create_batch,
    get_batch,
    insert_minimal_ddb_record,
    query_jobs_by_batch_id,
    update_batch_status,
)
from documentai_api.utils.dto import ClassificationData
from documentai_api.utils.tenant_access import validate_batch_tenant_access
from documentai_api.utils.uploads import (
    ImageConversionError,
    generate_unique_filename,
    upload_document_for_processing,
    validate_file_type,
)
from documentai_api.utils.zip import extract_files_from_zip

logger = get_logger(__name__)

# Router-level dep enforces auth on every route even if a handler forgets to inject `auth`.
# FastAPI caches the call within a request, so the per-handler `Depends(get_user_context_from_api_key)` is free.
router = APIRouter(dependencies=[Depends(get_user_context_from_api_key)])


async def _process_batch_files(
    files: list[UploadFile],
    batch_id: str,
    category: DocumentCategory | None,
    trace_id: str,
    tenant_id: str,
    api_key_name: str,
    external_document_id: str | None = None,
    external_system_id: str | None = None,
    ai_consent_flag: bool | None = None,
    upload_method: str = UploadMethod.BATCH,
) -> list[BatchJobItem]:
    """Upload each file in a batch to S3, return per-file job info."""
    input_location = get_aws_config().documentai_input_location
    if not input_location:
        raise HTTPException(
            status_code=500, detail="DOCUMENTAI_INPUT_LOCATION environment variable not set"
        )

    semaphore = asyncio.Semaphore(10)

    async def _process_one(idx: int, file: UploadFile) -> BatchJobItem:
        if not file.filename:
            raise HTTPException(
                status_code=400, detail=f"Filename is required (file at position {idx})"
            )

        actual_content_type = await validate_file_type(file)
        job_id = str(uuid.uuid4())
        unique_file_name = f"{idx}-{generate_unique_filename(file.filename, job_id)}"
        ddb_key = unique_file_name
        dest_path = f"{input_location}/{tenant_id}/{unique_file_name}"

        await asyncio.to_thread(
            insert_minimal_ddb_record,
            DocumentRecord(
                ddb_key=ddb_key,
                original_file_name=file.filename,
                job_id=job_id,
                category=category,
                trace_id=trace_id,
                batch_id=batch_id,
                content_type=actual_content_type,
                external_document_id=external_document_id,
                external_system_id=external_system_id,
                ai_consent_flag=ai_consent_flag,
                upload_method=upload_method,
                tenant_id=tenant_id,
                api_key_name=api_key_name,
            ),
        )

        if ai_consent_flag is False:
            await asyncio.to_thread(classify_as_ai_consent_declined, object_key=ddb_key)
            return BatchJobItem(file_name=file.filename, job_id=job_id, batch_position=idx)

        async with semaphore:
            try:
                await upload_document_for_processing(
                    src_file=file.file,
                    dest_path=dest_path,
                    original_file_name=file.filename,
                    content_type=actual_content_type,
                    user_provided_document_category=category,
                    job_id=job_id,
                    trace_id=trace_id,
                    batch_id=batch_id,
                    tenant_id=tenant_id,
                )
            except ImageConversionError as e:
                await asyncio.to_thread(
                    classify_as_conversion_failed, object_key=ddb_key, error_message=str(e)
                )
            except HTTPException as e:
                await asyncio.to_thread(
                    classify_as_failed,
                    object_key=ddb_key,
                    error_message=e.detail,
                    data=ClassificationData(additional_info=e.detail),
                )
                raise

        return BatchJobItem(file_name=file.filename, job_id=job_id, batch_position=idx)

    try:
        async with asyncio.TaskGroup() as tg:
            task_handles = [
                tg.create_task(_process_one(idx, file)) for idx, file in enumerate(files)
            ]
        return [t.result() for t in task_handles]
    except* HTTPException as eg:
        for exc in eg.exceptions:
            logger.warning("Batch file upload failed", extra={"error": str(exc)})
        raise eg.exceptions[0] from None
    except* Exception as eg:
        for exc in eg.exceptions:
            logger.exception("Unexpected batch file error", extra={"error": str(exc)})
        raise eg.exceptions[0] from None


async def _execute_batch(
    *,
    files: list[UploadFile],
    upload_method: str,
    auth: UserContext,
    category: DocumentCategory | None,
    trace_id: str,
    external_document_id: str | None,
    external_system_id: str | None,
    ai_consent_flag: bool | None,
) -> BatchUploadResponse:
    """Shared batch execution logic for both multi-file and ZIP uploads."""
    # Server-generated to prevent cross-tenant ID probing and collision attacks.
    # If tenant-supplied batch_id is needed, update dynamodb infra to support
    # a gsi on batch_id/tenant_id
    batch_id = f"{auth.tenant_id}/{uuid.uuid4()!s}"

    try:
        created_at = create_batch(
            batch_id,
            len(files),
            category,
            status=BatchStatus.UPLOADING,
            tenant_id=auth.tenant_id,
            api_key_name=auth.api_key_name,
        )
        jobs = await _process_batch_files(
            files=files,
            batch_id=batch_id,
            category=category,
            trace_id=trace_id,
            tenant_id=auth.tenant_id,
            api_key_name=auth.api_key_name,
            external_document_id=external_document_id,
            external_system_id=external_system_id,
            ai_consent_flag=ai_consent_flag,
            upload_method=upload_method,
        )
        update_batch_status(batch_id, status=BatchStatus.PROCESSING)

        return BatchUploadResponse(
            batch_id=batch_id,
            batch_status=BatchStatus.PROCESSING.value,
            total_files=len(files),
            created_at=created_at,
            jobs=jobs,
        )
    except HTTPException:
        raise
    except Exception as e:
        # Partial success is intentional: jobs that already uploaded keep processing
        # via S3 event triggers, independent of batch_status. We mark the batch FAILED
        # but do NOT delete completed siblings - those represent real user work and
        # have their own per-job status visible in GET /v1/batches/{batch_id}.
        # TODO: Jobs cancelled mid-upload leave DDB rows in non-terminal status
        # (S3 PUT never completed). Add TTL or sweeper to clean these up.
        logger.exception(
            "Batch upload failed",
            extra={"batch_id": batch_id, "trace_id": trace_id, "upload_method": upload_method},
        )
        if get_batch(batch_id):
            update_batch_status(
                batch_id, status=BatchStatus.FAILED, error_message=DEFAULT_DDB_ERROR_MESSAGE
            )
        raise HTTPException(status_code=500, detail="Failed to upload batch") from e


@router.post(
    "/v1/documents/batch",
    tags=[ApiVisualizationTag.DOCUMENTS_UPLOAD],
)
async def upload_document_batch(
    response: Response,
    files: Annotated[list[UploadFile], Form(description="Documents to process")],
    auth: AuthUser,
    category: Annotated[DocumentCategory | None, Form()] = None,
    trace_id: TraceId = None,
    external_document_id: Annotated[
        str | None, Form(description="External document identifier (applied to all files in batch)")
    ] = None,
    external_system_id: Annotated[
        str | None, Form(description="External system identifier (applied to all files in batch)")
    ] = None,
    ai_consent_flag: AiConsentFlag = True,
) -> BatchUploadResponse:
    """Upload multiple documents as a single batch."""
    if not trace_id:
        trace_id = str(uuid.uuid4())
    response.headers["X-Trace-ID"] = trace_id

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size exceeds maximum of {MAX_BATCH_SIZE} files",
        )

    return await _execute_batch(
        files=files,
        upload_method=UploadMethod.BATCH,
        auth=auth,
        category=category,
        trace_id=trace_id,
        external_document_id=external_document_id,
        external_system_id=external_system_id,
        ai_consent_flag=ai_consent_flag,
    )


@router.post(
    "/v1/documents/batch/zip",
    tags=[ApiVisualizationTag.DOCUMENTS_UPLOAD],
)
async def upload_zip_batch(
    response: Response,
    zip_file: Annotated[UploadFile, Form(description="ZIP file containing documents")],
    auth: AuthUser,
    category: Annotated[DocumentCategory | None, Form()] = None,
    trace_id: TraceId = None,
    external_document_id: Annotated[
        str | None, Form(description="External document identifier (applied to all files in batch)")
    ] = None,
    external_system_id: Annotated[
        str | None, Form(description="External system identifier (applied to all files in batch)")
    ] = None,
    ai_consent_flag: AiConsentFlag = True,
) -> BatchUploadResponse:
    """Upload a ZIP archive of documents as a single batch."""
    if not trace_id:
        trace_id = str(uuid.uuid4())
    response.headers["X-Trace-ID"] = trace_id

    files = await extract_files_from_zip(zip_file)
    if not files:
        raise HTTPException(status_code=400, detail="No valid files found in zip")

    return await _execute_batch(
        files=files,
        upload_method=UploadMethod.BATCH_ZIP,
        auth=auth,
        category=category,
        trace_id=trace_id,
        external_document_id=external_document_id,
        external_system_id=external_system_id,
        ai_consent_flag=ai_consent_flag,
    )


@router.get(
    "/v1/batches/{batch_id}",
    dependencies=[Depends(validate_batch_tenant_access)],
    tags=[ApiVisualizationTag.DOCUMENTS_QUERY],
)
async def get_batch_status(batch_id: str) -> BatchStatusResponse:
    """Get status of all documents in a batch.

    Batch completion is lazily evaluated: when all jobs are complete this endpoint
    updates the batch status to COMPLETED. For real-time updates use DDB Streams
    or EventBridge.
    """
    try:
        batch = get_batch(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

        # batch is guaranteed non-None from here
        batch_record: dict[str, Any] = batch

        job_records = query_jobs_by_batch_id(batch_id)
        jobs = [
            BatchStatusJobItem(
                file_name=record.get(DocumentMetadata.FILE_NAME),
                job_id=record.get(DocumentMetadata.JOB_ID),
                job_status=record.get(DocumentMetadata.PROCESS_STATUS, "not_found"),
            )
            for record in job_records
        ]

        completed = sum(1 for j in jobs if ProcessStatus.is_completed(j.job_status))
        failed = sum(1 for j in jobs if j.job_status == ProcessStatus.FAILED.value)
        current_batch_status = batch_record.get(DocumentBatches.BATCH_STATUS)

        # Lazy completion: if all jobs have reached a terminal state, mark batch done.
        # Terminal states include success, failed, conversion_failed, ai_consent_declined, etc.
        # TODO: Replace with atomic counters on the batch row so GET is pure-read
        # and completion doesn't depend on polling. See _execute_batch for context.
        all_classified = len(jobs) > 0 and all(
            ProcessStatus.is_classified(j.job_status) for j in jobs
        )
        if current_batch_status == BatchStatus.PROCESSING.value and all_classified:
            # TODO: Consider adding a PARTIAL batch status for mixed outcomes
            # (some jobs succeeded, some failed). Currently any failure marks the
            # entire batch FAILED, even if 99/100 succeeded. The response includes
            # completed/failed counts so clients can distinguish, but the status
            # itself doesn't reflect partial success.
            final_status = BatchStatus.COMPLETED if failed == 0 else BatchStatus.FAILED
            try:
                update_batch_status(
                    batch_id,
                    status=final_status,
                    condition_expression=f"{DocumentBatches.BATCH_STATUS} = :expected",
                    condition_values={":expected": BatchStatus.PROCESSING.value},
                )
                current_batch_status = final_status.value
                logger.info(
                    "Batch status updated",
                    extra={
                        "batch_id": batch_id,
                        "status": current_batch_status,
                        "completed": completed,
                        "failed": failed,
                    },
                )
            except Exception:
                # Another poller already updated - re-read current status
                refreshed = get_batch(batch_id)
                if refreshed:
                    current_batch_status = refreshed.get(DocumentBatches.BATCH_STATUS)

        classified = sum(1 for j in jobs if ProcessStatus.is_classified(j.job_status))

        return BatchStatusResponse(
            batch_id=batch_id,
            batch_status=current_batch_status,
            total_jobs=len(jobs),
            completed=completed,
            in_progress=len(jobs) - classified,
            failed=failed,
            created_at=batch.get(DocumentBatches.CREATED_AT),
            category=batch.get(DocumentBatches.CATEGORY),
            jobs=jobs,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error retrieving batch status", extra={"batch_id": batch_id})
        raise HTTPException(status_code=500, detail="Failed to retrieve batch") from e
