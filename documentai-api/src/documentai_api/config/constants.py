import re
from collections.abc import Iterable
from enum import StrEnum
from typing import ClassVar

import filetype  # type: ignore[import-untyped]

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

# Upload size limit
MAX_UPLOAD_SIZE_BYTES = 500 * 1024 * 1024  # 500MB

# ZIP extraction limits
MAX_ZIP_DECOMPRESSION_RATIO = 100
MAX_ZIP_EXTRACTED_BYTES = 500 * 1024 * 1024  # 500MB

# === Metric aggregates (S3 prefixes) ===
METRICS_RAW_DDB_DATA_S3_PREFIX = "raw/utc/date"
METRICS_AGG_DDB_DAILY_S3_PREFIX = "aggregated/utc/date"
METRICS_AGG_DDB_MONTHLY_S3_PREFIX = "aggregated/utc/month"
METRICS_USAGE_REPORT_S3_PREFIX = "usage-report/month"
METRICS_USAGE_REPORT_DAILY_S3_PREFIX = "usage-report/utc/date"

# === Grouped BDA job statuses ===
BDA_JOB_STATUS_RUNNING = ["Created", "InProgress"]
BDA_JOB_STATUS_FAILED = ["ServiceError", "ClientError"]
BDA_JOB_STATUS_COMPLETED = ["Success"]
BDA_PROJECT_KEY_ALL = "all"


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
    FIELD_TYPE = "type"
    FIELD_GEOMETRY = "geometry"
    MATCHED_BLUEPRINT = "matched_blueprint"
    MATCHED_BLUEPRINT_NAME = "name"
    MATCHED_BLUEPRINT_CONFIDENCE = "confidence"
    DOCUMENT_CLASS = "document_class"
    DOCUMENT_TYPE = "type"


class ConfigDefaults:
    FIELD_CONFIDENCE_THRESHOLD = 0.65
    POLL_INTERVAL_SECONDS = 5
    BDA_REGION_NOT_AVAILABLE = "N/A"
    LOG_RETENTION_DAYS = 30
    DOCUMENT_BATCHES_TTL_DAYS = 30
    DOCUMENT_BUILDS_TTL_DAYS = 30
    DOCUMENT_METADATA_TTL_DAYS = 180
    DEMO_DOCUMENT_TTL_DAYS = 7
    TENANT_REQUEST_COUNTS_TTL_DAYS = 365 * 5
    BDA_DOCUMENT_DETECTION_MIN_CHAR_LENGTH = 50
    BLURRY_DOCUMENT_THRESHOLD = 25

    # Textract-based blur detection thresholds
    BLUR_CONFIDENCE_FLOOR = 70.0  # per-word confidence % below which a word is "low confidence"
    BLUR_MIN_WORD_COUNT = 5  # fewer words than this -> is_not_document (too sparse to evaluate)
    BLUR_LOW_CONFIDENCE_MAX_PERCENT = (
        30.0  # if >30% of words in a quadrant are below floor -> blurry
    )
    BLUR_QUADRANT_MIN_AVG_CONFIDENCE = 85.0  # per-quadrant avg confidence below this -> blurry
    BLUR_TEXT_DENSE_MIN_WORDS = (
        20  # total words needed to consider empty quadrants suspicious (LLM fallback gate)
    )
    BLUR_QUADRANT_MODEL_ID = "us.amazon.nova-pro-v1:0"  # model for empty-quadrant blur check (Pro needed for spatial reasoning)
    MISSING_GEOMETRY_CONFIDENCE_THRESHOLD = 0.25
    BDA_MAX_IMAGE_SIZE_BYTES = 5_242_880

    # PIL pixel limit for DecompressionBomb protection. 60 MP covers high-res phone
    # photos of ID documents (typical range 8-48 MP) while still bounding memory use.
    MAX_IMAGE_PIXELS = 60_000_000

    BDA_MAX_DOCUMENT_FILE_SIZE_BYTES = 524_288_000
    # Bedrock Converse per-image limits (used by the vision bbox-detection call).
    # The real API ceiling is 3.75MB / 8000px per image - stricter than the 5MB BDA
    # limit above - so oversized images are downscaled in-memory just for detection.
    BEDROCK_CONVERSE_MAX_IMAGE_BYTES = 3_750_000
    BEDROCK_CONVERSE_MAX_IMAGE_DIMENSION_PX = 8000
    DDB_EMIT_CUSTOM_CLOUDWATCH_METRICS = False
    MAX_PAGES_PER_DOCUMENT = 5
    PRESIGNED_URL_SIGNATURE_VERSION = "s3v4"
    PRESIGNED_PREVIEW_EXPIRY_SECONDS = 300
    PROCESSING_PERCENTAGE_CACHE_TTL_MINUTES = 5


class FileValidation:
    # === Office document MIME types ===
    PDF_MIME = "application/pdf"
    DOC_MIME = "application/msword"
    DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

    # === Office container detection ===
    # ZIP local-file-header magic (all OOXML: docx/xlsx/pptx). OLE2/Compound File
    # magic covers legacy .doc/.xls AND ECMA-376-encrypted OOXML.
    ZIP_MAGIC = b"PK\x03\x04"
    OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

    # OOXML archive member prefix -> MIME. filetype only scans the first ~6KB of
    # the archive for this entry, so it misses it in newer Office layouts;
    # detect_ooxml_mime inspects the full member list instead.
    OOXML_MEMBER_MIME: ClassVar[tuple[tuple[str, str], ...]] = (
        ("word/", DOCX_MIME),
        ("xl/", XLSX_MIME),
        ("ppt/", PPTX_MIME),
    )

    # OLE2 stores stream names as UTF-16LE. An ECMA-376-encrypted OOXML package
    # carries these two streams; presence identifies a password-protected doc.
    OOXML_ENCRYPTION_MARKERS: ClassVar[tuple[bytes, ...]] = (
        "EncryptionInfo".encode("utf-16-le"),
        "EncryptedPackage".encode("utf-16-le"),
    )

    @staticmethod
    def is_office_container_magic(data: bytes) -> bool:
        """True if bytes start with a ZIP or OLE2 signature.

        These container formats (OOXML, and legacy/encrypted Office docs) can't be
        identified from a header alone - the caller must read the full file for
        detect_ooxml_mime / has_ooxml_encryption_markers to work. Everything else
        is a simple magic-number format that a header probe resolves.
        """
        return data.startswith((FileValidation.ZIP_MAGIC, FileValidation.OLE2_MAGIC))

    @staticmethod
    def detect_ooxml_mime(member_names: Iterable[str]) -> str | None:
        """Map an OOXML archive's member names to its MIME type, or None if not OOXML."""
        names = list(member_names)
        for prefix, mime in FileValidation.OOXML_MEMBER_MIME:
            if any(name.startswith(prefix) for name in names):
                return mime
        return None

    @staticmethod
    def has_ooxml_encryption_markers(data: bytes) -> bool:
        """True if bytes carry the OLE2 streams of an ECMA-376-encrypted OOXML package."""
        return all(marker in data for marker in FileValidation.OOXML_ENCRYPTION_MARKERS)

    NO_CONVERSION_NEEDED = (
        PDF_MIME,
        DOC_MIME,
        DOCX_MIME,
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

    PREVIEWABLE_TYPES = (
        "application/pdf",
        "image/jpeg",
        "image/png",
    )

    GRAYSCALE_CONVERTIBLE = (
        "image/jpeg",
        "image/png",
    )

    ODT_CONTENT_TYPES = ("application/vnd.oasis.opendocument.text",)

    @staticmethod
    def is_pdf(data: bytes) -> bool:
        return data[:4] == b"%PDF"

    @staticmethod
    def is_image(data: bytes) -> bool:
        mime = filetype.guess_mime(data)
        return (
            mime is not None
            and mime in FileValidation.SUPPORTED_CONTENT_TYPES
            and mime.startswith("image/")
        )

    @staticmethod
    def is_supported(content_type: str) -> bool:
        return content_type in FileValidation.SUPPORTED_CONTENT_TYPES

    @staticmethod
    def needs_conversion(content_type: str) -> bool:
        return content_type in FileValidation.REQUIRES_CONVERSION

    @staticmethod
    def is_odt(content_type: str) -> bool:
        return content_type in FileValidation.ODT_CONTENT_TYPES

    CONTENT_TYPE_TO_EXT: ClassVar[dict[str, str]] = {
        PDF_MIME: "pdf",
        DOC_MIME: "doc",
        DOCX_MIME: "docx",
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
    def get_extension(content_type: str, unknown: str = "bin") -> str:
        ct = content_type.lower().split(";")[0].strip()
        return FileValidation.CONTENT_TYPE_TO_EXT.get(ct, unknown)


class TextractConfig:
    """Textract AnalyzeID configuration."""

    # Content types supported by Textract AnalyzeID (inline bytes)
    SUPPORTED_CONTENT_TYPES = (
        "image/jpeg",
        "image/png",
        "application/pdf",
    )


class DeletionType(StrEnum):
    """How a document was deleted, recorded on the DDB record when DELETED."""

    SOFT = "soft"  # record marked deleted, S3 file retained (recoverable)
    HARD = "hard"  # record marked deleted, S3 file removed


class ProcessStatus(StrEnum):
    AI_CONSENT_DECLINED = "ai_consent_declined"
    BLURRY_DOCUMENT_DETECTED = "blurry_document_detected"
    CONVERSION_FAILED = "conversion_failed"
    DELETED = "deleted"
    EXCLUDED_PER_PRECLASSIFICATION = "excluded_per_preclassification"
    FAILED = "failed"
    MULTIPLE_DOCUMENTS_IN_MULTIPAGE = "multiple_documents_in_multipage"
    MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE = "multiple_documents_single_page"
    NO_CUSTOM_BLUEPRINT_MATCHED = "no_custom_blueprint_matched"
    NO_DOCUMENT_DETECTED = "no_document_detected"
    NOT_IMPLEMENTED = "not_implemented"
    NOT_STARTED = "not_started"
    PASSWORD_PROTECTED = "password_protected"
    PENDING_IMAGE_OPTIMIZATION = "pending_image_optimization"
    PENDING_UPLOAD = "pending_upload"
    PROCESSING_EXCLUDED = "processing_excluded"
    STARTED = "started"
    SUCCESS = "success"

    @classmethod
    def is_completed(cls, value: str) -> bool:
        return value in [
            cls.AI_CONSENT_DECLINED,
            cls.CONVERSION_FAILED,
            cls.PROCESSING_EXCLUDED,
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
            cls.MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
            cls.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
            cls.NO_CUSTOM_BLUEPRINT_MATCHED,
            cls.NO_DOCUMENT_DETECTED,
            cls.NOT_IMPLEMENTED,
            cls.EXCLUDED_PER_PRECLASSIFICATION,
            cls.PASSWORD_PROTECTED,
            cls.PROCESSING_EXCLUDED,
            cls.SUCCESS,
        ]

    @classmethod
    def is_not_supported(cls, value: str) -> bool:
        return value in [
            cls.MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
            cls.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
            cls.PASSWORD_PROTECTED,
        ]

    @classmethod
    def is_pending_extraction(cls, value: str) -> bool:
        return value in [cls.PENDING_IMAGE_OPTIMIZATION, cls.NOT_STARTED]

    @classmethod
    def is_awaiting_processing(cls, value: str) -> bool:
        return value in [cls.NOT_STARTED, cls.PENDING_UPLOAD]

    @classmethod
    def pending_message(cls, value: str) -> str:
        """Human-readable message for a document with no final result yet.

        Distinguishes a document still awaiting pickup by the processor from one
        that is actively being processed, so a stalled or never-claimed document
        does not misreport as "Processing in progress".
        """
        if cls.is_awaiting_processing(value):
            return "Awaiting processing"
        return "Processing in progress"

    @classmethod
    def is_successful(cls, value: str) -> bool:
        return value in [
            cls.SUCCESS,
            cls.NO_CUSTOM_BLUEPRINT_MATCHED,
            cls.NOT_IMPLEMENTED,
            cls.EXCLUDED_PER_PRECLASSIFICATION,
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


class UploadSource(StrEnum):
    DESKTOP = "desktop"
    MOBILE = "mobile"


class DocumentBuildStatus(StrEnum):
    SUBMITTED = "submitted"
    NOT_SUBMITTED = "not_submitted"
    COMPLETED = "completed"


class PreClassificationDefaults:
    MODEL_ID = "us.amazon.nova-pro-v1:0"
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
            'Analyze the provided document against the target category: "{user_category}".',
            "",
            "First, perform this evaluation step-by-step:",
            "1. Examine the visual layout of the page. Look for distinct borders, separate rectangles, multiple photos, or independent snippets (e.g., multiple receipts or cards placed on a single scanner bed).",
            "2. For each page, count how many individual, separate documents or items are visually present. max_document_count_on_page is the highest per-page count across the document, not a sum across pages.",
            "3. Evaluate multi-page consistency: pages belong together only if they are clearly continuation pages of the exact same document instance for the exact same individual (e.g. page 2 of the same W2, the same bank statement continued).",
            '4. Check if the document is directly and primarily a "{user_category}" document.',
            '   - Set category_match to false if: the document type does not match "{user_category}", max_document_count_on_page > 1, or has_multipage_inconsistency is true.',
            "",
            "Then, output your final answer strictly as a raw JSON object with no markdown formatting or backticks:",
            "{",
            '  "document_type": "<short description>",',
            '  "confidence": <float between 0.0 and 1.0>,',
            '  "max_document_count_on_page": <integer, maximum number of distinct visual document items found on any single page>,',
            '  "max_document_count_on_page_reason": "<brief explanation of what was counted on each page>",',
            '  "has_multipage_inconsistency": <false only if all pages are continuations of the exact same document instance for the exact same individual, otherwise true>,',
            '  "has_multipage_inconsistency_reason": "<brief explanation of why pages are consistent or inconsistent>",',
            '  "category_match": <true or false based on step 4>,',
            '  "is_identity_document": <true if passport or driver\'s license, else false>',
            "}",
        ]
    )


class PreprocessingBoundingBoxDefault:
    """Defaults for document bounding-box detection used to crop images before BDA."""

    # Vision model used for ROI detection. Kept separate from the preclassification
    # model so the two can be tuned/swapped independently (they happen to share a
    # default today, but bbox detection and classification are different tasks).
    MODEL_ID = "us.amazon.nova-lite-v1:0"

    PROMPT = "\n".join(
        [
            "Locate the single primary document, ID card, or form in this image.",
            "Return ONLY its bounding box as JSON, no other text:",
            '{"bounding_box": [x1, y1, x2, y2]}',
            "Coordinates use a 0-1000 scale (x1,y1 = top-left, x2,y2 = bottom-right).",
            "Draw the box tightly around the document, excluding background, hands, and surfaces.",
            'If no document is clearly present, respond {"bounding_box": null}.',
        ]
    )

    # tolerant of the malformed JSON vision models routinely emit (stray brackets,
    # missing braces): pulls the four bounding_box numbers rather than json.loads.
    ARRAY_RE = re.compile(
        r"bounding_box\"?\s*:\s*\[\s*"
        r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*"
        r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)"
    )


class OutputFormatType(StrEnum):
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


class MetricsDisplayValues:
    NOT_SPECIFIED = "not specified"
    _LEGACY_UNSET = ("unknown", "not specified", "null", "")

    @staticmethod
    def is_legacy_unset(value: str) -> bool:
        return value.strip().lower() in MetricsDisplayValues._LEGACY_UNSET


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


class ExtractMethod(StrEnum):
    """Which extraction engine produced the result."""

    BDA = "bda"
    TEXTRACT = "textract"


class FeatureFlags:
    DOCUMENT_CROP = "document-crop"
    ENABLE_BLUR_DETECTION = "enable-blur-detection"
    ENFORCE_BLUR_REJECTION = "enforce-blur-rejection"
    TEXTRACT_IDENTITY_ENABLED = "textract-identity-enabled"
    INCLUDE_MISSING_GEO_WITH_MISSING_FIELDS = "include-missing-geo-with-missing-fields"
    PRECLASSIFICATION_BASED_ROUTING = "preclassification-based-routing"
    SKIP_BDA_IF_UNCLASSIFIED = "skip-bda-if-unclassified"
    ENABLE_PRECLASSIFICATION_BLUEPRINT_MATCHING = "enable-preclassification-blueprint-matching"
    FLAG_MULTIPLE_DOCUMENTS_IN_MULTIPAGE = "flag-multiple-documents-in-multipage"


ATHENA_QUERY_TIMEOUT_SECONDS = 300
