"""Test fixtures for Cognito-backed user management endpoints."""

from typing import Any

import boto3
import pytest
from moto import mock_aws

POOL_NAME = "test-user-pool"


@pytest.fixture
def cognito_client(aws_credentials, monkeypatch):
    """Create mock Cognito user pool with groups/schema, point to app via COGNITO_USER_POOL_ID."""
    with mock_aws():
        client = boto3.client("cognito-idp", region_name="us-east-1")
        pool = client.create_user_pool(
            PoolName=POOL_NAME,
            Schema=[{"Name": "tenant_id", "AttributeDataType": "String", "Mutable": True}],
        )
        pool_id = pool["UserPool"]["Id"]
        client.create_group(UserPoolId=pool_id, GroupName="super-admin")
        client.create_group(UserPoolId=pool_id, GroupName="tenant-admin")

        monkeypatch.setenv("COGNITO_USER_POOL_ID", pool_id)
        # get_aws_config() is process-lifetime-cached; whichever fixture reads
        # it first (e.g. a sibling fixture that logs an event during setup)
        # freezes this value for the rest of the test unless we invalidate it
        # here, regardless of fixture parameter order.
        from documentai_api.config.env import get_aws_config

        get_aws_config.cache_clear()
        client.pool_id = pool_id
        yield client


def create_cognito_user(
    client: Any,
    username: str,
    email: str,
    role: str | None = None,
    tenant_id: str | None = None,
) -> None:
    """Create a user in the fixture's pool, optionally with a group and tenant."""
    attrs = [
        {"Name": "email", "Value": email},
        {"Name": "email_verified", "Value": "true"},
    ]
    if tenant_id:
        attrs.append({"Name": "custom:tenant_id", "Value": tenant_id})
    client.admin_create_user(UserPoolId=client.pool_id, Username=username, UserAttributes=attrs)
    if role:
        client.admin_add_user_to_group(UserPoolId=client.pool_id, Username=username, GroupName=role)


@pytest.fixture
def seeded_cognito_users(cognito_client):
    """Seed a super-admin and two tenant-admins across two tenants."""
    create_cognito_user(cognito_client, "super-admin-1", "super@example.com", role="super-admin")
    create_cognito_user(
        cognito_client,
        "tenant-admin-1",
        "acme-admin@example.com",
        role="tenant-admin",
        tenant_id="acme",
    )
    create_cognito_user(
        cognito_client,
        "tenant-admin-2",
        "globex-admin@example.com",
        role="tenant-admin",
        tenant_id="globex",
    )
    return cognito_client
