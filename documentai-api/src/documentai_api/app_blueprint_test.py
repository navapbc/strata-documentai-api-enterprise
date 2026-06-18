"""Blueprint test runner - upload a document and see extraction results.

Async approach: POST starts the test, GET polls for results.
"""

import os
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import Field

from documentai_api.annotations import AdminClaims, verify_jwt_with_role
from documentai_api.config.constants import ApiVisualizationTag, BdaJobStatus
from documentai_api.config.env import EnvVars, get_aws_config, get_required_env
from documentai_api.logging import get_logger
from documentai_api.models.base import BaseApiResponse
from documentai_api.utils.aws_client_factory import AWSClientFactory

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/admin/blueprints",
    tags=[ApiVisualizationTag.ADMIN_BLUEPRINTS],
    dependencies=[Depends(verify_jwt_with_role)],
)


class BlueprintTestStartResponse(BaseApiResponse):
    test_id: str
    status: str = "PROCESSING"


class BlueprintTestResult(BaseApiResponse):
    test_id: str
    status: str
    document_type: str | None = None
    matched_blueprint: str | None = None
    matched_confidence: float | None = None
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    field_confidences: dict[str, float] = Field(default_factory=dict)
    filtered_fields: dict[str, Any] = Field(default_factory=dict)
    missing_required_fields: list[str] = Field(default_factory=list)
    has_rules: bool = False
    error: str | None = None


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
    logger.info(
        f"Blueprint test {test_id}: starting for tenant={tenant_id}, doc_type={document_type}, file={file.filename}"
    )

    # Upload to temp S3 location
    input_location = get_aws_config().documentai_input_location
    if not input_location:
        raise HTTPException(status_code=500, detail="Input location not configured")

    input_bucket = input_location.replace("s3://", "").split("/")[0]
    test_key = f"test-runner/{test_id}/{file.filename}"

    try:
        s3 = AWSClientFactory.get_s3_client()
        file_bytes = await file.read()
        logger.info(
            f"Blueprint test {test_id}: uploading {len(file_bytes)} bytes to s3://{input_bucket}/{test_key}"
        )
        s3.put_object(Bucket=input_bucket, Key=test_key, Body=file_bytes)
    except Exception as e:
        logger.error(f"Blueprint test {test_id}: failed to upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file") from e

    # Invoke BDA with category-specific project
    try:
        import json as json_mod

        bda_runtime = AWSClientFactory.get_bda_runtime_client()
        output_location = get_required_env(EnvVars.DOCUMENTAI_OUTPUT_LOCATION).replace("s3://", "")

        # Look up project ARN for the category
        project_arns_json = os.environ.get("BDA_PROJECT_ARNS")
        if project_arns_json:
            project_arns = json_mod.loads(project_arns_json)
            bda_project_arn = project_arns.get(document_category)
            if not bda_project_arn:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown document category: {document_category}",
                )
        else:
            bda_project_arn = get_required_env(EnvVars.BDA_PROJECT_ARN)

        bda_profile_arn = get_required_env(EnvVars.BDA_PROFILE_ARN)

        logger.info(f"Blueprint test {test_id}: invoking BDA project={bda_project_arn}")
        response = bda_runtime.invoke_data_automation_async(
            dataAutomationProfileArn=bda_profile_arn,
            dataAutomationConfiguration={"dataAutomationProjectArn": bda_project_arn},
            inputConfiguration={"s3Uri": f"s3://{input_bucket}/{test_key}"},
            outputConfiguration={"s3Uri": f"s3://{output_location}/{test_key}"},
        )
        invocation_arn = response.get("invocationArn")
        logger.info(f"Blueprint test {test_id}: BDA invoked, arn={invocation_arn}")
    except Exception as e:
        logger.error(f"Blueprint test {test_id}: failed to invoke BDA: {e}")
        _cleanup_s3(s3, input_bucket, test_key)
        raise HTTPException(status_code=500, detail="Failed to invoke BDA") from e

    # Store test metadata in DDB for polling
    _store_test_metadata(test_id, invocation_arn, tenant_id, document_type, input_bucket, test_key)
    logger.info(f"Blueprint test {test_id}: metadata stored, returning")

    return BlueprintTestStartResponse(test_id=test_id)


@router.get("/test/{test_id}")
async def get_blueprint_test_result(
    test_id: str,
    claims: AdminClaims,
) -> BlueprintTestResult:
    """Poll for blueprint test results."""
    from documentai_api.services.bda import (
        extract_bda_output_s3_uri,
        get_bda_result_json,
    )
    from documentai_api.utils.bda import extract_field_values_from_bda_results
    from documentai_api.utils.bda_output_processor import get_matched_blueprint
    from documentai_api.utils.extraction_rules import apply_extraction_rules

    logger.info(f"Blueprint test {test_id}: polling for results")

    metadata = _get_test_metadata(test_id)
    if not metadata:
        logger.warning(f"Blueprint test {test_id}: metadata not found")
        raise HTTPException(status_code=404, detail="Test not found")

    invocation_arn = metadata["invocationArn"]
    tenant_id = metadata["tenantId"]
    document_type = metadata.get("documentType")
    input_bucket = metadata["inputBucket"]
    test_key = metadata["testKey"]

    logger.info(f"Blueprint test {test_id}: checking BDA status for {invocation_arn}")

    # Check BDA status - call directly to see errors
    job_response: dict[str, Any] | None = None
    try:
        bda_runtime = AWSClientFactory.get_bda_runtime_client()
        response = bda_runtime.get_data_automation_status(invocationArn=invocation_arn)
        job_response = dict(response)
        logger.info(f"Blueprint test {test_id}: raw BDA response={job_response}")
    except Exception as e:
        logger.error(f"Blueprint test {test_id}: get_data_automation_status failed: {e}")

    if not job_response:
        logger.info(f"Blueprint test {test_id}: no response from BDA yet")
        return BlueprintTestResult(test_id=test_id, status="PROCESSING")

    job_status = job_response.get("status", "")
    logger.info(f"Blueprint test {test_id}: BDA status={job_status}")

    if not job_status or BdaJobStatus.is_running(job_status):
        return BlueprintTestResult(test_id=test_id, status="PROCESSING")

    if BdaJobStatus.is_failed(job_status):
        error = job_response.get("error", {}).get("message", "Unknown error")
        _cleanup_test(test_id, input_bucket, test_key)
        return BlueprintTestResult(test_id=test_id, status="FAILED", error=error)

    if BdaJobStatus.is_completed(job_status):
        # Extract results
        output_config = job_response.get("outputConfiguration", {})
        output_s3_uri = output_config.get("s3Uri", "")
        output_bucket = output_s3_uri.replace("s3://", "").split("/")[0]
        output_key = "/".join(output_s3_uri.replace("s3://", "").split("/")[1:])

        bda_output_s3_uri = extract_bda_output_s3_uri(output_bucket, output_key)
        if not bda_output_s3_uri:
            _cleanup_test(test_id, input_bucket, test_key)
            return BlueprintTestResult(
                test_id=test_id, status="FAILED", error="No BDA output found"
            )

        bda_result_json = get_bda_result_json(bda_output_s3_uri)
        if not bda_result_json:
            _cleanup_test(test_id, input_bucket, test_key)
            return BlueprintTestResult(
                test_id=test_id, status="FAILED", error="Could not read BDA result"
            )

        matched_blueprint = get_matched_blueprint(bda_result_json)
        metadata, field_values, _ = extract_field_values_from_bda_results(bda_result_json)

        # Build confidence map from the list of {field: score} dicts
        field_confidences: dict[str, float] = {}
        for conf_map in metadata.field_confidence_map_list:
            field_confidences.update(conf_map)

        document_class = bda_result_json.get("document_class", {}).get("document_type")
        effective_doc_type = document_type or document_class or matched_blueprint.name

        # Apply extraction rules
        has_rules = False
        filtered_fields = field_values
        missing_required: list[str] = []

        if effective_doc_type and tenant_id:
            rule_result = apply_extraction_rules(tenant_id, effective_doc_type, field_values)
            if rule_result.fields != field_values:
                has_rules = True
                filtered_fields = rule_result.fields
                missing_required = rule_result.missing_required_field_list

        _cleanup_test(test_id, input_bucket, test_key)

        return BlueprintTestResult(
            test_id=test_id,
            status="COMPLETED",
            document_type=effective_doc_type,
            matched_blueprint=matched_blueprint.name,
            matched_confidence=matched_blueprint.confidence,
            extracted_fields=field_values,
            field_confidences=field_confidences,
            filtered_fields=filtered_fields,
            missing_required_fields=missing_required,
            has_rules=has_rules,
        )

    return BlueprintTestResult(test_id=test_id, status="PROCESSING")


# --- Storage helpers (DDB for test metadata) ---

_TEST_TABLE_TTL_SECONDS = 3600  # 1 hour


def _get_test_table_name() -> str:
    table_name = get_aws_config().audit_events_table_name
    if not table_name:
        raise ValueError("AUDIT_EVENTS_TABLE_NAME not configured")
    return table_name


def _store_test_metadata(
    test_id: str,
    invocation_arn: str,
    tenant_id: str | None,
    document_type: str | None,
    input_bucket: str,
    test_key: str,
) -> None:
    """Store test run metadata for polling."""
    import time

    try:
        table = AWSClientFactory.get_ddb_table(_get_test_table_name())
        # Reuse audit table with a special partition for test runs
        table.put_item(
            Item={
                "tenantId": f"__test__{test_id}",
                "timestamp#eventId": test_id,
                "invocationArn": invocation_arn,
                "tenantId_actual": tenant_id or "",
                "documentType": document_type or "",
                "inputBucket": input_bucket,
                "testKey": test_key,
                "ttl": int(time.time()) + _TEST_TABLE_TTL_SECONDS,
            }
        )
    except Exception as e:
        logger.error(f"Failed to store test metadata: {e}")


def _get_test_metadata(test_id: str) -> dict[str, Any] | None:
    """Retrieve test run metadata."""
    try:
        table = AWSClientFactory.get_ddb_table(_get_test_table_name())
        response = table.get_item(
            Key={"tenantId": f"__test__{test_id}", "timestamp#eventId": test_id}
        )
        item = response.get("Item")
        if item:
            item["tenantId"] = item.pop("tenantId_actual", "")
        return item
    except Exception as e:
        logger.error(f"Failed to get test metadata: {e}")
        return None


def _cleanup_test(test_id: str, input_bucket: str, test_key: str) -> None:
    """Clean up test artifacts."""
    _cleanup_s3(AWSClientFactory.get_s3_client(), input_bucket, test_key)
    try:
        table = AWSClientFactory.get_ddb_table(_get_test_table_name())
        table.delete_item(Key={"tenantId": f"__test__{test_id}", "timestamp#eventId": test_id})
    except Exception:
        pass


def _cleanup_s3(s3: Any, bucket: str, key: str) -> None:
    """Best-effort cleanup of the test file from S3."""
    try:
        s3.delete_object(Bucket=bucket, Key=key)
    except Exception:
        logger.warning(f"Failed to cleanup test file: s3://{bucket}/{key}")
