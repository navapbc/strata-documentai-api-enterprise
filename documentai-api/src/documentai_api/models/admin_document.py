"""Response models for admin documents endpoints."""

from typing import Any

from documentai_api.models.base import BaseApiResponse


class DocumentListItem(BaseApiResponse):
    job_id: str
    file_name: str
    tenant_id: str
    api_key_name: str
    process_status: str
    document_category: str
    matched_blueprint: str
    created_at: str
    processed_date: str


class DocumentListResponse(BaseApiResponse):
    documents: list[DocumentListItem]
    count: int
    next_cursor: str | None = None


class DocumentDetail(BaseApiResponse):
    job_id: str
    file_name: str
    tenant_id: str
    api_key_name: str
    process_status: str
    document_category: str
    matched_blueprint: str
    matched_blueprint_confidence: float | None = None
    matched_document_class: str
    created_at: str
    processed_date: str
    error_message: str | None = None
    content_type: str
    file_size_bytes: int | None = None
    pages_detected: int | None = None
    total_processing_time_seconds: float | None = None
    bda_processing_time_seconds: float | None = None
    bda_region_used: str
    retry_count: int = 0
    field_confidence_scores: list[dict[str, Any]] | dict[str, Any] | None = None
    external_document_id: str
    batch_id: str
    fields: dict[str, Any] | None = None


class DocumentPreviewResponse(BaseApiResponse):
    url: str
    content_type: str
    expires_in: int
