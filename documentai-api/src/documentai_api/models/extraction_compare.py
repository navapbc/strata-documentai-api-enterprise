from typing import Any

from pydantic import Field

from documentai_api.models.base import BaseApiResponse


class CompareFieldResult(BaseApiResponse):
    value: Any = None
    confidence: float | None = None
    geometry: list[dict[str, Any]] | None = None


class CompareSubmitResponse(BaseApiResponse):
    job_id: str


class CompareResponse(BaseApiResponse):
    job_id: str
    primary_method: str
    primary: dict[str, CompareFieldResult] = Field(default_factory=dict)
    llm: dict[str, CompareFieldResult] = Field(default_factory=dict)
    durations: dict[str, Any] = Field(default_factory=dict)
