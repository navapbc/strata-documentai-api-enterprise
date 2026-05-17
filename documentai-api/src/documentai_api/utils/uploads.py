"""Shared helpers used by single-file and batch upload endpoints."""

from typing import BinaryIO

import filetype  # type: ignore[import-untyped]
from fastapi import HTTPException, UploadFile

from documentai_api.config.constants import (
    DocumentCategory,
    FileValidation,
    S3MetadataKeys,
)
from documentai_api.logging import get_logger
from documentai_api.services import s3 as s3_service
from documentai_api.utils.s3 import parse_s3_uri

logger = get_logger(__name__)


async def validate_file_type(file: UploadFile) -> str:
    """Read the file, detect its MIME type, verify it's supported, reset the read pointer.

    Returns the detected content type string.

    Raises:
        HTTPException 400: if the type isn't in FileValidation.SUPPORTED_CONTENT_TYPES.
    """
    file_content = await file.read()
    actual_content_type = filetype.guess_mime(file_content) or "application/octet-stream"

    if not FileValidation.is_supported(actual_content_type):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid file type detected '{actual_content_type}'"
                + (f" for '{file.filename}'" if file.filename else "")
                + f". File must be {', '.join(FileValidation.SUPPORTED_CONTENT_TYPES)}"
            ),
        )

    file.file.seek(0)  # reset pointer for subsequent reads
    return actual_content_type


async def upload_document_for_processing(
    src_file: BinaryIO,
    dest_path: str,
    original_file_name: str,
    content_type: str,
    user_provided_document_category: DocumentCategory | None = None,
    job_id: str | None = None,
    trace_id: str | None = None,
    batch_id: str | None = None,
    build_id: str | None = None,
) -> None:
    """Upload a document file to S3 with traceability metadata.

    Sets the canonical S3 metadata keys (original filename, job_id, trace_id,
    batch_id, optional user category) so downstream Lambdas can read them off
    the S3 event without re-querying DDB.
    """
    logger.debug(
        "S3 upload started",
        extra={
            "dest_path": dest_path,
            "user_provided_document_category": user_provided_document_category,
            "category_type": type(user_provided_document_category).__name__,
        },
    )

    bucket_name, object_key = parse_s3_uri(dest_path)

    try:
        metadata = {}
        if user_provided_document_category:
            # add type check for safety
            if not isinstance(user_provided_document_category, DocumentCategory):
                raise ValueError(
                    f"Expected DocumentCategory, got {type(user_provided_document_category)}"
                )

            metadata[S3MetadataKeys.USER_PROVIDED_DOCUMENT_CATEGORY] = (
                user_provided_document_category.value
            )

        metadata[S3MetadataKeys.ORIGINAL_FILE_NAME] = original_file_name

        if job_id:
            metadata[S3MetadataKeys.JOB_ID] = job_id

        if trace_id:
            metadata[S3MetadataKeys.TRACE_ID] = trace_id

        if batch_id:
            metadata[S3MetadataKeys.BATCH_ID] = batch_id

        if build_id:
            metadata[S3MetadataKeys.BUILD_ID] = build_id

        logger.debug(
            "S3: Starting actual upload",
            extra={
                "metadata": metadata,
                "dest_path": dest_path,
            },
        )

        s3_service.upload_file(bucket_name, object_key, src_file, content_type, metadata)
        logger.info("=== S3 UPLOAD SUCCESS ===")

    except Exception as e:
        logger.error(f"Error uploading file to S3: {e}")
        logger.info(f"=== S3 UPLOAD FAILED: {e} ===")
        raise HTTPException(
            status_code=500,
            detail="Document upload failed",
        ) from e
