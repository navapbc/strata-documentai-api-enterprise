"""Evaluation statuses, keys, pipeline order, and skip reasons for the /evaluation endpoint."""


class EvaluationStatus:
    PASS = "pass"
    FAIL = "fail"
    NOT_EVALUATED = "not_evaluated"


class EvaluationKey:
    PASSWORD_PROTECTED = "passwordProtected"
    DOCUMENT_DETECTED = "documentDetected"
    BLUR = "blurDetection"
    MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE = "multipleDocumentsOnSinglePage"
    MULTIPLE_DOCUMENTS_IN_MULTIPAGE = "multipleDocumentsInMultipage"
    MISCATEGORIZATION = "miscategorization"
    MISSING_FIELDS = "missingFields"
    EXTRACTION_CONFIDENCE = "extractionConfidence"


EVALUATION_PIPELINE: list[str] = [
    EvaluationKey.PASSWORD_PROTECTED,
    EvaluationKey.DOCUMENT_DETECTED,
    EvaluationKey.BLUR,
    EvaluationKey.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
    EvaluationKey.MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
    EvaluationKey.MISCATEGORIZATION,
    EvaluationKey.MISSING_FIELDS,
    EvaluationKey.EXTRACTION_CONFIDENCE,
]


class BlurSkipReason:
    PASSWORD_PROTECTED = "Blur check was not performed - document is password protected."
    PROCESSING_EXCLUDED = "Blur check was not performed - document was excluded from processing."
    DETECTION_DISABLED = "Blur detection is not enabled."
    NOT_A_DOCUMENT = "Blur check was skipped - insufficient text detected to evaluate."


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
    STOPPED_MULTIPLE_DOCUMENTS_IN_MULTIPAGE = (
        "Not reached - processing stopped after multiple document types were detected across pages."
    )
    EXTRACTION_NOT_EXECUTED = "Not reached - extraction did not run."
    BLUR_NOT_APPLICABLE = "Not evaluated - blur detection does not apply to this document type."
    LEGACY_DOCUMENT = (
        "Evaluation data not available for documents processed before this feature was enabled."
    )
