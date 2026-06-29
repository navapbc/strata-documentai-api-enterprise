"""Admin usage reporting endpoint."""

import asyncio
import json
from calendar import monthrange
from datetime import UTC, datetime
from typing import Any

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status

from documentai_api.annotations import AdminClaims, OutputFormat, verify_jwt_with_role
from documentai_api.config.constants import (
    METRICS_AGG_DDB_DAILY_S3_PREFIX,
    METRICS_USAGE_REPORT_S3_PREFIX,
    MetricsGranularity,
    OutputFormatType,
)
from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.services import s3 as s3_service
from documentai_api.utils.jwt_auth import tenant_scope
from documentai_api.utils.response_builder import build_csv_response

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/admin/usage",
    dependencies=[Depends(verify_jwt_with_role)],
)


def _read_monthly_report(bucket: str, month: str) -> list[dict[str, Any]]:
    """Read the pre-computed monthly usage report from S3."""
    s3_key = f"{METRICS_USAGE_REPORT_S3_PREFIX}={month}/report.json"
    try:
        obj = s3_service.get_object(bucket, s3_key)
        report = json.loads(obj["Body"].read().decode())
        return report.get("tenants", [])
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return []
        raise
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Skipping corrupt monthly report for {s3_key}: {e}")
        return []


async def _read_daily_usage(bucket: str, month: str, tenant_id: str | None) -> list[dict[str, Any]]:
    """Read daily usage stats for a month from the metrics aggregator's daily output.

    Daily data lives under aggregated/utc/date={YYYY-MM-DD}/[tenant=X/]stats.json,
    written by the metrics_aggregator job. Not to be confused with the monthly
    usage report (usage-report/month=X/report.json) which is a separate Athena query.
    """
    year, mo = int(month[:4]), int(month[5:7])
    days_in_month = monthrange(year, mo)[1]

    async def fetch_day(day: int) -> dict[str, Any] | None:
        date_str = f"{month}-{day:02d}"
        if tenant_id:
            s3_key = f"{METRICS_AGG_DDB_DAILY_S3_PREFIX}={date_str}/tenant={tenant_id}/stats.json"
        else:
            s3_key = f"{METRICS_AGG_DDB_DAILY_S3_PREFIX}={date_str}/stats.json"

        try:
            obj = await asyncio.to_thread(s3_service.get_object, bucket, s3_key)
            stats = json.loads(obj["Body"].read().decode())
            usage = stats.get("usage_stats", {})
            return {
                "date": date_str,
                "total_records": stats.get("total_records", 0),
                "total_bda_invocations": stats.get("total_bda_invocations", 0),
                "total_pages": usage.get("total_pages", 0),
                "total_bda_pages": usage.get("total_bda_pages", 0),
                "total_file_size_bytes": usage.get("total_file_size_bytes", 0),
                "total_bedrock_input_tokens": usage.get("total_bedrock_input_tokens", 0),
                "total_bedrock_output_tokens": usage.get("total_bedrock_output_tokens", 0),
            }
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Skipping corrupt stats for {s3_key}: {e}")
            return None

    results = await asyncio.gather(*[fetch_day(day) for day in range(1, days_in_month + 1)])
    return [r for r in results if r is not None]


@router.get("")
async def get_usage(
    claims: AdminClaims,
    month: str | None = None,
    tenant_id: str | None = None,
    granularity: MetricsGranularity = MetricsGranularity.MONTHLY,
    output_format: OutputFormat = OutputFormatType.JSON,
):
    """Get usage report for a given month.

    granularity=monthly: per-tenant totals for the month.
    granularity=daily: per-day breakdown for a specific tenant or global.

    Super-admins see all tenants (or filter with ?tenant_id=X).
    Tenant-admins see only their own.
    Defaults to the current month if not specified.
    """
    if not month:
        month = datetime.now(UTC).strftime("%Y-%m")
    else:
        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="month must be in YYYY-MM format",
            ) from None

    aws_config = get_aws_config()
    bucket = aws_config.ddb_export_bucket_name
    if not bucket:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Metrics bucket not configured",
        )

    scope = tenant_scope(claims)
    # Tenant-admins are locked to their own; super-admins can optionally filter.
    effective_tenant = scope or tenant_id

    if granularity == MetricsGranularity.DAILY:
        data = await _read_daily_usage(bucket, month, effective_tenant)
        if output_format == OutputFormatType.CSV:
            return build_csv_response(data)
        return {"month": month, "granularity": "daily", "days": data}

    # Monthly
    tenants = _read_monthly_report(bucket, month)
    if effective_tenant:
        tenants = [t for t in tenants if t.get("tenant_id") == effective_tenant]

    if output_format == OutputFormatType.CSV:
        return build_csv_response(tenants)

    return {
        "month": month,
        "granularity": "monthly",
        "tenants": tenants,
        "note": "Monthly totals are produced on a schedule; the current month may be incomplete or absent until the next run. Daily stats are real-time and may not sum to the monthly total.",
    }
