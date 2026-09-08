"""Bedrock Data Automation service methods."""

from __future__ import annotations

from typing import TYPE_CHECKING

from documentai_api.logging import get_logger
from documentai_api.services.aws_client_factory import AWSClientFactory

if TYPE_CHECKING:
    from mypy_boto3_bedrock_data_automation.type_defs import (
        GetBlueprintResponseTypeDef,
        GetDataAutomationProjectResponseTypeDef,
    )
    from mypy_boto3_bedrock_data_automation_runtime.type_defs import (
        GetDataAutomationStatusResponseTypeDef,
    )

logger = get_logger(__name__)


def get_data_automation_project(project_arn: str) -> GetDataAutomationProjectResponseTypeDef:
    """Get BDA project details including blueprints."""
    bedrock_client = AWSClientFactory.get_bda_client()
    logger.debug(f"Getting BDA project details for project ARN: {project_arn}")
    return bedrock_client.get_data_automation_project(projectArn=project_arn)


def get_blueprint(blueprint_arn: str) -> GetBlueprintResponseTypeDef:
    """Get blueprint schema details."""
    bedrock_client = AWSClientFactory.get_bda_client()
    return bedrock_client.get_blueprint(blueprintArn=blueprint_arn)


def get_bda_job_response(bda_invocation_arn: str) -> GetDataAutomationStatusResponseTypeDef | None:
    """Get BDA job status."""
    try:
        bedrock_client = AWSClientFactory.get_bda_runtime_client()
        return bedrock_client.get_data_automation_status(invocationArn=bda_invocation_arn)
    except Exception as e:
        logger.warning(f"Failed to get BDA job status for {bda_invocation_arn}: {e}")
        return None
