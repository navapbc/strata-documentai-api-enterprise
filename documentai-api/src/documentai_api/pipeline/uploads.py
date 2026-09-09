"""Upload orchestration - handles classification on failure."""

import asyncio
from typing import BinaryIO

from fastapi import HTTPException

from documentai_api.classifiers.document_classification import (
    classify_as_conversion_failed,
    classify_as_failed,
)
from documentai_api.dtos.classification import ClassificationData
from documentai_api.logging import get_logger
from documentai_api.utils.uploads import ImageConversionError, upload_document_for_processing

logger = get_logger(__name__)


async def dispatch_upload(
    *,
    src_file: BinaryIO,
    dest_path: str,
    original_file_name: str,
    content_type: str,
    category: str | None,
    job_id: str,
    trace_id: str,
    ddb_key: str,
    tenant_id: str | None = None,
) -> None:
    """Upload file to S3. Classifies DDB record on failure."""
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
