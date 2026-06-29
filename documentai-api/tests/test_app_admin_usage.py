"""Tests for GET /v1/admin/usage endpoint."""

import json

import pytest
from fastapi.testclient import TestClient

from documentai_api.app import app
from documentai_api.config.env import EnvVars
from documentai_api.utils.jwt_auth import verify_jwt

USAGE_URL = "/v1/admin/usage"

SUPER_ADMIN_CLAIMS = {
    "sub": "admin-001",
    "email": "admin@example.com",
    "token_use": "access",
    "cognito:groups": ["super-admin"],
}

TENANT_ADMIN_CLAIMS = {
    "sub": "user-001",
    "email": "user@example.com",
    "token_use": "access",
    "cognito:groups": ["tenant-admin"],
    "custom:tenant_id": "tenant-a",
}


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def as_super_admin(client):
    app.dependency_overrides[verify_jwt] = lambda: SUPER_ADMIN_CLAIMS
    return client


@pytest.fixture
def as_tenant_admin(client):
    app.dependency_overrides[verify_jwt] = lambda: TENANT_ADMIN_CLAIMS
    return client


@pytest.fixture
def metrics_bucket(s3_bucket, monkeypatch):
    monkeypatch.setenv(EnvVars.DDB_EXPORT_BUCKET_NAME, s3_bucket.name)
    return s3_bucket


def _put_monthly_report(bucket, month: str, tenants: list[dict]):
    report = {"month": month, "report_type": "usage_only", "tenants": tenants}
    bucket.put_object(
        Key=f"usage-report/month={month}/report.json",
        Body=json.dumps(report),
    )


def _put_daily_stats(bucket, date: str, stats: dict, tenant_id: str | None = None):
    if tenant_id:
        key = f"aggregated/utc/date={date}/tenant={tenant_id}/stats.json"
    else:
        key = f"aggregated/utc/date={date}/stats.json"
    bucket.put_object(Key=key, Body=json.dumps(stats))


def _make_daily_stats(date: str, total_records: int = 10):
    return {
        "date": date,
        "total_records": total_records,
        "total_bda_invocations": total_records - 2,
        "usage_stats": {
            "total_file_size_bytes": total_records * 500000,
            "total_pages": total_records,
            "total_bda_pages": total_records - 2,
            "total_bedrock_input_tokens": total_records * 2000,
            "total_bedrock_output_tokens": total_records * 100,
        },
    }


TENANT_A = {
    "tenant_id": "tenant-a",
    "total_records": 100,
    "total_bda_invocations": 80,
    "total_file_size_bytes": 50000000,
    "total_bda_pages": 75,
    "total_bedrock_input_tokens": 200000,
    "total_bedrock_output_tokens": 10000,
}

TENANT_B = {
    "tenant_id": "tenant-b",
    "total_records": 50,
    "total_bda_invocations": 40,
    "total_file_size_bytes": 25000000,
    "total_bda_pages": 38,
    "total_bedrock_input_tokens": 100000,
    "total_bedrock_output_tokens": 5000,
}


@pytest.fixture
def seeded_monthly(metrics_bucket):
    _put_monthly_report(metrics_bucket, "2026-06", [TENANT_A, TENANT_B])


@pytest.fixture
def seeded_daily(metrics_bucket):
    for day in range(1, 4):
        _put_daily_stats(metrics_bucket, f"2026-06-{day:02d}", _make_daily_stats(f"2026-06-{day:02d}", 10))
    _put_daily_stats(
        metrics_bucket, "2026-06-01", _make_daily_stats("2026-06-01", 5), tenant_id="tenant-a"
    )


##############################################################################
# Monthly
##############################################################################


def test_monthly_returns_all_tenants(as_super_admin, seeded_monthly):
    response = as_super_admin.get(USAGE_URL, params={"month": "2026-06"})
    assert response.status_code == 200
    data = response.json()
    assert data["month"] == "2026-06"
    assert data["granularity"] == "monthly"
    assert len(data["tenants"]) == 2


def test_monthly_empty_when_no_report(as_super_admin, metrics_bucket):
    response = as_super_admin.get(USAGE_URL, params={"month": "2026-01"})
    assert response.status_code == 200
    assert response.json()["tenants"] == []


def test_monthly_defaults_to_current_month(as_super_admin, metrics_bucket):
    response = as_super_admin.get(USAGE_URL)
    assert response.status_code == 200
    from datetime import UTC, datetime

    assert response.json()["month"] == datetime.now(UTC).strftime("%Y-%m")


def test_monthly_tenant_scoping(as_tenant_admin, seeded_monthly):
    response = as_tenant_admin.get(USAGE_URL, params={"month": "2026-06"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["tenants"]) == 1
    assert data["tenants"][0]["tenant_id"] == "tenant-a"


def test_monthly_csv_format(as_super_admin, seeded_monthly):
    response = as_super_admin.get(USAGE_URL, params={"month": "2026-06", "format": "csv"})
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    lines = response.text.strip().split("\n")
    assert len(lines) == 3  # header + 2 tenants


##############################################################################
# Daily
##############################################################################


def test_daily_returns_days(as_super_admin, seeded_daily):
    response = as_super_admin.get(USAGE_URL, params={"month": "2026-06", "granularity": "daily"})
    assert response.status_code == 200
    data = response.json()
    assert data["granularity"] == "daily"
    assert len(data["days"]) == 3


def test_daily_tenant_scoped(as_tenant_admin, seeded_daily):
    response = as_tenant_admin.get(USAGE_URL, params={"month": "2026-06", "granularity": "daily"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["days"]) == 1
    assert data["days"][0]["total_records"] == 5


def test_daily_super_admin_filters_by_tenant_id(as_super_admin, seeded_daily):
    response = as_super_admin.get(
        USAGE_URL, params={"month": "2026-06", "granularity": "daily", "tenant_id": "tenant-a"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["days"]) == 1
    assert data["days"][0]["total_records"] == 5


def test_daily_csv_format(as_super_admin, seeded_daily):
    response = as_super_admin.get(
        USAGE_URL, params={"month": "2026-06", "granularity": "daily", "format": "csv"}
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]


##############################################################################
# Validation
##############################################################################


def test_invalid_month_returns_400(as_super_admin, metrics_bucket):
    response = as_super_admin.get(USAGE_URL, params={"month": "abc"})
    assert response.status_code == 400
    assert "YYYY-MM" in response.json()["detail"]


def test_invalid_month_number_returns_400(as_super_admin, metrics_bucket):
    response = as_super_admin.get(USAGE_URL, params={"month": "2026-13"})
    assert response.status_code == 400


##############################################################################
# Auth
##############################################################################


def test_unauthenticated_returns_401(client, metrics_bucket):
    response = client.get(USAGE_URL)
    assert response.status_code == 401


##############################################################################
# Error handling
##############################################################################


def test_bucket_not_configured(as_super_admin, monkeypatch):
    monkeypatch.delenv(EnvVars.DDB_EXPORT_BUCKET_NAME, raising=False)
    response = as_super_admin.get(USAGE_URL, params={"month": "2026-06"})
    assert response.status_code == 500
    assert "not configured" in response.json()["detail"]
