"""Auth event reporting endpoint - allows the admin UI to report auth events."""

from fastapi import APIRouter, Depends

from documentai_api.annotations import AuthUserWithFallback
from documentai_api.config.constants import ApiVisualizationTag
from documentai_api.logging import get_logger
from documentai_api.models.auth_event import AuthEventRequest
from documentai_api.schemas.audit_event import AuditAction, AuditTargetType
from documentai_api.utils.audit import log_event
from documentai_api.utils.auth import get_user_context_with_fallback

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(get_user_context_with_fallback)])

VALID_AUTH_ACTIONS = {
    "login": AuditAction.AUTH_LOGIN,
    "logout": AuditAction.AUTH_LOGOUT,
}


@router.post(
    "/v1/audit/auth-event",
    status_code=204,
    tags=[ApiVisualizationTag.ADMIN_AUDIT_LOG],
)
async def report_auth_event(
    body: AuthEventRequest,
    auth: AuthUserWithFallback,
) -> None:
    """Report an auth event from the admin UI (login, logout)."""
    audit_action = VALID_AUTH_ACTIONS.get(body.action)
    if not audit_action:
        return  # Silently ignore unknown actions

    # Build a claims-like dict for log_event
    claims = {
        "sub": body.email or auth.api_key_name,
        "email": body.email or auth.api_key_name,
    }

    try:
        log_event(
            claims=claims,
            action=audit_action,
            target_type=AuditTargetType.SESSION,
            target_id=body.email or auth.api_key_name,
            tenant_id=auth.tenant_id,
            metadata=body.metadata,
        )
    except Exception:
        logger.exception("Failed to write auth audit event")
