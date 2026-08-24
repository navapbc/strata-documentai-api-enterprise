import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from documentai_api.config.constants import (
    ConfigDefaults,
    DeletionType,
    ExtractMethod,
    ProcessStatus,
)
from documentai_api.config.env import EnvVars, get_aws_config, get_required_env
from documentai_api.dtos.classification import ClassificationData
from documentai_api.dtos.ddb import InitialDdbRecord, UpdateDdbRecord
from documentai_api.dtos.processing import InternalApiResponse, ProcessingTimes
from documentai_api.logging import get_logger
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.services import ddb as ddb_service
from documentai_api.services import s3 as s3_service
from documentai_api.services import sqs as sqs_service
from documentai_api.utils import s3 as s3_utils
from documentai_api.utils.bda import extract_region_from_bda_arn
from documentai_api.utils.dates import get_ttl_epoch_in_days
from documentai_api.utils.extraction_timing import (
    calculate_field_metrics as _calculate_field_metrics,
)
from documentai_api.utils.extraction_timing import (
    calculate_processing_times,
    calculate_wait_time,
)
from documentai_api.utils.response_builder import build_v1_api_response

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
                logger.info(f"Using S3 LastModified for extractionCompletedAt: {completed_time}")
            except Exception as e:
                logger.warning(
                    f"Failed to get S3 timestamp for extractionCompletedAt, using current time: {e}"
                )

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
        now_iso = datetime.now(UTC).isoformat()
        updates.append(f"{DocumentMetadata.EXTRACTION_STARTED_AT} = :extractionStartedAt")
        values[":extractionStartedAt"] = now_iso

        try:
            wait_time = _calculate_wait_time(object_key)
            updates.append(
                f"{DocumentMetadata.EXTRACTION_WAIT_TIME_SECONDS} = :extractionWaitTimeSeconds"
            )
            values[":extractionWaitTimeSeconds"] = wait_time
        except Exception as e:
            logger.error(f"Failed to calculate extraction wait time for {object_key}: {e}")

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
    used_category_specific_project: bool = False,
    error_message: str | None = None,
    below_extraction_confidence_floor: bool = False,
    extraction_rules_configured: bool | None = None,
    missing_required_field_list: list[str] | None = None,
    required_field_list: list[str] | None = None,
    applied_extraction_confidence_floor: float | None = None,
    used_default_confidence_floor: bool | None = None,
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
            DocumentMetadata.BDA_MATCHED_BLUEPRINT_FIELD_MISSING_GEOMETRY_LIST: data.field_missing_geometry_list,
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

    if used_category_specific_project:
        updates.append(
            f"{DocumentMetadata.USED_CATEGORY_SPECIFIC_PROJECT} = :usedCategorySpecificProject"
        )
        values[":usedCategorySpecificProject"] = True

    if error_message:
        updates.append(f"{DocumentMetadata.ERROR_MESSAGE} = :errorMessage")
        values[":errorMessage"] = error_message

    if below_extraction_confidence_floor:
        updates.append(f"{DocumentMetadata.BELOW_EXTRACTION_CONFIDENCE_FLOOR} = :belowFloor")
        values[":belowFloor"] = True

    if extraction_rules_configured is not None:
        updates.append(
            f"{DocumentMetadata.EXTRACTION_RULES_CONFIGURED} = :extractionRulesConfigured"
        )
        values[":extractionRulesConfigured"] = extraction_rules_configured

    if missing_required_field_list is not None:
        updates.append(
            f"{DocumentMetadata.MISSING_REQUIRED_FIELD_LIST} = :missingRequiredFieldList"
        )
        values[":missingRequiredFieldList"] = json.dumps(missing_required_field_list)

    if required_field_list is not None:
        updates.append(f"{DocumentMetadata.REQUIRED_FIELD_LIST} = :requiredFieldList")
        values[":requiredFieldList"] = json.dumps(required_field_list)

    if applied_extraction_confidence_floor is not None:
        updates.append(
            f"{DocumentMetadata.EXTRACTION_CONFIDENCE_THRESHOLD} = :extractionConfidenceThreshold"
        )
        values[":extractionConfidenceThreshold"] = Decimal(str(applied_extraction_confidence_floor))

    if used_default_confidence_floor is not None:
        updates.append(
            f"{DocumentMetadata.USED_DEFAULT_EXTRACTION_CONFIDENCE_THRESHOLD} = :usedDefaultExtractionConfidenceThreshold"
        )
        values[":usedDefaultExtractionConfidenceThreshold"] = used_default_confidence_floor

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

        # Inject traceparent into SQS MessageAttributes so metrics-processor can
        # attach its spans as children of the originating document trace.
        from opentelemetry.propagate import inject

        carrier: dict[str, str] = {}
        inject(carrier)
        message_attributes = {
            k: {"DataType": "String", "StringValue": v} for k, v in carrier.items()
        }

        sqs_service.send_message(
            queue_url, json.dumps(ddb_record, default=str), message_attributes or None
        )
        logger.info(f"Successfully sent {object_key} to SQS queue")

    except Exception as e:
        logger.error(f"Failed to send {object_key} to SQS queue: {e}")


def get_user_provided_document_category(object_key: str) -> str | None:
    """Get the tenant-provided document category for a file, or None if unset.

    Categories are free-form and stored verbatim; the attribute is simply absent
    when none was provided at upload. Callers treat None as "no category provided".
    """
    ddb_record = get_ddb_record(object_key)
    if ddb_record is None:
        return None

    return ddb_record.get(DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY)


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


def update_ddb(data: UpdateDdbRecord) -> None:
    """Update DynamoDB processing status for a file."""
    try:
        update_expr, expr_values = _build_update_expression(
            status=data.status,
            data=data.data,
            internal_api_response=data.internal_api_response,
            v1_api_response=None,
            bda_invocation_arn=data.bda_invocation_arn,
            bda_project_arn_used=data.bda_project_arn_used,
            used_category_specific_project=data.used_category_specific_project,
            error_message=data.error_message,
            below_extraction_confidence_floor=data.below_extraction_confidence_floor,
            extraction_rules_configured=data.extraction_rules_configured,
            missing_required_field_list=data.missing_required_field_list,
            required_field_list=data.required_field_list,
            applied_extraction_confidence_floor=data.applied_extraction_confidence_floor,
            used_default_confidence_floor=data.used_default_confidence_floor,
        )

        if data.pages_sent_to_bda is not None:
            update_expr += f", {DocumentMetadata.PAGES_SENT_TO_BDA} = :pagesSentToBda"
            expr_values[":pagesSentToBda"] = data.pages_sent_to_bda

        if data.bda_invoke_duration_seconds is not None:
            update_expr += f", {DocumentMetadata.BDA_INVOKE_DURATION_SECONDS} = :bdaInvokeDs"
            expr_values[":bdaInvokeDs"] = data.bda_invoke_duration_seconds

        if data.bda_invoke_retry_count is not None:
            update_expr += f", {DocumentMetadata.BDA_INVOKE_RETRY_COUNT} = :bdaRetryCount"
            expr_values[":bdaRetryCount"] = data.bda_invoke_retry_count

        if data.result_processor_started_at is not None:
            update_expr += f", {DocumentMetadata.RESULT_PROCESSOR_STARTED_AT} = :rpStartedAt"
            expr_values[":rpStartedAt"] = data.result_processor_started_at

        timing_updates, timing_values = _build_timing_updates(
            data.object_key,
            data.status,
            bda_output_s3_uri=data.data.bda_output_s3_uri if data.data else None,
        )
        if timing_updates:
            update_expr += f", {timing_updates}"
            expr_values.update(timing_values)

        _execute_ddb_update(data.object_key, update_expr, expr_values)
        _finalize_v1_response(data.object_key, data.status, data.data, data.error_message)

        if ProcessStatus.is_classified(data.status):
            _send_record_to_metrics_queue(data.object_key)

    except Exception as e:
        logger.error(f"Failed to update DDB status: {e}")
        raise


def set_extract_method(object_key: str, method: ExtractMethod, started_at: str) -> None:
    """Record which extraction engine is processing this document and when it started.

    Used by non-BDA extraction engines (e.g. Textract) that need to stamp the
    method independently of the standard update_ddb/STARTED flow, which handles
    the BDA case inline via _build_update_expression.
    """
    _execute_ddb_update(
        object_key,
        (
            f"SET {DocumentMetadata.EXTRACTION_STARTED_AT} = :start, "
            f"{DocumentMetadata.EXTRACT_METHOD} = :method"
        ),
        {
            ":start": started_at,
            ":method": method.value,
        },
    )


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
        elif isinstance(value, dict):
            value = json.dumps(value)

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


def upsert_ddb(data: InitialDdbRecord) -> None:
    """Upsert a document-metadata DDB row by file name.

    Creates the row if missing, updates it in place if present. `createdAt` is
    set only on initial create (preserved on subsequent calls via if_not_exists);
    `updatedAt` is always refreshed.
    """
    try:
        now = datetime.now(UTC).isoformat()

        expr_fields: list[str] = [
            f"{DocumentMetadata.ORIGINAL_FILE_NAME} = :originalFileName",
            f"{DocumentMetadata.ORIGINAL_FILE_NAME_LOWER} = :originalFileNameLower",
            f"{DocumentMetadata.PROCESS_STATUS} = :processStatus",
            f"{DocumentMetadata.CREATED_AT} = if_not_exists({DocumentMetadata.CREATED_AT}, :now)",
            f"{DocumentMetadata.UPDATED_AT} = :now",
            f"{DocumentMetadata.IS_PASSWORD_PROTECTED} = :pwProt",
            f"{DocumentMetadata.IS_DOCUMENT_BLURRY} = :blurry",
            f"{DocumentMetadata.BLUR_ANALYSIS_FAILED} = :blurFailed",
            f"{DocumentMetadata.BLUR_LLM_CHECKED} = :blurLlm",
            f"{DocumentMetadata.AI_CONSENT_FLAG} = "
            f"if_not_exists({DocumentMetadata.AI_CONSENT_FLAG}, :aiConsent)",
            "#ttl = if_not_exists(#ttl, :ttl)",
        ]
        expr_values: dict[str, Any] = {
            ":originalFileName": data.original_file_name,
            ":originalFileNameLower": data.original_file_name.lower(),
            ":processStatus": data.process_status,
            ":now": now,
            ":pwProt": bool(data.is_password_protected),
            ":blurry": bool(data.is_document_blurry),
            ":blurFailed": bool(data.blur_analysis_failed),
            ":blurLlm": bool(data.blur_llm_checked),
            ":aiConsent": bool(data.ai_consent_flag),
            ":ttl": get_ttl_epoch_in_days(
                data.ttl_days or ConfigDefaults.DOCUMENT_METADATA_TTL_DAYS
            ),
        }

        # Categories are free-form and optional: write the attribute only when
        # provided, leaving it absent otherwise (no sentinel to strip on read).
        if data.user_provided_document_category:
            expr_fields.append(f"{DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY} = :category")
            expr_values[":category"] = data.user_provided_document_category

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
