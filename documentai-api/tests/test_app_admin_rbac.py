"""Tests for admin endpoint RBAC — verifies role-based access control."""

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
TENANT_ADMIN = "tenant-admin"


# --- Helpers ---


def _make_claims(*, groups: list[str] | None = None, tenant_id: str | None = None):
    claims = {
        "sub": "user-123",
        "email": "test@example.com",
        "token_use": "access",
        "cognito:groups": groups or [],
    }
    if tenant_id:
        claims["custom:tenant_id"] = tenant_id
    return claims


def _override_jwt(claims: dict):
    app.dependency_overrides[verify_jwt] = lambda: claims


def _clear_overrides():
    app.dependency_overrides.pop(verify_jwt, None)


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    _clear_overrides()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def seed_tenant(client, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(TENANTS_URL, json=NEW_TENANT)


# ==============================================================================
# Admin API Keys — super-admin
# ==============================================================================


def test_keys_unauthenticated_returns_401(client):
    response = client.get(KEYS_URL)
    assert response.status_code == 401


def test_keys_pending_user_returns_403(client):
    _override_jwt(_make_claims(groups=[]))
    response = client.get(KEYS_URL)
    assert response.status_code == 403


def test_keys_super_admin_list_returns_200(client, api_keys_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.get(KEYS_URL)
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_keys_tenant_admin_list_returns_200(client, api_keys_table):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id="tenant-a"))
    response = client.get(KEYS_URL)
    assert response.status_code == 200


def test_keys_super_admin_create_returns_200(client, api_keys_table, audit_events_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(KEYS_URL, json={"client_name": "test-client", "environment": "dev"})
    assert response.status_code == 200
    data = response.json()
    assert "apiKey" in data
    assert data["clientName"] == "test-client"
    # Verify audit event written
    items = audit_events_table.scan()["Items"]
    assert len(items) == 1
    assert items[0][AuditEventRecord.ACTION] == AuditAction.KEY_CREATE


# ==============================================================================
# Admin API Keys — tenant-admin
# ==============================================================================


def test_keys_tenant_admin_create_scoped_to_own_tenant(client, api_keys_table):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.post(KEYS_URL, json={"client_name": "my-client", "environment": "dev"})
    assert response.status_code == 200
    assert response.json()["clientName"] == "my-client"


def test_keys_tenant_admin_list_returns_own_only(client, api_keys_table):
    # Create a key as super-admin (no tenant) and one as tenant-admin
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(KEYS_URL, json={"client_name": "global-client", "environment": "dev"})
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    client.post(KEYS_URL, json={"client_name": "tenant-client", "environment": "dev"})

    # Tenant-admin should only see their own key
    response = client.get(KEYS_URL)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["keys"][0]["clientName"] == "tenant-client"


def test_keys_tenant_admin_delete_own_returns_200(client, api_keys_table):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    client.post(KEYS_URL, json={"client_name": "to-delete", "environment": "dev"})
    # Get the hash prefix from the list endpoint
    list_resp = client.get(KEYS_URL)
    key_prefix = list_resp.json()["keys"][0]["keyPrefix"]
    response = client.delete(f"{KEYS_URL}/{key_prefix}")
    assert response.status_code == 200
    assert response.json()["deactivated"] is True


def test_keys_tenant_admin_delete_other_returns_404(client, api_keys_table):
    # Create key as super-admin (no tenant)
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    create_resp = client.post(KEYS_URL, json={"client_name": "other-key", "environment": "dev"})
    key_prefix = create_resp.json()["apiKey"][:8]

    # Tenant-admin tries to delete it
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.delete(f"{KEYS_URL}/{key_prefix}")
    assert response.status_code == 404


def test_keys_tenant_admin_no_tenant_in_jwt_returns_403(client, api_keys_table):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN]))
    response = client.get(KEYS_URL)
    assert response.status_code == 403


# ==============================================================================
# Admin Tenants — super-admin
# ==============================================================================


def test_tenants_unauthenticated_returns_401(client):
    response = client.get(TENANTS_URL)
    assert response.status_code == 401


def test_tenants_pending_user_returns_403(client):
    _override_jwt(_make_claims(groups=[]))
    response = client.get(TENANTS_URL)
    assert response.status_code == 403


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
    # Verify audit event written
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
    # Verify audit event written
    items = audit_events_table.scan()["Items"]
    actions = [i[AuditEventRecord.ACTION] for i in items]
    assert AuditAction.TENANT_DEACTIVATE in actions


def test_tenants_super_admin_delete_not_found_returns_404(client, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.delete(f"{TENANTS_URL}/{MISSING_TENANT_ID}")
    assert response.status_code == 404


# ==============================================================================
# Admin Tenants — tenant-admin
# ==============================================================================


def test_tenants_tenant_admin_create_returns_403(client, tenants_table):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.post(
        TENANTS_URL, json={"tenant_id": OTHER_TENANT_ID, "display_name": "Other"}
    )
    assert response.status_code == 403


def test_tenants_tenant_admin_list_returns_own_only(client, seed_tenant):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.get(TENANTS_URL)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["tenants"][0]["tenantId"] == TENANT_ID


def test_tenants_tenant_admin_get_own_returns_200(client, seed_tenant):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.get(f"{TENANTS_URL}/{TENANT_ID}")
    assert response.status_code == 200
    assert response.json()["tenantId"] == TENANT_ID


def test_tenants_tenant_admin_get_other_returns_403(client, seed_tenant):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.get(f"{TENANTS_URL}/{OTHER_TENANT_ID}")
    assert response.status_code == 403


def test_tenants_tenant_admin_update_own_returns_200(client, seed_tenant):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.patch(f"{TENANTS_URL}/{TENANT_ID}", json={"display_name": "New Name"})
    assert response.status_code == 200
    assert response.json()["displayName"] == "New Name"


def test_tenants_tenant_admin_update_other_returns_403(client, seed_tenant):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.patch(f"{TENANTS_URL}/{OTHER_TENANT_ID}", json={"display_name": "Nope"})
    assert response.status_code == 403


def test_tenants_tenant_admin_update_is_active_ignored(client, seed_tenant):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.patch(
        f"{TENANTS_URL}/{TENANT_ID}", json={"display_name": "Still Active", "is_active": False}
    )
    assert response.status_code == 200
    assert response.json()["isActive"] is True
    assert response.json()["displayName"] == "Still Active"


def test_tenants_tenant_admin_delete_own_returns_403(client, seed_tenant):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.delete(f"{TENANTS_URL}/{TENANT_ID}")
    assert response.status_code == 403


def test_tenants_tenant_admin_delete_other_returns_403(client, seed_tenant):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.delete(f"{TENANTS_URL}/{OTHER_TENANT_ID}")
    assert response.status_code == 403


# ==============================================================================
# Admin API Keys — edge cases
# ==============================================================================


def test_keys_create_missing_client_name_returns_422(client, api_keys_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(KEYS_URL, json={})
    assert response.status_code == 422


def test_keys_create_invalid_json_returns_422(client, api_keys_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(
        KEYS_URL, content="not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422


def test_keys_delete_ambiguous_prefix_returns_409(client, api_keys_table):
    """When multiple active keys share a prefix, delete should return 409."""
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    # Create several keys to increase chance of shared single-char prefix
    for i in range(10):
        client.post(KEYS_URL, json={"client_name": f"client-{i}", "environment": "dev"})
    # Use a single-char prefix which is likely ambiguous
    list_resp = client.get(KEYS_URL)
    keys = list_resp.json()["keys"]
    # Find a 1-char prefix shared by at least 2 keys
    from collections import Counter

    prefixes = Counter(k["keyPrefix"][0] for k in keys)
    ambiguous = [char for char, count in prefixes.items() if count > 1]
    if ambiguous:
        response = client.delete(f"{KEYS_URL}/{ambiguous[0]}")
        assert response.status_code == 409


# ==============================================================================
# Admin Tenants — edge cases
# ==============================================================================


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


def test_tenants_tenant_admin_no_tenant_in_jwt_returns_403(client, tenants_table):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN]))
    response = client.get(TENANTS_URL)
    assert response.status_code == 403


def test_tenants_update_empty_body_returns_400(client, seed_tenant):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.patch(f"{TENANTS_URL}/{TENANT_ID}", json={})
    assert response.status_code == 400


# ==============================================================================
# Admin Users
# ==============================================================================


def test_users_unauthenticated_returns_401(client):
    response = client.get(USERS_URL)
    assert response.status_code == 401


def test_users_pending_user_returns_403(client):
    _override_jwt(_make_claims(groups=[]))
    response = client.get(USERS_URL)
    assert response.status_code == 403


def test_users_super_admin_returns_200(client):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    with patch("documentai_api.services.cognito.list_users", return_value=[]):
        response = client.get(USERS_URL)
    assert response.status_code == 200
