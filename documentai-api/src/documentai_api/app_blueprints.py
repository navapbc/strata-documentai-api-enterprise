"""Blueprint management endpoints - create, test, publish, and go live."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from documentai_api.annotations import AdminClaims, verify_jwt_with_role
from documentai_api.config.constants import ApiVisualizationTag, BdaJobStatus, BlueprintStatus
from documentai_api.config.env import EnvVars, get_aws_config, get_required_env
from documentai_api.logging import get_logger
from documentai_api.models.blueprint import (
    BlueprintCreateRequest,
    BlueprintDeleteResponse,
    BlueprintItem,
    BlueprintListResponse,
    BlueprintLiveResponse,
    BlueprintPublishResponse,
    BlueprintUpdateRequest,
)
from documentai_api.schemas.blueprints import BlueprintRecord
from documentai_api.services import s3 as s3_service
from documentai_api.services.bda import (
    extract_bda_output_s3_uri,
    get_bda_job_response,
    get_bda_result_json,
)
from documentai_api.utils.aws_client_factory import AWSClientFactory
from documentai_api.utils.blueprint_test import cleanup_test, get_test_metadata, store_test_metadata
from documentai_api.utils.blueprints import (
    create_blueprint_draft,
    delete_blueprint,
    disable_blueprint,
    enable_blueprint,
    get_blueprint,
    list_blueprints,
    publish_blueprint,
    update_blueprint_draft,
)
from documentai_api.utils.jwt_auth import require_tenant

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/blueprints",
    tags=[ApiVisualizationTag.ADMIN_BLUEPRINTS],
    dependencies=[Depends(verify_jwt_with_role)],
)


def _to_blueprint_item(record: dict[str, Any]) -> BlueprintItem:
    return BlueprintItem(
        blueprint_id=record[BlueprintRecord.BLUEPRINT_ID],
        tenant_id=record[BlueprintRecord.TENANT_ID],
        description=record[BlueprintRecord.DESCRIPTION],
        document_type=record[BlueprintRecord.DOCUMENT_TYPE],
        fields=record.get(BlueprintRecord.FIELDS, []),
        status=record.get(BlueprintRecord.STATUS, BlueprintStatus.DRAFT),
        blueprint_arn=record.get(BlueprintRecord.BLUEPRINT_ARN),
        project_arn=record.get(BlueprintRecord.PROJECT_ARN),
        created_at=record.get("createdAt", ""),
        updated_at=record.get("updatedAt", ""),
    )


# =============================================================================
# CRUD
# =============================================================================


@router.get("")
async def list_tenant_blueprints(
    claims: AdminClaims,
    tenant_id: str | None = None,
) -> BlueprintListResponse:
    """List all blueprints for a tenant."""
    effective_tenant = require_tenant(claims, tenant_id)
    records = list_blueprints(effective_tenant)
    return BlueprintListResponse(blueprints=[_to_blueprint_item(r) for r in records])


@router.post("")
async def create_blueprint(
    claims: AdminClaims,
    body: BlueprintCreateRequest,
    tenant_id: str | None = None,
) -> BlueprintItem:
    """Create a new blueprint draft."""
    effective_tenant = require_tenant(claims, tenant_id)
    try:
        record = create_blueprint_draft(
            tenant_id=effective_tenant,
            description=body.description,
            document_type=body.document_type,
            fields=[f.model_dump(exclude_none=True) for f in body.fields],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _to_blueprint_item(record)


@router.get("/{blueprint_id}")
async def get_blueprint_by_id(
    blueprint_id: str,
    claims: AdminClaims,
    tenant_id: str | None = None,
) -> BlueprintItem:
    """Get a single blueprint."""
    effective_tenant = require_tenant(claims, tenant_id)
    record = get_blueprint(effective_tenant, blueprint_id)
    if not record:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return _to_blueprint_item(record)


@router.put("/{blueprint_id}")
async def update_blueprint(
    blueprint_id: str,
    claims: AdminClaims,
    body: BlueprintUpdateRequest,
    tenant_id: str | None = None,
) -> BlueprintItem:
    """Update a draft or published blueprint. Live blueprints must be taken offline first."""
    effective_tenant = require_tenant(claims, tenant_id)
    updates: dict[str, Any] = {}

    if body.description is not None:
        updates[BlueprintRecord.DESCRIPTION] = body.description

    if body.document_type is not None:
        updates[BlueprintRecord.DOCUMENT_TYPE] = body.document_type

    if body.fields is not None:
        updates[BlueprintRecord.FIELDS] = [f.model_dump(exclude_none=True) for f in body.fields]

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        record = update_blueprint_draft(effective_tenant, blueprint_id, **updates)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return _to_blueprint_item(record)


@router.delete("/{blueprint_id}")
async def delete_blueprint_by_id(
    blueprint_id: str,
    claims: AdminClaims,
    tenant_id: str | None = None,
) -> BlueprintDeleteResponse:
    """Delete a draft or published blueprint. Live blueprints must be taken offline first."""
    effective_tenant = require_tenant(claims, tenant_id)

    try:
        deleted = delete_blueprint(effective_tenant, blueprint_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not deleted:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    return BlueprintDeleteResponse(message="Blueprint deleted")


# =============================================================================
# Publish
# =============================================================================


@router.post("/{blueprint_id}/publish")
async def publish_blueprint_endpoint(
    blueprint_id: str,
    claims: AdminClaims,
    tenant_id: str | None = None,
) -> BlueprintPublishResponse:
    """Register blueprint with BDA. Auto-creates tenant project if needed."""
    effective_tenant = require_tenant(claims, tenant_id)

    try:
        record = publish_blueprint(effective_tenant, blueprint_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to publish blueprint {blueprint_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to publish blueprint") from e

    return BlueprintPublishResponse(
        blueprint_id=blueprint_id,
        blueprint_arn=record[BlueprintRecord.BLUEPRINT_ARN],
        project_arn=record[BlueprintRecord.PROJECT_ARN],
        message="Blueprint published and registered with BDA",
    )


# =============================================================================
# Test
# =============================================================================


@router.post("/{blueprint_id}/test")
async def test_blueprint(
    blueprint_id: str,
    claims: AdminClaims,
    file: Annotated[UploadFile, File(...)],
    document_category: Annotated[str, Form(...)],
    tenant_id: Annotated[str | None, Form()] = None,  # noqa: PT028
) -> dict[str, Any]:
    """Upload a sample document and run it through BDA using this blueprint's project.

    Blueprint must be published (has a BDA blueprint ARN) before testing.
    Returns a test_id to poll via GET /{blueprint_id}/test/{test_id}.
    """
    effective_tenant = require_tenant(claims, tenant_id)
    record = get_blueprint(effective_tenant, blueprint_id)
    if not record:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    if not record.get(BlueprintRecord.BLUEPRINT_ARN):
        raise HTTPException(status_code=400, detail="Blueprint must be published before testing")

    project_arn = record[BlueprintRecord.PROJECT_ARN]
    test_id = str(uuid.uuid4())
    input_bucket = get_aws_config().get_input_bucket_name()
    test_key = f"blueprint-test/{effective_tenant}/{blueprint_id}/{test_id}/{file.filename}"

    try:
        s3_service.put_object(input_bucket, test_key, await file.read())
    except Exception as e:
        logger.error(f"Blueprint test {test_id}: upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload test file") from e

    try:
        output_location = get_required_env(EnvVars.DOCUMENTAI_OUTPUT_LOCATION).replace("s3://", "")
        bda_profile_arn = get_required_env(EnvVars.BDA_PROFILE_ARN)
        response = AWSClientFactory.get_bda_runtime_client().invoke_data_automation_async(
            dataAutomationProfileArn=bda_profile_arn,
            dataAutomationConfiguration={"dataAutomationProjectArn": project_arn},
            inputConfiguration={"s3Uri": f"s3://{input_bucket}/{test_key}"},
            outputConfiguration={"s3Uri": f"s3://{output_location}/{test_key}"},
        )
        invocation_arn = response.get("invocationArn")
    except Exception as e:
        logger.error(f"Blueprint test {test_id}: BDA invocation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to invoke BDA") from e

    store_test_metadata(test_id, invocation_arn, effective_tenant, document_category, test_key)
    return {"test_id": test_id, "status": "PROCESSING"}


@router.get("/{blueprint_id}/test/{test_id}")
async def get_blueprint_test_result(
    blueprint_id: str,
    test_id: str,
    claims: AdminClaims,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Poll for blueprint test results."""
    from documentai_api.utils.bda import extract_field_values_from_bda_results
    from documentai_api.utils.bda_output_processor import get_matched_blueprint

    effective_tenant = require_tenant(claims, tenant_id)
    metadata = get_test_metadata(test_id)

    if not metadata or metadata.tenant_id != effective_tenant:
        raise HTTPException(status_code=404, detail="Test not found")

    job_response = get_bda_job_response(metadata.invocation_arn)

    if not job_response:
        return {"test_id": test_id, "status": "PROCESSING"}

    job_status = job_response.get("status", "")

    if not job_status or BdaJobStatus.is_running(job_status):
        return {"test_id": test_id, "status": "PROCESSING"}

    if BdaJobStatus.is_failed(job_status):
        cleanup_test(test_id, metadata.test_key)
        return {"test_id": test_id, "status": "FAILED", "error": "BDA processing failed"}

    if BdaJobStatus.is_completed(job_status):
        output_s3_uri = job_response.get("outputConfiguration", {}).get("s3Uri", "")
        output_bucket = output_s3_uri.replace("s3://", "").split("/")[0]
        output_key = "/".join(output_s3_uri.replace("s3://", "").split("/")[1:])

        bda_output_s3_uri = extract_bda_output_s3_uri(output_bucket, output_key)
        if not bda_output_s3_uri:
            cleanup_test(test_id, metadata.test_key)
            return {"test_id": test_id, "status": "FAILED", "error": "No BDA output found"}

        bda_result_json = get_bda_result_json(bda_output_s3_uri)
        if not bda_result_json:
            cleanup_test(test_id, metadata.test_key)
            return {"test_id": test_id, "status": "FAILED", "error": "Could not read BDA result"}

        matched = get_matched_blueprint(bda_result_json)
        field_data, field_values, _ = extract_field_values_from_bda_results(bda_result_json)
        field_confidences = {
            k: v for m in field_data.field_confidence_map_list for k, v in m.items()
        }
        cleanup_test(test_id, metadata.test_key)
        return {
            "test_id": test_id,
            "status": "COMPLETED",
            "matched_blueprint": matched.name,
            "matched_confidence": matched.confidence,
            "extracted_fields": field_values,
            "field_confidences": field_confidences,
            "empty_fields": field_data.empty_fields,
        }

    return {"test_id": test_id, "status": "PROCESSING"}


# =============================================================================
# Live toggle
# =============================================================================


@router.post("/{blueprint_id}/live")
async def go_live(
    blueprint_id: str,
    claims: AdminClaims,
    tenant_id: str | None = None,
) -> BlueprintLiveResponse:
    """Make a published blueprint live - it will be used in document routing."""
    effective_tenant = require_tenant(claims, tenant_id)
    try:
        return enable_blueprint(effective_tenant, blueprint_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{blueprint_id}/live")
async def take_offline(
    blueprint_id: str,
    claims: AdminClaims,
    tenant_id: str | None = None,
) -> BlueprintLiveResponse:
    """Take a live blueprint offline - routing falls back to shared projects."""
    effective_tenant = require_tenant(claims, tenant_id)

    try:
        return disable_blueprint(effective_tenant, blueprint_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
