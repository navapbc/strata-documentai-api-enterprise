from enum import StrEnum


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
    BLUEPRINT_DISABLED = "blueprint_disabled"
    PROCESSING_EXCLUDED = "processing_excluded"
    STARTED = "started"
    SUCCESS = "success"
    TIMED_OUT = "timed_out"

    @classmethod
    def is_completed(cls, value: str) -> bool:
        return value in [
            cls.AI_CONSENT_DECLINED,
            cls.BLUEPRINT_DISABLED,
            cls.CONVERSION_FAILED,
            cls.PROCESSING_EXCLUDED,
            cls.SUCCESS,
            cls.FAILED,
            cls.NO_DOCUMENT_DETECTED,
            cls.NO_CUSTOM_BLUEPRINT_MATCHED,
            cls.TIMED_OUT,
        ]

    @classmethod
    def is_classified(cls, value: str) -> bool:
        return value in [
            cls.AI_CONSENT_DECLINED,
            cls.BLUEPRINT_DISABLED,
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
            cls.TIMED_OUT,
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

    @classmethod
    def non_terminal(cls) -> list["ProcessStatus"]:
        return [
            cls.STARTED,
            cls.NOT_STARTED,
            cls.PENDING_UPLOAD,
            cls.PENDING_IMAGE_OPTIMIZATION,
        ]

    @classmethod
    def build_ddb_non_terminal_condition(cls) -> tuple[str, dict[str, str]]:
        values = {f":nt{i}": s.value for i, s in enumerate(cls.non_terminal())}
        placeholders = ", ".join(values)
        condition = f"attribute_not_exists(processStatus) OR processStatus IN ({placeholders})"
        return condition, values


class BatchStatus(StrEnum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"
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


class ExtractMethod(StrEnum):
    """Which extraction engine produced the result."""

    BDA = "bda"
    TEXTRACT = "textract"
    OCR_MAPPING = "ocr-mapping"


class OutputFormatType(StrEnum):
    JSON = "json"
    CSV = "csv"


class LlmUsageReason(StrEnum):
    """Which pipeline step consumed the tokens."""

    PRECLASSIFICATION = "preclassification"
    BLUEPRINT_MATCH = "blueprintMatch"
    OCR_MAPPING = "ocrMapping"
    CROP_DETECTION = "cropDetection"


class S3MetadataKeys:
    USER_PROVIDED_DOCUMENT_CATEGORY = "user-provided-document-category"
    JOB_ID = "job-id"
    TRACE_ID = "trace-id"
    ORIGINAL_FILE_NAME = "original-file-name"
    BATCH_ID = "batch-id"
    BUILD_ID = "build-id"
