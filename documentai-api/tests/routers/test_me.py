"""Tests for GET /v1/me endpoint."""

import pytest

from documentai_api.app import app
from documentai_api.utils.auth import UserContext, get_user_context_with_fallback

ME_URL = "/v1/me"

EXPECTED_KEYS = {"tenantId", "principal", "authMethod"}


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.pop(get_user_context_with_fallback, None)


def test_me_no_credentials_returns_401(api_client):
    response = api_client.get(ME_URL)
    assert response.status_code == 401


def test_me_invalid_api_key_returns_401(api_client):
    response = api_client.get(ME_URL, headers={"API-Key": "bad-key"})
    assert response.status_code == 401


def test_me_invalid_bearer_returns_401(api_client):
    response = api_client.get(ME_URL, headers={"Authorization": "Bearer invalid.jwt.token"})
    assert response.status_code == 401


def test_me_api_key_context(api_client):
    app.dependency_overrides[get_user_context_with_fallback] = lambda: UserContext(
        tenant_id="test-tenant", api_key_name="my-service"
    )
    response = api_client.get(ME_URL)
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == EXPECTED_KEYS
    assert data["tenantId"] == "test-tenant"
    assert data["principal"] == "my-service"
    assert data["authMethod"] == "api_key"


def test_me_jwt_context(api_client):
    app.dependency_overrides[get_user_context_with_fallback] = lambda: UserContext(
        tenant_id="__admin__", api_key_name="admin@example.com", auth_method="jwt"
    )
    response = api_client.get(ME_URL)
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == EXPECTED_KEYS
    assert data["tenantId"] == "__admin__"
    assert data["principal"] == "admin@example.com"
    assert data["authMethod"] == "jwt"


def test_me_tenant_admin_jwt_context(api_client):
    """Tenant-admin JWT correctly reports auth_method=jwt."""
    app.dependency_overrides[get_user_context_with_fallback] = lambda: UserContext(
        tenant_id="test-tenant", api_key_name="user@test-tenant.com", auth_method="jwt"
    )
    response = api_client.get(ME_URL)
    assert response.status_code == 200
    data = response.json()
    assert data["tenantId"] == "test-tenant"
    assert data["authMethod"] == "jwt"


def test_me_post_returns_405(api_client):
    response = api_client.post(ME_URL)
    assert response.status_code == 405
