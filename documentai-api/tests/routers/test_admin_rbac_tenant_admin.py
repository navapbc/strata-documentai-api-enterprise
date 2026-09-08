"""Tenant-admin RBAC tests - scoping, isolation, 403s."""

import hashlib

import pytest

from tests.helpers.fixtures.claims import SUPER_ADMIN, TENANT_ADMIN, make_claims, override_jwt

KEYS_URL = "/v1/admin/api-keys"
TENANTS_URL = "/v1/admin/tenants"
USERS_URL = "/v1/admin/users"

TENANT_ID = "test-tenant"
OTHER_TENANT_ID = "other-tenant"
NEW_TENANT = {"tenant_id": TENANT_ID, "display_name": "Test Tenant"}


@pytest.fixture
def seed_tenant(api_client, tenants_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.post(TENANTS_URL, json=NEW_TENANT)
    assert response.status_code == 201


# ==============================================================================
# Keys - tenant-admin
# ==============================================================================


def test_keys_tenant_admin_list_returns_200(api_client, api_keys_table):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id="tenant-a"))
    response = api_client.get(KEYS_URL)
    assert response.status_code == 200


def test_keys_tenant_admin_create_scoped_to_own_tenant(api_client, api_keys_table, tenants_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    api_client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.post(KEYS_URL, json={"api_key_name": "my-client", "environment": "dev"})
    assert response.status_code == 200
    assert response.json()["apiKeyName"] == "my-client"


def test_keys_tenant_admin_list_returns_own_only(api_client, api_keys_table, tenants_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    api_client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    api_client.post(TENANTS_URL, json={"tenant_id": OTHER_TENANT_ID, "display_name": "Other"})
    api_client.post(
        KEYS_URL,
        json={"api_key_name": "global-client", "environment": "dev", "tenant_id": OTHER_TENANT_ID},
    )
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    api_client.post(KEYS_URL, json={"api_key_name": "tenant-client", "environment": "dev"})

    response = api_client.get(KEYS_URL)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["keys"][0]["apiKeyName"] == "tenant-client"


def test_keys_tenant_admin_delete_own_returns_200(api_client, api_keys_table, tenants_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    api_client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    api_client.post(KEYS_URL, json={"api_key_name": "to-delete", "environment": "dev"})
    list_resp = api_client.get(KEYS_URL)
    key_prefix = list_resp.json()["keys"][0]["keyPrefix"]
    response = api_client.delete(f"{KEYS_URL}/{key_prefix}")
    assert response.status_code == 200
    assert response.json()["deactivated"] is True


def test_keys_tenant_admin_delete_other_returns_404(api_client, api_keys_table, tenants_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    api_client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    api_client.post(TENANTS_URL, json={"tenant_id": OTHER_TENANT_ID, "display_name": "Other"})
    api_client.post(
        KEYS_URL,
        json={"api_key_name": "other-key", "environment": "dev", "tenant_id": OTHER_TENANT_ID},
    )
    list_resp = api_client.get(KEYS_URL, params={"tenant_id": OTHER_TENANT_ID})
    key_prefix = list_resp.json()["keys"][0]["keyPrefix"]

    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.delete(f"{KEYS_URL}/{key_prefix}")
    assert response.status_code == 404


def test_keys_delete_full_hash_other_tenant_returns_404(api_client, api_keys_table, tenants_table):
    """Tenant-admin sending full hash of another tenant's key gets 404."""
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    api_client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    api_client.post(TENANTS_URL, json={"tenant_id": OTHER_TENANT_ID, "display_name": "Other"})
    create_resp = api_client.post(
        KEYS_URL,
        json={"api_key_name": "other-key", "environment": "dev", "tenant_id": OTHER_TENANT_ID},
    )
    raw_key = create_resp.json()["apiKey"]
    full_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.delete(f"{KEYS_URL}/{full_hash}")
    assert response.status_code == 404


def test_keys_tenant_admin_no_tenant_in_jwt_returns_403(api_client, api_keys_table):
    override_jwt(make_claims(groups=[TENANT_ADMIN]))
    response = api_client.get(KEYS_URL)
    assert response.status_code == 403


def test_keys_tenant_admin_no_tenant_in_jwt_create_returns_403(api_client, api_keys_table):
    override_jwt(make_claims(groups=[TENANT_ADMIN]))
    response = api_client.post(KEYS_URL, json={"api_key_name": "test", "environment": "dev"})
    assert response.status_code == 403


def test_keys_tenant_admin_body_tenant_id_ignored(api_client, api_keys_table, tenants_table):
    """Tenant-admin's body tenant_id is ignored - key is scoped to their JWT tenant."""
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    api_client.post(TENANTS_URL, json={"tenant_id": TENANT_ID, "display_name": "Test"})
    api_client.post(TENANTS_URL, json={"tenant_id": OTHER_TENANT_ID, "display_name": "Other"})

    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.post(
        KEYS_URL,
        json={"api_key_name": "spoofed", "environment": "dev", "tenant_id": OTHER_TENANT_ID},
    )
    assert response.status_code == 200
    list_resp = api_client.get(KEYS_URL)
    assert list_resp.json()["count"] == 1


# ==============================================================================
# Tenants - tenant-admin
# ==============================================================================


def test_tenants_tenant_admin_create_returns_403(api_client, tenants_table):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.post(
        TENANTS_URL, json={"tenant_id": OTHER_TENANT_ID, "display_name": "Other"}
    )
    assert response.status_code == 403


def test_tenants_tenant_admin_list_returns_own_only(api_client, seed_tenant):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.get(TENANTS_URL)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["tenants"][0]["tenantId"] == TENANT_ID


def test_tenants_tenant_admin_get_own_returns_200(api_client, seed_tenant):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.get(f"{TENANTS_URL}/{TENANT_ID}")
    assert response.status_code == 200
    assert response.json()["tenantId"] == TENANT_ID


def test_tenants_tenant_admin_get_other_returns_403(api_client, seed_tenant):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.get(f"{TENANTS_URL}/{OTHER_TENANT_ID}")
    assert response.status_code == 403


def test_tenants_tenant_admin_update_own_returns_200(api_client, seed_tenant):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.patch(f"{TENANTS_URL}/{TENANT_ID}", json={"display_name": "New Name"})
    assert response.status_code == 200
    assert response.json()["displayName"] == "New Name"


def test_tenants_tenant_admin_update_other_returns_403(api_client, seed_tenant):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.patch(f"{TENANTS_URL}/{OTHER_TENANT_ID}", json={"display_name": "Nope"})
    assert response.status_code == 403


def test_tenants_tenant_admin_update_is_active_forbidden(api_client, seed_tenant):
    """A tenant-admin PATCH including a super-admin-only field returns 403.

    Rejected wholesale - even alongside a field they may otherwise change.
    """
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.patch(
        f"{TENANTS_URL}/{TENANT_ID}", json={"display_name": "New Name", "is_active": False}
    )
    assert response.status_code == 403


def test_tenants_tenant_admin_update_primary_contact(api_client, seed_tenant):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.patch(
        f"{TENANTS_URL}/{TENANT_ID}", json={"primary_contact": "new@example.com"}
    )
    assert response.status_code == 200
    assert response.json()["primaryContact"] == "new@example.com"


def test_tenants_tenant_admin_delete_own_returns_403(api_client, seed_tenant):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.delete(f"{TENANTS_URL}/{TENANT_ID}")
    assert response.status_code == 403


def test_tenants_tenant_admin_delete_other_returns_403(api_client, seed_tenant):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.delete(f"{TENANTS_URL}/{OTHER_TENANT_ID}")
    assert response.status_code == 403


def test_tenants_tenant_admin_no_tenant_in_jwt_returns_403(api_client, tenants_table):
    override_jwt(make_claims(groups=[TENANT_ADMIN]))
    response = api_client.get(TENANTS_URL)
    assert response.status_code == 403


# ==============================================================================
# Users - tenant-admin (all 403)
# ==============================================================================


def test_users_tenant_admin_list_returns_403(api_client):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.get(USERS_URL)
    assert response.status_code == 403


def test_users_tenant_admin_approve_returns_403(api_client):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.post(
        f"{USERS_URL}/new-user/approve",
        json={"role": "tenant-admin", "tenant_id": TENANT_ID},
    )
    assert response.status_code == 403


def test_users_tenant_admin_delete_returns_403(api_client):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.delete(f"{USERS_URL}/some-user")
    assert response.status_code == 403
