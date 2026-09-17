from documentai_api.models.base import BaseApiResponse


class CheckEntry(BaseApiResponse):
    status: str
    reason: str | None = None


class CheckResponse(BaseApiResponse):
    job_id: str
    created_at: str | None
    response_code: str | None
    response_code_description: str | None
    checks: dict[str, CheckEntry]
