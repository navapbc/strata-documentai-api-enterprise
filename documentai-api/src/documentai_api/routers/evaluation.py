"""Evaluation endpoint - returns per-check pass/fail/not_evaluated breakdown for a document."""

import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from documentai_api.annotations import AuthUser
from documentai_api.logging import get_logger
from documentai_api.models.evaluation import EvaluationEntry, EvaluationResponse
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.auth import get_user_context_from_api_key
from documentai_api.utils.evaluations import (
    EVALUATION_PIPELINE,
    EvaluationKey,
    EvaluationStatus,
    NotEvaluatedReason,
)
from documentai_api.utils.jobs import get_job_status
from documentai_api.utils.response_codes import ResponseCodes
from documentai_api.utils.tenant_access import validate_document_tenant_access

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(get_user_context_from_api_key)])

_NOT_EVALUATED = EvaluationStatus.NOT_EVALUATED
_PASS = EvaluationStatus.PASS
_FAIL = EvaluationStatus.FAIL


# Maps a pre-extraction terminal code to the pipeline key where processing stopped.
# 101/102/105 are NOT here - they reached extraction, so all keys are evaluated from signals.
_PRE_EXTRACTION_STOP_MAP: dict[str, tuple[str, str]] = {
    ResponseCodes.PASSWORD_PROTECTED: (
        EvaluationKey.PASSWORD_PROTECTED,
        NotEvaluatedReason.STOPPED_PASSWORD_PROTECTED,
    ),
    ResponseCodes.NO_DOCUMENT_DETECTED: (
        EvaluationKey.DOCUMENT_DETECTED,
        NotEvaluatedReason.STOPPED_NO_DOCUMENT,
    ),
    ResponseCodes.BLURRY_DOCUMENT_DETECTED: (
        EvaluationKey.BLUR,
        NotEvaluatedReason.STOPPED_BLURRY,
    ),
    ResponseCodes.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE: (
        EvaluationKey.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
        NotEvaluatedReason.STOPPED_MULTIPLE_DOCUMENTS,
    ),
    ResponseCodes.MULTIPLE_DOCUMENTS_IN_MULTIPAGE: (
        EvaluationKey.MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
        NotEvaluatedReason.STOPPED_MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
    ),
}

_EXTRACTION_TIER = {
    ResponseCodes.SUCCESS,
    ResponseCodes.MISSING_FIELDS,
    ResponseCodes.MISCATEGORIZED,
    ResponseCodes.LOW_EXTRACTION_CONFIDENCE,
}

_STOP_FAIL_REASONS: dict[str, str] = {
    EvaluationKey.PASSWORD_PROTECTED: "Document is password protected.",
    EvaluationKey.DOCUMENT_DETECTED: "Insufficient text detected to identify a document.",
    EvaluationKey.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE: "Multiple documents were detected on a single page.",
    EvaluationKey.MULTIPLE_DOCUMENTS_IN_MULTIPAGE: "Pages are not continuations of a single document instance.",
}

_BLUR_STOP_FALLBACK = "Document was flagged as blurry."


def _stop_fail_entry(key: str, ddb_record: dict[str, Any]) -> EvaluationEntry:
    """Return a guaranteed-fail entry for the stop key, driven by the response code."""
    if key == EvaluationKey.BLUR:
        reason = ddb_record.get(DocumentMetadata.IS_DOCUMENT_BLURRY_REASON) or _BLUR_STOP_FALLBACK
        return EvaluationEntry(status=_FAIL, reason=reason)
    return EvaluationEntry(status=_FAIL, reason=_STOP_FAIL_REASONS[key])


def _evaluate_key(key: str, ddb_record: dict[str, Any]) -> EvaluationEntry:
    """Return pass/fail for a single pipeline key using its own stored signal."""
    if key == EvaluationKey.PASSWORD_PROTECTED:
        if ddb_record.get(DocumentMetadata.IS_PASSWORD_PROTECTED):
            return EvaluationEntry(status=_FAIL, reason="Document is password protected.")
        return EvaluationEntry(status=_PASS, reason="Document is not password protected.")

    if key == EvaluationKey.DOCUMENT_DETECTED:
        # No stored boolean - reaching this key means OCR succeeded.
        return EvaluationEntry(status=_PASS, reason="Sufficient text detected.")

    if key == EvaluationKey.BLUR:
        is_blurry = ddb_record.get(DocumentMetadata.IS_DOCUMENT_BLURRY)
        reason = ddb_record.get(DocumentMetadata.IS_DOCUMENT_BLURRY_REASON)
        if is_blurry:
            return EvaluationEntry(status=_FAIL, reason=reason)
        return EvaluationEntry(status=_PASS, reason=reason)

    if key == EvaluationKey.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE:
        # No stored boolean - reaching this key means only one document was detected.
        return EvaluationEntry(status=_PASS, reason="No multiple documents detected.")

    if key == EvaluationKey.MULTIPLE_DOCUMENTS_IN_MULTIPAGE:
        # No stored boolean - reaching this key means pages are continuations of a single document instance.
        return EvaluationEntry(
            status=_PASS, reason="Pages are continuations of a single document instance."
        )

    if key == EvaluationKey.MISCATEGORIZATION:
        category_match = ddb_record.get(DocumentMetadata.PRECLASSIFICATION_CATEGORY_MATCH)
        if category_match is False:
            expected = ddb_record.get(DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY)
            detected = ddb_record.get(DocumentMetadata.PRECLASSIFICATION_CATEGORY)
            detail = (
                f"The detected document type ({detected.lower()}) does not appear to belong to the provided document category ({expected.lower()})."
                if expected and detected
                else "Document category did not match the expected type."
            )
            return EvaluationEntry(status=_FAIL, reason=detail)
        return EvaluationEntry(status=_PASS, reason=None)

    if key == EvaluationKey.MISSING_FIELDS:
        if DocumentMetadata.EXTRACTION_RULES_CONFIGURED not in ddb_record:
            return EvaluationEntry(status=_NOT_EVALUATED, reason=NotEvaluatedReason.LEGACY_DOCUMENT)
        if ddb_record.get(DocumentMetadata.EXTRACTION_RULES_CONFIGURED) is False:
            return EvaluationEntry(status=_NOT_EVALUATED, reason="Extraction rules not configured.")
        raw = ddb_record.get(DocumentMetadata.MISSING_REQUIRED_FIELD_LIST)
        missing_required = json.loads(raw) if isinstance(raw, str) else (raw or [])
        if missing_required:
            return EvaluationEntry(
                status=_FAIL,
                reason=f"One or more required fields were not extracted: {', '.join(missing_required)}.",
            )
        raw_required = ddb_record.get(DocumentMetadata.REQUIRED_FIELD_LIST)
        required = (
            json.loads(raw_required) if isinstance(raw_required, str) else (raw_required or [])
        )
        reason = f"All required fields were extracted: {', '.join(required)}." if required else None
        return EvaluationEntry(status=_PASS, reason=reason)

    if key == EvaluationKey.EXTRACTION_CONFIDENCE:
        if DocumentMetadata.EXTRACTION_CONFIDENCE_THRESHOLD not in ddb_record:
            return EvaluationEntry(status=_NOT_EVALUATED, reason=NotEvaluatedReason.LEGACY_DOCUMENT)
        avg = ddb_record.get(DocumentMetadata.BDA_MATCHED_BLUEPRINT_FIELD_NOT_EMPTY_AVG_CONFIDENCE)
        floor = ddb_record.get(DocumentMetadata.EXTRACTION_CONFIDENCE_THRESHOLD)
        used_default = ddb_record.get(DocumentMetadata.USED_DEFAULT_EXTRACTION_CONFIDENCE_THRESHOLD)
        avg_pct = f" ({avg:.0%})" if avg is not None else ""
        threshold_label = "default" if used_default else "tenant-configured"
        floor_pct = f" ({floor:.0%})" if floor is not None else ""

        if ddb_record.get(DocumentMetadata.BELOW_EXTRACTION_CONFIDENCE_FLOOR):
            return EvaluationEntry(
                status=_FAIL,
                reason=f"Average field confidence{avg_pct} did not meet the {threshold_label} required threshold{floor_pct}.",
            )

        return EvaluationEntry(
            status=_PASS,
            reason=f"Average field confidence{avg_pct} exceeded the {threshold_label} required threshold{floor_pct}.",
        )

    return EvaluationEntry(status=_NOT_EVALUATED, reason=None)


def _build_evaluations(
    response_code: str | None, ddb_record: dict[str, Any]
) -> dict[str, EvaluationEntry]:
    """Build the full fixed evaluation key set for a given response code."""
    if response_code is None:
        return {
            key: EvaluationEntry(
                status=_NOT_EVALUATED, reason=NotEvaluatedReason.STOPPED_INTERNAL_ERROR
            )
            for key in EVALUATION_PIPELINE
        }

    if response_code == ResponseCodes.NO_BLUEPRINT_MATCHED:
        # BDA_INVOCATION_ARN present -> BDA ran, no blueprint matched -> all keys from signals
        # BDA_INVOCATION_ARN absent -> preclassified as unknown, BDA not invoked -> all not_evaluated
        if ddb_record.get(DocumentMetadata.BDA_INVOCATION_ARN):
            return {key: _evaluate_key(key, ddb_record) for key in EVALUATION_PIPELINE}
        return {
            key: EvaluationEntry(
                status=_NOT_EVALUATED, reason=NotEvaluatedReason.STOPPED_NO_BLUEPRINT_MATCHED
            )
            for key in EVALUATION_PIPELINE
        }

    if response_code in (
        ResponseCodes.PROCESSING_EXCLUDED,
        ResponseCodes.AI_CONSENT_DECLINED,
        ResponseCodes.SKIPPED_PER_PRECLASSIFICATION,
        ResponseCodes.INTERNAL_PROCESSING_ERROR,
    ):
        reason = {
            ResponseCodes.PROCESSING_EXCLUDED: NotEvaluatedReason.STOPPED_PROCESSING_EXCLUDED,
            ResponseCodes.AI_CONSENT_DECLINED: NotEvaluatedReason.STOPPED_AI_CONSENT_DECLINED,
            ResponseCodes.SKIPPED_PER_PRECLASSIFICATION: NotEvaluatedReason.STOPPED_SKIPPED_PER_PRECLASSIFICATION,
            ResponseCodes.INTERNAL_PROCESSING_ERROR: NotEvaluatedReason.STOPPED_INTERNAL_ERROR,
        }.get(response_code, NotEvaluatedReason.STOPPED_INTERNAL_ERROR)

        return {
            key: EvaluationEntry(status=_NOT_EVALUATED, reason=reason)
            for key in EVALUATION_PIPELINE
        }

    stopped_pre_extraction = _PRE_EXTRACTION_STOP_MAP.get(response_code)

    if stopped_pre_extraction is None:
        if response_code in _EXTRACTION_TIER:
            return {key: _evaluate_key(key, ddb_record) for key in EVALUATION_PIPELINE}

        logger.warning(
            f"Unrecognized response code in _build_evaluations: {response_code!r} - defaulting to not_evaluated"
        )
        return {
            key: EvaluationEntry(
                status=_NOT_EVALUATED, reason=NotEvaluatedReason.STOPPED_INTERNAL_ERROR
            )
            for key in EVALUATION_PIPELINE
        }

    stop_key, not_evaluated_reason = stopped_pre_extraction
    stop_index = EVALUATION_PIPELINE.index(stop_key)

    result: dict[str, EvaluationEntry] = {}
    for i, key in enumerate(EVALUATION_PIPELINE):
        if i < stop_index:
            result[key] = _evaluate_key(key, ddb_record)
        elif i == stop_index:
            result[key] = _stop_fail_entry(key, ddb_record)
        else:
            result[key] = EvaluationEntry(status=_NOT_EVALUATED, reason=not_evaluated_reason)

    return result


@router.get("/v1/documents/{job_id}/evaluation", tags=["Documents:Query"])
async def get_document_evaluation(job_id: uuid.UUID, auth: AuthUser) -> EvaluationResponse:
    """Return a per-check evaluation breakdown for a processed document."""
    job_status = await asyncio.to_thread(get_job_status, str(job_id))

    if not job_status.ddb_record:
        raise HTTPException(status_code=404, detail=f"Job ID {job_id} not found")

    validate_document_tenant_access(job_status.ddb_record, auth.tenant_id, str(job_id))

    if not job_status.v1_response_json:
        raise HTTPException(status_code=400, detail="Document has not finished processing yet")

    response_code = job_status.ddb_record.get(DocumentMetadata.RESPONSE_CODE)
    created_at = job_status.ddb_record.get(DocumentMetadata.CREATED_AT)
    evaluations = _build_evaluations(response_code, job_status.ddb_record)

    return EvaluationResponse(
        job_id=str(job_id),
        created_at=created_at,
        response_code=response_code,
        response_code_description=ResponseCodes.get_message(response_code)
        if response_code
        else None,
        evaluations=evaluations,
    )
