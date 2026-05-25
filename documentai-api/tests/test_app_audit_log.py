"""Tests for GET /v1/admin/audit-log endpoint."""

import pytest
from fastapi.testclient import TestClient

from documentai_api.app import app
from documentai_api.schemas.audit_event import AuditAction, AuditTargetType
from documentai_api.utils.audit import log_event
from documentai_api.utils.jwt_auth import verify_jwt

AUDIT_LOG_URL = "/v1/admin/audit-log"

SUPER_ADMIN = "super-admin"
TENANT_ADMIN = "tenant-admin"

SUPER_ADMIN_CLAIMS = {
    "sub": "admin-001",
    "email": "admin@example.com",
    "token_use": "access",
    "cognito:groups": [SUPER_ADMIN],
}

TENANT_ADMIN_CLAIMS = {
    "sub": "user-001",
    "email": "user@example.com",
    "token_use": "access",
    "cognito:groups": [TENANT_ADMIN],
    "custom:tenant_id": "test-tenant",
}


def _override_jwt(claims: dict):
    app.dependency_overrides[verify_jwt] = lambda: claims


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.pop(verify_jwt, None)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def seeded_events(audit_events_table):
    """Seed audit events across multiple tenants."""
    # Super-admin creates a tenant (lands in __global__)
    log_event(
        SUPER_ADMIN_CLAIMS,
        action=AuditAction.TENANT_CREATE,
        target_type=AuditTargetType.TENANT,
        target_id="test-tenant",
    )
    # Tenant-admin creates a key for their own tenant (lands in "test-tenant")
    log_event(
        TENANT_ADMIN_CLAIMS,
        action=AuditAction.KEY_CREATE,
        target_type=AuditTargetType.KEY,
        target_id="abc12345",
        tenant_id="test-tenant",
    )
    # Super-admin revokes a key in another tenant (lands in "other-tenant")
    log_event(
        SUPER_ADMIN_CLAIMS,
        action=AuditAction.KEY_REVOKE,
        target_type=AuditTargetType.KEY,
        target_id="def67890",
        tenant_id="other-tenant",
    )


def test_audit_log_unauthenticated_returns_401(client):
    response = client.get(AUDIT_LOG_URL)
    assert response.status_code == 401


def test_audit_log_pending_user_returns_403(client):
    _override_jwt({**SUPER_ADMIN_CLAIMS, "cognito:groups": []})
    response = client.get(AUDIT_LOG_URL)
    assert response.status_code == 403


def test_audit_log_super_admin_queries_global(client, seeded_events):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(AUDIT_LOG_URL)
    assert response.status_code == 200
    data = response.json()
    # All 3 events appear in __global__ (1 direct + 2 double-writes)
    assert data["count"] == 3


def test_audit_log_super_admin_queries_by_tenant(client, seeded_events):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(AUDIT_LOG_URL, params={"tenant_id": "test-tenant"})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["events"][0]["action"] == AuditAction.KEY_CREATE


def test_audit_log_super_admin_queries_by_action(client, seeded_events):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(AUDIT_LOG_URL, params={"action": AuditAction.KEY_CREATE})
    assert response.status_code == 200
    data = response.json()
    # 2 items: tenant partition + __global__ double-write
    assert data["count"] == 2
    assert all(e["action"] == AuditAction.KEY_CREATE for e in data["events"])


def test_audit_log_tenant_admin_sees_own_only(client, seeded_events):
    _override_jwt(TENANT_ADMIN_CLAIMS)
    response = client.get(AUDIT_LOG_URL)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert all(e["tenantId"] == "test-tenant" for e in data["events"])


def test_audit_log_tenant_admin_cannot_query_other_tenant(client, seeded_events):
    _override_jwt(TENANT_ADMIN_CLAIMS)
    response = client.get(AUDIT_LOG_URL, params={"tenant_id": "other-tenant"})
    assert response.status_code == 403


def test_audit_log_respects_limit(client, audit_events_table):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    # Seed 5 events in __global__
    for i in range(5):
        log_event(
            SUPER_ADMIN_CLAIMS,
            action=AuditAction.TENANT_CREATE,
            target_type=AuditTargetType.TENANT,
            target_id=f"tenant-{i}",
        )
    response = client.get(AUDIT_LOG_URL, params={"limit": 3})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    assert data["nextCursor"] is not None


def test_audit_log_pagination(client, audit_events_table):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    for i in range(5):
        log_event(
            SUPER_ADMIN_CLAIMS,
            action=AuditAction.TENANT_CREATE,
            target_type=AuditTargetType.TENANT,
            target_id=f"tenant-{i}",
        )
    # First page
    resp1 = client.get(AUDIT_LOG_URL, params={"limit": 3})
    data1 = resp1.json()
    assert data1["count"] == 3
    # Second page
    resp2 = client.get(AUDIT_LOG_URL, params={"limit": 3, "cursor": data1["nextCursor"]})
    data2 = resp2.json()
    assert data2["count"] == 2
    assert data2["nextCursor"] is None


def test_audit_log_invalid_cursor_returns_400(client, audit_events_table):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(AUDIT_LOG_URL, params={"cursor": "not-valid-base64!"})
    assert response.status_code == 400


def test_audit_log_filter_by_action_and_tenant(client, seeded_events):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(
        AUDIT_LOG_URL, params={"tenant_id": "test-tenant", "action": AuditAction.KEY_CREATE}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["events"][0]["action"] == AuditAction.KEY_CREATE
    assert data["events"][0]["tenantId"] == "test-tenant"


##############################################################################
# GET /v1/admin/audit-log/actions
##############################################################################

ACTIONS_URL = "/v1/admin/audit-log/actions"


def test_actions_unauthenticated_returns_401(client):
    response = client.get(ACTIONS_URL)
    assert response.status_code == 401


def test_actions_returns_sorted_list(client):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(ACTIONS_URL)
    assert response.status_code == 200
    data = response.json()
    actions = data["actions"]
    assert isinstance(actions, list)
    assert len(actions) > 0
    assert actions == sorted(actions)


def test_actions_contains_known_actions(client):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(ACTIONS_URL)
    actions = response.json()["actions"]
    assert AuditAction.KEY_CREATE in actions
    assert AuditAction.TENANT_CREATE in actions
    assert AuditAction.USER_DELETE in actions


def test_actions_tenant_admin_can_access(client):
    _override_jwt(TENANT_ADMIN_CLAIMS)
    response = client.get(ACTIONS_URL)
    assert response.status_code == 200
    assert len(response.json()["actions"]) > 0
