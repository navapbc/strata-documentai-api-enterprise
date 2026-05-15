"""Tests for API authentication."""

from unittest.mock import patch

from documentai_api.config.env import EnvVars

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
    """Every non-public route must declare Depends(verify_api_key).

    Locks in the auth posture at the structural level: if someone adds a new
    endpoint and forgets the dependency, this test fails immediately.
    """
    from fastapi.routing import APIRoute

    from documentai_api.app import app, verify_api_key

    public = {"/", "/health", "/openapi.json", "/docs", "/redoc"}

    for route in app.routes:
        if not isinstance(route, APIRoute) or route.path in public:
            continue
        deps = [d.call for d in route.dependant.dependencies]
        assert verify_api_key in deps, (
            f"Route {sorted(route.methods)} {route.path} is missing Depends(verify_api_key)"
        )


def test_verify_api_key_valid(api_client, api_skeleton_key, mocker):
    """Test allows request with valid API key."""
    mocker.patch("documentai_api.app.get_all_schemas", return_value={"test": {}})

    response = api_client.get("/v1/dictionary/schemas", headers={"API-Key": api_skeleton_key})
    assert response.status_code == 200


##############################################################################
# DynamoDB multi-key mode (API_AUTH_ENABLED=true)
##############################################################################


def test_ddb_auth_valid_key(api_client, monkeypatch, mocker):
    """Test allows request when API key is valid in DDB."""
    monkeypatch.setenv(EnvVars.API_AUTH_ENABLED, "true")
    mocker.patch("documentai_api.app.get_all_schemas", return_value={"test": {}})

    with patch("documentai_api.utils.auth._verify_with_ddb"):
        response = api_client.get("/v1/dictionary/schemas", headers={"API-Key": "docai_somekey"})

    assert response.status_code == 200


def test_ddb_auth_invalid_key(api_client, monkeypatch):
    """Test returns 401 when API key is not in DDB."""
    from fastapi import HTTPException

    monkeypatch.setenv(EnvVars.API_AUTH_ENABLED, "true")

    with patch(
        "documentai_api.utils.auth._verify_with_ddb",
        side_effect=HTTPException(status_code=401, detail="Invalid API key"),
    ):
        response = api_client.get("/v1/dictionary/schemas", headers={"API-Key": "docai_badkey"})

    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]


def test_ddb_auth_missing_header(api_client, monkeypatch):
    """Test returns 401 when API key header is missing in DDB mode."""
    from fastapi import HTTPException

    monkeypatch.setenv(EnvVars.API_AUTH_ENABLED, "true")

    with patch(
        "documentai_api.utils.auth._verify_with_ddb",
        side_effect=HTTPException(status_code=401, detail="Invalid API key"),
    ):
        response = api_client.get("/v1/dictionary/schemas")

    assert response.status_code == 401
