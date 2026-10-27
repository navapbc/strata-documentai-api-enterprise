class ApiMetadata:
    VERSION = "v1"
    TITLE = "Document AI API"
    DESCRIPTION = "API for document processing"
    AUTH_KEY_HEADER_NAME = "API-Key"
    DEFAULT_TIMEOUT = 30


class V1JobStatus:
    """jobStatus values used in v1 API responses.

    These are the external-facing status strings written into v1ApiResponseJson
    and returned by the v1 API. Distinct from the internal ProcessStatus enum.
    """

    AI_CONSENT_DECLINED = "ai_consent_declined"
    COMPLETED = "completed"
    CONVERSION_FAILED = "conversion_failed"
    DELETED = "deleted"
    FAILED = "failed"
    PROCESSING = "processing"


class ApiVisualizationTag:
    DOCUMENTS_UPLOAD = "Documents:Upload"
    DOCUMENTS_QUERY = "Documents:Query"
    DOCUMENTS_DELETE = "Documents:Delete"
    BUILDS_LIFECYCLE = "Builds:Lifecycle"
    BUILDS_PAGES = "Builds:Pages"
    BUILDS_STATUS = "Builds:Status"
    DICTIONARY_SCHEMAS = "Dictionary:Schemas"
    DICTIONARY_FIELDS = "Dictionary:Fields"
    DICTIONARY_REFERENCE = "Dictionary:Reference"
    CONFIG_RULES = "Config:Rules"
    ADMIN_API_KEYS = "Admin:API Keys"
    ADMIN_TENANTS = "Admin:Tenants"
    ADMIN_USERS = "Admin:Users"
    ADMIN_AUDIT_LOG = "Admin:Audit Log"
    ADMIN_DOCUMENTS = "Admin:Documents"
    ADMIN_CATEGORIES = "Admin:Categories"
    ADMIN_BLUEPRINTS = "Admin:Blueprints"
    IDENTITY = "Identity"
