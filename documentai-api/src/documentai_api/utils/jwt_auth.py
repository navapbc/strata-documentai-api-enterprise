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

    # Validate client_id/audience for both token types to prevent cross-client reuse.
    # Access tokens carry client_id; id tokens carry aud.
    config = get_aws_config()
    expected_client_id = config.cognito_client_id

    if expected_client_id:
        if token_use == "id":
            token_aud = payload.get("aud")
            if token_aud != expected_client_id:
                raise jwt.InvalidTokenError(
                    f"Invalid audience: expected {expected_client_id}, got {token_aud}"
                )
        else:  # access token
            token_client_id = payload.get("client_id")
            if token_client_id != expected_client_id:
                raise jwt.InvalidTokenError(
                    f"Invalid client_id: expected {expected_client_id}, got {token_client_id}"
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


# =============================================================================
# Role + tenant helpers
# =============================================================================

SUPER_ADMIN = "__admin__"  # tenant_id sentinel value for super-admins
SUPER_ADMIN_GROUP = "super-admin"  # Cognito group name
TENANT_ADMIN = "tenant-admin"


def get_roles(claims: dict[str, Any]) -> list[str]:
    """Return Cognito group memberships for the caller (empty if no role)."""
    groups = claims.get("cognito:groups") or []
    if isinstance(groups, str):
        return [groups]

    return list(groups)


def get_tenant_id(claims: dict[str, Any]) -> str | None:
    """Return the tenant this caller is scoped to administer, if any.

    This is an authorization scope, not membership - super-admins always
    have none (they aren't scoped to any single tenant).
    """
    return claims.get("custom:tenant_id")


def is_super_admin(claims: dict[str, Any]) -> bool:
    return SUPER_ADMIN_GROUP in get_roles(claims)


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

    Tenant-admins: always returns their own tenant. Raises 403 if
    requested_tenant_id is provided but doesn't match.
    Super-admins: returns requested_tenant_id as-is (may be None).
    """
    scope = tenant_scope(claims)

    if scope is not None:
        if requested_tenant_id and requested_tenant_id != scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant.",
            )

        return scope

    return requested_tenant_id


def require_tenant(claims: dict[str, Any], requested_tenant_id: str | None = None) -> str:
    """Resolve the effective tenant, raising 400 if none can be determined.

    Use for endpoints where a specific tenant is always required.
    """
    tenant = resolve_tenant(claims, requested_tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="tenant_id is required."
        )

    return tenant
