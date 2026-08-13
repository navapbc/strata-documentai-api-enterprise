"""Response models for the user-management (Cognito) endpoints."""

from pydantic import Field

from documentai_api.models.base import BaseApiResponse


class CognitoUserItem(BaseApiResponse):
    username: str
    email: str | None = None
    email_verified: bool = False
    status: str | None = None
    enabled: bool = True
    created_at: str | None = None
    tenant_id: str | None = None
    groups: list[str] | None = Field(
        default=None,
        description="Role group memberships, or null if not fetched (see list_users(include_groups=)).",
    )


class ListUsersResponse(BaseApiResponse):
    users: list[CognitoUserItem]
    count: int
