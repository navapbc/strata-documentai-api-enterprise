"""Response models for the user-management (Cognito) endpoints."""

from pydantic import Field

from documentai_api.models.base import BaseApiResponse


class CognitoUserItem(BaseApiResponse):
    """User response item.

    When privacy mode is active, `email` and `username` are masked and
    `masked_tenant_id` is populated. The real `tenant_id` is always returned so that
    frontend filter calls continue to work - `masked_tenant_id` is for display only.
    """

    username: str
    email: str | None = None
    email_verified: bool = False
    status: str | None = None
    enabled: bool = True
    created_at: str | None = None
    tenant_id: str | None = None
    masked_tenant_id: str | None = None
    groups: list[str] | None = Field(
        default=None,
        description="Role group memberships, or null if not fetched (see list_users(include_groups=)).",
    )


class ListUsersResponse(BaseApiResponse):
    users: list[CognitoUserItem]
    count: int
