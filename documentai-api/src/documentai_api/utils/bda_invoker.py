import os

import documentai_api.utils.documents as document_utils
from documentai_api.config.constants import ConfigDefaults, PreclassificationCategory
from documentai_api.config.env import EnvVars, get_aws_config, get_required_env
from documentai_api.logging import get_logger
from documentai_api.utils.aws_client_factory import AWSClientFactory

logger = get_logger(__name__)

_project_arns_cache: dict[str, str] | None = None


def _get_project_arns() -> dict[str, str]:
    """Load BDA project ARN map from AWSEnvConfig."""
    global _project_arns_cache
    if _project_arns_cache is not None:
        return _project_arns_cache

    config = get_aws_config()
    arns = {}
    for category in PreclassificationCategory:
        value = getattr(config, f"bda_project_arn_{category.value}", None)
        if value:
            arns[category.value] = value

    # "all" project as fallback
    if config.bda_project_arn_all:
        arns["all"] = config.bda_project_arn_all
    elif config.bda_project_arn:
        arns["all"] = config.bda_project_arn

    _project_arns_cache = arns
    return _project_arns_cache


def _is_preclassification_routing_enabled() -> bool:
    """Check SSM feature flag for preclassification-based routing."""
    config = get_aws_config()
    if not config.preclassification_routing_param:
        return False
    from documentai_api.utils.ssm import get_parameter_value

    value = get_parameter_value(config.preclassification_routing_param, default="false")
    return value.lower() == "true"


def resolve_project_arn(category: str | None) -> str:
    """Resolve BDA project ARN for a preclassification category."""
    arns = _get_project_arns()

    if category and _is_preclassification_routing_enabled() and category in arns:
        return arns[category]

    # Routing disabled or category not found - use "all" project
    return arns["all"]


def invoke_bedrock_data_automation(
    source_bucket_name: str, source_object_name: str, category: str | None = None
) -> tuple[str, str, int]:
    """Invoke BDA and return (invocation_arn, project_arn, pages_sent_to_bda)."""
    bda_project_arn = resolve_project_arn(category)
    bda_profile_arn = get_required_env(EnvVars.BDA_PROFILE_ARN)
    documentai_output_location = get_required_env(EnvVars.DOCUMENTAI_OUTPUT_LOCATION).replace(
        "s3://", ""
    )

    logger.info(f"documentai_output_location after processing: {documentai_output_location}")
    logger.info(f"BDA_PROJECT_ARN: {bda_project_arn}")
    logger.info(f"BDA_PROFILE_ARN: {bda_profile_arn}")

    try:
        bedrock = AWSClientFactory.get_bda_runtime_client()
    except Exception as e:
        logger.error(f"Failed to create bedrock client: {e}")
        raise

    try:
        from documentai_api.services import s3 as s3_service

        file_bytes = s3_service.get_file_bytes(source_bucket_name, source_object_name)
        page_count = document_utils.get_page_count(file_bytes)
        pages_sent = (
            min(page_count, int(ConfigDefaults.MAX_PAGES_PER_DOCUMENT)) if page_count else 1
        )

        if page_count and page_count > int(ConfigDefaults.MAX_PAGES_PER_DOCUMENT):
            logger.info(
                f"{source_object_name} has {page_count} pages, truncating to {int(ConfigDefaults.MAX_PAGES_PER_DOCUMENT)}"
            )

            truncated_bytes = document_utils.truncate_to_pages(
                file_bytes, max_pages=int(ConfigDefaults.MAX_PAGES_PER_DOCUMENT)
            )

            # create new truncated file name
            base_name, extension = os.path.splitext(source_object_name)
            extension = extension or ""  # handle None/empty extension
            source_object_name = f"{base_name}_truncated{extension}"

            # upload truncated version to S3
            s3_service.put_object(
                bucket=source_bucket_name, key=source_object_name, body=truncated_bytes
            )

        # TODO: refactor to call services/bda.py instead of calling runtime client directly
        response = bedrock.invoke_data_automation_async(
            dataAutomationProfileArn=bda_profile_arn,
            dataAutomationConfiguration={"dataAutomationProjectArn": bda_project_arn},
            inputConfiguration={"s3Uri": f"s3://{source_bucket_name}/{source_object_name}"},
            outputConfiguration={
                "s3Uri": f"s3://{documentai_output_location}/{source_object_name}"
            },
        )
        logger.info(f"BDA response: {response}")
        return str(response.get("invocationArn")), bda_project_arn, pages_sent
    except Exception as e:
        logger.error(f"BDA API call failed: {e}")
        raise


__all__ = ["invoke_bedrock_data_automation"]
