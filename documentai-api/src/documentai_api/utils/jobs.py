"""Job status utilities."""

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from documentai_api.config.constants import ProcessStatus
from documentai_api.logging import get_logger
from documentai_api.models.api_responses import JobStatusResponse
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.ddb import get_ddb_by_job_id
from documentai_api.utils.document_lifecycle import classify_as_failed
from documentai_api.utils.dto import ClassificationData
from documentai_api.utils.response_builder import build_v1_api_response

logger = get_logger(__name__)


@dataclass
class JobStatus:
    """Job status data from DDB."""

    ddb_record: dict[str, Any] | None
    object_key: str | None
    process_status: str | None
    v1_response_json: str | None


def get_job_status(job_id: str) -> JobStatus:
    """Get job status from DDB."""
    ddb_record = get_ddb_by_job_id(job_id)

    if not ddb_record:
        return JobStatus(None, None, None, None)

    object_key = ddb_record.get(DocumentMetadata.FILE_NAME)
    process_status = ddb_record.get(DocumentMetadata.PROCESS_STATUS)
    v1_response = ddb_record.get(DocumentMetadata.V1_API_RESPONSE_JSON)

    return JobStatus(ddb_record, object_key, process_status, v1_response)


async def poll_for_completion(
    job_id: str,
    timeout: int,
    request: Any = None,
    include_extracted_data: bool = False,
    include_bounding_box: bool = False,
) -> JobStatusResponse:
    """Poll for document processing completion with timeout."""
    elapsed_time = 0
    object_key = None
    polling_interval = 5

    while elapsed_time < timeout:
        # Stop polling if client disconnected
        if request and await request.is_disconnected():
            logger.info(f"Client disconnected while polling job {job_id}")
            break

        try:
            job_status = get_job_status(job_id)

            if job_status.object_key:
                object_key = job_status.object_key

            if (
                job_status.process_status
                and ProcessStatus.is_completed(job_status.process_status)
                and job_status.v1_response_json
            ):
                if include_extracted_data and job_status.object_key:
                    result = build_v1_api_response(
                        object_key=job_status.object_key,
                        job_status=job_status.process_status,
                        include_extracted_data=True,
                        include_bounding_box=include_bounding_box,
                    )
                    return JobStatusResponse.from_v1(result)
                return JobStatusResponse.from_v1(json.loads(job_status.v1_response_json))

            await asyncio.sleep(polling_interval)
            elapsed_time += polling_interval

        except Exception as e:
            logger.error(f"Error polling DynamoDB for job {job_id}: {e}")
            await asyncio.sleep(polling_interval)
            elapsed_time += polling_interval

    if object_key:
        classify_as_failed(
            object_key=object_key,
            error_message="Processing timeout",
            data=ClassificationData(
                additional_info=f"Processing did not complete within {timeout} seconds"
            ),
        )

    return JobStatusResponse(
        job_id=job_id,
        job_status=ProcessStatus.FAILED.value,
        message=f"Processing timeout after {timeout} seconds",
    )
