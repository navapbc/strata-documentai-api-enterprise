from typing import Any

from pydantic import Field

from documentai_api.models.base import BaseApiResponse


class EvalFieldResult(BaseApiResponse):
    value: Any = None
    confidence: float | None = None


class EvalSubmitResponse(BaseApiResponse):
    job_id: str


class EvalResponse(BaseApiResponse):
    job_id: str
    bda: dict[str, EvalFieldResult] = Field(default_factory=dict)
    llm: dict[str, EvalFieldResult] = Field(default_factory=dict)
