"""Metrics service for reading aggregated stats from S3."""

import json
from datetime import datetime, timedelta
from typing import Any

from botocore.exceptions import ClientError

from documentai_api.config.constants import (
    S3_AGG_DDB_DATA_DAILY_PREFIX,
    S3_AGG_DDB_DATA_MONTHLY_PREFIX,
    MetricsGranularity,
    TimingMetrics,
)
from documentai_api.logging import get_logger
from documentai_api.services import s3 as s3_service
from documentai_api.utils.response_codes import ResponseCodes

logger = get_logger(__name__)


def get_aggregated_metrics(
    bucket: str,
    start_date: str,
    end_date: str,
    granularity: MetricsGranularity = MetricsGranularity.DAILY,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Read aggregated metrics from S3 for date range.

    Args:
        bucket: S3 bucket name
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        granularity: Aggregation granularity (MetricsGranularity.DAILY or MetricsGranularity.MONTHLY)
        tenant_id: Optional tenant ID for scoped metrics. None returns global.
    """
    if granularity == MetricsGranularity.MONTHLY:
        return _get_monthly_metrics(bucket, start_date, end_date, tenant_id)
    else:
        return _get_daily_metrics(bucket, start_date, end_date, tenant_id)


def _get_daily_metrics(
    bucket: str, start_date: str, end_date: str, tenant_id: str | None = None
) -> dict[str, Any]:
    """Read daily aggregated metrics from S3."""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    daily_stats = []
    current_dt = start_dt

    while current_dt <= end_dt:
        date_str = current_dt.strftime("%Y-%m-%d")
        if tenant_id:
            s3_key = f"{S3_AGG_DDB_DATA_DAILY_PREFIX}={date_str}/tenant={tenant_id}/stats.json"
        else:
            s3_key = f"{S3_AGG_DDB_DATA_DAILY_PREFIX}={date_str}/stats.json"

        logger.info(f"Reading metrics for {date_str}")

        try:
            obj = s3_service.get_object(bucket, s3_key)
            stats = json.loads(obj["Body"].read().decode())
            daily_stats.append(_map_response_codes(stats))
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(f"No stats found for {date_str}")
            else:
                raise

        current_dt += timedelta(days=1)

    summary = build_summary(daily_stats)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "granularity": MetricsGranularity.DAILY.value,
        "daily_stats": daily_stats,
        "summary": summary,
    }


def _get_monthly_metrics(
    bucket: str, start_date: str, end_date: str, tenant_id: str | None = None
) -> dict[str, Any]:
    """Read monthly aggregated metrics from S3."""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    # generate list of unique months in range
    months = set()
    current_dt = start_dt
    while current_dt <= end_dt:
        months.add(current_dt.strftime("%Y-%m"))
        # move to next month
        if current_dt.month == 12:
            current_dt = current_dt.replace(year=current_dt.year + 1, month=1, day=1)
        else:
            current_dt = current_dt.replace(month=current_dt.month + 1, day=1)

    monthly_stats = []
    for yyyymm in sorted(months):
        if tenant_id:
            s3_key = f"{S3_AGG_DDB_DATA_MONTHLY_PREFIX}={yyyymm}/tenant={tenant_id}/stats.json"
        else:
            s3_key = f"{S3_AGG_DDB_DATA_MONTHLY_PREFIX}={yyyymm}/stats.json"

        try:
            obj = s3_service.get_object(bucket, s3_key)
            stats = json.loads(obj["Body"].read().decode())
            monthly_stats.append(_map_response_codes(stats))
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(f"No stats found for {yyyymm}")
            else:
                raise

    summary = build_summary(monthly_stats)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "granularity": MetricsGranularity.MONTHLY.value,
        "monthly_stats": monthly_stats,
        "summary": summary,
    }


def _map_response_codes(stats: dict[str, Any]) -> dict[str, Any]:
    if "by_response_code" not in stats:
        return stats
    mapped = {}
    for code, count in stats["by_response_code"].items():
        display = ResponseCodes.get_message(code)
        key = f"{code} - {display}" if display else code
        mapped[key] = count
    stats["by_response_code"] = mapped
    return stats


def build_summary(stats_list: list[dict[str, Any]]) -> dict[str, Any]:
    """Build summary stats across all periods."""
    timing_stats: dict[str, float] = {}
    for prefix in (
        TimingMetrics.TOTAL_PROCESSING_TIME,
        TimingMetrics.BDA_PROCESSING_TIME,
        TimingMetrics.BDA_WAIT_TIME,
    ):
        timing_stats[f"{prefix}_avg"] = 0
        timing_stats[f"{prefix}_sum"] = 0
        timing_stats[f"{prefix}_count"] = 0

    by_status: dict[str, int] = {}
    by_classification: dict[str, int] = {}
    by_response_code: dict[str, int] = {}
    total_records = 0
    total_bda_invocations = 0

    for stats in stats_list:
        total_records += stats.get("total_records", 0)
        total_bda_invocations += stats.get("total_bda_invocations", 0)

        for status, count in stats.get("by_status", {}).items():
            by_status[status] = by_status.get(status, 0) + count

        for classification, count in stats.get("by_classification", {}).items():
            by_classification[classification] = by_classification.get(classification, 0) + count

        for code, count in stats.get("by_response_code", {}).items():
            by_response_code[code] = by_response_code.get(code, 0) + count

        if "timing_stats" in stats:
            timing = stats["timing_stats"]
            for prefix in (
                TimingMetrics.TOTAL_PROCESSING_TIME,
                TimingMetrics.BDA_PROCESSING_TIME,
                TimingMetrics.BDA_WAIT_TIME,
            ):
                timing_stats[f"{prefix}_sum"] += timing.get(f"{prefix}_sum", 0)
                timing_stats[f"{prefix}_count"] += timing.get(f"{prefix}_count", 0)

    for prefix in (
        TimingMetrics.TOTAL_PROCESSING_TIME,
        TimingMetrics.BDA_PROCESSING_TIME,
        TimingMetrics.BDA_WAIT_TIME,
    ):
        count = timing_stats[f"{prefix}_count"]
        timing_stats[f"{prefix}_avg"] = (
            round(timing_stats[f"{prefix}_sum"] / count, 2) if count > 0 else 0
        )

    return {
        "total_records": total_records,
        "total_bda_invocations": total_bda_invocations,
        "by_status": by_status,
        "by_classification": by_classification,
        "by_response_code": by_response_code,
        "timing_stats": timing_stats,
    }
