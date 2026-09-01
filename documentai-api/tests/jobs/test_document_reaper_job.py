"""Tests for jobs/document_reaper/main.py."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from documentai_api.config.constants import BdaJobStatus, ProcessStatus
from documentai_api.jobs.document_reaper.main import main
from documentai_api.schemas.document_metadata import DocumentMetadata

STALE_CREATED_AT = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
FRESH_CREATED_AT = datetime.now(UTC).isoformat()
BDA_INVOCATION_ARN = "arn:aws:bda:us-east-1:123:job/1"
BDA_INVOCATION_ARN_2 = "arn:aws:bda:us-east-1:123:job/2"


@pytest.fixture
def mock_env(runtime_required_env):
    pass


@pytest.fixture
def create_stale_record(ddb_doc_metadata_table):
    """Return a callable that inserts stale records into the metadata table."""

    def _create(file_name: str, status: str, bda_invocation_arn: str | None = None) -> None:
        item = {
            DocumentMetadata.FILE_NAME: file_name,
            DocumentMetadata.PROCESS_STATUS: status,
            DocumentMetadata.CREATED_AT: STALE_CREATED_AT,
        }
        if bda_invocation_arn:
            item[DocumentMetadata.BDA_INVOCATION_ARN] = bda_invocation_arn
        ddb_doc_metadata_table.put_item(Item=item)

    return _create


def _get_record(table: Any, file_name: str) -> dict[str, Any]:
    return cast(dict[str, Any], table.get_item(Key={DocumentMetadata.FILE_NAME: file_name})["Item"])


def test_main_raises_if_config_missing():
    with pytest.raises(ValueError, match="must be set"):
        main()


def test_no_stale_records(mock_env, ddb_doc_metadata_table, mocker):
    mock_put = mocker.patch(
        "documentai_api.jobs.document_reaper.main.cloudwatch_service.put_metric_data"
    )

    result = main()

    assert result == {"staleRecordsFound": 0, "outcomes": {}}
    mock_put.assert_called_once_with("DocumentAI/DocumentReaper", "StaleRecordsFound", 0)


def test_timed_out_when_no_bda_arn(mock_env, ddb_doc_metadata_table, create_stale_record, mocker):
    mock_put = mocker.patch(
        "documentai_api.jobs.document_reaper.main.cloudwatch_service.put_metric_data"
    )
    create_stale_record("file.pdf", ProcessStatus.STARTED)

    result = main()

    assert result["staleRecordsFound"] == 1
    mock_put.assert_called_once_with("DocumentAI/DocumentReaper", "StaleRecordsFound", 1)
    assert result["outcomes"][ProcessStatus.TIMED_OUT] == 1
    assert (
        _get_record(ddb_doc_metadata_table, "file.pdf")[DocumentMetadata.PROCESS_STATUS]
        == ProcessStatus.TIMED_OUT
    )


def test_timed_out_when_bda_returns_none(
    mock_env, ddb_doc_metadata_table, create_stale_record, mocker
):
    create_stale_record("file.pdf", ProcessStatus.STARTED, BDA_INVOCATION_ARN)
    mocker.patch("documentai_api.jobs.document_reaper.main.get_bda_job_response", return_value=None)

    result = main()

    assert result["outcomes"][ProcessStatus.TIMED_OUT] == 1
    assert (
        _get_record(ddb_doc_metadata_table, "file.pdf")[DocumentMetadata.PROCESS_STATUS]
        == ProcessStatus.TIMED_OUT
    )


def test_failed_when_bda_completed_but_never_processed(
    mock_env, ddb_doc_metadata_table, create_stale_record, mocker
):
    create_stale_record("file.pdf", ProcessStatus.STARTED, BDA_INVOCATION_ARN)
    mocker.patch(
        "documentai_api.jobs.document_reaper.main.get_bda_job_response",
        return_value={"status": BdaJobStatus.SUCCESS},
    )

    result = main()

    assert result["outcomes"][ProcessStatus.FAILED] == 1
    record = _get_record(ddb_doc_metadata_table, "file.pdf")
    assert record[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.FAILED
    assert "never processed" in record[DocumentMetadata.ERROR_MESSAGE]


@pytest.mark.parametrize("bda_status", [BdaJobStatus.SERVICE_ERROR, BdaJobStatus.CLIENT_ERROR])
def test_failed_when_bda_reported_error(
    mock_env, ddb_doc_metadata_table, create_stale_record, mocker, bda_status
):
    create_stale_record("file.pdf", ProcessStatus.STARTED, BDA_INVOCATION_ARN)
    mocker.patch(
        "documentai_api.jobs.document_reaper.main.get_bda_job_response",
        return_value={"status": bda_status},
    )

    result = main()

    assert result["outcomes"][ProcessStatus.FAILED] == 1
    record = _get_record(ddb_doc_metadata_table, "file.pdf")
    assert record[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.FAILED
    assert bda_status in record[DocumentMetadata.ERROR_MESSAGE]


def test_skipped_when_bda_still_in_progress(mock_env, create_stale_record, mocker):
    create_stale_record("file.pdf", ProcessStatus.STARTED, BDA_INVOCATION_ARN)
    mocker.patch(
        "documentai_api.jobs.document_reaper.main.get_bda_job_response",
        return_value={"status": BdaJobStatus.IN_PROGRESS},
    )

    result = main()

    assert result["staleRecordsFound"] == 1
    assert result["outcomes"] == {}


def test_fresh_records_not_reaped(mock_env, ddb_doc_metadata_table):
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "fresh.pdf",
            DocumentMetadata.PROCESS_STATUS: ProcessStatus.STARTED,
            DocumentMetadata.CREATED_AT: FRESH_CREATED_AT,
        }
    )

    result = main()

    assert result["staleRecordsFound"] == 0
    assert (
        _get_record(ddb_doc_metadata_table, "fresh.pdf")[DocumentMetadata.PROCESS_STATUS]
        == ProcessStatus.STARTED
    )


def test_multiple_records_mixed_outcomes(
    mock_env, ddb_doc_metadata_table, create_stale_record, mocker
):
    create_stale_record("no-arn.pdf", ProcessStatus.STARTED)
    create_stale_record("bda-done.pdf", ProcessStatus.PENDING_UPLOAD, BDA_INVOCATION_ARN)
    create_stale_record("in-progress.pdf", ProcessStatus.STARTED, BDA_INVOCATION_ARN_2)

    def bda_side_effect(arn):
        if arn == BDA_INVOCATION_ARN:
            return {"status": BdaJobStatus.SUCCESS}
        return {"status": BdaJobStatus.IN_PROGRESS}

    mocker.patch(
        "documentai_api.jobs.document_reaper.main.get_bda_job_response",
        side_effect=bda_side_effect,
    )

    result = main()

    assert result["staleRecordsFound"] == 3
    assert result["outcomes"][ProcessStatus.TIMED_OUT] == 1
    assert result["outcomes"][ProcessStatus.FAILED] == 1
    assert ProcessStatus.STARTED not in result["outcomes"]


def test_reap_error_counted(mock_env, ddb_doc_metadata_table, create_stale_record, mocker):
    create_stale_record("file.pdf", ProcessStatus.STARTED, BDA_INVOCATION_ARN)
    mocker.patch(
        "documentai_api.jobs.document_reaper.main.get_bda_job_response",
        side_effect=Exception,
    )

    result = main()

    assert result["outcomes"].get("error") == 1


def test_pipeline_race_not_clobbered(mock_env, ddb_doc_metadata_table, create_stale_record):
    """Pipeline completing a record between GSI read and reaper write must not be clobbered."""
    create_stale_record("file.pdf", ProcessStatus.STARTED)

    # Simulate pipeline winning the race by updating to SUCCESS before reaper writes
    ddb_doc_metadata_table.update_item(
        Key={DocumentMetadata.FILE_NAME: "file.pdf"},
        UpdateExpression=f"SET {DocumentMetadata.PROCESS_STATUS} = :s",
        ExpressionAttributeValues={":s": ProcessStatus.SUCCESS},
    )

    result = main()

    assert result["outcomes"] == {}
    assert (
        _get_record(ddb_doc_metadata_table, "file.pdf")[DocumentMetadata.PROCESS_STATUS]
        == ProcessStatus.SUCCESS
    )
