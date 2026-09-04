"""Audit event logging for admin mutations.

Writes structured events to the audit-events DynamoDB table.
Each mutating admin action should call log_event() after success.

Metadata conventions per action:
    key.create       -> {api_key_name, environment, expires_at, email_address}
    key.revoke       -> {key_prefix, api_key_name}
    user.approve     -> {role, tenant_id}
    user.role.change -> {previous_role, new_role}
    user.tenant.change -> {previous_tenant, new_tenant}
    user.delete      -> {email}
    tenant.create    -> {display_name, primary_contact}
    tenant.update    -> {changed_fields: [...], previous: {...}}
    tenant.deactivate -> {display_name}
"""

import time
from datetime import UTC, datetime
from typing import Any

from boto3.dynamodb.conditions import Attr, ConditionBase, Key
from ulid import ULID

from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.models.audit import AuditEventItem
from documentai_api.schemas.audit_event import GLOBAL_TENANT, AuditEventRecord, AuditEventsTable
from documentai_api.services.aws_client_factory import AWSClientFactory

_table = AuditEventsTable()


logger = get_logger(__name__)

_TTL_SECONDS = 365 * 24 * 60 * 60  # 1 year


def _generate_event_id() -> str:
    """Generate a ULID for the audit event."""
    return str(ULID())


def _get_table_name() -> str:
    table_name = get_aws_config().audit_events_table_name
    if not table_name:
        raise ValueError("AUDIT_EVENTS_TABLE_NAME environment variable not set")
    return table_name


def log_event(
    claims: dict[str, Any],
    action: str,
    target_type: str,
    target_id: str,
    tenant_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Write an audit event to DynamoDB.

    Args:
        claims: Decoded JWT claims (must contain 'sub', optionally 'email').
        action: Dotted action string (e.g. 'tenant.create', 'key.revoke').
        target_type: Resource type ('tenant', 'key', 'user').
        target_id: Specific resource identifier.
        tenant_id: Tenant partition for the event. Defaults to GLOBAL_TENANT.
        metadata: Action-specific context (see module docstring).
    """
    partition = tenant_id or GLOBAL_TENANT
    event_id = _generate_event_id()
    now = datetime.now(UTC).isoformat()
    sort_key = f"{now}#{event_id}"
    ttl = int(time.time()) + _TTL_SECONDS

    base_item = {
        AuditEventRecord.TIMESTAMP_EVENT_ID: sort_key,
        AuditEventRecord.EVENT_ID: event_id,
        AuditEventRecord.ACTOR_SUB: claims.get("sub", "unknown"),
        AuditEventRecord.ACTOR_EMAIL: claims.get("email", "unknown"),
        AuditEventRecord.ACTION: action,
        AuditEventRecord.TARGET_TYPE: target_type,
        AuditEventRecord.TARGET_ID: target_id,
        AuditEventRecord.METADATA: metadata or {},
        AuditEventRecord.TTL: ttl,
    }

    try:
        table = AWSClientFactory.get_ddb_table(_get_table_name())

        # Write to tenant partition
        table.put_item(Item={**base_item, AuditEventRecord.TENANT_ID: partition})

        # Double-write to __global__ for super-admin "all events" view.
        # Note: these two writes are not atomic - a failure on the second write
        # leaves the tenant partition written but the global view incomplete.
        # This is acceptable for audit observability (tenant record is authoritative)
        # but callers should not rely on global-view consistency.
        if partition != GLOBAL_TENANT:
            table.put_item(Item={**base_item, AuditEventRecord.TENANT_ID: GLOBAL_TENANT})

    except Exception:
        # Log at ERROR so failures are visible in CloudWatch alarms rather than
        # silently dropped. Audit failures are non-fatal to the request but must
        # be monitored - a sustained failure means the audit trail has gaps.
        logger.error(
            f"Failed to write audit event: {action} on {target_type}/{target_id}",
            exc_info=True,
        )


def record_to_item(record: dict[str, Any]) -> AuditEventItem:
    sort_key = record.get(AuditEventRecord.TIMESTAMP_EVENT_ID, "")
    timestamp = sort_key.split("#")[0] if "#" in sort_key else sort_key
    return AuditEventItem(
        event_id=record.get(AuditEventRecord.EVENT_ID, ""),
        tenant_id=record.get(AuditEventRecord.TENANT_ID, ""),
        actor_sub=record.get(AuditEventRecord.ACTOR_SUB, ""),
        actor_email=record.get(AuditEventRecord.ACTOR_EMAIL, ""),
        action=record.get(AuditEventRecord.ACTION, ""),
        target_type=record.get(AuditEventRecord.TARGET_TYPE, ""),
        target_id=record.get(AuditEventRecord.TARGET_ID, ""),
        metadata=record.get(AuditEventRecord.METADATA, {}),
        timestamp=timestamp,
    )


def build_sk_condition(start_date: str | None, end_date: str | None) -> ConditionBase | None:
    sk = Key(AuditEventRecord.TIMESTAMP_EVENT_ID)
    if start_date and end_date:
        return sk.between(start_date, end_date + "~")
    elif start_date:
        return sk.gte(start_date)
    elif end_date:
        return sk.lte(end_date + "~")
    return None


def query_by_tenant(
    tenant_id: str,
    action: str | None,
    actor_email: str | None,
    start_date: str | None,
    end_date: str | None,
    limit: int,
    exclusive_start_key: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    key_condition: ConditionBase = Key(AuditEventRecord.TENANT_ID).eq(tenant_id)
    sk_condition = build_sk_condition(start_date, end_date)
    if sk_condition:
        key_condition = key_condition & sk_condition

    filter_expr = None
    if action:
        filter_expr = Attr(AuditEventRecord.ACTION).eq(action)
    if actor_email:
        actor_filter = Attr(AuditEventRecord.ACTOR_EMAIL).eq(actor_email)
        filter_expr = filter_expr & actor_filter if filter_expr else actor_filter

    return _table.query(
        key_condition=key_condition,
        filter_expression=filter_expr,
        limit=limit,
        scan_forward=False,
        start_key=exclusive_start_key,
    )


def query_by_actor(
    actor_email: str,
    action: str | None,
    start_date: str | None,
    end_date: str | None,
    limit: int,
    exclusive_start_key: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    key_condition: ConditionBase = Key(AuditEventRecord.ACTOR_EMAIL).eq(actor_email)
    sk_condition = build_sk_condition(start_date, end_date)
    if sk_condition:
        key_condition = key_condition & sk_condition

    filter_expr = Attr(AuditEventRecord.ACTION).eq(action) if action else None

    return _table.query(
        key_condition=key_condition,
        index_name="actor-email-timestamp-index",
        filter_expression=filter_expr,
        limit=limit,
        scan_forward=False,
        start_key=exclusive_start_key,
    )


def query_by_action(
    action: str,
    start_date: str | None,
    end_date: str | None,
    limit: int,
    exclusive_start_key: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    key_condition: ConditionBase = Key(AuditEventRecord.ACTION).eq(action)
    sk_condition = build_sk_condition(start_date, end_date)
    if sk_condition:
        key_condition = key_condition & sk_condition

    return _table.query(
        key_condition=key_condition,
        index_name="action-timestamp-index",
        limit=limit,
        scan_forward=False,
        start_key=exclusive_start_key,
    )
