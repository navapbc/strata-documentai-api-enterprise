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

from ulid import ULID

from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.schemas.audit_event import GLOBAL_TENANT, AuditEventRecord
from documentai_api.utils.aws_client_factory import AWSClientFactory

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

        # Double-write to __global__ for super-admin "all events" view
        if partition != GLOBAL_TENANT:
            table.put_item(Item={**base_item, AuditEventRecord.TENANT_ID: GLOBAL_TENANT})
    except Exception:
        logger.exception(f"Failed to write audit event: {action} on {target_type}/{target_id}")
