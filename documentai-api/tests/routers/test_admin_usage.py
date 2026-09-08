"""Tests for GET /v1/admin/usage endpoint."""

import json
from typing import Any

import pytest

from documentai_api.config.env import EnvVars
from tests.helpers.fixtures.claims import (
    SUPER_ADMIN_CLAIMS,
    TENANT_ADMIN_CLAIMS,
    TENANT_ADMIN_ID,
    override_jwt,
)

USAGE_URL = "/v1/admin/usage"


@pytest.fixture
def metrics_bucket(s3_bucket, monkeypatch):
    monkeypatch.setenv(EnvVars.DDB_EXPORT_BUCKET_NAME, s3_bucket.name)
    return s3_bucket


def _put_monthly_report(bucket: Any, month: str, tenants: list[dict[str, Any]]) -> None:
    report = {"month": month, "report_type": "usage_only", "tenants": tenants}
    bucket.put_object(
        Key=f"usage-report/month={month}/report.json",
        Body=json.dumps(report),
    )


def _put_daily_stats(
    bucket: Any, date: str, stats: dict[str, Any], tenant_id: str | None = None
) -> None:
    if tenant_id:
        key = f"usage-report/utc/date={date}/tenant={tenant_id}/stats.json"
    else:
        key = f"usage-report/utc/date={date}/stats.json"
    bucket.put_object(Key=key, Body=json.dumps(stats))


def _make_daily_stats(date: str, total_records: int = 10) -> dict[str, Any]:
    return {
        "date": date,
        "total_records": total_records,
        "total_bda_invocations": total_records - 2,
        "total_file_size_bytes": total_records * 500000,
        "total_bda_pages": total_records - 2,
        "total_bedrock_input_tokens": total_records * 2000,
        "total_bedrock_output_tokens": total_records * 100,
    }


TENANT_ADMIN = {
    "tenant_id": TENANT_ADMIN_ID,
    "total_records": 100,
    "total_bda_invocations": 80,
    "total_file_size_bytes": 50000000,
    "total_bda_pages": 75,
    "total_bedrock_input_tokens": 200000,
    "total_bedrock_output_tokens": 10000,
}

OTHER_TENANT_ID = "other-tenant-id"
OTHER_TENANT = {
    "tenant_id": OTHER_TENANT_ID,
    "total_records": 50,
    "total_bda_invocations": 40,
    "total_file_size_bytes": 25000000,
    "total_bda_pages": 38,
    "total_bedrock_input_tokens": 100000,
    "total_bedrock_output_tokens": 5000,
}


@pytest.fixture
def seeded_monthly(metrics_bucket):
    _put_monthly_report(metrics_bucket, "2026-06", [TENANT_ADMIN, OTHER_TENANT])


@pytest.fixture
def seeded_daily(metrics_bucket):
    for day in range(1, 4):
        _put_daily_stats(
            metrics_bucket, f"2026-06-{day:02d}", _make_daily_stats(f"2026-06-{day:02d}", 10)
        )
    _put_daily_stats(
        metrics_bucket, "2026-06-01", _make_daily_stats("2026-06-01", 5), tenant_id=TENANT_ADMIN_ID
    )


##############################################################################
# Monthly
##############################################################################


def test_monthly_returns_all_tenants(api_client, seeded_monthly):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(USAGE_URL, params={"month": "2026-06"})
    assert response.status_code == 200
    data = response.json()
    assert data["month"] == "2026-06"
    assert data["granularity"] == "monthly"
    assert len(data["tenants"]) == 2


def test_monthly_empty_when_no_report(api_client, metrics_bucket):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(USAGE_URL, params={"month": "2026-01"})
    assert response.status_code == 200
    assert response.json()["tenants"] == []


def test_monthly_defaults_to_current_month(api_client, metrics_bucket):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(USAGE_URL)
    assert response.status_code == 200
    from datetime import UTC, datetime

    assert response.json()["month"] == datetime.now(UTC).strftime("%Y-%m")


def test_monthly_tenant_scoping(api_client, seeded_monthly):
    override_jwt(TENANT_ADMIN_CLAIMS)
    response = api_client.get(USAGE_URL, params={"month": "2026-06"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["tenants"]) == 1
    assert data["tenants"][0]["tenantId"] == TENANT_ADMIN_ID


def test_tenant_admin_cannot_see_other_tenant(api_client, seeded_monthly):
    """Tenant-admin passing another tenant_id still only sees their own data."""
    override_jwt(TENANT_ADMIN_CLAIMS)
    response = api_client.get(USAGE_URL, params={"month": "2026-06", "tenant_id": OTHER_TENANT_ID})
    assert response.status_code == 200
    data = response.json()
    assert len(data["tenants"]) == 1
    assert data["tenants"][0]["tenantId"] == TENANT_ADMIN_ID


def test_monthly_csv_format(api_client, seeded_monthly):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(USAGE_URL, params={"month": "2026-06", "format": "csv"})
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    lines = response.text.strip().split("\n")
    assert len(lines) == 3  # header + 2 tenants
    assert "tenantId" in lines[0]
    assert "totalRecords" in lines[0]


##############################################################################
# Daily
##############################################################################


def test_daily_returns_days(api_client, seeded_daily):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(USAGE_URL, params={"month": "2026-06", "granularity": "daily"})
    assert response.status_code == 200
    data = response.json()
    assert data["granularity"] == "daily"
    assert len(data["days"]) == 3


def test_daily_tenant_scoped(api_client, seeded_daily):
    override_jwt(TENANT_ADMIN_CLAIMS)
    response = api_client.get(USAGE_URL, params={"month": "2026-06", "granularity": "daily"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["days"]) == 1
    assert data["days"][0]["totalRecords"] == 5


def test_daily_super_admin_filters_by_tenant_id(api_client, seeded_daily):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(
        USAGE_URL, params={"month": "2026-06", "granularity": "daily", "tenant_id": TENANT_ADMIN_ID}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["days"]) == 1
    assert data["days"][0]["totalRecords"] == 5


def test_daily_csv_format(api_client, seeded_daily):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(
        USAGE_URL, params={"month": "2026-06", "granularity": "daily", "format": "csv"}
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    lines = response.text.strip().split("\n")
    assert "totalRecords" in lines[0]


def test_daily_current_day_partial_fallback(api_client, metrics_bucket, monkeypatch):
    """Current day falls back to metrics aggregator and is tagged partial=true."""
    override_jwt(SUPER_ADMIN_CLAIMS)
    from datetime import UTC, datetime

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    month = today[:7]

    # Seed ONLY the metrics aggregator prefix (no usage-report file for today)
    aggregator_stats = {
        "date": today,
        "total_records": 7,
        "total_bda_invocations": 5,
        "usage_stats": {
            "total_file_size_bytes": 350000,
            "total_bda_pages": 5,
            "total_bedrock_input_tokens": 1400,
            "total_bedrock_output_tokens": 70,
        },
    }
    metrics_bucket.put_object(
        Key=f"aggregated/utc/date={today}/stats.json",
        Body=json.dumps(aggregator_stats),
    )

    response = api_client.get(USAGE_URL, params={"month": month, "granularity": "daily"})
    assert response.status_code == 200
    data = response.json()

    # Should have today's data from the aggregator fallback
    today_entries = [d for d in data["days"] if d["date"] == today]
    assert len(today_entries) == 1
    assert today_entries[0]["partial"] is True
    assert today_entries[0]["totalRecords"] == 7
    assert today_entries[0]["totalBdaPages"] == 5


def test_monthly_current_month_includes_today_no_double_count(
    api_client, metrics_bucket, monkeypatch
):
    """Monthly view for current month = report (through yesterday) + today's live. No double-count."""
    override_jwt(SUPER_ADMIN_CLAIMS)
    from datetime import UTC, datetime

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    month = today[:7]

    # Seed a monthly report with prior-day data (through yesterday)
    report = {
        "month": month,
        "report_type": "usage_only",
        "tenants": [
            {
                "tenant_id": TENANT_ADMIN_ID,
                "total_records": 20,
                "total_bda_invocations": 18,
                "total_file_size_bytes": 1000000,
                "total_bda_pages": 18,
                "total_bedrock_input_tokens": 4000,
                "total_bedrock_output_tokens": 200,
            }
        ],
    }
    metrics_bucket.put_object(
        Key=f"usage-report/month={month}/report.json",
        Body=json.dumps(report),
    )

    # Seed today's live aggregator data for tenant-a
    aggregator_stats = {
        "date": today,
        "total_records": 3,
        "total_bda_invocations": 3,
        "usage_stats": {
            "total_file_size_bytes": 150000,
            "total_bda_pages": 3,
            "total_bedrock_input_tokens": 600,
            "total_bedrock_output_tokens": 30,
        },
    }
    metrics_bucket.put_object(
        Key=f"aggregated/utc/date={today}/tenant={TENANT_ADMIN_ID}/stats.json",
        Body=json.dumps(aggregator_stats),
    )

    # Monthly view should be report + today (no double-count)
    response = api_client.get(USAGE_URL, params={"month": month, "tenant_id": TENANT_ADMIN_ID})
    assert response.status_code == 200
    data = response.json()
    assert len(data["tenants"]) == 1
    tenant = data["tenants"][0]
    # 20 (report) + 3 (today) = 23, NOT 23 + 3 = 26 (double-count)
    assert tenant["totalRecords"] == 23
    assert tenant["totalBdaPages"] == 21
    assert tenant["totalFileSizeBytes"] == 1150000


def test_monthly_current_month_surfaces_new_tenant_not_in_report(
    api_client, metrics_bucket, monkeypatch
):
    """Unfiltered monthly view surfaces a brand-new tenant with today's activity.

    even when that tenant is absent from report.json.
    """
    override_jwt(SUPER_ADMIN_CLAIMS)
    from datetime import UTC, datetime

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    month = today[:7]

    # Report only has tenant-a (tenant-b is brand new, not in report)
    _put_monthly_report(metrics_bucket, month, [TENANT_ADMIN])

    # Today's aggregator data exists for both tenants
    for tid, records in [(TENANT_ADMIN_ID, 3), (OTHER_TENANT_ID, 7)]:
        metrics_bucket.put_object(
            Key=f"aggregated/utc/date={today}/tenant={tid}/stats.json",
            Body=json.dumps(
                {
                    "date": today,
                    "total_records": records,
                    "total_bda_invocations": records,
                    "usage_stats": {
                        "total_file_size_bytes": records * 1000,
                        "total_bda_pages": records,
                        "total_bedrock_input_tokens": records * 100,
                        "total_bedrock_output_tokens": records * 10,
                    },
                }
            ),
        )

    # Mock list_tenants to return both tenants (simulates tenant table)
    monkeypatch.setattr(
        "documentai_api.utils.tenants.list_tenants",
        lambda *, active_only: [
            {"tenantId": TENANT_ADMIN_ID, "isActive": True},
            {"tenantId": OTHER_TENANT_ID, "isActive": True},
        ],
    )

    response = api_client.get(USAGE_URL, params={"month": month})
    assert response.status_code == 200
    data = response.json()
    tenant_ids = {t["tenantId"] for t in data["tenants"]}
    assert OTHER_TENANT_ID in tenant_ids
    other_tenant = next(t for t in data["tenants"] if t["tenantId"] == OTHER_TENANT_ID)
    assert other_tenant["totalRecords"] == 7


def test_monthly_current_month_deactivated_tenant_discovered_via_registry(
    api_client, metrics_bucket, monkeypatch
):
    """A deactivated tenant NOT in report but with today's activity surfaces.

    only because active_only=False includes it in the discovery set.
    """
    override_jwt(SUPER_ADMIN_CLAIMS)
    from datetime import UTC, datetime

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    month = today[:7]

    # Report has only tenant-a (tenant-deactivated is absent)
    _put_monthly_report(metrics_bucket, month, [TENANT_ADMIN])

    # Today's aggregator data exists for the deactivated tenant
    metrics_bucket.put_object(
        Key=f"aggregated/utc/date={today}/tenant=tenant-deactivated/stats.json",
        Body=json.dumps(
            {
                "date": today,
                "total_records": 4,
                "total_bda_invocations": 4,
                "usage_stats": {
                    "total_file_size_bytes": 4000,
                    "total_bda_pages": 4,
                    "total_bedrock_input_tokens": 400,
                    "total_bedrock_output_tokens": 40,
                },
            }
        ),
    )

    # patch honors active_only to pin production's active_only=False; changing
    # active_only=True in the prod code would omit the deactivated tenant and
    # fail the assertions below. this test guards production behavior from a
    # potential regression
    monkeypatch.setattr(
        "documentai_api.utils.tenants.list_tenants",
        lambda *, active_only: (
            [{"tenantId": TENANT_ADMIN_ID, "isActive": True}]
            if active_only
            else [
                {"tenantId": TENANT_ADMIN_ID, "isActive": True},
                {"tenantId": "tenant-deactivated", "isActive": False},
            ]
        ),
    )

    response = api_client.get(USAGE_URL, params={"month": month})
    assert response.status_code == 200
    data = response.json()
    tenant_ids = {t["tenantId"] for t in data["tenants"]}
    assert "tenant-deactivated" in tenant_ids
    deactivated = next(t for t in data["tenants"] if t["tenantId"] == "tenant-deactivated")
    assert deactivated["totalRecords"] == 4


def test_monthly_current_month_graceful_degradation_on_registry_failure(
    api_client, metrics_bucket, monkeypatch
):
    """If list_tenants raises, monthly view still works with report tenants only."""
    override_jwt(SUPER_ADMIN_CLAIMS)
    from datetime import UTC, datetime

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    month = today[:7]

    _put_monthly_report(metrics_bucket, month, [TENANT_ADMIN])

    # Aggregator data for tenant-admin
    metrics_bucket.put_object(
        Key=f"aggregated/utc/date={today}/tenant={TENANT_ADMIN_ID}/stats.json",
        Body=json.dumps(
            {
                "date": today,
                "total_records": 2,
                "total_bda_invocations": 2,
                "usage_stats": {
                    "total_file_size_bytes": 2000,
                    "total_bda_pages": 2,
                    "total_bedrock_input_tokens": 200,
                    "total_bedrock_output_tokens": 20,
                },
            }
        ),
    )

    # list_tenants blows up
    def _boom(*, active_only):
        raise RuntimeError("DDB down")

    monkeypatch.setattr("documentai_api.utils.tenants.list_tenants", _boom)

    response = api_client.get(USAGE_URL, params={"month": month})
    assert response.status_code == 200
    data = response.json()
    # Still returns tenant-a from report, augmented with today
    assert len(data["tenants"]) == 1
    assert data["tenants"][0]["tenantId"] == TENANT_ADMIN_ID
    assert data["tenants"][0]["totalRecords"] == TENANT_ADMIN["total_records"] + 2  # type: ignore[operator]


##############################################################################
# Validation
##############################################################################


def test_invalid_month_returns_400(api_client, metrics_bucket):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(USAGE_URL, params={"month": "abc"})
    assert response.status_code == 400
    assert "YYYY-MM" in response.json()["detail"]


def test_invalid_month_number_returns_400(api_client, metrics_bucket):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(USAGE_URL, params={"month": "2026-13"})
    assert response.status_code == 400


##############################################################################
# Auth
##############################################################################


def test_unauthenticated_returns_401(api_client, metrics_bucket):
    response = api_client.get(USAGE_URL)
    assert response.status_code == 401


##############################################################################
# Error handling
##############################################################################


def test_bucket_not_configured(api_client, monkeypatch):
    override_jwt(SUPER_ADMIN_CLAIMS)
    monkeypatch.delenv(EnvVars.DDB_EXPORT_BUCKET_NAME, raising=False)
    response = api_client.get(USAGE_URL, params={"month": "2026-06"})
    assert response.status_code == 500
    assert "not configured" in response.json()["detail"]
