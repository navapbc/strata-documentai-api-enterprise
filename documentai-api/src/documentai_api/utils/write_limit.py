"""Tenant write quota enforcement via DDB atomic counters.

Each item tracks the write count for a tenant on a given calendar day.
Items are retained for 5 years (see ConfigDefaults.TENANT_REQUEST_COUNTS_TTL_DAYS)
for historical trend analysis and capacity planning.
Monthly totals are derived by summing daily items - no separate monthly counter needed.
"""

from decimal import Decimal
from typing import Any

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from documentai_api.config.constants import ConfigDefaults
from documentai_api.logging import get_logger
from documentai_api.schemas.tenant_request_counts import (
    TenantRequestCountRecord,
    TenantRequestCountsTable,
)
from documentai_api.schemas.tenants import TenantRecord
from documentai_api.services import ddb as ddb_service
from documentai_api.utils.dates import get_month_prefix, get_today_iso, get_ttl_epoch_in_days
from documentai_api.utils.tenants import get_tenant

logger = get_logger(__name__)

_tenants_count_table = TenantRequestCountsTable()


def _get_tenant_update_key(tenant_id: str, date: str) -> dict[str, str]:
    return {
        TenantRequestCountRecord.TENANT_ID: tenant_id,
        TenantRequestCountRecord.DATE: date,
    }


def increment_and_check(tenant_id: str) -> None:
    """Atomically increment today's write count and raise 429 if a limit is exceeded.

    Checks both daily and monthly limits if configured on the tenant.
    Raises HTTPException(429) before incrementing if the limit is already reached.
    """
    tenant = get_tenant(tenant_id)
    if not tenant:
        return

    max_per_day: int | None = tenant.get(TenantRecord.MAX_WRITES_PER_DAY)
    max_per_month: int | None = tenant.get(TenantRecord.MAX_WRITES_PER_MONTH)

    if max_per_day is None and max_per_month is None:
        return

    today = get_today_iso()
    table_name = _tenants_count_table._get_table_name()

    result = ddb_service.update_item(
        table_name,
        key=_get_tenant_update_key(tenant_id, today),
        update_expression="ADD #count :one SET #ttl = if_not_exists(#ttl, :ttl)",
        expression_names={
            "#count": TenantRequestCountRecord.COUNT,
            "#ttl": TenantRequestCountRecord.TTL,
        },
        expression_values={
            ":one": Decimal(1),
            ":ttl": get_ttl_epoch_in_days(ConfigDefaults.TENANT_REQUEST_COUNTS_TTL_DAYS),
        },
        return_values="ALL_NEW",
    )
    new_count = int(result[TenantRequestCountRecord.COUNT])  # type: ignore[index]

    if max_per_day is not None and new_count > max_per_day:
        _rollback(table_name, tenant_id, today)
        logger.warning(f"Daily write limit exceeded for tenant {tenant_id} (limit={max_per_day})")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily write limit of {max_per_day} requests exceeded",
        )

    if (
        max_per_month is not None
        and _get_monthly_total(table_name, tenant_id, today, new_count) > max_per_month
    ):
        _rollback(table_name, tenant_id, today)
        logger.warning(
            f"Monthly write limit exceeded for tenant {tenant_id} (limit={max_per_month})"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly write limit of {max_per_month} requests exceeded",
        )


def _rollback(table_name: str, tenant_id: str, today: str) -> None:
    try:
        ddb_service.update_item(
            table_name,
            key=_get_tenant_update_key(tenant_id, today),
            update_expression="ADD #count :neg_one",
            expression_names={"#count": TenantRequestCountRecord.COUNT},
            expression_values={":neg_one": Decimal(-1), ":zero": Decimal(0)},
            condition_expression="#count > :zero",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.warning(
                f"Skipped decrement for tenant {tenant_id} on {today}: count already at zero"
            )
        else:
            raise


def decrement(tenant_id: str, date: str) -> None:
    """Decrement the write count for a tenant on the given date.

    Pass the upload date rather than today to avoid skew when the processor
    runs on a different calendar day than the upload.
    """
    _rollback(_tenants_count_table._get_table_name(), tenant_id, date)


def _get_monthly_total(table_name: str, tenant_id: str, today: str, today_count: int) -> int:
    """Sum daily counts for the current month. Uses today_count for today to avoid a stale read."""
    items = _query_month_items(table_name, tenant_id, get_month_prefix(today))
    return sum(
        today_count
        if item[TenantRequestCountRecord.DATE] == today
        else int(item.get(TenantRequestCountRecord.COUNT, 0))
        for item in items
    )


def get_write_counts(tenant_id: str, month: str) -> list[dict[str, Any]]:
    """Return daily request count items for a tenant in the given month (YYYY-MM)."""
    table_name = _tenants_count_table._get_table_name()
    return _query_month_items(table_name, tenant_id, month)


def _query_month_items(table_name: str, tenant_id: str, month_prefix: str) -> list[dict[str, Any]]:
    from documentai_api.services.aws_client_factory import AWSClientFactory

    table = AWSClientFactory.get_ddb_table(table_name)
    response = table.query(
        KeyConditionExpression=(
            Key(TenantRequestCountRecord.TENANT_ID).eq(tenant_id)
            & Key(TenantRequestCountRecord.DATE).begins_with(month_prefix)
        ),
        ProjectionExpression="#date, #count",
        ExpressionAttributeNames={
            "#date": TenantRequestCountRecord.DATE,
            "#count": TenantRequestCountRecord.COUNT,
        },
    )
    return response.get("Items", [])
