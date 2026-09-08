"""Admin audit log router - read-only access to audit events."""

from fastapi import APIRouter, Depends, HTTPException, status

from documentai_api.annotations import AdminClaims, IsoDateParam, PageLimit, verify_jwt_with_role
from documentai_api.config.constants import ApiVisualizationTag
from documentai_api.logging import get_logger
from documentai_api.models.audit import (
    AuditActionsResponse,
    AuditActorsResponse,
    AuditLogResponse,
)
from documentai_api.schemas.audit_event import GLOBAL_TENANT, AuditAction
from documentai_api.services import cognito as cognito_service
from documentai_api.utils.audit_log import (
    query_by_action,
    query_by_actor,
    query_by_tenant,
    record_to_item,
)
from documentai_api.utils.jwt_auth import tenant_scope
from documentai_api.utils.pagination import decode_cursor, encode_cursor

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/admin/audit-log",
    tags=[ApiVisualizationTag.ADMIN_AUDIT_LOG],
    dependencies=[Depends(verify_jwt_with_role)],
)


@router.get("/actors")
async def get_audit_actors(
    claims: AdminClaims,
    tenant_id: str | None = None,
) -> AuditActorsResponse:
    """Return distinct actor emails visible to the caller.

    Super-admins can optionally scope to a tenant; tenant-admins are always
    scoped to their own partition. Sourced from Cognito only (see
    docs/decisions/2026-08-06-audit-log-actor-dropdown-source.md) - this
    is a filter, not a guarantee: a user with no audit events for the scoped
    tenant may still appear, and a super-admin who acted on a tenant's
    resources but isn't a Cognito member of it will not.
    """
    scope = tenant_scope(claims)
    if scope is not None:
        tenant_id = scope

    try:
        users = cognito_service.list_users(include_groups=False)
        actors = {u.email for u in users if u.email and (not tenant_id or u.tenant_id == tenant_id)}
    except Exception as e:
        logger.error(f"Failed to list audit actors: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list audit actors",
        ) from e

    return AuditActorsResponse(actors=sorted(actors))


@router.get("/actions")
async def get_audit_actions() -> AuditActionsResponse:
    """Return all known audit action strings."""
    actions = [
        v for k, v in vars(AuditAction).items() if not k.startswith("_") and isinstance(v, str)
    ]
    return AuditActionsResponse(actions=sorted(actions))


@router.get("")
async def get_audit_log(
    claims: AdminClaims,
    tenant_id: str | None = None,
    action: str | None = None,
    actor_email: str | None = None,
    start_date: IsoDateParam = None,
    end_date: IsoDateParam = None,
    limit: PageLimit = 50,
    cursor: str | None = None,
) -> AuditLogResponse:
    """Query audit events.

    Super-admins can query any tenant or by action/actor (via GSI).
    Tenant-admins can only query their own tenant's events.
    """
    scope = tenant_scope(claims)

    if scope is not None:
        if tenant_id and tenant_id != scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant's audit log.",
            )
        tenant_id = scope

    try:
        exclusive_start_key = decode_cursor(cursor) if cursor else None

        if actor_email and not tenant_id:
            records, last_key = query_by_actor(
                actor_email, action, start_date, end_date, limit, exclusive_start_key
            )
        elif action and not tenant_id:
            records, last_key = query_by_action(
                action, start_date, end_date, limit, exclusive_start_key
            )
        else:
            partition = tenant_id or GLOBAL_TENANT
            records, last_key = query_by_tenant(
                partition, action, actor_email, start_date, end_date, limit, exclusive_start_key
            )
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Audit log query error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query audit log",
        ) from e
    except Exception as e:
        logger.error(f"Failed to query audit log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query audit log",
        ) from e

    items = [record_to_item(r) for r in records]
    next_cursor = encode_cursor(last_key) if last_key else None
    return AuditLogResponse(events=items, count=len(items), next_cursor=next_cursor)
