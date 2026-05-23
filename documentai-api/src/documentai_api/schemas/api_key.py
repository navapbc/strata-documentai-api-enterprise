"""Schema for the api-keys DynamoDB table."""


class ApiKeyRecord:
    """Field names for the api-keys DynamoDB table."""

    KEY_HASH = "keyHash"
    CLIENT_NAME = "clientName"
    TENANT_ID = "tenantId"
    ENVIRONMENT = "environment"
    IS_ACTIVE = "isActive"
    CREATED_AT = "createdAt"
    EXPIRES_AT = "expiresAt"
    LAST_USED = "lastUsed"
    CREATED_BY = "createdBy"
    EMAIL_ADDRESS = "emailAddress"
