"""Super-admin RBAC tests - CRUD, edge cases, audit events."""

import hashlib
from collections import Counter
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from documentai_api.app import app
from documentai_api.schemas.audit_event import AuditAction, AuditEventRecord
from documentai_api.utils.jwt_auth import verify_jwt

KEYS_URL = "/v1/admin/api-keys"
TENANTS_URL = "/v1/admin/tenants"
USERS_URL = "/v1/admin/users"

TENANT_ID = "test-tenant"
OTHER_TENANT_ID = "other-tenant"
MISSING_TENANT_ID = "missing"
NEW_TENANT = {"tenant_id": TENANT_ID, "display_name": "Test Tenant"}

SUPER_ADMIN = "super-admin"


def _make_claims(*, groups: list[str] | None = None, tenant_id: str | None = None):
    claims = {
        "sub": "test-user",
        "email": "test@example.com",
        "token_use": "access",
        "cognito:groups": groups or [],
    }
    if tenant_id:
        claims["custom:tenant_id"] = tenant_id
    return claims


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
def seed_tenant(client, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(TENANTS_URL, json=NEW_TENANT)
    assert response.status_code == 201


# ==============================================================================
# Keys - super-admin
# ==============================================================================


def test_keys_super_admin_list_returns_200(client, api_keys_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.get(KEYS_URL)
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_keys_super_admin_create_returns_200(
    client, api_keys_table, tenants_table, audit_events_table
):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    response = client.post(
        KEYS_URL, json={"api_key_name": "test-client", "environment": "dev", "tenant_id": TENANT_ID}
    )
    assert response.status_code == 200
    data = response.json()
    assert "apiKey" in data
    assert data["apiKeyName"] == "test-client"
    items = audit_events_table.scan()["Items"]
    actions = [i[AuditEventRecord.ACTION] for i in items]
    assert AuditAction.KEY_CREATE in actions


def test_keys_super_admin_create_no_tenant_returns_400(client, api_keys_table, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(KEYS_URL, json={"api_key_name": "test", "environment": "dev"})
    assert response.status_code == 400
    assert "tenant_id is required" in response.json()["detail"]


def test_keys_create_nonexistent_tenant_returns_400(client, api_keys_table, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(
        KEYS_URL, json={"api_key_name": "test", "environment": "dev", "tenant_id": "nonexistent"}
    )
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_keys_create_missing_api_key_name_returns_422(client, api_keys_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(KEYS_URL, json={})
    assert response.status_code == 422


def test_keys_create_invalid_json_returns_422(client, api_keys_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(
        KEYS_URL, content="not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422


def test_keys_list_include_inactive(client, api_keys_table, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    client.post(
        KEYS_URL, json={"api_key_name": "to-revoke", "environment": "dev", "tenant_id": TENANT_ID}
    )
    list_resp = client.get(KEYS_URL, params={"tenant_id": TENANT_ID})
    key_prefix = list_resp.json()["keys"][0]["keyPrefix"]
    client.delete(f"{KEYS_URL}/{key_prefix}")

    resp = client.get(KEYS_URL, params={"tenant_id": TENANT_ID})
    assert resp.json()["count"] == 0

    resp = client.get(KEYS_URL, params={"tenant_id": TENANT_ID, "include_inactive": "true"})
    assert resp.json()["count"] == 1
    assert resp.json()["keys"][0]["isActive"] is False


def test_keys_list_filter_by_api_key_name(client, api_keys_table, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    client.post(
        KEYS_URL, json={"api_key_name": "alpha", "environment": "dev", "tenant_id": TENANT_ID}
    )
    client.post(
        KEYS_URL, json={"api_key_name": "beta", "environment": "dev", "tenant_id": TENANT_ID}
    )

    resp = client.get(KEYS_URL, params={"tenant_id": TENANT_ID, "api_key_name": "alpha"})
    assert resp.json()["count"] == 1
    assert resp.json()["keys"][0]["apiKeyName"] == "alpha"


def test_keys_list_super_admin_filter_by_tenant(client, api_keys_table, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    client.post(TENANTS_URL, json={"tenant_id": OTHER_TENANT_ID, "display_name": "Other"})
    client.post(KEYS_URL, json={"api_key_name": "a", "environment": "dev", "tenant_id": TENANT_ID})
    client.post(
        KEYS_URL, json={"api_key_name": "b", "environment": "dev", "tenant_id": OTHER_TENANT_ID}
    )

    resp = client.get(KEYS_URL, params={"tenant_id": TENANT_ID})
    assert resp.json()["count"] == 1
    assert resp.json()["keys"][0]["apiKeyName"] == "a"


def test_keys_delete_by_full_hash(client, api_keys_table, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    create_resp = client.post(
        KEYS_URL, json={"api_key_name": "full-hash", "environment": "dev", "tenant_id": TENANT_ID}
    )
    raw_key = create_resp.json()["apiKey"]
    full_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    response = client.delete(f"{KEYS_URL}/{full_hash}")
    assert response.status_code == 200
    assert response.json()["deactivated"] is True


def test_keys_delete_ambiguous_prefix_returns_409(client, api_keys_table, tenants_table):
    """When multiple active keys share a prefix, delete should return 409."""
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    for i in range(10):
        client.post(
            KEYS_URL,
            json={"api_key_name": f"client-{i}", "environment": "dev", "tenant_id": TENANT_ID},
        )
    list_resp = client.get(KEYS_URL)
    keys = list_resp.json()["keys"]
    prefixes = Counter(k["keyPrefix"][0] for k in keys)
    ambiguous = [char for char, count in prefixes.items() if count > 1]
    if not ambiguous:
        pytest.skip("No ambiguous prefix generated in random keys")
    response = client.delete(f"{KEYS_URL}/{ambiguous[0]}")
    assert response.status_code == 409


def test_keys_revoke_writes_audit_event(client, api_keys_table, tenants_table, audit_events_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    client.post(
        KEYS_URL, json={"api_key_name": "audit-test", "environment": "dev", "tenant_id": TENANT_ID}
    )
    list_resp = client.get(KEYS_URL, params={"tenant_id": TENANT_ID})
    key_prefix = list_resp.json()["keys"][0]["keyPrefix"]
    client.delete(f"{KEYS_URL}/{key_prefix}")

    items = audit_events_table.scan()["Items"]
    actions = [i[AuditEventRecord.ACTION] for i in items]
    assert AuditAction.KEY_REVOKE in actions


# ==============================================================================
# Tenants - super-admin
# ==============================================================================


def test_tenants_super_admin_list_returns_200(client, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.get(TENANTS_URL)
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_tenants_super_admin_create_returns_201(client, tenants_table, audit_events_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(TENANTS_URL, json=NEW_TENANT)
    assert response.status_code == 201
    assert response.json()["tenantId"] == TENANT_ID
    items = audit_events_table.scan()["Items"]
    assert len(items) == 1
    assert items[0][AuditEventRecord.ACTION] == AuditAction.TENANT_CREATE
    assert items[0][AuditEventRecord.TARGET_ID] == TENANT_ID


def test_tenants_super_admin_create_duplicate_returns_409(client, seed_tenant):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(TENANTS_URL, json=NEW_TENANT)
    assert response.status_code == 409


def test_tenants_super_admin_get_returns_200(client, seed_tenant):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.get(f"{TENANTS_URL}/{TENANT_ID}")
    assert response.status_code == 200
    assert response.json()["displayName"] == "Test Tenant"


def test_tenants_super_admin_get_not_found_returns_404(client, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.get(f"{TENANTS_URL}/{MISSING_TENANT_ID}")
    assert response.status_code == 404


def test_tenants_super_admin_update_returns_200(client, seed_tenant):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.patch(f"{TENANTS_URL}/{TENANT_ID}", json={"display_name": "Updated Name"})
    assert response.status_code == 200
    assert response.json()["displayName"] == "Updated Name"


def test_tenants_super_admin_delete_returns_200(client, tenants_table, audit_events_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(TENANTS_URL, json=NEW_TENANT)
    response = client.delete(f"{TENANTS_URL}/{TENANT_ID}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True
    items = audit_events_table.scan()["Items"]
    actions = [i[AuditEventRecord.ACTION] for i in items]
    assert AuditAction.TENANT_DEACTIVATE in actions


def test_tenants_super_admin_delete_not_found_returns_404(client, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.delete(f"{TENANTS_URL}/{MISSING_TENANT_ID}")
    assert response.status_code == 404


def test_tenants_create_missing_required_fields_returns_422(client, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(TENANTS_URL, json={})
    assert response.status_code == 422


def test_tenants_create_invalid_tenant_id_returns_422(client, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(TENANTS_URL, json={"tenant_id": "INVALID!!", "display_name": "X"})
    assert response.status_code == 422


def test_tenants_create_tenant_id_too_long_returns_422(client, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(TENANTS_URL, json={"tenant_id": "a" * 129, "display_name": "X"})
    assert response.status_code == 422


def test_tenants_create_display_name_too_long_returns_422(client, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(TENANTS_URL, json={"tenant_id": "valid-id", "display_name": "x" * 256})
    assert response.status_code == 422


def test_tenants_create_empty_display_name_returns_422(client, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(TENANTS_URL, json={"tenant_id": "valid-id", "display_name": ""})
    assert response.status_code == 422


def test_tenants_create_invalid_json_returns_422(client, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(
        TENANTS_URL, content="not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422


def test_tenants_update_empty_body_returns_400(client, seed_tenant):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.patch(f"{TENANTS_URL}/{TENANT_ID}", json={})
    assert response.status_code == 400


def test_tenants_update_deactivated_tenant(client, seed_tenant):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.delete(f"{TENANTS_URL}/{TENANT_ID}")
    response = client.patch(f"{TENANTS_URL}/{TENANT_ID}", json={"is_active": True})
    assert response.status_code == 200
    assert response.json()["isActive"] is True


def test_tenants_update_writes_audit_event(client, tenants_table, audit_events_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(TENANTS_URL, json=NEW_TENANT)
    client.patch(f"{TENANTS_URL}/{TENANT_ID}", json={"display_name": "Updated"})

    items = audit_events_table.scan()["Items"]
    actions = [i[AuditEventRecord.ACTION] for i in items]
    assert AuditAction.TENANT_UPDATE in actions


# ==============================================================================
# Users - super-admin
# ==============================================================================


def test_users_super_admin_returns_200(client):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    with patch("documentai_api.services.cognito.list_users", return_value=[]):
        response = client.get(USERS_URL)
    assert response.status_code == 200


def test_users_approve_happy_path(client):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    with (
        patch("documentai_api.services.cognito.replace_role") as mock_role,
        patch("documentai_api.services.cognito.set_tenant") as mock_tenant,
    ):
        response = client.post(
            f"{USERS_URL}/new-user/approve",
            json={"role": "tenant-admin", "tenant_id": "acme"},
        )
    assert response.status_code == 200
    assert response.json()["role"] == "tenant-admin"
    mock_role.assert_called_once_with("new-user", "tenant-admin")
    mock_tenant.assert_called_once_with("new-user", "acme")


def test_users_approve_super_admin_clears_tenant(client):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    with (
        patch("documentai_api.services.cognito.replace_role"),
        patch("documentai_api.services.cognito.set_tenant") as mock_tenant,
    ):
        response = client.post(
            f"{USERS_URL}/new-user/approve",
            json={"role": "super-admin"},
        )
    assert response.status_code == 200
    mock_tenant.assert_called_once_with("new-user", None)


def test_users_approve_tenant_admin_requires_tenant_id(client):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(
        f"{USERS_URL}/new-user/approve",
        json={"role": "tenant-admin"},
    )
    assert response.status_code == 400


def test_users_change_role(client):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    with patch("documentai_api.services.cognito.replace_role") as mock_role:
        response = client.post(f"{USERS_URL}/some-user/role", json={"role": "super-admin"})
    assert response.status_code == 200
    mock_role.assert_called_once_with("some-user", "super-admin")


def test_users_change_role_revoke(client):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    with patch("documentai_api.services.cognito.replace_role") as mock_role:
        response = client.post(f"{USERS_URL}/some-user/role", json={"role": None})
    assert response.status_code == 200
    mock_role.assert_called_once_with("some-user", None)


def test_users_change_tenant(client):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    with patch("documentai_api.services.cognito.set_tenant") as mock_tenant:
        response = client.post(f"{USERS_URL}/some-user/tenant", json={"tenant_id": "new-tenant"})
    assert response.status_code == 200
    mock_tenant.assert_called_once_with("some-user", "new-tenant")


def test_users_change_tenant_clear(client):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    with patch("documentai_api.services.cognito.set_tenant") as mock_tenant:
        response = client.post(f"{USERS_URL}/some-user/tenant", json={"tenant_id": None})
    assert response.status_code == 200
    mock_tenant.assert_called_once_with("some-user", None)


def test_users_delete_user(client):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    with patch("documentai_api.services.cognito.delete_user") as mock_delete:
        response = client.delete(f"{USERS_URL}/other-user")
    assert response.status_code == 200
    assert response.json()["deleted"] is True
    mock_delete.assert_called_once_with("other-user")


def test_users_delete_self_returns_400(client):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.delete(f"{USERS_URL}/test-user")
    assert response.status_code == 400
    assert "cannot delete your own" in response.json()["detail"].lower()
