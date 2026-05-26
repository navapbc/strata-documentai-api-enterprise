"""Document category DDB operations."""

from typing import Any

from documentai_api.logging import get_logger
from documentai_api.schemas.document_category import DocumentCategoriesTable, DocumentCategoryRecord

logger = get_logger(__name__)

_table = DocumentCategoriesTable()


def get_category(tenant_id: str, category_name: str) -> dict[str, Any] | None:
    """Get a single document category."""
    return _table.get(tenant_id, category_name)


def list_categories(tenant_id: str, active_only: bool = True) -> list[dict[str, Any]]:
    """List document categories for a tenant."""
    return _table.list_by_pk(tenant_id, active_only=active_only)


def list_all_categories(active_only: bool = True) -> list[dict[str, Any]]:
    """List all document categories across all tenants (super-admin only)."""
    return _table.list_all(active_only=active_only)


def create_category(
    tenant_id: str,
    category_name: str,
    display_name: str,
    description: str | None = None,
) -> dict[str, Any]:
    """Create a new document category. Raises ValueError if it already exists."""
    item = {
        DocumentCategoryRecord.TENANT_ID: tenant_id,
        DocumentCategoryRecord.CATEGORY_NAME: category_name,
        DocumentCategoryRecord.DISPLAY_NAME: display_name,
        DocumentCategoryRecord.DESCRIPTION: description or "",
    }
    return _table.create(item)


def update_category(
    tenant_id: str,
    category_name: str,
    display_name: str | None = None,
    description: str | None = None,
    is_active: bool | None = None,
) -> dict[str, Any]:
    """Update a document category. Raises ValueError if not found or no fields to update."""
    fields: dict[str, Any] = {}
    if display_name is not None:
        fields[DocumentCategoryRecord.DISPLAY_NAME] = display_name
    if description is not None:
        fields[DocumentCategoryRecord.DESCRIPTION] = description
    if is_active is not None:
        fields[DocumentCategoryRecord.IS_ACTIVE] = is_active

    if not fields:
        raise ValueError("No fields to update")

    return _table.update(tenant_id, category_name, **fields)


def delete_category(tenant_id: str, category_name: str) -> bool:
    """Deactivate a document category. Returns False if not found."""
    return _table.deactivate(tenant_id, category_name)
