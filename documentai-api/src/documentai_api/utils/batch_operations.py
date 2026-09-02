"""Batch upload DynamoDB operations."""

from datetime import UTC, datetime
from typing import Any

from documentai_api.config.constants import (
    BatchStatus,
    ConfigDefaults,
)
from documentai_api.config.env import EnvVars, get_required_env
from documentai_api.logging import get_logger
from documentai_api.schemas.document_batches import DocumentBatches
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.services import ddb as ddb_service
from documentai_api.utils.dates import get_ttl_epoch_in_days

logger = get_logger(__name__)


def create_batch(
    batch_id: str,
    total_files: int,
    category: str | None,
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
        # TTL from creation - batch records are short-lived tracking artifacts.
        DocumentBatches.TIME_TO_LIVE: get_ttl_epoch_in_days(
            ConfigDefaults.DOCUMENT_BATCHES_TTL_DAYS
        ),
    }

    if category:
        item[DocumentBatches.CATEGORY] = category

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


def increment_resolved_count(batch_id: str) -> None:
    """Atomically increment resolvedCount and finalize batch status when all jobs are done.

    Swallows all exceptions - a counter failure must never abort the job that triggered it.
    """
    try:
        table_name = get_required_env(EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME)
        from documentai_api.utils.aws_client_factory import AWSClientFactory

        table = AWSClientFactory.get_ddb_table(table_name)

        response = table.update_item(
            Key={DocumentBatches.BATCH_ID: batch_id},
            UpdateExpression=(
                f"ADD {DocumentBatches.RESOLVED_COUNT} :one SET {DocumentBatches.UPDATED_AT} = :now"
            ),
            ExpressionAttributeValues={
                ":one": 1,
                ":now": datetime.now(UTC).isoformat(),
                ":processing": BatchStatus.PROCESSING.value,
            },
            ConditionExpression=f"{DocumentBatches.BATCH_STATUS} = :processing",
            ReturnValues="ALL_NEW",
        )

        updated = response.get("Attributes", {})
        resolved = int(updated.get(DocumentBatches.RESOLVED_COUNT) or 0)  # type: ignore[arg-type]
        total = int(updated.get(DocumentBatches.TOTAL_FILES) or 0)  # type: ignore[arg-type]

        if resolved < total:
            return

        # All jobs resolved - determine terminal batch status.
        # Re-query jobs to get accurate failed count rather than tracking it
        # incrementally (avoids counter drift from retries or reaper overlap).
        jobs = query_jobs_by_batch_id(batch_id)
        from documentai_api.config.constants import ProcessStatus

        failed_count = sum(
            1
            for j in jobs
            if j.get(DocumentMetadata.PROCESS_STATUS) == ProcessStatus.FAILED.value
            or j.get(DocumentMetadata.PROCESS_STATUS) == ProcessStatus.TIMED_OUT.value
        )

        if failed_count == 0:
            terminal = BatchStatus.COMPLETED
        elif failed_count == total:
            terminal = BatchStatus.FAILED
        else:
            terminal = BatchStatus.PARTIAL

        update_batch_status(
            batch_id,
            status=terminal,
            condition_expression=f"{DocumentBatches.BATCH_STATUS} = :expected",
            condition_values={":expected": BatchStatus.PROCESSING.value},
        )
        logger.info(
            f"Batch {batch_id} finalized",
            extra={
                "status": terminal,
                "resolved": resolved,
                "failed": failed_count,
                "total": total,
            },
        )
    except Exception as e:
        logger.warning(f"Failed to increment resolved count for batch {batch_id}: {e}")
