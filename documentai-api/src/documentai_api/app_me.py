"""Identity endpoint - returns the authenticated user's context."""

from fastapi import APIRouter

from documentai_api.annotations import AuthMethod, AuthUserWithFallback
from documentai_api.config.constants import ApiVisualizationTag
from documentai_api.models.base import BaseApiResponse

router = APIRouter(tags=[ApiVisualizationTag.IDENTITY])


class MeResponse(BaseApiResponse):
    tenant_id: str
    principal: str
    auth_method: AuthMethod


@router.get("/v1/me")
async def get_me(auth: AuthUserWithFallback) -> MeResponse:
    """Return the authenticated user's identity context.

    Works with both API key and JWT auth. For API key callers, principal is the
    key name. For JWT callers, principal is the email or sub.

    Note: pending JWT users (no Cognito group) still get 200 here - the UI
    needs this to render the "pending approval" state. Access control is
    enforced at the individual admin endpoints via verify_jwt_with_role.
    """
    return MeResponse(
        tenant_id=auth.tenant_id,
        principal=auth.api_key_name,
        auth_method=auth.auth_method,
    )
