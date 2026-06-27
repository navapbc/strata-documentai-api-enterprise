"""Tests for Lambda handler error handling - DDB marked as failed on unhandled errors."""

from unittest.mock import patch

import pytest

from documentai_api.config.constants import ProcessStatus
from documentai_api.config.env import EnvVars
from documentai_api.jobs.bda_result_processor.handler import handler as bda_handler
from documentai_api.jobs.document_processor.handler import handler as doc_handler
from documentai_api.schemas.document_metadata import DocumentMetadata

EVENTBRIDGE_S3_EVENT = {
    "detail": {
        "bucket": {"name": "test-bucket"},
        "object": {"key": "input/test-tenant/doc.pdf"},
    }
}

BDA_INVOCATION_ID = "de8464af-d53e-44dc-a9f7-ad5360530210"
BDA_EVENT = {
    "detail": {
        "bucket": {"name": "output-bucket"},
        "object": {
            "key": f"processed/input/test-tenant/doc.pdf/{BDA_INVOCATION_ID}/0/custom_output/job_metadata.json"
        },
    }
}
BDA_DDB_FILE_NAME = "input/test-tenant/doc.pdf"


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME, "metadata")
    monkeypatch.setenv(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_JOB_ID_INDEX_NAME, "job-id-index")
    monkeypatch.setenv(
        EnvVars.DOCUMENTAI_DOCUMENT_METADATA_BDA_INVOCATION_ID_INDEX_NAME, "bda-inv-index"
    )
    monkeypatch.setenv(EnvVars.DOCUMENTAI_INPUT_LOCATION, "s3://test-bucket/input")
    monkeypatch.setenv(EnvVars.DOCUMENTAI_OUTPUT_LOCATION, "s3://test-bucket/output")
    monkeypatch.setenv(EnvVars.BDA_PROJECT_ARN, "arn:aws:test")
    monkeypatch.setenv(EnvVars.BDA_PROFILE_ARN, "arn:aws:test")
    monkeypatch.setenv(EnvVars.BDA_REGION, "us-east-1")


##############################################################################
# Unit tests - verify handler wiring
##############################################################################


def test_document_processor_marks_failed_on_error():
    with (
        patch(
            "documentai_api.jobs.document_processor.handler.main",
            side_effect=RuntimeError("boom"),
        ),
        patch("documentai_api.jobs.document_processor.handler.classify_as_failed") as mock_fail,
    ):
        result = doc_handler(EVENTBRIDGE_S3_EVENT, None)

        assert result["statusCode"] == 500
        mock_fail.assert_called_once()
        call_kwargs = mock_fail.call_args.kwargs
        assert call_kwargs["object_key"] == "doc.pdf"
        assert "boom" in call_kwargs["error_message"]


def test_bda_result_processor_marks_failed_on_error():
    with (
        patch(
            "documentai_api.jobs.bda_result_processor.handler.main",
            side_effect=RuntimeError("bda crash"),
        ),
        patch(
            "documentai_api.jobs.bda_result_processor.handler.get_ddb_key_from_bda_output",
            return_value=BDA_DDB_FILE_NAME,
        ),
        patch("documentai_api.jobs.bda_result_processor.handler.classify_as_failed") as mock_fail,
    ):
        result = bda_handler(BDA_EVENT, None)

        assert result["statusCode"] == 500
        mock_fail.assert_called_once()
        call_kwargs = mock_fail.call_args.kwargs
        assert call_kwargs["object_key"] == BDA_DDB_FILE_NAME
        assert "bda crash" in call_kwargs["error_message"]


def test_document_processor_success_does_not_mark_failed():
    with (
        patch("documentai_api.jobs.document_processor.handler.main") as mock_main,
        patch("documentai_api.jobs.document_processor.handler.classify_as_failed") as mock_fail,
    ):
        result = doc_handler(EVENTBRIDGE_S3_EVENT, None)

        mock_main.assert_called_once()
        mock_fail.assert_not_called()
        assert result == {"statusCode": 200}


def test_bda_result_processor_success_does_not_mark_failed():
    with (
        patch("documentai_api.jobs.bda_result_processor.handler.main") as mock_main,
        patch("documentai_api.jobs.bda_result_processor.handler.classify_as_failed") as mock_fail,
    ):
        result = bda_handler(BDA_EVENT, None)

        mock_main.assert_called_once()
        mock_fail.assert_not_called()
        assert result == {"statusCode": 200}


##############################################################################
# Integration tests - verify DDB actually updated to FAILED
##############################################################################


def test_document_processor_updates_ddb_to_failed(ddb_doc_metadata_table):
    """Integration: handler error → DDB record marked as FAILED."""
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "doc.pdf",
            DocumentMetadata.PROCESS_STATUS: ProcessStatus.NOT_STARTED.value,
        }
    )

    with patch(
        "documentai_api.jobs.document_processor.handler.main",
        side_effect=RuntimeError("integration boom"),
    ):
        result = doc_handler(EVENTBRIDGE_S3_EVENT, None)

    assert result["statusCode"] == 500

    record = ddb_doc_metadata_table.get_item(Key={"fileName": "doc.pdf"})["Item"]
    assert record[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.FAILED.value
    assert "integration boom" in record.get(DocumentMetadata.ERROR_MESSAGE, "")


@pytest.mark.parametrize(
    "initial_status",
    [
        ProcessStatus.NOT_STARTED.value,
        ProcessStatus.STARTED.value,
    ],
)
def test_bda_result_processor_updates_ddb_to_failed(initial_status, ddb_doc_metadata_table):
    """Integration: BDA handler error → DDB record marked as FAILED via invocation ID lookup."""
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: BDA_DDB_FILE_NAME,
            DocumentMetadata.BDA_INVOCATION_ID: BDA_INVOCATION_ID,
            DocumentMetadata.PROCESS_STATUS: initial_status,
        }
    )

    with patch(
        "documentai_api.jobs.bda_result_processor.handler.main",
        side_effect=RuntimeError("bda integration crash"),
    ):
        result = bda_handler(BDA_EVENT, None)

    assert result["statusCode"] == 500

    record = ddb_doc_metadata_table.get_item(Key={"fileName": BDA_DDB_FILE_NAME})["Item"]
    assert record[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.FAILED.value
    assert "bda integration crash" in record.get(DocumentMetadata.ERROR_MESSAGE, "")


def test_bda_result_processor_returns_500_when_ddb_key_unresolvable():
    """If get_ddb_key_from_bda_output returns None, handler still returns 500."""
    with (
        patch(
            "documentai_api.jobs.bda_result_processor.handler.main",
            side_effect=RuntimeError("crash"),
        ),
        patch(
            "documentai_api.jobs.bda_result_processor.handler.get_ddb_key_from_bda_output",
            return_value=None,
        ),
        patch("documentai_api.jobs.bda_result_processor.handler.classify_as_failed") as mock_fail,
    ):
        result = bda_handler(BDA_EVENT, None)

        assert result["statusCode"] == 500
        mock_fail.assert_not_called()


def test_handler_returns_500_with_original_error_when_classify_fails():
    """If classify_as_failed throws, the original error still surfaces."""
    with (
        patch(
            "documentai_api.jobs.document_processor.handler.main",
            side_effect=RuntimeError("original error"),
        ),
        patch(
            "documentai_api.jobs.document_processor.handler.classify_as_failed",
            side_effect=RuntimeError("ddb update failed"),
        ),
    ):
        result = doc_handler(EVENTBRIDGE_S3_EVENT, None)

    assert result["statusCode"] == 500
    # Original error surfaces, not the cascading DDB failure
    assert "original error" in result["body"]


def test_malformed_event_returns_500_without_ddb_update():
    """Malformed event → extract_s3_info_from_event raises before try/except."""
    bad_event = {"garbage": "data"}

    with patch("documentai_api.jobs.document_processor.handler.classify_as_failed") as mock_fail:
        result = doc_handler(bad_event, None)

    assert result["statusCode"] == 500
    mock_fail.assert_not_called()


##############################################################################
# Cold start lifecycle toggle
##############################################################################


def test_document_processor_cold_start_toggle():
    """First handler() passes is_cold_start=True to main, second passes False."""
    from documentai_api.jobs.document_processor import handler as handler_mod

    # Reset module-level state to simulate fresh container
    handler_mod.lifecycle["is_cold_start"] = True

    with patch("documentai_api.jobs.document_processor.handler.main") as mock_main:
        doc_handler(EVENTBRIDGE_S3_EVENT, None)
        assert mock_main.call_args.kwargs["is_cold_start"] is True

        doc_handler(EVENTBRIDGE_S3_EVENT, None)
        assert mock_main.call_args.kwargs["is_cold_start"] is False

        # Third call still False
        doc_handler(EVENTBRIDGE_S3_EVENT, None)
        assert mock_main.call_args.kwargs["is_cold_start"] is False
