from documentai_api.models.base import BaseApiResponse


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
