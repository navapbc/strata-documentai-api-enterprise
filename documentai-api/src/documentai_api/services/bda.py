"""Bedrock Data Automation service methods."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from documentai_api.config.env import EnvVars, get_aws_config, get_required_env
from documentai_api.logging import get_logger
from documentai_api.utils.aws_client_factory import AWSClientFactory
from documentai_api.utils.json_parsing import parse_json_object
from documentai_api.utils.s3 import parse_s3_uri

if TYPE_CHECKING:
    from mypy_boto3_bedrock_data_automation.type_defs import (
        GetBlueprintResponseTypeDef,
        GetDataAutomationProjectResponseTypeDef,
    )
    from mypy_boto3_bedrock_data_automation_runtime.type_defs import (
        GetDataAutomationStatusResponseTypeDef,
    )

logger = get_logger(__name__)


def get_project_arn_for_category(document_category: str) -> str:
    """Resolve BDA project ARN for a document category.

    Uses BDA_PROJECT_ARNS (JSON map) if set, falls back to BDA_PROJECT_ARN_ALL.
    Raises ValueError if the category is not found in the map.
    """
    project_arns_json = os.environ.get(EnvVars.BDA_PROJECT_ARNS)
    if project_arns_json:
        project_arns = json.loads(project_arns_json)
        project_arn = project_arns.get(document_category)

        if not project_arn:
            raise ValueError(f"Unknown document category: {document_category}")

        return str(project_arn)

    return get_required_env(EnvVars.BDA_PROJECT_ARN_ALL)


def invoke_bda_async(input_s3_uri: str, output_s3_uri: str, document_category: str) -> str:
    """Invoke BDA async job. Returns the invocationArn."""
    project_arn = get_project_arn_for_category(document_category)
    profile_arn = get_required_env(EnvVars.BDA_PROFILE_ARN)
    response = AWSClientFactory.get_bda_runtime_client().invoke_data_automation_async(
        dataAutomationProfileArn=profile_arn,
        dataAutomationConfiguration={"dataAutomationProjectArn": project_arn},
        inputConfiguration={"s3Uri": input_s3_uri},
        outputConfiguration={"s3Uri": output_s3_uri},
    )
    return response["invocationArn"]


def get_data_automation_project(project_arn: str) -> GetDataAutomationProjectResponseTypeDef:
    """Get BDA project details including blueprints."""
    bedrock_client = AWSClientFactory.get_bda_client()
    logger.debug(f"Getting BDA project details for project ARN: {project_arn}")
    return bedrock_client.get_data_automation_project(projectArn=project_arn)


def get_blueprint(blueprint_arn: str) -> GetBlueprintResponseTypeDef:
    """Get blueprint schema details."""
    bedrock_client = AWSClientFactory.get_bda_client()
    return bedrock_client.get_blueprint(blueprintArn=blueprint_arn)


def get_bda_result_json(bda_result_uri: str) -> dict[str, Any] | None:
    """Read and return BDA result JSON from S3."""
    if not bda_result_uri:
        return None

    try:
        s3_parts = bda_result_uri.replace("s3://", "").split("/", 1)
        result_bucket = s3_parts[0]
        result_key = s3_parts[1]

        # Validate the bucket is the configured output bucket to prevent SSRF
        # via a crafted BDA response pointing at an arbitrary S3 location.
        output_location = get_aws_config().documentai_output_location
        if output_location:
            expected_bucket, _ = parse_s3_uri(output_location)
            if result_bucket != expected_bucket:
                logger.error(
                    f"BDA result URI bucket {result_bucket!r} does not match "
                    f"expected output bucket {expected_bucket!r}"
                )
                return None

        s3 = AWSClientFactory.get_s3_client()
        bda_result_object = s3.get_object(Bucket=result_bucket, Key=result_key)
        return parse_json_object(bda_result_object["Body"].read(), context="BDA result JSON")
    except Exception as e:
        logger.error(f"Failed to read result JSON: {e}")
        return None


def get_bda_job_response(bda_invocation_arn: str) -> GetDataAutomationStatusResponseTypeDef | None:
    """Get BDA job status."""
    try:
        bedrock_client = AWSClientFactory.get_bda_runtime_client()
        return bedrock_client.get_data_automation_status(invocationArn=bda_invocation_arn)
    except Exception as e:
        logger.warning(f"Failed to get BDA job status for {bda_invocation_arn}: {e}")
        return None


def extract_bda_output_s3_uri(
    bda_output_bucket_name: str, bda_output_object_key: str
) -> str | None:
    """Read and parse BDA job metadata from S3."""
    s3 = AWSClientFactory.get_s3_client()
    metadata_response = s3.get_object(Bucket=bda_output_bucket_name, Key=bda_output_object_key)
    job_metadata = parse_json_object(metadata_response["Body"].read(), context="BDA job metadata")
    if job_metadata is None:
        return None

    # extract bda result uri from job metadata
    try:
        for output_meta in job_metadata.get("output_metadata", []):
            for segment in output_meta.get("segment_metadata", []):
                if "custom_output_path" in segment:
                    return str(segment["custom_output_path"])

                if "standard_output_path" in segment:
                    return str(segment["standard_output_path"])

        return None
    except (TypeError, AttributeError) as e:
        logger.error(f"Failed to extract BDA result uri: {e}")
        return None
