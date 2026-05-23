"""Schema for the tenants DynamoDB table."""


class TenantRecord:
    """Field names for the tenants DynamoDB table."""

    TENANT_ID = "tenantId"
    DISPLAY_NAME = "displayName"
    PRIMARY_CONTACT = "primaryContact"
    IS_ACTIVE = "isActive"
    CREATED_AT = "createdAt"
    UPDATED_AT = "updatedAt"
