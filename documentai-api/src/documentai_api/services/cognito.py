"""Cognito user management - list, role assignment, tenant assignment."""

from typing import Any

from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.models.user import CognitoUserItem
from documentai_api.utils.aws_client_factory import AWSClientFactory

logger = get_logger(__name__)

TENANT_ATTRIBUTE = "custom:tenant_id"


def _user_pool_id() -> str:
    pool_id = get_aws_config().cognito_user_pool_id

    if not pool_id:
        raise ValueError("COGNITO_USER_POOL_ID environment variable not set")

    return pool_id


def _summarize_user(user: dict[str, Any], groups: list[str] | None) -> CognitoUserItem:
    """Reduce a Cognito user record to the fields the admin UI needs."""
    attrs = {a["Name"]: a["Value"] for a in user.get("Attributes", []) or []}

    return CognitoUserItem(
        username=user.get("Username"),
        email=attrs.get("email"),
        email_verified=attrs.get("email_verified") == "true",
        status=user.get("UserStatus"),
        enabled=user.get("Enabled", True),
        created_at=user["UserCreateDate"].isoformat() if user.get("UserCreateDate") else None,
        tenant_id=attrs.get(TENANT_ATTRIBUTE),
        groups=groups,
    )


def list_users(include_groups: bool = True) -> list[CognitoUserItem]:
    """List all users in the pool, optionally with their group memberships.

    Group membership costs one admin_list_groups_for_user call per user, so
    callers that don't need role information (e.g. the audit actor list,
    which only reads email/tenant_id) should pass include_groups=False to
    skip it - result items have groups=None rather than [] in that case, to
    distinguish "not fetched" from "fetched, no groups".
    """
    client = AWSClientFactory.get_cognito_client()
    pool_id = _user_pool_id()

    users: list[Any] = []
    paginator = client.get_paginator("list_users")

    for page in paginator.paginate(UserPoolId=pool_id):
        users.extend(page.get("Users", []))

    enriched: list[CognitoUserItem] = []

    for user in users:
        username = user.get("Username")

        if not username:
            continue

        group_names: list[str] | None = None

        if include_groups:
            groups_resp = client.admin_list_groups_for_user(UserPoolId=pool_id, Username=username)
            group_names = [
                g["GroupName"] for g in groups_resp.get("Groups", []) if g.get("GroupName")
            ]
        enriched.append(_summarize_user(user, group_names))

    return enriched


def add_to_group(username: str, group: str) -> None:
    client = AWSClientFactory.get_cognito_client()
    client.admin_add_user_to_group(UserPoolId=_user_pool_id(), Username=username, GroupName=group)


def remove_from_group(username: str, group: str) -> None:
    client = AWSClientFactory.get_cognito_client()
    client.admin_remove_user_from_group(
        UserPoolId=_user_pool_id(), Username=username, GroupName=group
    )


def set_tenant(username: str, tenant_id: str | None) -> None:
    """Set or clear which tenant this user is scoped to administer.

    This is an authorization scope (custom:tenant_id), not membership -
    pass None for super-admins or revoked users, who aren't scoped to any
    single tenant.
    """
    client = AWSClientFactory.get_cognito_client()
    if tenant_id:
        client.admin_update_user_attributes(
            UserPoolId=_user_pool_id(),
            Username=username,
            UserAttributes=[{"Name": TENANT_ATTRIBUTE, "Value": tenant_id}],
        )
    else:
        client.admin_delete_user_attributes(
            UserPoolId=_user_pool_id(),
            Username=username,
            UserAttributeNames=[TENANT_ATTRIBUTE],
        )


def delete_user(username: str) -> None:
    client = AWSClientFactory.get_cognito_client()
    client.admin_delete_user(UserPoolId=_user_pool_id(), Username=username)


def replace_role(username: str, new_role: str | None) -> None:
    """Remove the user from any role group and optionally add them to a new one.

    Passing ``None`` returns the user to the pending state (no groups).
    """
    client = AWSClientFactory.get_cognito_client()
    pool_id = _user_pool_id()
    groups_resp = client.admin_list_groups_for_user(UserPoolId=pool_id, Username=username)
    for g in groups_resp.get("Groups", []):
        name = g.get("GroupName")
        if name in ("super-admin", "tenant-admin"):
            client.admin_remove_user_from_group(
                UserPoolId=pool_id, Username=username, GroupName=name
            )
    if new_role:
        client.admin_add_user_to_group(UserPoolId=pool_id, Username=username, GroupName=new_role)
