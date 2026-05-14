"""Tests for metrics_aggregator."""

import json
from unittest.mock import patch

import pytest
from moto import mock_aws

from documentai_api.config.constants import (
    S3_AGG_DDB_DATA_DAILY_PREFIX,
    S3_AGG_DDB_DATA_MONTHLY_PREFIX,
)
from documentai_api.jobs.metrics_aggregator.main import (
    _aggregate_records,
    _build_deduplication_query,
    _check_if_previously_aggregated,
    _write_aggregated_stats,
    main,
)


def create_record(
    status="success",
    created_at="2026-02-20T10:00:00Z",
    classification="W2",
    total_time=None,
    bda_time=None,
):
    """Factory function to create test records with defaults."""
    record = {
        "file_name": "test.pdf",
        "process_status": status,
        "created_at": created_at,
        "bda_matched_document_class": classification,
    }
    if total_time:
        record["total_processing_time_seconds"] = str(total_time)
    if bda_time:
        record["bda_processing_time_seconds"] = str(bda_time)
    return record


def create_daily_stats(s3_client, date, total_records=5):
    """Factory function to create daily stats in S3."""
    bda_wait_time_avg = 2.4
    bda_processing_time_avg = 30.0
    total_processing_time_avg = bda_wait_time_avg + bda_processing_time_avg

    stats = {
        "date": date,
        "total_records": total_records,
        "total_bda_invocations": total_records - 2,
        "by_status": {"success": total_records - 1, "failed": 1},
        "by_classification": {"W2": total_records},
        "by_response_code": {"200": total_records},
        "by_hour": {"10": total_records},
        "timing_stats": {
            "total_processing_time_avg": total_processing_time_avg,
            "total_processing_time_sum": total_processing_time_avg * total_records,
            "total_processing_time_count": total_records,
            "bda_processing_time_avg": bda_processing_time_avg,
            "bda_processing_time_sum": bda_processing_time_avg * total_records,
            "bda_processing_time_count": total_records,
            "bda_wait_time_avg": bda_wait_time_avg,
            "bda_wait_time_sum": bda_wait_time_avg * total_records,
            "bda_wait_time_count": total_records,
        },
    }

    s3_client.put_object(
        Bucket="test-bucket",
        Key=f"{S3_AGG_DDB_DATA_DAILY_PREFIX}={date}/stats.json",
        Body=json.dumps(stats),
    )
    return stats


def create_aggregated_stats(date="2026-02-20", total_records=10):
    """Factory function to create aggregated stats structure."""
    bda_wait_time_avg = 2.4
    bda_processing_time_avg = 30.0
    total_processing_time_avg = bda_wait_time_avg + bda_processing_time_avg

    return {
        "date": date,
        "total_records": total_records,
        "total_bda_invocations": total_records - 2,
        "by_status": {"success": total_records - 2, "failed": 2},
        "by_classification": {"W2": total_records},
        "by_response_code": {"000": total_records},
        "by_hour": {"10": total_records},
        "timing_stats": {
            "total_processing_time_avg": total_processing_time_avg,
            "total_processing_time_sum": total_processing_time_avg * total_records,
            "total_processing_time_count": total_records,
            "bda_processing_time_avg": bda_processing_time_avg,
            "bda_processing_time_sum": bda_processing_time_avg * total_records,
            "bda_processing_time_count": total_records,
            "bda_wait_time_avg": bda_wait_time_avg,
            "bda_wait_time_sum": bda_wait_time_avg * total_records,
            "bda_wait_time_count": total_records,
        },
    }


def test_build_deduplication_query():
    """Test SQL query generation."""
    query = _build_deduplication_query("test_db", "test_table", "2026-02-20")

    assert "test_db.test_table" in query
    assert "date = '2026-02-20'" in query
    assert "ROW_NUMBER() OVER" in query
    assert "PARTITION BY file_name" in query
    assert "ORDER BY updated_at DESC" in query
    assert "WHERE rn = 1" in query


def test_aggregate_records_empty():
    """Test aggregation with no records returns zeroed stats structure."""
    stats = _aggregate_records([], "2026-02-20")

    assert stats["date"] == "2026-02-20"
    assert stats["total_records"] == 0
    assert stats["by_status"] == {}
    assert stats["by_hour"] == {}
    assert stats["by_classification"] == {}
    assert stats["by_response_code"] == {}
    assert stats["timing_stats"] == {
        "total_processing_time_avg": 0,
        "total_processing_time_sum": 0,
        "total_processing_time_count": 0,
        "bda_processing_time_avg": 0,
        "bda_processing_time_sum": 0,
        "bda_processing_time_count": 0,
        "bda_wait_time_avg": 0,
        "bda_wait_time_sum": 0,
        "bda_wait_time_count": 0,
    }


def test_main_no_records_skips_write(s3_client, s3_bucket, mock_metrics_aggregator_env):
    """Test that main skips writing stats when Athena returns zero records."""
    mock_results = mock_metrics_aggregator_env["mock_results"]
    mock_results.return_value = []

    result = main("2026-02-20", overwrite=True)

    assert result["statusCode"] == 200
    assert result["recordsProcessed"] == 0
    assert result["message"] == "No records found, skipping aggregation"

    # verify no stats file was written to S3
    objects = s3_client.list_objects_v2(Bucket="test-bucket")
    assert objects.get("KeyCount", 0) == 0


def test_aggregate_records_single_record():
    """Test aggregation with one record."""
    record = create_record(
        status="success",
        created_at="2026-02-20T10:30:00Z",
        classification="W2",
        total_time=5.5,
        bda_time=3.2,
    )

    stats = _aggregate_records([record], "2026-02-20")

    assert stats["total_records"] == 1
    assert stats["by_status"]["success"] == 1
    assert stats["by_hour"]["10"] == 1
    assert stats["by_classification"]["W2"] == 1
    assert stats["timing_stats"]["total_processing_time_sum"] == 5.5
    assert stats["timing_stats"]["total_processing_time_count"] == 1
    assert stats["timing_stats"]["bda_processing_time_sum"] == 3.2
    assert stats["timing_stats"]["bda_processing_time_count"] == 1


def test_aggregate_records_multiple_records():
    """Test aggregation with multiple records."""
    records = [
        create_record(status="success", created_at="2026-02-20T10:00:00Z", total_time=5.0),
        create_record(status="success", created_at="2026-02-20T10:30:00Z", total_time=3.0),
        create_record(status="failed", created_at="2026-02-20T11:00:00Z", classification="1099"),
    ]

    stats = _aggregate_records(records, "2026-02-20")

    assert stats["total_records"] == 3
    assert stats["by_status"]["success"] == 2
    assert stats["by_status"]["failed"] == 1
    assert stats["by_hour"]["10"] == 2
    assert stats["by_hour"]["11"] == 1
    assert stats["by_classification"]["W2"] == 2
    assert stats["by_classification"]["1099"] == 1
    assert stats["timing_stats"]["total_processing_time_sum"] == 8.0
    assert stats["timing_stats"]["total_processing_time_count"] == 2


def test_check_if_previously_aggregated(s3_client, s3_bucket):
    """Test checking for existing aggregation."""
    # create the aggregated stats file
    s3_client.put_object(
        Bucket="test-bucket",
        Key=f"{S3_AGG_DDB_DATA_DAILY_PREFIX}=2026-02-20/stats.json",
        Body=b'{"date": "2026-02-20"}',
    )

    result = _check_if_previously_aggregated("test-bucket", "2026-02-20")

    assert result is True


def test_check_if_previously_aggregated_not_exists(s3_client, s3_bucket):
    """Test checking for non-existent aggregation."""
    result = _check_if_previously_aggregated("test-bucket", "2026-02-20")

    assert result is False


def test_check_if_previously_aggregated_reraises_non_404(s3_client, s3_bucket):
    """Test that non-404 S3 errors are re-raised rather than swallowed."""
    from unittest.mock import MagicMock, patch

    from botocore.exceptions import ClientError

    error_response = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
    mock_s3 = MagicMock()
    mock_s3.head_object.side_effect = ClientError(error_response, "HeadObject")

    with (
        patch(
            "documentai_api.jobs.metrics_aggregator.main.AWSClientFactory.get_s3_client",
            return_value=mock_s3,
        ),
        pytest.raises(ClientError) as exc_info,
    ):
        _check_if_previously_aggregated("test-bucket", "2026-02-20")

    assert exc_info.value.response["Error"]["Code"] == "AccessDenied"


def test_write_aggregated_stats(s3_client, s3_bucket):
    """Test writing aggregated stats to S3."""
    stats = create_aggregated_stats()

    s3_key = _write_aggregated_stats("test-bucket", stats, "2026-02-20")

    assert s3_key == f"{S3_AGG_DDB_DATA_DAILY_PREFIX}=2026-02-20/stats.json"

    # verify file was written
    obj = s3_client.get_object(Bucket="test-bucket", Key=s3_key)
    content = obj["Body"].read().decode()
    assert "2026-02-20" in content
    assert "total_records" in content


def test_get_daily_stats_for_month_empty(s3_client, s3_bucket):
    """Test reading daily stats when none exist."""
    from documentai_api.jobs.metrics_aggregator.main import _get_daily_stats_for_month

    daily_stats = _get_daily_stats_for_month("test-bucket", "2026-02")

    assert daily_stats == []


def test_get_daily_stats_for_month_multiple_days(s3_client, s3_bucket):
    """Test reading daily stats for multiple days."""
    from documentai_api.jobs.metrics_aggregator.main import _get_daily_stats_for_month

    create_daily_stats(s3_client, "2026-02-01", total_records=10)
    create_daily_stats(s3_client, "2026-02-02", total_records=15)
    create_daily_stats(s3_client, "2026-02-03", total_records=12)

    daily_stats = _get_daily_stats_for_month("test-bucket", "2026-02")

    assert len(daily_stats) == 3
    assert all(stat["date"].startswith("2026-02") for stat in daily_stats)


def test_aggregate_monthly_no_daily_stats(s3_client, s3_bucket):
    """Test monthly aggregation when no daily stats exist."""
    from documentai_api.jobs.metrics_aggregator.main import _aggregate_monthly

    result = _aggregate_monthly("test-bucket", "2026-02")

    assert result is None


def test_aggregate_monthly_success(s3_client, s3_bucket):
    """Test successful monthly aggregation."""
    from documentai_api.jobs.metrics_aggregator.main import _aggregate_monthly

    create_daily_stats(s3_client, "2026-02-01", total_records=10)
    create_daily_stats(s3_client, "2026-02-02", total_records=15)
    create_daily_stats(s3_client, "2026-02-03", total_records=12)

    result = _aggregate_monthly("test-bucket", "2026-02")

    assert result is not None
    assert result["month"] == "2026-02"
    assert result["daysProcessed"] == 3
    assert "outputLocation" in result
    assert "month=2026-02" in result["outputLocation"]

    # verify monthly stats were written
    obj = s3_client.get_object(
        Bucket="test-bucket", Key=f"{S3_AGG_DDB_DATA_MONTHLY_PREFIX}=2026-02/stats.json"
    )
    monthly_stats = json.loads(obj["Body"].read().decode())

    assert monthly_stats["month"] == "2026-02"
    assert monthly_stats["total_records"] == 37  # 10 + 15 + 12
    assert monthly_stats["total_bda_invocations"] == 31  # (10-2) + (15-2) + (12-2)


def test_main_already_aggregated(s3_client, s3_bucket):
    """Test main skips daily aggregation when already aggregated but still returns stats."""
    existing_stats = create_aggregated_stats(date="2026-02-20", total_records=10)
    s3_client.put_object(
        Bucket="test-bucket",
        Key=f"{S3_AGG_DDB_DATA_DAILY_PREFIX}=2026-02-20/stats.json",
        Body=json.dumps(existing_stats).encode(),
    )

    with patch.dict("os.environ", {"DDB_EXPORT_BUCKET_NAME": "test-bucket"}):
        result = main("2026-02-20", overwrite=False)

    assert result["statusCode"] == 200
    assert result["message"] == "Already aggregated"
    assert "2026-02-20" in result["outputLocation"]
    assert result["recordsProcessed"] == 10
    assert "monthlyAggregations" in result


def test_main_already_aggregated_still_runs_monthly(
    s3_client, s3_bucket, mock_metrics_aggregator_env
):
    """Test monthly rollup still runs when daily aggregation is skipped."""
    # pre-existing daily stats for two days
    create_daily_stats(s3_client, "2026-02-19", total_records=8)
    create_daily_stats(s3_client, "2026-02-20", total_records=10)

    # mark the 20th as already aggregated with a full stats shape
    existing_stats = create_aggregated_stats(date="2026-02-20", total_records=10)
    s3_client.put_object(
        Bucket="test-bucket",
        Key=f"{S3_AGG_DDB_DATA_DAILY_PREFIX}=2026-02-20/stats.json",
        Body=json.dumps(existing_stats).encode(),
    )

    result = main("2026-02-20", overwrite=False)

    assert result["message"] == "Already aggregated"
    assert len(result["monthlyAggregations"]) == 1
    assert result["monthlyAggregations"][0]["month"] == "2026-02"
    assert result["monthlyAggregations"][0]["daysProcessed"] == 2


def test_get_athena_results_timeout():
    """Test that Athena polling raises after timeout rather than looping forever."""
    from unittest.mock import MagicMock, patch

    mock_athena = MagicMock()
    mock_athena.get_query_execution.return_value = {
        "QueryExecution": {"Status": {"State": "RUNNING"}}
    }

    with (
        patch(
            "documentai_api.jobs.metrics_aggregator.main.AWSClientFactory.get_athena_client",
            return_value=mock_athena,
        ),
        patch("documentai_api.jobs.metrics_aggregator.main.ATHENA_QUERY_TIMEOUT_SECONDS", 3),
        patch("documentai_api.jobs.metrics_aggregator.main.time.sleep"),
    ):
        from documentai_api.jobs.metrics_aggregator.main import _get_athena_results

        with pytest.raises(Exception, match="did not complete within"):
            _get_athena_results("fake-execution-id")


def test_process_record_logs_warning_for_invalid_timing(caplog):
    """Test that records with unparseable timing values emit warnings and skip those fields."""
    import logging

    from documentai_api.jobs.metrics_aggregator.main import _process_record

    record = {
        "file_name": "bad-record.pdf",
        "process_status": "success",
        "created_at": "2026-02-20T10:00:00Z",
        "total_processing_time_seconds": "not-a-number",
        "bda_processing_time_seconds": "also-bad",
        "bda_wait_time_seconds": "",
    }
    stats = {
        "total_records": 0,
        "by_status": {},
        "by_classification": {},
        "by_response_code": {},
        "by_hour": {},
        "timing_stats": {
            "total_processing_time_sum": 0,
            "total_processing_time_count": 0,
            "bda_processing_time_sum": 0,
            "bda_processing_time_count": 0,
            "bda_wait_time_sum": 0,
            "bda_wait_time_count": 0,
        },
    }

    with (
        patch.object(
            logging.getLogger("documentai_api.jobs.metrics_aggregator.main"), "propagate", True
        ),
        caplog.at_level(logging.WARNING, logger="documentai_api.jobs.metrics_aggregator.main"),
    ):
        _process_record(record, stats)

    warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("total_processing_time_seconds" in msg for msg in warning_messages)
    assert any("bda_processing_time_seconds" in msg for msg in warning_messages)
    assert stats["timing_stats"]["total_processing_time_count"] == 0
    assert stats["timing_stats"]["bda_processing_time_count"] == 0


@mock_aws
@pytest.mark.parametrize(
    ("overwrite", "should_skip"),
    [
        (False, True),  # normal run - skips aggregation if exists
        (True, False),  # overwrite - processes aggregation even if exists
    ],
)
def test_main_success(s3_client, s3_bucket, mock_metrics_aggregator_env, overwrite, should_skip):
    """Test successful aggregation with and without overwrite."""
    # create existing aggregation with full stats shape so _build_summary doesn't blow up
    existing_stats = create_aggregated_stats(date="2026-02-20", total_records=10)
    s3_client.put_object(
        Bucket="test-bucket",
        Key=f"{S3_AGG_DDB_DATA_DAILY_PREFIX}=2026-02-20/stats.json",
        Body=json.dumps(existing_stats).encode(),
    )

    mock_athena = mock_metrics_aggregator_env["mock_athena"]
    mock_results = mock_metrics_aggregator_env["mock_results"]
    mock_results.return_value = [
        {"process_status": "success", "created_at": "2026-02-20T10:00:00Z"}
    ]

    result = main("2026-02-20", overwrite=overwrite)

    if should_skip:
        # should skip and not call athena
        mock_athena.assert_not_called()
        assert result["message"] == "Already aggregated"
    else:
        # should process and call athena
        mock_athena.assert_called_once()
        assert result["recordsProcessed"] == 1

    assert result["statusCode"] == 200
    assert result["date"] == "2026-02-20"


def test_main_with_monthly_aggregation(s3_client, s3_bucket, mock_metrics_aggregator_env):
    """Test main function includes monthly aggregation."""
    mock_results = mock_metrics_aggregator_env["mock_results"]
    mock_results.return_value = [
        {"process_status": "success", "created_at": "2026-02-03T10:00:00Z"}
    ]

    create_daily_stats(s3_client, "2026-02-01", total_records=5)
    create_daily_stats(s3_client, "2026-02-02", total_records=5)
    create_daily_stats(s3_client, "2026-02-03", total_records=5)
    result = main("2026-02-03", overwrite=True)

    assert result["statusCode"] == 200
    assert result["date"] == "2026-02-03"
    assert "monthlyAggregations" in result
    assert len(result["monthlyAggregations"]) == 1
    assert result["monthlyAggregations"][0]["month"] == "2026-02"
    assert result["monthlyAggregations"][0]["daysProcessed"] == 3


@mock_aws
def test_main_first_day_of_month(s3_client, s3_bucket, mock_metrics_aggregator_env):
    """Test main function on first day of month finalizes previous month."""
    mock_results = mock_metrics_aggregator_env["mock_results"]
    mock_results.return_value = [
        {"process_status": "success", "created_at": "2026-02-01T10:00:00Z"}
    ]

    create_daily_stats(s3_client, "2026-01-30", total_records=5)
    create_daily_stats(s3_client, "2026-01-31", total_records=5)

    result = main("2026-02-01", overwrite=False)

    assert result["statusCode"] == 200
    assert "monthlyAggregations" in result
    # should have both current month (february) and previous month (january)
    assert len(result["monthlyAggregations"]) == 2
    months = [agg["month"] for agg in result["monthlyAggregations"]]
    assert "2026-02" in months
    assert "2026-01" in months
