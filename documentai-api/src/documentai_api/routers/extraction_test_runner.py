"""Extraction test runner - upload a document and see extraction results.

Async approach: POST starts the test, GET polls for results via the standard
document pipeline (preclassify → BDA/Textract → extraction rules).
"""

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile

from documentai_api.annotations import AdminClaims, TenantIdField, verify_jwt_with_role
from documentai_api.classifiers.api_response import build_v1_api_response
from documentai_api.config.constants import ApiVisualizationTag, ProcessStatus
from documentai_api.logging import get_logger
from documentai_api.models.base import BaseApiResponse
from documentai_api.models.job_status import JobStatusResponse
from documentai_api.routers.documents import upload_document
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.auth import UserContext, resolve_tenant_from_context
from documentai_api.utils.jobs import get_job_status
from documentai_api.utils.jwt_auth import (
    SUPER_ADMIN,
    assert_tenant_scope,
    get_tenant_id,
    is_super_admin,
    tenant_scope,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/admin/extraction-test",
    tags=[ApiVisualizationTag.ADMIN_DOCUMENTS],
    dependencies=[Depends(verify_jwt_with_role)],
)


class ExtractionTestStartResponse(BaseApiResponse):
    job_id: str
    job_status: str


@router.post("")
async def start_extraction_test(
    claims: AdminClaims,
    response: Response,
    file: UploadFile,
    tenant_id: TenantIdField,
) -> ExtractionTestStartResponse:
    """Upload a document through the full extraction pipeline.

    Returns a job_id to poll for results via GET /{job_id}.
    """
    jwt_context = UserContext(
        tenant_id=SUPER_ADMIN if is_super_admin(claims) else (get_tenant_id(claims) or ""),
        api_key_name=claims.get("email", "admin"),
        auth_method="jwt",
    )
    resolve_tenant_from_context(jwt_context, tenant_id)
    auth = UserContext(
        tenant_id=tenant_id, api_key_name=jwt_context.api_key_name, auth_method="jwt"
    )
    result = await upload_document(
        response=response,
        file=file,
        auth=auth,
        is_test_run=True,
    )
    return ExtractionTestStartResponse(job_id=result.job_id, job_status=result.job_status)


@router.get("/{job_id}")
async def get_extraction_test_result(
    job_id: str,
    claims: AdminClaims,
    include_extracted_data: bool = False,
) -> JobStatusResponse:
    """Poll for extraction test results."""
    scope = tenant_scope(claims)
    job_status = await asyncio.to_thread(get_job_status, job_id)

    if not job_status.ddb_record:
        raise HTTPException(status_code=404, detail="Job not found")

    assert_tenant_scope(job_status.ddb_record, scope, DocumentMetadata.TENANT_ID)

    if not job_status.v1_response_json:
        current_status = job_status.process_status or ProcessStatus.NOT_STARTED.value
        return JobStatusResponse(
            job_id=job_id,
            job_status=current_status,
            message=ProcessStatus.pending_message(current_status),
        )

    if include_extracted_data:
        if not job_status.object_key or not job_status.process_status:
            raise HTTPException(status_code=500, detail=f"Incomplete record for job {job_id}")

        result = await asyncio.to_thread(
            build_v1_api_response,
            object_key=job_status.object_key,
            job_status=job_status.process_status,
            include_extracted_data=True,
        )
        return JobStatusResponse.from_v1(result)

    return JobStatusResponse.from_v1(json.loads(job_status.v1_response_json))
