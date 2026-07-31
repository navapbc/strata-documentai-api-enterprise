"""Tenant DDB operations."""

from typing import Any

from documentai_api.schemas.tenants import TenantRecord, TenantsTable
from documentai_api.utils.strings import snake_to_camel

_table = TenantsTable()

SUPER_ADMIN_PROTECTED_FIELDS = _table.super_admin_protected_fields


def get_tenant(tenant_id: str) -> dict[str, Any] | None:
    """Get a tenant by ID. Returns None if not found."""
    return _table.get(tenant_id)


def get_extraction_confidence_floor(tenant_id: str | None) -> float:
    """Get the extraction confidence floor for a tenant, falling back to global default."""
    from documentai_api.config.constants import ConfigDefaults

    if tenant_id:
        record = _table.get(tenant_id)
        if record and TenantRecord.EXTRACTION_CONFIDENCE_FLOOR in record:
            return float(record[TenantRecord.EXTRACTION_CONFIDENCE_FLOOR])
    return ConfigDefaults.FIELD_CONFIDENCE_THRESHOLD


def tenant_has_confidence_floor(tenant_id: str | None) -> bool:
    """Return True if the tenant has an explicit confidence floor configured."""
    if not tenant_id:
        return False
    record = _table.get(tenant_id)
    return bool(record and TenantRecord.EXTRACTION_CONFIDENCE_FLOOR in record)


def list_tenants(*, active_only: bool = True) -> list[dict[str, Any]]:
    """List all tenants, optionally filtered to active only."""
    return _table.list_all(active_only=active_only)


def create_tenant(
    tenant_id: str,
    display_name: str,
    primary_contact: str | None = None,
    extraction_confidence_floor: float | None = None,
    max_writes_per_day: int | None = None,
    max_writes_per_month: int | None = None,
) -> dict[str, Any]:
    """Create a new tenant. Raises ValueError if already exists."""
    item: dict[str, Any] = {
        TenantRecord.TENANT_ID: tenant_id,
        TenantRecord.DISPLAY_NAME: display_name,
    }
    if primary_contact:
        item[TenantRecord.PRIMARY_CONTACT] = primary_contact
    if extraction_confidence_floor is not None:
        item[TenantRecord.EXTRACTION_CONFIDENCE_FLOOR] = extraction_confidence_floor
    if max_writes_per_day is not None:
        item[TenantRecord.MAX_WRITES_PER_DAY] = max_writes_per_day
    if max_writes_per_month is not None:
        item[TenantRecord.MAX_WRITES_PER_MONTH] = max_writes_per_month

    return _table.create(item)


def update_tenant(
    tenant_id: str, clear_fields: set[str] | None = None, **fields: Any
) -> dict[str, Any]:
    """Update tenant fields. Returns updated record. Raises ValueError if not found.

    Pass clear_fields (python field names) to explicitly remove nullable overrides.
    Only fields in TenantsTable.clearable_fields are accepted; others are silently ignored.
    """
    ddb_fields = _table.to_ddb_fields(**{k: v for k, v in fields.items() if v is not None})
    ddb_clear = {
        snake_to_camel(k)
        for k in (clear_fields or set())
        if snake_to_camel(k) in _table.clearable_fields
    }
    if not ddb_fields and not ddb_clear:
        raise ValueError("No fields to update")

    return _table.update(tenant_id, clear_fields=ddb_clear or None, **ddb_fields)


def deactivate_tenant(tenant_id: str) -> bool:
    """Soft-delete a tenant. Returns True if deactivated."""
    return _table.deactivate(tenant_id)
