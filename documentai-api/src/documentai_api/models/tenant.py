"""Request and response models for tenant endpoints."""

from typing import Annotated

from pydantic import Field, StringConstraints

from documentai_api.annotations import RequestLimit
from documentai_api.models.base import BaseApiResponse

TenantIdStr = Annotated[
    str, StringConstraints(pattern=r"^[a-z0-9-]+$", min_length=1, max_length=128)
]
DisplayNameStr = Annotated[str, StringConstraints(min_length=1, max_length=255)]
ConfidenceFloor = Annotated[
    float,
    Field(
        ge=0.0,
        le=1.0,
        description=(
            "Minimum average non-empty field confidence (0.0-1.0) below which an "
            "extraction is flagged. When null, the platform default applies."
        ),
    ),
]


class CreateTenantRequest(BaseApiResponse):
    tenant_id: TenantIdStr
    display_name: DisplayNameStr
    primary_contact: str | None = None
    extraction_confidence_floor: ConfidenceFloor | None = None
    max_requests_per_day: RequestLimit | None = None
    max_requests_per_month: RequestLimit | None = None


class UpdateTenantRequest(BaseApiResponse):
    display_name: DisplayNameStr | None = None
    primary_contact: str | None = None
    is_active: bool | None = None
    extraction_confidence_floor: ConfidenceFloor | None = None
    max_requests_per_day: RequestLimit | None = None
    max_requests_per_month: RequestLimit | None = None


class TenantItem(BaseApiResponse):
    tenant_id: str
    display_name: str
    primary_contact: str | None = None
    is_active: bool = True
    extraction_confidence_floor: float | None = Field(
        default=None,
        description=(
            "Tenant override for the extraction confidence floor (0.0-1.0). "
            "Null means no override is set and the platform default applies."
        ),
    )
    max_requests_per_day: int | None = None
    max_requests_per_month: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ListTenantsResponse(BaseApiResponse):
    tenants: list[TenantItem]
    count: int


class DeleteTenantResponse(BaseApiResponse):
    deleted: bool
    tenant_id: str


class TenantRequestCountItem(BaseApiResponse):
    date: str
    count: int


class TenantRequestCountsResponse(BaseApiResponse):
    tenant_id: str
    month: str
    monthly_total: int
    daily: list[TenantRequestCountItem]
