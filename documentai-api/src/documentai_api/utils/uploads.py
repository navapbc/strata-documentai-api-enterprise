"""Shared helpers used by single-file and batch upload endpoints."""

import asyncio
import os
from io import BytesIO
from typing import BinaryIO

import filetype  # type: ignore[import-untyped]
from fastapi import HTTPException, UploadFile

from documentai_api.config.constants import (
    DocumentCategory,
    FileValidation,
    S3MetadataKeys,
)
from documentai_api.config.env import EnvVars
from documentai_api.logging import get_logger
from documentai_api.services import s3 as s3_service
from documentai_api.utils.image_conversion import convert_to_png
from documentai_api.utils.s3 import get_bucket_and_key, parse_s3_uri

logger = get_logger(__name__)


class ImageConversionError(Exception):
    """Raised when image format conversion fails."""


def purge_document_s3_artifacts(object_key: str, tenant_id: str) -> list[str]:
    """Remove every S3 copy of a document, used by hard delete.

    Covers all three locations a document's bytes can land in: the original
    upload (input), the preprocessing copies, and the BDA output tree. Attempts
    all three regardless of individual failures (so one error doesn't strand the
    rest), and returns the names of any locations that could NOT be purged.

    The caller treats a non-empty return as a failed hard delete: an empty list
    means every artifact is confirmed gone. Note that S3 deletes are idempotent -
    a missing object is a success, not a failure - so a non-empty result reflects
    a real error (permissions, throttling, etc.), not "nothing to delete".
    """
    failures: list[str] = []

    # 1. Original upload: {input}/{tenant}/{object_key}
    input_location = os.environ.get(EnvVars.DOCUMENTAI_INPUT_LOCATION)
    if input_location:
        try:
            bucket, key = get_bucket_and_key(input_location, tenant_id, object_key)
            s3_service.delete_object(bucket, key)
        except Exception as e:
            logger.warning(f"Failed to delete input object for {object_key}: {e}")
            failures.append("input")

    # 2. Preprocessing copies, both tenant-scoped: the upload-time original at
    #    {preprocessing}/{tenant}/{object_key} and the pre-crop original at
    #    {preprocessing}/{tenant}/precrop/{object_key}.
    preprocessing_location = os.environ.get(EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION)
    if preprocessing_location:
        try:
            bucket, _ = parse_s3_uri(preprocessing_location)
            for subpath in ("", "precrop"):
                _, key = get_bucket_and_key(preprocessing_location, tenant_id, object_key, subpath)
                s3_service.delete_object(bucket, key)
        except Exception as e:
            logger.warning(f"Failed to delete preprocessing object for {object_key}: {e}")
            failures.append("preprocessing")

    # 3. BDA output tree: {output}/{input_key}/{invocation_id}/... A recursive
    #    prefix delete of the doc's output root removes everything BDA wrote -
    #    standard output, custom output, and job_metadata.json. input_key is the
    #    object_key, or the "_truncated" variant for oversized docs (see
    #    bda_invoker), so purge both candidate roots.
    output_location = os.environ.get(EnvVars.DOCUMENTAI_OUTPUT_LOCATION)
    if output_location:
        try:
            bucket, prefix = parse_s3_uri(output_location)
            base, ext = os.path.splitext(object_key)
            for name in (object_key, f"{base}_truncated{ext}"):
                out_prefix = f"{prefix}/{name}/" if prefix else f"{name}/"
                s3_service.delete_prefix(bucket, out_prefix)
        except Exception as e:
            logger.warning(f"Failed to delete output objects for {object_key}: {e}")
            failures.append("output")

    return failures


def generate_unique_filename(filename: str, job_id: str) -> str:
    """Generate a unique filename embedding the job_id."""
    if not filename:
        raise ValueError("Invalid filename")
    # Strip path components to prevent traversal or unintended S3 prefixes
    filename = os.path.basename(filename)
    name, ext = os.path.splitext(filename)
    return f"{name}-{job_id}{ext}"


async def validate_file_type(file: UploadFile) -> str:
    """Detect MIME type from file header bytes, verify it's supported, reset pointer.

    Only reads the first 2048 bytes for detection (filetype needs ~261).

    Returns the detected content type string.

    Raises:
        HTTPException 400: if the type isn't in FileValidation.SUPPORTED_CONTENT_TYPES.
    """
    header_bytes = await file.read(2048)
    actual_content_type = filetype.guess_mime(header_bytes) or "application/octet-stream"
    await file.seek(0)

    if not FileValidation.is_supported(actual_content_type):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid file type detected '{actual_content_type}'"
                + (f" for '{file.filename}'" if file.filename else "")
                + f". File must be {', '.join(FileValidation.SUPPORTED_CONTENT_TYPES)}"
            ),
        )

    return actual_content_type


async def validate_upload(file: UploadFile) -> str:
    """Full upload validation: filename, MIME detection, mismatch warning.

    Returns the detected content type string.

    Raises:
        HTTPException 400: if filename is missing or type isn't supported.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    actual_content_type = await validate_file_type(file)

    if file.content_type and file.content_type != actual_content_type:
        logger.warning(
            f"MIME mismatch: declared={file.content_type} detected={actual_content_type} file={file.filename}"
        )

    return actual_content_type


def _save_original_to_preprocessing(
    file_bytes: bytes, object_key: str, content_type: str, tenant_id: str | None = None
) -> None:
    """Save original file to preprocessing location for audit trail.

    Stored under the owning tenant's prefix (mirroring the input layout) so
    preprocessing artifacts are tenant-scoped. ``object_key`` is the bare file
    name; the tenant prefix is added here.
    """
    preprocessing_location = os.environ.get(EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION)
    if not preprocessing_location:
        return

    bucket, key = get_bucket_and_key(preprocessing_location, tenant_id, object_key)

    try:
        s3_service.upload_file(bucket, key, BytesIO(file_bytes), content_type)
        logger.info(f"Original file saved to preprocessing: {key}")
    except Exception as e:
        logger.warning(f"Failed to save original to preprocessing: {e}")


async def dispatch_upload(
    *,
    src_file: BinaryIO,
    dest_path: str,
    original_file_name: str,
    content_type: str,
    category: DocumentCategory | None,
    job_id: str,
    trace_id: str,
    ddb_key: str,
    tenant_id: str | None = None,
) -> None:
    """Upload file to S3. Classifies DDB record on failure."""
    from documentai_api.utils.document_lifecycle import (
        classify_as_conversion_failed,
        classify_as_failed,
    )
    from documentai_api.utils.dto import ClassificationData

    try:
        await upload_document_for_processing(
            src_file=src_file,
            dest_path=dest_path,
            original_file_name=original_file_name,
            content_type=content_type,
            user_provided_document_category=category,
            job_id=job_id,
            trace_id=trace_id,
            tenant_id=tenant_id,
        )
    except ImageConversionError as e:
        await asyncio.to_thread(
            classify_as_conversion_failed, object_key=ddb_key, error_message=str(e)
        )
        raise
    except HTTPException as e:
        await asyncio.to_thread(
            classify_as_failed,
            object_key=ddb_key,
            error_message=e.detail,
            data=ClassificationData(additional_info=e.detail),
        )
        raise
    except Exception as e:
        logger.exception(f"Unexpected upload failure for job {job_id}")
        await asyncio.to_thread(
            classify_as_failed,
            object_key=ddb_key,
            error_message=str(e),
            data=ClassificationData(additional_info=f"Unexpected error: {e}"),
        )
        raise HTTPException(status_code=500, detail="Upload failed") from e


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
    tenant_id: str | None = None,
) -> None:
    """Upload a document file to S3 with traceability metadata.

    If the file requires format conversion (HEIC, WebP, GIF, BMP), the original
    is saved to the preprocessing location and a converted PNG is uploaded to the
    destination path.
    """
    bucket_name, object_key = parse_s3_uri(dest_path)

    # handle format conversion for mobile/unsupported-by-BDA formats
    if FileValidation.needs_conversion(content_type):
        file_bytes = await asyncio.to_thread(src_file.read)
        logger.info(
            f"Converting {content_type} to PNG",
            extra={"upload_filename": original_file_name, "original_size_bytes": len(file_bytes)},
        )

        _save_original_to_preprocessing(
            file_bytes, os.path.basename(object_key), content_type, tenant_id=tenant_id
        )

        try:
            converted_bytes = await asyncio.to_thread(convert_to_png, file_bytes, content_type)
        except ValueError as e:
            raise ImageConversionError(str(e)) from e

        src_file = BytesIO(converted_bytes)
        content_type = "image/png"

    try:
        metadata = {}
        if user_provided_document_category:
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
            "S3: Starting upload",
            extra={"metadata": metadata, "dest_path": dest_path},
        )

        s3_service.upload_file(bucket_name, object_key, src_file, content_type, metadata)
        logger.info("=== S3 UPLOAD SUCCESS ===")

    except Exception as e:
        logger.error(f"Error uploading file to S3: {e}")
        raise HTTPException(
            status_code=500,
            detail="Document upload failed",
        ) from e
