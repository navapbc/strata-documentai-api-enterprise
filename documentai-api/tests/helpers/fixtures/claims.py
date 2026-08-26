"""Shared JWT claims fixtures for admin endpoint tests."""

from typing import Any

SUPER_ADMIN = "super-admin"
TENANT_ADMIN = "tenant-admin"
TENANT_ADMIN_ID = "tenant-admin-id"

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
    "custom:tenant_id": TENANT_ADMIN_ID,
}


def make_claims(*, groups: list[str] | None = None, tenant_id: str | None = None) -> dict[str, Any]:
    claims: dict[str, Any] = {
        "sub": "test-user",
        "email": "test@example.com",
        "token_use": "access",
        "cognito:groups": groups or [],
    }

    if tenant_id:
        claims["custom:tenant_id"] = tenant_id

    return claims


def override_jwt(claims: dict[str, Any]) -> None:
    from documentai_api.app import app
    from documentai_api.utils.jwt_auth import verify_jwt

    app.dependency_overrides[verify_jwt] = lambda: claims
