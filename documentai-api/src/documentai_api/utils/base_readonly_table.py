"""Base read-only table for DynamoDB query operations.

Subclass and declare table config to get standard read operations:

    class DocumentMetadataTable(ReadOnlyTable):
        table_name_env = "documentai_document_metadata_table_name"
        pk_field = "fileName"

    docs = DocumentMetadataTable()
    docs.get("input/tenant/file.pdf")
    docs.query(key_condition=Key("tenantId").eq("acme"), index_name="TenantIdIndex")
"""

from typing import Any

from fastapi import HTTPException, status

from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.services import ddb as ddb_service
from documentai_api.services.aws_client_factory import AWSClientFactory

logger = get_logger(__name__)


class ReadOnlyTable:
    """Generic read operations for a DynamoDB table."""

    table_name_env: str
    pk_field: str
    sk_field: str | None = None

    def _get_table_name(self) -> str:
        table_name: str | None = getattr(get_aws_config(), self.table_name_env.lower(), None)
        if not table_name:
            # Log the specific config name for operators; keep it out of the
            # client-facing response so we don't leak internal table names.
            logger.error("Required table not configured: %s", self.table_name_env)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage not configured",
            )
        return table_name

    def _build_key(self, pk_value: str, sk_value: str | None = None) -> dict[str, str]:
        key: dict[str, str] = {self.pk_field: pk_value}
        if self.sk_field and sk_value:
            key[self.sk_field] = sk_value
        return key

    def get(self, pk_value: str, sk_value: str | None = None) -> dict[str, Any] | None:
        """Get a single item by key."""
        return ddb_service.get_item(self._get_table_name(), self._build_key(pk_value, sk_value))

    def list_by_pk(self, pk_value: str) -> list[dict[str, Any]]:
        """List items by partition key (requires sort key on table)."""
        if not self.sk_field:
            raise NotImplementedError(
                f"{type(self).__name__}.list_by_pk requires sk_field; use list_all() or query() instead"
            )
        return ddb_service.query_by_pk(self._get_table_name(), self.pk_field, pk_value)

    def list_all(self) -> list[dict[str, Any]]:
        """Scan all items (use sparingly)."""
        return ddb_service.scan(self._get_table_name())

    def query(
        self,
        key_condition: Any,
        filter_expression: Any | None = None,
        index_name: str | None = None,
        limit: int | None = None,
        scan_forward: bool = True,
        start_key: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """Run a DDB query with full control over conditions.

        Returns (items, last_evaluated_key). last_evaluated_key is None if
        there are no more pages.
        """
        table = AWSClientFactory.get_ddb_table(self._get_table_name())

        kwargs: dict[str, Any] = {
            "KeyConditionExpression": key_condition,
            "ScanIndexForward": scan_forward,
        }
        if filter_expression is not None:
            kwargs["FilterExpression"] = filter_expression
        if index_name:
            kwargs["IndexName"] = index_name
        if limit:
            kwargs["Limit"] = limit
        if start_key:
            kwargs["ExclusiveStartKey"] = start_key

        # When a FilterExpression is present, DynamoDB applies Limit *before*
        # filtering, so a single page may return fewer items than requested.
        # Paginate internally until we have enough results or the index is exhausted.
        # Return all collected items (never truncate) enabling the cursor to always
        # point past every item we return; truncating would silently drop the
        # surplus matches as the cursor already skips past them.
        if filter_expression is not None and limit:
            collected: list[dict[str, Any]] = []
            last_key = start_key

            while len(collected) < limit:
                page_kwargs = {**kwargs, "Limit": limit}
                if last_key:
                    page_kwargs["ExclusiveStartKey"] = last_key
                elif "ExclusiveStartKey" in page_kwargs:
                    del page_kwargs["ExclusiveStartKey"]

                resp = table.query(**page_kwargs)
                collected.extend(resp.get("Items", []))
                last_key = resp.get("LastEvaluatedKey")
                if not last_key:
                    break

            return collected, last_key

        response = table.query(**kwargs)
        return response.get("Items", []), response.get("LastEvaluatedKey")
