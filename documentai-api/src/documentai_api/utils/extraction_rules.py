from dataclasses import dataclass, field
from typing import Any

from documentai_api.logging import get_logger
from documentai_api.schemas.extraction_rules import ExtractionRulesTable

logger = get_logger(__name__)


@dataclass
class ExtractionRuleResult:
    fields: dict[str, Any]
    missing_required_field_list: list[str]
    required_field_list: list[str] = field(default_factory=list)


_table = ExtractionRulesTable()


def get_rules(tenant_id: str, document_type: str | None = None) -> list[dict[str, Any]]:
    """Get extraction rules for a tenant, optionally filtered by document type."""
    if document_type:
        item = _table.get(tenant_id, document_type)
        return [item] if item else []
    else:
        return _table.list_by_pk(tenant_id, active_only=False)


def upsert_rule(
    tenant_id: str,
    document_type: str,
    required_fields: list[str],
    optional_fields: list[str],
    blueprint_arn: str | None = None,
) -> dict[str, Any]:
    """Create or update an extraction rule atomically."""
    fields: dict[str, Any] = {
        "requiredFields": required_fields,
        "optionalFields": optional_fields,
    }
    if blueprint_arn:
        fields["blueprintArn"] = blueprint_arn

    return _table.upsert(tenant_id, document_type, **fields)


def delete_rule(tenant_id: str, document_type: str) -> bool:
    """Delete an extraction rule. Returns True if the rule existed, False otherwise."""
    return _table.delete(tenant_id, document_type)


def apply_extraction_rules(
    tenant_id: str,
    document_type: str,
    fields: dict[str, Any],
    missing_fields: list[str] | None = None,
) -> ExtractionRuleResult:
    rules = get_rules(tenant_id, document_type)

    if not rules:
        return ExtractionRuleResult(fields=fields, missing_required_field_list=[])

    rule = rules[0]
    required = set(rule.get("requiredFields", []))
    optional = set(rule.get("optionalFields", []))
    allowed_lower = {f.lower() for f in required | optional}
    required_lower = {f.lower() for f in required}

    absent_lower = {f.lower() for f in (missing_fields or [])} & required_lower
    filtered = {
        k: v
        for k, v in fields.items()
        if k.lower() in allowed_lower and k.lower() not in absent_lower
    }
    present_lower = {k.lower() for k in filtered}
    missing = sorted(f for f in required if f.lower() not in present_lower)

    return ExtractionRuleResult(
        fields=filtered, missing_required_field_list=missing, required_field_list=sorted(required)
    )


def get_missing_required_fields(
    tenant_id: str | None,
    document_type: str | None,
    empty_fields: list[str],
    fields_missing_geometry: list[str],
) -> tuple[list[str], list[str]] | None:
    """Return (missing_required, all_required) per extraction rules at processing time.

    Returns None if no rules are configured.
    """
    if not tenant_id or not document_type:
        return None

    rules = get_rules(tenant_id, document_type)

    if not rules:
        return None
    rule = rules[0]
    required = set(rule.get("requiredFields", []))
    empty_lower = {f.lower() for f in (set(empty_fields) | set(fields_missing_geometry))}
    missing = sorted(f for f in required if f.lower() in empty_lower)
    return missing, sorted(required)
