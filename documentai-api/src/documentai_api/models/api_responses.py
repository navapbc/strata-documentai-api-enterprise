from typing import Any

from pydantic import AwareDatetime, HttpUrl

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


class HealthResponse(BaseApiResponse):
    message: str


class ConfigResponse(BaseApiResponse):
    api_url: HttpUrl
    version: str
    image_tag: str | None
    environment: str
    endpoints: dict[str, str]
    supported_file_types: list[str]


class DictionaryFieldItem(BaseApiResponse):
    document_type: str
    name: str
    type: str
    description: str


class DictionaryFieldsResponse(BaseApiResponse):
    fields: list[DictionaryFieldItem]


class DictionarySearchResponse(BaseApiResponse):
    fields: list[DictionaryFieldItem]


class DictionarySchemaListResponse(BaseApiResponse):
    schemas: list[str]


class DictionarySchemaFieldResponse(BaseApiResponse):
    name: str
    type: str
    description: str


class DictionarySchemaDetailResponse(BaseApiResponse):
    document_type: str
    fields: list[DictionarySchemaFieldResponse]


class DictionaryResponseCodeItem(BaseApiResponse):
    code: str
    message: str


class DictionaryResponseCodesResponse(BaseApiResponse):
    response_codes: list[DictionaryResponseCodeItem]


class DictionaryDocumentCategoriesResponse(BaseApiResponse):
    document_categories: list[str]


class ExtractionRuleItem(BaseApiResponse):
    tenant_id: str
    document_type: str
    required_fields: list[str]
    optional_fields: list[str]
    created_at: str
    updated_at: str


class ExtractionRulesListResponse(BaseApiResponse):
    rules: list[ExtractionRuleItem]


class ExtractionRuleDeleteResponse(BaseApiResponse):
    message: str


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
