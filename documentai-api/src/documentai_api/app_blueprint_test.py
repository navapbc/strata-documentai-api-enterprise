"""Blueprint test runner - upload a document and see extraction results.

Async approach: POST starts the test, GET polls for results.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from documentai_api.annotations import AdminClaims, verify_jwt_with_role
from documentai_api.config.constants import ApiVisualizationTag, BdaJobStatus, BlueprintTestStatus
from documentai_api.config.env import EnvVars, get_aws_config, get_required_env
from documentai_api.logging import get_logger
from documentai_api.models.blueprint import BlueprintTestResult, BlueprintTestStartResponse
from documentai_api.services import s3 as s3_service
from documentai_api.services.bda import (
    extract_bda_output_s3_uri,
    get_bda_job_response,
    get_bda_result_json,
    invoke_bda_async,
)
from documentai_api.utils.bda_output_processor import (
    extract_bda_result as extract_bda_result_from_json,
)
from documentai_api.utils.blueprint_test import (
    cleanup_test,
    get_test_metadata,
    store_test_metadata,
)
from documentai_api.utils.jwt_auth import require_tenant

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/admin/blueprints",
    tags=[ApiVisualizationTag.ADMIN_BLUEPRINTS],
    dependencies=[Depends(verify_jwt_with_role)],
)


@router.post("/test")
async def start_blueprint_test(
    claims: AdminClaims,
    file: Annotated[UploadFile, File(...)],
    document_category: Annotated[str, Form(...)],
    tenant_id: Annotated[str | None, Form()] = None,
    document_type: Annotated[str | None, Form()] = None,
) -> BlueprintTestStartResponse:
    """Upload a document and start BDA extraction.

    Returns a test_id to poll for results via GET /test/{test_id}.
    """
    test_id = str(uuid.uuid4())
    tenant_id = require_tenant(claims, tenant_id)
    logger.info(
        f"Blueprint test {test_id}: starting for tenant={tenant_id}, doc_type={document_type}, file={file.filename}"
    )

    # Upload to temp S3 location
    input_bucket = get_aws_config().get_input_bucket_name()
    test_key = f"test-runner/{test_id}/{file.filename}"
    s3_service.put_object(input_bucket, test_key, await file.read())
    logger.info(
        f"Blueprint test {test_id}: uploaded {file.filename} to s3://{input_bucket}/{test_key}"
    )

    # Invoke BDA with category-specific project
    output_location = get_required_env(EnvVars.DOCUMENTAI_OUTPUT_LOCATION).replace("s3://", "")
    try:
        invocation_arn = invoke_bda_async(
            input_s3_uri=f"s3://{input_bucket}/{test_key}",
            output_s3_uri=f"s3://{output_location}/{test_key}",
            document_category=document_category,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    logger.info(f"Blueprint test {test_id}: BDA invoked, arn={invocation_arn}")
    store_test_metadata(test_id, invocation_arn, tenant_id, document_type, test_key)
    logger.info(f"Blueprint test {test_id}: metadata stored, returning")

    return BlueprintTestStartResponse(test_id=test_id)


@router.get("/test/{test_id}")
async def get_blueprint_test_result(
    test_id: str,
    claims: AdminClaims,
) -> BlueprintTestResult:
    """Poll for blueprint test results."""
    logger.info(f"Blueprint test {test_id}: polling for results")

    metadata = get_test_metadata(test_id)

    if not metadata:
        logger.warning(f"Blueprint test {test_id}: metadata not found")
        raise HTTPException(status_code=404, detail="Test not found")

    invocation_arn = metadata.invocation_arn
    tenant_id = require_tenant(claims, metadata.tenant_id)
    document_type = metadata.document_type
    test_key = metadata.test_key

    logger.info(f"Blueprint test {test_id}: checking BDA status for {invocation_arn}")
    job_response = get_bda_job_response(invocation_arn)

    if not job_response:
        logger.info(f"Blueprint test {test_id}: no response from BDA yet")
        return BlueprintTestResult(test_id=test_id, status=BlueprintTestStatus.PROCESSING)

    job_status = job_response.get("status", "")
    logger.info(f"Blueprint test {test_id}: BDA status={job_status}")

    if not job_status or BdaJobStatus.is_running(job_status):
        return BlueprintTestResult(test_id=test_id, status=BlueprintTestStatus.PROCESSING)

    if BdaJobStatus.is_failed(job_status):
        logger.warning(f"Blueprint test {test_id}: BDA job failed")
        cleanup_test(test_id, test_key)
        return BlueprintTestResult(
            test_id=test_id, status=BlueprintTestStatus.FAILED, error="BDA processing failed"
        )

    if BdaJobStatus.is_completed(job_status):
        output_config = job_response.get("outputConfiguration", {})
        output_s3_uri = output_config.get("s3Uri", "")
        output_bucket = output_s3_uri.replace("s3://", "").split("/")[0]
        output_key = "/".join(output_s3_uri.replace("s3://", "").split("/")[1:])

        bda_output_s3_uri = extract_bda_output_s3_uri(output_bucket, output_key)

        if not bda_output_s3_uri:
            return BlueprintTestResult(
                test_id=test_id, status=BlueprintTestStatus.FAILED, error="No BDA output found"
            )

        bda_result_json = get_bda_result_json(bda_output_s3_uri)

        if not bda_result_json:
            return BlueprintTestResult(
                test_id=test_id,
                status=BlueprintTestStatus.FAILED,
                error="Could not read BDA result",
            )

        result = extract_bda_result_from_json(bda_result_json, tenant_id, document_type)
        cleanup_test(test_id, test_key)

        return BlueprintTestResult(
            test_id=test_id,
            status=BlueprintTestStatus.COMPLETED,
            document_type=result.document_type,
            matched_blueprint=result.matched_blueprint.name,
            matched_confidence=result.matched_blueprint.confidence,
            extracted_fields=result.field_values,
            field_confidences=result.field_confidences,
            filtered_fields=result.filtered_fields,
            missing_required_fields=result.missing_required,
            has_rules=result.has_rules,
        )

    return BlueprintTestResult(test_id=test_id, status=BlueprintTestStatus.PROCESSING)
