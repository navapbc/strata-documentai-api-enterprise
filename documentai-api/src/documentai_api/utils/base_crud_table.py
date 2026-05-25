"""Base CRUD table for DynamoDB operations.

Subclass and declare table config to get standard CRUD operations:

    class TenantsTable(BaseCrudTable):
        table_name_env = "tenants_table_name"
        pk_field = "tenantId"

    tenants = TenantsTable()
    tenants.get("acme")
    tenants.list_all(active_only=True)
    tenants.create({"tenantId": "acme", "displayName": "Acme Corp"})
"""

from datetime import UTC, datetime
from typing import Any

from documentai_api.logging import get_logger
from documentai_api.services import ddb as ddb_service
from documentai_api.utils.aws_client_factory import AWSClientFactory
from documentai_api.utils.base_readonly_table import ReadOnlyTable

logger = get_logger(__name__)


class BaseCrudTable(ReadOnlyTable):
    """Generic CRUD operations for a DynamoDB table."""

    active_field: str = "isActive"
    created_field: str = "createdAt"
    updated_field: str = "updatedAt"

    def list_by_pk(self, pk_value: str, active_only: bool = True) -> list[dict[str, Any]]:
        """List items by partition key."""
        items = super().list_by_pk(pk_value)
        if active_only and self.active_field:
            items = [i for i in items if i.get(self.active_field, True)]
        return items

    def list_all(self, active_only: bool = True) -> list[dict[str, Any]]:
        """Scan all items (use sparingly)."""
        items = super().list_all()
        if active_only and self.active_field:
            items = [i for i in items if i.get(self.active_field, True)]
        return items

    def create(self, item: dict[str, Any], check_exists: bool = True) -> dict[str, Any]:
        """Create a new item. Raises ValueError if it already exists (when check_exists=True)."""
        pk_value = item[self.pk_field]
        sk_value = item.get(self.sk_field) if self.sk_field else None

        if check_exists:
            existing = self.get(pk_value, sk_value)
            if existing:
                raise ValueError(f"Item already exists: {pk_value}/{sk_value or ''}")

        now = datetime.now(UTC).isoformat()
        item.setdefault(self.created_field, now)
        item.setdefault(self.updated_field, now)
        if self.active_field:
            item.setdefault(self.active_field, True)

        ddb_service.put_item(self._get_table_name(), item)
        return item

    def update(self, pk_value: str, sk_value: str | None = None, **fields: Any) -> dict[str, Any]:
        """Update fields on an existing item. Raises ValueError if not found or no fields."""
        existing = self.get(pk_value, sk_value)
        if not existing:
            raise ValueError("Item not found")

        # Filter out None values
        updates = {k: v for k, v in fields.items() if v is not None}
        if not updates:
            raise ValueError("No fields to update")

        now = datetime.now(UTC).isoformat()
        updates[self.updated_field] = now

        update_parts = []
        expr_values: dict[str, Any] = {}
        for field_name, value in updates.items():
            param = f":{field_name}"
            update_parts.append(f"{field_name} = {param}")
            expr_values[param] = value

        update_expr = "SET " + ", ".join(update_parts)
        key = self._build_key(pk_value, sk_value)

        ddb_service.update_item(self._get_table_name(), key, update_expr, expr_values)

        updated = self.get(pk_value, sk_value)
        if not updated:
            raise ValueError("Update failed")
        return updated

    def upsert(self, pk_value: str, sk_value: str | None = None, **fields: Any) -> dict[str, Any]:
        """Create or update atomically. Sets created_field only if item is new."""
        now = datetime.now(UTC).isoformat()

        update_parts = []
        expr_values: dict[str, Any] = {":now": now}

        for field_name, value in fields.items():
            if value is not None:
                param = f":{field_name}"
                update_parts.append(f"{field_name} = {param}")
                expr_values[param] = value

        update_parts.append(f"{self.updated_field} = :now")
        update_parts.append(f"{self.created_field} = if_not_exists({self.created_field}, :now)")

        update_expr = "SET " + ", ".join(update_parts)
        key = self._build_key(pk_value, sk_value)

        table = AWSClientFactory.get_ddb_table(self._get_table_name())
        response = table.update_item(
            Key=key,
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
            ReturnValues="ALL_NEW",
        )
        return response["Attributes"]

    def deactivate(self, pk_value: str, sk_value: str | None = None) -> bool:
        """Soft-delete by setting active_field to False. Returns False if not found."""
        existing = self.get(pk_value, sk_value)
        if not existing:
            return False

        now = datetime.now(UTC).isoformat()
        key = self._build_key(pk_value, sk_value)
        update_expr = f"SET {self.active_field} = :isActive, {self.updated_field} = :updatedAt"
        expr_values: dict[str, Any] = {":isActive": False, ":updatedAt": now}

        ddb_service.update_item(self._get_table_name(), key, update_expr, expr_values)
        return True

    def delete(self, pk_value: str, sk_value: str | None = None) -> bool:
        """Hard-delete an item. Returns False if not found."""
        key = self._build_key(pk_value, sk_value)
        existing = ddb_service.get_item(self._get_table_name(), key)
        if not existing:
            return False
        ddb_service.delete_item(self._get_table_name(), key)
        return True
