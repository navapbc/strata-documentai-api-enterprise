"""Document category DDB operations."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from documentai_api.config.constants import ConfigDefaults
from documentai_api.logging import get_logger
from documentai_api.schemas.document_category import DocumentCategoriesTable, DocumentCategoryRecord
from documentai_api.utils.aws_client_factory import AWSClientFactory
from documentai_api.utils.cache import get_cache

logger = get_logger(__name__)

_table = DocumentCategoriesTable()
_registered_categories: set[tuple[str, str]] = set()


def get_processing_percentage(tenant_id: str, category_name: str) -> float:
    """Return processingPercentage for a category, defaulting to 1.0 if not found."""
    cache_key = f"processing_percentage:{tenant_id}:{category_name}"
    cached = get_cache().get(cache_key)
    if cached is not None:
        return float(cached)
    record = get_category(tenant_id, category_name)
    value = float(record.get(DocumentCategoryRecord.PROCESSING_PERCENTAGE, 1.0)) if record else 1.0
    get_cache().add(
        cache_key, value, ttl_minutes=ConfigDefaults.PROCESSING_PERCENTAGE_CACHE_TTL_MINUTES
    )
    return value


def get_category(tenant_id: str, category_name: str) -> dict[str, Any] | None:
    """Get a single document category."""
    return _table.get(tenant_id, category_name)


def list_categories(tenant_id: str, active_only: bool = True) -> list[dict[str, Any]]:
    """List document categories for a tenant."""
    return _table.list_by_pk(tenant_id, active_only=active_only)


def list_all_categories(active_only: bool = True) -> list[dict[str, Any]]:
    """List all document categories across all tenants (super-admin only)."""
    return _table.list_all(active_only=active_only)


def auto_register_category(tenant_id: str, category_name: str) -> None:
    """Upsert a category seen at upload time.

    Creates the record if it doesn't exist. Uses if_not_exists on all fields except
    updatedAt so existing manually-created records are not overwritten, provided
    isAutoRegistered was explicitly set to False at creation. Skips the DDB write
    if already registered this container lifetime.
    """
    if (tenant_id, category_name) in _registered_categories:
        return

    now = datetime.now(UTC).isoformat()
    r = DocumentCategoryRecord
    table = AWSClientFactory.get_ddb_table(_table._get_table_name())
    table.update_item(
        Key={r.TENANT_ID: tenant_id, r.CATEGORY_NAME: category_name},
        UpdateExpression=(
            "SET "
            f"{r.IS_AUTO_REGISTERED} = if_not_exists({r.IS_AUTO_REGISTERED}, :t), "
            f"{r.IS_ACTIVE} = if_not_exists({r.IS_ACTIVE}, :t), "
            f"{r.DISPLAY_NAME} = if_not_exists({r.DISPLAY_NAME}, :name), "
            f"{r.PROCESSING_PERCENTAGE} = if_not_exists({r.PROCESSING_PERCENTAGE}, :one), "
            f"{r.CREATED_AT} = if_not_exists({r.CREATED_AT}, :now), "
            f"{r.UPDATED_AT} = :now"
        ),
        ExpressionAttributeValues={
            ":t": True,
            ":now": now,
            ":name": category_name,
            ":one": Decimal("1.0"),
        },
    )
    _registered_categories.add((tenant_id, category_name))


def create_category(
    tenant_id: str,
    category_name: str,
    display_name: str,
    description: str | None = None,
    processing_percentage: float = 1.0,
) -> dict[str, Any]:
    """Create a new document category. Raises ValueError if it already exists."""
    item = {
        DocumentCategoryRecord.TENANT_ID: tenant_id,
        DocumentCategoryRecord.CATEGORY_NAME: category_name,
        DocumentCategoryRecord.DISPLAY_NAME: display_name,
        DocumentCategoryRecord.DESCRIPTION: description or "",
        DocumentCategoryRecord.IS_AUTO_REGISTERED: False,
        DocumentCategoryRecord.PROCESSING_PERCENTAGE: processing_percentage,
    }
    return _table.create(item)


def update_category(
    tenant_id: str,
    category_name: str,
    display_name: str | None = None,
    description: str | None = None,
    is_active: bool | None = None,
    processing_percentage: float | None = None,
) -> dict[str, Any]:
    """Update a document category. Raises ValueError if not found or no fields to update."""
    fields: dict[str, Any] = {}
    if display_name is not None:
        fields[DocumentCategoryRecord.DISPLAY_NAME] = display_name
    if description is not None:
        fields[DocumentCategoryRecord.DESCRIPTION] = description
    if is_active is not None:
        fields[DocumentCategoryRecord.IS_ACTIVE] = is_active
    if processing_percentage is not None:
        fields[DocumentCategoryRecord.PROCESSING_PERCENTAGE] = processing_percentage

    if not fields:
        raise ValueError("No fields to update")

    result = _table.update(tenant_id, category_name, **fields)
    if processing_percentage is not None:
        get_cache().invalidate(f"processing_percentage:{tenant_id}:{category_name}")
    return result


def delete_category(tenant_id: str, category_name: str) -> bool:
    """Deactivate a document category. Returns False if not found."""
    return _table.deactivate(tenant_id, category_name)
