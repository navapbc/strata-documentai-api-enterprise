"""User management router - super-admin only.

Endpoints for listing Cognito users, approving pending sign-ups, and changing
role / tenant assignments. All gated by ``require_super_admin``.
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from documentai_api.annotations import SuperAdminClaims, verify_jwt_with_super_admin
from documentai_api.config.constants import ApiVisualizationTag
from documentai_api.logging import get_logger
from documentai_api.schemas.audit_event import AuditAction, AuditTargetType
from documentai_api.services import cognito as cognito_service
from documentai_api.utils.audit import log_event
from documentai_api.utils.jwt_auth import SUPER_ADMIN, TENANT_ADMIN

logger = get_logger(__name__)

Role = Literal["super-admin", "tenant-admin"]


router = APIRouter(
    prefix="/v1/admin/users",
    tags=[ApiVisualizationTag.ADMIN_USERS],
    dependencies=[Depends(verify_jwt_with_super_admin)],
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
async def list_users(claims: SuperAdminClaims) -> dict[str, Any]:
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
    claims: SuperAdminClaims,
) -> dict[str, Any]:
    """Approve a pending user by assigning a role and (for tenant-admin) a tenant."""
    _validate_tenant_for_role(body.role, body.tenant_id)
    try:
        cognito_service.replace_role(username, body.role)
        # Super-admin is cross-tenant by definition - clear any prior tenant
        # attribute so the user record reflects the role accurately.
        # Tenant-admin always gets the supplied tenant.
        if body.role == SUPER_ADMIN:
            cognito_service.set_tenant(username, None)
        else:
            cognito_service.set_tenant(username, body.tenant_id)
    except Exception as e:
        logger.error(f"Failed to approve user {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve user",
        ) from e
    log_event(
        claims,
        action=AuditAction.USER_APPROVE,
        target_type=AuditTargetType.USER,
        target_id=username,
        tenant_id=body.tenant_id,
        metadata={"role": body.role, "tenant_id": body.tenant_id},
    )
    return {"username": username, "role": body.role, "tenant_id": body.tenant_id}


@router.post("/{username}/role")
async def change_role(
    username: str,
    body: ChangeRoleRequest,
    claims: SuperAdminClaims,
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
    log_event(
        claims,
        action=AuditAction.USER_ROLE_CHANGE,
        target_type=AuditTargetType.USER,
        target_id=username,
        metadata={"new_role": body.role},
    )
    return {"username": username, "role": body.role}


@router.post("/{username}/tenant")
async def change_tenant(
    username: str,
    body: ChangeTenantRequest,
    claims: SuperAdminClaims,
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
    log_event(
        claims,
        action=AuditAction.USER_TENANT_CHANGE,
        target_type=AuditTargetType.USER,
        target_id=username,
        tenant_id=body.tenant_id,
        metadata={"new_tenant": body.tenant_id},
    )
    return {"username": username, "tenant_id": body.tenant_id}


@router.delete("/{username}")
async def delete_user(username: str, claims: SuperAdminClaims) -> dict[str, Any]:
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
    log_event(
        claims,
        action=AuditAction.USER_DELETE,
        target_type=AuditTargetType.USER,
        target_id=username,
    )
    return {"username": username, "deleted": True}


__all__ = ["SUPER_ADMIN", "TENANT_ADMIN", "Role", "router"]
