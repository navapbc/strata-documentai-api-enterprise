"""Response models for audit log endpoints."""

from typing import Any

from pydantic import Field

from documentai_api.models.base import BaseApiResponse


class AuditEventItem(BaseApiResponse):
    """Audit event item.

    When presentation mode is active, `actor_email` is masked and `masked_tenant_id`
    is populated. The real `tenant_id` is always returned so that frontend filter
    calls continue to work - `masked_tenant_id` is for display only.
    """

    event_id: str
    tenant_id: str
    masked_tenant_id: str | None = None
    actor_sub: str
    actor_email: str
    action: str
    target_type: str
    target_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class AuditActionsResponse(BaseApiResponse):
    actions: list[str]


class AuditActorsResponse(BaseApiResponse):
    actors: list[str]


class AuditLogResponse(BaseApiResponse):
    events: list[AuditEventItem]
    count: int
    next_cursor: str | None = None
