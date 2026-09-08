"""Tests for GET /v1/metrics endpoint."""

import json
from typing import Any

import pytest

from documentai_api.app import app
from documentai_api.config.env import EnvVars
from documentai_api.utils.auth import UserContext, get_user_context_with_fallback

METRICS_URL = "/v1/metrics"


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def as_super_admin(api_client):
    """Authenticate as super-admin (JWT)."""
    app.dependency_overrides[get_user_context_with_fallback] = lambda: UserContext(
        tenant_id="__admin__", api_key_name="admin@example.com", auth_method="jwt"
    )
    return api_client


@pytest.fixture
def as_tenant_admin(api_client):
    """Authenticate as tenant-admin (JWT)."""
    app.dependency_overrides[get_user_context_with_fallback] = lambda: UserContext(
        tenant_id="test-tenant", api_key_name="user@example.com", auth_method="jwt"
    )
    return api_client


@pytest.fixture
def as_api_key(api_client):
    """Authenticate as API key caller."""
    app.dependency_overrides[get_user_context_with_fallback] = lambda: UserContext(
        tenant_id="test-tenant", api_key_name="tenant-ingest", auth_method="api_key"
    )
    return api_client


@pytest.fixture
def metrics_bucket(s3_bucket, monkeypatch):
    """Point metrics env var at the shared test bucket."""
    monkeypatch.setenv(EnvVars.DDB_EXPORT_BUCKET_NAME, s3_bucket.name)
    return s3_bucket


def _put_daily_stats(
    bucket: Any, date: str, stats: dict[str, Any], tenant_id: str | None = None
) -> None:
    """Helper to write a daily stats file."""
    if tenant_id:
        key = f"aggregated/utc/date={date}/tenant={tenant_id}/stats.json"
    else:
        key = f"aggregated/utc/date={date}/stats.json"
    bucket.put_object(Key=key, Body=json.dumps(stats))


def _put_monthly_stats(
    bucket: Any, month: str, stats: dict[str, Any], tenant_id: str | None = None
) -> None:
    """Helper to write a monthly stats file."""
    if tenant_id:
        key = f"aggregated/utc/month={month}/tenant={tenant_id}/stats.json"
    else:
        key = f"aggregated/utc/month={month}/stats.json"
    bucket.put_object(Key=key, Body=json.dumps(stats))


def _make_stats(date: str, total_records: int = 10, **overrides: Any) -> dict[str, Any]:
    """Build a minimal valid stats dict."""
    base = {
        "date": date,
        "total_records": total_records,
        "total_bda_invocations": total_records - 1,
        "by_status": {"completed": total_records - 1, "failed": 1},
        "by_classification": {"W2": total_records},
        "by_response_code": {"SUCCESS": total_records - 1, "INTERNAL_PROCESSING_ERROR": 1},
        "timing_stats": {
            "total_processing_time_sum": total_records * 20.0,
            "total_processing_time_count": total_records - 1,
            "bda_processing_time_sum": total_records * 18.0,
            "bda_processing_time_count": total_records - 1,
            "bda_wait_time_sum": total_records * 2.0,
            "bda_wait_time_count": total_records - 1,
        },
    }
    base.update(overrides)
    return base


@pytest.fixture
def seeded_metrics(metrics_bucket):
    """Seed global and tenant-scoped daily stats for multiple days."""
    _put_daily_stats(metrics_bucket, "2026-01-14", _make_stats("2026-01-14", 20))
    _put_daily_stats(metrics_bucket, "2026-01-15", _make_stats("2026-01-15", 42))
    _put_daily_stats(metrics_bucket, "2026-01-16", _make_stats("2026-01-16", 30))
    # Tenant-scoped stats for the same date (separate S3 key path)
    _put_daily_stats(
        metrics_bucket, "2026-01-15", _make_stats("2026-01-15", 10), tenant_id="test-tenant"
    )
    _put_monthly_stats(metrics_bucket, "2026-01", _make_stats("2026-01", 100))
    _put_monthly_stats(
        metrics_bucket, "2026-01", _make_stats("2026-01", 25), tenant_id="test-tenant"
    )


##############################################################################
# Auth
##############################################################################


def test_metrics_unauthenticated_returns_401(api_client):
    response = api_client.get(METRICS_URL, params={"start_date": "2026-01-15"})
    assert response.status_code == 401


##############################################################################
# Validation
##############################################################################


def test_metrics_missing_start_date(as_super_admin, metrics_bucket):
    response = as_super_admin.get(METRICS_URL)
    assert response.status_code == 422


def test_metrics_invalid_date_format(as_super_admin, metrics_bucket):
    response = as_super_admin.get(METRICS_URL, params={"start_date": "not-a-date"})
    assert response.status_code == 400
    assert "Invalid date format" in response.json()["detail"]


def test_metrics_start_after_end(as_super_admin, metrics_bucket):
    response = as_super_admin.get(
        METRICS_URL, params={"start_date": "2026-01-20", "end_date": "2026-01-10"}
    )
    assert response.status_code == 400


def test_metrics_daily_range_too_large(as_super_admin, metrics_bucket):
    response = as_super_admin.get(
        METRICS_URL, params={"start_date": "2020-01-01", "end_date": "2026-01-01"}
    )
    assert response.status_code == 400
    assert "cannot exceed" in response.json()["detail"]


def test_metrics_invalid_granularity(as_super_admin, metrics_bucket):
    response = as_super_admin.get(
        METRICS_URL, params={"start_date": "2026-01-15", "granularity": "hourly"}
    )
    assert response.status_code == 422


##############################################################################
# Super-admin (global)
##############################################################################


def test_super_admin_sees_global_metrics(as_super_admin, seeded_metrics):
    response = as_super_admin.get(METRICS_URL, params={"start_date": "2026-01-15"})
    assert response.status_code == 200
    data = response.json()
    assert data["granularity"] == "daily"
    assert len(data["dailyStats"]) == 1
    assert data["dailyStats"][0]["totalRecords"] == 42
    assert data["summary"]["totalRecords"] == 42


def test_super_admin_multi_day_rollup(as_super_admin, seeded_metrics):
    """Summary aggregates across multiple days."""
    response = as_super_admin.get(
        METRICS_URL, params={"start_date": "2026-01-14", "end_date": "2026-01-16"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["dailyStats"]) == 3
    assert data["summary"]["totalRecords"] == 20 + 42 + 30
    assert "completed" in data["summary"]["byStatus"]


def test_super_admin_partial_data(as_super_admin, seeded_metrics):
    """Range with missing days returns only available data."""
    response = as_super_admin.get(
        METRICS_URL, params={"start_date": "2026-01-13", "end_date": "2026-01-15"}
    )
    assert response.status_code == 200
    data = response.json()
    # 2026-01-13 has no data, 2026-01-14 and 2026-01-15 do
    assert len(data["dailyStats"]) == 2
    assert data["summary"]["totalRecords"] == 20 + 42


def test_super_admin_can_filter_by_tenant(as_super_admin, seeded_metrics):
    response = as_super_admin.get(
        METRICS_URL, params={"start_date": "2026-01-15", "tenant_id": "test-tenant"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["dailyStats"][0]["totalRecords"] == 10


def test_super_admin_no_data_returns_empty(as_super_admin, metrics_bucket):
    response = as_super_admin.get(METRICS_URL, params={"start_date": "2026-06-01"})
    assert response.status_code == 200
    data = response.json()
    assert data["dailyStats"] == []
    assert data["summary"]["totalRecords"] == 0


def test_super_admin_empty_tenant_id_returns_global(as_super_admin, seeded_metrics):
    """Empty string tenant_id falls through to global."""
    response = as_super_admin.get(METRICS_URL, params={"start_date": "2026-01-15", "tenant_id": ""})
    assert response.status_code == 200
    data = response.json()
    assert data["dailyStats"][0]["totalRecords"] == 42


def test_super_admin_monthly_granularity(as_super_admin, seeded_metrics):
    response = as_super_admin.get(
        METRICS_URL,
        params={"start_date": "2026-01-01", "end_date": "2026-01-31", "granularity": "monthly"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["granularity"] == "monthly"
    assert len(data["monthlyStats"]) == 1
    assert data["monthlyStats"][0]["totalRecords"] == 100


def test_super_admin_monthly_with_tenant(as_super_admin, seeded_metrics):
    response = as_super_admin.get(
        METRICS_URL,
        params={
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
            "granularity": "monthly",
            "tenant_id": "test-tenant",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["monthlyStats"][0]["totalRecords"] == 25


##############################################################################
# Malformed stats resilience
##############################################################################


def test_malformed_stats_missing_keys(as_super_admin, metrics_bucket):
    """Stats file missing expected keys returns 200 with zeros."""
    _put_daily_stats(metrics_bucket, "2026-02-01", {"date": "2026-02-01"})
    response = as_super_admin.get(METRICS_URL, params={"start_date": "2026-02-01"})
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["totalRecords"] == 0
    assert data["summary"]["byStatus"] == {}


##############################################################################
# Tenant-admin (scoped)
##############################################################################


def test_tenant_admin_sees_own_metrics(as_tenant_admin, seeded_metrics):
    response = as_tenant_admin.get(METRICS_URL, params={"start_date": "2026-01-15"})
    assert response.status_code == 200
    data = response.json()
    assert data["dailyStats"][0]["totalRecords"] == 10


def test_tenant_admin_own_tenant_explicit(as_tenant_admin, seeded_metrics):
    """Tenant-admin passing their own tenant_id succeeds."""
    response = as_tenant_admin.get(
        METRICS_URL, params={"start_date": "2026-01-15", "tenant_id": "test-tenant"}
    )
    assert response.status_code == 200
    assert response.json()["dailyStats"][0]["totalRecords"] == 10


def test_tenant_admin_cannot_see_other(as_tenant_admin, seeded_metrics):
    """Tenant-admin requesting another tenant gets 403."""
    response = as_tenant_admin.get(
        METRICS_URL, params={"start_date": "2026-01-15", "tenant_id": "other-tenant"}
    )
    assert response.status_code == 403


##############################################################################
# API key (scoped)
##############################################################################


def test_api_key_sees_own_tenant_metrics(as_api_key, seeded_metrics):
    response = as_api_key.get(METRICS_URL, params={"start_date": "2026-01-15"})
    assert response.status_code == 200
    data = response.json()
    assert data["dailyStats"][0]["totalRecords"] == 10


def test_api_key_rejects_mismatched_tenant(as_api_key, seeded_metrics):
    response = as_api_key.get(
        METRICS_URL, params={"start_date": "2026-01-15", "tenant_id": "other-tenant"}
    )
    assert response.status_code == 403


##############################################################################
# Error handling
##############################################################################


def test_metrics_bucket_not_configured(as_super_admin, monkeypatch):
    monkeypatch.delenv(EnvVars.DDB_EXPORT_BUCKET_NAME, raising=False)
    response = as_super_admin.get(METRICS_URL, params={"start_date": "2026-01-15"})
    assert response.status_code == 500
    assert "not configured" in response.json()["detail"]


##############################################################################
# Polish: response code mapping, timing math, monthly span, S3 errors
##############################################################################


def test_response_codes_mapped_to_display_keys(as_super_admin, metrics_bucket):
    """by_response_code keys include 'CODE - message' format."""
    stats = _make_stats("2026-03-01")
    stats["by_response_code"] = {"000": 5, "999": 2}
    _put_daily_stats(metrics_bucket, "2026-03-01", stats)

    response = as_super_admin.get(METRICS_URL, params={"start_date": "2026-03-01"})
    assert response.status_code == 200
    codes = response.json()["summary"]["byResponseCode"]
    assert "000 - Document validation passed" in codes
    assert "999 - Internal processing error" in codes


def test_timing_stats_avg_computed_correctly(as_super_admin, metrics_bucket):
    """Verify avg = sum / count in the summary."""
    stats = _make_stats("2026-03-02", 10)
    # sum=200, count=9 → avg=22.22
    stats["timing_stats"]["total_processing_time_sum"] = 200.0
    stats["timing_stats"]["total_processing_time_count"] = 9
    _put_daily_stats(metrics_bucket, "2026-03-02", stats)

    response = as_super_admin.get(METRICS_URL, params={"start_date": "2026-03-02"})
    assert response.status_code == 200
    timing = response.json()["summary"]["timingStats"]
    assert timing["totalProcessingTimeAvg"] == 22.22
    assert timing["totalProcessingTimeSum"] == 200.0
    assert timing["totalProcessingTimeCount"] == 9


def test_timing_stats_zero_count_no_divide_by_zero(as_super_admin, metrics_bucket):
    """Zero count produces avg=0, not a crash."""
    stats = _make_stats("2026-03-03")
    stats["timing_stats"]["total_processing_time_sum"] = 0
    stats["timing_stats"]["total_processing_time_count"] = 0
    stats["timing_stats"]["bda_processing_time_sum"] = 0
    stats["timing_stats"]["bda_processing_time_count"] = 0
    stats["timing_stats"]["bda_wait_time_sum"] = 0
    stats["timing_stats"]["bda_wait_time_count"] = 0
    _put_daily_stats(metrics_bucket, "2026-03-03", stats)

    response = as_super_admin.get(METRICS_URL, params={"start_date": "2026-03-03"})
    assert response.status_code == 200
    timing = response.json()["summary"]["timingStats"]
    assert timing["totalProcessingTimeAvg"] == 0
    assert timing["bdaProcessingTimeAvg"] == 0


def test_monthly_range_too_large(as_super_admin, metrics_bucket):
    """Monthly span cap is enforced."""
    response = as_super_admin.get(
        METRICS_URL,
        params={"start_date": "2020-01-01", "end_date": "2026-01-01", "granularity": "monthly"},
    )
    assert response.status_code == 400
    assert "cannot exceed" in response.json()["detail"]


def test_s3_non_nosuchkey_error_returns_500(as_super_admin, metrics_bucket, monkeypatch):
    """Non-NoSuchKey S3 errors propagate as 500."""
    from botocore.exceptions import ClientError

    def _raise_access_denied(*args, **kwargs):
        raise ClientError({"Error": {"Code": "AccessDenied", "Message": "Forbidden"}}, "GetObject")

    monkeypatch.setattr("documentai_api.services.s3.get_object", _raise_access_denied)
    response = as_super_admin.get(METRICS_URL, params={"start_date": "2026-01-15"})
    assert response.status_code == 500
