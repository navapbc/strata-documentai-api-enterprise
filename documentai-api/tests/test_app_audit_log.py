"""Tests for GET /v1/admin/audit-log endpoint."""

import pytest

from documentai_api.schemas.audit_event import AuditAction, AuditTargetType
from documentai_api.utils.audit_log import log_event
from tests.helpers.fixtures.claims import (
    SUPER_ADMIN_CLAIMS,
    TENANT_ADMIN_CLAIMS,
    TENANT_ADMIN_ID,
    override_jwt,
)
from tests.helpers.fixtures.cognito import create_cognito_user

AUDIT_LOG_URL = "/v1/admin/audit-log"


@pytest.fixture
def seeded_events(audit_events_table):
    """Seed audit events across multiple tenants."""
    # Super-admin creates a tenant (lands in __global__)
    log_event(
        SUPER_ADMIN_CLAIMS,
        action=AuditAction.TENANT_CREATE,
        target_type=AuditTargetType.TENANT,
        target_id=TENANT_ADMIN_ID,
    )
    # Tenant-admin creates a key for their own tenant (lands in TENANT_ADMIN_ID)
    log_event(
        TENANT_ADMIN_CLAIMS,
        action=AuditAction.KEY_CREATE,
        target_type=AuditTargetType.KEY,
        target_id="abc12345",
        tenant_id=TENANT_ADMIN_ID,
    )
    # Super-admin revokes a key in another tenant (lands in "other-tenant")
    log_event(
        SUPER_ADMIN_CLAIMS,
        action=AuditAction.KEY_REVOKE,
        target_type=AuditTargetType.KEY,
        target_id="def67890",
        tenant_id="other-tenant",
    )


def test_audit_log_unauthenticated_returns_401(api_client):
    response = api_client.get(AUDIT_LOG_URL)
    assert response.status_code == 401


def test_audit_log_pending_user_returns_403(api_client):
    override_jwt({**SUPER_ADMIN_CLAIMS, "cognito:groups": []})
    response = api_client.get(AUDIT_LOG_URL)
    assert response.status_code == 403


def test_audit_log_super_admin_queries_global(api_client, seeded_events):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(AUDIT_LOG_URL)
    assert response.status_code == 200
    data = response.json()
    # All 3 events appear in __global__ (1 direct + 2 double-writes)
    assert data["count"] == 3


def test_audit_log_super_admin_queries_by_tenant(api_client, seeded_events):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(AUDIT_LOG_URL, params={"tenant_id": TENANT_ADMIN_ID})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["events"][0]["action"] == AuditAction.KEY_CREATE


def test_audit_log_super_admin_queries_by_action(api_client, seeded_events):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(AUDIT_LOG_URL, params={"action": AuditAction.KEY_CREATE})
    assert response.status_code == 200
    data = response.json()
    # 2 items: tenant partition + __global__ double-write
    assert data["count"] == 2
    assert all(e["action"] == AuditAction.KEY_CREATE for e in data["events"])


def test_audit_log_tenant_admin_sees_own_only(api_client, seeded_events):
    override_jwt(TENANT_ADMIN_CLAIMS)
    response = api_client.get(AUDIT_LOG_URL)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert all(e["tenantId"] == TENANT_ADMIN_ID for e in data["events"])


def test_audit_log_tenant_admin_cannot_query_other_tenant(api_client, seeded_events):
    override_jwt(TENANT_ADMIN_CLAIMS)
    response = api_client.get(AUDIT_LOG_URL, params={"tenant_id": "other-tenant"})
    assert response.status_code == 403


def test_audit_log_respects_limit(api_client, audit_events_table):
    override_jwt(SUPER_ADMIN_CLAIMS)
    # Seed 5 events in __global__
    for i in range(5):
        log_event(
            SUPER_ADMIN_CLAIMS,
            action=AuditAction.TENANT_CREATE,
            target_type=AuditTargetType.TENANT,
            target_id=f"tenant-{i}",
        )
    response = api_client.get(AUDIT_LOG_URL, params={"limit": 3})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    assert data["nextCursor"] is not None


def test_audit_log_pagination(api_client, audit_events_table):
    override_jwt(SUPER_ADMIN_CLAIMS)
    for i in range(5):
        log_event(
            SUPER_ADMIN_CLAIMS,
            action=AuditAction.TENANT_CREATE,
            target_type=AuditTargetType.TENANT,
            target_id=f"tenant-{i}",
        )
    # First page
    resp1 = api_client.get(AUDIT_LOG_URL, params={"limit": 3})
    data1 = resp1.json()
    assert data1["count"] == 3
    # Second page
    resp2 = api_client.get(AUDIT_LOG_URL, params={"limit": 3, "cursor": data1["nextCursor"]})
    data2 = resp2.json()
    assert data2["count"] == 2
    assert data2["nextCursor"] is None


def test_audit_log_invalid_cursor_returns_400(api_client, audit_events_table):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(AUDIT_LOG_URL, params={"cursor": "not-valid-base64!"})
    assert response.status_code == 400


def test_audit_log_filter_by_action_and_tenant(api_client, seeded_events):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(
        AUDIT_LOG_URL, params={"tenant_id": TENANT_ADMIN_ID, "action": AuditAction.KEY_CREATE}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["events"][0]["action"] == AuditAction.KEY_CREATE
    assert data["events"][0]["tenantId"] == TENANT_ADMIN_ID


##############################################################################
# GET /v1/admin/audit-log/actions
##############################################################################

ACTIONS_URL = "/v1/admin/audit-log/actions"


def test_actions_unauthenticated_returns_401(api_client):
    response = api_client.get(ACTIONS_URL)
    assert response.status_code == 401


def test_actions_returns_sorted_list(api_client):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(ACTIONS_URL)
    assert response.status_code == 200
    data = response.json()
    actions = data["actions"]
    assert isinstance(actions, list)
    assert len(actions) > 0
    assert actions == sorted(actions)


def test_actions_contains_known_actions(api_client):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(ACTIONS_URL)
    actions = response.json()["actions"]
    assert AuditAction.KEY_CREATE in actions
    assert AuditAction.TENANT_CREATE in actions
    assert AuditAction.USER_DELETE in actions


def test_actions_tenant_admin_can_access(api_client):
    override_jwt(TENANT_ADMIN_CLAIMS)
    response = api_client.get(ACTIONS_URL)
    assert response.status_code == 200
    assert len(response.json()["actions"]) > 0


##############################################################################
# GET /v1/admin/audit-log/actors
##############################################################################

ACTORS_URL = "/v1/admin/audit-log/actors"


def test_actors_unauthenticated_returns_401(api_client):
    response = api_client.get(ACTORS_URL)
    assert response.status_code == 401


def test_actors_does_not_fetch_group_memberships(api_client, cognito_client, mocker):
    """Perf regression guard: actors only needs email/tenant_id.

    It must skip the per-user admin_list_groups_for_user lookup that /users needs.
    """
    from documentai_api.services.aws_client_factory import AWSClientFactory

    create_cognito_user(cognito_client, "admin-1", "admin@example.com")
    spy = mocker.spy(AWSClientFactory.get_cognito_client(), "admin_list_groups_for_user")

    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(ACTORS_URL)

    assert response.status_code == 200
    spy.assert_not_called()


def test_actors_super_admin_returns_all_distinct_emails(api_client, cognito_client):
    create_cognito_user(cognito_client, "admin-1", "admin@example.com")
    create_cognito_user(cognito_client, "user-1", "user@example.com", tenant_id=TENANT_ADMIN_ID)
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(ACTORS_URL)
    assert response.status_code == 200
    actors = response.json()["actors"]
    assert "admin@example.com" in actors
    assert "user@example.com" in actors


def test_actors_returns_sorted_list(api_client, cognito_client):
    create_cognito_user(cognito_client, "zeta-1", "zeta@example.com")
    create_cognito_user(cognito_client, "admin-1", "admin@example.com")
    create_cognito_user(cognito_client, "user-1", "user@example.com", tenant_id=TENANT_ADMIN_ID)
    override_jwt(SUPER_ADMIN_CLAIMS)
    actors = api_client.get(ACTORS_URL).json()["actors"]
    assert actors == sorted(actors)


def test_actors_returns_unique_emails(api_client, cognito_client):
    """Two Cognito accounts sharing an email collapse to one entry - actors is a set."""
    create_cognito_user(cognito_client, "admin-1", "admin@example.com")
    create_cognito_user(cognito_client, "admin-2", "admin@example.com")
    override_jwt(SUPER_ADMIN_CLAIMS)
    actors = api_client.get(ACTORS_URL).json()["actors"]
    assert actors.count("admin@example.com") == 1


def test_actors_tenant_admin_sees_own_tenant_only(api_client, cognito_client):
    create_cognito_user(cognito_client, "user-1", "user@example.com", tenant_id=TENANT_ADMIN_ID)
    create_cognito_user(cognito_client, "other-1", "other@example.com", tenant_id="other-tenant")
    override_jwt(TENANT_ADMIN_CLAIMS)
    response = api_client.get(ACTORS_URL)
    assert response.status_code == 200
    actors = response.json()["actors"]
    assert actors == ["user@example.com"]


def test_actors_tenant_scope_excludes_history_only_actors_by_design(
    api_client, audit_events_table, cognito_client
):
    """Accepted tradeoff from the ADR: actors is Cognito-only, not derived from audit history.

    See docs/decisions/2026-08-06-audit-log-actor-dropdown-source.md. A
    super-admin who acted on a tenant's resources has no tenant_id in
    Cognito, so they won't appear here even though their email is visible in
    that tenant's audit rows - this is intentional, not a bug.
    """
    log_event(
        SUPER_ADMIN_CLAIMS,
        action=AuditAction.USER_APPROVE,
        target_type=AuditTargetType.USER,
        target_id="some-user",
        tenant_id=TENANT_ADMIN_ID,
    )
    override_jwt(SUPER_ADMIN_CLAIMS)
    actors = api_client.get(ACTORS_URL, params={"tenant_id": TENANT_ADMIN_ID}).json()["actors"]
    assert actors == []


def test_actors_empty_when_no_events(api_client, audit_events_table, cognito_client):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(ACTORS_URL)
    assert response.status_code == 200
    assert response.json()["actors"] == []


##############################################################################
# GET /v1/admin/audit-log?actor_email=...
##############################################################################


def test_audit_log_super_admin_filter_by_actor(api_client, seeded_events):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(AUDIT_LOG_URL, params={"actor_email": "user@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    assert all(e["actorEmail"] == "user@example.com" for e in data["events"])


def test_audit_log_super_admin_filter_by_actor_and_action(api_client, seeded_events):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(
        AUDIT_LOG_URL,
        params={"actor_email": "admin@example.com", "action": AuditAction.KEY_REVOKE},
    )
    assert response.status_code == 200
    data = response.json()
    assert all(e["actorEmail"] == "admin@example.com" for e in data["events"])
    assert all(e["action"] == AuditAction.KEY_REVOKE for e in data["events"])


def test_audit_log_filter_by_actor_within_tenant(api_client, seeded_events):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(
        AUDIT_LOG_URL,
        params={"tenant_id": TENANT_ADMIN_ID, "actor_email": "user@example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["events"][0]["actorEmail"] == "user@example.com"
    assert data["events"][0]["tenantId"] == TENANT_ADMIN_ID


def test_audit_log_filter_by_actor_no_match_returns_empty(api_client, seeded_events):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(AUDIT_LOG_URL, params={"actor_email": "nobody@example.com"})
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_audit_log_tenant_admin_filter_by_actor(api_client, seeded_events):
    override_jwt(TENANT_ADMIN_CLAIMS)
    response = api_client.get(AUDIT_LOG_URL, params={"actor_email": "user@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["events"][0]["actorEmail"] == "user@example.com"


##############################################################################
# Filter + limit interaction (regression: DynamoDB Limit applied pre-filter)
##############################################################################


def test_audit_log_filter_by_actor_and_action_past_limit_boundary(api_client, audit_events_table):
    """Matching events must be returned even when buried past the Limit boundary.

    Seeds (limit + 1) non-matching events for the actor, then one matching
    event with a different action.  Without the internal pagination fix the
    query would read exactly `limit` items, find no matches, and return empty.
    """
    override_jwt(SUPER_ADMIN_CLAIMS)
    limit = 5

    # Seed (limit + 1) events that won't match the action filter
    for i in range(limit + 1):
        log_event(
            SUPER_ADMIN_CLAIMS,
            action=AuditAction.TENANT_CREATE,
            target_type=AuditTargetType.TENANT,
            target_id=f"tenant-{i}",
        )

    # Seed one event that matches both actor and action
    log_event(
        SUPER_ADMIN_CLAIMS,
        action=AuditAction.KEY_REVOKE,
        target_type=AuditTargetType.KEY,
        target_id="key-target",
    )

    response = api_client.get(
        AUDIT_LOG_URL,
        params={
            "actor_email": "admin@example.com",
            "action": AuditAction.KEY_REVOKE,
            "limit": limit,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert all(e["action"] == AuditAction.KEY_REVOKE for e in data["events"])
