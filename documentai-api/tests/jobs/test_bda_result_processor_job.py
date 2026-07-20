"""Tests for jobs/bda_result_processor/main.py."""

import pytest

from documentai_api.jobs.bda_result_processor.main import main


@pytest.fixture(autouse=True)
def mock_env(runtime_required_env):
    pass


def test_main_success(s3_bucket, mocker):
    """Test successful BDA output processing."""
    mock_process = mocker.patch("documentai_api.jobs.bda_result_processor.main.process_bda_output")
    mock_process.return_value = {"status": "success", "data": {"field1": "value1"}}

    result = main(s3_bucket.name, "output/input/test-file.pdf/job_metadata.json")

    assert result == {"status": "success", "data": {"field1": "value1"}}
    mock_process.assert_called_once_with(
        "test-bucket",
        "output/input/test-file.pdf/job_metadata.json",
        result_processor_started_at=None,
    )


def test_main_with_truncated_filename(s3_bucket, mocker):
    """Test processing BDA output with truncated filename."""
    mock_process = mocker.patch("documentai_api.jobs.bda_result_processor.main.process_bda_output")
    mock_process.return_value = {"status": "success"}

    main(s3_bucket.name, "output/input/long_truncated.pdf/job_metadata.json")

    mock_process.assert_called_once_with(
        "test-bucket",
        "output/input/long_truncated.pdf/job_metadata.json",
        result_processor_started_at=None,
    )


def test_main_skips_non_metadata_files(s3_bucket, mocker):
    """Test that non-metadata files are skipped."""
    mock_process = mocker.patch("documentai_api.jobs.bda_result_processor.main.process_bda_output")

    result = main(s3_bucket.name, "output/input/test-file.pdf/.s3_access_check")

    assert result == {}
    mock_process.assert_not_called()
