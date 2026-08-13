"""Admin tenants router - CRUD for tenant management."""

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from documentai_api.annotations import (
    AdminClaims,
    MonthParam,
    SuperAdminClaims,
    verify_jwt_with_role,
)
from documentai_api.config.constants import ApiVisualizationTag
from documentai_api.logging import get_logger
from documentai_api.models.tenant import (
    CreateTenantRequest,
    DeleteTenantResponse,
    ListTenantsResponse,
    TenantItem,
    TenantRequestCountItem,
    TenantRequestCountsResponse,
    UpdateTenantRequest,
)
from documentai_api.schemas.audit_event import AuditAction, AuditTargetType
from documentai_api.schemas.tenants import TenantRecord
from documentai_api.utils import tenants as tenants_util
from documentai_api.utils.audit_log import log_event
from documentai_api.utils.dates import get_month_prefix, get_today_iso
from documentai_api.utils.jwt_auth import is_super_admin, tenant_scope
from documentai_api.utils.strings import camel_to_snake
from documentai_api.utils.tenants import SUPER_ADMIN_PROTECTED_FIELDS
from documentai_api.utils.write_limit import get_write_counts

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/admin/tenants",
    tags=[ApiVisualizationTag.ADMIN_TENANTS],
    dependencies=[Depends(verify_jwt_with_role)],
)


def _to_item(record: dict[str, Any]) -> TenantItem:
    return TenantItem(
        tenant_id=record.get(TenantRecord.TENANT_ID, ""),
        display_name=record.get(TenantRecord.DISPLAY_NAME, ""),
        primary_contact=record.get(TenantRecord.PRIMARY_CONTACT),
        is_active=record.get(TenantRecord.IS_ACTIVE, True),
        extraction_confidence_floor=record.get(TenantRecord.EXTRACTION_CONFIDENCE_FLOOR),
        max_writes_per_day=record.get(TenantRecord.MAX_WRITES_PER_DAY),
        max_writes_per_month=record.get(TenantRecord.MAX_WRITES_PER_MONTH),
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
            extraction_confidence_floor=body.extraction_confidence_floor,
            max_writes_per_day=body.max_writes_per_day,
            max_writes_per_month=body.max_writes_per_month,
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


@router.patch(
    "/{tenant_id}",
    description="Update a tenant's metadata. Pass `null` for `extractionConfidenceFloor`, `maxWritesPerDay`, or `maxWritesPerMonth` to clear the override back to the platform default. `isActive`, `extractionConfidenceFloor`, `maxWritesPerDay`, and `maxWritesPerMonth` are super-admin only.",
)
async def update_tenant(
    tenant_id: str,
    body: UpdateTenantRequest,
    claims: AdminClaims,
) -> TenantItem:
    """Update a tenant's metadata."""
    _enforce_scope(claims, tenant_id)

    record = tenants_util.get_tenant(tenant_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    allowed = set(body.model_fields_set)
    super_admin_only = {camel_to_snake(f) for f in SUPER_ADMIN_PROTECTED_FIELDS}
    restricted = allowed & super_admin_only
    if not is_super_admin(claims) and restricted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only super-admins may modify: {', '.join(sorted(restricted))}",
        )

    set_fields = {f: getattr(body, f) for f in allowed if getattr(body, f) is not None}
    clear_fields = {f for f in allowed if getattr(body, f) is None}

    _day = camel_to_snake(TenantRecord.MAX_WRITES_PER_DAY)
    _month = camel_to_snake(TenantRecord.MAX_WRITES_PER_MONTH)
    effective_day = (
        None
        if _day in clear_fields
        else set_fields.get(_day, record.get(TenantRecord.MAX_WRITES_PER_DAY))
    )
    effective_month = (
        None
        if _month in clear_fields
        else set_fields.get(_month, record.get(TenantRecord.MAX_WRITES_PER_MONTH))
    )
    if (
        effective_day is not None
        and effective_month is not None
        and effective_day > effective_month
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Daily write limit cannot exceed monthly write limit",
        )

    try:
        updated = tenants_util.update_tenant(
            tenant_id,
            clear_fields=clear_fields,
            **set_fields,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    log_event(
        claims,
        action=AuditAction.TENANT_UPDATE,
        target_type=AuditTargetType.TENANT,
        target_id=tenant_id,
        tenant_id=tenant_id,
        metadata={"changed_fields": list(allowed)},
    )
    return _to_item(updated)


@router.get("/{tenant_id}/request-counts")
async def get_tenant_request_counts(
    tenant_id: str,
    claims: AdminClaims,
    month: MonthParam = None,
) -> TenantRequestCountsResponse:
    """Get daily request counts for a tenant in a given month (defaults to current month)."""
    _enforce_scope(claims, tenant_id)
    month = month or get_month_prefix(get_today_iso())
    items = await asyncio.to_thread(get_write_counts, tenant_id, month)
    daily = sorted(
        [TenantRequestCountItem(date=i["date"], count=int(i["count"])) for i in items],
        key=lambda x: x.date,
    )
    return TenantRequestCountsResponse(
        tenant_id=tenant_id,
        month=month,
        monthly_total=sum(d.count for d in daily),
        daily=daily,
    )


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
