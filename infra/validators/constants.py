"""Infrastructure validation constants."""


class DriftStatus:
    PRESENT = "PRESENT"
    MISSING = "MISSING"
    DRIFTED = "DRIFTED"
    UNDISCOVERABLE = "UNDISCOVERABLE"


class Tag:
    UNTAGGED = "_untagged"


class AwsErrorCode:
    REPOSITORY_NOT_FOUND = "RepositoryNotFoundException"
    RESOURCE_NOT_FOUND = "ResourceNotFoundException"
    ENTITY_NOT_FOUND = "EntityNotFoundException"
    NO_SUCH_ENTITY = "NoSuchEntity"
    PARAMETER_NOT_FOUND = "ParameterNotFound"
    SQS_NON_EXISTENT_QUEUE = "AWS.SimpleQueueService.NonExistentQueue"


# Required Lambda environment variable keys.
# Source: local.lambda_env_vars in environments/dev/main.tf
# If that local changes, update this set.
REQUIRED_LAMBDA_ENV_VARS: set[str] = {
    "API_AUTH_ENABLED",
    "API_AUTH_INSECURE_SHARED_KEY_PARAM",
    "API_KEYS_TABLE_NAME",
    "AUDIT_EVENTS_TABLE_NAME",
    "BDA_PROFILE_ARN",
    "BDA_PROJECT_ARN",
    "BDA_REGION",
    "DDB_EXPORT_BUCKET_NAME",
    "DDB_METRICS_INPUT_QUEUE_URL",
    "DOCUMENTAI_BATCH_TABLE_NAME",
    "DOCUMENTAI_DOCUMENT_BUILD_TABLE_NAME",
    "DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME",
    "DOCUMENTAI_INPUT_LOCATION",
    "DOCUMENTAI_OUTPUT_LOCATION",
    "DOCUMENT_CATEGORIES_TABLE_NAME",
    "ENVIRONMENT",
    "EXTRACTION_RULES_TABLE_NAME",
    "SSM_PREFIX",
    "TENANTS_TABLE_NAME",
}
