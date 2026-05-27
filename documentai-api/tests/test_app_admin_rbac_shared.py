"""Shared auth gate tests - 401/403 for unauthenticated and pending users."""

import pytest
from fastapi.testclient import TestClient

from documentai_api.app import app
from documentai_api.utils.jwt_auth import verify_jwt

KEYS_URL = "/v1/admin/api-keys"
TENANTS_URL = "/v1/admin/tenants"
USERS_URL = "/v1/admin/users"

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


# ==============================================================================
# Unauthenticated - 401
# ==============================================================================


def test_keys_unauthenticated_returns_401(client):
    response = client.get(KEYS_URL)
    assert response.status_code == 401


def test_tenants_unauthenticated_returns_401(client):
    response = client.get(TENANTS_URL)
    assert response.status_code == 401


def test_users_unauthenticated_returns_401(client):
    response = client.get(USERS_URL)
    assert response.status_code == 401


# ==============================================================================
# Pending user (no groups) - 403
# ==============================================================================


def test_keys_pending_user_returns_403(client):
    _override_jwt(_make_claims(groups=[]))
    response = client.get(KEYS_URL)
    assert response.status_code == 403


def test_tenants_pending_user_returns_403(client):
    _override_jwt(_make_claims(groups=[]))
    response = client.get(TENANTS_URL)
    assert response.status_code == 403


def test_users_pending_user_returns_403(client):
    _override_jwt(_make_claims(groups=[]))
    response = client.get(USERS_URL)
    assert response.status_code == 403
