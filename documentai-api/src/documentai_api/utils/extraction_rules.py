from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.services import ddb as ddb_service

logger = get_logger(__name__)


@dataclass
class ExtractionRuleResult:
    fields: dict[str, Any]
    missing_required_field_list: list[str]


def _get_table_name() -> str:
    table_name = get_aws_config().extraction_rules_table_name
    if not table_name:
        raise ValueError("EXTRACTION_RULES_TABLE_NAME environment variable not set")
    return table_name


def get_rules(tenant_id: str, document_type: str | None = None) -> list[dict[str, Any]]:
    """Get extraction rules for a tenant, optionally filtered by document type."""
    table_name = _get_table_name()

    if document_type:
        item = ddb_service.get_item(
            table_name, {"tenantId": tenant_id, "documentType": document_type}
        )
        return [item] if item else []
    else:
        items = ddb_service.query_by_pk(table_name, "tenantId", tenant_id)
        return items


def upsert_rule(
    tenant_id: str,
    document_type: str,
    required_fields: list[str],
    optional_fields: list[str],
) -> dict[str, Any]:
    """Create or update an extraction rule atomically."""
    from documentai_api.utils.aws_client_factory import AWSClientFactory

    table_name = _get_table_name()
    now = datetime.now(UTC).isoformat()

    ddb_table = AWSClientFactory.get_ddb_table(table_name)
    response = ddb_table.update_item(
        Key={"tenantId": tenant_id, "documentType": document_type},
        UpdateExpression=(
            "SET requiredFields = :rf, optionalFields = :of, updatedAt = :now, "
            "createdAt = if_not_exists(createdAt, :now)"
        ),
        ExpressionAttributeValues={
            ":rf": required_fields,
            ":of": optional_fields,
            ":now": now,
        },
        ReturnValues="ALL_NEW",
    )

    return response["Attributes"]


def delete_rule(tenant_id: str, document_type: str) -> bool:
    """Delete an extraction rule. Returns True if the rule existed, False otherwise."""
    table_name = _get_table_name()
    key = {"tenantId": tenant_id, "documentType": document_type}
    existing = ddb_service.get_item(table_name, key)
    if not existing:
        return False
    ddb_service.delete_item(table_name, key)
    return True


def apply_extraction_rules(
    tenant_id: str, document_type: str, fields: dict[str, Any]
) -> ExtractionRuleResult:
    from documentai_api.utils.strings import snake_to_camel

    rules = get_rules(tenant_id, document_type)

    if not rules:
        return ExtractionRuleResult(fields=fields, missing_required_field_list=[])

    rule = rules[0]
    required = set(rule.get("requiredFields", []))
    optional = set(rule.get("optionalFields", []))
    allowed = {snake_to_camel(f) for f in required | optional}

    filtered = {k: v for k, v in fields.items() if k in allowed}
    required_camel = {snake_to_camel(f) for f in required}
    missing = sorted(required_camel - set(filtered.keys()))

    return ExtractionRuleResult(fields=filtered, missing_required_field_list=missing)
