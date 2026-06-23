"""Cognito JWT verification dependency for admin endpoints."""

from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWKClientError

from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger

logger = get_logger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _get_jwks_client() -> PyJWKClient:
    """Create and cache a JWKS client for the Cognito user pool."""
    config = get_aws_config()
    pool_id = config.cognito_user_pool_id
    region = pool_id.split("_")[0] if pool_id else "us-east-1"
    jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/jwks.json"
    return PyJWKClient(jwks_url)


@lru_cache(maxsize=1)
def _get_issuer() -> str:
    config = get_aws_config()
    pool_id = config.cognito_user_pool_id
    region = pool_id.split("_")[0] if pool_id else "us-east-1"
    return f"https://cognito-idp.{region}.amazonaws.com/{pool_id}"


def _decode_and_verify(token: str) -> dict[str, Any]:
    """Decode and verify JWT signature + claims using Cognito JWKS."""
    jwks_client = _get_jwks_client()
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    # First decode without aud to inspect token_use
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=_get_issuer(),
        options={
            "verify_exp": True,
            "verify_iss": True,
            "verify_aud": False,  # checked manually below based on token_use
        },
    )

    # Accept either access or id tokens
    token_use = payload.get("token_use")
    if token_use not in ("access", "id"):
        raise jwt.InvalidTokenError("Not an access or id token")

    # Cognito access tokens don't carry an aud claim, but id tokens do -
    # validate audience for id tokens to prevent cross-client token reuse.
    if token_use == "id":
        config = get_aws_config()
        expected_aud = config.cognito_client_id
        token_aud = payload.get("aud")
        if expected_aud and token_aud != expected_aud:
            raise jwt.InvalidTokenError(
                f"Invalid audience: expected {expected_aud}, got {token_aud}"
            )

    return payload


async def verify_jwt(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict[str, Any]:
    """Verify Cognito JWT signature and claims, return decoded payload."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        return _decode_and_verify(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except (jwt.InvalidTokenError, PyJWKClientError) as e:
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


def resolve_tenant(claims: dict[str, Any], requested_tenant_id: str | None = None) -> str | None:
    """Resolve the effective tenant for an operation.

    Tenant-admins: always returns their own tenant (ignores requested).
    Super-admins: returns requested_tenant_id (or None for "all").

    Use when the endpoint allows None (e.g. list all). For endpoints that
    require a tenant, check the return value and raise 400 if None.
    """
    scope = tenant_scope(claims)
    if scope is not None:
        return scope
    return requested_tenant_id
