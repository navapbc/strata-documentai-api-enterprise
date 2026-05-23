"""Response models for audit log endpoints."""

from typing import Any

from pydantic import Field

from documentai_api.models.base import BaseApiResponse


class AuditEventItem(BaseApiResponse):
    event_id: str
    tenant_id: str
    actor_sub: str
    actor_email: str
    action: str
    target_type: str
    target_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class AuditLogResponse(BaseApiResponse):
    events: list[AuditEventItem]
    count: int
    next_cursor: str | None = None
