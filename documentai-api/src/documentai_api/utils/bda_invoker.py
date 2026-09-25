import os

from opentelemetry import trace

import documentai_api.utils.documents as document_utils
from documentai_api.config.constants import ConfigDefaults, ExtractMethod
from documentai_api.config.env import get_env_config
from documentai_api.logging import get_logger
from documentai_api.services import s3 as s3_service
from documentai_api.services.aws_client_factory import AWSClientFactory
from documentai_api.utils.s3 import generate_s3_uri
from documentai_api.utils.ssm import is_skip_bda_if_unclassified

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)

_project_arns_cache: dict[str, str] | None = None


def _get_project_arns() -> dict[str, str]:
    """Load BDA project ARN map from environment variables."""
    global _project_arns_cache
    if _project_arns_cache is not None:
        return _project_arns_cache

    _project_arns_cache = get_env_config().get_bda_project_arns()
    return _project_arns_cache


def skip_bda_if_unclassified() -> bool:
    """Check SSM feature flag: should BDA be skipped when preclassification returns other_document?

    Defaults to false (always invoke BDA) if the param is not configured.
    """
    return is_skip_bda_if_unclassified()


def resolve_project_arn(category: str | None) -> tuple[str | None, bool]:
    """Resolve BDA project ARN for a preclassification category.

    A matched category must have a configured BDA project - if not, that's a
    deploy misconfiguration and this raises. Blueprint matching often yields no
    category for perfectly valid documents (low confidence, "OTHER", the
    matching flag disabled, or a model error), so a None/unmatched category
    falls back to the default project (bda_project_arn), or returns None if no
    default is configured - a normal outcome now that there's no catch-all
    project. Callers should check for a None return and skip BDA rather than
    treat it as a failure.

    Returns (arn, used_category_specific_project). used_category_specific_project
    is True only when a category-specific project was used.
    """
    arns = _get_project_arns()

    if category:
        if category not in arns:
            raise ValueError(
                f"No BDA project configured for preclassification category: {category!r}"
            )
        return arns[category], True

    return get_env_config().bda_project_arn, False


def invoke_bedrock_data_automation(
    source_bucket_name: str,
    source_object_name: str,
    tenant_id: str,
    ddb_key: str,
    category: str | None = None,
) -> tuple[str, str, int, bool]:
    """Invoke BDA and return (invocation_arn, project_arn, pages_sent_to_bda, used_category_specific_project)."""
    bda_project_arn, used_category_specific_project = resolve_project_arn(category)
    if bda_project_arn is None:
        # Callers should check resolve_project_arn's return value and skip BDA
        # before reaching here - this is a defensive guard against misuse.
        raise ValueError(
            "No preclassification category matched and no default BDA project "
            "(BDA_PROJECT_ARN) is configured"
        )
    bda_profile_arn = get_env_config().get_bda_profile_arn
    output_location = get_env_config().get_output_location
    output_uri = generate_s3_uri(output_location, tenant_id, ddb_key, ExtractMethod.BDA)

    logger.info(f"BDA_PROJECT_ARN: {bda_project_arn}")
    logger.info(f"BDA_PROFILE_ARN: {bda_profile_arn}")

    try:
        bedrock = AWSClientFactory.get_bda_runtime_client()
    except Exception as e:
        logger.error(f"Failed to create bedrock client: {e}")
        raise

    try:
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

        # considered moving to services/bda.py instead of calling runtime client
        # directly. ultimately decided not to. services/bda.py does not have
        # tracing/span. moving the call would mean either introducing
        # span-wrapping into a service module that's otherwise plain client calls,
        # or splitting the span from the actual invocation across two files.
        # neither is an improvement. the juice isn't worth the squeeze.
        with tracer.start_as_current_span("bda.invoke_data_automation_async") as span:
            span.set_attribute("bda.project_arn", bda_project_arn)
            span.set_attribute("bda.pages_sent", pages_sent)
            span.set_attribute("bda.object_key", source_object_name)
            response = bedrock.invoke_data_automation_async(
                dataAutomationProfileArn=bda_profile_arn,
                dataAutomationConfiguration={"dataAutomationProjectArn": bda_project_arn},
                inputConfiguration={"s3Uri": f"s3://{source_bucket_name}/{source_object_name}"},
                outputConfiguration={"s3Uri": output_uri},
            )
        logger.info(f"BDA response: {response}")

        return (
            str(response.get("invocationArn")),
            bda_project_arn,
            pages_sent,
            used_category_specific_project,
        )
    except Exception as e:
        logger.error(f"BDA API call failed: {e}")
        raise


__all__ = [
    "invoke_bedrock_data_automation",
    "resolve_project_arn",
    "skip_bda_if_unclassified",
]
