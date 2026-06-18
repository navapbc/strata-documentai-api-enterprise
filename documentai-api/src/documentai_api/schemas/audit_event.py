"""Schema for the audit-events DynamoDB table."""

from documentai_api.utils.base_crud_table import BaseCrudTable

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
    DOCUMENT_CATEGORY_CREATE = "document_category.create"
    DOCUMENT_CATEGORY_UPDATE = "document_category.update"
    DOCUMENT_CATEGORY_DEACTIVATE = "document_category.deactivate"
    EXTRACTION_RULE_UPDATE = "extraction_rule.update"
    EXTRACTION_RULE_DELETE = "extraction_rule.delete"
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    DOCUMENT_VIEW = "document.view"
    DOCUMENT_VIEW_EXTRACTED_DATA = "document.view_extracted_data"
    DOCUMENT_SEARCH = "document.search"
    DOCUMENT_LIST = "document.list"
    DOCUMENT_PREVIEW = "document.preview"


class AuditTargetType:
    """Target type values for audit events."""

    TENANT = "tenant"
    KEY = "key"
    USER = "user"
    DOCUMENT = "document"
    DOCUMENT_CATEGORY = "document_category"
    EXTRACTION_RULE = "extraction_rule"
    SESSION = "session"


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


class AuditEventsTable(BaseCrudTable):
    table_name_env = "audit_events_table_name"
    pk_field = AuditEventRecord.TENANT_ID
    sk_field = AuditEventRecord.TIMESTAMP_EVENT_ID
    active_field = ""  # No active field
