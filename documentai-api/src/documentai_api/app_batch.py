"""Batch upload endpoints.

Three routes:
- POST /v1/documents/batch       — multi-file upload
- POST /v1/documents/batch/zip   — ZIP archive upload
- GET  /v1/batches/{batch_id}    — aggregate status with per-job list
"""

import uuid
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Header,
    HTTPException,
    Response,
    UploadFile,
)

from documentai_api.config.constants import (
    MAX_BATCH_SIZE,
    BatchStatus,
    DocumentCategory,
    ProcessStatus,
)
from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.schemas.document_batches import DocumentBatches
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.auth import verify_api_key
from documentai_api.utils.ddb import (
    classify_as_ai_consent_declined,
    classify_as_failed,
    create_batch,
    get_batch,
    insert_minimal_ddb_record,
    query_jobs_by_batch_id,
    update_batch_status,
)
from documentai_api.utils.models import ClassificationData
from documentai_api.utils.uploads import upload_document_for_processing, validate_file_type
from documentai_api.utils.zip import extract_files_from_zip

logger = get_logger(__name__)

router = APIRouter()


def validate_batch_id(batch_id: str) -> None:
    """Reject duplicate batch IDs. Raises 409 if the batch already exists."""
    if get_batch(batch_id) is not None:
        raise HTTPException(status_code=409, detail="Batch ID already exists")


async def _process_batch_files(
    files: list[UploadFile],
    batch_id: str,
    category: DocumentCategory | None,
    trace_id: str,
    external_document_id: str | None = None,
    external_system_id: str | None = None,
    ai_consent_flag: bool | None = None,
) -> list[dict[str, Any]]:
    """Upload each file in a batch to S3, return per-file job info."""
    jobs: list[dict[str, Any]] = []

    input_location = get_aws_config().documentai_input_location
    if not input_location:
        raise HTTPException(
            status_code=500, detail="DOCUMENTAI_INPUT_LOCATION environment variable not set"
        )

    for idx, file in enumerate(files):
        if not file.filename:
            raise HTTPException(
                status_code=400, detail=f"Filename is required (file at position {idx})"
            )

        actual_content_type = await validate_file_type(file)
        job_id = str(uuid.uuid4())
        file_extension = file.filename.split(".")[-1]
        file_name = file.filename.split(".")[0]
        # Position-prefix keeps batch members ordered in S3 listings; job_id keeps
        # filename ↔ DDB record correlated.
        unique_file_name = f"{idx}-{file_name}-{job_id}.{file_extension}"
        ddb_key = unique_file_name
        dest_path = f"{input_location}/{unique_file_name}"

        insert_minimal_ddb_record(
            ddb_key=ddb_key,
            original_file_name=file.filename,
            job_id=job_id,
            user_provided_document_category=category,
            trace_id=trace_id,
            batch_id=batch_id,
            content_type=actual_content_type,
            external_document_id=external_document_id,
            external_system_id=external_system_id,
            ai_consent_flag=ai_consent_flag,
        )

        if ai_consent_flag is False:
            classify_as_ai_consent_declined(object_key=ddb_key)
            jobs.append({"fileName": file.filename, "jobId": job_id, "batchPosition": idx})
            continue

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
            )
        except HTTPException as e:
            classify_as_failed(
                object_key=ddb_key,
                error_message=e.detail,
                data=ClassificationData(additional_info=e.detail),
            )
            raise

        jobs.append({"fileName": file.filename, "jobId": job_id, "batchPosition": idx})

    return jobs


@router.post("/v1/documents/batch", dependencies=[Depends(verify_api_key)], name="batchUpload")
async def upload_document_batch(
    response: Response,
    files: Annotated[list[UploadFile], Form(description="Documents to process")],
    batch_id: Annotated[str | None, Form()] = None,
    category: Annotated[DocumentCategory | None, Form()] = None,
    trace_id: Annotated[str | None, Header(alias="X-Trace-ID")] = None,
    external_document_id: Annotated[
        str | None, Form(description="External document identifier")
    ] = None,
    external_system_id: Annotated[
        str | None, Form(description="External system identifier")
    ] = None,
    ai_consent_flag: Annotated[bool | None, Form(description="AI consent flag")] = None,
) -> dict[str, Any]:
    """Upload multiple documents as a single batch."""
    if not trace_id:
        trace_id = str(uuid.uuid4())
    if not batch_id:
        batch_id = str(uuid.uuid4())
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size exceeds maximum of {MAX_BATCH_SIZE} files",
        )

    validate_batch_id(batch_id)

    try:
        create_batch(batch_id, len(files), category, status=BatchStatus.UPLOADING)
        jobs = await _process_batch_files(
            files=files,
            batch_id=batch_id,
            category=category,
            trace_id=trace_id,
            external_document_id=external_document_id,
            external_system_id=external_system_id,
            ai_consent_flag=ai_consent_flag,
        )
        update_batch_status(batch_id, status=BatchStatus.PROCESSING)

        response.headers["X-Trace-ID"] = trace_id
        batch_record = get_batch(batch_id)
        return {
            "batchId": batch_id,
            "batchStatus": BatchStatus.PROCESSING.value,
            "totalFiles": len(files),
            "createdAt": batch_record.get(DocumentBatches.CREATED_AT) if batch_record else None,
            "jobs": jobs,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading batch: {e}")
        update_batch_status(batch_id, status=BatchStatus.FAILED, error_message=str(e))
        raise HTTPException(status_code=500, detail="Failed to upload batch") from e


@router.post(
    "/v1/documents/batch/zip",
    dependencies=[Depends(verify_api_key)],
    name="batchUploadZip",
)
async def upload_zip_batch(
    response: Response,
    zip_file: Annotated[UploadFile, Form(description="ZIP file containing documents")],
    batch_id: Annotated[str | None, Form()] = None,
    category: Annotated[DocumentCategory | None, Form()] = None,
    trace_id: Annotated[str | None, Header(alias="X-Trace-ID")] = None,
    external_document_id: Annotated[
        str | None, Form(description="External document identifier")
    ] = None,
    external_system_id: Annotated[
        str | None, Form(description="External system identifier")
    ] = None,
    ai_consent_flag: Annotated[bool | None, Form(description="AI consent flag")] = None,
) -> dict[str, Any]:
    """Upload a ZIP archive of documents as a single batch."""
    if not trace_id:
        trace_id = str(uuid.uuid4())
    if not batch_id:
        batch_id = str(uuid.uuid4())

    validate_batch_id(batch_id)

    try:
        files = await extract_files_from_zip(zip_file)
        if not files:
            raise HTTPException(status_code=400, detail="No valid files found in zip")
        if len(files) > MAX_BATCH_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Batch size exceeds maximum of {MAX_BATCH_SIZE} files",
            )

        create_batch(batch_id, len(files), category, status=BatchStatus.UPLOADING)
        jobs = await _process_batch_files(
            files=files,
            batch_id=batch_id,
            category=category,
            trace_id=trace_id,
            external_document_id=external_document_id,
            external_system_id=external_system_id,
            ai_consent_flag=ai_consent_flag,
        )
        update_batch_status(batch_id, status=BatchStatus.PROCESSING)

        response.headers["X-Trace-ID"] = trace_id
        batch_record = get_batch(batch_id)
        return {
            "batchId": batch_id,
            "batchStatus": BatchStatus.PROCESSING.value,
            "totalFiles": len(files),
            "createdAt": batch_record.get(DocumentBatches.CREATED_AT) if batch_record else None,
            "jobs": jobs,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading zip batch: {e}")
        update_batch_status(batch_id, status=BatchStatus.FAILED, error_message=str(e))
        raise HTTPException(status_code=500, detail="Failed to upload zip batch") from e


@router.get(
    "/v1/batches/{batch_id}",
    dependencies=[Depends(verify_api_key)],
    name="batchUploadStatus",
)
async def get_batch_status(batch_id: str) -> dict[str, Any]:
    """Get status of all documents in a batch.

    Batch completion is lazily evaluated: when all jobs are complete this endpoint
    updates the batch status to COMPLETED. For real-time updates use DDB Streams
    or EventBridge.
    """
    try:
        batch = get_batch(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

        job_records = query_jobs_by_batch_id(batch_id)
        jobs = [
            {
                "fileName": record.get(DocumentMetadata.FILE_NAME),
                "jobId": record.get(DocumentMetadata.JOB_ID),
                "jobStatus": record.get(DocumentMetadata.PROCESS_STATUS, "not_found"),
            }
            for record in job_records
        ]

        completed = sum(1 for j in jobs if ProcessStatus.is_completed(j["jobStatus"]))
        failed = sum(1 for j in jobs if j["jobStatus"] == ProcessStatus.FAILED.value)
        current_batch_status = batch.get(DocumentBatches.BATCH_STATUS)

        # Lazy completion: if all jobs are done and batch is still "processing",
        # update batch status to "completed" in DDB.
        if (
            current_batch_status == BatchStatus.PROCESSING.value
            and len(jobs) > 0
            and completed == len(jobs)
        ):
            update_batch_status(batch_id, status=BatchStatus.COMPLETED)
            current_batch_status = BatchStatus.COMPLETED.value
            logger.info(f"Batch {batch_id} marked completed ({completed}/{len(jobs)} jobs done)")

        return {
            "batchId": batch_id,
            "batchStatus": current_batch_status,
            "totalJobs": len(jobs),
            "completed": completed,
            "inProgress": len(jobs) - completed,
            "failed": failed,
            "createdAt": batch.get(DocumentBatches.CREATED_AT),
            "category": batch.get(DocumentBatches.CATEGORY),
            "jobs": jobs,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving batch {batch_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve batch") from e
