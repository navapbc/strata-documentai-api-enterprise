"""User management router — super-admin only.

Endpoints for listing Cognito users, approving pending sign-ups, and changing
role / tenant assignments. All gated by ``require_super_admin``.
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from documentai_api.annotations import AdminClaims
from documentai_api.logging import get_logger
from documentai_api.services import cognito as cognito_service
from documentai_api.utils.jwt_auth import (
    SUPER_ADMIN,
    TENANT_ADMIN,
    require_super_admin,
)

logger = get_logger(__name__)

Role = Literal["super-admin", "tenant-admin"]


async def require_super_admin_dep(claims: AdminClaims) -> dict[str, Any]:
    require_super_admin(claims)
    return claims


router = APIRouter(
    prefix="/v1/admin/users",
    tags=["admin-users"],
    dependencies=[Depends(require_super_admin_dep)],
)


class ApproveRequest(BaseModel):
    role: Role
    tenant_id: str | None = Field(
        default=None,
        description="Required for tenant-admin; ignored for super-admin.",
    )


class ChangeRoleRequest(BaseModel):
    role: Role | None = Field(
        default=None,
        description="New role, or null to revoke (return user to pending).",
    )


class ChangeTenantRequest(BaseModel):
    tenant_id: str | None = Field(
        default=None,
        description="New tenant, or null to clear.",
    )


@router.get("")
async def list_users(claims: AdminClaims) -> dict[str, Any]:
    """List every user in the pool with their group + tenant assignment."""
    try:
        users = cognito_service.list_users()
    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users",
        ) from e
    return {"users": users, "count": len(users)}


def _validate_tenant_for_role(role: Role, tenant_id: str | None) -> None:
    if role == TENANT_ADMIN and not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required when assigning the tenant-admin role.",
        )


@router.post("/{username}/approve")
async def approve_user(
    username: str,
    body: ApproveRequest,
    claims: AdminClaims,
) -> dict[str, Any]:
    """Approve a pending user by assigning a role and (for tenant-admin) a tenant."""
    _validate_tenant_for_role(body.role, body.tenant_id)
    try:
        cognito_service.replace_role(username, body.role)
        # super-admin keeps any prior tenant unless explicitly set; tenant-admin always sets.
        if body.role == TENANT_ADMIN or body.tenant_id is not None:
            cognito_service.set_tenant(username, body.tenant_id)
    except Exception as e:
        logger.error(f"Failed to approve user {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve user",
        ) from e
    return {"username": username, "role": body.role, "tenant_id": body.tenant_id}


@router.post("/{username}/role")
async def change_role(
    username: str,
    body: ChangeRoleRequest,
    claims: AdminClaims,
) -> dict[str, Any]:
    """Change a user's role, or pass ``role: null`` to revoke."""
    try:
        cognito_service.replace_role(username, body.role)
    except Exception as e:
        logger.error(f"Failed to change role for {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change role",
        ) from e
    return {"username": username, "role": body.role}


@router.post("/{username}/tenant")
async def change_tenant(
    username: str,
    body: ChangeTenantRequest,
    claims: AdminClaims,
) -> dict[str, Any]:
    """Set or clear a user's tenant assignment."""
    try:
        cognito_service.set_tenant(username, body.tenant_id)
    except Exception as e:
        logger.error(f"Failed to change tenant for {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change tenant",
        ) from e
    return {"username": username, "tenant_id": body.tenant_id}


@router.delete("/{username}")
async def delete_user(username: str, claims: AdminClaims) -> dict[str, Any]:
    """Permanently delete a user."""
    # Prevent self-deletion to avoid locking yourself out.
    if claims.get("cognito:username") == username or claims.get("sub") == username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account.",
        )
    try:
        cognito_service.delete_user(username)
    except Exception as e:
        logger.error(f"Failed to delete user {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
        ) from e
    return {"username": username, "deleted": True}


__all__ = ["SUPER_ADMIN", "TENANT_ADMIN", "Role", "router"]
