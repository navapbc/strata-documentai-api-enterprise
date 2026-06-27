"""Tests for usage_report job."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from moto import mock_aws

from documentai_api.config.constants import METRICS_USAGE_REPORT_S3_PREFIX
from documentai_api.jobs.usage_report.handler import handler
from documentai_api.jobs.usage_report.main import (
    _build_usage_query,
    generate_usage_report,
    main,
)


def test_build_usage_query_structure():
    """Test SQL query contains expected structural elements.

    NOTE: SQL aggregation correctness (LEAST cap, NULL filtering, token summing,
    dedup) is not unit-testable without a real Athena engine. This test only
    verifies structural integrity. Correctness is currently verified via manual
    runs (make usage-report MONTH=... against a deployed environment).
    """
    query = _build_usage_query("test_db", "test_table", "2026-06")

    # Table reference
    assert "test_db.test_table" in query
    # Month range partition pruning
    assert "2026-06" in query
    # Deduplication
    assert "ROW_NUMBER() OVER" in query
    assert "PARTITION BY file_name" in query
    # BDA pages tracked directly (not derived from pages_detected)
    assert "pages_sent_to_bda" in query
    # Both token sources included
    assert "preclassification_input_tokens" in query
    assert "crop_input_tokens" in query
    assert "preclassification_output_tokens" in query
    assert "crop_output_tokens" in query


def test_generate_usage_report_invalid_month():
    """Test that an invalid month format raises ValueError."""
    with pytest.raises(ValueError, match="Invalid month format"):
        generate_usage_report("2026-1")

    with pytest.raises(ValueError, match="Invalid month format"):
        generate_usage_report("junk")

    with pytest.raises(ValueError, match="Invalid month format"):
        generate_usage_report("2026-06-01")


def test_generate_usage_report_happy_path(monkeypatch):
    """Test generate_usage_report maps Athena rows to tenant dicts."""
    monkeypatch.setenv("GLUE_DATABASE_NAME", "test_db")
    monkeypatch.setenv("DDB_RAW_DATA_TABLE_NAME", "test_table")
    monkeypatch.setenv("ATHENA_WORKGROUP_NAME", "test_workgroup")
    monkeypatch.setenv("DDB_EXPORT_BUCKET_NAME", "test-bucket")

    mock_rows = [
        {
            "tenant_id": "tenant-a",
            "total_records": "50",
            "total_bda_invocations": "45",
            "total_file_size_bytes": "1000000",
            "total_bda_pages": "45",
            "total_bedrock_input_tokens": "5000",
            "total_bedrock_output_tokens": "200",
        },
        {
            "tenant_id": "tenant-b",
            "total_records": "10",
            "total_bda_invocations": "10",
            "total_file_size_bytes": "500000",
            "total_bda_pages": "10",
            "total_bedrock_input_tokens": "1000",
            "total_bedrock_output_tokens": "50",
        },
    ]

    with patch("documentai_api.jobs.usage_report.main._execute_query", return_value=mock_rows):
        result = generate_usage_report("2026-06")

    assert result["month"] == "2026-06"
    assert result["report_type"] == "usage_only"
    assert len(result["tenants"]) == 2

    tenant_a = result["tenants"][0]
    assert tenant_a["tenant_id"] == "tenant-a"
    assert tenant_a["total_records"] == 50
    assert tenant_a["total_bda_invocations"] == 45
    assert tenant_a["total_file_size_bytes"] == 1000000
    assert tenant_a["total_bda_pages"] == 45
    assert tenant_a["total_bedrock_input_tokens"] == 5000
    assert tenant_a["total_bedrock_output_tokens"] == 200


def test_generate_usage_report_empty_result(monkeypatch):
    """Test generate_usage_report returns message when no data found."""
    monkeypatch.setenv("GLUE_DATABASE_NAME", "test_db")
    monkeypatch.setenv("DDB_RAW_DATA_TABLE_NAME", "test_table")
    monkeypatch.setenv("ATHENA_WORKGROUP_NAME", "test_workgroup")
    monkeypatch.setenv("DDB_EXPORT_BUCKET_NAME", "test-bucket")

    with patch("documentai_api.jobs.usage_report.main._execute_query", return_value=[]):
        result = generate_usage_report("2026-06")

    assert result["month"] == "2026-06"
    assert result["tenants"] == []
    assert result["message"] == "No data found"


def test_generate_usage_report_missing_env(monkeypatch):
    """Test generate_usage_report raises when env vars are missing."""
    monkeypatch.delenv("GLUE_DATABASE_NAME", raising=False)
    monkeypatch.delenv("DDB_RAW_DATA_TABLE_NAME", raising=False)
    monkeypatch.delenv("ATHENA_WORKGROUP_NAME", raising=False)
    monkeypatch.setenv("DDB_EXPORT_BUCKET_NAME", "test-bucket")

    with pytest.raises(ValueError, match="GLUE_DATABASE_NAME"):
        generate_usage_report("2026-06")


@mock_aws
def test_main_writes_to_s3(s3_client, s3_bucket, monkeypatch):
    """Test main writes the report to the correct S3 key."""
    monkeypatch.setenv("GLUE_DATABASE_NAME", "test_db")
    monkeypatch.setenv("DDB_RAW_DATA_TABLE_NAME", "test_table")
    monkeypatch.setenv("ATHENA_WORKGROUP_NAME", "test_workgroup")
    monkeypatch.setenv("DDB_EXPORT_BUCKET_NAME", "test-bucket")

    mock_rows = [
        {
            "tenant_id": "tenant-a",
            "total_records": "5",
            "total_bda_invocations": "5",
            "total_file_size_bytes": "100000",
            "total_bda_pages": "5",
            "total_bedrock_input_tokens": "500",
            "total_bedrock_output_tokens": "20",
        },
    ]

    with patch("documentai_api.jobs.usage_report.main._execute_query", return_value=mock_rows):
        result = main("2026-06")

    assert result["statusCode"] == 200
    assert result["month"] == "2026-06"
    assert result["tenant_count"] == 1
    assert f"{METRICS_USAGE_REPORT_S3_PREFIX}=2026-06/report.json" in result["output_location"]

    # Verify S3 content
    obj = s3_client.get_object(
        Bucket="test-bucket", Key=f"{METRICS_USAGE_REPORT_S3_PREFIX}=2026-06/report.json"
    )
    report = json.loads(obj["Body"].read().decode())
    assert report["month"] == "2026-06"
    assert len(report["tenants"]) == 1
    assert report["tenants"][0]["tenant_id"] == "tenant-a"


def test_handler_current_month(monkeypatch):
    """Test handler resolves 'current' to the current UTC month."""
    monkeypatch.setenv("GLUE_DATABASE_NAME", "test_db")
    monkeypatch.setenv("DDB_RAW_DATA_TABLE_NAME", "test_table")
    monkeypatch.setenv("ATHENA_WORKGROUP_NAME", "test_workgroup")
    monkeypatch.setenv("DDB_EXPORT_BUCKET_NAME", "test-bucket")

    expected_month = datetime.now(UTC).strftime("%Y-%m")

    with patch("documentai_api.jobs.usage_report.handler.main") as mock_main:
        mock_main.return_value = {"statusCode": 200, "month": expected_month}
        handler({"month": "current"}, None)
        mock_main.assert_called_once_with(expected_month)


def test_handler_previous_month(monkeypatch):
    """Test handler resolves 'previous' to the previous UTC month."""
    monkeypatch.setenv("GLUE_DATABASE_NAME", "test_db")
    monkeypatch.setenv("DDB_RAW_DATA_TABLE_NAME", "test_table")
    monkeypatch.setenv("ATHENA_WORKGROUP_NAME", "test_workgroup")
    monkeypatch.setenv("DDB_EXPORT_BUCKET_NAME", "test-bucket")

    first_of_month = datetime.now(UTC).replace(day=1)
    expected_month = (first_of_month - timedelta(days=1)).strftime("%Y-%m")

    with patch("documentai_api.jobs.usage_report.handler.main") as mock_main:
        mock_main.return_value = {"statusCode": 200, "month": expected_month}
        handler({"month": "previous"}, None)
        mock_main.assert_called_once_with(expected_month)


def test_handler_explicit_month(monkeypatch):
    """Test handler passes explicit YYYY-MM through unchanged."""
    monkeypatch.setenv("GLUE_DATABASE_NAME", "test_db")
    monkeypatch.setenv("DDB_RAW_DATA_TABLE_NAME", "test_table")
    monkeypatch.setenv("ATHENA_WORKGROUP_NAME", "test_workgroup")
    monkeypatch.setenv("DDB_EXPORT_BUCKET_NAME", "test-bucket")

    with patch("documentai_api.jobs.usage_report.handler.main") as mock_main:
        mock_main.return_value = {"statusCode": 200, "month": "2026-03"}
        handler({"month": "2026-03"}, None)
        mock_main.assert_called_once_with("2026-03")


def test_handler_missing_month():
    """Test handler returns error when month is not provided."""
    result = handler({}, None)
    assert result["statusCode"] == 500
    assert "month" in result["body"]
