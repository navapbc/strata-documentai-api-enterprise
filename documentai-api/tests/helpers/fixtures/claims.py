"""Shared JWT claims fixtures for admin endpoint tests."""

from documentai_api.app import app
from documentai_api.utils.jwt_auth import verify_jwt

SUPER_ADMIN_CLAIMS = {
    "sub": "admin-001",
    "email": "admin@example.com",
    "token_use": "access",
    "cognito:groups": ["super-admin"],
}

TENANT_ADMIN_CLAIMS = {
    "sub": "user-001",
    "email": "user@example.com",
    "token_use": "access",
    "cognito:groups": ["tenant-admin"],
    "custom:tenant_id": "test-tenant",
}


def make_claims(*, groups: list[str], tenant_id: str | None = None) -> dict:
    claims: dict = {
        "sub": "user-001",
        "email": "user@example.com",
        "token_use": "access",
        "cognito:groups": groups,
    }
    if tenant_id:
        claims["custom:tenant_id"] = tenant_id
    return claims


def override_jwt(claims: dict) -> None:
    app.dependency_overrides[verify_jwt] = lambda: claims


def clear_jwt_override() -> None:
    app.dependency_overrides.pop(verify_jwt, None)
