"""Tenant-admin RBAC tests - scoping, isolation, 403s."""

import hashlib

import pytest
from fastapi.testclient import TestClient

from documentai_api.app import app
from documentai_api.utils.jwt_auth import verify_jwt

KEYS_URL = "/v1/admin/api-keys"
TENANTS_URL = "/v1/admin/tenants"
USERS_URL = "/v1/admin/users"

TENANT_ID = "test-tenant"
OTHER_TENANT_ID = "other-tenant"
NEW_TENANT = {"tenant_id": TENANT_ID, "display_name": "Test Tenant"}

SUPER_ADMIN = "super-admin"
TENANT_ADMIN = "tenant-admin"


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
# Keys - tenant-admin
# ==============================================================================


def test_keys_tenant_admin_list_returns_200(client, api_keys_table):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id="tenant-a"))
    response = client.get(KEYS_URL)
    assert response.status_code == 200


def test_keys_tenant_admin_create_scoped_to_own_tenant(client, api_keys_table, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.post(KEYS_URL, json={"api_key_name": "my-client", "environment": "dev"})
    assert response.status_code == 200
    assert response.json()["apiKeyName"] == "my-client"


def test_keys_tenant_admin_list_returns_own_only(client, api_keys_table, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    client.post(TENANTS_URL, json={"tenant_id": OTHER_TENANT_ID, "display_name": "Other"})
    client.post(
        KEYS_URL,
        json={"api_key_name": "global-client", "environment": "dev", "tenant_id": OTHER_TENANT_ID},
    )
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    client.post(KEYS_URL, json={"api_key_name": "tenant-client", "environment": "dev"})

    response = client.get(KEYS_URL)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["keys"][0]["apiKeyName"] == "tenant-client"


def test_keys_tenant_admin_delete_own_returns_200(client, api_keys_table, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    client.post(KEYS_URL, json={"api_key_name": "to-delete", "environment": "dev"})
    list_resp = client.get(KEYS_URL)
    key_prefix = list_resp.json()["keys"][0]["keyPrefix"]
    response = client.delete(f"{KEYS_URL}/{key_prefix}")
    assert response.status_code == 200
    assert response.json()["deactivated"] is True


def test_keys_tenant_admin_delete_other_returns_404(client, api_keys_table, tenants_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    client.post(TENANTS_URL, json={"tenant_id": OTHER_TENANT_ID, "display_name": "Other"})
    client.post(
        KEYS_URL,
        json={"api_key_name": "other-key", "environment": "dev", "tenant_id": OTHER_TENANT_ID},
    )
    list_resp = client.get(KEYS_URL, params={"tenant_id": OTHER_TENANT_ID})
    key_prefix = list_resp.json()["keys"][0]["keyPrefix"]

    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.delete(f"{KEYS_URL}/{key_prefix}")
    assert response.status_code == 404


def test_keys_delete_full_hash_other_tenant_returns_404(client, api_keys_table, tenants_table):
    """Tenant-admin sending full hash of another tenant's key gets 404."""
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    client.post(TENANTS_URL, json={"tenant_id": OTHER_TENANT_ID, "display_name": "Other"})
    create_resp = client.post(
        KEYS_URL,
        json={"api_key_name": "other-key", "environment": "dev", "tenant_id": OTHER_TENANT_ID},
    )
    raw_key = create_resp.json()["apiKey"]
    full_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.delete(f"{KEYS_URL}/{full_hash}")
    assert response.status_code == 404


def test_keys_tenant_admin_no_tenant_in_jwt_returns_403(client, api_keys_table):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN]))
    response = client.get(KEYS_URL)
    assert response.status_code == 403


def test_keys_tenant_admin_no_tenant_in_jwt_create_returns_403(client, api_keys_table):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN]))
    response = client.post(KEYS_URL, json={"api_key_name": "test", "environment": "dev"})
    assert response.status_code == 403


def test_keys_tenant_admin_body_tenant_id_ignored(client, api_keys_table, tenants_table):
    """Tenant-admin's body tenant_id is ignored - key is scoped to their JWT tenant."""
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    client.post(TENANTS_URL, json={"tenant_id": OTHER_TENANT_ID, "display_name": "Other"})

    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.post(
        KEYS_URL,
        json={"api_key_name": "spoofed", "environment": "dev", "tenant_id": OTHER_TENANT_ID},
    )
    assert response.status_code == 200
    list_resp = client.get(KEYS_URL)
    assert list_resp.json()["count"] == 1


# ==============================================================================
# Tenants - tenant-admin
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


def test_tenants_tenant_admin_update_primary_contact(client, seed_tenant):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.patch(
        f"{TENANTS_URL}/{TENANT_ID}", json={"primary_contact": "new@example.com"}
    )
    assert response.status_code == 200
    assert response.json()["primaryContact"] == "new@example.com"


def test_tenants_tenant_admin_delete_own_returns_403(client, seed_tenant):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.delete(f"{TENANTS_URL}/{TENANT_ID}")
    assert response.status_code == 403


def test_tenants_tenant_admin_delete_other_returns_403(client, seed_tenant):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.delete(f"{TENANTS_URL}/{OTHER_TENANT_ID}")
    assert response.status_code == 403


def test_tenants_tenant_admin_no_tenant_in_jwt_returns_403(client, tenants_table):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN]))
    response = client.get(TENANTS_URL)
    assert response.status_code == 403


# ==============================================================================
# Users - tenant-admin (all 403)
# ==============================================================================


def test_users_tenant_admin_list_returns_403(client):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.get(USERS_URL)
    assert response.status_code == 403


def test_users_tenant_admin_approve_returns_403(client):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.post(
        f"{USERS_URL}/new-user/approve",
        json={"role": "tenant-admin", "tenant_id": TENANT_ID},
    )
    assert response.status_code == 403


def test_users_tenant_admin_delete_returns_403(client):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.delete(f"{USERS_URL}/some-user")
    assert response.status_code == 403
