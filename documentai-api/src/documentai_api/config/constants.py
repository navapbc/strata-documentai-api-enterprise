from enum import StrEnum
from typing import ClassVar

# === API ===
API_VERSION = "v1"
API_TITLE = "Document AI API"
API_DESCRIPTION = "API for document processing"
API_AUTH_KEY_HEADER_NAME = "API-Key"
DEFAULT_TIMEOUT = 30

# === Document categories ===

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
# Max files per batch upload - set to match BDA concurrent job limit (~25) to
# prevent throttling. Can be raised if the BDA quota is raised.
# TODO: make configurable via environment variable for different deployments.
MAX_BATCH_SIZE = 25
MAX_PAGES_PER_BUILD = 50
MAX_SEARCH_JOB_IDS = 25

# Default error message for DDB persistence (avoids leaking exception internals)
DEFAULT_DDB_ERROR_MESSAGE = "Internal processing error"

# ZIP extraction limits
MAX_ZIP_DECOMPRESSION_RATIO = 100
MAX_ZIP_EXTRACTED_BYTES = 500 * 1024 * 1024  # 500MB

# === Metric aggregates (S3 prefixes) ===
S3_RAW_DDB_DATA_PREFIX = "raw/utc/date"
S3_AGG_DDB_DATA_DAILY_PREFIX = "aggregated/utc/date"
S3_AGG_DDB_DATA_MONTHLY_PREFIX = "aggregated/utc/month"

# === Grouped BDA job statuses ===
BDA_JOB_STATUS_RUNNING = ["Created", "InProgress"]
BDA_JOB_STATUS_FAILED = ["ServiceError", "ClientError"]
BDA_JOB_STATUS_COMPLETED = ["Success"]


UUID_PATTERN = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


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

    @classmethod
    def is_running(cls, status: str) -> bool:
        return status in (cls.CREATED, cls.IN_PROGRESS)

    @classmethod
    def is_completed(cls, status: str) -> bool:
        return status == cls.SUCCESS

    @classmethod
    def is_failed(cls, status: str) -> bool:
        return status in (cls.SERVICE_ERROR, cls.CLIENT_ERROR)


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
    DOCUMENT_BATCHES_TTL_DAYS = 30
    DOCUMENT_BUILDS_TTL_DAYS = 30
    DOCUMENT_METADATA_TTL_DAYS = 180
    BDA_DOCUMENT_DETECTION_MIN_CHAR_LENGTH = 50
    BLURRY_DOCUMENT_THRESHOLD = 25
    BDA_MAX_IMAGE_SIZE_BYTES = 5_242_880
    BDA_MAX_DOCUMENT_FILE_SIZE_BYTES = 524_288_000
    DDB_EMIT_CUSTOM_CLOUDWATCH_METRICS = False
    EMPTY_FIELD_PERCENTAGE_THRESHOLD = 50
    MAX_PAGES_PER_DOCUMENT = 5


# Document categories - must match the BDA project keys in infra/environments/*/main.tf
class DocumentCategory(StrEnum):
    INCOME = "income"
    EXPENSES = "expenses"
    IDENTITY = "identity"
    EMPLOYMENT = "employment"
    TRAINING = "training"


class FileValidation:
    NO_CONVERSION_NEEDED = (
        "application/pdf",
        "image/jpeg",
        "image/png",
    )

    REQUIRES_CONVERSION = (
        "image/bmp",
        "image/heic",
        "image/heif",
        "image/webp",
        "image/gif",
        "image/tiff",
    )

    SUPPORTED_CONTENT_TYPES = NO_CONVERSION_NEEDED + REQUIRES_CONVERSION

    GRAYSCALE_CONVERTIBLE = (
        "image/jpeg",
        "image/png",
    )

    @staticmethod
    def is_supported(content_type: str) -> bool:
        return content_type in FileValidation.SUPPORTED_CONTENT_TYPES

    @staticmethod
    def needs_conversion(content_type: str) -> bool:
        return content_type in FileValidation.REQUIRES_CONVERSION

    CONTENT_TYPE_TO_EXT: ClassVar[dict[str, str]] = {
        "application/pdf": "pdf",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/tiff": "tiff",
        "image/bmp": "bmp",
        "image/heic": "heic",
        "image/heif": "heif",
        "image/webp": "webp",
        "image/gif": "gif",
    }

    @staticmethod
    def get_extension(content_type: str) -> str:
        return FileValidation.CONTENT_TYPE_TO_EXT.get(content_type, "bin")


class ProcessStatus(StrEnum):
    AI_CONSENT_DECLINED = "ai_consent_declined"
    BLURRY_DOCUMENT_DETECTED = "blurry_document_detected"
    CONVERSION_FAILED = "conversion_failed"
    DELETED = "deleted"
    FAILED = "failed"
    MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE = "multiple_documents_single_page"
    NO_CUSTOM_BLUEPRINT_MATCHED = "no_custom_blueprint_matched"
    NO_DOCUMENT_DETECTED = "no_document_detected"
    NOT_IMPLEMENTED = "not_implemented"
    NOT_STARTED = "not_started"
    NOT_SAMPLED = "not_sampled"
    PASSWORD_PROTECTED = "password_protected"
    PENDING_IMAGE_OPTIMIZATION = "pending_image_optimization"
    PENDING_UPLOAD = "pending_upload"
    STARTED = "started"
    SUCCESS = "success"

    @classmethod
    def is_completed(cls, value: str) -> bool:
        return value in [
            cls.AI_CONSENT_DECLINED,
            cls.CONVERSION_FAILED,
            cls.SUCCESS,
            cls.FAILED,
            cls.NO_DOCUMENT_DETECTED,
            cls.NO_CUSTOM_BLUEPRINT_MATCHED,
        ]

    @classmethod
    def is_classified(cls, value: str) -> bool:
        return value in [
            cls.AI_CONSENT_DECLINED,
            cls.BLURRY_DOCUMENT_DETECTED,
            cls.CONVERSION_FAILED,
            cls.DELETED,
            cls.FAILED,
            cls.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
            cls.NO_CUSTOM_BLUEPRINT_MATCHED,
            cls.NO_DOCUMENT_DETECTED,
            cls.NOT_IMPLEMENTED,
            cls.NOT_SAMPLED,
            cls.PASSWORD_PROTECTED,
            cls.SUCCESS,
        ]

    @classmethod
    def is_not_supported(cls, value: str) -> bool:
        return value in [cls.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE, cls.PASSWORD_PROTECTED]

    @classmethod
    def is_pending_extraction(cls, value: str) -> bool:
        return value in [cls.PENDING_IMAGE_OPTIMIZATION, cls.NOT_STARTED]

    @classmethod
    def is_awaiting_processing(cls, value: str) -> bool:
        return value in [cls.NOT_STARTED, cls.PENDING_UPLOAD]

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


class UploadMethod(StrEnum):
    DIRECT = "direct"
    PRESIGNED = "presigned"
    BATCH = "batch"
    BATCH_ZIP = "batch_zip"
    BUILD = "build"


class DocumentBuildStatus(StrEnum):
    SUBMITTED = "submitted"
    NOT_SUBMITTED = "not_submitted"
    COMPLETED = "completed"


class PreclassificationCategory(StrEnum):
    TAX_DOCUMENTS = "tax_documents"
    EMPLOYMENT_WAGES = "employment_wages"
    INDEPENDENT_EARNINGS = "independent_earnings"
    GOVERNMENT_BENEFITS = "government_benefits"
    PRIVATE_BENEFITS_AND_SETTLEMENTS = "private_benefits_and_settlements"
    COURT_ORDERED_BENEFITS = "court_ordered_benefits"
    FINANCIAL_ASSETS = "financial_assets"
    RECEIPTS_AND_INVOICES = "receipts_and_invoices"
    RECURRING_BILLS = "recurring_bills"
    HOUSING_EXPENSES = "housing_expenses"
    DEBT_OBLIGATIONS = "debt_obligations"
    IDENTITY_VERIFICATION = "identity_verification"
    RIGHT_TO_WORK = "right_to_work"
    SYSTEM_REJECT = "system_reject"


class PreClassificationDefaults:
    MODEL_ID = "us.amazon.nova-lite-v1:0"
    # Converse API supports more document types (csv, html, txt, md, docx, xlsx)
    # but those are rejected at the upload layer before reaching preclassification.
    SUPPORTED_CONTENT_TYPES = (
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "application/pdf",
    )
    PROMPT = "\n".join(
        [
            "Classify this document into one of the categories below. Respond in JSON only:",
            '{"document_type": "string", "confidence": float 0-1, "document_count": int, "is_blurry": bool}',
            "",
            "Categories and their document types:",
            "- tax_documents: W-2, 1040, 1099-INT, 1099-MISC, 1099-G",
            "- employment_wages: Paystubs, payslips, earnings statements",
            "- independent_earnings: Gig platform summaries (Uber, DoorDash, Etsy), freelance 1099-NEC",
            "- government_benefits: Social Security letters (SSI/SSDI), unemployment award letters",
            "- private_benefits_and_settlements: Pension statements, life insurance payouts, annuities",
            "- court_ordered_benefits: Child support orders, alimony decrees, divorce agreements",
            "- financial_assets: Bank statements, 401(k) summaries, brokerage statements",
            "- receipts_and_invoices: Point-of-sale receipts, vendor invoices",
            "- recurring_bills: Electric, water, gas, phone, internet, insurance bills",
            "- housing_expenses: Rental leases, landlord payment ledgers, HOA letters",
            "- debt_obligations: Mortgage statements, auto loan bills, student loans, credit card statements",
            "- identity_verification: Driver's license, passport, state ID, Global Entry card",
            "- right_to_work: Form I-9, work permits, EAD cards, visa stamps",
            "- system_reject: Blurry photos, blank pages, corrupted files, non-document images",
            "",
            "ONLY use one of the exact category names listed above for document_type.",
            "Do not create new categories. If unsure, use 'other_document'.",
            "Use 'system_reject' for blurry, blank, corrupted, or non-document images.",
            "Set is_blurry to true ONLY if the document appears out of focus, smeared, or motion-blurred.",
            "If is_blurry is true, set confidence below 0.5 and use 'system_reject'.",
            "document_count: how many separate documents are visible?",
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


ATHENA_QUERY_TIMEOUT_SECONDS = 300
