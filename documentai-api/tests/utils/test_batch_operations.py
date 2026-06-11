from datetime import UTC, datetime

import pytest

from documentai_api.config.constants import ProcessStatus
from documentai_api.utils import batch_operations as batch_ops
from documentai_api.utils import ddb as ddb_util


@pytest.mark.integration
class TestCreateBatch:
    def test_creates_record_with_tenant(self, ddb_batches_table):
        """create_batch writes tenantId and clientName to DDB."""
        from documentai_api.schemas.document_batches import DocumentBatches

        batch_ops.create_batch(
            "batch-1",
            3,
            None,
            tenant_id="tenant-abc",
            api_key_name="client-xyz",
        )

        item = ddb_batches_table.get_item(Key={"batchId": "batch-1"})["Item"]
        assert item[DocumentBatches.TENANT_ID] == "tenant-abc"
        assert item[DocumentBatches.API_KEY_NAME] == "client-xyz"
        assert item[DocumentBatches.BATCH_STATUS] == "uploading"
        assert item[DocumentBatches.TOTAL_FILES] == 3

        # ttl stamped ~30 days out as an integer epoch
        ttl = item[DocumentBatches.TIME_TO_LIVE]
        expected = int(datetime.now(UTC).timestamp()) + 30 * 24 * 60 * 60
        assert abs(int(ttl) - expected) < 600

    def test_returns_created_at_timestamp(self, ddb_batches_table):
        """create_batch returns the createdAt ISO timestamp."""
        from datetime import datetime

        created_at = batch_ops.create_batch("batch-2", 1, None)
        assert created_at is not None
        datetime.fromisoformat(created_at)

    def test_duplicate_batch_id_raises_409(self, ddb_batches_table):
        """create_batch with existing batch_id raises HTTPException 409."""
        from fastapi import HTTPException

        batch_ops.create_batch("batch-dup", 1, None)

        with pytest.raises(HTTPException) as exc_info:
            batch_ops.create_batch("batch-dup", 2, None)

        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.detail


@pytest.mark.integration
class TestUpdateBatchStatus:
    def test_updates_status(self, ddb_batches_table):
        """update_batch_status changes the batch status."""
        from documentai_api.config.constants import BatchStatus
        from documentai_api.schemas.document_batches import DocumentBatches

        batch_ops.create_batch("batch-u1", 1, None)
        batch_ops.update_batch_status("batch-u1", status=BatchStatus.PROCESSING)

        item = ddb_batches_table.get_item(Key={"batchId": "batch-u1"})["Item"]
        assert item[DocumentBatches.BATCH_STATUS] == BatchStatus.PROCESSING.value

    def test_conditional_update_succeeds(self, ddb_batches_table):
        """Conditional update succeeds when condition matches."""
        from documentai_api.config.constants import BatchStatus
        from documentai_api.schemas.document_batches import DocumentBatches

        batch_ops.create_batch("batch-c1", 1, None)
        batch_ops.update_batch_status("batch-c1", status=BatchStatus.PROCESSING)

        batch_ops.update_batch_status(
            "batch-c1",
            status=BatchStatus.COMPLETED,
            condition_expression=f"{DocumentBatches.BATCH_STATUS} = :expected",
            condition_values={":expected": BatchStatus.PROCESSING.value},
        )

        item = ddb_batches_table.get_item(Key={"batchId": "batch-c1"})["Item"]
        assert item[DocumentBatches.BATCH_STATUS] == BatchStatus.COMPLETED.value

    def test_conditional_update_fails_on_mismatch(self, ddb_batches_table):
        """Conditional update raises when condition doesn't match (race lost)."""
        from botocore.exceptions import ClientError

        from documentai_api.config.constants import BatchStatus
        from documentai_api.schemas.document_batches import DocumentBatches

        batch_ops.create_batch("batch-c2", 1, None)
        batch_ops.update_batch_status("batch-c2", status=BatchStatus.COMPLETED)

        with pytest.raises(ClientError) as exc_info:
            batch_ops.update_batch_status(
                "batch-c2",
                status=BatchStatus.FAILED,
                condition_expression=f"{DocumentBatches.BATCH_STATUS} = :expected",
                condition_values={":expected": BatchStatus.PROCESSING.value},
            )

        assert exc_info.value.response["Error"]["Code"] == "ConditionalCheckFailedException"


@pytest.mark.integration
class TestQueryJobsByBatchId:
    def test_returns_jobs_for_batch(self, ddb_doc_metadata_table):
        """query_jobs_by_batch_id returns all jobs associated with a batch."""
        ddb_util.upsert_ddb(
            object_key="0-file1.pdf",
            original_file_name="file1.pdf",
            process_status=ProcessStatus.SUCCESS.value,
            job_id="job-1",
            batch_id="batch-q1",
        )
        ddb_util.upsert_ddb(
            object_key="1-file2.pdf",
            original_file_name="file2.pdf",
            process_status=ProcessStatus.STARTED.value,
            job_id="job-2",
            batch_id="batch-q1",
        )
        ddb_util.upsert_ddb(
            object_key="0-file3.pdf",
            original_file_name="file3.pdf",
            process_status=ProcessStatus.SUCCESS.value,
            job_id="job-3",
            batch_id="batch-other",
        )

        results = batch_ops.query_jobs_by_batch_id("batch-q1")

        assert len(results) == 2
        job_ids = {r["jobId"] for r in results}
        assert job_ids == {"job-1", "job-2"}

    def test_returns_empty_for_nonexistent_batch(self, ddb_doc_metadata_table):
        """query_jobs_by_batch_id returns empty list for unknown batch."""
        results = batch_ops.query_jobs_by_batch_id("batch-nonexistent")
        assert results == []


@pytest.mark.integration
class TestGetBatch:
    def test_returns_record(self, ddb_batches_table):
        """get_batch returns the batch record."""
        from documentai_api.schemas.document_batches import DocumentBatches

        batch_ops.create_batch("batch-g1", 5, None, tenant_id="t1", api_key_name="c1")

        record = batch_ops.get_batch("batch-g1")

        assert record is not None
        assert record[DocumentBatches.BATCH_ID] == "batch-g1"
        assert record[DocumentBatches.TENANT_ID] == "t1"

    def test_returns_none_for_missing(self, ddb_batches_table):
        """get_batch returns None for nonexistent batch."""
        assert batch_ops.get_batch("batch-missing") is None
