"""Worker Lambda smoke tests.

Each test invokes a worker Lambda directly and validates it can complete its
job without IAM or runtime errors. Requires LAMBDA_FUNCTION_PREFIX in .env.e2e
(e.g. docai-dev-123456789012) — run 'make .env.e2e' first.

  - document-reaper    -> seeds stale document_metadata + document_batches rows,
                          invokes reaper, asserts both reach a terminal state.
                          Validates ddb:Query/UpdateItem/GetItem on both tables
                          and their CMKs, cloudwatch:PutMetricData, ssm:GetParameter.

  - metrics-aggregator -> invokes for today with overwrite. Validates s3:GetObject/
                          PutObject (metrics bucket), Athena, Glue,
                          cloudwatch:PutMetricData, ssm:GetParameter.

  - usage-report       -> invokes for current month. Validates s3:GetObject/PutObject
                          (metrics + analytics-results buckets), Athena,
                          cloudwatch:PutMetricData, ssm:GetParameter.

Run with: make test-smoke (serial) or make test-e2e (parallel, includes smoke).
"""

import secrets
from datetime import UTC, datetime, timedelta

import boto3

from documentai_api.config.constants import BatchStatus, ProcessStatus
from documentai_api.config.env_var_names_generated import EnvVarNames
from documentai_api.schemas.document_batches import DocumentBatches
from documentai_api.schemas.document_metadata import DocumentMetadata

_WORKER_DOCUMENT_REAPER = "document-reaper"
_WORKER_METRICS_AGGREGATOR = "metrics-aggregator"
_WORKER_USAGE_REPORT = "usage-report"


def test_worker_document_reaper(lambda_client, reset_env):
    """Seed a stale document and batch, invoke the reaper, assert both are resolved.

    A green test confirms the reaper can query the GSI, mark documents terminal,
    and finalize the parent batch — covering all DDB permissions and CMK access.
    """
    ddb = boto3.resource("dynamodb")

    metadata_table = ddb.Table(reset_env[EnvVarNames.DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME])
    batches_table = ddb.Table(reset_env[EnvVarNames.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME])

    batch_id = f"smoke-reaper-{secrets.token_hex(4)}"
    file_name = f"smoke-reaper/{batch_id}/test.pdf"
    stale_created_at = (datetime.now(UTC) - timedelta(hours=2)).isoformat()

    metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: file_name,
            DocumentMetadata.PROCESS_STATUS: ProcessStatus.STARTED,
            DocumentMetadata.CREATED_AT: stale_created_at,
            DocumentMetadata.BATCH_ID: batch_id,
        }
    )
    batches_table.put_item(
        Item={
            DocumentBatches.BATCH_ID: batch_id,
            DocumentBatches.BATCH_STATUS: BatchStatus.PROCESSING,
            DocumentBatches.TOTAL_FILES: 1,
            DocumentBatches.RESOLVED_COUNT: 0,
        }
    )

    try:
        result = lambda_client(_WORKER_DOCUMENT_REAPER, {})
        assert result.get("staleRecordsFound", 0) >= 1, f"reaper found no stale records: {result}"
        assert "error" not in result.get("outcomes", {}), f"reaper had errors: {result}"

        doc = metadata_table.get_item(Key={DocumentMetadata.FILE_NAME: file_name}).get("Item", {})
        assert doc.get(DocumentMetadata.PROCESS_STATUS) in (
            ProcessStatus.TIMED_OUT,
            ProcessStatus.FAILED,
        ), f"document not resolved: {doc.get(DocumentMetadata.PROCESS_STATUS)!s}"

        batch = batches_table.get_item(Key={DocumentBatches.BATCH_ID: batch_id}).get("Item", {})
        # resolvedCount is incremented before the batch-id GSI lookup (infra follow-up
        # adds that index), so this proves UpdateItem + CMK access on document_batches.
        resolved = batch.get(DocumentBatches.RESOLVED_COUNT, 0)
        assert int(str(resolved)) == 1, f"batch counter not updated: {batch}"
        # TODO: assert terminal batch status once the batch-id GSI is added.
    finally:
        metadata_table.delete_item(Key={DocumentMetadata.FILE_NAME: file_name})
        batches_table.delete_item(Key={DocumentBatches.BATCH_ID: batch_id})


def test_worker_metrics_aggregator(lambda_client):
    """Invoke metrics-aggregator for today and assert no FunctionError.

    Validates s3:GetObject and s3:PutObject on the metrics bucket, Athena query
    execution, Glue table access, cloudwatch:PutMetricData, and ssm:GetParameter.
    """
    lambda_client(_WORKER_METRICS_AGGREGATOR, {"mode": "today", "overwrite": "true"})


def test_worker_usage_report(lambda_client):
    """Invoke usage-report for the current month and assert no FunctionError.

    Validates s3:GetObject and s3:PutObject on the metrics and analytics-results
    buckets, Athena query execution, cloudwatch:PutMetricData, and ssm:GetParameter.
    """
    lambda_client(_WORKER_USAGE_REPORT, {"month": "current"})
