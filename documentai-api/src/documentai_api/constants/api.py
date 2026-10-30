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
    ADMIN_API_KEYS = "Admin:API Keys"
    ADMIN_AUDIT_LOG = "Admin:Audit Log"
    ADMIN_BLUEPRINTS = "Admin:Blueprints"
    ADMIN_CATEGORIES = "Admin:Categories"
    ADMIN_COMPARE = "Admin:Compare"
    ADMIN_DOCUMENTS = "Admin:Documents"
    ADMIN_TENANTS = "Admin:Tenants"
    ADMIN_USERS = "Admin:Users"
    BUILDS_LIFECYCLE = "Builds:Lifecycle"
    BUILDS_PAGES = "Builds:Pages"
    BUILDS_STATUS = "Builds:Status"
    CONFIG_RULES = "Config:Rules"
    DICTIONARY_FIELDS = "Dictionary:Fields"
    DICTIONARY_REFERENCE = "Dictionary:Reference"
    DICTIONARY_SCHEMAS = "Dictionary:Schemas"
    DOCUMENTS_DELETE = "Documents:Delete"
    DOCUMENTS_QUERY = "Documents:Query"
    DOCUMENTS_UPLOAD = "Documents:Upload"
    IDENTITY = "Identity"
