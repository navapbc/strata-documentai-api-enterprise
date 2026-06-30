import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from documentai_api.config.constants import (
    ConfigDefaults,
    DeletionType,
    DocumentCategory,
    ExtractMethod,
    ProcessStatus,
)
from documentai_api.config.env import EnvVars, get_aws_config, get_required_env
from documentai_api.logging import get_logger
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.services import ddb as ddb_service
from documentai_api.services import s3 as s3_service
from documentai_api.services import sqs as sqs_service
from documentai_api.utils import s3 as s3_utils
from documentai_api.utils.bda import extract_region_from_bda_arn
from documentai_api.utils.dto import (
    ClassificationData,
    InternalApiResponse,
    ProcessingTimes,
    UpsertDdbData,
)
from documentai_api.utils.extraction_timing import (
    calculate_field_metrics as _calculate_field_metrics,
)
from documentai_api.utils.extraction_timing import (
    calculate_processing_times,
    calculate_wait_time,
)
from documentai_api.utils.response_builder import build_v1_api_response
from documentai_api.utils.ttl import ttl_epoch_in_days

logger = get_logger(__name__)


def _calculate_bda_processing_times(object_key: str, completion_time: datetime) -> ProcessingTimes:
    """Calculate BDA processing timing metrics.

    Delegates to extraction.calculate_processing_times with the DDB record.
    """
    ddb_record = get_ddb_record(object_key)
    if ddb_record is None:
        return ProcessingTimes()
    return calculate_processing_times(ddb_record, completion_time)


def _calculate_wait_time(object_key: str) -> Decimal | None:
    """Calculate wait time from file creation to extraction start."""
    ddb_record = get_ddb_record(object_key)
    if ddb_record is None:
        return None
    return calculate_wait_time(ddb_record)


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

    if ddb_record.get(DocumentMetadata.BDA_STARTED_AT) or ddb_record.get(
        DocumentMetadata.EXTRACTION_STARTED_AT
    ):
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
        updates.append(f"{DocumentMetadata.EXTRACTION_COMPLETED_AT} = :extractionCompletedAt")
        values[":extractionCompletedAt"] = completed_time.isoformat()

        updates.append(f"{DocumentMetadata.PROCESSED_DATE} = :processedDate")
        values[":processedDate"] = completed_time.strftime("%Y-%m-%d")

        timing_data = _calculate_bda_processing_times(object_key, completed_time)

        if timing_data.total_processing_time_seconds:
            updates.append(
                f"{DocumentMetadata.TOTAL_PROCESSING_TIME_SECONDS} = :totalProcessingTime"
            )
            values[":totalProcessingTime"] = timing_data.total_processing_time_seconds

        if timing_data.bda_processing_time_seconds:
            updates.append(f"{DocumentMetadata.BDA_PROCESSING_TIME_SECONDS} = :bdaProcessingTime")
            values[":bdaProcessingTime"] = timing_data.bda_processing_time_seconds
            updates.append(
                f"{DocumentMetadata.EXTRACTION_PROCESSING_TIME_SECONDS} = :extractionProcessingTime"
            )
            values[":extractionProcessingTime"] = timing_data.bda_processing_time_seconds

    return updates, values


def _build_timing_updates(
    object_key: str, status: str, bda_output_s3_uri: str | None
) -> tuple[str, dict[str, Any]]:
    """Handle all timing-related updates for different statuses."""
    status = status.value if isinstance(status, ProcessStatus) else status

    updates = []
    values: dict[str, Any] = {}

    if status == ProcessStatus.STARTED:
        # TODO: Drop bda* writes once all readers (UI, response_builder) are migrated
        # to extraction* fields. The bda* fields are the legacy bridge for old records.
        now_iso = datetime.now(UTC).isoformat()
        updates.append(f"{DocumentMetadata.BDA_STARTED_AT} = :bdaStartedAt")
        values[":bdaStartedAt"] = now_iso
        updates.append(f"{DocumentMetadata.EXTRACTION_STARTED_AT} = :extractionStartedAt")
        values[":extractionStartedAt"] = now_iso

        try:
            wait_time = _calculate_wait_time(object_key)
            updates.append(f"{DocumentMetadata.BDA_WAIT_TIME_SECONDS} = :bdaWaitTimeSeconds")
            values[":bdaWaitTimeSeconds"] = wait_time
            updates.append(
                f"{DocumentMetadata.EXTRACTION_WAIT_TIME_SECONDS} = :extractionWaitTimeSeconds"
            )
            values[":extractionWaitTimeSeconds"] = wait_time
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
    below_extraction_confidence_floor: bool = False,
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

        updates.append(f"{DocumentMetadata.EXTRACT_METHOD} = :extractMethod")
        values[":extractMethod"] = ExtractMethod.BDA.value

    if bda_project_arn_used:
        updates.append(f"{DocumentMetadata.BDA_PROJECT_ARN_USED} = :bdaProjectArn")
        values[":bdaProjectArn"] = bda_project_arn_used

    if error_message:
        updates.append(f"{DocumentMetadata.ERROR_MESSAGE} = :errorMessage")
        values[":errorMessage"] = error_message

    if below_extraction_confidence_floor:
        updates.append(f"{DocumentMetadata.BELOW_EXTRACTION_CONFIDENCE_FLOOR} = :belowFloor")
        values[":belowFloor"] = True

    return "SET " + ", ".join(updates), values


def _execute_ddb_update(
    object_key: str,
    update_expression: str,
    expression_values: dict[str, Any],
    expression_names: dict[str, str] | None = None,
) -> None:
    """Execute the DynamoDB update."""
    table_name = get_required_env(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME)
    key = {"fileName": object_key}

    ddb_service.update_item(table_name, key, update_expression, expression_values, expression_names)


def _send_record_to_metrics_queue(object_key: str) -> None:
    """Write object key to SQS queue."""
    try:
        queue_url = get_aws_config().ddb_metrics_input_queue_url

        if not queue_url:
            msg = "DDB_METRICS_INPUT_QUEUE_URL environment variable not set, skipping metrics"
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
        logger.info(f"Successfully sent {object_key} to SQS queue")

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
    below_extraction_confidence_floor: bool = False,
    pages_sent_to_bda: int | None = None,
    result_processor_started_at: str | None = None,
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
            below_extraction_confidence_floor=below_extraction_confidence_floor,
        )

        if pages_sent_to_bda is not None:
            update_expr += f", {DocumentMetadata.PAGES_SENT_TO_BDA} = :pagesSentToBda"
            expr_values[":pagesSentToBda"] = pages_sent_to_bda

        if result_processor_started_at is not None:
            update_expr += f", {DocumentMetadata.RESULT_PROCESSOR_STARTED_AT} = :rpStartedAt"
            expr_values[":rpStartedAt"] = result_processor_started_at

        # add timing updates
        timing_updates, timing_values = _build_timing_updates(
            object_key, status, bda_output_s3_uri=data.bda_output_s3_uri if data else None
        )
        if timing_updates:
            update_expr += f", {timing_updates}"
            expr_values.update(timing_values)

        _execute_ddb_update(object_key, update_expr, expr_values)

        # finalize: build v1 response, sync responseCode
        _finalize_v1_response(object_key, status, data, error_message)

        # metrics: enqueue for any terminal (classified) status
        if ProcessStatus.is_classified(status):
            _send_record_to_metrics_queue(object_key)

    except Exception as e:
        logger.error(f"Failed to update DDB status: {e}")
        raise


def _apply_ddb_fields(
    model: BaseModel,
    set_fields: dict[str, Any],
    expr_fields: list[str],
    expr_values: dict[str, Any],
) -> None:
    """Append DDB expression clauses for fields with ddb metadata that were explicitly set."""
    for field_name, field_info in type(model).model_fields.items():
        if field_name not in set_fields:
            continue
        extra = field_info.json_schema_extra
        if not isinstance(extra, dict) or "ddb_attr" not in extra:
            continue
        value = set_fields[field_name]
        # skip explicit None: leave the attribute absent rather than writing a
        # DynamoDB NULL (sparse items are idiomatic; absent == "not provided")
        if value is None:
            continue
        if isinstance(value, float):
            value = Decimal(str(value))
        ddb_attr = str(extra["ddb_attr"])
        ddb_param = str(extra["ddb_param"])
        expr_fields.append(f"{ddb_attr} = {ddb_param}")
        expr_values[ddb_param] = value


def mark_document_deleted(object_key: str, deletion_type: DeletionType) -> None:
    """Mark a document-metadata record DELETED and record soft vs hard delete."""
    update_expr = (
        f"SET {DocumentMetadata.PROCESS_STATUS} = :status, "
        f"{DocumentMetadata.DELETION_TYPE} = :deletionType, "
        f"{DocumentMetadata.UPDATED_AT} = :updatedAt"
    )
    expr_values: dict[str, Any] = {
        ":status": ProcessStatus.DELETED.value,
        ":deletionType": deletion_type.value,
        ":updatedAt": datetime.now(UTC).isoformat(),
    }
    _execute_ddb_update(object_key, update_expr, expr_values)


def _finalize_v1_response(
    object_key: str,
    status: str,
    data: ClassificationData | None = None,
    error_message: str | None = None,
) -> None:
    """Build and persist the v1 API response and sync responseCode.

    This is the single authority for v1 response finalization - called by both
    update_ddb (extraction completion) and upsert_ddb (terminal pre-extraction statuses).
    Does NOT enqueue metrics - callers own that policy.
    """
    v1_response = build_v1_api_response(object_key, status, data, error_message=error_message)

    update_expr = f"SET {DocumentMetadata.V1_API_RESPONSE_JSON} = :v1ResponseJson"
    expr_values: dict[str, Any] = {":v1ResponseJson": json.dumps(v1_response)}
    if "responseCode" in v1_response:
        update_expr += f", {DocumentMetadata.RESPONSE_CODE} = :responseCode"
        expr_values[":responseCode"] = v1_response["responseCode"]
    _execute_ddb_update(object_key, update_expr, expr_values)


def upsert_ddb(data: UpsertDdbData) -> None:
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
            f"{DocumentMetadata.CREATED_AT} = if_not_exists({DocumentMetadata.CREATED_AT}, :now)",
            f"{DocumentMetadata.UPDATED_AT} = :now",
            f"{DocumentMetadata.IS_PASSWORD_PROTECTED} = :pwProt",
            f"{DocumentMetadata.IS_DOCUMENT_BLURRY} = :blurry",
            f"{DocumentMetadata.AI_CONSENT_FLAG} = "
            f"if_not_exists({DocumentMetadata.AI_CONSENT_FLAG}, :aiConsent)",
            "#ttl = if_not_exists(#ttl, :ttl)",
        ]
        expr_values: dict[str, Any] = {
            ":originalFileName": data.original_file_name,
            ":processStatus": data.process_status,
            ":category": (
                data.user_provided_document_category
                or ConfigDefaults.USER_DOCUMENT_TYPE_NOT_PROVIDED
            ),
            ":now": now,
            ":pwProt": bool(data.is_password_protected),
            ":blurry": bool(data.is_document_blurry),
            ":aiConsent": bool(data.ai_consent_flag),
            ":ttl": ttl_epoch_in_days(data.ttl_days or ConfigDefaults.DOCUMENT_METADATA_TTL_DAYS),
        }

        # internal_api_response and pre_classification are handled by dedicated
        # paths below, so exclude them here - dumping them is dead work and would
        # needlessly re-serialize the nested objects.
        set_fields = data.model_dump(
            exclude_unset=True, exclude={"internal_api_response", "pre_classification"}
        )

        # Dynamically add optional fields that were explicitly set and have ddb metadata
        _apply_ddb_fields(data, set_fields, expr_fields, expr_values)

        # internal_api_response needs JSON serialization
        if data.internal_api_response:
            expr_fields.append(f"{DocumentMetadata.RESPONSE_JSON} = :respJson")
            expr_values[":respJson"] = json.dumps(data.internal_api_response.__dict__)

        # Pre-classification sub-model
        if data.pre_classification:
            pc_fields = data.pre_classification.model_dump(exclude_unset=True)
            _apply_ddb_fields(data.pre_classification, pc_fields, expr_fields, expr_values)

        update_expr = "SET " + ", ".join(expr_fields)
        _execute_ddb_update(
            data.object_key,
            update_expr,
            expr_values,
            expression_names={"#ttl": DocumentMetadata.TIME_TO_LIVE},
        )

        # finalize terminal statuses: build v1 response, sync responseCode, enqueue metrics
        if data.process_status and ProcessStatus.is_classified(data.process_status):
            _finalize_v1_response(data.object_key, data.process_status)
            _send_record_to_metrics_queue(data.object_key)

    except Exception as e:
        logger.error(f"Failed to upsert DDB record for {data.object_key}: {e}")
        raise
