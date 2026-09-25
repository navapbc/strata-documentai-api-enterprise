"""Compare router - run BDA and LLM on the same document through the real pipeline."""

import io
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from starlette.datastructures import Headers

from documentai_api.annotations import AdminClaims, verify_jwt_with_role
from documentai_api.config.constants import ApiVisualizationTag, ExtractMethod, LlmUsageReason
from documentai_api.logging import get_logger
from documentai_api.models.extraction_compare import (
    CompareFieldResult,
    CompareResponse,
    CompareSubmitResponse,
)
from documentai_api.routers.documents import upload_document
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.ddb import get_ddb_by_job_id, get_token_usage_by_reason, sum_token_usage_by_model
from documentai_api.utils.llm_cost import compute_bda_cost, compute_llm_cost, compute_textract_cost

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/admin/extraction-compare",
    tags=[ApiVisualizationTag.ADMIN_COMPARE],
    dependencies=[Depends(verify_jwt_with_role)],
)

_LLM = ExtractMethod.LLM.value


def _extract_fields(v1_response_json: str | dict[str, Any]) -> dict[str, CompareFieldResult]:
    v1 = json.loads(v1_response_json) if isinstance(v1_response_json, str) else v1_response_json
    fields = v1.get("fields") or {}
    return {
        name: CompareFieldResult(
            value=data.get("value"),
            confidence=data.get("confidence"),
            geometry=data.get("geometry"),
        )
        for name, data in fields.items()
        if isinstance(data, dict)
    }


@router.post("", status_code=202)
async def run_compare(
    claims: AdminClaims,
    file: Annotated[UploadFile, File(...)],
) -> CompareSubmitResponse:
    """Submit a document through the real pipeline with both BDA and LLM extraction.

    Returns immediately with a job_id. Poll GET /{job_id} until 200.

    Uses is_compare=True which:
    - Forces LLM extraction regardless of the feature flag
    - Writes each path's output to apiResponsesByMethod map instead of terminal status
    - Suppresses metrics queue emission and batch counter increments
    """
    from documentai_api.utils.auth import UserContext

    file_bytes = await file.read()
    filename = file.filename or "compare-doc"
    content_type = file.content_type or "application/octet-stream"

    sub = claims.get("sub", "compare")
    auth = UserContext(tenant_id=f"compare-{sub}", api_key_name=sub, auth_method="jwt")

    upload_file = UploadFile(
        filename=filename,
        file=io.BytesIO(file_bytes),
        headers=Headers({"content-type": content_type}),
    )
    result = await upload_document(
        response=Response(),
        file=upload_file,
        auth=auth,
        is_compare=True,
    )
    logger.info(f"Compare submitted: job_id={result.job_id}")
    return CompareSubmitResponse(job_id=result.job_id)


@router.get("/{job_id}")
def get_compare_result(job_id: str) -> CompareResponse:
    """Poll for compare results. Returns 200 with results when both paths complete, 404 until then."""
    record = get_ddb_by_job_id(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")

    primary_method = record.get(DocumentMetadata.EXTRACT_METHOD) or ExtractMethod.BDA.value
    responses = record.get(DocumentMetadata.API_RESPONSES_BY_METHOD) or {}
    if not {primary_method, _LLM}.issubset(responses.keys()):
        raise HTTPException(status_code=404, detail="Results not ready")

    object_key = record.get(DocumentMetadata.FILE_NAME, "")
    tokens = sum_token_usage_by_model(object_key)
    cost: dict[str, float] = {
        model_id: round(c, 8)
        for model_id, entry in tokens.items()
        if (c := compute_llm_cost(model_id, entry["inputTokens"], entry["outputTokens"])) is not None
    }
    if primary_method == ExtractMethod.TEXTRACT.value:
        cost[ExtractMethod.TEXTRACT.value] = compute_textract_cost(1)
    elif primary_method == ExtractMethod.BDA.value:
        pages = int(record.get(DocumentMetadata.PAGES_SENT_TO_BDA) or 1)
        is_custom = bool(record.get(DocumentMetadata.BDA_MATCHED_BLUEPRINT_NAME))
        cost[ExtractMethod.BDA.value] = compute_bda_cost(pages, is_custom)

    # cost_by_reason: collapse per-model costs into reason buckets so callers
    # can compare primary-path cost vs llm-extraction cost directly.
    # shared = preclassification + blueprintMatch + cropDetection (both paths pay)
    # llmExtraction = LLM extraction only
    # primary = textract flat fee (when applicable)
    _LLM_EXTRACTION_REASON = LlmUsageReason.LLM_EXTRACTION.value
    _PRIMARY_REASON = "primary"
    _SHARED_REASON = "shared"
    cost_by_reason: dict[str, float] = {}
    for composite_key, entry in get_token_usage_by_reason(object_key).items():
        model_id, _, reason = composite_key.partition("#")
        c = compute_llm_cost(model_id, entry["inputTokens"], entry["outputTokens"])
        if c is None:
            continue
        bucket = _LLM_EXTRACTION_REASON if reason == _LLM_EXTRACTION_REASON else _SHARED_REASON
        cost_by_reason[bucket] = round(cost_by_reason.get(bucket, 0.0) + c, 8)
    if primary_method == ExtractMethod.TEXTRACT.value:
        cost_by_reason[_PRIMARY_REASON] = compute_textract_cost(1)
    elif primary_method == ExtractMethod.BDA.value:
        pages = int(record.get(DocumentMetadata.PAGES_SENT_TO_BDA) or 1)
        is_custom = bool(record.get(DocumentMetadata.BDA_MATCHED_BLUEPRINT_NAME))
        cost_by_reason[_PRIMARY_REASON] = compute_bda_cost(pages, is_custom)

    return CompareResponse(
        job_id=job_id,
        primary_method=primary_method,
        primary=_extract_fields(responses[primary_method]),
        llm=_extract_fields(responses[_LLM]),
        durations=record.get(DocumentMetadata.DURATIONS_BY_METHOD) or {},
        tokens=tokens,
        cost=cost,
        cost_by_reason=cost_by_reason,
    )
