"""Request and response models for tenant endpoints."""

from typing import Annotated

from pydantic import StringConstraints

from documentai_api.models.base import BaseApiResponse

TenantIdStr = Annotated[
    str, StringConstraints(pattern=r"^[a-z0-9-]+$", min_length=1, max_length=128)
]
DisplayNameStr = Annotated[str, StringConstraints(min_length=1, max_length=255)]


class CreateTenantRequest(BaseApiResponse):
    tenant_id: TenantIdStr
    display_name: DisplayNameStr
    primary_contact: str | None = None


class UpdateTenantRequest(BaseApiResponse):
    display_name: DisplayNameStr | None = None
    primary_contact: str | None = None
    is_active: bool | None = None


class TenantItem(BaseApiResponse):
    tenant_id: str
    display_name: str
    primary_contact: str | None = None
    is_active: bool = True
    created_at: str | None = None
    updated_at: str | None = None


class ListTenantsResponse(BaseApiResponse):
    tenants: list[TenantItem]
    count: int


class DeleteTenantResponse(BaseApiResponse):
    deleted: bool
    tenant_id: str
