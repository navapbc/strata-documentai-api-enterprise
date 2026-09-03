"""Document lifecycle: initial record creation and pre-extraction pipeline."""

import random
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from decimal import Decimal

from botocore.exceptions import ClientError
from opentelemetry import trace
from opentelemetry.propagate import inject

import documentai_api.utils.documents as document_utils
from documentai_api.config.constants import (
    FileValidation,
    ProcessStatus,
)
from documentai_api.config.env import EnvVars, get_required_env
from documentai_api.dtos.classification import PreclassificationMatchResult, TextractResult
from documentai_api.dtos.ddb import InitialDdbRecord, PreClassificationDdbFields, UpdateDdbRecord
from documentai_api.dtos.processing import InternalApiResponse
from documentai_api.logging import get_logger
from documentai_api.models.document_record import DocumentRecord
from documentai_api.services import cloudwatch as cloudwatch_service
from documentai_api.services import s3 as s3_service
from documentai_api.utils.bbox_detection import BboxResult
from documentai_api.utils.blur_detection import BlurResult, detect_blur
from documentai_api.utils.ddb import update_ddb, upsert_ddb
from documentai_api.utils.evaluations import BlurSkipReason
from documentai_api.utils.image_optimization import get_bbox_if_enabled
from documentai_api.utils.otel_context import submit_with_otel_context
from documentai_api.utils.preclassification import find_matching_blueprint, preclassify_document
from documentai_api.utils.response_builder import get_internal_api_response
from documentai_api.utils.response_codes import ResponseCodes
from documentai_api.utils.ssm import (
    is_blur_detection_enabled,
    is_blur_rejection_enforced,
    is_multipage_document_flagging_enabled,
)
from documentai_api.utils.textract import finalize_textract_result, try_textract_identity

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class _BlurOutcome:
    blur_result: BlurResult | None
    process_status: str | None  # None = not terminal, continue to preclassification
    response_code: str | None


@dataclass
class _PreclassificationOutcome:
    process_status: str
    response_code: str
    pre_classification: PreClassificationDdbFields | None
    textract_result: TextractResult | None


def is_selected_for_processing(
    tenant_id: str | None, category_name: str | None
) -> tuple[bool, float | None, float | None]:
    """Return (selected, processing_percentage, processing_assigned_value).

    processing_percentage is None when tenant/category are absent.
    processing_assigned_value is None when percentage is 1.0 (no random value needed).
    """
    from documentai_api.utils.document_categories import get_processing_percentage

    if not tenant_id or not category_name:
        return True, None, None

    percent_processed = get_processing_percentage(tenant_id, category_name)

    if percent_processed >= 1.0:
        return True, percent_processed, None

    selected_value = random.random()
    return selected_value < percent_processed, percent_processed, selected_value


# =============================================================================
# BDA processing status setters
# =============================================================================


def set_bda_processing_status_started(
    object_key: str,
    bda_invocation_arn: str,
    bda_project_arn_used: str | None = None,
    used_category_specific_project: bool = False,
    pages_sent_to_bda: int | None = None,
    bda_invoke_duration_seconds: Decimal | None = None,
    bda_invoke_retry_count: int | None = None,
) -> None:
    """Mark file processing as started with BDA job ARN."""
    update_ddb(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.STARTED,
            internal_api_response=None,
            bda_invocation_arn=bda_invocation_arn,
            bda_project_arn_used=bda_project_arn_used,
            used_category_specific_project=used_category_specific_project,
            pages_sent_to_bda=pages_sent_to_bda,
            bda_invoke_duration_seconds=bda_invoke_duration_seconds,
            bda_invoke_retry_count=bda_invoke_retry_count,
        )
    )


def set_bda_processing_status_not_started(object_key: str) -> None:
    update_ddb(
        UpdateDdbRecord(
            object_key=object_key,
            status=ProcessStatus.NOT_STARTED,
            internal_api_response=None,
        )
    )


def set_processing_status_started(object_key: str, expected_status: str) -> bool:
    """Atomically claim a document by transitioning its status to STARTED.

    Uses a DynamoDB conditional update: succeeds only if the current status
    matches expected_status. Returns True if claimed, False if another
    invocation already claimed it. This prevents duplicate processing from
    concurrent S3-triggered Lambda invocations.
    """
    from documentai_api.services import ddb as ddb_service

    table_name = get_required_env(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME)
    try:
        ddb_service.update_item(
            table_name,
            {"fileName": object_key},
            "SET processStatus = :new_status",
            {":new_status": ProcessStatus.STARTED.value, ":expected": expected_status},
            condition_expression="processStatus = :expected",
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


# =============================================================================
# Initial record creation
# =============================================================================


def insert_minimal_ddb_record(record: DocumentRecord) -> None:
    """Create initial tracking record from the API upload path.

    Uses upsert_ddb so doc-processor's later upsert_initial_ddb_record can update
    in place (preserving createdAt, job_id, trace_id) rather than overwriting.
    """
    upsert_ddb(
        InitialDdbRecord(
            object_key=record.ddb_key,
            original_file_name=record.original_file_name,
            user_provided_document_category=record.category,
            process_status=record.process_status,
            file_size_bytes=record.file_size_bytes,
            content_type=record.content_type,
            job_id=record.job_id,
            system_document_id=record.system_document_id,
            trace_id=record.trace_id,
            batch_id=record.batch_id,
            external_document_id=record.external_document_id,
            external_system_id=record.external_system_id,
            ai_consent_flag=record.ai_consent_flag,
            upload_method=record.upload_method,
            upload_source=record.upload_source,
            tenant_id=record.tenant_id,
            api_key_name=record.api_key_name,
            is_demo=record.is_demo,
            ttl_days=record.ttl_days,
        )
    )

    logger.info(
        f"Inserted initial DDB record for {record.ddb_key} with status {record.process_status}"
    )


def _get_blur_outcome(file_bytes: bytes, content_type: str) -> _BlurOutcome:
    """Run blur detection and return a terminal process_status if the document is rejected.

    Returns _BlurOutcome with process_status=None when blur detection passes or is
    disabled, signalling the caller to continue to preclassification.
    """
    blur_enabled = is_blur_detection_enabled()
    blur_enforced = is_blur_rejection_enforced()

    if not blur_enabled:
        return _BlurOutcome(
            blur_result=BlurResult(
                is_blurry=False, blur_reason_text=BlurSkipReason.DETECTION_DISABLED
            ),
            process_status=None,
            response_code=None,
        )

    blur_result = detect_blur(file_bytes, content_type)

    if blur_result.is_not_document:
        blur_result.blur_reason_text = BlurSkipReason.NOT_A_DOCUMENT

    if blur_result.is_not_document and blur_enforced:
        return _BlurOutcome(
            blur_result, ProcessStatus.NO_DOCUMENT_DETECTED, ResponseCodes.NO_DOCUMENT_DETECTED
        )

    if blur_result.is_blurry and blur_enforced:
        return _BlurOutcome(
            blur_result,
            ProcessStatus.BLURRY_DOCUMENT_DETECTED,
            ResponseCodes.BLURRY_DOCUMENT_DETECTED,
        )

    if blur_result.analysis_failed:
        logger.warning("Blur detection failed, continuing with preclassification")

    return _BlurOutcome(blur_result, None, None)


def _run_preclassification(
    file_bytes: bytes,
    content_type: str,
    user_provided_document_category: str | None,
    pages_detected: int | None,
    ddb_key: str,
) -> _PreclassificationOutcome:
    """Run preclassification and blueprint matching concurrently.

    Both Bedrock calls are independent network-bound invocations with no data
    dependency. Running them in parallel cuts ~5.3s off the pre-BDA wall-clock
    time (sequential: ~10.8s, parallel: ~5.5s).

    Tradeoff: find_matching_blueprint always fires, even for the subset of
    documents that preclassify flags as multi-doc or multipage-inconsistent
    (where the result would be discarded).
    """
    with tracer.start_as_current_span("document.preclassification") as span:
        span.set_attribute("document.content_type", content_type)
        span.set_attribute("document.key", ddb_key)
        with ThreadPoolExecutor(max_workers=2) as executor:
            blueprint_future: Future[PreclassificationMatchResult] = submit_with_otel_context(
                executor, find_matching_blueprint, file_bytes, content_type
            )
            preclassification = preclassify_document(
                file_bytes, content_type, user_provided_document_category or None
            )

    if preclassification.max_document_count_on_page > 1:
        return _PreclassificationOutcome(
            ProcessStatus.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
            ResponseCodes.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
            pre_classification=PreClassificationDdbFields.from_results(preclassification, None),
            textract_result=None,
        )

    if (
        pages_detected
        and pages_detected > 1
        and preclassification.has_multipage_inconsistency
        and is_multipage_document_flagging_enabled()
    ):
        return _PreclassificationOutcome(
            ProcessStatus.MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
            ResponseCodes.MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
            pre_classification=PreClassificationDdbFields.from_results(preclassification, None),
            textract_result=None,
        )

    blueprint_match = blueprint_future.result()
    pre_classification = PreClassificationDdbFields.from_results(preclassification, blueprint_match)
    logger.info(
        "Blueprint match result",
        extra={
            "matched_document_type": blueprint_match.matched_document_type,
            "confidence": blueprint_match.confidence,
            "duration_seconds": str(blueprint_match.duration_seconds),
        },
    )

    textract_result = (
        try_textract_identity(content_type, file_bytes, ddb_key)
        if preclassification.is_identity_document
        else None
    )

    if textract_result is not None:
        # Textract succeeded inline; finalize_textract_result transitions to SUCCESS
        return _PreclassificationOutcome(
            ProcessStatus.STARTED, ResponseCodes.SUCCESS, pre_classification, textract_result
        )

    process_status = (
        ProcessStatus.PENDING_IMAGE_OPTIMIZATION
        if content_type in FileValidation.GRAYSCALE_CONVERTIBLE
        else ProcessStatus.NOT_STARTED
    )
    return _PreclassificationOutcome(
        process_status, ResponseCodes.SUCCESS, pre_classification, None
    )


def upsert_initial_ddb_record(
    source_bucket_name: str,
    source_object_key: str,
    ddb_key: str,
    original_file_name: str,
    tenant_id: str | None = None,
    upload_date: str | None = None,
    user_provided_document_category: str | None = None,
    job_id: str | None = None,
    trace_id: str | None = None,
    batch_id: str | None = None,
    document_processor_started_at: str | None = None,
    is_document_processor_cold_start: bool | None = None,
    file_bytes: bytes | None = None,
    content_type: str | None = None,
    file_size_bytes: int | None = None,
    s3_fetch_duration_seconds: Decimal | None = None,
) -> Future[BboxResult | None] | None:
    """Run preclassification on the S3 object and upsert its DDB record.

    Creates the row if it doesn't exist; updates it in place if it does. Safe
    to call after the API Lambda's insert_minimal_ddb_record - createdAt and
    other minimal-record fields are preserved.

    file_bytes, content_type, and file_size_bytes may be passed in when the
    caller already has them (e.g. from a get_object response), avoiding
    redundant S3 round trips.
    """
    with tracer.start_as_current_span("document.process") as span:
        span.set_attribute("document.key", ddb_key)
        span.set_attribute("document.tenant_id", tenant_id or "")

        # Inject traceparent so downstream Lambda workers (bda-result-processor)
        # can extract it from DDB and attach their spans as children of this trace.
        carrier: dict[str, str] = {}
        inject(carrier)
        traceparent = carrier.get("traceparent")

        if not user_provided_document_category:
            logger.warning(f"Warning: user_provided_document_category is None/empty for {ddb_key}")

        if content_type is None:
            content_type = s3_service.get_content_type(source_bucket_name, source_object_key)

        if file_size_bytes is None:
            file_size_bytes = s3_service.get_file_size_bytes(source_bucket_name, source_object_key)

        if file_bytes is None:
            file_bytes = s3_service.get_file_bytes(source_bucket_name, source_object_key)

        response_code = ResponseCodes.SUCCESS
        internal_api_response: InternalApiResponse | None = None
        process_status = ProcessStatus.PENDING_IMAGE_OPTIMIZATION
        pages_detected = document_utils.get_page_count(file_bytes)
        is_password_protected = document_utils.is_password_protected(file_bytes)
        blur_result: BlurResult | None = None
        processing_percentage: float | None = None
        processing_assigned_value: float | None = None
        pre_classification: PreClassificationDdbFields | None = None
        textract_result = None

        # assume document will be processed, but check if it should be excluded by sampling
        is_processing_selected = True

        if not is_password_protected:
            is_processing_selected, processing_percentage, processing_assigned_value = (
                is_selected_for_processing(tenant_id, user_provided_document_category)
            )

        # purposefully not using elif here so that password-protected docs are not subject to sampling
        if is_password_protected:
            process_status = ProcessStatus.PASSWORD_PROTECTED
            response_code = ResponseCodes.PASSWORD_PROTECTED
            textract_result = None
            if batch_id:
                from documentai_api.utils.batch_operations import increment_resolved_count

                increment_resolved_count(batch_id)

        elif not is_processing_selected:
            logger.info(
                f"{ddb_key} excluded by sampling for category {user_provided_document_category}"
            )
            cloudwatch_service.put_metric_data(
                "DocumentAI/DocumentProcessor",
                "ProcessingExcludedBySampling",
                1,
                dimensions={"Category": user_provided_document_category or "unknown"},
            )

            if tenant_id and upload_date:
                from documentai_api.utils.write_limit import decrement

                decrement(tenant_id, upload_date)

            if batch_id:
                from documentai_api.utils.batch_operations import increment_resolved_count

                increment_resolved_count(batch_id)

            process_status = ProcessStatus.PROCESSING_EXCLUDED
            response_code = ResponseCodes.PROCESSING_EXCLUDED
            textract_result = None

        else:
            with ThreadPoolExecutor(max_workers=3) as executor:
                blur_future: Future[_BlurOutcome] = submit_with_otel_context(
                    executor, _get_blur_outcome, file_bytes, content_type
                )
                preclassification_future: Future[_PreclassificationOutcome] = (
                    submit_with_otel_context(
                        executor,
                        _run_preclassification,
                        file_bytes,
                        content_type,
                        user_provided_document_category,
                        pages_detected,
                        ddb_key,
                    )
                )
                bbox_future: Future[BboxResult | None] = submit_with_otel_context(
                    executor, get_bbox_if_enabled, file_bytes, content_type
                )

            blur_outcome = blur_future.result()
            preclassification_outcome = preclassification_future.result()
            blur_result = blur_outcome.blur_result

            if blur_outcome.process_status is not None:
                process_status = blur_outcome.process_status
                response_code = blur_outcome.response_code or ResponseCodes.SUCCESS
            else:
                process_status = preclassification_outcome.process_status
                response_code = preclassification_outcome.response_code
                pre_classification = preclassification_outcome.pre_classification
                textract_result = preclassification_outcome.textract_result

        # initial status does not qualify for bda processing
        # create the json response signaling the process is complete
        # (skip for Textract -- finalize_textract_result handles its own response)
        if not ProcessStatus.is_pending_extraction(process_status) and textract_result is None:
            internal_api_response = get_internal_api_response(
                object_key=ddb_key,
                response_code=response_code,
                matched_document_class=None,
                user_provided_document_category=user_provided_document_category,
            )

        upsert_ddb(
            InitialDdbRecord(
                object_key=ddb_key,
                original_file_name=original_file_name,
                user_provided_document_category=user_provided_document_category,
                process_status=process_status,
                internal_api_response=internal_api_response,
                file_size_bytes=file_size_bytes,
                content_type=content_type,
                pages_detected=pages_detected,
                job_id=job_id,
                trace_id=trace_id,
                batch_id=batch_id,
                is_document_blurry=blur_result.is_blurry if blur_result else False,
                blur_analysis_failed=blur_result.analysis_failed if blur_result else False,
                ocr_avg_word_confidence=blur_result.avg_confidence if blur_result else None,
                document_word_count=blur_result.word_count if blur_result else None,
                blur_llm_checked=blur_result.llm_checked if blur_result else False,
                blur_quadrant_stats=blur_result.quadrant_stats if blur_result else None,
                blur_reason_text=blur_result.blur_reason_text
                if blur_result
                else BlurSkipReason.from_status(process_status),
                blur_detection_duration_seconds=blur_result.duration_seconds
                if blur_result
                else None,
                is_password_protected=is_password_protected,
                pre_classification=pre_classification,
                document_processor_started_at=document_processor_started_at,
                is_document_processor_cold_start=is_document_processor_cold_start,
                processing_percentage=processing_percentage,
                processing_assigned_value=processing_assigned_value,
                s3_fetch_duration_seconds=s3_fetch_duration_seconds,
                traceparent=traceparent,
            )
        )

        # explicitly remove file reference to free memory
        del file_bytes

        # Textract completed inline - finalize the record with extraction results
        if textract_result is not None:
            finalize_textract_result(
                ddb_key, textract_result, user_provided_document_category, batch_id
            )

        if ProcessStatus.is_pending_extraction(process_status):
            return bbox_future

        return None
