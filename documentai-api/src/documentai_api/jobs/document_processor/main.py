#!/usr/bin/env python3
"""Process uploaded documents: insert to DDB, convert if needed, invoke BDA."""

import os
from typing import Any

import typer
from botocore.exceptions import ClientError
from tenacity import (
    RetryError,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

import documentai_api.logging
from documentai_api.config.constants import (
    ProcessStatus,
    S3MetadataKeys,
)
from documentai_api.config.env import EnvVars, get_aws_config, get_required_env
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.services import s3 as s3_service
from documentai_api.utils.bda_invoker import invoke_bedrock_data_automation
from documentai_api.utils.ddb import (
    classify_as_failed,
    classify_as_not_implemented,
    get_ddb_record,
    set_bda_processing_status_not_started,
    set_bda_processing_status_started,
    upsert_initial_ddb_record,
)
from documentai_api.utils.dto import ClassificationData
from documentai_api.utils.image_optimization import (
    convert_s3_object_to_grayscale,
    crop_image_to_document_roi,
)
from documentai_api.utils.s3 import parse_s3_uri

logger = documentai_api.logging.get_logger(__name__)
app = typer.Typer()


def _invoke_bda(
    bucket_name: str, object_key: str, ddb_key: str, preclassification_category: str | None = None
) -> dict[str, Any]:
    """Invoke BDA for a file that's ready for processing."""
    result: dict[str, Any] = {}

    for attempt in Retrying(
        stop=stop_after_attempt(get_aws_config().max_bda_invoke_retry_attempts),
        wait=wait_exponential_jitter(initial=10, max=120),
        retry=retry_if_exception_type(ClientError),
    ):
        with attempt:
            invocation_arn, project_arn = invoke_bedrock_data_automation(
                bucket_name, object_key, preclassification_category
            )

            set_bda_processing_status_started(
                object_key=ddb_key,
                bda_invocation_arn=invocation_arn,
                bda_project_arn_used=project_arn,
            )

            logger.info(f"BDA job started for {ddb_key}, ARN: {invocation_arn}")
            result = {"invocationArn": invocation_arn}

    return result


def invoke_bda(
    bucket_name: str, object_key: str, ddb_key: str, preclassification_category: str | None = None
) -> dict[str, Any]:
    """Wrapper that handles retry failures."""
    try:
        return _invoke_bda(bucket_name, object_key, ddb_key, preclassification_category)
    except RetryError as e:
        retry_state = e.last_attempt
        attempt_number = retry_state.attempt_number

        logger.error(f"BDA invocation failed for {ddb_key} after {attempt_number} attempts: {e}")
        classify_as_failed(
            object_key=ddb_key,
            error_message="BDA invocation failed",
            data=ClassificationData(additional_info=str(e)),
        )
        raise


def main(
    object_key: str,
    bucket_name: str | None = None,
    user_provided_document_category: str | None = None,
    job_id: str | None = None,
    trace_id: str | None = None,
    batch_id: str | None = None,
) -> None:
    """Process uploaded document and invoke BDA.

    This job combines DDB insertion, grayscale conversion, and BDA invocation
    into a single workflow triggered by S3 upload events.

    Args:
        object_key: S3 object key (e.g. "input/document.pdf")
        bucket_name: Optional S3 bucket name (defaults to DOCUMENTAI_INPUT_LOCATION env var)
        user_provided_document_category: Optional document category (will be read from S3 metadata if not provided)
        job_id: Optional job ID (will be read from S3 metadata if not provided)
        trace_id: Optional trace ID (will be read from S3 metadata if not provided)
        batch_id: Optional batch ID (will be read from S3 metadata if not provided)
    """
    if bucket_name is None:
        input_location = get_required_env(EnvVars.DOCUMENTAI_INPUT_LOCATION)
        bucket_name, _ = parse_s3_uri(input_location)

    logger.info(f"Processing document: s3://{bucket_name}/{object_key}")

    response = s3_service.head_object(bucket_name, object_key)
    metadata = response.get("Metadata", {})
    original_file_name = metadata.get(S3MetadataKeys.ORIGINAL_FILE_NAME)
    if not original_file_name:
        logger.warning("Original file name not present in S3 metadata")
        original_file_name = ""

    if not all([job_id, trace_id, user_provided_document_category, batch_id]):
        try:
            job_id = job_id or metadata.get(S3MetadataKeys.JOB_ID)
            trace_id = trace_id or metadata.get(S3MetadataKeys.TRACE_ID)
            batch_id = batch_id or metadata.get(S3MetadataKeys.BATCH_ID)
            user_provided_document_category = user_provided_document_category or metadata.get(
                S3MetadataKeys.USER_PROVIDED_DOCUMENT_CATEGORY
            )
        except Exception as e:
            logger.warning(f"Could not read S3 metadata: {e}")

    # strip S3 prefix for DynamoDB key (files are stored without prefix)
    ddb_key = os.path.basename(object_key)
    existing_record = get_ddb_record(ddb_key)

    # Run preclassification (and the rest of upsert_initial_ddb_record) only when
    # the record is in its initial pre-classification state:
    #   - no record (doc-processor saw the S3 event before the API Lambda), OR
    #   - the API Lambda's minimal upload row (status=NOT_STARTED with no
    #     preclassificationCategory yet).
    # Otherwise we'd re-classify when grayscale conversion overwrites the input
    # file in S3 and fires another event, looping the pipeline.
    needs_preclassification = existing_record is None or (
        ProcessStatus.is_awaiting_processing(
            existing_record.get(DocumentMetadata.PROCESS_STATUS, "")
        )
        and DocumentMetadata.PRECLASSIFICATION_CATEGORY not in existing_record
    )

    if needs_preclassification:
        upsert_initial_ddb_record(
            source_bucket_name=bucket_name,
            source_object_key=object_key,
            ddb_key=ddb_key,
            original_file_name=original_file_name,
            user_provided_document_category=user_provided_document_category,
            job_id=job_id,
            trace_id=trace_id,
            batch_id=batch_id,
        )
        existing_record = get_ddb_record(ddb_key)

    if existing_record is None:
        raise Exception("Could not retrieve DDB record after upsert")

    status = existing_record.get(DocumentMetadata.PROCESS_STATUS)

    if status == ProcessStatus.PENDING_IMAGE_OPTIMIZATION:
        preclassification_category = existing_record.get(
            DocumentMetadata.PRECLASSIFICATION_CATEGORY
        )
        crop_image_to_document_roi(bucket_name, object_key)
        if convert_s3_object_to_grayscale(bucket_name, object_key):
            set_bda_processing_status_not_started(ddb_key)
            invoke_bda(bucket_name, object_key, ddb_key, preclassification_category)
            logger.info(f"Converted {ddb_key} to grayscale and invoked BDA")
        else:
            classify_as_not_implemented(
                object_key=ddb_key,
                data=ClassificationData(additional_info="File too large after conversion"),
            )
    elif status and ProcessStatus.is_awaiting_processing(status):
        preclassification_category = existing_record.get(
            DocumentMetadata.PRECLASSIFICATION_CATEGORY
        )
        crop_image_to_document_roi(bucket_name, object_key)
        invoke_bda(bucket_name, object_key, ddb_key, preclassification_category)
    else:
        logger.info(f"File {ddb_key} already has status: {status}, skipping")


@app.command()
def cli(
    object_key: str = typer.Argument(..., help="S3 object key (e.g. 'input/document.pdf')"),
    bucket_name: str | None = typer.Argument(
        None, help="S3 bucket name (defaults to DOCUMENTAI_INPUT_LOCATION env var)"
    ),
    user_provided_document_category: str | None = typer.Option(
        None, help="User-provided document category (read from S3 metadata if not provided)"
    ),
    job_id: str | None = typer.Option(None, help="Job ID (read from S3 metadata if not provided)"),
    trace_id: str | None = typer.Option(
        None, help="Trace ID (read from S3 metadata if not provided)"
    ),
) -> None:
    """Process uploaded document and invoke BDA."""
    with documentai_api.logging.init(__package__):
        try:
            main(object_key, bucket_name, user_provided_document_category, job_id, trace_id)
        except Exception:
            raise typer.Exit(1) from None


if __name__ == "__main__":
    app()
