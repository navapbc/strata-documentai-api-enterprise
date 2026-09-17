"""Check statuses, keys, pipeline order, and skip reasons for the /check endpoint."""

from documentai_api.config.constants import ProcessStatus


class CheckStatus:
    PASS = "pass"
    FAIL = "fail"
    NOT_EVALUATED = "not_evaluated"


class CheckKey:
    PASSWORD_PROTECTED = "passwordProtected"
    DOCUMENT_DETECTED = "documentDetected"
    BLUR = "blurDetection"
    MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE = "multipleDocumentsOnSinglePage"
    MULTIPLE_DOCUMENTS_IN_MULTIPAGE = "multipleDocumentsInMultipage"
    MISCATEGORIZATION = "miscategorization"
    MISSING_FIELDS = "missingFields"
    EXTRACTION_CONFIDENCE = "extractionConfidence"


CHECKLIST: list[str] = [
    CheckKey.PASSWORD_PROTECTED,
    CheckKey.DOCUMENT_DETECTED,
    CheckKey.BLUR,
    CheckKey.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
    CheckKey.MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
    CheckKey.MISCATEGORIZATION,
    CheckKey.MISSING_FIELDS,
    CheckKey.EXTRACTION_CONFIDENCE,
]


class BlurSkipReason:
    PASSWORD_PROTECTED = "Blur check was not performed - document is password protected."
    PROCESSING_EXCLUDED = "Blur check was not performed - document was excluded from processing."
    DETECTION_DISABLED = (
        "Blur detection is not enabled."  # config state, no process status equivalent
    )
    NOT_A_DOCUMENT = "Blur check was skipped - insufficient text detected to evaluate."  # set directly on blur_result

    @classmethod
    def from_status(cls, process_status: str) -> str | None:
        """Map a terminal process status to its blur skip reason."""
        return {
            ProcessStatus.PASSWORD_PROTECTED.value: cls.PASSWORD_PROTECTED,
            ProcessStatus.PROCESSING_EXCLUDED.value: cls.PROCESSING_EXCLUDED,
        }.get(process_status)


class NotEvaluatedReason:
    STOPPED_PASSWORD_PROTECTED = (
        "Not reached - processing stopped because the document is password protected."
    )
    STOPPED_PROCESSING_EXCLUDED = "Not reached - document was excluded from processing."
    STOPPED_AI_CONSENT_DECLINED = (
        "Not reached - document was not processed because AI consent was not provided."
    )
    STOPPED_NO_BLUEPRINT_MATCHED = "Not reached - BDA ran but no blueprint matched."
    STOPPED_SKIPPED_PER_PRECLASSIFICATION = (
        "Not reached - document bypassed extraction per preclassification."
    )
    STOPPED_INTERNAL_ERROR = "Not reached - an internal processing error occurred."
    STOPPED_NO_DOCUMENT = "Not reached - processing stopped after no document was detected."
    STOPPED_BLURRY = "Not reached - processing stopped after the document was flagged as blurry."
    STOPPED_MULTIPLE_DOCUMENTS = (
        "Not reached - processing stopped after multiple documents were detected."
    )
    STOPPED_MULTIPLE_DOCUMENTS_IN_MULTIPAGE = "Not reached - processing stopped because pages are not continuations of a single document instance."
    EXTRACTION_NOT_EXECUTED = "Not reached - extraction did not run."
    BLUR_NOT_APPLICABLE = "Not evaluated - blur detection does not apply to this document type."
    LEGACY_DOCUMENT = (
        "Check data not available for documents processed before this feature was enabled."
    )
