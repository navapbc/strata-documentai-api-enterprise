"""Tests for the Cognito service layer, focused on the include_groups perf flag."""

from documentai_api.services import cognito as cognito_service
from documentai_api.utils.aws_client_factory import AWSClientFactory
from tests.helpers.fixtures.cognito import create_cognito_user


def test_list_users_include_groups_true_fetches_groups(cognito_client):
    create_cognito_user(
        cognito_client, "user-1", "user1@example.com", role="tenant-admin", tenant_id="acme"
    )
    users = cognito_service.list_users(include_groups=True)
    user = next(u for u in users if u.username == "user-1")
    assert user.groups == ["tenant-admin"]


def test_list_users_include_groups_false_skips_group_lookup(cognito_client, mocker):
    create_cognito_user(
        cognito_client, "user-1", "user1@example.com", role="tenant-admin", tenant_id="acme"
    )
    spy = mocker.spy(AWSClientFactory.get_cognito_client(), "admin_list_groups_for_user")

    users = cognito_service.list_users(include_groups=False)

    spy.assert_not_called()
    user = next(u for u in users if u.username == "user-1")
    # None (not fetched), not [] (fetched, empty) - distinguishes "didn't ask"
    # from "genuinely has no groups".
    assert user.groups is None
    assert user.email == "user1@example.com"
    assert user.tenant_id == "acme"
