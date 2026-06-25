# TODO: Split this file into domain-specific modules (e.g. api_responses_batch.py,
# api_responses_documents.py) once it grows further. Keeping in one file for now
# for discoverability.

from typing import Any

from pydantic import AwareDatetime

from documentai_api.models.base import BaseApiResponse


class UploadAsyncResponse(BaseApiResponse):
    job_id: str
    job_status: str
    message: str


class JobStatusResponse(BaseApiResponse):
    job_id: str
    job_status: str
    message: str
    created_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    total_processing_time_seconds: float | None = None
    matched_document_class: str | None = None
    fields: dict[str, Any] | None = None
    error: str | None = None
    additional_info: str | None = None

    @classmethod
    def from_v1(cls, v1_response: dict[str, Any]) -> "JobStatusResponse":
        """Construct from a stored/built v1 response dict, applying presentation nesting."""
        from documentai_api.utils.response_builder import present_v1_response

        return cls(**present_v1_response(v1_response))


class HealthResponse(BaseApiResponse):
    message: str


class ConfigResponse(BaseApiResponse):
    api_url: str
    version: str
    image_tag: str | None
    environment: str
    endpoints: dict[str, str]
    supported_file_types: list[str]


class BuildCreatedResponse(BaseApiResponse):
    build_id: str
    message: str


class BuildPageUploadResponse(BaseApiResponse):
    build_id: str
    page_number: int
    file_name: str | None = None
    message: str


class BuildPageBatchItem(BaseApiResponse):
    page_number: int
    file_name: str | None = None


class BuildPagesBatchResponse(BaseApiResponse):
    build_id: str
    pages_added: int
    pages: list[BuildPageBatchItem]
    message: str


class BuildSubmitAsyncResponse(BaseApiResponse):
    job_id: str
    build_id: str
    job_status: str
    message: str
    page_count: int


class BuildPageItem(BaseApiResponse):
    page_number: int
    original_file_name: str | None = None
    created_at: str | None = None
    category: str | None = None


class BuildDetailsResponse(BaseApiResponse):
    build_id: str
    build_status: str
    page_count: int
    pages: list[BuildPageItem]


class DocumentSearchRequest(BaseApiResponse):
    job_ids: list[str]
    include_extracted_data: bool = False


class DocumentSearchResponse(BaseApiResponse):
    results: list[JobStatusResponse]


class PresignedUploadResponse(BaseApiResponse):
    upload_url: str
    method: str = "POST"
    fields: dict[str, str]
    job_id: str
    expires_in: int
    max_size_bytes: int


# =============================================================================
# Batch responses
# =============================================================================


class BatchJobItem(BaseApiResponse):
    file_name: str
    job_id: str
    batch_position: int


class BatchUploadResponse(BaseApiResponse):
    batch_id: str
    batch_status: str
    total_files: int
    created_at: str
    jobs: list[BatchJobItem]


class BatchStatusJobItem(BaseApiResponse):
    file_name: str | None
    job_id: str | None
    job_status: str


class BatchStatusResponse(BaseApiResponse):
    batch_id: str
    batch_status: str
    total_jobs: int
    completed: int
    in_progress: int
    failed: int
    created_at: str | None
    category: str | None
    jobs: list[BatchStatusJobItem]
