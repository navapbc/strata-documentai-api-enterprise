"""Metrics endpoint — aggregated document processing metrics."""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from documentai_api.annotations import AuthUserWithFallback
from documentai_api.config.constants import ApiVisualizationTag, MetricsGranularity
from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.models.metrics import MetricsResponse
from documentai_api.utils.auth import resolve_tenant_from_context
from documentai_api.utils.dates import validate_date_range
from documentai_api.utils.metrics import get_aggregated_metrics

logger = get_logger(__name__)

MAX_DAILY_SPAN = 366
MAX_MONTHLY_SPAN = 60

router = APIRouter(
    prefix="/v1/metrics",
    tags=[ApiVisualizationTag.DOCUMENTS_QUERY],
)


@router.get("")
async def get_metrics(
    auth: AuthUserWithFallback,
    start_date: str,
    end_date: str | None = None,
    granularity: MetricsGranularity = MetricsGranularity.DAILY,
    tenant_id: str | None = None,
) -> MetricsResponse:
    """Get aggregated metrics for date range.

    API key callers see their own tenant's metrics.
    JWT super-admins can pass tenant_id or omit for global.
    JWT tenant-admins see their own tenant only.
    """
    try:
        start_date, end_date = validate_date_range(start_date, end_date)
        _check_span(start_date, end_date, granularity)

        bucket_name = get_aws_config().ddb_export_bucket_name
        if not bucket_name:
            raise HTTPException(status_code=500, detail="Metrics bucket not configured")

        # Resolve tenant scope
        resolved_tenant = resolve_tenant_from_context(auth, tenant_id)

        result = await run_in_threadpool(
            get_aggregated_metrics, bucket_name, start_date, end_date, granularity, resolved_tenant
        )
        logger.info(
            f"Metrics result: {result.get('summary', {}).get('total_records', 0)} total records"
        )
        return MetricsResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics") from e


def _check_span(start_date: str, end_date: str, granularity: MetricsGranularity) -> None:
    """Raise ValueError if the date range exceeds the allowed span."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    days = (end - start).days

    if granularity == MetricsGranularity.DAILY and days > MAX_DAILY_SPAN:
        raise ValueError(f"Daily range cannot exceed {MAX_DAILY_SPAN} days")
    if granularity == MetricsGranularity.MONTHLY:
        months = (end.year - start.year) * 12 + (end.month - start.month) + 1
        if months > MAX_MONTHLY_SPAN:
            raise ValueError(f"Monthly range cannot exceed {MAX_MONTHLY_SPAN} months")
