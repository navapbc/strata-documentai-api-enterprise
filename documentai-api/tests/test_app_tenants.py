"""Tests for tenant admin endpoints."""

from decimal import Decimal

import pytest

from documentai_api.app import app
from documentai_api.schemas.tenant_request_counts import TenantRequestCountRecord
from documentai_api.schemas.tenants import TenantRecord
from documentai_api.utils.dates import get_month_prefix, get_today_iso
from documentai_api.utils.jwt_auth import verify_jwt

URL = "/v1/admin/tenants"
SUPER_ADMIN = "super-admin"


def _make_claims(*, groups: list[str] | None = None, tenant_id: str | None = None):
    claims = {"sub": "test-user", "cognito:groups": groups or []}
    if tenant_id:
        claims["custom:tenant_id"] = tenant_id
    return claims


@pytest.fixture(autouse=True)
def _disable_auth(disable_auth):
    pass


@pytest.fixture(autouse=True)
def _super_admin_jwt():
    app.dependency_overrides[verify_jwt] = lambda: _make_claims(groups=[SUPER_ADMIN])
    yield
    app.dependency_overrides.pop(verify_jwt, None)


def _seed_tenant(tenants_table, tenant_id: str, max_per_day=None, max_per_month=None):
    item = {
        TenantRecord.TENANT_ID: tenant_id,
        TenantRecord.DISPLAY_NAME: "Test Tenant",
        TenantRecord.IS_ACTIVE: True,
    }
    if max_per_day is not None:
        item[TenantRecord.MAX_REQUESTS_PER_DAY] = max_per_day
    if max_per_month is not None:
        item[TenantRecord.MAX_REQUESTS_PER_MONTH] = max_per_month
    tenants_table.put_item(Item=item)


def _seed_counts(counts_table, tenant_id: str, date: str, count: int):
    counts_table.put_item(
        Item={
            TenantRequestCountRecord.TENANT_ID: tenant_id,
            TenantRequestCountRecord.DATE: date,
            TenantRequestCountRecord.COUNT: Decimal(count),
        }
    )


# =============================================================================
# CRUD
# =============================================================================


def test_create_tenant(api_client, tenants_table):
    response = api_client.post(URL, json={"tenant_id": "t1", "display_name": "Tenant One"})
    assert response.status_code == 201
    data = response.json()
    assert data["tenantId"] == "t1"
    assert data["displayName"] == "Tenant One"
    assert data["isActive"] is True


def test_create_tenant_duplicate_returns_409(api_client, tenants_table):
    api_client.post(URL, json={"tenant_id": "t1", "display_name": "Tenant One"})
    response = api_client.post(URL, json={"tenant_id": "t1", "display_name": "Duplicate"})
    assert response.status_code == 409


def test_create_tenant_with_rate_limits(api_client, tenants_table):
    response = api_client.post(
        URL,
        json={
            "tenant_id": "t1",
            "display_name": "T1",
            "max_requests_per_day": 100,
            "max_requests_per_month": 2000,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["maxRequestsPerDay"] == 100
    assert data["maxRequestsPerMonth"] == 2000


def test_list_tenants(api_client, tenants_table):
    api_client.post(URL, json={"tenant_id": "t1", "display_name": "One"})
    api_client.post(URL, json={"tenant_id": "t2", "display_name": "Two"})
    response = api_client.get(URL)
    assert response.status_code == 200
    assert response.json()["count"] == 2


def test_get_tenant(api_client, tenants_table):
    api_client.post(URL, json={"tenant_id": "t1", "display_name": "One"})
    response = api_client.get(f"{URL}/t1")
    assert response.status_code == 200
    assert response.json()["tenantId"] == "t1"


def test_get_tenant_not_found(api_client, tenants_table):
    response = api_client.get(f"{URL}/nonexistent")
    assert response.status_code == 404


def test_update_tenant(api_client, tenants_table):
    api_client.post(URL, json={"tenant_id": "t1", "display_name": "Old"})
    response = api_client.patch(f"{URL}/t1", json={"display_name": "New"})
    assert response.status_code == 200
    assert response.json()["displayName"] == "New"


def test_update_tenant_rate_limits(api_client, tenants_table):
    api_client.post(URL, json={"tenant_id": "t1", "display_name": "T1"})
    response = api_client.patch(f"{URL}/t1", json={"max_requests_per_day": 50})
    assert response.status_code == 200
    assert response.json()["maxRequestsPerDay"] == 50


def test_update_tenant_rate_limit_omitted_leaves_unchanged(api_client, tenants_table):
    """Omitting a quota field leaves the existing value unchanged."""
    api_client.post(
        URL, json={"tenant_id": "t1", "display_name": "T1", "max_requests_per_day": 100}
    )
    response = api_client.patch(f"{URL}/t1", json={"display_name": "Updated"})
    assert response.status_code == 200
    assert response.json()["maxRequestsPerDay"] == 100


def test_update_tenant_rate_limit_null_clears_limit(api_client, tenants_table):
    """Passing null for a quota field removes the limit entirely."""
    api_client.post(
        URL, json={"tenant_id": "t1", "display_name": "T1", "max_requests_per_day": 100}
    )
    response = api_client.patch(f"{URL}/t1", json={"max_requests_per_day": None})
    assert response.status_code == 200
    assert response.json()["maxRequestsPerDay"] is None


def test_delete_tenant(api_client, tenants_table):
    api_client.post(URL, json={"tenant_id": "t1", "display_name": "T1"})
    response = api_client.delete(f"{URL}/t1")
    assert response.status_code == 200
    assert response.json()["deleted"] is True


def test_delete_tenant_not_found(api_client, tenants_table):
    response = api_client.delete(f"{URL}/nonexistent")
    assert response.status_code == 404


def test_tenant_admin_cannot_set_quota_field(api_client, tenants_table):
    """Tenant-admin setting a quota field returns 403."""
    api_client.post(URL, json={"tenant_id": "t1", "display_name": "T1"})
    app.dependency_overrides[verify_jwt] = lambda: _make_claims(
        groups=["tenant-admin"], tenant_id="t1"
    )
    response = api_client.patch(f"{URL}/t1", json={"max_requests_per_day": 50})
    assert response.status_code == 403


def test_tenant_admin_cannot_clear_quota_field(api_client, tenants_table):
    """Tenant-admin clearing a quota field returns 403."""
    _seed_tenant(tenants_table, "t1", max_per_day=100)
    app.dependency_overrides[verify_jwt] = lambda: _make_claims(
        groups=["tenant-admin"], tenant_id="t1"
    )
    response = api_client.patch(f"{URL}/t1", json={"max_requests_per_day": None})
    assert response.status_code == 403


# =============================================================================
# GET /{tenant_id}/request-counts
# =============================================================================


def test_request_counts_empty(api_client, tenants_table, tenant_request_counts_table):
    _seed_tenant(tenants_table, "t1")
    response = api_client.get(f"{URL}/t1/request-counts")
    assert response.status_code == 200
    data = response.json()
    assert data["tenantId"] == "t1"
    assert data["monthlyTotal"] == 0
    assert data["daily"] == []


def test_request_counts_current_month_default(
    api_client, tenants_table, tenant_request_counts_table
):
    today = get_today_iso()
    _seed_tenant(tenants_table, "t1")
    _seed_counts(tenant_request_counts_table, "t1", today, 5)
    response = api_client.get(f"{URL}/t1/request-counts")
    assert response.status_code == 200
    data = response.json()
    assert data["month"] == get_month_prefix(today)
    assert data["monthlyTotal"] == 5
    assert len(data["daily"]) == 1
    assert data["daily"][0] == {"date": today, "count": 5}


def test_request_counts_sums_multiple_days(api_client, tenants_table, tenant_request_counts_table):
    today = get_today_iso()
    month = get_month_prefix(today)
    _seed_tenant(tenants_table, "t1")
    _seed_counts(tenant_request_counts_table, "t1", f"{month}-01", 10)
    _seed_counts(tenant_request_counts_table, "t1", f"{month}-02", 7)
    response = api_client.get(f"{URL}/t1/request-counts")
    assert response.status_code == 200
    data = response.json()
    assert data["monthlyTotal"] == 17
    assert len(data["daily"]) == 2


def test_request_counts_explicit_month(api_client, tenants_table, tenant_request_counts_table):
    _seed_tenant(tenants_table, "t1")
    _seed_counts(tenant_request_counts_table, "t1", "2025-03-15", 3)
    response = api_client.get(f"{URL}/t1/request-counts?month=2025-03")
    assert response.status_code == 200
    data = response.json()
    assert data["month"] == "2025-03"
    assert data["monthlyTotal"] == 3
    assert data["daily"][0]["date"] == "2025-03-15"


def test_request_counts_excludes_other_months(
    api_client, tenants_table, tenant_request_counts_table
):
    _seed_tenant(tenants_table, "t1")
    _seed_counts(tenant_request_counts_table, "t1", "2025-03-01", 10)
    _seed_counts(tenant_request_counts_table, "t1", "2025-04-01", 99)
    response = api_client.get(f"{URL}/t1/request-counts?month=2025-03")
    assert response.status_code == 200
    data = response.json()
    assert data["monthlyTotal"] == 10
    assert len(data["daily"]) == 1


def test_request_counts_daily_sorted_by_date(
    api_client, tenants_table, tenant_request_counts_table
):
    _seed_tenant(tenants_table, "t1")
    _seed_counts(tenant_request_counts_table, "t1", "2025-03-10", 1)
    _seed_counts(tenant_request_counts_table, "t1", "2025-03-02", 2)
    _seed_counts(tenant_request_counts_table, "t1", "2025-03-20", 3)
    response = api_client.get(f"{URL}/t1/request-counts?month=2025-03")
    assert response.status_code == 200
    dates = [d["date"] for d in response.json()["daily"]]
    assert dates == sorted(dates)
