"""Document reaper job.

Finds DocumentRecord rows stuck in PROCESSING for more than one hour,
checks BDA for the actual job status, and resolves them to a terminal state.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from botocore.exceptions import ClientError

from documentai_api.config.constants import (
    BdaJobStatus,
    ConfigDefaults,
    ProcessStatus,
)
from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.services import cloudwatch as cloudwatch_service
from documentai_api.services import ddb as ddb_service
from documentai_api.services.bda import get_bda_job_response
from documentai_api.utils.aws_client_factory import AWSClientFactory

logger = get_logger(__name__)


def _query_stale_by_status(
    table: Any, index_name: str, status: str, cutoff: str
) -> list[dict[str, Any]]:
    """Query a single status from the GSI for records older than cutoff."""
    items: list[dict[str, Any]] = []
    last_key = None

    while True:
        kwargs: dict[str, Any] = {
            "IndexName": index_name,
            "KeyConditionExpression": (
                boto3.dynamodb.conditions.Key(DocumentMetadata.PROCESS_STATUS).eq(status)  # type: ignore[attr-defined]
                & boto3.dynamodb.conditions.Key(DocumentMetadata.CREATED_AT).lt(cutoff)  # type: ignore[attr-defined]
            ),
        }

        if last_key:
            kwargs["ExclusiveStartKey"] = last_key

        response = table.query(**kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")

        if not last_key:
            break

    return items


def _find_stale_records(table_name: str, index_name: str) -> list[dict[str, Any]]:
    """Query all non-terminal statuses in parallel for records older than the threshold."""
    cutoff = (
        datetime.now(UTC) - timedelta(hours=ConfigDefaults.PROCESSING_REAPER_STALE_THRESHOLD_HOURS)
    ).isoformat()
    table = AWSClientFactory.get_ddb_table(table_name)

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=len(ProcessStatus.non_terminal())) as executor:
        futures = {
            executor.submit(_query_stale_by_status, table, index_name, status, cutoff): status
            for status in ProcessStatus.non_terminal()
        }
        for future in as_completed(futures):
            status = futures[future]
            try:
                results.extend(future.result())
            except Exception as e:
                logger.error(f"Failed to query stale records for status {status!r}: {e}")

    return results


def _process_stale_record(table_name: str, ddb_record: dict[str, Any]) -> str | None:
    """Determine and apply the terminal status for a stale record.

    Returns the status that was applied, or None if the record was left alone.
    """
    file_name = ddb_record[DocumentMetadata.FILE_NAME]
    bda_invocation_arn = ddb_record.get(DocumentMetadata.BDA_INVOCATION_ARN)

    if not bda_invocation_arn:
        applied = _mark_terminal(table_name, file_name, ProcessStatus.TIMED_OUT)
        return ProcessStatus.TIMED_OUT if applied else None

    bda_response = get_bda_job_response(bda_invocation_arn)
    if bda_response is None:
        applied = _mark_terminal(table_name, file_name, ProcessStatus.TIMED_OUT)
        return ProcessStatus.TIMED_OUT if applied else None

    bda_status = bda_response.get("status", "")

    if BdaJobStatus.is_completed(bda_status):
        applied = _mark_terminal(
            table_name,
            file_name,
            ProcessStatus.FAILED,
            "BDA completed but result was never processed",
        )
        return ProcessStatus.FAILED if applied else None

    if BdaJobStatus.is_failed(bda_status):
        applied = _mark_terminal(
            table_name, file_name, ProcessStatus.FAILED, f"BDA reported status: {bda_status}"
        )
        return ProcessStatus.FAILED if applied else None

    # BDA job is still running or in an unrecognized state - leave it be
    return None


def _mark_terminal(
    table_name: str, file_name: str, status: ProcessStatus, reason: str | None = None
) -> bool:
    """Write terminal status. Returns False if the pipeline already completed the record."""
    expr = f"SET {DocumentMetadata.PROCESS_STATUS} = :s, {DocumentMetadata.UPDATED_AT} = :u"
    values: dict[str, Any] = {":s": status, ":u": datetime.now(UTC).isoformat()}

    if reason:
        expr += f", {DocumentMetadata.ERROR_MESSAGE} = :e"
        values[":e"] = reason

    non_terminal_values = {f":st{i}": s for i, s in enumerate(ProcessStatus.non_terminal())}
    condition = f"{DocumentMetadata.PROCESS_STATUS} IN ({', '.join(non_terminal_values)})"

    try:
        ddb_service.update_item(
            table_name,
            {DocumentMetadata.FILE_NAME: file_name},
            expr,
            {**values, **non_terminal_values},
            condition_expression=condition,
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.info(f"Skipping {file_name!r} - pipeline already completed it")
            return False
        raise


def main() -> dict[str, Any]:
    aws_config = get_aws_config()
    table_name = aws_config.documentai_document_metadata_table_name
    index_name = aws_config.documentai_document_metadata_status_created_at_index_name

    if not table_name or not index_name:
        raise ValueError(
            "documentai_document_metadata_table_name and documentai_document_metadata_status_created_at_index_name must be set"
        )

    stale = _find_stale_records(table_name, index_name)
    logger.info(f"Found {len(stale)} stale PROCESSING record(s)")
    cloudwatch_service.put_metric_data("DocumentAI/DocumentReaper", "StaleRecordsFound", len(stale))

    counts: dict[str, int] = {}

    for ddb_record in stale:
        file_name = ddb_record[DocumentMetadata.FILE_NAME]

        try:
            reaped_status = _process_stale_record(table_name, ddb_record)

            if reaped_status:
                counts[reaped_status] = counts.get(reaped_status, 0) + 1
                logger.info(f"Resolved {file_name!r} -> {reaped_status}")
            else:
                logger.debug(f"Skipped {file_name!r} - BDA still in progress")
        except Exception as e:
            logger.error(f"Failed to reap {file_name!r}: {e}")
            counts["error"] = counts.get("error", 0) + 1

    return {"staleRecordsFound": len(stale), "outcomes": counts}
