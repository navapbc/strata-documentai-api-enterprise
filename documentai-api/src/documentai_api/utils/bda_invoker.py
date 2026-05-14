import os

import documentai_api.utils.documents as document_utils
from documentai_api.config.constants import ConfigDefaults
from documentai_api.config.env import EnvVars, get_required_env
from documentai_api.logging import get_logger
from documentai_api.utils.aws_client_factory import AWSClientFactory

logger = get_logger(__name__)


def invoke_bedrock_data_automation(source_bucket_name: str, source_object_name: str) -> str:
    """Invoke BDA and return job ARN."""
    bda_project_arn = get_required_env(EnvVars.BDA_PROJECT_ARN)
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
        return str(response.get("invocationArn"))
    except Exception as e:
        logger.error(f"BDA API call failed: {e}")
        raise


__all__ = ["invoke_bedrock_data_automation"]
