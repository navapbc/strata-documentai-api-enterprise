"""Tests for JWT auth - signature verification, claims, roles."""

import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from documentai_api.utils.jwt_auth import (
    _decode_and_verify,
    get_roles,
    get_tenant_id,
    is_super_admin,
    is_tenant_admin,
    require_role,
    require_super_admin,
    tenant_scope,
)

# --- Helpers ---


def _generate_rsa_keypair():
    """Generate an RSA key pair for testing."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key


def _encode_token(payload: dict, private_key, kid: str = "test-kid") -> str:
    """Encode a JWT with RS256."""
    return pyjwt.encode(payload, private_key, algorithm="RS256", headers={"kid": kid})


@pytest.fixture
def rsa_keys():
    return _generate_rsa_keypair()


@pytest.fixture
def valid_payload():
    return {
        "sub": "test-user",
        "email": "test@example.com",
        "token_use": "access",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TestPool",
        "exp": int(time.time()) + 3600,
        "cognito:groups": ["super-admin"],
    }


# --- Signature verification tests ---


class TestDecodeAndVerify:
    def test_valid_token(self, rsa_keys, valid_payload, monkeypatch):
        private_key, public_key = rsa_keys
        token = _encode_token(valid_payload, private_key)

        monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_TestPool")

        mock_jwk = MagicMock()
        mock_jwk.key = public_key

        with patch("documentai_api.utils.jwt_auth._get_jwks_client") as mock_client:
            mock_client.return_value.get_signing_key_from_jwt.return_value = mock_jwk
            result = _decode_and_verify(token)

        assert result["sub"] == "test-user"
        assert result["email"] == "test@example.com"

    def test_expired_token(self, rsa_keys, valid_payload, monkeypatch):
        private_key, public_key = rsa_keys
        valid_payload["exp"] = int(time.time()) - 100
        token = _encode_token(valid_payload, private_key)

        monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_TestPool")

        mock_jwk = MagicMock()
        mock_jwk.key = public_key

        with patch("documentai_api.utils.jwt_auth._get_jwks_client") as mock_client:
            mock_client.return_value.get_signing_key_from_jwt.return_value = mock_jwk
            with pytest.raises(pyjwt.ExpiredSignatureError):
                _decode_and_verify(token)

    def test_wrong_issuer(self, rsa_keys, valid_payload, monkeypatch):
        private_key, public_key = rsa_keys
        valid_payload["iss"] = "https://evil.example.com"
        token = _encode_token(valid_payload, private_key)

        monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_TestPool")

        mock_jwk = MagicMock()
        mock_jwk.key = public_key

        with patch("documentai_api.utils.jwt_auth._get_jwks_client") as mock_client:
            mock_client.return_value.get_signing_key_from_jwt.return_value = mock_jwk
            with pytest.raises(pyjwt.InvalidIssuerError):
                _decode_and_verify(token)

    def test_invalid_token_use(self, rsa_keys, valid_payload, monkeypatch):
        private_key, public_key = rsa_keys
        valid_payload["token_use"] = "refresh"
        token = _encode_token(valid_payload, private_key)

        monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_TestPool")

        mock_jwk = MagicMock()
        mock_jwk.key = public_key

        with patch("documentai_api.utils.jwt_auth._get_jwks_client") as mock_client:
            mock_client.return_value.get_signing_key_from_jwt.return_value = mock_jwk
            with pytest.raises(pyjwt.InvalidTokenError, match="Not an access or id token"):
                _decode_and_verify(token)

    def test_wrong_signing_key_rejects(self, rsa_keys, valid_payload, monkeypatch):
        private_key, _ = rsa_keys
        _, wrong_public_key = _generate_rsa_keypair()
        token = _encode_token(valid_payload, private_key)

        monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_TestPool")

        mock_jwk = MagicMock()
        mock_jwk.key = wrong_public_key

        with patch("documentai_api.utils.jwt_auth._get_jwks_client") as mock_client:
            mock_client.return_value.get_signing_key_from_jwt.return_value = mock_jwk
            with pytest.raises(pyjwt.InvalidSignatureError):
                _decode_and_verify(token)


# --- Role helper tests ---


class TestRoleHelpers:
    def test_get_roles_from_list(self):
        assert get_roles({"cognito:groups": ["super-admin", "tenant-admin"]}) == [
            "super-admin",
            "tenant-admin",
        ]

    def test_get_roles_empty(self):
        assert get_roles({}) == []

    def test_get_roles_string(self):
        assert get_roles({"cognito:groups": "super-admin"}) == ["super-admin"]

    def test_is_super_admin_true(self):
        assert is_super_admin({"cognito:groups": ["super-admin"]}) is True

    def test_is_super_admin_false(self):
        assert is_super_admin({"cognito:groups": ["tenant-admin"]}) is False

    def test_is_tenant_admin_true(self):
        assert is_tenant_admin({"cognito:groups": ["tenant-admin"]}) is True

    def test_get_tenant_id(self):
        assert get_tenant_id({"custom:tenant_id": "acme"}) == "acme"

    def test_get_tenant_id_missing(self):
        assert get_tenant_id({}) is None

    def test_require_super_admin_passes(self):
        require_super_admin({"cognito:groups": ["super-admin"]})

    def test_require_super_admin_rejects(self):
        with pytest.raises(HTTPException) as exc_info:
            require_super_admin({"cognito:groups": ["tenant-admin"]})
        assert exc_info.value.status_code == 403

    def test_require_role_passes_super_admin(self):
        require_role({"cognito:groups": ["super-admin"]})

    def test_require_role_passes_tenant_admin(self):
        require_role({"cognito:groups": ["tenant-admin"]})

    def test_require_role_rejects_no_groups(self):
        with pytest.raises(HTTPException) as exc_info:
            require_role({"cognito:groups": []})
        assert exc_info.value.status_code == 403

    def test_tenant_scope_super_admin_returns_none(self):
        assert tenant_scope({"cognito:groups": ["super-admin"]}) is None

    def test_tenant_scope_tenant_admin_returns_tenant(self):
        claims = {"cognito:groups": ["tenant-admin"], "custom:tenant_id": "acme"}
        assert tenant_scope(claims) == "acme"

    def test_tenant_scope_tenant_admin_no_tenant_rejects(self):
        claims = {"cognito:groups": ["tenant-admin"]}
        with pytest.raises(HTTPException) as exc_info:
            tenant_scope(claims)
        assert exc_info.value.status_code == 403
