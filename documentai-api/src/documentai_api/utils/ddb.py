import json
import random
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import documentai_api.utils.documents as document_utils
from documentai_api.config.constants import (
    BatchStatus,
    ConfigDefaults,
    DocumentCategory,
    FileValidation,
    ProcessStatus,
)
from documentai_api.config.env import EnvVars, get_aws_config, get_required_env
from documentai_api.logging import get_logger
from documentai_api.models.document_record import DocumentRecord
from documentai_api.schemas.document_batches import DocumentBatches
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.services import ddb as ddb_service
from documentai_api.services import s3 as s3_service
from documentai_api.services import sqs as sqs_service
from documentai_api.utils import s3 as s3_utils
from documentai_api.utils.bedrock import preclassify_document
from documentai_api.utils.dto import (
    ClassificationData,
    FieldMetrics,
    InternalApiResponse,
    ProcessingTimes,
)
from documentai_api.utils.response_builder import build_v1_api_response, get_internal_api_response
from documentai_api.utils.response_codes import ResponseCodes
from documentai_api.utils.ssm import get_bda_percentage

logger = get_logger(__name__)


# =============================================================================
# Batch Upload Functions
# =============================================================================


def create_batch(
    batch_id: str,
    total_files: int,
    category: DocumentCategory | None,
    status: BatchStatus = BatchStatus.UPLOADING,
    tenant_id: str | None = None,
    api_key_name: str | None = None,
) -> str:
    """Create batch record in DynamoDB. Returns the createdAt timestamp."""
    table_name = get_required_env(EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME)

    created_at = datetime.now(UTC).isoformat()
    item: dict[str, Any] = {
        DocumentBatches.BATCH_ID: batch_id,
        DocumentBatches.BATCH_STATUS: status.value,
        DocumentBatches.TOTAL_FILES: total_files,
        DocumentBatches.CREATED_AT: created_at,
        # TTL 30 days from creation - batch records are short-lived tracking artifacts.
        DocumentBatches.TIME_TO_LIVE: int(datetime.now(UTC).timestamp() + (30 * 24 * 60 * 60)),
    }

    if category:
        item[DocumentBatches.CATEGORY] = (
            category.value if isinstance(category, DocumentCategory) else category
        )
    if tenant_id is not None:
        item[DocumentBatches.TENANT_ID] = tenant_id
    if api_key_name is not None:
        item[DocumentBatches.API_KEY_NAME] = api_key_name

    try:
        ddb_service.put_item(
            table_name,
            item,
            condition_expression="attribute_not_exists(batchId)",
        )
    except Exception as e:
        if "ConditionalCheckFailedException" in type(e).__name__ or (
            hasattr(e, "response")
            and e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"
        ):
            from fastapi import HTTPException

            raise HTTPException(status_code=409, detail="Batch ID already exists") from None
        raise
    return created_at


def update_batch_status(
    batch_id: str,
    status: BatchStatus,
    error_message: str | None = None,
    condition_expression: str | None = None,
    condition_values: dict[str, Any] | None = None,
) -> None:
    """Update batch status (and optionally errorMessage)."""
    table_name = get_required_env(EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME)
    key = {DocumentBatches.BATCH_ID: batch_id}

    update_expr = f"SET {DocumentBatches.BATCH_STATUS} = :batchStatus, {DocumentBatches.UPDATED_AT} = :updatedAt"
    expr_values: dict[str, Any] = {
        ":batchStatus": status.value,
        ":updatedAt": datetime.now(UTC).isoformat(),
    }

    if error_message:
        update_expr += f", {DocumentBatches.ERROR_MESSAGE} = :errorMessage"
        expr_values[":errorMessage"] = error_message

    if condition_values:
        expr_values.update(condition_values)

    kwargs: dict[str, Any] = {
        "Key": key,
        "UpdateExpression": update_expr,
        "ExpressionAttributeValues": expr_values,
    }
    if condition_expression:
        kwargs["ConditionExpression"] = condition_expression

    from documentai_api.utils.aws_client_factory import AWSClientFactory

    ddb_table = AWSClientFactory.get_ddb_table(table_name)
    ddb_table.update_item(**kwargs)


def get_batch(batch_id: str) -> dict[str, Any] | None:
    """Get batch record by batch ID."""
    table_name = get_required_env(EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME)
    key = {DocumentBatches.BATCH_ID: batch_id}
    return ddb_service.get_item(table_name, key)


def query_jobs_by_batch_id(batch_id: str) -> list[dict[str, Any]]:
    """Query the document-metadata table for all jobs in a batch via the batch-id GSI."""
    table_name = get_required_env(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME)
    index_name = get_required_env(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_BATCH_ID_INDEX_NAME)
    return ddb_service.query_by_key(table_name, index_name, DocumentMetadata.BATCH_ID, batch_id)


# =============================================================================


def extract_region_from_bda_arn(bda_invocation_arn: str) -> str | None:
    """Extract AWS region from BDA invocation ARN."""
    try:
        # arn format: arn:aws:bedrock-data-automation:us-east-1:account:job/job-id
        parts = bda_invocation_arn.split(":")
        if len(parts) >= 4:
            return parts[3]  # Region is the 4th part
        return None
    except Exception as e:
        logger.error(f"Failed to extract region from ARN {bda_invocation_arn}: {e}")
        return None


def get_elapsed_time_seconds(start_time: datetime, end_time: datetime) -> Decimal:
    """Calculate elapsed time in seconds with 2 decimal precision."""
    return Decimal(str(round((end_time - start_time).total_seconds(), 2)))


def calculate_bda_processing_times(object_key: str, completion_time: datetime) -> ProcessingTimes:
    """Calculate BDA processing timing metrics.

    Returns dict with timing data to add to DDB update, or empty dict if calculation fails.
    """
    ddb_record = get_ddb_record(object_key)
    if ddb_record is None:
        return ProcessingTimes()

    created_at_str = ddb_record.get(DocumentMetadata.CREATED_AT)
    bda_started_at_str = ddb_record.get(DocumentMetadata.BDA_STARTED_AT)

    timing_data = ProcessingTimes()

    if created_at_str:
        created_at = datetime.fromisoformat(created_at_str)
        total_processing_time_seconds = get_elapsed_time_seconds(created_at, completion_time)
        timing_data.total_processing_time_seconds = total_processing_time_seconds
        logger.info(f"Total processing time: {total_processing_time_seconds:.2f} seconds")

    if bda_started_at_str:
        bda_started_at = datetime.fromisoformat(bda_started_at_str)
        bda_processing_time_seconds = get_elapsed_time_seconds(bda_started_at, completion_time)
        timing_data.bda_processing_time_seconds = bda_processing_time_seconds
        logger.info(f"BDA processing time: {bda_processing_time_seconds:.2f} seconds")

    return timing_data


def _calculate_wait_time(object_key: str) -> Decimal | None:
    """Calculate BDA wait time from file creation to BDA start."""
    ddb_record = get_ddb_record(object_key)
    if ddb_record is None:
        return None

    created_at_str = ddb_record.get(DocumentMetadata.CREATED_AT)

    if not created_at_str:
        return None

    created_at = datetime.fromisoformat(created_at_str)
    return get_elapsed_time_seconds(created_at, datetime.now(UTC))


def _calculate_field_metrics(data: ClassificationData) -> FieldMetrics:
    """Calculate field count metrics from classification data."""
    if not data.field_confidence_scores:
        return FieldMetrics(0, 0, None)

    field_count = len(data.field_confidence_scores)
    empty_fields = set(data.field_empty_list or [])

    # Count non-empty fields and sum their confidence scores
    non_empty_count = 0
    confidence_sum = 0

    for field_data in data.field_confidence_scores:
        field_name = next(iter(field_data.keys()))
        confidence = next(iter(field_data.values()))

        if field_name not in empty_fields:
            non_empty_count += 1
            confidence_sum += confidence

    avg_confidence = confidence_sum / non_empty_count if non_empty_count > 0 else None

    return FieldMetrics(field_count, non_empty_count, avg_confidence)


def _build_completion_timing(
    object_key: str, bda_output_s3_uri: str | None
) -> tuple[list[str], dict[str, Any]]:
    """Build completion timing updates."""
    updates: list[str] = []
    values: dict[str, Any] = {}

    ddb_record = get_ddb_record(object_key)
    # record doesn't exist yet (eg. pre-ddb insert failure), skip bda timing
    if ddb_record is None:
        return updates, values

    if ddb_record.get(DocumentMetadata.BDA_STARTED_AT):
        completed_time = datetime.now(UTC)

        # use S3 LastModified timestamp if available
        if bda_output_s3_uri:
            try:
                bucket, key = s3_utils.parse_s3_uri(bda_output_s3_uri)
                completed_time = s3_service.get_last_modified_at(bucket, key)
                logger.info(f"Using S3 LastModified for bdaCompletedAt: {completed_time}")
            except Exception as e:
                logger.warning(
                    f"Failed to get S3 timestamp for bdaCompletedAt, using current time: {e}"
                )

        updates.append(f"{DocumentMetadata.BDA_COMPLETED_AT} = :bdaCompletedAt")
        values[":bdaCompletedAt"] = completed_time.isoformat()

        updates.append(f"{DocumentMetadata.PROCESSED_DATE} = :processedDate")
        values[":processedDate"] = completed_time.strftime("%Y-%m-%d")

        timing_data = calculate_bda_processing_times(object_key, completed_time)

        if timing_data.total_processing_time_seconds:
            updates.append(
                f"{DocumentMetadata.TOTAL_PROCESSING_TIME_SECONDS} = :totalProcessingTime"
            )
            values[":totalProcessingTime"] = timing_data.total_processing_time_seconds

        if timing_data.bda_processing_time_seconds:
            updates.append(f"{DocumentMetadata.BDA_PROCESSING_TIME_SECONDS} = :bdaProcessingTime")
            values[":bdaProcessingTime"] = timing_data.bda_processing_time_seconds

    return updates, values


def _build_timing_updates(
    object_key: str, status: str, bda_output_s3_uri: str | None
) -> tuple[str, dict[str, Any]]:
    """Handle all timing-related updates for different statuses."""
    status = status.value if isinstance(status, ProcessStatus) else status

    updates = []
    values: dict[str, Any] = {}

    if status == ProcessStatus.STARTED:
        updates.append(f"{DocumentMetadata.BDA_STARTED_AT} = :bdaStartedAt")
        values[":bdaStartedAt"] = datetime.now(UTC).isoformat()

        try:
            wait_time = _calculate_wait_time(object_key)
            updates.append(f"{DocumentMetadata.BDA_WAIT_TIME_SECONDS} = :bdaWaitTimeSeconds")
            values[":bdaWaitTimeSeconds"] = wait_time
        except Exception as e:
            logger.error(f"Failed to calculate bda wait time for {object_key}: {e}")

    elif ProcessStatus.is_completed(status):
        completion_updates, completion_values = _build_completion_timing(
            object_key, bda_output_s3_uri
        )
        updates.extend(completion_updates)
        values.update(completion_values)

    return ", ".join(updates), values


def _build_update_expression(
    status: str,
    data: ClassificationData | None,
    internal_api_response: InternalApiResponse | None,
    v1_api_response: str | None,
    bda_invocation_arn: str | None = None,
    bda_project_arn_used: str | None = None,
    error_message: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build DynamoDB update expression and values."""
    updates = [
        f"{DocumentMetadata.PROCESS_STATUS} = :processStatus",
        f"{DocumentMetadata.UPDATED_AT} = :updatedAt",
    ]

    values: dict[str, Any] = {":processStatus": status, ":updatedAt": datetime.now(UTC).isoformat()}

    if data:
        metrics = _calculate_field_metrics(data)

        field_mappings = {
            DocumentMetadata.BDA_OUTPUT_S3_URI: data.bda_output_s3_uri,
            DocumentMetadata.BDA_MATCHED_BLUEPRINT_NAME: data.matched_blueprint_name,
            DocumentMetadata.BDA_MATCHED_BLUEPRINT_CONFIDENCE: data.matched_blueprint_confidence,
            DocumentMetadata.FIELD_CONFIDENCE_SCORES: data.field_confidence_scores,
            DocumentMetadata.ADDITIONAL_INFO: data.additional_info,
            DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS: data.matched_document_class,
            DocumentMetadata.BDA_MATCHED_BLUEPRINT_FIELD_EMPTY_LIST: data.field_empty_list,
            DocumentMetadata.BDA_MATCHED_BLUEPRINT_FIELD_BELOW_THRESHOLD_LIST: data.field_below_threshold_list,
            DocumentMetadata.BDA_MATCHED_BLUEPRINT_FIELD_COUNT: metrics.field_count,
            DocumentMetadata.BDA_MATCHED_BLUEPRINT_FIELD_COUNT_NOT_EMPTY: metrics.field_count_not_empty,
            DocumentMetadata.BDA_MATCHED_BLUEPRINT_FIELD_NOT_EMPTY_AVG_CONFIDENCE: metrics.field_not_empty_avg_confidence,
        }

        for ddb_field, value in field_mappings.items():
            if value is not None:
                param_key = f":{ddb_field.lower().replace('_', '')}"
                updates.append(f"{ddb_field} = {param_key}")

                if isinstance(value, (list, dict)):
                    values[param_key] = json.dumps(value)
                elif isinstance(value, float):
                    values[param_key] = Decimal(str(value))
                else:
                    values[param_key] = value

    if internal_api_response:
        updates.append(f"{DocumentMetadata.RESPONSE_JSON} = :responseJson")
        values[":responseJson"] = json.dumps(internal_api_response.__dict__)

        updates.append(f"{DocumentMetadata.RESPONSE_CODE} = :responseCode")
        values[":responseCode"] = internal_api_response.response_code

    if v1_api_response:
        updates.append(f"{DocumentMetadata.V1_API_RESPONSE_JSON} = :v1ResponseJson")
        values[":v1ResponseJson"] = json.dumps(v1_api_response)

    if bda_invocation_arn:
        updates.append(f"{DocumentMetadata.BDA_INVOCATION_ARN} = :bdaInvocationArn")
        values[":bdaInvocationArn"] = bda_invocation_arn

        bda_region = (
            extract_region_from_bda_arn(bda_invocation_arn)
            or ConfigDefaults.BDA_REGION_NOT_AVAILABLE
        )

        bda_invocation_id = bda_invocation_arn.split("/")[
            -1
        ]  # invocation ID is last segment of ARN
        updates.append(f"{DocumentMetadata.BDA_INVOCATION_ID} = :bdaInvocationId")
        values[":bdaInvocationId"] = bda_invocation_id

        updates.append(f"{DocumentMetadata.BDA_REGION_USED} = :bdaRegion")
        values[":bdaRegion"] = bda_region

    if bda_project_arn_used:
        updates.append(f"{DocumentMetadata.BDA_PROJECT_ARN_USED} = :bdaProjectArn")
        values[":bdaProjectArn"] = bda_project_arn_used

    if error_message:
        updates.append(f"{DocumentMetadata.ERROR_MESSAGE} = :errorMessage")
        values[":errorMessage"] = error_message

    return "SET " + ", ".join(updates), values


def _execute_ddb_update(
    object_key: str, update_expression: str, expression_values: dict[str, Any]
) -> None:
    """Execute the DynamoDB update."""
    table_name = get_required_env(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME)
    key = {"fileName": object_key}

    ddb_service.update_item(table_name, key, update_expression, expression_values)


def _send_record_to_metrics_queue(object_key: str) -> None:
    """Write object key to SQS queue."""
    try:
        queue_url = get_aws_config().ddb_metrics_input_queue_url

        if not queue_url:
            msg = "DDB_METRICS_INPUT_QUEUE_URL environment variable not set, skipping metrics"
            print(msg)
            logger.warning(msg)
            # do not raise an exception here. metrics are optional and shouldn't
            # prevent process from completing successfully
            return

        table_name = get_required_env(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME)
        key = {"fileName": object_key}
        ddb_record = ddb_service.get_item(table_name, key)

        if not ddb_record:
            logger.warning(f"DDB record not found for {object_key}, skipping metrics")
            # do not raise an exception here. metrics are optional and shouldn't
            # prevent process from completing successfully
            return

        sqs_service.send_message(queue_url, json.dumps(ddb_record, default=str))
        print(f"Successfully sent {object_key} to SQS queue")

    except Exception as e:
        logger.error(f"Failed to send {object_key} to SQS queue: {e}")


def get_user_provided_document_category(object_key: str) -> DocumentCategory | None:
    """Get the user-provided DocumentCategory for a file, or None if unset/invalid.

    The DDB record may hold values that don't map to a DocumentCategory enum
    member (e.g. the "Not specified" default when the API caller doesn't pick a
    category, or the legacy "unknown" fallback from insert_initial_ddb_record).
    Returns None in those cases rather than raising - the caller treats None as
    "no category provided" and downstream paths handle it.
    """
    ddb_record = get_ddb_record(object_key)
    if ddb_record is None:
        return None

    user_provided_document_category = ddb_record.get(
        DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY
    )

    if not user_provided_document_category:
        logger.warning(f"User specified document type not found for file: {object_key}")
        return None

    try:
        return DocumentCategory(user_provided_document_category)
    except ValueError:
        logger.info(
            f"User-provided document category '{user_provided_document_category}' "
            f"is not a recognized DocumentCategory for {object_key}; treating as None"
        )
        return None


def get_ddb_record(object_key: str) -> dict[str, Any] | None:
    """Get DDB record by file name. Raises ValueError if not found."""
    table_name = get_required_env(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME)
    key = {"fileName": object_key}
    item = ddb_service.get_item(table_name, key)

    if not item:
        return None

    return item


def get_ddb_by_job_id(job_id: str) -> dict[str, Any] | None:
    """Get document metadata record by job ID."""
    table_name = get_required_env(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME)
    index_name = get_required_env(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_JOB_ID_INDEX_NAME)
    items = ddb_service.query_by_key(table_name, index_name, "jobId", job_id)
    return items[0] if items else None


def update_ddb(
    object_key: str,
    status: str,
    internal_api_response: InternalApiResponse | None = None,
    data: ClassificationData | None = None,
    bda_invocation_arn: str | None = None,
    bda_project_arn_used: str | None = None,
    error_message: str | None = None,
) -> None:
    """Update DynamoDB processing status for a file."""
    try:
        # build base update expression (without v1_response)
        update_expr, expr_values = _build_update_expression(
            status=status,
            data=data,
            internal_api_response=internal_api_response,
            v1_api_response=None,  # built after ddb update
            bda_invocation_arn=bda_invocation_arn,
            bda_project_arn_used=bda_project_arn_used,
            error_message=error_message,
        )

        # add timing updates
        timing_updates, timing_values = _build_timing_updates(
            object_key, status, bda_output_s3_uri=data.bda_output_s3_uri if data else None
        )
        if timing_updates:
            update_expr += f", {timing_updates}"
            expr_values.update(timing_values)

        _execute_ddb_update(object_key, update_expr, expr_values)

        # build v1 response after ddb has been updated
        v1_response = build_v1_api_response(object_key, status, data, error_message=error_message)

        # update ddb again with v1_response
        update_expr = f"SET {DocumentMetadata.V1_API_RESPONSE_JSON} = :v1ResponseJson"
        expr_values = {":v1ResponseJson": json.dumps(v1_response)}
        _execute_ddb_update(object_key, update_expr, expr_values)

        if ProcessStatus.is_completed(status):
            _send_record_to_metrics_queue(object_key)

    except Exception as e:
        logger.error(f"Failed to update DDB status: {e}")
        raise


def upsert_ddb(
    object_key: str,
    original_file_name: str,
    user_provided_document_category: str | None = None,
    process_status: str | None = None,
    internal_api_response: InternalApiResponse | None = None,
    file_size_bytes: int | None = None,
    content_type: str | None = None,
    pages_detected: int | None = None,
    job_id: str | None = None,
    trace_id: str | None = None,
    batch_id: str | None = None,
    is_password_protected: bool | None = False,
    is_document_blurry: bool | None = False,
    pre_classification_document_type: str | None = None,
    pre_classification_confidence: float | None = None,
    external_document_id: str | None = None,
    external_system_id: str | None = None,
    ai_consent_flag: bool | None = None,
    upload_method: str | None = None,
    tenant_id: str | None = None,
    api_key_name: str | None = None,
) -> None:
    """Upsert a document-metadata DDB row by file name.

    Creates the row if missing, updates it in place if present. `createdAt` is
    set only on initial create (preserved on subsequent calls via if_not_exists);
    `updatedAt` is always refreshed.
    """
    try:
        now = datetime.now(UTC).isoformat()

        expr_fields: list[str] = [
            f"{DocumentMetadata.ORIGINAL_FILE_NAME} = :originalFileName",
            f"{DocumentMetadata.PROCESS_STATUS} = :processStatus",
            f"{DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY} = :category",
            (f"{DocumentMetadata.CREATED_AT} = if_not_exists({DocumentMetadata.CREATED_AT}, :now)"),
            f"{DocumentMetadata.UPDATED_AT} = :now",
        ]
        expr_values: dict[str, Any] = {
            ":originalFileName": original_file_name,
            ":processStatus": process_status,
            ":category": (
                user_provided_document_category or ConfigDefaults.USER_DOCUMENT_TYPE_NOT_PROVIDED
            ),
            ":now": now,
        }

        if file_size_bytes is not None:
            expr_fields.append(f"{DocumentMetadata.FILE_SIZE_BYTES} = :fileSize")
            expr_values[":fileSize"] = file_size_bytes
        if content_type:
            expr_fields.append(f"{DocumentMetadata.CONTENT_TYPE} = :contentType")
            expr_values[":contentType"] = content_type
        if pages_detected is not None:
            expr_fields.append(f"{DocumentMetadata.PAGES_DETECTED} = :pages")
            expr_values[":pages"] = pages_detected
        if internal_api_response:
            expr_fields.append(f"{DocumentMetadata.RESPONSE_JSON} = :respJson")
            expr_values[":respJson"] = json.dumps(internal_api_response.__dict__)
        if job_id:
            expr_fields.append(f"{DocumentMetadata.JOB_ID} = :jobId")
            expr_values[":jobId"] = job_id
        if trace_id:
            expr_fields.append(f"{DocumentMetadata.TRACE_ID} = :traceId")
            expr_values[":traceId"] = trace_id
        if batch_id:
            expr_fields.append(f"{DocumentMetadata.BATCH_ID} = :batchId")
            expr_values[":batchId"] = batch_id
        if is_password_protected is not None:
            expr_fields.append(f"{DocumentMetadata.IS_PASSWORD_PROTECTED} = :pwProt")
            expr_values[":pwProt"] = bool(is_password_protected)
        if is_document_blurry is not None:
            expr_fields.append(f"{DocumentMetadata.IS_DOCUMENT_BLURRY} = :blurry")
            expr_values[":blurry"] = bool(is_document_blurry)
        if pre_classification_document_type is not None:
            expr_fields.append(f"{DocumentMetadata.PRECLASSIFICATION_CATEGORY} = :pcdt")
            expr_values[":pcdt"] = pre_classification_document_type
        if pre_classification_confidence is not None:
            expr_fields.append(f"{DocumentMetadata.PRECLASSIFICATION_CONFIDENCE} = :pcc")
            expr_values[":pcc"] = Decimal(str(pre_classification_confidence))
        if external_document_id is not None:
            expr_fields.append(f"{DocumentMetadata.EXTERNAL_DOCUMENT_ID} = :extDocId")
            expr_values[":extDocId"] = external_document_id
        if external_system_id is not None:
            expr_fields.append(f"{DocumentMetadata.EXTERNAL_SYSTEM_ID} = :extSysId")
            expr_values[":extSysId"] = external_system_id
        if ai_consent_flag is not None:
            expr_fields.append(f"{DocumentMetadata.AI_CONSENT_FLAG} = :aiConsent")
            expr_values[":aiConsent"] = ai_consent_flag
        if upload_method is not None:
            expr_fields.append(f"{DocumentMetadata.UPLOAD_METHOD} = :uploadMethod")
            expr_values[":uploadMethod"] = upload_method
        if tenant_id is not None:
            expr_fields.append(f"{DocumentMetadata.TENANT_ID} = :tenantId")
            expr_values[":tenantId"] = tenant_id
        if api_key_name is not None:
            expr_fields.append(f"{DocumentMetadata.API_KEY_NAME} = :clientName")
            expr_values[":clientName"] = api_key_name

        update_expr = "SET " + ", ".join(expr_fields)
        _execute_ddb_update(object_key, update_expr, expr_values)
    except Exception as e:
        logger.error(f"Failed to upsert DDB record for {object_key}: {e}")
        raise


def insert_minimal_ddb_record(record: DocumentRecord) -> None:
    """Create initial tracking record from the API upload path.

    Uses upsert_ddb so doc-processor's later upsert_initial_ddb_record can update
    in place (preserving createdAt, job_id, trace_id) rather than overwriting.
    """
    upsert_ddb(
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
        tenant_id=record.tenant_id,
        api_key_name=record.api_key_name,
    )

    logger.info(
        f"Inserted initial DDB record for {record.ddb_key} with status {record.process_status}"
    )


def upsert_initial_ddb_record(
    source_bucket_name: str,
    source_object_key: str,
    ddb_key: str,
    original_file_name: str,
    user_provided_document_category: str | None = None,
    job_id: str | None = None,
    trace_id: str | None = None,
    batch_id: str | None = None,
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

    bda_percentage = get_bda_percentage(user_provided_document_category)
    response_code = ResponseCodes.SUCCESS
    internal_api_response: InternalApiResponse | None = None
    process_status = ProcessStatus.PENDING_IMAGE_OPTIMIZATION
    pages_detected = document_utils.get_page_count(file_bytes)
    is_password_protected = document_utils.is_password_protected(file_bytes)
    is_document_blurry = False
    pre_classification_document_type = None
    pre_classification_confidence = None

    if is_password_protected:
        process_status = ProcessStatus.PASSWORD_PROTECTED
        response_code = ResponseCodes.MISSING_FIELDS

    elif bda_percentage == 0.0 or not bda_percentage:
        process_status = ProcessStatus.NOT_IMPLEMENTED
        response_code = ResponseCodes.DOCUMENT_TYPE_NOT_IMPLEMENTED

    elif bda_percentage == 1.0 or random.random() <= bda_percentage:
        result = preclassify_document(file_bytes, content_type)

        pre_classification_document_type = result.document_type
        pre_classification_confidence = result.confidence

        if not result.is_document:
            # clearly not a document (cat, random photo, etc.)
            process_status = ProcessStatus.NO_DOCUMENT_DETECTED
            response_code = ResponseCodes.NO_DOCUMENT_DETECTED

        elif result.is_blurry:
            process_status = ProcessStatus.BLURRY_DOCUMENT_DETECTED
            response_code = ResponseCodes.BLURRY_DOCUMENT_DETECTED
            is_document_blurry = True

        elif result.document_count > 1:
            process_status = ProcessStatus.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE
            response_code = ResponseCodes.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE

        else:
            # document passed pre-classification, proceed to extraction
            if content_type in FileValidation.GRAYSCALE_CONVERTIBLE:
                process_status = ProcessStatus.PENDING_IMAGE_OPTIMIZATION
            else:
                process_status = ProcessStatus.NOT_STARTED

    else:
        process_status = ProcessStatus.NOT_SAMPLED
        response_code = ResponseCodes.SUCCESS

    # initial status does not qualify for bda processing
    # create the json response signaling the process is complete
    if not ProcessStatus.is_pending_extraction(process_status):
        internal_api_response = get_internal_api_response(
            object_key=ddb_key,
            response_code=response_code,
            matched_document_class=None,
            user_provided_document_category=user_provided_document_category,
        )

    upsert_ddb(
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
        is_password_protected=is_password_protected,
        pre_classification_document_type=pre_classification_document_type,
        pre_classification_confidence=pre_classification_confidence,
    )

    # explicity remove file reference to free memory for the lambda
    del file_bytes

    # document did not qualify for bda, processing complete
    # create the v1 api response here and save to ddb
    # write to sqs as the file was received, but no data extracted
    if not ProcessStatus.is_pending_extraction(process_status):
        v1_response = build_v1_api_response(ddb_key, process_status)
        update_expr = f"SET {DocumentMetadata.V1_API_RESPONSE_JSON} = :v1ResponseJson"
        expr_values = {":v1ResponseJson": json.dumps(v1_response)}
        _execute_ddb_update(ddb_key, update_expr, expr_values)
        _send_record_to_metrics_queue(ddb_key)


def set_bda_processing_status_started(
    object_key: str, bda_invocation_arn: str, bda_project_arn_used: str | None = None
) -> None:
    """Mark file processing as started with BDA job ARN."""
    update_ddb(
        object_key=object_key,
        status=ProcessStatus.STARTED,
        internal_api_response=None,
        bda_invocation_arn=bda_invocation_arn,
        bda_project_arn_used=bda_project_arn_used,
    )


def set_bda_processing_status_not_started(object_key: str) -> None:
    update_ddb(
        object_key=object_key,
        status=ProcessStatus.NOT_STARTED,
        internal_api_response=None,
    )


def classify_as_success(
    object_key: str, response_code: str, data: ClassificationData
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
    )

    # convert dataclass to dict for JSON serialization
    return internal_api_response.__dict__


def classify_as_failed(
    object_key: str, error_message: str, data: ClassificationData
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


def classify_as_no_document_detected(object_key: str, data: ClassificationData) -> dict[str, Any]:
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


def classify_as_no_custom_blueprint_matched(
    object_key: str, data: ClassificationData
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
