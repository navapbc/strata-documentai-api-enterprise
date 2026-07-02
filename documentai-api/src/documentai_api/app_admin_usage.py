"""Admin usage reporting endpoint."""

import asyncio
import json
from calendar import monthrange
from datetime import UTC, datetime
from typing import Any

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Response, status

from documentai_api.annotations import AdminClaims, OutputFormat, verify_jwt_with_role
from documentai_api.config.constants import (
    METRICS_USAGE_REPORT_DAILY_S3_PREFIX,
    METRICS_USAGE_REPORT_S3_PREFIX,
    MetricsGranularity,
    OutputFormatType,
)
from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.models.usage import (
    DailyUsage,
    DailyUsageResponse,
    MonthlyUsageResponse,
    TenantUsage,
)
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
        report: dict[str, Any] = json.loads(obj["Body"].read().decode())
        tenants: list[dict[str, Any]] = report.get("tenants", [])
        return tenants
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return []
        raise
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Skipping corrupt monthly report for {s3_key}: {e}")
        return []


async def _read_daily_usage(bucket: str, month: str, tenant_id: str | None) -> list[dict[str, Any]]:
    """Read daily usage stats for a month.

    Prior days: reads deduped files from usage-report/utc/date= (written by usage_report job).
    Current day: falls back to the metrics aggregator's near-real-time stats,
    tagged with partial=true so the FE can indicate the data is not yet finalized.
    """
    from documentai_api.utils.metrics import _get_daily_metrics

    year, mo = int(month[:4]), int(month[5:7])
    days_in_month = monthrange(year, mo)[1]
    today = datetime.now(UTC).strftime("%Y-%m-%d")

    async def fetch_day(day: int) -> dict[str, Any] | None:
        date_str = f"{month}-{day:02d}"

        # Current day always comes from the metrics aggregator (near-real-time)
        if date_str == today:
            metrics = await asyncio.to_thread(
                _get_daily_metrics, bucket, date_str, date_str, tenant_id
            )
            daily_stats = metrics.get("daily_stats", [])
            if daily_stats:
                usage = daily_stats[0].get("usage_stats", {})
                return {
                    "date": date_str,
                    "total_records": daily_stats[0].get("total_records", 0),
                    "total_bda_invocations": daily_stats[0].get("total_bda_invocations", 0),
                    "total_bda_pages": usage.get("total_bda_pages", 0),
                    "total_file_size_bytes": usage.get("total_file_size_bytes", 0),
                    "total_bedrock_input_tokens": usage.get("total_bedrock_input_tokens", 0),
                    "total_bedrock_output_tokens": usage.get("total_bedrock_output_tokens", 0),
                    "partial": True,
                }
            return None

        # Prior days: read deduped usage-report file
        if tenant_id:
            s3_key = (
                f"{METRICS_USAGE_REPORT_DAILY_S3_PREFIX}={date_str}/tenant={tenant_id}/stats.json"
            )
        else:
            s3_key = f"{METRICS_USAGE_REPORT_DAILY_S3_PREFIX}={date_str}/stats.json"

        try:
            obj = await asyncio.to_thread(s3_service.get_object, bucket, s3_key)
            stats = json.loads(obj["Body"].read().decode())
            return {
                "date": date_str,
                "total_records": stats.get("total_records", 0),
                "total_bda_invocations": stats.get("total_bda_invocations", 0),
                "total_bda_pages": stats.get("total_bda_pages", 0),
                "total_file_size_bytes": stats.get("total_file_size_bytes", 0),
                "total_bedrock_input_tokens": stats.get("total_bedrock_input_tokens", 0),
                "total_bedrock_output_tokens": stats.get("total_bedrock_output_tokens", 0),
            }
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchKey":
                raise
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Skipping corrupt stats for {s3_key}: {e}")

        return None

    results = await asyncio.gather(*[fetch_day(day) for day in range(1, days_in_month + 1)])
    return [r for r in results if r is not None]


@router.get("", response_model=None)
async def get_usage(
    claims: AdminClaims,
    month: str | None = None,
    tenant_id: str | None = None,
    granularity: MetricsGranularity = MetricsGranularity.MONTHLY,
    output_format: OutputFormat = OutputFormatType.JSON,
) -> MonthlyUsageResponse | DailyUsageResponse | Response:
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
        # Prior days: deduped files from usage_report job.
        # Current day: near-real-time from metrics aggregator, tagged partial=true.
        data = await _read_daily_usage(bucket, month, effective_tenant)
        days = [DailyUsage(**d) for d in data]
        if output_format == OutputFormatType.CSV:
            return build_csv_response([d.model_dump(by_alias=True) for d in days])
        return DailyUsageResponse(month=month, days=days)

    # Monthly
    tenants_raw = _read_monthly_report(bucket, month)

    # If viewing the current month, add today's live metrics to each tenant
    # so monthly totals stay congruent with the daily view.
    current_month = datetime.now(UTC).strftime("%Y-%m")
    if month == current_month:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        from documentai_api.schemas.tenants import TenantRecord
        from documentai_api.utils.metrics import _get_daily_metrics
        from documentai_api.utils.tenants import list_tenants

        if effective_tenant:
            tenant_ids = [effective_tenant]
        else:
            report_tids = {t["tenant_id"] for t in tenants_raw}
            try:
                active = await asyncio.to_thread(list_tenants, active_only=False)
                tenant_ids = list(report_tids | {t[TenantRecord.TENANT_ID] for t in active})
            except Exception:
                logger.warning("tenant registry unavailable; falling back to report tenants only")
                tenant_ids = list(report_tids)

        today_results = await asyncio.gather(
            *[
                asyncio.to_thread(_get_daily_metrics, bucket, today, today, tid)
                for tid in tenant_ids
            ]
        )

        for tid, today_metrics in zip(tenant_ids, today_results, strict=True):
            today_stats = today_metrics.get("daily_stats", [])
            if not today_stats:
                continue
            usage = today_stats[0].get("usage_stats", {})
            additions = {
                "total_records": today_stats[0].get("total_records", 0),
                "total_bda_invocations": today_stats[0].get("total_bda_invocations", 0),
                "total_file_size_bytes": usage.get("total_file_size_bytes", 0),
                "total_bda_pages": usage.get("total_bda_pages", 0),
                "total_bedrock_input_tokens": usage.get("total_bedrock_input_tokens", 0),
                "total_bedrock_output_tokens": usage.get("total_bedrock_output_tokens", 0),
            }
            matched = next((t for t in tenants_raw if t.get("tenant_id") == tid), None)
            if matched:
                for k, v in additions.items():
                    matched[k] = matched.get(k, 0) + v
            else:
                tenants_raw.append({"tenant_id": tid, **additions})

    if effective_tenant:
        tenants_raw = [t for t in tenants_raw if t.get("tenant_id") == effective_tenant]
    tenants = [TenantUsage(**t) for t in tenants_raw]

    if output_format == OutputFormatType.CSV:
        return build_csv_response([t.model_dump(by_alias=True) for t in tenants])

    return MonthlyUsageResponse(month=month, tenants=tenants)
