"""Tests for tenant write rate limiting."""

from decimal import Decimal
from typing import Any

import pytest
from fastapi import HTTPException

from documentai_api.schemas.tenant_request_counts import TenantRequestCountRecord
from documentai_api.schemas.tenants import TenantRecord
from documentai_api.utils import write_limit as write_limit_util
from documentai_api.utils.dates import get_month_prefix, get_today_iso


def _seed_tenant(
    tenants_table: Any,
    tenant_id: str,
    max_per_day: int | None = None,
    max_per_month: int | None = None,
) -> None:
    item = {
        TenantRecord.TENANT_ID: tenant_id,
        TenantRecord.DISPLAY_NAME: "Test Tenant",
        TenantRecord.IS_ACTIVE: True,
    }
    if max_per_day is not None:
        item["maxWritesPerDay"] = max_per_day
    if max_per_month is not None:
        item["maxWritesPerMonth"] = max_per_month
    tenants_table.put_item(Item=item)


def _seed_count(counts_table: Any, tenant_id: str, date: str, count: int) -> None:
    counts_table.put_item(
        Item={
            TenantRequestCountRecord.TENANT_ID: tenant_id,
            TenantRequestCountRecord.DATE: date,
            TenantRequestCountRecord.COUNT: Decimal(count),
        }
    )


def _get_count(counts_table: Any, tenant_id: str, date: str) -> int:
    item = counts_table.get_item(
        Key={TenantRequestCountRecord.TENANT_ID: tenant_id, TenantRequestCountRecord.DATE: date}
    ).get("Item")
    return int(item[TenantRequestCountRecord.COUNT]) if item else 0


# =============================================================================
# Fast path - no limits configured
# =============================================================================


def test_no_limits_skips_counter(tenants_table, tenant_request_counts_table):
    _seed_tenant(tenants_table, "t1")
    write_limit_util.increment_and_check("t1")
    assert _get_count(tenant_request_counts_table, "t1", get_today_iso()) == 0


def test_unknown_tenant_skips_counter(tenants_table, tenant_request_counts_table):
    write_limit_util.increment_and_check("unknown")
    assert _get_count(tenant_request_counts_table, "unknown", get_today_iso()) == 0


# =============================================================================
# Daily limit
# =============================================================================


def test_daily_limit_increments_counter(tenants_table, tenant_request_counts_table):
    _seed_tenant(tenants_table, "t1", max_per_day=5)
    write_limit_util.increment_and_check("t1")
    assert _get_count(tenant_request_counts_table, "t1", get_today_iso()) == 1


def test_daily_limit_allows_up_to_limit(tenants_table, tenant_request_counts_table):
    _seed_tenant(tenants_table, "t1", max_per_day=3)
    for _ in range(3):
        write_limit_util.increment_and_check("t1")
    assert _get_count(tenant_request_counts_table, "t1", get_today_iso()) == 3


def test_daily_limit_raises_429_when_exceeded(tenants_table, tenant_request_counts_table):
    _seed_tenant(tenants_table, "t1", max_per_day=2)
    write_limit_util.increment_and_check("t1")
    write_limit_util.increment_and_check("t1")

    with pytest.raises(HTTPException) as exc_info:
        write_limit_util.increment_and_check("t1")
    assert exc_info.value.status_code == 429
    assert "Daily" in exc_info.value.detail


def test_daily_limit_rolls_back_on_exceed(tenants_table, tenant_request_counts_table):
    _seed_tenant(tenants_table, "t1", max_per_day=2)
    write_limit_util.increment_and_check("t1")
    write_limit_util.increment_and_check("t1")

    with pytest.raises(HTTPException):
        write_limit_util.increment_and_check("t1")

    # Counter should be rolled back to 2, not left at 3
    assert _get_count(tenant_request_counts_table, "t1", get_today_iso()) == 2


# =============================================================================
# Monthly limit
# =============================================================================


def test_monthly_limit_raises_429_when_exceeded(tenants_table, tenant_request_counts_table):
    _seed_tenant(tenants_table, "t1", max_per_month=2)

    today = get_today_iso()
    prior_day = f"{get_month_prefix(today)}-01"
    if prior_day == today:
        prior_day = f"{get_month_prefix(today)}-02"

    tenant_request_counts_table.put_item(
        Item={
            TenantRequestCountRecord.TENANT_ID: "t1",
            TenantRequestCountRecord.DATE: prior_day,
            TenantRequestCountRecord.COUNT: Decimal(2),
        }
    )

    with pytest.raises(HTTPException) as exc_info:
        write_limit_util.increment_and_check("t1")
    assert exc_info.value.status_code == 429
    assert "Monthly" in exc_info.value.detail


def test_monthly_limit_rolls_back_on_exceed(tenants_table, tenant_request_counts_table):
    _seed_tenant(tenants_table, "t1", max_per_month=1)

    today = get_today_iso()
    prior_day = f"{get_month_prefix(today)}-01"
    if prior_day == today:
        prior_day = f"{get_month_prefix(today)}-02"

    tenant_request_counts_table.put_item(
        Item={
            TenantRequestCountRecord.TENANT_ID: "t1",
            TenantRequestCountRecord.DATE: prior_day,
            TenantRequestCountRecord.COUNT: Decimal(1),
        }
    )

    with pytest.raises(HTTPException):
        write_limit_util.increment_and_check("t1")

    assert _get_count(tenant_request_counts_table, "t1", get_today_iso()) == 0


# =============================================================================
# Daily limit takes precedence over monthly
# =============================================================================


def test_daily_limit_checked_before_monthly(tenants_table, tenant_request_counts_table):
    """Daily limit should raise before monthly is even evaluated."""
    _seed_tenant(tenants_table, "t1", max_per_day=1, max_per_month=100)
    write_limit_util.increment_and_check("t1")

    with pytest.raises(HTTPException) as exc_info:
        write_limit_util.increment_and_check("t1")
    assert "Daily" in exc_info.value.detail


# =============================================================================
# decrement
# =============================================================================


@pytest.mark.parametrize(
    ("initial_count", "decrement_count", "expected"),
    [
        (2, 1, 1),  # reduces count
        (1, 2, 0),  # floors at zero
    ],
)
def test_decrement(
    tenants_table, tenant_request_counts_table, initial_count, decrement_count, expected
):
    today = get_today_iso()
    _seed_tenant(tenants_table, "t1", max_per_day=10)
    _seed_count(tenant_request_counts_table, "t1", today, initial_count)
    for _ in range(decrement_count):
        write_limit_util.decrement("t1", today)
    assert _get_count(tenant_request_counts_table, "t1", today) == expected


def test_decrement_targets_specified_date(tenants_table, tenant_request_counts_table):
    from datetime import date, timedelta

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _seed_count(tenant_request_counts_table, "t1", yesterday, 3)
    write_limit_util.decrement("t1", yesterday)
    assert _get_count(tenant_request_counts_table, "t1", yesterday) == 2
    assert _get_count(tenant_request_counts_table, "t1", get_today_iso()) == 0
