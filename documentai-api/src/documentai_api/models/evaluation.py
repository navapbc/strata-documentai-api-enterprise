from documentai_api.models.base import BaseApiResponse


class EvaluationEntry(BaseApiResponse):
    status: str
    reason: str | None = None


class EvaluationResponse(BaseApiResponse):
    job_id: str
    created_at: str | None
    response_code: str | None
    response_code_description: str | None
    evaluations: dict[str, EvaluationEntry]
