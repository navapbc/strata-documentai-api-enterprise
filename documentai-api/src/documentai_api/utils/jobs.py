"""Job status utilities."""

from dataclasses import dataclass
from typing import Any

from documentai_api.logging import get_logger
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.ddb import get_ddb_by_job_id

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
