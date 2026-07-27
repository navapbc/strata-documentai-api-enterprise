"""Document classification state machine and initial record creation."""

import random
from typing import Any

from botocore.exceptions import ClientError

import documentai_api.utils.documents as document_utils
from documentai_api.config.constants import (
    FileValidation,
    ProcessStatus,
)
from documentai_api.config.env import EnvVars, get_required_env
from documentai_api.dtos.classification import ClassificationData, PreclassificationMatchResult
from documentai_api.dtos.ddb import PreClassificationDdbFields, UpsertDdbData
from documentai_api.dtos.processing import InternalApiResponse
from documentai_api.logging import get_logger
from documentai_api.models.document_record import DocumentRecord
from documentai_api.services import s3 as s3_service
from documentai_api.utils.blur_detection import detect_blur
from documentai_api.utils.ddb import (
    update_ddb,
    upsert_ddb,
)
from documentai_api.utils.preclassification import find_matching_blueprint, preclassify_document
from documentai_api.utils.response_builder import get_internal_api_response
from documentai_api.utils.response_codes import ResponseCodes
from documentai_api.utils.ssm import is_blur_detection_enabled, is_blur_rejection_enforced
from documentai_api.utils.textract import finalize_textract_result, try_textract_identity

logger = get_logger(__name__)


# =============================================================================
# Classification state machine
# =============================================================================


def classify_as_success(
    object_key: str,
    response_code: str,
    data: ClassificationData,
    below_extraction_confidence_floor: bool = False,
    result_processor_started_at: str | None = None,
) -> dict[str, Any]:
    """Mark file processing as completed."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=response_code,
        matched_document_class=data.matched_document_class,
    )

    update_ddb(
        object_key=object_key,
        status=ProcessStatus.SUCCESS,
        internal_api_response=internal_api_response,
        data=data,
        below_extraction_confidence_floor=below_extraction_confidence_floor,
        result_processor_started_at=result_processor_started_at,
    )

    # convert dataclass to dict for JSON serialization
    return internal_api_response.__dict__


def classify_as_failed(
    object_key: str,
    error_message: str,
    data: ClassificationData,
    result_processor_started_at: str | None = None,
) -> dict[str, Any]:
    """Mark file processing as failed with error message."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.INTERNAL_PROCESSING_ERROR,
        matched_document_class=None,
    )

    update_ddb(
        object_key=object_key,
        status=ProcessStatus.FAILED,
        internal_api_response=internal_api_response,
        error_message=error_message,
        data=data,
        result_processor_started_at=result_processor_started_at,
    )

    # convert dataclass to dict for JSON serialization
    return internal_api_response.__dict__


def classify_as_not_implemented(object_key: str, data: ClassificationData) -> dict[str, Any]:
    """Mark file processing as not implemented."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.DOCUMENT_TYPE_NOT_IMPLEMENTED,
        matched_document_class=None,
    )

    update_ddb(
        object_key=object_key,
        status=ProcessStatus.SUCCESS,
        internal_api_response=internal_api_response,
        data=data,
    )

    # convert dataclass to dict for JSON serialization
    return internal_api_response.__dict__


def classify_as_no_document_detected(
    object_key: str, data: ClassificationData, result_processor_started_at: str | None = None
) -> dict[str, Any]:
    """Mark file processing as no document detected."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.NO_DOCUMENT_DETECTED,
        matched_document_class=None,
    )

    update_ddb(
        object_key=object_key,
        status=ProcessStatus.NO_DOCUMENT_DETECTED,
        internal_api_response=internal_api_response,
        data=data,
        result_processor_started_at=result_processor_started_at,
    )

    # convert dataclass to dict for JSON serialization
    return internal_api_response.__dict__


def classify_as_ai_consent_declined(object_key: str) -> dict[str, Any]:
    """Mark file as not processed due to AI consent not provided."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.AI_CONSENT_DECLINED,
        matched_document_class=None,
    )

    update_ddb(
        object_key=object_key,
        status=ProcessStatus.AI_CONSENT_DECLINED,
        internal_api_response=internal_api_response,
    )

    return internal_api_response.__dict__


def classify_as_conversion_failed(object_key: str, error_message: str) -> dict[str, Any]:
    """Mark file as failed due to image format conversion error."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.INTERNAL_PROCESSING_ERROR,
        matched_document_class=None,
    )

    update_ddb(
        object_key=object_key,
        status=ProcessStatus.CONVERSION_FAILED,
        internal_api_response=internal_api_response,
        error_message=error_message,
    )

    return internal_api_response.__dict__


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


def classify_as_no_custom_blueprint_matched(
    object_key: str, data: ClassificationData, result_processor_started_at: str | None = None
) -> dict[str, Any]:
    """Mark file processing as not implemented."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.DOCUMENT_TYPE_NOT_IMPLEMENTED,
        matched_document_class=None,
    )

    update_ddb(
        object_key=object_key,
        status=ProcessStatus.NO_CUSTOM_BLUEPRINT_MATCHED,
        internal_api_response=internal_api_response,
        data=data,
        result_processor_started_at=result_processor_started_at,
    )

    # convert dataclass to dict for JSON serialization
    return internal_api_response.__dict__


def classify_as_multiple_documents_on_page(
    object_key: str, data: ClassificationData
) -> dict[str, Any]:
    """Mark file processing as multiple documents detected on single page."""
    internal_api_response: InternalApiResponse = get_internal_api_response(
        object_key=object_key,
        response_code=ResponseCodes.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
        matched_document_class=None,
    )

    update_ddb(
        object_key=object_key,
        status=ProcessStatus.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
        internal_api_response=internal_api_response,
        data=data,
    )

    # convert dataclass to dict for JSON serialization
    return internal_api_response.__dict__


# =============================================================================
# BDA processing status setters
# =============================================================================


def set_bda_processing_status_started(
    object_key: str,
    bda_invocation_arn: str,
    bda_project_arn_used: str | None = None,
    pages_sent_to_bda: int | None = None,
) -> None:
    """Mark file processing as started with BDA job ARN."""
    update_ddb(
        object_key=object_key,
        status=ProcessStatus.STARTED,
        internal_api_response=None,
        bda_invocation_arn=bda_invocation_arn,
        bda_project_arn_used=bda_project_arn_used,
        pages_sent_to_bda=pages_sent_to_bda,
    )


def set_bda_processing_status_not_started(object_key: str) -> None:
    update_ddb(
        object_key=object_key,
        status=ProcessStatus.NOT_STARTED,
        internal_api_response=None,
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
        UpsertDdbData(
            object_key=record.ddb_key,
            original_file_name=record.original_file_name,
            user_provided_document_category=record.category,
            process_status=record.process_status,
            file_size_bytes=record.file_size_bytes,
            content_type=record.content_type,
            job_id=record.job_id,
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
) -> None:
    """Run preclassification on the S3 object and upsert its DDB record.

    Creates the row if it doesn't exist; updates it in place if it does. Safe
    to call after the API Lambda's insert_minimal_ddb_record - createdAt and
    other minimal-record fields are preserved.
    """
    if not user_provided_document_category:
        logger.warning(f"Warning: user_provided_document_category is None/empty for {ddb_key}")
        user_provided_document_category = "unknown"

    content_type = s3_service.get_content_type(source_bucket_name, source_object_key)
    file_size_bytes = s3_service.get_file_size_bytes(source_bucket_name, source_object_key)
    file_bytes = s3_service.get_file_bytes(source_bucket_name, source_object_key)

    response_code = ResponseCodes.SUCCESS
    internal_api_response: InternalApiResponse | None = None
    process_status = ProcessStatus.PENDING_IMAGE_OPTIMIZATION
    pages_detected = document_utils.get_page_count(file_bytes)
    is_password_protected = document_utils.is_password_protected(file_bytes)
    is_document_blurry = False
    blur_analysis_failed = False
    ocr_avg_word_confidence: float | None = None
    document_word_count: int | None = None
    blur_llm_checked = False
    processing_percentage: float | None = None
    processing_assigned_value: float | None = None
    pre_classification_document_type = None
    pre_classification_confidence = None
    pre_classification_input_tokens = None
    pre_classification_output_tokens = None
    pre_classification_duration_seconds = None
    pre_classification_model_id = None
    pre_classification_blueprint_match_result: PreclassificationMatchResult | None = None
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

    elif not is_processing_selected:
        logger.info(
            f"{ddb_key} excluded by sampling for category {user_provided_document_category}"
        )
        # TODO: add a CloudWatch metric filter on this log line (dimensioned by category)
        # to make sampling rates observable without a custom metric
        if tenant_id and upload_date:
            from documentai_api.utils.write_limit import decrement

            decrement(tenant_id, upload_date)
        process_status = ProcessStatus.PROCESSING_EXCLUDED
        response_code = ResponseCodes.PROCESSING_EXCLUDED
        textract_result = None

    else:
        # Textract-based blur detection (deterministic, confidence-score based)
        blur_enabled = is_blur_detection_enabled()
        blur_enforced = is_blur_rejection_enforced()

        if blur_enabled:
            blur_result = detect_blur(file_bytes, content_type)
            is_document_blurry = blur_result.is_blurry
            blur_analysis_failed = blur_result.analysis_failed
            ocr_avg_word_confidence = blur_result.avg_confidence
            document_word_count = blur_result.word_count
            blur_llm_checked = blur_result.llm_checked

            if blur_result.is_not_document and blur_enforced:
                process_status = ProcessStatus.NO_DOCUMENT_DETECTED
                response_code = ResponseCodes.NO_DOCUMENT_DETECTED
                textract_result = None

            elif blur_result.is_blurry and blur_enforced:
                process_status = ProcessStatus.BLURRY_DOCUMENT_DETECTED
                response_code = ResponseCodes.BLURRY_DOCUMENT_DETECTED
                textract_result = None

            elif blur_result.analysis_failed:
                logger.warning("Blur detection failed, continuing with preclassification")

        if process_status not in (
            ProcessStatus.NO_DOCUMENT_DETECTED,
            ProcessStatus.BLURRY_DOCUMENT_DETECTED,
        ):
            # Blur check passed or was skipped - run LLM preclassification
            result = preclassify_document(file_bytes, content_type)

            pre_classification_document_type = result.document_type
            pre_classification_confidence = result.confidence
            pre_classification_input_tokens = result.input_tokens
            pre_classification_output_tokens = result.output_tokens
            pre_classification_duration_seconds = result.duration_seconds
            pre_classification_model_id = result.model_id

            if result.document_count > 1:
                process_status = ProcessStatus.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE
                response_code = ResponseCodes.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE
                textract_result = None

            else:
                pre_classification_blueprint_match_result = find_matching_blueprint(
                    file_bytes, content_type, category=result.document_type
                )
                logger.info(
                    "Blueprint match result",
                    extra={
                        "matched_document_type": pre_classification_blueprint_match_result.matched_document_type,
                        "confidence": pre_classification_blueprint_match_result.confidence,
                        "duration_seconds": str(
                            pre_classification_blueprint_match_result.duration_seconds
                        ),
                    },
                )

                # Check if this is an identity document eligible for Textract
                textract_result = try_textract_identity(
                    result.document_type, content_type, file_bytes, ddb_key
                )

                if textract_result is None:
                    # Not a Textract-eligible doc or flag is off; route to BDA
                    if content_type in FileValidation.GRAYSCALE_CONVERTIBLE:
                        process_status = ProcessStatus.PENDING_IMAGE_OPTIMIZATION
                    else:
                        process_status = ProcessStatus.NOT_STARTED
                else:
                    # Textract succeeded inline; upsert as STARTED, finalize_textract_result
                    # will transition to SUCCESS after the upsert
                    process_status = ProcessStatus.STARTED

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
        UpsertDdbData(
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
            is_document_blurry=is_document_blurry,
            blur_analysis_failed=blur_analysis_failed,
            ocr_avg_word_confidence=ocr_avg_word_confidence,
            document_word_count=document_word_count,
            blur_llm_checked=blur_llm_checked,
            is_password_protected=is_password_protected,
            pre_classification=PreClassificationDdbFields(
                document_type=pre_classification_document_type,
                confidence=pre_classification_confidence,
                input_tokens=pre_classification_input_tokens,
                output_tokens=pre_classification_output_tokens,
                duration_seconds=pre_classification_duration_seconds,
                model_id=pre_classification_model_id,
                blueprint_matched_document_type=(
                    pre_classification_blueprint_match_result.matched_document_type
                    if pre_classification_blueprint_match_result
                    else None
                ),
                blueprint_match_confidence=(
                    pre_classification_blueprint_match_result.confidence
                    if pre_classification_blueprint_match_result
                    else None
                ),
                blueprint_match_input_tokens=(
                    pre_classification_blueprint_match_result.input_tokens
                    if pre_classification_blueprint_match_result
                    else None
                ),
                blueprint_match_output_tokens=(
                    pre_classification_blueprint_match_result.output_tokens
                    if pre_classification_blueprint_match_result
                    else None
                ),
                blueprint_match_duration_seconds=(
                    pre_classification_blueprint_match_result.duration_seconds
                    if pre_classification_blueprint_match_result
                    else None
                ),
            ),
            document_processor_started_at=document_processor_started_at,
            is_document_processor_cold_start=is_document_processor_cold_start,
            processing_percentage=processing_percentage,
            processing_assigned_value=processing_assigned_value,
        )
    )

    # explicitly remove file reference to free memory for the lambda
    del file_bytes

    # Textract completed inline -- finalize the record with extraction results
    if textract_result is not None:
        finalize_textract_result(ddb_key, textract_result, user_provided_document_category)
        return
