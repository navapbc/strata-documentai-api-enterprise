from datetime import UTC, datetime

import pytest

from documentai_api.config.constants import BatchStatus, ProcessStatus
from documentai_api.dtos.ddb import InitialDdbRecord
from documentai_api.utils import batch_operations as batch_util
from documentai_api.utils import ddb as ddb_util

# =============================================================================
# create_batch
# =============================================================================


def test_create_batch_writes_tenant_and_client(ddb_batches_table):
    """create_batch writes tenantId and clientName to DDB."""
    from documentai_api.schemas.document_batches import DocumentBatches

    batch_util.create_batch(
        "test-batch-id",
        3,
        None,
        tenant_id="test-tenant-id",
        api_key_name="test-api-key-name",
    )

    item = ddb_batches_table.get_item(Key={"batchId": "test-batch-id"})["Item"]
    assert item[DocumentBatches.TENANT_ID] == "test-tenant-id"
    assert item[DocumentBatches.API_KEY_NAME] == "test-api-key-name"
    assert item[DocumentBatches.BATCH_STATUS] == "uploading"
    assert item[DocumentBatches.TOTAL_FILES] == 3

    ttl = item[DocumentBatches.TIME_TO_LIVE]
    expected = int(datetime.now(UTC).timestamp()) + 30 * 24 * 60 * 60
    assert abs(int(ttl) - expected) < 600


def test_create_batch_returns_created_at_timestamp(ddb_batches_table):
    """create_batch returns the createdAt ISO timestamp."""
    created_at = batch_util.create_batch("test-batch-id", 1, None)
    assert created_at is not None
    datetime.fromisoformat(created_at)


def test_create_batch_duplicate_raises_409(ddb_batches_table):
    """create_batch with existing batch_id raises HTTPException 409."""
    from fastapi import HTTPException

    batch_util.create_batch("test-batch-id", 1, None)

    with pytest.raises(HTTPException) as exc_info:
        batch_util.create_batch("test-batch-id", 2, None)

    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail


# =============================================================================
# update_batch_status
# =============================================================================


def test_update_batch_status_changes_status(ddb_batches_table):
    """update_batch_status changes the batch status."""
    from documentai_api.schemas.document_batches import DocumentBatches

    batch_util.create_batch("test-batch-id", 1, None)
    batch_util.update_batch_status("test-batch-id", status=BatchStatus.PROCESSING)

    item = ddb_batches_table.get_item(Key={"batchId": "test-batch-id"})["Item"]
    assert item[DocumentBatches.BATCH_STATUS] == BatchStatus.PROCESSING.value


def test_update_batch_status_conditional_succeeds(ddb_batches_table):
    """Conditional update succeeds when condition matches."""
    from documentai_api.schemas.document_batches import DocumentBatches

    batch_util.create_batch("test-batch-id", 1, None)
    batch_util.update_batch_status("test-batch-id", status=BatchStatus.PROCESSING)

    batch_util.update_batch_status(
        "test-batch-id",
        status=BatchStatus.COMPLETED,
        condition_expression=f"{DocumentBatches.BATCH_STATUS} = :expected",
        condition_values={":expected": BatchStatus.PROCESSING.value},
    )

    item = ddb_batches_table.get_item(Key={"batchId": "test-batch-id"})["Item"]
    assert item[DocumentBatches.BATCH_STATUS] == BatchStatus.COMPLETED.value


def test_update_batch_status_conditional_fails_on_mismatch(ddb_batches_table):
    """Conditional update raises when condition doesn't match (race lost)."""
    from botocore.exceptions import ClientError

    from documentai_api.schemas.document_batches import DocumentBatches

    batch_util.create_batch("test-batch-id", 1, None)
    batch_util.update_batch_status("test-batch-id", status=BatchStatus.COMPLETED)

    with pytest.raises(ClientError) as exc_info:
        batch_util.update_batch_status(
            "test-batch-id",
            status=BatchStatus.FAILED,
            condition_expression=f"{DocumentBatches.BATCH_STATUS} = :expected",
            condition_values={":expected": BatchStatus.PROCESSING.value},
        )

    assert exc_info.value.response["Error"]["Code"] == "ConditionalCheckFailedException"


# =============================================================================
# query_jobs_by_batch_id
# =============================================================================


def test_query_jobs_by_batch_id_returns_jobs_for_batch(ddb_doc_metadata_table):
    """query_jobs_by_batch_id returns all jobs associated with a batch."""
    ddb_util.upsert_ddb(
        InitialDdbRecord(
            object_key="0-file1.pdf",
            original_file_name="file1.pdf",
            process_status=ProcessStatus.SUCCESS.value,
            job_id="test-job-id-1",
            batch_id="test-batch-id",
        )
    )
    ddb_util.upsert_ddb(
        InitialDdbRecord(
            object_key="1-file2.pdf",
            original_file_name="file2.pdf",
            process_status=ProcessStatus.STARTED.value,
            job_id="test-job-id-2",
            batch_id="test-batch-id",
        )
    )
    ddb_util.upsert_ddb(
        InitialDdbRecord(
            object_key="0-file3.pdf",
            original_file_name="file3.pdf",
            process_status=ProcessStatus.SUCCESS.value,
            job_id="test-job-id-3",
            batch_id="batch-other",
        )
    )

    results = batch_util.query_jobs_by_batch_id("test-batch-id")

    assert len(results) == 2
    assert {r["jobId"] for r in results} == {"test-job-id-1", "test-job-id-2"}


def test_query_jobs_by_batch_id_returns_empty_for_unknown_batch(ddb_doc_metadata_table):
    """query_jobs_by_batch_id returns empty list for unknown batch."""
    assert batch_util.query_jobs_by_batch_id("batch-nonexistent") == []


# =============================================================================
# get_batch
# =============================================================================


def test_get_batch_returns_record(ddb_batches_table):
    """get_batch returns the batch record."""
    from documentai_api.schemas.document_batches import DocumentBatches

    batch_util.create_batch("test-batch-id", 5, None, tenant_id="t1", api_key_name="c1")

    record = batch_util.get_batch("test-batch-id")

    assert record is not None
    assert record[DocumentBatches.BATCH_ID] == "test-batch-id"
    assert record[DocumentBatches.TENANT_ID] == "t1"


def test_get_batch_returns_none_for_missing(ddb_batches_table):
    """get_batch returns None for nonexistent batch."""
    assert batch_util.get_batch("batch-missing") is None


# =============================================================================
# increment_resolved_count
# =============================================================================


def _seed_jobs(statuses: list[str], batch_id: str) -> None:
    for i, status in enumerate(statuses):
        ddb_util.upsert_ddb(
            InitialDdbRecord(
                object_key=f"{i}-file.pdf",
                original_file_name=f"file{i}.pdf",
                process_status=status,
                job_id=f"job-{i}",
                batch_id=batch_id,
            )
        )


def test_increment_resolved_count_partial_leaves_batch_processing(
    ddb_batches_table, ddb_doc_metadata_table
):
    """ResolvedCount increments but batch stays PROCESSING when not all jobs are done."""
    from documentai_api.schemas.document_batches import DocumentBatches

    batch_util.create_batch("test-batch-id", 3, None)
    batch_util.update_batch_status("test-batch-id", BatchStatus.PROCESSING)

    batch_util.increment_resolved_count("test-batch-id")

    item = ddb_batches_table.get_item(Key={"batchId": "test-batch-id"})["Item"]
    assert item[DocumentBatches.BATCH_STATUS] == BatchStatus.PROCESSING.value
    assert int(item[DocumentBatches.RESOLVED_COUNT]) == 1


@pytest.mark.parametrize(
    ("job_statuses", "expected_batch_status"),
    [
        ([ProcessStatus.SUCCESS.value, ProcessStatus.SUCCESS.value], BatchStatus.COMPLETED),
        ([ProcessStatus.FAILED.value, ProcessStatus.FAILED.value], BatchStatus.FAILED),
        ([ProcessStatus.SUCCESS.value, ProcessStatus.FAILED.value], BatchStatus.PARTIAL),
    ],
)
def test_increment_resolved_count_finalizes_batch(
    ddb_batches_table, ddb_doc_metadata_table, job_statuses, expected_batch_status
):
    """All jobs resolved → batch finalized as COMPLETED, FAILED, or PARTIAL."""
    from documentai_api.schemas.document_batches import DocumentBatches

    _seed_jobs(job_statuses, "test-batch-id")
    batch_util.create_batch("test-batch-id", len(job_statuses), None)
    batch_util.update_batch_status("test-batch-id", BatchStatus.PROCESSING)

    for _ in job_statuses:
        batch_util.increment_resolved_count("test-batch-id")

    item = ddb_batches_table.get_item(Key={"batchId": "test-batch-id"})["Item"]
    assert item[DocumentBatches.BATCH_STATUS] == expected_batch_status.value


def test_increment_resolved_count_already_finalized_is_swallowed(
    ddb_batches_table, ddb_doc_metadata_table
):
    """Calling increment on an already-finalized batch does not raise."""
    batch_util.create_batch("test-batch-id", 1, None)
    batch_util.update_batch_status("test-batch-id", BatchStatus.COMPLETED)

    batch_util.increment_resolved_count("test-batch-id")
