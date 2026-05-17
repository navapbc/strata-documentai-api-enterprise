from enum import StrEnum

# === API ===
API_VERSION = "v1"
API_TITLE = "Document AI API"
API_DESCRIPTION = "API for document processing"
API_AUTH_KEY_HEADER_NAME = "API-Key"
DEFAULT_TIMEOUT = 30

# === File validation ===
SUPPORTED_CONTENT_TYPES = (
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
)

# === Document categories ===
DOCUMENT_CATEGORIES = [
    "income",
    "expenses",
    "legal_documents",
    "employment_training",
]

# === Upload / S3 metadata keys ===
UPLOAD_METADATA_KEYS = {
    "job_id": "job-id",
    "original_file_name": "original-file-name",
    "trace_id": "trace-id",
    "user_provided_document_category": "user-provided-document-category",
    "batch_id": "batch-id",
    "build_id": "build-id",
}

# S3 metadata keys (for reading from S3 objects)
S3_METADATA_KEY_USER_PROVIDED_DOCUMENT_CATEGORY = UPLOAD_METADATA_KEYS[
    "user_provided_document_category"
]
S3_METADATA_KEY_JOB_ID = UPLOAD_METADATA_KEYS["job_id"]
S3_METADATA_KEY_TRACE_ID = UPLOAD_METADATA_KEYS["trace_id"]
S3_METADATA_KEY_ORIGINAL_FILE_NAME = UPLOAD_METADATA_KEYS["original_file_name"]
S3_METADATA_KEY_BATCH_ID = UPLOAD_METADATA_KEYS["batch_id"]

# === Batch upload ===
# Max files per batch upload — set to match BDA concurrent job limit (~25) to
# prevent throttling. Can be raised if the BDA quota is raised.
# TODO: make configurable via environment variable for different deployments.
MAX_BATCH_SIZE = 25

# === Metric aggregates (S3 prefixes) ===
S3_RAW_DDB_DATA_PREFIX = "raw/utc/date"
S3_AGG_DDB_DATA_DAILY_PREFIX = "aggregated/utc/date"
S3_AGG_DDB_DATA_MONTHLY_PREFIX = "aggregated/utc/month"

# === Grouped BDA job statuses ===
BDA_JOB_STATUS_RUNNING = ["Created", "InProgress"]
BDA_JOB_STATUS_FAILED = ["ServiceError", "ClientError"]
BDA_JOB_STATUS_COMPLETED = ["Success"]


class APIConfig:
    VERSION = "v1"
    TITLE = "Document AI API"
    DESCRIPTION = "API for document processing"
    AUTH_KEY_HEADER_NAME = "API-Key"
    DEFAULT_TIMEOUT = 30


class BdaJobStatus(StrEnum):
    CREATED = "Created"
    IN_PROGRESS = "InProgress"
    SUCCESS = "Success"
    SERVICE_ERROR = "ServiceError"
    CLIENT_ERROR = "ClientError"


class BdaResponseFields:
    EXPLAINABILITY_INFO = "explainability_info"
    FIELD_CONFIDENCE = "confidence"
    FIELD_VALUE = "value"
    MATCHED_BLUEPRINT = "matched_blueprint"
    MATCHED_BLUEPRINT_NAME = "name"
    MATCHED_BLUEPRINT_CONFIDENCE = "confidence"
    DOCUMENT_CLASS = "document_class"
    DOCUMENT_TYPE = "type"


class Cache:
    KEY_BLUEPRINT_SCHEMAS = "blueprint_schemas"
    TTL_BLUEPRINT_SCHEMAS_MINUTES = 60


class ConfigDefaults:
    FIELD_CONFIDENCE_THRESHOLD = 0.7
    POLL_INTERVAL_SECONDS = 5
    MAX_WAIT_SECONDS = 120
    ALB_TIMEOUT_BUFFER_SECONDS = 15
    USER_DOCUMENT_TYPE_NOT_PROVIDED = "Not specified"
    BDA_REGION_NOT_AVAILABLE = "N/A"
    LOG_RETENTION_DAYS = 30
    BDA_DOCUMENT_DETECTION_MIN_CHAR_LENGTH = 50
    BLURRY_DOCUMENT_THRESHOLD = 25
    BDA_MAX_IMAGE_SIZE_BYTES = 5_242_880
    BDA_MAX_DOCUMENT_FILE_SIZE_BYTES = 524_288_000
    DDB_EMIT_CUSTOM_CLOUDWATCH_METRICS = False
    EMPTY_FIELD_PERCENTAGE_THRESHOLD = 50
    MAX_PAGES_PER_DOCUMENT = 5


class DocumentCategory(StrEnum):
    INCOME = "income"
    EXPENSES = "expenses"
    LEGAL_DOCUMENTS = "legal_documents"
    EMPLOYMENT_TRAINING = "employment_training"


class FileValidation:
    SUPPORTED_CONTENT_TYPES = (
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/tiff",
    )

    @staticmethod
    def is_supported(content_type: str) -> bool:
        return content_type in FileValidation.SUPPORTED_CONTENT_TYPES


class ProcessStatus(StrEnum):
    BLURRY_DOCUMENT_DETECTED = "blurry_document_detected"
    FAILED = "failed"
    MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE = "multiple_documents_single_page"
    NO_CUSTOM_BLUEPRINT_MATCHED = "no_custom_blueprint_matched"
    NO_DOCUMENT_DETECTED = "no_document_detected"
    NOT_IMPLEMENTED = "not_implemented"
    NOT_STARTED = "not_started"
    NOT_SAMPLED = "not_sampled"
    PASSWORD_PROTECTED = "password_protected"
    PENDING_GRAYSCALE_CONVERSION = "pending_grayscale_conversion"
    STARTED = "started"
    SUCCESS = "success"

    @classmethod
    def is_completed(cls, value: str) -> bool:
        return value in [
            cls.SUCCESS,
            cls.FAILED,
            cls.NO_DOCUMENT_DETECTED,
            cls.NO_CUSTOM_BLUEPRINT_MATCHED,
        ]

    @classmethod
    def is_not_supported(cls, value: str) -> bool:
        return value in [cls.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE, cls.PASSWORD_PROTECTED]

    @classmethod
    def is_pending_extraction(cls, value: str) -> bool:
        return value in [cls.PENDING_GRAYSCALE_CONVERSION, cls.NOT_STARTED]

    @classmethod
    def is_successful(cls, value: str) -> bool:
        return value in [
            cls.SUCCESS,
            cls.NO_CUSTOM_BLUEPRINT_MATCHED,
            cls.NOT_SAMPLED,
            cls.NOT_IMPLEMENTED,
        ]


class S3MetadataKeys:
    # S3 metadata keys (for reading from S3 objects)
    USER_PROVIDED_DOCUMENT_CATEGORY = "user-provided-document-category"
    JOB_ID = "job-id"
    TRACE_ID = "trace-id"
    ORIGINAL_FILE_NAME = "original-file-name"
    BATCH_ID = "batch-id"
    BUILD_ID = "build-id"


class BatchStatus(StrEnum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentBuildStatus(StrEnum):
    SUBMITTED = "submitted"
    NOT_SUBMITTED = "not_submitted"
    COMPLETED = "completed"


class PreClassificationDefaults:
    MODEL_ID = "us.amazon.nova-lite-v1:0"
    PROMPT = "\n".join(
        [
            "Analyze this image. Respond in JSON only:",
            '{"document_type": "string", "confidence": float 0-1, "document_count": int, "is_blurry": bool}',
            "ONLY use one of these exact values for document_type: <<DOCUMENT_TYPES>>",
            "Do not create new categories. If unsure, use 'other_document'.",
            "If the image is a photograph, scenery, artwork, or contains no structured text, use 'not_a_document'.",
            "Use 'other_document' ONLY for documents that don't match any listed type.",
            "Set is_blurry to true ONLY if the image appears out of focus, smeared, or motion-blurred.",
            "If is_blurry is true, set confidence below 0.5.",
            "document_count: how many separate documents are visible in this image?",
        ]
    )


class DictionaryFormatType(StrEnum):
    JSON = "json"
    CSV = "csv"


class DictionaryBlueprintSchema(StrEnum):
    FIELDS = "fields"


class DictionaryBlueprintField(StrEnum):
    NAME = "name"
    TYPE = "type"
    DESCRIPTION = "description"
    DOCUMENT_TYPE = "documentType"


class MetricsGranularity(StrEnum):
    DAILY = "daily"
    MONTHLY = "monthly"


class MetricsAggregatorTargetDate:
    TODAY = "today"
    YESTERDAY = "yesterday"


class TimingMetrics:
    TOTAL_PROCESSING_TIME = "total_processing_time"
    BDA_PROCESSING_TIME = "bda_processing_time"
    BDA_WAIT_TIME = "bda_wait_time"


class AthenaQueryStatus:
    """AWS Athena query execution states.

    See: https://docs.aws.amazon.com/athena/latest/APIReference/API_QueryExecutionStatus.html
    Note: AWS uses British spelling 'CANCELLED' (double L). Canceled is preferred
    in American English, while cancelled is standard in British English.
    """

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @staticmethod
    def is_final(status: str) -> bool:
        return status in {
            AthenaQueryStatus.SUCCEEDED,
            AthenaQueryStatus.FAILED,
            AthenaQueryStatus.CANCELLED,
        }
