"""Document record model for initial DDB tracking records."""

from pydantic import BaseModel

from documentai_api.config.constants import ProcessStatus


class DocumentRecord(BaseModel):
    """Initial tracking record created at upload time.

    Encapsulates all fields written by insert_minimal_ddb_record.
    Adding a new field is a one-line change here instead of touching every call site.
    """

    ddb_key: str
    original_file_name: str
    job_id: str
    upload_method: str
    upload_source: str | None = None
    tenant_id: str
    api_key_name: str
    process_status: ProcessStatus = ProcessStatus.NOT_STARTED
    category: str | None = None
    trace_id: str | None = None
    batch_id: str | None = None
    content_type: str | None = None
    file_size_bytes: int | None = None
    external_document_id: str | None = None
    external_system_id: str | None = None
    ai_consent_flag: bool | None = None
    is_demo: bool = False
    ttl_days: int | None = None  # override default TTL (e.g. 3 for demo)
