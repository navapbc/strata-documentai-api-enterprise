"""Admin tenants router — CRUD for tenant management."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from documentai_api.annotations import AdminClaims, SuperAdminClaims, verify_jwt_with_role
from documentai_api.logging import get_logger
from documentai_api.models.tenants import (
    CreateTenantRequest,
    DeleteTenantResponse,
    ListTenantsResponse,
    TenantItem,
    UpdateTenantRequest,
)
from documentai_api.schemas.audit_event import AuditAction, AuditTargetType
from documentai_api.schemas.tenants import TenantRecord
from documentai_api.utils import tenants as tenants_util
from documentai_api.utils.audit import log_event
from documentai_api.utils.jwt_auth import is_super_admin, tenant_scope

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/admin/tenants",
    tags=["admin-tenants"],
    dependencies=[Depends(verify_jwt_with_role)],
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


def _enforce_scope(claims: dict[str, Any], tenant_id: str) -> None:
    """Raise 403 if a tenant-admin tries to access another tenant."""
    scope = tenant_scope(claims)
    if scope is not None and scope != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant.",
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

    log_event(
        claims,
        action=AuditAction.TENANT_CREATE,
        target_type=AuditTargetType.TENANT,
        target_id=body.tenant_id,
        metadata={"display_name": body.display_name, "primary_contact": body.primary_contact},
    )
    return _to_item(record)


@router.get("")
async def list_tenants(
    claims: AdminClaims,
    active_only: bool = True,
) -> ListTenantsResponse:
    """List tenants. Super-admins see all; tenant-admins see only their own."""
    scope = tenant_scope(claims)
    if scope:
        record = tenants_util.get_tenant(scope)
        items = [_to_item(record)] if record else []
    else:
        records = tenants_util.list_tenants(active_only=active_only)
        items = [_to_item(r) for r in records]
    return ListTenantsResponse(tenants=items, count=len(items))


@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    claims: AdminClaims,
) -> TenantItem:
    """Get a single tenant by ID."""
    _enforce_scope(claims, tenant_id)
    record = tenants_util.get_tenant(tenant_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return _to_item(record)


@router.patch("/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    body: UpdateTenantRequest,
    claims: AdminClaims,
) -> TenantItem:
    """Update a tenant's metadata."""
    _enforce_scope(claims, tenant_id)

    # Tenant-admins cannot change activation status
    is_active = body.is_active if is_super_admin(claims) else None

    try:
        updated = tenants_util.update_tenant(
            tenant_id,
            display_name=body.display_name,
            primary_contact=body.primary_contact,
            is_active=is_active,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from e

    log_event(
        claims,
        action=AuditAction.TENANT_UPDATE,
        target_type=AuditTargetType.TENANT,
        target_id=tenant_id,
        tenant_id=tenant_id,
        metadata={"changed_fields": [k for k, v in body.model_dump(exclude_none=True).items()]},
    )
    return _to_item(updated)


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    claims: SuperAdminClaims,
) -> DeleteTenantResponse:
    """Deactivate a tenant (soft delete). Super-admin only."""
    if not tenants_util.deactivate_tenant(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    log_event(
        claims,
        action=AuditAction.TENANT_DEACTIVATE,
        target_type=AuditTargetType.TENANT,
        target_id=tenant_id,
        tenant_id=tenant_id,
    )
    return DeleteTenantResponse(deleted=True, tenant_id=tenant_id)
