from documentai_api.models.base import BaseApiResponse


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
