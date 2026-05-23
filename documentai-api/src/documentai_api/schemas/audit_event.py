"""Schema for the audit-events DynamoDB table."""

GLOBAL_TENANT = "__global__"
"""Partition key for events not scoped to a specific tenant (e.g. tenant.create)."""


class AuditAction:
    """Dotted action strings for audit events."""

    TENANT_CREATE = "tenant.create"
    TENANT_UPDATE = "tenant.update"
    TENANT_DEACTIVATE = "tenant.deactivate"
    KEY_CREATE = "key.create"
    KEY_REVOKE = "key.revoke"
    USER_APPROVE = "user.approve"
    USER_ROLE_CHANGE = "user.role.change"
    USER_TENANT_CHANGE = "user.tenant.change"
    USER_DELETE = "user.delete"


class AuditTargetType:
    """Target type values for audit events."""

    TENANT = "tenant"
    KEY = "key"
    USER = "user"


class AuditEventRecord:
    """Field names for the audit-events DynamoDB table."""

    TENANT_ID = "tenantId"
    TIMESTAMP_EVENT_ID = "timestamp#eventId"
    EVENT_ID = "eventId"
    ACTOR_SUB = "actorSub"
    ACTOR_EMAIL = "actorEmail"
    ACTION = "action"
    TARGET_TYPE = "targetType"
    TARGET_ID = "targetId"
    METADATA = "metadata"
    TTL = "ttl"
