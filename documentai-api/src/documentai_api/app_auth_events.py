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

    # Use the verified identity from the auth context, not the caller-supplied
    # body.email, to prevent actor identity spoofing in audit records.
    verified_actor = auth.api_key_name

    claims = {
        "sub": verified_actor,
        "email": verified_actor,
    }

    try:
        log_event(
            claims=claims,
            action=audit_action,
            target_type=AuditTargetType.SESSION,
            target_id=verified_actor,
            tenant_id=auth.tenant_id,
            metadata=body.metadata,
        )
    except Exception:
        logger.exception("Failed to write auth audit event")
