"""Tenant DDB operations."""

from datetime import UTC, datetime
from typing import Any

from documentai_api.config.env import get_aws_config
from documentai_api.schemas.tenants import TenantRecord
from documentai_api.services import ddb as ddb_service


def _get_table_name() -> str:
    table_name = get_aws_config().tenants_table_name
    if not table_name:
        raise ValueError("TENANTS_TABLE_NAME not configured")
    return table_name


def get_tenant(tenant_id: str) -> dict[str, Any] | None:
    """Get a tenant by ID. Returns None if not found."""
    return ddb_service.get_item(_get_table_name(), {TenantRecord.TENANT_ID: tenant_id})


def list_tenants(*, active_only: bool = True) -> list[dict[str, Any]]:
    """List all tenants, optionally filtered to active only."""
    records = ddb_service.scan(_get_table_name())
    if active_only:
        return [r for r in records if r.get(TenantRecord.IS_ACTIVE, True)]
    return records


def create_tenant(
    tenant_id: str,
    display_name: str,
    primary_contact: str | None = None,
) -> dict[str, Any]:
    """Create a new tenant. Raises ValueError if already exists."""
    table_name = _get_table_name()
    existing = ddb_service.get_item(table_name, {TenantRecord.TENANT_ID: tenant_id})
    if existing:
        raise ValueError(f"Tenant '{tenant_id}' already exists")

    now = datetime.now(UTC).isoformat()
    item: dict[str, Any] = {
        TenantRecord.TENANT_ID: tenant_id,
        TenantRecord.DISPLAY_NAME: display_name,
        TenantRecord.IS_ACTIVE: True,
        TenantRecord.CREATED_AT: now,
        TenantRecord.UPDATED_AT: now,
    }

    if primary_contact:
        item[TenantRecord.PRIMARY_CONTACT] = primary_contact

    ddb_service.put_item(table_name, item)
    return item


def update_tenant(tenant_id: str, **fields: Any) -> dict[str, Any]:
    """Update tenant fields. Returns updated record. Raises ValueError if not found."""
    table_name = _get_table_name()
    existing = ddb_service.get_item(table_name, {TenantRecord.TENANT_ID: tenant_id})
    if not existing:
        raise ValueError(f"Tenant '{tenant_id}' not found")

    updates = []
    values: dict[str, Any] = {}
    now = datetime.now(UTC).isoformat()

    field_map = {
        "display_name": TenantRecord.DISPLAY_NAME,
        "primary_contact": TenantRecord.PRIMARY_CONTACT,
        "is_active": TenantRecord.IS_ACTIVE,
    }

    for key, value in fields.items():
        if value is not None and key in field_map:
            attr = field_map[key]
            param = f":{attr}"
            updates.append(f"{attr} = {param}")
            values[param] = value

    if not updates:
        raise ValueError("No fields to update")

    updates.append(f"{TenantRecord.UPDATED_AT} = :updatedAt")
    values[":updatedAt"] = now

    update_expr = "SET " + ", ".join(updates)
    ddb_service.update_item(table_name, {TenantRecord.TENANT_ID: tenant_id}, update_expr, values)

    updated = ddb_service.get_item(table_name, {TenantRecord.TENANT_ID: tenant_id})
    if not updated:
        raise ValueError("Update failed")
    return updated


def deactivate_tenant(tenant_id: str) -> bool:
    """Soft-delete a tenant. Returns True if deactivated."""
    table_name = _get_table_name()
    existing = ddb_service.get_item(table_name, {TenantRecord.TENANT_ID: tenant_id})
    if not existing:
        return False

    now = datetime.now(UTC).isoformat()
    update_expr = (
        f"SET {TenantRecord.IS_ACTIVE} = :isActive, {TenantRecord.UPDATED_AT} = :updatedAt"
    )
    values: dict[str, Any] = {":isActive": False, ":updatedAt": now}
    ddb_service.update_item(table_name, {TenantRecord.TENANT_ID: tenant_id}, update_expr, values)
    return True
