"""Admin tenants router — CRUD for tenant management."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from documentai_api.annotations import SuperAdminClaims, verify_jwt_with_super_admin
from documentai_api.logging import get_logger
from documentai_api.models.tenants import (
    CreateTenantRequest,
    DeleteTenantResponse,
    ListTenantsResponse,
    TenantItem,
    UpdateTenantRequest,
)
from documentai_api.schemas.tenants import TenantRecord
from documentai_api.utils import tenants as tenants_util

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/admin/tenants",
    tags=["admin-tenants"],
    # Tenant CRUD is super-admin only — tenant-admins must not edit other tenants.
    dependencies=[Depends(verify_jwt_with_super_admin)],
)


def _to_item(record: dict[str, Any]) -> TenantItem:
    return TenantItem(
        tenant_id=record.get(TenantRecord.TENANT_ID, ""),
        display_name=record.get(TenantRecord.DISPLAY_NAME, ""),
        primary_contact=record.get(TenantRecord.PRIMARY_CONTACT),
        is_active=record.get(TenantRecord.IS_ACTIVE, True),
        created_at=record.get(TenantRecord.CREATED_AT),
        updated_at=record.get(TenantRecord.UPDATED_AT),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: CreateTenantRequest,
    claims: SuperAdminClaims,
) -> TenantItem:
    """Create a new tenant."""
    try:
        record = tenants_util.create_tenant(
            tenant_id=body.tenant_id,
            display_name=body.display_name,
            primary_contact=body.primary_contact,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e

    return _to_item(record)


@router.get("")
async def list_tenants(
    claims: SuperAdminClaims,
    active_only: bool = True,
) -> ListTenantsResponse:
    """List all tenants."""
    records = tenants_util.list_tenants(active_only=active_only)
    items = [_to_item(r) for r in records]
    return ListTenantsResponse(tenants=items, count=len(items))


@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    claims: SuperAdminClaims,
) -> TenantItem:
    """Get a single tenant by ID."""
    record = tenants_util.get_tenant(tenant_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return _to_item(record)


@router.patch("/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    body: UpdateTenantRequest,
    claims: SuperAdminClaims,
) -> TenantItem:
    """Update a tenant's metadata."""
    try:
        updated = tenants_util.update_tenant(
            tenant_id,
            display_name=body.display_name,
            primary_contact=body.primary_contact,
            is_active=body.is_active,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from e

    return _to_item(updated)


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    claims: SuperAdminClaims,
) -> DeleteTenantResponse:
    """Deactivate a tenant (soft delete)."""
    if not tenants_util.deactivate_tenant(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return DeleteTenantResponse(deleted=True, tenant_id=tenant_id)
