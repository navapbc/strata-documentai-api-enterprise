"""Schema for the api-keys DynamoDB table."""


class ApiKeyRecord:
    """Field names for the api-keys DynamoDB table."""

    KEY_HASH = "keyHash"
    # IMPORTANT: api_key_name is immutable after creation. It is written to
    # document/batch/build metadata as an audit trail. Renaming would break
    # the correlation between keys and the records they processed.
    API_KEY_NAME = "apiKeyName"
    TENANT_ID = "tenantId"
    ENVIRONMENT = "environment"
    IS_ACTIVE = "isActive"
    CREATED_AT = "createdAt"
    EXPIRES_AT = "expiresAt"
    LAST_USED = "lastUsed"
    CREATED_BY = "createdBy"
    EMAIL_ADDRESS = "emailAddress"
