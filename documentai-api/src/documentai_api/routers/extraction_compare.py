"""Compare router - run BDA and LLM on the same document through the real pipeline."""

import io
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from starlette.datastructures import Headers

from documentai_api.annotations import AdminClaims, verify_jwt_with_role
from documentai_api.config.constants import ApiVisualizationTag, ExtractMethod
from documentai_api.logging import get_logger
from documentai_api.models.extraction_compare import (
    CompareFieldResult,
    CompareResponse,
    CompareSubmitResponse,
)
from documentai_api.routers.documents import upload_document
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.ddb import get_ddb_by_job_id

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

    return CompareResponse(
        job_id=job_id,
        primary_method=primary_method,
        primary=_extract_fields(responses[primary_method]),
        llm=_extract_fields(responses[_LLM]),
        durations=record.get(DocumentMetadata.DURATIONS_BY_METHOD) or {},
    )
