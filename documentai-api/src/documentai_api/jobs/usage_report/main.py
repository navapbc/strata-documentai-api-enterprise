"""Monthly tenant usage report generator.

Queries raw metrics data directly via Athena and produces a per-tenant usage
report. No dependency on the metrics aggregator having run.
"""

import json
import re
import time
from typing import Any

from documentai_api.config.constants import (
    ATHENA_QUERY_TIMEOUT_SECONDS,
    METRICS_USAGE_REPORT_S3_PREFIX,
    AthenaQueryStatus,
)
from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.utils.aws_client_factory import AWSClientFactory

logger = get_logger(__name__)


def _build_usage_query(database_name: str, table_name: str, yyyymm: str) -> str:
    """Build Athena query to aggregate usage dimensions per tenant for a month."""
    return f"""
    WITH deduped AS (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY file_name
                ORDER BY updated_at DESC
            ) AS rn
        FROM {database_name}.{table_name}
        WHERE date BETWEEN '{yyyymm}-01' AND '{yyyymm}-31'
    )
    SELECT
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
    GROUP BY COALESCE(tenant_id, '__unknown__')
    ORDER BY total_records DESC
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


def generate_usage_report(yyyymm: str) -> dict[str, Any]:
    """Generate a per-tenant usage report for a given month via Athena."""
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

    query = _build_usage_query(database_name, table_name, yyyymm)
    logger.info(f"Querying usage data for {yyyymm}")
    rows = _execute_query(query, database_name, workgroup_name)

    if not rows:
        return {
            "month": yyyymm,
            "report_type": "usage_only",
            "tenants": [],
            "message": "No data found",
        }

    tenants = [
        {
            "tenant_id": row["tenant_id"],
            "total_records": int(row["total_records"]),
            "total_bda_invocations": int(row["total_bda_invocations"]),
            "total_file_size_bytes": int(row["total_file_size_bytes"]),
            "total_bda_pages": int(row["total_bda_pages"]),
            "total_bedrock_input_tokens": int(row["total_bedrock_input_tokens"]),
            "total_bedrock_output_tokens": int(row["total_bedrock_output_tokens"]),
        }
        for row in rows
    ]

    return {
        "month": yyyymm,
        "report_type": "usage_only",
        "tenants": tenants,
    }


def main(yyyymm: str) -> dict[str, Any]:
    """Generate and write usage report to S3."""
    aws_config = get_aws_config()
    bucket = aws_config.ddb_export_bucket_name
    if not bucket:
        raise ValueError("DDB_EXPORT_BUCKET_NAME not configured")

    report = generate_usage_report(yyyymm)

    # Write report to S3
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
        "output_location": f"s3://{bucket}/{s3_key}",
    }
