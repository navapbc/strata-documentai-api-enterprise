"""Blueprint management utilities - publish, live toggle, and routing lookup."""

import json
import uuid
from typing import Any

from documentai_api.config.constants import (
    BdaBlueprintStage,
    BdaProjectConfig,
    BdaProjectStage,
    BlueprintStatus,
)
from documentai_api.logging import get_logger
from documentai_api.models.blueprint import BlueprintLiveResponse
from documentai_api.schemas.blueprints import (
    BlueprintRecord,
    BlueprintsTable,
)
from documentai_api.utils.aws_client_factory import AWSClientFactory
from documentai_api.utils.tenants import get_override_bda_project_arn, set_override_bda_project_arn

logger = get_logger(__name__)

_blueprints_table = BlueprintsTable()


# =============================================================================
# Helpers
# =============================================================================


def _validate_blueprint_id(tenant_id: str, blueprint_id: str) -> dict[str, Any]:
    item = _blueprints_table.get(tenant_id, blueprint_id)

    if not item:
        raise ValueError("Blueprint not found")

    return item


# =============================================================================
# Draft management
# =============================================================================


def create_blueprint_draft(
    tenant_id: str, name: str, description: str, document_type: str, fields: list[dict[str, Any]]
) -> dict[str, Any]:
    blueprint_id = str(uuid.uuid4())

    return _blueprints_table.create(
        {
            BlueprintRecord.TENANT_ID: tenant_id,
            BlueprintRecord.BLUEPRINT_ID: blueprint_id,
            BlueprintRecord.NAME: name,
            BlueprintRecord.DESCRIPTION: description,
            BlueprintRecord.DOCUMENT_TYPE: document_type,
            BlueprintRecord.FIELDS: fields,
            BlueprintRecord.STATUS: BlueprintStatus.DRAFT,
        }
    )


def update_blueprint_draft(tenant_id: str, blueprint_id: str, **fields: Any) -> dict[str, Any]:
    item = _validate_blueprint_id(tenant_id, blueprint_id)
    if item.get(BlueprintRecord.STATUS) == BlueprintStatus.LIVE:
        raise ValueError("Cannot edit a live blueprint — take it offline first")

    return _blueprints_table.update(tenant_id, blueprint_id, **fields)


def get_blueprint(tenant_id: str, blueprint_id: str) -> dict[str, Any] | None:
    return _blueprints_table.get(tenant_id, blueprint_id)


def list_blueprints(tenant_id: str) -> list[dict[str, Any]]:
    return _blueprints_table.list_by_pk(tenant_id)


def delete_blueprint(tenant_id: str, blueprint_id: str) -> bool:
    item = _blueprints_table.get(tenant_id, blueprint_id)

    if not item:
        return False

    if item.get(BlueprintRecord.STATUS) == BlueprintStatus.LIVE:
        raise ValueError("Cannot delete a live blueprint — take it offline first")

    return _blueprints_table.deactivate(tenant_id, blueprint_id)


# =============================================================================
# Publish
# =============================================================================


def publish_blueprint(tenant_id: str, blueprint_id: str) -> dict[str, Any]:
    """Register blueprint with BDA. Auto-creates tenant project if needed."""
    item = _validate_blueprint_id(tenant_id, blueprint_id)
    project_arn = _get_or_create_tenant_project(tenant_id)
    blueprint_arn = _register_bda_blueprint(tenant_id, item, project_arn)

    return _blueprints_table.update(
        tenant_id,
        blueprint_id,
        blueprintStatus=BlueprintStatus.PUBLISHED,
        blueprintArn=blueprint_arn,
    )


def _get_or_create_tenant_project(tenant_id: str) -> str:
    """Return existing tenant BDA project ARN or create a new one, stored on the tenant record."""
    if arn := get_override_bda_project_arn(tenant_id):
        return arn

    project_arn = _create_bda_project(tenant_id)
    set_override_bda_project_arn(tenant_id, project_arn)
    logger.info(f"Created BDA project for tenant {tenant_id}: {project_arn}")
    return project_arn


def _create_bda_project(tenant_id: str) -> str:
    bda = AWSClientFactory.get_bda_client()
    response = bda.create_data_automation_project(
        projectName=f"tenant-{tenant_id}-custom",
        projectDescription=f"Custom blueprints for tenant {tenant_id}",
        projectStage=BdaProjectStage.LIVE.value,
        standardOutputConfiguration=BdaProjectConfig.STANDARD_OUTPUT_CONFIGURATION,  # type: ignore[arg-type]
    )
    return response["projectArn"]


def _register_bda_blueprint(tenant_id: str, item: dict[str, Any], project_arn: str) -> str:
    bda = AWSClientFactory.get_bda_client()

    schema = {
        "description": item[BlueprintRecord.DESCRIPTION],
        "fields": item[BlueprintRecord.FIELDS],
    }

    response = bda.create_blueprint(
        blueprintName=f"{tenant_id}-{item[BlueprintRecord.NAME]}",
        type="DOCUMENT",
        blueprintStage=BdaBlueprintStage.LIVE.value,
        schema=json.dumps(schema),
    )

    blueprint_arn = response["blueprint"]["blueprintArn"]

    bda.update_data_automation_project(
        projectArn=project_arn,
        customOutputConfiguration={"blueprints": [{"blueprintArn": blueprint_arn}]},
        standardOutputConfiguration=BdaProjectConfig.STANDARD_OUTPUT_CONFIGURATION,  # type: ignore[arg-type]
    )

    return blueprint_arn


# =============================================================================
# Live toggle
# =============================================================================


def enable_blueprint(tenant_id: str, blueprint_id: str) -> BlueprintLiveResponse:
    item = _validate_blueprint_id(tenant_id, blueprint_id)
    bp_status = item.get(BlueprintRecord.STATUS)

    if bp_status == BlueprintStatus.LIVE:
        raise ValueError("Blueprint is already live")

    if bp_status == BlueprintStatus.DRAFT:
        raise ValueError("Blueprint must be published before going live")

    document_type = item[BlueprintRecord.DOCUMENT_TYPE]
    _blueprints_table.update(tenant_id, blueprint_id, blueprintStatus=BlueprintStatus.LIVE)

    return BlueprintLiveResponse(
        blueprint_id=blueprint_id, document_type=document_type, message="Blueprint is now live"
    )


def disable_blueprint(tenant_id: str, blueprint_id: str) -> BlueprintLiveResponse:
    item = _validate_blueprint_id(tenant_id, blueprint_id)
    document_type = item[BlueprintRecord.DOCUMENT_TYPE]
    _blueprints_table.update(tenant_id, blueprint_id, blueprintStatus=BlueprintStatus.PUBLISHED)

    return BlueprintLiveResponse(
        blueprint_id=blueprint_id, document_type=document_type, message="Blueprint is now offline"
    )


# =============================================================================
# Routing lookup
# =============================================================================


def get_live_blueprint_arn(tenant_id: str, document_type: str) -> str | None:
    """Return the blueprint ARN for the live blueprint matching this document type, or None."""
    from boto3.dynamodb.conditions import Key

    items, _ = _blueprints_table.query(
        key_condition=Key(BlueprintRecord.TENANT_ID).eq(tenant_id)
        & Key(BlueprintRecord.DOCUMENT_TYPE).eq(document_type),
        index_name=_blueprints_table.document_type_index(),
    )
    item = next((i for i in items if i.get(BlueprintRecord.STATUS) == BlueprintStatus.LIVE), None)

    return item.get(BlueprintRecord.BLUEPRINT_ARN) if item else None
