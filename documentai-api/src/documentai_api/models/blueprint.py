"""Response models for blueprint endpoints."""

from typing import Any

from pydantic import Field

from documentai_api.config.constants import BlueprintStatus, BlueprintTestStatus
from documentai_api.models.base import BaseApiResponse


class BlueprintField(BaseApiResponse):
    name: str
    field_type: str
    description: str


class BlueprintItem(BaseApiResponse):
    blueprint_id: str
    tenant_id: str
    name: str
    description: str
    document_type: str
    fields: list[BlueprintField]
    status: BlueprintStatus
    blueprint_arn: str | None = None
    project_arn: str | None = None
    created_at: str
    updated_at: str


class BlueprintListResponse(BaseApiResponse):
    blueprints: list[BlueprintItem]


class BlueprintCreateRequest(BaseApiResponse):
    name: str
    description: str
    document_type: str
    fields: list[BlueprintField]


class BlueprintUpdateRequest(BaseApiResponse):
    name: str | None = None
    description: str | None = None
    document_type: str | None = None
    fields: list[BlueprintField] | None = None


class BlueprintTestRequest(BaseApiResponse):
    document_category: str
    tenant_id: str | None = None


class BlueprintPublishResponse(BaseApiResponse):
    blueprint_id: str
    blueprint_arn: str
    project_arn: str
    message: str


class BlueprintLiveResponse(BaseApiResponse):
    blueprint_id: str
    document_type: str
    message: str


class BlueprintDeleteResponse(BaseApiResponse):
    message: str


class BlueprintTestStartResponse(BaseApiResponse):
    test_id: str
    status: BlueprintTestStatus = BlueprintTestStatus.PROCESSING


class BlueprintTestResult(BaseApiResponse):
    test_id: str
    status: BlueprintTestStatus
    document_type: str | None = None
    matched_blueprint: str | None = None
    matched_confidence: float | None = None
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    field_confidences: dict[str, float] = Field(default_factory=dict)
    filtered_fields: dict[str, Any] = Field(default_factory=dict)
    missing_required_fields: list[str] = Field(default_factory=list)
    has_rules: bool = False
    error: str | None = None
