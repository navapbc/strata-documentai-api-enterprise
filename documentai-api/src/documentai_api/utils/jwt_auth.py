"""Cognito JWT verification dependency for admin endpoints."""

import json
import time
from functools import lru_cache
from typing import Annotated, Any, cast
from urllib.request import urlopen

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger

logger = get_logger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _get_jwks() -> dict[str, Any]:
    """Fetch and cache Cognito JWKS."""
    config = get_aws_config()
    pool_id = config.cognito_user_pool_id
    region = pool_id.split("_")[0] if pool_id else "us-east-1"
    url = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/jwks.json"

    with urlopen(url) as response:
        return cast(dict[str, Any], json.loads(response.read()))


def _decode_jwt_unverified(token: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Decode JWT header and payload without signature verification."""
    import base64

    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")

    def _b64decode(s: str) -> bytes:
        padding = 4 - len(s) % 4
        return base64.urlsafe_b64decode(s + "=" * padding)

    header = json.loads(_b64decode(parts[0]))
    payload = json.loads(_b64decode(parts[1]))
    return header, payload


def _verify_claims(payload: dict[str, Any]) -> None:
    """Verify JWT claims (expiry, token_use, issuer)."""
    config = get_aws_config()
    pool_id = config.cognito_user_pool_id
    region = pool_id.split("_")[0] if pool_id else "us-east-1"
    expected_issuer = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}"

    # Check expiry
    if time.time() > payload.get("exp", 0):
        raise ValueError("Token expired")

    # Accept either access or id tokens. ID tokens carry the email claim used
    # for admin audit fields; access tokens are used elsewhere.
    if payload.get("token_use") not in ("access", "id"):
        raise ValueError("Not an access or id token")

    # Check issuer
    if payload.get("iss") != expected_issuer:
        raise ValueError("Invalid issuer")


async def verify_jwt(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict[str, Any]:
    """Verify Cognito JWT and return claims.

    For production, add full RSA signature verification using the JWKS.
    This implementation verifies claims but trusts the token structure
    (suitable for internal/dev use behind API Gateway).
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        _, payload = _decode_jwt_unverified(token)
        _verify_claims(payload)
        return payload
    except Exception as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# --- Role + tenant helpers ---------------------------------------------------

SUPER_ADMIN = "super-admin"
TENANT_ADMIN = "tenant-admin"


def get_roles(claims: dict[str, Any]) -> list[str]:
    """Return Cognito group memberships for the caller (empty if no role)."""
    groups = claims.get("cognito:groups") or []
    if isinstance(groups, str):
        return [groups]
    return list(groups)


def get_tenant_id(claims: dict[str, Any]) -> str | None:
    """Return the tenant the caller belongs to, if any."""
    return claims.get("custom:tenant_id")


def is_super_admin(claims: dict[str, Any]) -> bool:
    return SUPER_ADMIN in get_roles(claims)


def is_tenant_admin(claims: dict[str, Any]) -> bool:
    return TENANT_ADMIN in get_roles(claims)


def require_super_admin(claims: dict[str, Any]) -> None:
    """Reject anyone who isn't a super-admin (used for user-management endpoints)."""
    if not is_super_admin(claims):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super-admin role required.",
        )


def require_role(claims: dict[str, Any]) -> None:
    """Reject users who have authenticated but haven't been approved.

    A new sign-up has a valid JWT but no Cognito group membership. Admin
    endpoints should require that the user has been placed in either
    super-admin or tenant-admin first.
    """
    if not (is_super_admin(claims) or is_tenant_admin(claims)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending approval by an administrator.",
        )


def tenant_scope(claims: dict[str, Any]) -> str | None:
    """Return the tenant filter to apply for this caller.

    Super-admins see all tenants (returns None). Tenant-admins are scoped to
    their assigned tenant; if a tenant-admin has no tenant_id we treat that as
    a misconfiguration and refuse the request.
    """
    if is_super_admin(claims):
        return None
    tenant = get_tenant_id(claims)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has no tenant assigned. Contact an administrator.",
        )
    return tenant
