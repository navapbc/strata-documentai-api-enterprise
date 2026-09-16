#!/usr/bin/env python3
"""Process uploaded documents: insert to DDB, convert if needed, invoke BDA."""

import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import typer
from tenacity import (
    RetryError,
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

import documentai_api.logging
from documentai_api.classifiers.document_classification import (
    classify_as_ai_consent_declined,
    classify_as_extraction_not_configured,
    classify_as_failed,
    classify_as_not_implemented,
)
from documentai_api.config.constants import (
    ProcessStatus,
    S3MetadataKeys,
)
from documentai_api.config.env import get_env_config
from documentai_api.dtos.classification import ClassificationData
from documentai_api.dtos.processing import (
    CropResult,
    LlmExtractionMessage,
    OptimizationResult,
    PreExtractionResult,
)
from documentai_api.pipeline.document_lifecycle import (
    set_bda_processing_status_started,
    set_processing_status_started,
    upsert_initial_ddb_record,
)
from documentai_api.pipeline.textract import run_textract_pipeline
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.services import ddb as ddb_service
from documentai_api.services import s3 as s3_service
from documentai_api.services import sqs as sqs_service
from documentai_api.services.exceptions import is_retryable
from documentai_api.services.textract import get_ocr_blocks
from documentai_api.utils.bda_invoker import (
    invoke_bedrock_data_automation,
    skip_bda_if_unclassified,
)
from documentai_api.utils.dates import strip_time
from documentai_api.utils.ddb import get_ddb_record
from documentai_api.utils.image_optimization import optimize_s3_image
from documentai_api.utils.s3 import parse_s3_uri
from documentai_api.utils.ssm import is_llm_extraction_enabled
from documentai_api.utils.uploads import validate_s3_object_is_bda_native

logger = documentai_api.logging.get_logger(__name__)
app = typer.Typer()


@dataclass
class _PreclassifyResult:
    # Internal data class not to be mistaken with a dto. Leave private and local.
    existing_record: dict[str, Any]
    pre_extraction_result: PreExtractionResult | None
    bbox_future: Any
    tenant_id: str | None


def _preclassify(
    bucket_name: str,
    object_key: str,
    ddb_key: str,
    original_file_name: str,
    existing_record: dict[str, Any] | None,
    s3_content_type: str,
    s3_file_bytes: bytes,
    s3_file_size_bytes: int,
    s3_fetch_duration: Decimal,
    processor_started_at: str,
    is_cold_start: bool,
    user_provided_document_category: str | None,
    job_id: str | None,
    trace_id: str | None,
    batch_id: str | None,
) -> _PreclassifyResult:
    """Run preclassification if needed and return the post-preclassification state."""
    tenant_id = existing_record.get(DocumentMetadata.TENANT_ID) if existing_record else None

    needs_preclassification = existing_record is None or (
        ProcessStatus.is_awaiting_processing(
            existing_record.get(DocumentMetadata.PROCESS_STATUS, "")
        )
        and DocumentMetadata.PRECLASSIFICATION_CATEGORY not in existing_record
    )

    if not needs_preclassification:
        return _PreclassifyResult(
            existing_record=existing_record,  # type: ignore[arg-type]
            pre_extraction_result=None,
            bbox_future=None,
            tenant_id=tenant_id,
        )

    pre_extraction_result = upsert_initial_ddb_record(
        source_bucket_name=bucket_name,
        source_object_key=object_key,
        ddb_key=ddb_key,
        original_file_name=original_file_name,
        tenant_id=tenant_id,
        upload_date=strip_time(existing_record[DocumentMetadata.CREATED_AT])
        if existing_record and DocumentMetadata.CREATED_AT in existing_record
        else None,
        user_provided_document_category=user_provided_document_category,
        job_id=job_id,
        trace_id=trace_id,
        batch_id=batch_id,
        document_processor_started_at=processor_started_at,
        is_document_processor_cold_start=is_cold_start,
        file_bytes=s3_file_bytes,
        content_type=s3_content_type,
        file_size_bytes=s3_file_size_bytes,
        s3_fetch_duration_seconds=s3_fetch_duration,
    )
    updated_record = get_ddb_record(ddb_key)

    if updated_record is None:
        raise Exception("Could not retrieve DDB record after upsert")

    return _PreclassifyResult(
        existing_record=updated_record,
        pre_extraction_result=pre_extraction_result,
        bbox_future=pre_extraction_result.bbox_future if pre_extraction_result else None,
        tenant_id=tenant_id,
    )


def _should_invoke_bda(preclassification_category: str | None) -> bool:
    """Determine if BDA should be invoked based on preclassification and feature flag.

    Skip is driven by preclassify returning "other_document" (i.e. no category,
    so no blueprint would match) - NOT by an actual blueprint match test. The
    flag name references blueprints because "unclassified" implies "no blueprint
    will match"; the live check is the free other_document signal from preclassify.
    """
    if preclassification_category and preclassification_category != "other_document":
        return True

    return not skip_bda_if_unclassified()


def _persist_optimization_metrics(
    ddb_key: str,
    crop_result: CropResult,
    grayscale_applied: bool,
    processed_file_size_bytes: int | None,
    opt_result: OptimizationResult | None = None,
) -> None:
    """Write image optimization metrics to the DDB record."""
    field_map = {
        DocumentMetadata.CROP_BOUNDING_BOX: str(list(crop_result.bounding_box))
        if crop_result.bounding_box
        else None,
        DocumentMetadata.CROP_RETAINED_PERCENTAGE: crop_result.retained_percentage,
        DocumentMetadata.CROP_DURATION_SECONDS: crop_result.duration_seconds,
        DocumentMetadata.CROP_INPUT_TOKENS: crop_result.input_tokens,
        DocumentMetadata.CROP_OUTPUT_TOKENS: crop_result.output_tokens,
        DocumentMetadata.CROP_MODEL_ID: crop_result.model_id,
        DocumentMetadata.GRAYSCALE_CONVERSION: grayscale_applied,
        DocumentMetadata.PROCESSED_FILE_SIZE_BYTES: processed_file_size_bytes,
        DocumentMetadata.IMAGE_OPT_CROP_BLOCK_DURATION_SECONDS: opt_result.crop_block_duration_seconds
        if opt_result
        else None,
        DocumentMetadata.IMAGE_OPT_WRITE_DURATION_SECONDS: opt_result.write_duration_seconds
        if opt_result
        else None,
    }

    updates = []
    values = {}
    for field, value in field_map.items():
        if value is not None:
            param = f":{field[0].lower()}{field[1:]}"
            updates.append(f"{field} = {param}")
            values[param] = value

    if updates:
        table_name = get_env_config().get_document_metadata_table_name
        ddb_service.update_item(
            table_name, {"fileName": ddb_key}, "SET " + ", ".join(updates), values
        )


def _invoke_textract_if_identity_path(
    pre_extraction_result: PreExtractionResult | None,
    ddb_key: str,
    content_type: str | None,
    file_bytes: bytes | None,
    tenant_id: str,
    batch_id: str | None = None,
) -> bool:
    """Run Textract extraction if preclassification identified an identity document.

    Returns True if Textract handled the document (caller should skip BDA).
    """
    if not pre_extraction_result or not pre_extraction_result.is_identity_document:
        return False

    if not content_type or not file_bytes:
        return False

    try:
        return run_textract_pipeline(ddb_key, content_type, file_bytes, tenant_id, batch_id)
    except Exception as e:
        logger.error(f"Textract extraction failed for {ddb_key}: {e}")
        return False


def _invoke_bda(
    bucket_name: str,
    object_key: str,
    ddb_key: str,
    tenant_id: str,
    preclassification_category: str | None = None,
) -> dict[str, Any]:
    """Invoke BDA for a file that's ready for processing."""
    result: dict[str, Any] = {}
    retry_count = 0

    for attempt in Retrying(
        stop=stop_after_attempt(get_env_config().max_bda_invoke_retry_attempts),
        wait=wait_exponential_jitter(initial=10, max=120),
        retry=retry_if_exception(is_retryable),
    ):
        with attempt:
            if attempt.retry_state.attempt_number > 1:
                retry_count += 1
            invoke_start = time.monotonic()
            invocation_arn, project_arn, pages_sent, used_category_specific_project = (
                invoke_bedrock_data_automation(
                    bucket_name, object_key, tenant_id, ddb_key, preclassification_category
                )
            )
            invoke_duration = Decimal(str(round(time.monotonic() - invoke_start, 3)))

            set_bda_processing_status_started(
                object_key=ddb_key,
                bda_invocation_arn=invocation_arn,
                bda_project_arn_used=project_arn,
                used_category_specific_project=used_category_specific_project,
                pages_sent_to_bda=pages_sent,
                bda_invoke_duration_seconds=invoke_duration,
                bda_invoke_retry_count=retry_count,
            )

            logger.info(f"BDA job started for {ddb_key}, ARN: {invocation_arn}")
            result = {"invocationArn": invocation_arn}

    return result


def invoke_bda(
    bucket_name: str,
    object_key: str,
    ddb_key: str,
    tenant_id: str,
    preclassification_category: str | None = None,
    batch_id: str | None = None,
) -> dict[str, Any]:
    """Wrapper that handles retry failures."""
    try:
        return _invoke_bda(bucket_name, object_key, ddb_key, tenant_id, preclassification_category)
    except RetryError as e:
        retry_state = e.last_attempt
        attempt_number = retry_state.attempt_number

        logger.error(f"BDA invocation failed for {ddb_key} after {attempt_number} attempts: {e}")
        classify_as_failed(
            object_key=ddb_key,
            error_message="BDA invocation failed",
            data=ClassificationData(additional_info=str(e)),
            batch_id=batch_id,
        )
        raise


def _invoke_llm_path(
    ddb_key: str,
    existing_record: dict[str, Any],
    file_bytes: bytes,
    content_type: str,
    tenant_id: str,
    batch_id: str | None,
) -> None:
    """Write OCR blocks to S3 and enqueue an LLM extraction request.

    No-ops when the feature flag is off or no blueprint type was matched.
    Errors are logged and swallowed — BDA is the authoritative extraction path.
    """
    import json

    document_type = existing_record.get(DocumentMetadata.PRECLASSIFICATION_BLUEPRINT_MATCHED_TYPE)

    if not document_type or not is_llm_extraction_enabled():
        return

    try:
        output_location = get_env_config().get_output_location
        output_bucket, output_prefix = parse_s3_uri(output_location)
        ocr_blocks = get_ocr_blocks(file_bytes)
        ocr_key = f"{output_prefix}/llm/ocr/{ddb_key}.json"
        s3_service.put_object(
            output_bucket,
            ocr_key,
            json.dumps(ocr_blocks).encode(),
            content_type="application/json",
        )
        ocr_blocks_uri = f"s3://{output_bucket}/{ocr_key}"

        queue_url = get_env_config().llm_input_queue_url
        if not queue_url:
            logger.warning("LLM_INPUT_QUEUE_URL not set, skipping LLM extraction")
            return

        from opentelemetry.propagate import inject

        carrier: dict[str, str] = {}
        inject(carrier)
        message_attributes = {
            k: {"DataType": "String", "StringValue": v} for k, v in carrier.items()
        } or None
        payload = json.dumps(
            LlmExtractionMessage(
                ddb_key=ddb_key,
                document_type=document_type,
                ocr_blocks_uri=ocr_blocks_uri,
                tenant_id=tenant_id,
                batch_id=batch_id,
            ).to_dict()
        )
        sqs_service.send_message(queue_url, payload, message_attributes)
        logger.info(f"Enqueued LLM extraction for {ddb_key}")
    except Exception as e:
        logger.error(f"Failed to enqueue LLM extraction for {ddb_key}: {e}")


def _invoke_bda_path(
    bucket_name: str,
    object_key: str,
    ddb_key: str,
    existing_record: dict[str, Any],
    s3_content_type: str,
    s3_file_bytes: bytes,
    bbox_future: Any,
    apply_grayscale: bool,
    tenant_id: str,
    batch_id: str | None,
) -> None:
    """Optimize image and invoke BDA (or classify as not-configured/not-implemented)."""
    preclassification_document_type = existing_record.get(
        DocumentMetadata.PRECLASSIFICATION_CATEGORY
    )
    routing_category = existing_record.get(
        DocumentMetadata.PRECLASSIFICATION_BLUEPRINT_MATCH_CATEGORY
    )

    opt = optimize_s3_image(
        bucket_name,
        object_key,
        apply_grayscale=apply_grayscale,
        file_bytes=s3_file_bytes,
        content_type=s3_content_type,
        precomputed_bbox=bbox_future.result() if bbox_future is not None else None,
    )

    if apply_grayscale and (opt.too_large or opt.failed):
        # It's possible, though unlikely, that an image is too large after optimization.
        # If so, we persist the optimization metrics for future reference and
        # classify the document as not implemented
        _persist_optimization_metrics(ddb_key, opt.crop_result, False, None, opt_result=opt)
        classify_as_not_implemented(
            object_key=ddb_key,
            data=ClassificationData(
                additional_info="File too large after conversion"
                if opt.too_large
                else "Failed to download file for optimization"
            ),
            batch_id=batch_id,
        )
        return

    _persist_optimization_metrics(
        ddb_key, opt.crop_result, opt.grayscale_applied, opt.file_size_bytes, opt_result=opt
    )

    if _should_invoke_bda(preclassification_document_type):
        invoke_bda(bucket_name, object_key, ddb_key, tenant_id, routing_category, batch_id)

        if apply_grayscale:
            logger.info(f"Optimized {ddb_key} and invoked BDA")
    else:
        logger.info(f"{ddb_key} preclassified as other_document; skipping BDA (flag on)")
        classify_as_extraction_not_configured(
            object_key=ddb_key,
            data=ClassificationData(
                additional_info="Preclassified as other_document; BDA skipped per feature flag"
            ),
            batch_id=batch_id,
        )


def _dispatch_document_processor(
    bucket_name: str,
    object_key: str,
    ddb_key: str,
    status: str | None,
    existing_record: dict[str, Any],
    pre_extraction_result: PreExtractionResult | None,
    tenant_id: str | None,
    s3_content_type: str,
    s3_file_bytes: bytes,
    bbox_future: Any,
    batch_id: str | None,
) -> None:
    """Validate content and dispatch to the appropriate extraction path."""
    # upload paths with ai consent false should never make it this far, but
    # handle it defensively if it occurs. this should never happen in theory,
    # but if it does, we don't want to process the file
    if existing_record.get(DocumentMetadata.AI_CONSENT_FLAG) is False:
        logger.info(f"AI consent declined for {ddb_key}, skipping processing")
        classify_as_ai_consent_declined(object_key=ddb_key, batch_id=batch_id)
        return

    if status == ProcessStatus.PENDING_IMAGE_OPTIMIZATION:
        apply_grayscale = True
    elif status and ProcessStatus.is_awaiting_processing(status):
        apply_grayscale = False
    else:
        # Already processing or terminal (SUCCESS, FAILED, STARTED) - skip.
        logger.info(f"File {ddb_key} already has status: {status}, skipping")
        return

    try:
        validate_s3_object_is_bda_native(bucket_name, object_key)
    except ValueError as e:
        logger.warning(f"Rejecting {ddb_key}: {e}")
        classify_as_failed(
            object_key=ddb_key,
            error_message="Uploaded file content is not a supported document type",
            data=ClassificationData(additional_info=str(e)),
            batch_id=batch_id,
        )
        return

    if not tenant_id:
        logger.error(f"Cannot dispatch {ddb_key}: tenant_id is required")
        classify_as_failed(
            object_key=ddb_key,
            error_message="tenant_id is required for document processing",
            data=ClassificationData(additional_info="Missing tenant_id"),
            batch_id=batch_id,
        )
        return

    if not set_processing_status_started(ddb_key, status):
        # Atomically claim - only one invocation proceeds; duplicates bail.
        logger.info(f"{ddb_key} already claimed from {status}; skipping")
        return

    # Textract identity and BDA are mutually exclusive. Textract identity is
    # optimized for identity documents (driver's licenses, passports), and
    # is 5x to 20x faster than BDA.
    if _invoke_textract_if_identity_path(
        pre_extraction_result, ddb_key, s3_content_type, s3_file_bytes, tenant_id, batch_id
    ):
        # Exit early - Textract handled the document.
        return

    _invoke_llm_path(
        ddb_key,
        existing_record,
        s3_file_bytes,
        s3_content_type,
        tenant_id,
        batch_id,
    )

    _invoke_bda_path(
        bucket_name,
        object_key,
        ddb_key,
        existing_record,
        s3_content_type,
        s3_file_bytes,
        bbox_future,
        apply_grayscale=apply_grayscale,
        tenant_id=tenant_id,
        batch_id=batch_id,
    )


def main(
    object_key: str,
    bucket_name: str | None = None,
    user_provided_document_category: str | None = None,
    job_id: str | None = None,
    trace_id: str | None = None,
    batch_id: str | None = None,
    is_cold_start: bool = False,
) -> None:
    """Process uploaded document: fetch from S3, preclassify, dispatch to extraction."""
    processor_started_at = datetime.now(UTC)
    if bucket_name is None:
        input_location = get_env_config().get_input_location
        bucket_name, _ = parse_s3_uri(input_location)

    logger.info(f"Processing document: s3://{bucket_name}/{object_key}")

    # Single get_object call eliminates separate head_object + get_content_type +
    # get_file_size_bytes round trips.
    s3_fetch_start = time.monotonic()
    s3_response = s3_service.get_object(bucket_name, object_key)
    metadata = s3_response.get("Metadata", {})
    s3_content_type: str = str(s3_response.get("ContentType", "application/octet-stream"))
    s3_file_size_bytes: int = int(s3_response.get("ContentLength", 0))
    s3_file_bytes: bytes = bytes(s3_response["Body"].read())
    s3_fetch_duration = Decimal(str(round(time.monotonic() - s3_fetch_start, 3)))

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

    ddb_key = os.path.basename(object_key)
    existing_record = get_ddb_record(ddb_key)

    preclassify_result = _preclassify(
        bucket_name=bucket_name,
        object_key=object_key,
        ddb_key=ddb_key,
        original_file_name=original_file_name,
        existing_record=existing_record,
        s3_content_type=s3_content_type,
        s3_file_bytes=s3_file_bytes,
        s3_file_size_bytes=s3_file_size_bytes,
        s3_fetch_duration=s3_fetch_duration,
        processor_started_at=processor_started_at.isoformat(),
        is_cold_start=is_cold_start,
        user_provided_document_category=user_provided_document_category,
        job_id=job_id,
        trace_id=trace_id,
        batch_id=batch_id,
    )

    existing_record = preclassify_result.existing_record
    status = existing_record.get(DocumentMetadata.PROCESS_STATUS)
    logger.info(
        f"Processing {ddb_key}: status={status}, "
        f"has_preclassification={'preclassificationCategory' in existing_record}"
    )

    _dispatch_document_processor(
        bucket_name=bucket_name,
        object_key=object_key,
        ddb_key=ddb_key,
        status=status,
        existing_record=existing_record,
        pre_extraction_result=preclassify_result.pre_extraction_result,
        tenant_id=preclassify_result.tenant_id,
        s3_content_type=s3_content_type,
        s3_file_bytes=s3_file_bytes,
        bbox_future=preclassify_result.bbox_future,
        batch_id=batch_id,
    )


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
