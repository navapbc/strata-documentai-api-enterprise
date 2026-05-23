"""Tests for API authentication."""

import pytest

from documentai_api.config.env import EnvVars
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils import auth as auth_util

TENANT_A = "tenant-a"
TENANT_B = "tenant-b"
TENANT_A_DOC_ID = "aaaaaaaa-1111-1111-1111-111111111111"

##############################################################################
# insecure shared key mode (API_AUTH_ENABLED=false, default)
##############################################################################


def test_verify_api_key_missing_env_var(api_client, monkeypatch):
    """Test returns 500 when API_AUTH_INSECURE_SHARED_KEY not set."""
    from documentai_api.config.env import get_app_env_config

    monkeypatch.delenv(EnvVars.API_AUTH_INSECURE_SHARED_KEY, raising=False)
    get_app_env_config.cache_clear()
    response = api_client.get("/v1/dictionary/schemas")
    assert response.status_code == 500


def test_verify_api_key_invalid_key(api_client, api_skeleton_key):
    """Test returns 401 when API key is invalid."""
    response = api_client.get(
        "/v1/dictionary/schemas", headers={"API-Key": api_skeleton_key + "extra"}
    )
    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]


def test_verify_api_key_missing_header(api_client, api_skeleton_key):
    """Test returns 401 when API key header is missing."""
    response = api_client.get("/v1/dictionary/schemas")
    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]


def test_all_non_public_routes_require_auth():
    """Every non-public route must declare Depends(verify_api_key) or Depends(get_user_context).

    Locks in the auth posture at the structural level: if someone adds a new
    endpoint and forgets the dependency, this test fails immediately.
    """
    from fastapi.routing import APIRoute

    from documentai_api.app import app
    from documentai_api.utils.auth import get_user_context, verify_api_key
    from documentai_api.utils.jwt_auth import verify_jwt

    public = {"/", "/health", "/openapi.json", "/docs", "/redoc"}
    auth_deps = {verify_api_key, get_user_context, verify_jwt}

    def walk(dependant) -> set:
        """Collect every callable in this dependency subtree."""
        calls = {d.call for d in dependant.dependencies}
        for child in dependant.dependencies:
            calls |= walk(child)
        return calls

    for route in app.routes:
        if not isinstance(route, APIRoute) or route.path in public:
            continue
        deps = walk(route.dependant)
        assert not deps.isdisjoint(auth_deps), (
            f"Route {sorted(route.methods)} {route.path} is missing auth dependency"
        )


def test_verify_api_key_valid(api_client, api_skeleton_key, mocker):
    """Test allows request with valid API key."""
    mocker.patch("documentai_api.app_dictionary.get_all_schemas", return_value={"test": {}})

    response = api_client.get("/v1/dictionary/schemas", headers={"API-Key": api_skeleton_key})
    assert response.status_code == 200


##############################################################################
# DynamoDB multi-key mode (API_AUTH_ENABLED=true)
##############################################################################


def test_ddb_auth_valid_key(api_client, monkeypatch, mocker, api_keys_table):
    """Test allows request when API key is valid in DDB."""
    import hashlib

    monkeypatch.setenv(EnvVars.API_AUTH_ENABLED, "true")
    mocker.patch("documentai_api.app_dictionary.get_all_schemas", return_value={"test": {}})

    raw_key = "docai_" + "a" * 32
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    api_keys_table.put_item(
        Item={
            "keyHash": key_hash,
            "clientName": "test-client",
            "tenantId": "test-tenant",
            "environment": "dev",
            "isActive": True,
            "createdAt": "2025-01-01T00:00:00Z",
        }
    )

    response = api_client.get("/v1/dictionary/schemas", headers={"API-Key": raw_key})

    assert response.status_code == 200


def test_ddb_auth_invalid_key(api_client, monkeypatch, api_keys_table):
    """Test returns 401 when API key is not in DDB."""
    monkeypatch.setenv(EnvVars.API_AUTH_ENABLED, "true")

    response = api_client.get("/v1/dictionary/schemas", headers={"API-Key": "docai_badkey"})

    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]


def test_ddb_auth_missing_header(api_client, monkeypatch, api_keys_table):
    """Test returns 401 when API key header is missing in DDB mode."""
    monkeypatch.setenv(EnvVars.API_AUTH_ENABLED, "true")

    response = api_client.get("/v1/dictionary/schemas")

    assert response.status_code == 401


##############################################################################
# Tenant isolation (integration)
##############################################################################


@pytest.fixture
def tenant_a_key(api_keys_table):
    api_key, _ = auth_util.generate_api_key("client-a", "dev", tenant_id=TENANT_A)
    return api_key


@pytest.fixture
def tenant_b_key(api_keys_table):
    api_key, _ = auth_util.generate_api_key("client-b", "dev", tenant_id=TENANT_B)
    return api_key


@pytest.fixture
def tenant_a_document(ddb_doc_metadata_table):
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: f"{TENANT_A_DOC_ID}.pdf",
            DocumentMetadata.JOB_ID: TENANT_A_DOC_ID,
            DocumentMetadata.TENANT_ID: TENANT_A,
            DocumentMetadata.PROCESS_STATUS: "COMPLETED",
            DocumentMetadata.CLIENT_NAME: "client-a",
        }
    )


@pytest.mark.integration
def test_tenant_can_access_own_document(api_client, tenant_a_key, tenant_a_document, monkeypatch):
    """API key scoped to tenant-a can read tenant-a's document."""
    monkeypatch.setenv(EnvVars.API_AUTH_ENABLED, "true")

    response = api_client.get(f"/v1/documents/{TENANT_A_DOC_ID}", headers={"API-Key": tenant_a_key})
    assert response.status_code == 200
    assert response.json()["jobId"] == TENANT_A_DOC_ID


@pytest.mark.integration
def test_tenant_cannot_access_other_tenants_document(
    api_client, tenant_b_key, tenant_a_document, monkeypatch
):
    """API key scoped to tenant-b cannot read tenant-a's document (returns 404)."""
    monkeypatch.setenv(EnvVars.API_AUTH_ENABLED, "true")

    response = api_client.get(f"/v1/documents/{TENANT_A_DOC_ID}", headers={"API-Key": tenant_b_key})
    assert response.status_code == 404


@pytest.mark.integration
def test_tenant_cannot_delete_other_tenants_document(
    api_client, tenant_b_key, tenant_a_document, monkeypatch
):
    """API key scoped to tenant-b cannot delete tenant-a's document."""
    monkeypatch.setenv(EnvVars.API_AUTH_ENABLED, "true")

    response = api_client.delete(
        f"/v1/documents/{TENANT_A_DOC_ID}", headers={"API-Key": tenant_b_key}
    )
    assert response.status_code == 404
