"""Monthly tenant usage report generator.

Queries raw metrics data directly via Athena and produces a per-tenant usage
report (monthly + daily breakdown). No dependency on the metrics aggregator
having run.
"""

import json
import re
import time
from collections import defaultdict
from typing import Any

from documentai_api.config.constants import (
    ATHENA_QUERY_TIMEOUT_SECONDS,
    METRICS_USAGE_REPORT_DAILY_S3_PREFIX,
    METRICS_USAGE_REPORT_S3_PREFIX,
    AthenaQueryStatus,
)
from documentai_api.config.env import get_aws_config
from documentai_api.dtos.usage_stats import UsageStats
from documentai_api.logging import get_logger
from documentai_api.utils.aws_client_factory import AWSClientFactory

logger = get_logger(__name__)


def _build_daily_usage_query(database_name: str, table_name: str, yyyymm: str) -> str:
    """Build Athena query to aggregate usage per tenant per day for a month.

    For the current month, excludes today (today's data comes from the
    metrics aggregator at read time to avoid double-counting).
    """
    from calendar import monthrange
    from datetime import UTC, datetime, timedelta

    year, month = int(yyyymm[:4]), int(yyyymm[5:7])
    last_day = monthrange(year, month)[1]
    end_date = f"{yyyymm}-{last_day:02d}"

    # For the current month, only query through yesterday
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    if today[:7] == yyyymm and today > f"{yyyymm}-01":
        # Yesterday (or start of month if today is the 1st)
        yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = yesterday

    return f"""
    WITH deduped AS (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY file_name
                ORDER BY updated_at DESC
            ) AS rn
        FROM {database_name}.{table_name}
        WHERE date BETWEEN '{yyyymm}-01' AND '{end_date}'
    )
    SELECT
        CAST(date AS VARCHAR) AS date,
        COALESCE(tenant_id, '__unknown__') AS tenant_id,
        COUNT(*) AS total_records,
        COUNT(bda_invocation_arn) AS total_bda_invocations,
        COALESCE(SUM(CAST(file_size_bytes AS BIGINT)), 0) AS total_file_size_bytes,
        COALESCE(SUM(CAST(pages_sent_to_bda AS BIGINT)), 0) AS total_bda_pages,
        COALESCE(
            SUM(CAST(preclassification_input_tokens AS BIGINT))
            + SUM(CAST(crop_input_tokens AS BIGINT)),
            0
        ) AS total_bedrock_input_tokens,
        COALESCE(
            SUM(CAST(preclassification_output_tokens AS BIGINT))
            + SUM(CAST(crop_output_tokens AS BIGINT)),
            0
        ) AS total_bedrock_output_tokens
    FROM deduped
    WHERE rn = 1
    GROUP BY CAST(date AS VARCHAR), COALESCE(tenant_id, '__unknown__')
    ORDER BY date, total_records DESC
    """


def _execute_query(query: str, database_name: str, workgroup_name: str) -> list[dict[str, Any]]:
    """Execute Athena query and return results."""
    athena = AWSClientFactory.get_athena_client()

    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database_name},
        WorkGroup=workgroup_name,
    )
    execution_id = response["QueryExecutionId"]

    for _ in range(ATHENA_QUERY_TIMEOUT_SECONDS):
        status_resp = athena.get_query_execution(QueryExecutionId=execution_id)
        status = status_resp["QueryExecution"]["Status"]["State"]
        if AthenaQueryStatus.is_final(status):
            break
        time.sleep(1)
    else:
        raise RuntimeError(
            f"Athena query {execution_id} did not complete within {ATHENA_QUERY_TIMEOUT_SECONDS}s"
        )

    if status != AthenaQueryStatus.SUCCEEDED:
        reason = status_resp["QueryExecution"]["Status"].get("StateChangeReason", "")
        raise RuntimeError(f"Query failed ({status}): {reason}")

    results = []
    paginator = athena.get_paginator("get_query_results")
    for page in paginator.paginate(QueryExecutionId=execution_id):
        columns = [col["Name"] for col in page["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]]
        for row in page["ResultSet"]["Rows"][1:]:
            record = {}
            for i, col in enumerate(columns):
                record[col] = row["Data"][i].get("VarCharValue", "")
            results.append(record)

    return results


def generate_usage_report(
    yyyymm: str, daily_data: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    """Generate a per-tenant monthly usage report by summing daily data."""
    # Sum across all days per tenant
    tenant_totals: dict[str, UsageStats] = defaultdict(UsageStats)

    for tenant_rows in daily_data.values():
        for row in tenant_rows:
            current = tenant_totals[row["tenant_id"]]
            tenant_totals[row["tenant_id"]] = UsageStats.sum([current, UsageStats.from_dict(row)])

    tenants = [
        {"tenant_id": tid, **totals.to_dict()}
        for tid, totals in sorted(
            tenant_totals.items(), key=lambda x: x[1].total_records, reverse=True
        )
    ]

    if not tenants:
        return {
            "month": yyyymm,
            "report_type": "usage_only",
            "tenants": [],
            "message": "No data found",
        }

    return {
        "month": yyyymm,
        "report_type": "usage_only",
        "tenants": tenants,
    }


def generate_daily_usage(yyyymm: str) -> dict[str, list[dict[str, Any]]]:
    """Generate per-tenant daily usage for a month via Athena.

    Returns {date: [tenant_stats, ...]} grouped by date.
    """
    if not re.match(r"^\d{4}-\d{2}$", yyyymm):
        raise ValueError(f"Invalid month format: {yyyymm!r} (expected YYYY-MM)")

    aws_config = get_aws_config()
    database_name = aws_config.glue_database_name
    table_name = aws_config.ddb_raw_data_table_name
    workgroup_name = aws_config.athena_workgroup_name

    if not database_name:
        raise ValueError("GLUE_DATABASE_NAME not configured")
    if not table_name:
        raise ValueError("DDB_RAW_DATA_TABLE_NAME not configured")
    if not workgroup_name:
        raise ValueError("ATHENA_WORKGROUP_NAME not configured")

    query = _build_daily_usage_query(database_name, table_name, yyyymm)
    logger.info(f"Querying daily usage data for {yyyymm}")
    rows = _execute_query(query, database_name, workgroup_name)

    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        stats = UsageStats.from_dict(row)
        by_date[row["date"]].append({"tenant_id": row["tenant_id"], **stats.to_dict()})

    return dict(by_date)


def _write_daily_files(bucket: str, daily_data: dict[str, list[dict[str, Any]]]) -> int:
    """Write per-day global + per-tenant stats files to S3.

    Writes:
      usage-report/utc/date={date}/stats.json  (global: all tenants summed)
      usage-report/utc/date={date}/tenant={id}/stats.json  (per-tenant)
    """
    s3 = AWSClientFactory.get_s3_client()
    files_written = 0

    for date_str, tenant_rows in daily_data.items():
        # Per-tenant files
        for row in tenant_rows:
            tenant_key = (
                f"{METRICS_USAGE_REPORT_DAILY_S3_PREFIX}={date_str}"
                f"/tenant={row['tenant_id']}/stats.json"
            )
            s3.put_object(
                Bucket=bucket,
                Key=tenant_key,
                Body=json.dumps(row, default=str),
                ContentType="application/json",
            )
            files_written += 1

        # Global file (sum across tenants)
        total = UsageStats.sum(UsageStats.from_dict(r) for r in tenant_rows)
        global_stats = {"date": date_str, **total.to_dict()}
        global_key = f"{METRICS_USAGE_REPORT_DAILY_S3_PREFIX}={date_str}/stats.json"
        s3.put_object(
            Bucket=bucket,
            Key=global_key,
            Body=json.dumps(global_stats, default=str),
            ContentType="application/json",
        )
        files_written += 1

    return files_written


def main(yyyymm: str) -> dict[str, Any]:
    """Generate and write monthly + daily usage reports to S3."""
    aws_config = get_aws_config()
    bucket = aws_config.ddb_export_bucket_name
    if not bucket:
        raise ValueError("DDB_EXPORT_BUCKET_NAME not configured")

    # Single Athena query: daily breakdown for the full month
    daily_data = generate_daily_usage(yyyymm)

    # Write daily files
    daily_files = _write_daily_files(bucket, daily_data)
    logger.info(f"Daily usage: wrote {daily_files} files for {len(daily_data)} days")

    # Derive monthly report by summing daily
    report = generate_usage_report(yyyymm, daily_data)
    s3 = AWSClientFactory.get_s3_client()
    s3_key = f"{METRICS_USAGE_REPORT_S3_PREFIX}={yyyymm}/report.json"
    s3.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=json.dumps(report, default=str),
        ContentType="application/json",
    )
    logger.info(f"Usage report written to s3://{bucket}/{s3_key}")

    return {
        "statusCode": 200,
        "month": yyyymm,
        "report_type": report["report_type"],
        "tenant_count": len(report["tenants"]),
        "daily_days": len(daily_data),
        "daily_files": daily_files,
        "output_location": f"s3://{bucket}/{s3_key}",
    }
