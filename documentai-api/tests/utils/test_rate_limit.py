"""Tests for tenant write rate limiting."""

from decimal import Decimal

import pytest
from fastapi import HTTPException

from documentai_api.schemas.tenant_request_counts import TenantRequestCountRecord
from documentai_api.schemas.tenants import TenantRecord
from documentai_api.utils import rate_limit as rate_limit_util
from documentai_api.utils.dates import get_month_prefix, get_today_iso


def _seed_tenant(tenants_table, tenant_id: str, max_per_day=None, max_per_month=None):
    item = {
        TenantRecord.TENANT_ID: tenant_id,
        TenantRecord.DISPLAY_NAME: "Test Tenant",
        TenantRecord.IS_ACTIVE: True,
    }
    if max_per_day is not None:
        item["maxRequestsPerDay"] = max_per_day
    if max_per_month is not None:
        item["maxRequestsPerMonth"] = max_per_month
    tenants_table.put_item(Item=item)


def _get_count(counts_table, tenant_id: str, date: str) -> int:
    item = counts_table.get_item(
        Key={TenantRequestCountRecord.TENANT_ID: tenant_id, TenantRequestCountRecord.DATE: date}
    ).get("Item")
    return int(item[TenantRequestCountRecord.COUNT]) if item else 0


# =============================================================================
# Fast path - no limits configured
# =============================================================================


def test_no_limits_skips_counter(tenants_table, tenant_request_counts_table):
    _seed_tenant(tenants_table, "t1")
    rate_limit_util.increment_and_check("t1")
    assert _get_count(tenant_request_counts_table, "t1", get_today_iso()) == 0


def test_unknown_tenant_skips_counter(tenants_table, tenant_request_counts_table):
    rate_limit_util.increment_and_check("unknown")
    assert _get_count(tenant_request_counts_table, "unknown", get_today_iso()) == 0


# =============================================================================
# Daily limit
# =============================================================================


def test_daily_limit_increments_counter(tenants_table, tenant_request_counts_table):
    _seed_tenant(tenants_table, "t1", max_per_day=5)
    rate_limit_util.increment_and_check("t1")
    assert _get_count(tenant_request_counts_table, "t1", get_today_iso()) == 1


def test_daily_limit_allows_up_to_limit(tenants_table, tenant_request_counts_table):
    _seed_tenant(tenants_table, "t1", max_per_day=3)
    for _ in range(3):
        rate_limit_util.increment_and_check("t1")
    assert _get_count(tenant_request_counts_table, "t1", get_today_iso()) == 3


def test_daily_limit_raises_429_when_exceeded(tenants_table, tenant_request_counts_table):
    _seed_tenant(tenants_table, "t1", max_per_day=2)
    rate_limit_util.increment_and_check("t1")
    rate_limit_util.increment_and_check("t1")

    with pytest.raises(HTTPException) as exc_info:
        rate_limit_util.increment_and_check("t1")
    assert exc_info.value.status_code == 429
    assert "Daily" in exc_info.value.detail


def test_daily_limit_rolls_back_on_exceed(tenants_table, tenant_request_counts_table):
    _seed_tenant(tenants_table, "t1", max_per_day=2)
    rate_limit_util.increment_and_check("t1")
    rate_limit_util.increment_and_check("t1")

    with pytest.raises(HTTPException):
        rate_limit_util.increment_and_check("t1")

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
        rate_limit_util.increment_and_check("t1")
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
        rate_limit_util.increment_and_check("t1")

    assert _get_count(tenant_request_counts_table, "t1", get_today_iso()) == 0


# =============================================================================
# Daily limit takes precedence over monthly
# =============================================================================


def test_daily_limit_checked_before_monthly(tenants_table, tenant_request_counts_table):
    """Daily limit should raise before monthly is even evaluated."""
    _seed_tenant(tenants_table, "t1", max_per_day=1, max_per_month=100)
    rate_limit_util.increment_and_check("t1")

    with pytest.raises(HTTPException) as exc_info:
        rate_limit_util.increment_and_check("t1")
    assert "Daily" in exc_info.value.detail
