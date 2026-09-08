"""Shared auth gate tests - 401/403 for unauthenticated and pending users."""

from tests.helpers.fixtures.claims import make_claims, override_jwt

KEYS_URL = "/v1/admin/api-keys"
TENANTS_URL = "/v1/admin/tenants"
USERS_URL = "/v1/admin/users"


# ==============================================================================
# Unauthenticated - 401
# ==============================================================================


def test_keys_unauthenticated_returns_401(api_client):
    response = api_client.get(KEYS_URL)
    assert response.status_code == 401


def test_tenants_unauthenticated_returns_401(api_client):
    response = api_client.get(TENANTS_URL)
    assert response.status_code == 401


def test_users_unauthenticated_returns_401(api_client):
    response = api_client.get(USERS_URL)
    assert response.status_code == 401


# ==============================================================================
# Pending user (no groups) - 403
# ==============================================================================


def test_keys_pending_user_returns_403(api_client):
    override_jwt(make_claims(groups=[]))
    response = api_client.get(KEYS_URL)
    assert response.status_code == 403


def test_tenants_pending_user_returns_403(api_client):
    override_jwt(make_claims(groups=[]))
    response = api_client.get(TENANTS_URL)
    assert response.status_code == 403


def test_users_pending_user_returns_403(api_client):
    override_jwt(make_claims(groups=[]))
    response = api_client.get(USERS_URL)
    assert response.status_code == 403
