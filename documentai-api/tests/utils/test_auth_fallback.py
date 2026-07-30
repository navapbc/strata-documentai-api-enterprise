"""Tests for get_user_context_with_fallback and resolve_tenant_from_context.

Tests the real functions directly - not via the api_client fixture, which
dependency-overrides both and would make these tests vacuous.
"""

import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from documentai_api.utils.auth import (
    UserContext,
    get_user_context_with_fallback,
    resolve_tenant_from_context,
)
from documentai_api.utils.jwt_auth import SUPER_ADMIN


def _generate_rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _make_token(payload: dict, private_key, kid: str = "test-kid") -> str:
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": kid})


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _base_payload(groups: list[str], tenant_id: str | None = None) -> dict:
    p = {
        "sub": "user-123",
        "email": "user@example.com",
        "token_use": "access",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TestPool",
        "exp": int(time.time()) + 3600,
        "cognito:groups": groups,
    }
    if tenant_id is not None:
        p["custom:tenant_id"] = tenant_id
    return p


def _api_key_ctx(tenant_id: str) -> UserContext:
    return UserContext(tenant_id=tenant_id, api_key_name="test-api-key-name", auth_method="api_key")


def _jwt_ctx(tenant_id: str) -> UserContext:
    return UserContext(tenant_id=tenant_id, api_key_name="user@example.com", auth_method="jwt")


@pytest.fixture
def rsa_keys():
    return _generate_rsa_keypair()


@pytest.fixture
def mock_jwks(rsa_keys):
    _, public_key = rsa_keys
    mock_jwk = MagicMock()
    mock_jwk.key = public_key
    with patch("documentai_api.utils.jwt_auth._get_jwks_client") as mock_client:
        mock_client.return_value.get_signing_key_from_jwt.return_value = mock_jwk
        yield


@pytest.fixture(autouse=True)
def pin_cognito_pool(monkeypatch):
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_TestPool")


# --- get_user_context_with_fallback ---


@pytest.mark.asyncio
async def test_fallback_super_admin_group_yields_admin_sentinel(rsa_keys, mock_jwks):
    private_key, _ = rsa_keys
    token = _make_token(_base_payload(["super-admin"]), private_key)

    ctx = await get_user_context_with_fallback(api_key=None, credentials=_bearer(token))

    assert ctx.tenant_id == SUPER_ADMIN
    assert ctx.auth_method == "jwt"


@pytest.mark.asyncio
async def test_fallback_tenant_admin_with_tenant_claim_yields_tenant(rsa_keys, mock_jwks):
    private_key, _ = rsa_keys
    token = _make_token(_base_payload(["tenant-admin"], tenant_id="test-tenant-id"), private_key)

    ctx = await get_user_context_with_fallback(api_key=None, credentials=_bearer(token))

    assert ctx.tenant_id == "test-tenant-id"
    assert ctx.auth_method == "jwt"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("groups", "tenant_id"),
    [
        ([], None),  # no group - HIGH-01 bypass guard
        (["tenant-admin"], None),  # approved role but no tenant assigned
    ],
)
async def test_fallback_raises_403(groups, tenant_id, rsa_keys, mock_jwks):
    private_key, _ = rsa_keys
    token = _make_token(_base_payload(groups, tenant_id=tenant_id), private_key)

    with pytest.raises(HTTPException) as exc_info:
        await get_user_context_with_fallback(api_key=None, credentials=_bearer(token))

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_fallback_no_credentials_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        await get_user_context_with_fallback(api_key=None, credentials=None)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_fallback_api_key_takes_precedence(api_keys_table):
    from documentai_api.utils import auth as auth_util

    raw_key, _ = auth_util.generate_api_key(
        "test-api-key-name", "prod", tenant_id="tenant-from-key"
    )

    with patch("documentai_api.utils.auth.get_app_env_config") as mock_cfg:
        mock_cfg.return_value.api_auth_enabled = True
        mock_cfg.return_value.api_auth_cache_ttl = 300
        ctx = await get_user_context_with_fallback(api_key=raw_key, credentials=None)

    assert ctx.tenant_id == "tenant-from-key"
    assert ctx.auth_method == "api_key"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("extra", "client_id_env"),
    [
        ({"client_id": "test-client-id"}, "test-client-id"),
        ({"token_use": "id", "aud": "test-client-id"}, "test-client-id"),
        ({}, None),
    ],
)
async def test_fallback_client_id_accepted(extra, client_id_env, rsa_keys, mock_jwks, monkeypatch):
    if client_id_env:
        monkeypatch.setenv("COGNITO_CLIENT_ID", client_id_env)
    else:
        monkeypatch.delenv("COGNITO_CLIENT_ID", raising=False)
    private_key, _ = rsa_keys
    payload = {**_base_payload(["tenant-admin"], tenant_id="test-tenant-id"), **extra}

    ctx = await get_user_context_with_fallback(
        api_key=None, credentials=_bearer(_make_token(payload, private_key))
    )

    assert ctx.tenant_id == "test-tenant-id"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("extra", "match"),
    [
        ({"client_id": "evil-client"}, "client_id"),
        ({"token_use": "id", "aud": "wrong-client"}, "audience"),
    ],
)
async def test_fallback_client_id_rejected(extra, match, rsa_keys, mock_jwks, monkeypatch):
    monkeypatch.setenv("COGNITO_CLIENT_ID", "test-client-id")
    private_key, _ = rsa_keys
    payload = {**_base_payload(["tenant-admin"], tenant_id="test-tenant-id"), **extra}

    with pytest.raises(HTTPException) as exc_info:
        await get_user_context_with_fallback(
            api_key=None, credentials=_bearer(_make_token(payload, private_key))
        )

    assert exc_info.value.status_code == 401


def test_resolve_super_admin_returns_requested_tenant():
    assert resolve_tenant_from_context(_jwt_ctx(SUPER_ADMIN), "test-tenant-id") == "test-tenant-id"


def test_resolve_super_admin_no_requested_tenant_returns_none():
    assert resolve_tenant_from_context(_jwt_ctx(SUPER_ADMIN), None) is None


def test_resolve_tenant_admin_locked_to_own_tenant():
    assert (
        resolve_tenant_from_context(_jwt_ctx("test-tenant-id"), "test-tenant-id")
        == "test-tenant-id"
    )


def test_resolve_api_key_no_requested_tenant_returns_own():
    assert resolve_tenant_from_context(_api_key_ctx("test-tenant-id"), None) == "test-tenant-id"


@pytest.mark.parametrize(
    "ctx",
    [
        _jwt_ctx("test-tenant-id"),
        _api_key_ctx("test-tenant-id"),
    ],
)
def test_resolve_mismatch_raises_403(ctx):
    with pytest.raises(HTTPException) as exc_info:
        resolve_tenant_from_context(ctx, "other-tenant-id")
    assert exc_info.value.status_code == 403
