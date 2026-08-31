from documentai_api.models.base import BaseApiResponse


class PresignedUploadResponse(BaseApiResponse):
    upload_url: str
    method: str = "POST"
    fields: dict[str, str]
    job_id: str
    expires_in: int
    max_size_bytes: int
