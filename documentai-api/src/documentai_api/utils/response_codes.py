class ResponseCodes:
    SUCCESS = "000"
    DOCUMENT_TYPE_NOT_IMPLEMENTED = "002"
    AI_CONSENT_DECLINED = "003"
    MISSING_FIELDS = "101"
    MISCATEGORIZED = "102"
    NO_DOCUMENT_DETECTED = "103"
    BLURRY_DOCUMENT_DETECTED = "104"
    LOW_EXTRACTION_CONFIDENCE = "105"
    PASSWORD_PROTECTED = "106"
    MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE = "400"
    INTERNAL_PROCESSING_ERROR = "999"

    @classmethod
    def get_message(cls, code: str) -> str:
        """Get message for response code."""
        messages = {
            cls.SUCCESS: "Document validation passed",
            cls.DOCUMENT_TYPE_NOT_IMPLEMENTED: "Document type not implemented",
            cls.AI_CONSENT_DECLINED: "Document not processed - AI consent not provided",
            cls.MISSING_FIELDS: "Missing fields",
            cls.MISCATEGORIZED: "Document category mismatch",
            cls.LOW_EXTRACTION_CONFIDENCE: "Average field confidence below tenant threshold",
            cls.PASSWORD_PROTECTED: "Password protected document",
            cls.NO_DOCUMENT_DETECTED: "No document detected",
            cls.BLURRY_DOCUMENT_DETECTED: "Document is blurry",
            cls.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE: "Multiple documents detected on single page",
            cls.INTERNAL_PROCESSING_ERROR: "Internal processing error",
        }
        return messages.get(code, "")

    @classmethod
    def is_success_response_code(cls, code: str) -> bool:
        """Check if response code indicates success (0xx codes)."""
        return code.startswith("0")

    @classmethod
    def get_all(cls) -> list[dict[str, str]]:
        return [
            {"code": v, "message": cls.get_message(v)}
            for k, v in vars(cls).items()
            if not k.startswith("_") and isinstance(v, str) and v[0].isdigit()
        ]
