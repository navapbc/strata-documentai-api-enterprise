"""Tests for /v1/admin/users - role assignment and tenant scope consistency.

The main thing under test is that a user's role (Cognito group) and tenant
scope (custom:tenant_id) can never drift apart: super-admins always have no
tenant scope, tenant-admins always have exactly one.
"""

import pytest

from tests.helpers.fixtures.claims import SUPER_ADMIN_CLAIMS, TENANT_ADMIN_CLAIMS, override_jwt
from tests.helpers.fixtures.cognito import create_cognito_user

USERS_URL = "/v1/admin/users"


@pytest.fixture
def acme_tenant(tenants_table):
    tenants_table.put_item(Item={"tenantId": "acme"})
    return "acme"


def _user(users: list[dict], username: str) -> dict:
    return next(u for u in users if u["username"] == username)


##############################################################################
# Authorization
##############################################################################


def test_unauthenticated_returns_401(api_client, cognito_client):
    response = api_client.get(USERS_URL)
    assert response.status_code == 401


def test_tenant_admin_cannot_access(api_client, cognito_client):
    override_jwt(TENANT_ADMIN_CLAIMS)
    response = api_client.get(USERS_URL)
    assert response.status_code == 403


##############################################################################
# GET /v1/admin/users
##############################################################################


def test_list_users_returns_seeded_users(api_client, seeded_cognito_users):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(USERS_URL)
    assert response.status_code == 200
    emails = {u["email"] for u in response.json()["users"]}
    assert {"super@example.com", "acme-admin@example.com", "globex-admin@example.com"} <= emails


def test_list_users_serializes_camel_case(api_client, seeded_cognito_users):
    """Regression guard for the admin UI reading user.tenantId / user.createdAt.

    A regression back to a raw dict here would silently blank those columns
    without failing anything.
    """
    override_jwt(SUPER_ADMIN_CLAIMS)
    user = _user(api_client.get(USERS_URL).json()["users"], "tenant-admin-1")
    assert "tenantId" in user
    assert "createdAt" in user
    assert "tenant_id" not in user
    assert "created_at" not in user


##############################################################################
# POST /v1/admin/users/{username}/approve
##############################################################################


def test_approve_tenant_admin_sets_tenant(api_client, cognito_client, acme_tenant):
    create_cognito_user(cognito_client, "pending-1", "pending1@example.com")
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.post(
        f"{USERS_URL}/pending-1/approve", json={"role": "tenant-admin", "tenant_id": "acme"}
    )
    assert response.status_code == 200
    assert response.json()["tenant_id"] == "acme"


def test_approve_tenant_admin_requires_tenant(api_client, cognito_client):
    create_cognito_user(cognito_client, "pending-2", "pending2@example.com")
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.post(f"{USERS_URL}/pending-2/approve", json={"role": "tenant-admin"})
    assert response.status_code == 400


def test_approve_super_admin_clears_any_prior_tenant(api_client, cognito_client, acme_tenant):
    create_cognito_user(cognito_client, "pending-3", "pending3@example.com", tenant_id="acme")
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.post(f"{USERS_URL}/pending-3/approve", json={"role": "super-admin"})
    assert response.status_code == 200
    assert response.json()["tenant_id"] is None


##############################################################################
# POST /v1/admin/users/{username}/role - the role/tenant-scope consistency fix
##############################################################################


def test_change_role_tenant_admin_to_super_admin_clears_tenant(api_client, seeded_cognito_users):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.post(f"{USERS_URL}/tenant-admin-1/role", json={"role": "super-admin"})
    assert response.status_code == 200
    assert response.json()["tenant_id"] is None

    updated = _user(api_client.get(USERS_URL).json()["users"], "tenant-admin-1")
    assert updated["tenantId"] is None
    assert "super-admin" in updated["groups"]


def test_change_role_super_admin_to_tenant_admin_requires_tenant(api_client, seeded_cognito_users):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.post(f"{USERS_URL}/super-admin-1/role", json={"role": "tenant-admin"})
    assert response.status_code == 400


def test_change_role_super_admin_to_tenant_admin_sets_tenant(
    api_client, seeded_cognito_users, acme_tenant
):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.post(
        f"{USERS_URL}/super-admin-1/role", json={"role": "tenant-admin", "tenant_id": "acme"}
    )
    assert response.status_code == 200
    assert response.json()["tenant_id"] == "acme"

    updated = _user(api_client.get(USERS_URL).json()["users"], "super-admin-1")
    assert updated["tenantId"] == "acme"


def test_change_role_rejects_nonexistent_tenant(api_client, seeded_cognito_users, tenants_table):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.post(
        f"{USERS_URL}/super-admin-1/role",
        json={"role": "tenant-admin", "tenant_id": "does-not-exist"},
    )
    assert response.status_code == 400


def test_change_role_revoke_clears_tenant_and_groups(api_client, seeded_cognito_users):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.post(f"{USERS_URL}/tenant-admin-1/role", json={"role": None})
    assert response.status_code == 200
    assert response.json()["tenant_id"] is None

    updated = _user(api_client.get(USERS_URL).json()["users"], "tenant-admin-1")
    assert updated["tenantId"] is None
    assert updated["groups"] == []


##############################################################################
# POST /v1/admin/users/{username}/tenant
##############################################################################


def test_change_tenant_reassigns_existing_tenant_admin(
    api_client, seeded_cognito_users, acme_tenant
):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.post(f"{USERS_URL}/tenant-admin-2/tenant", json={"tenant_id": "acme"})
    assert response.status_code == 200
    assert response.json()["tenant_id"] == "acme"


def test_change_tenant_rejects_nonexistent_tenant(api_client, seeded_cognito_users, tenants_table):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.post(
        f"{USERS_URL}/tenant-admin-1/tenant", json={"tenant_id": "does-not-exist"}
    )
    assert response.status_code == 400


##############################################################################
# DELETE /v1/admin/users/{username}
##############################################################################


def test_delete_user(api_client, seeded_cognito_users):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.delete(f"{USERS_URL}/tenant-admin-2")
    assert response.status_code == 200
    users = api_client.get(USERS_URL).json()["users"]
    assert all(u["username"] != "tenant-admin-2" for u in users)


def test_delete_self_is_rejected(api_client, seeded_cognito_users):
    override_jwt({**SUPER_ADMIN_CLAIMS, "sub": "super-admin-1"})
    response = api_client.delete(f"{USERS_URL}/super-admin-1")
    assert response.status_code == 400
