"""Tests for metrics utility."""

import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from documentai_api.config.constants import MetricsGranularity, TimingMetrics
from documentai_api.utils.metrics import _map_response_codes, build_summary, get_aggregated_metrics


def _make_stats(total_records=10, total_bda_invocations=8):
    return {
        "total_records": total_records,
        "total_bda_invocations": total_bda_invocations,
        "by_status": {"completed": total_records},
        "by_classification": {"income": total_records},
        "by_response_code": {"000": total_records},
        "timing_stats": {
            f"{TimingMetrics.TOTAL_PROCESSING_TIME}_sum": total_records * 10,
            f"{TimingMetrics.TOTAL_PROCESSING_TIME}_count": total_records,
            f"{TimingMetrics.BDA_PROCESSING_TIME}_sum": total_records * 8,
            f"{TimingMetrics.BDA_PROCESSING_TIME}_count": total_records,
            f"{TimingMetrics.BDA_WAIT_TIME}_sum": total_records * 2,
            f"{TimingMetrics.BDA_WAIT_TIME}_count": total_records,
        },
    }


def _mock_s3_body(stats: dict):
    body = MagicMock()
    body.read.return_value = json.dumps(stats).encode()
    return {"Body": body}


def _no_such_key_error():
    return ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")


@pytest.mark.parametrize(
    ("code", "expected_key"),
    [
        ("000", "000 - Document validation passed"),
        ("101", "101 - Missing fields"),
        ("555", "555"),
    ],
    ids=["known-success", "known-missing-fields", "unknown"],
)
def test_map_response_codes(code, expected_key):
    stats = {"by_response_code": {code: 5}}
    result = _map_response_codes(stats)
    assert expected_key in result["by_response_code"]
    assert result["by_response_code"][expected_key] == 5


def test_map_response_codes_no_key():
    stats = {"total_records": 10}
    assert _map_response_codes(stats) == stats


@pytest.mark.parametrize(
    ("stats_list", "expected_records", "expected_avg"),
    [
        ([], 0, 0),
        ([_make_stats(10)], 10, 10.0),
        ([_make_stats(10), _make_stats(20)], 30, 100 / 10),
    ],
    ids=["empty", "single", "multiple"],
)
def test_build_summary(stats_list, expected_records, expected_avg):
    summary = build_summary(stats_list)
    assert summary["total_records"] == expected_records
    assert summary["timing_stats"][f"{TimingMetrics.TOTAL_PROCESSING_TIME}_avg"] == expected_avg


def test_build_summary_no_timing_stats():
    stats = {
        "total_records": 5,
        "total_bda_invocations": 3,
        "by_status": {"completed": 5},
        "by_classification": {"income": 5},
        "by_response_code": {"000": 5},
    }
    summary = build_summary([stats])
    assert summary["total_records"] == 5
    assert summary["timing_stats"][f"{TimingMetrics.TOTAL_PROCESSING_TIME}_avg"] == 0


@pytest.mark.parametrize(
    ("start", "end", "granularity", "expected_count", "stats_key"),
    [
        ("2026-01-01", "2026-01-01", MetricsGranularity.DAILY, 1, "daily_stats"),
        ("2026-01-01", "2026-01-03", MetricsGranularity.DAILY, 3, "daily_stats"),
        ("2026-01-01", "2026-01-31", MetricsGranularity.MONTHLY, 1, "monthly_stats"),
        ("2026-01-01", "2026-03-01", MetricsGranularity.MONTHLY, 3, "monthly_stats"),
        ("2025-11-01", "2026-02-01", MetricsGranularity.MONTHLY, 4, "monthly_stats"),
    ],
    ids=["daily-single", "daily-range", "monthly-single", "monthly-range", "monthly-year-boundary"],
)
def test_get_aggregated_metrics(start, end, granularity, expected_count, stats_key):
    with patch("documentai_api.utils.metrics.s3_service.get_object") as mock_get:
        mock_get.return_value = _mock_s3_body(_make_stats())
        result = get_aggregated_metrics("bucket", start, end, granularity)
        assert result["granularity"] == granularity.value
        assert len(result[stats_key]) == expected_count


@pytest.mark.parametrize(
    ("granularity", "stats_key"),
    [
        (MetricsGranularity.DAILY, "daily_stats"),
        (MetricsGranularity.MONTHLY, "monthly_stats"),
    ],
    ids=["daily", "monthly"],
)
def test_get_aggregated_metrics_missing_data(granularity, stats_key):
    with patch("documentai_api.utils.metrics.s3_service.get_object") as mock_get:
        mock_get.side_effect = _no_such_key_error()
        result = get_aggregated_metrics("bucket", "2026-01-01", "2026-01-01", granularity)
        assert len(result[stats_key]) == 0


@pytest.mark.parametrize(
    "granularity",
    [MetricsGranularity.DAILY, MetricsGranularity.MONTHLY],
    ids=["daily", "monthly"],
)
def test_get_aggregated_metrics_non_nosuchkey_error_raises(granularity):
    with patch("documentai_api.utils.metrics.s3_service.get_object") as mock_get:
        mock_get.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "GetObject")
        with pytest.raises(ClientError):
            get_aggregated_metrics("bucket", "2026-01-01", "2026-01-01", granularity)


def test_build_summary_with_usage_stats():
    """Test build_summary aggregates usage_stats across periods."""
    stats_list = [
        {
            "total_records": 10,
            "total_bda_invocations": 8,
            "by_status": {"success": 10},
            "by_classification": {"W2": 10},
            "by_response_code": {"000": 10},
            "timing_stats": {
                f"{TimingMetrics.TOTAL_PROCESSING_TIME}_sum": 100,
                f"{TimingMetrics.TOTAL_PROCESSING_TIME}_count": 10,
                f"{TimingMetrics.BDA_PROCESSING_TIME}_sum": 80,
                f"{TimingMetrics.BDA_PROCESSING_TIME}_count": 10,
                f"{TimingMetrics.BDA_WAIT_TIME}_sum": 20,
                f"{TimingMetrics.BDA_WAIT_TIME}_count": 10,
            },
            "usage_stats": {
                "total_file_size_bytes": 5000000,
                "total_pages": 10,
                "total_bda_pages": 8,
                "total_bedrock_input_tokens": 2000,
                "total_bedrock_output_tokens": 100,
            },
        },
        {
            "total_records": 5,
            "total_bda_invocations": 5,
            "by_status": {"success": 5},
            "by_classification": {"1099": 5},
            "by_response_code": {"000": 5},
            "timing_stats": {
                f"{TimingMetrics.TOTAL_PROCESSING_TIME}_sum": 50,
                f"{TimingMetrics.TOTAL_PROCESSING_TIME}_count": 5,
                f"{TimingMetrics.BDA_PROCESSING_TIME}_sum": 40,
                f"{TimingMetrics.BDA_PROCESSING_TIME}_count": 5,
                f"{TimingMetrics.BDA_WAIT_TIME}_sum": 10,
                f"{TimingMetrics.BDA_WAIT_TIME}_count": 5,
            },
            "usage_stats": {
                "total_file_size_bytes": 3000000,
                "total_pages": 5,
                "total_bda_pages": 5,
                "total_bedrock_input_tokens": 1000,
                "total_bedrock_output_tokens": 50,
            },
        },
    ]

    summary = build_summary(stats_list)

    assert summary["usage_stats"]["total_file_size_bytes"] == 8000000
    assert summary["usage_stats"]["total_pages"] == 15
    assert summary["usage_stats"]["total_bda_pages"] == 13
    assert summary["usage_stats"]["total_bedrock_input_tokens"] == 3000
    assert summary["usage_stats"]["total_bedrock_output_tokens"] == 150


def test_build_summary_without_usage_stats():
    """Test build_summary handles stats dicts that lack usage_stats (backward compat)."""
    stats_list = [
        {
            "total_records": 5,
            "total_bda_invocations": 3,
            "by_status": {"success": 5},
            "by_classification": {"W2": 5},
            "by_response_code": {"000": 5},
            "timing_stats": {
                f"{TimingMetrics.TOTAL_PROCESSING_TIME}_sum": 50,
                f"{TimingMetrics.TOTAL_PROCESSING_TIME}_count": 5,
                f"{TimingMetrics.BDA_PROCESSING_TIME}_sum": 40,
                f"{TimingMetrics.BDA_PROCESSING_TIME}_count": 5,
                f"{TimingMetrics.BDA_WAIT_TIME}_sum": 10,
                f"{TimingMetrics.BDA_WAIT_TIME}_count": 5,
            },
        },
    ]

    summary = build_summary(stats_list)

    assert summary["total_records"] == 5
    assert summary["usage_stats"]["total_file_size_bytes"] == 0
    assert summary["usage_stats"]["total_pages"] == 0
    assert summary["usage_stats"]["total_bda_pages"] == 0
    assert summary["usage_stats"]["total_bedrock_input_tokens"] == 0
    assert summary["usage_stats"]["total_bedrock_output_tokens"] == 0
