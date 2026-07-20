"""Tests for usage_report job."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from moto import mock_aws

from documentai_api.config.constants import METRICS_USAGE_REPORT_S3_PREFIX
from documentai_api.jobs.usage_report.handler import handler
from documentai_api.jobs.usage_report.main import (
    _build_daily_usage_query,
    generate_daily_usage,
    generate_usage_report,
    main,
)


def test_build_daily_usage_query_structure():
    """Test SQL query contains expected structural elements.

    NOTE: SQL aggregation correctness (LEAST cap, NULL filtering, token summing,
    dedup) is not unit-testable without a real Athena engine. This test only
    verifies structural integrity. Correctness is currently verified via manual
    runs (make usage-report MONTH=... against a deployed environment).
    """
    query = _build_daily_usage_query("test_db", "test_table", "2026-06")

    # Table reference
    assert "test_db.test_table" in query
    # Month range with correct last day
    assert "2026-06-01" in query
    assert "2026-06-30" in query
    # Deduplication
    assert "ROW_NUMBER() OVER" in query
    assert "PARTITION BY file_name" in query
    # Grouped by date
    assert "GROUP BY" in query
    assert "date" in query
    # BDA pages tracked directly (not derived from pages_detected)
    assert "pages_sent_to_bda" in query
    # Both token sources included
    assert "preclassification_input_tokens" in query
    assert "crop_input_tokens" in query
    assert "preclassification_output_tokens" in query
    assert "crop_output_tokens" in query


def test_build_daily_usage_query_february():
    """February uses correct last day (28 or 29), not 31."""
    query = _build_daily_usage_query("db", "tbl", "2026-02")
    assert "2026-02-28" in query
    assert "2026-02-31" not in query

    # Leap year
    query = _build_daily_usage_query("db", "tbl", "2024-02")
    assert "2024-02-29" in query


def test_build_daily_usage_query_current_month_excludes_today():
    """Current month query stops at yesterday to avoid double-counting with live augmentation."""
    from freezegun import freeze_time

    with freeze_time("2026-07-15 12:00:00", tz_offset=0):
        query = _build_daily_usage_query("db", "tbl", "2026-07")

    # Should end at yesterday (July 14), not today or month-end
    assert "2026-07-14" in query
    assert "2026-07-15" not in query
    assert "2026-07-31" not in query


def test_build_daily_usage_query_past_month_includes_full_range():
    """Past month query includes the full month regardless of today."""
    query = _build_daily_usage_query("db", "tbl", "2026-06")
    assert "2026-06-01" in query
    assert "2026-06-30" in query


@pytest.mark.parametrize("invalid_month", ["2026-1", "junk", "2026-06-01"])
def test_generate_daily_usage_invalid_month(invalid_month):
    """Test that an invalid month format raises ValueError."""
    with pytest.raises(ValueError, match="Invalid month format"):
        generate_daily_usage(invalid_month)


def test_generate_usage_report_happy_path():
    """Test generate_usage_report sums daily data into tenant totals."""
    daily_data = {
        "2026-06-15": [
            {
                "tenant_id": "tenant-a",
                "total_records": 30,
                "total_bda_invocations": 25,
                "total_file_size_bytes": 600000,
                "total_bda_pages": 25,
                "total_bedrock_input_tokens": 3000,
                "total_bedrock_output_tokens": 120,
            },
            {
                "tenant_id": "tenant-b",
                "total_records": 10,
                "total_bda_invocations": 10,
                "total_file_size_bytes": 500000,
                "total_bda_pages": 10,
                "total_bedrock_input_tokens": 1000,
                "total_bedrock_output_tokens": 50,
            },
        ],
        "2026-06-16": [
            {
                "tenant_id": "tenant-a",
                "total_records": 20,
                "total_bda_invocations": 20,
                "total_file_size_bytes": 400000,
                "total_bda_pages": 20,
                "total_bedrock_input_tokens": 2000,
                "total_bedrock_output_tokens": 80,
            },
        ],
    }

    result = generate_usage_report("2026-06", daily_data)

    assert result["month"] == "2026-06"
    assert result["report_type"] == "usage_only"
    assert len(result["tenants"]) == 2

    # Sorted by total_records desc
    tenant_a = result["tenants"][0]
    assert tenant_a["tenant_id"] == "tenant-a"
    assert tenant_a["total_records"] == 50  # 30 + 20
    assert tenant_a["total_bda_invocations"] == 45
    assert tenant_a["total_file_size_bytes"] == 1000000
    assert tenant_a["total_bda_pages"] == 45
    assert tenant_a["total_bedrock_input_tokens"] == 5000
    assert tenant_a["total_bedrock_output_tokens"] == 200

    tenant_b = result["tenants"][1]
    assert tenant_b["tenant_id"] == "tenant-b"
    assert tenant_b["total_records"] == 10


def test_generate_usage_report_empty_result():
    """Test generate_usage_report returns message when no data found."""
    result = generate_usage_report("2026-06", {})

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
        generate_daily_usage("2026-06")


@mock_aws
def test_main_writes_to_s3(s3_client, s3_bucket, monkeypatch):
    """Test main writes monthly and daily reports to the correct S3 keys."""
    monkeypatch.setenv("GLUE_DATABASE_NAME", "test_db")
    monkeypatch.setenv("DDB_RAW_DATA_TABLE_NAME", "test_table")
    monkeypatch.setenv("ATHENA_WORKGROUP_NAME", "test_workgroup")
    monkeypatch.setenv("DDB_EXPORT_BUCKET_NAME", "test-bucket")

    daily_rows = [
        {
            "date": "2026-06-15",
            "tenant_id": "tenant-a",
            "total_records": "3",
            "total_bda_invocations": "3",
            "total_file_size_bytes": "60000",
            "total_bda_pages": "3",
            "total_bedrock_input_tokens": "300",
            "total_bedrock_output_tokens": "12",
        },
        {
            "date": "2026-06-16",
            "tenant_id": "tenant-a",
            "total_records": "2",
            "total_bda_invocations": "2",
            "total_file_size_bytes": "40000",
            "total_bda_pages": "2",
            "total_bedrock_input_tokens": "200",
            "total_bedrock_output_tokens": "8",
        },
    ]

    with patch(
        "documentai_api.jobs.usage_report.main._execute_query",
        return_value=daily_rows,
    ):
        result = main("2026-06")

    assert result["statusCode"] == 200
    assert result["month"] == "2026-06"
    assert result["tenant_count"] == 1
    assert result["daily_days"] == 2
    assert f"{METRICS_USAGE_REPORT_S3_PREFIX}=2026-06/report.json" in result["output_location"]

    # Verify monthly S3 content (derived from daily sums)
    obj = s3_client.get_object(
        Bucket="test-bucket", Key=f"{METRICS_USAGE_REPORT_S3_PREFIX}=2026-06/report.json"
    )
    report = json.loads(obj["Body"].read().decode())
    assert report["month"] == "2026-06"
    assert len(report["tenants"]) == 1
    assert report["tenants"][0]["tenant_id"] == "tenant-a"
    assert report["tenants"][0]["total_records"] == 5  # 3 + 2

    # Verify daily S3 content
    from documentai_api.config.constants import METRICS_USAGE_REPORT_DAILY_S3_PREFIX

    obj = s3_client.get_object(
        Bucket="test-bucket",
        Key=f"{METRICS_USAGE_REPORT_DAILY_S3_PREFIX}=2026-06-15/tenant=tenant-a/stats.json",
    )
    daily_stat = json.loads(obj["Body"].read().decode())
    assert daily_stat["total_records"] == 3

    # Global daily file sums across tenants
    obj = s3_client.get_object(
        Bucket="test-bucket",
        Key=f"{METRICS_USAGE_REPORT_DAILY_S3_PREFIX}=2026-06-15/stats.json",
    )
    global_stat = json.loads(obj["Body"].read().decode())
    assert global_stat["total_records"] == 3


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
