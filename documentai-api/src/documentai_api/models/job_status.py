from typing import Any, Self

from pydantic import AwareDatetime, model_validator

from documentai_api.constants.api import V1JobStatus
from documentai_api.constants.processing import ProcessStatus
from documentai_api.models.base import BaseApiResponse
from documentai_api.utils.response_builder import present_v1_response


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
    response_code: str | None = None
    response_message: str | None = None
    missing_required_field_list: list[str] | None = None
    below_extraction_confidence_floor: bool | None = None
    user_provided_document_category: str | None = None
    is_completed: bool = False
    is_failed: bool = False
    inferred_document_type: str | None = None

    @model_validator(mode="after")
    def _set_completion_flags(self) -> Self:
        # job_status in v1 API responses uses "completed" rather than the internal
        # ProcessStatus values — treat it as terminal.
        self.is_completed = (
            ProcessStatus.is_completed(self.job_status) or self.job_status == V1JobStatus.COMPLETED
        )
        self.is_failed = self.job_status == ProcessStatus.FAILED
        return self

    @classmethod
    def from_v1(cls, v1_response: dict[str, Any]) -> Self:
        """Construct from a stored/built v1 response dict, applying presentation nesting."""
        return cls(**present_v1_response(v1_response))


class DocumentSearchRequest(BaseApiResponse):
    job_ids: list[str]
    include_extracted_data: bool = False


class DocumentSearchResponse(BaseApiResponse):
    results: list[JobStatusResponse]
