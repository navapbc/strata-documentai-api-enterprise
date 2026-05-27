"""Tests for auth event reporting and audit logging on categories/extraction rules."""

import pytest
from fastapi.testclient import TestClient

from documentai_api.annotations import verify_jwt_with_role
from documentai_api.app import app
from documentai_api.schemas.audit_event import AuditAction, AuditTargetType
from documentai_api.utils.auth import UserContext, get_user_context_with_fallback

client = TestClient(app)

MOCK_CONTEXT = UserContext(tenant_id="test-tenant", api_key_name="test-client")
MOCK_CLAIMS = {
    "sub": "user-123",
    "email": "admin@test.com",
    "cognito:groups": ["super-admin"],
}


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_user_context_with_fallback] = lambda: MOCK_CONTEXT
    app.dependency_overrides[verify_jwt_with_role] = lambda: MOCK_CLAIMS
    yield
    app.dependency_overrides.pop(get_user_context_with_fallback, None)
    app.dependency_overrides.pop(verify_jwt_with_role, None)


@pytest.fixture
def mock_log_event(mocker):
    return mocker.patch("documentai_api.app_auth_events.log_event")


@pytest.fixture
def mock_log_event_categories(mocker):
    return mocker.patch("documentai_api.app_document_categories.log_event")


@pytest.fixture
def mock_log_event_rules(mocker):
    return mocker.patch("documentai_api.app_extraction_rules.log_event")


# =============================================================================
# Auth events endpoint
# =============================================================================


def test_report_login_event(mock_log_event):
    response = client.post(
        "/v1/audit/auth-event", json={"action": "login", "email": "admin@co.com"}
    )

    assert response.status_code == 204
    mock_log_event.assert_called_once_with(
        claims={"sub": "admin@co.com", "email": "admin@co.com"},
        action=AuditAction.AUTH_LOGIN,
        target_type=AuditTargetType.SESSION,
        target_id="admin@co.com",
        tenant_id="test-tenant",
        metadata=None,
    )


def test_report_logout_event(mock_log_event):
    response = client.post(
        "/v1/audit/auth-event", json={"action": "logout", "email": "admin@co.com"}
    )

    assert response.status_code == 204
    mock_log_event.assert_called_once_with(
        claims={"sub": "admin@co.com", "email": "admin@co.com"},
        action=AuditAction.AUTH_LOGOUT,
        target_type=AuditTargetType.SESSION,
        target_id="admin@co.com",
        tenant_id="test-tenant",
        metadata=None,
    )


def test_report_event_with_metadata(mock_log_event):
    response = client.post(
        "/v1/audit/auth-event",
        json={"action": "login", "email": "admin@co.com", "metadata": {"ip": "1.2.3.4"}},
    )

    assert response.status_code == 204
    mock_log_event.assert_called_once()
    call_kwargs = mock_log_event.call_args[1]
    assert call_kwargs["metadata"] == {"ip": "1.2.3.4"}


def test_report_unknown_action_ignored(mock_log_event):
    response = client.post("/v1/audit/auth-event", json={"action": "unknown_action"})

    assert response.status_code == 204
    mock_log_event.assert_not_called()


def test_report_event_without_email_uses_api_key_name(mock_log_event):
    response = client.post("/v1/audit/auth-event", json={"action": "login"})

    assert response.status_code == 204
    mock_log_event.assert_called_once()
    call_kwargs = mock_log_event.call_args[1]
    assert call_kwargs["target_id"] == "test-client"
    assert call_kwargs["claims"] == {"sub": "test-client", "email": "test-client"}


# =============================================================================
# Document categories audit logging
# =============================================================================


def test_create_category_logs_audit(mock_log_event_categories, mocker):
    mocker.patch(
        "documentai_api.app_document_categories.categories_util.create_category",
        return_value={
            "tenantId": "test-tenant",
            "categoryName": "tax",
            "displayName": "Tax",
            "description": "",
            "isActive": True,
            "createdAt": "2026-01-01",
            "updatedAt": "2026-01-01",
        },
    )

    response = client.post(
        "/v1/admin/document-categories?tenant_id=test-tenant",
        json={"category_name": "tax", "display_name": "Tax"},
    )

    assert response.status_code == 201
    mock_log_event_categories.assert_called_once_with(
        claims=MOCK_CLAIMS,
        action=AuditAction.DOCUMENT_CATEGORY_CREATE,
        target_type=AuditTargetType.DOCUMENT_CATEGORY,
        target_id="tax",
        tenant_id="test-tenant",
    )


def test_delete_category_logs_audit(mock_log_event_categories, mocker):
    mocker.patch(
        "documentai_api.app_document_categories.categories_util.delete_category",
        return_value=True,
    )

    response = client.delete("/v1/admin/document-categories/tax?tenant_id=test-tenant")

    assert response.status_code == 204
    mock_log_event_categories.assert_called_once_with(
        claims=MOCK_CLAIMS,
        action=AuditAction.DOCUMENT_CATEGORY_DEACTIVATE,
        target_type=AuditTargetType.DOCUMENT_CATEGORY,
        target_id="tax",
        tenant_id="test-tenant",
    )


# =============================================================================
# Extraction rules audit logging
# =============================================================================


def test_put_extraction_rule_logs_audit(mock_log_event_rules, mocker):
    mocker.patch(
        "documentai_api.utils.extraction_rules.upsert_rule",
        return_value={
            "tenant_id": "test-tenant",
            "document_type": "W2",
            "required_fields": ["ssn"],
            "optional_fields": [],
            "createdAt": "2026-01-01",
            "updatedAt": "2026-01-01",
        },
    )

    response = client.put(
        "/v1/config/extraction-rules",
        json={
            "tenant_id": "test-tenant",
            "document_type": "W2",
            "required_fields": ["ssn"],
            "optional_fields": [],
        },
    )

    assert response.status_code == 200
    mock_log_event_rules.assert_called_once_with(
        claims={"sub": "test-client", "email": "test-client"},
        action=AuditAction.EXTRACTION_RULE_UPDATE,
        target_type=AuditTargetType.EXTRACTION_RULE,
        target_id="W2",
        tenant_id="test-tenant",
    )


def test_delete_extraction_rule_logs_audit(mock_log_event_rules, mocker):
    mocker.patch(
        "documentai_api.utils.extraction_rules.delete_rule",
        return_value=True,
    )

    response = client.delete("/v1/config/extraction-rules?document_type=W2&tenant_id=test-tenant")

    assert response.status_code == 200
    mock_log_event_rules.assert_called_once_with(
        claims={"sub": "test-client", "email": "test-client"},
        action=AuditAction.EXTRACTION_RULE_DELETE,
        target_type=AuditTargetType.EXTRACTION_RULE,
        target_id="W2",
        tenant_id="test-tenant",
    )


def test_update_category_logs_audit(mock_log_event_categories, mocker):
    mocker.patch(
        "documentai_api.app_document_categories.categories_util.update_category",
        return_value={
            "tenantId": "test-tenant",
            "categoryName": "tax",
            "displayName": "Tax Updated",
            "description": "",
            "isActive": True,
            "createdAt": "2026-01-01",
            "updatedAt": "2026-01-02",
        },
    )

    response = client.patch(
        "/v1/admin/document-categories/tax?tenant_id=test-tenant",
        json={"display_name": "Tax Updated"},
    )

    assert response.status_code == 200
    mock_log_event_categories.assert_called_once_with(
        claims=MOCK_CLAIMS,
        action=AuditAction.DOCUMENT_CATEGORY_UPDATE,
        target_type=AuditTargetType.DOCUMENT_CATEGORY,
        target_id="tax",
        tenant_id="test-tenant",
    )


# =============================================================================
# No audit on failure
# =============================================================================


def test_create_category_no_audit_on_conflict(mock_log_event_categories, mocker):
    mocker.patch(
        "documentai_api.app_document_categories.categories_util.create_category",
        side_effect=ValueError("Category already exists"),
    )

    response = client.post(
        "/v1/admin/document-categories?tenant_id=test-tenant",
        json={"category_name": "tax", "display_name": "Tax"},
    )

    assert response.status_code == 409
    mock_log_event_categories.assert_not_called()


def test_delete_category_no_audit_on_not_found(mock_log_event_categories, mocker):
    mocker.patch(
        "documentai_api.app_document_categories.categories_util.delete_category",
        return_value=False,
    )

    response = client.delete("/v1/admin/document-categories/missing?tenant_id=test-tenant")

    assert response.status_code == 404
    mock_log_event_categories.assert_not_called()


def test_delete_extraction_rule_no_audit_on_not_found(mock_log_event_rules, mocker):
    mocker.patch(
        "documentai_api.utils.extraction_rules.delete_rule",
        return_value=False,
    )

    response = client.delete("/v1/config/extraction-rules?document_type=W2&tenant_id=test-tenant")

    assert response.status_code == 404
    mock_log_event_rules.assert_not_called()


# =============================================================================
# Edge cases
# =============================================================================


def test_missing_action_returns_422():
    """Pydantic rejects request body without required 'action' field."""
    response = client.post("/v1/audit/auth-event", json={"email": "a@b.com"})
    assert response.status_code == 422


def test_non_dict_metadata_returns_422():
    """Pydantic rejects non-dict metadata."""
    response = client.post(
        "/v1/audit/auth-event", json={"action": "login", "metadata": "not-a-dict"}
    )
    assert response.status_code == 422


def test_action_is_case_sensitive(mock_log_event):
    """'Login' (capitalized) is not recognized - silently ignored."""
    response = client.post("/v1/audit/auth-event", json={"action": "Login", "email": "a@b.com"})

    assert response.status_code == 204
    mock_log_event.assert_not_called()


def test_audit_logging_failure_does_not_break_request(mocker):
    """log_event already catches exceptions internally - verify endpoint still succeeds."""
    # Mock the DDB table to raise, but log_event catches it
    mocker.patch(
        "documentai_api.utils.audit.AWSClientFactory.get_ddb_table",
        side_effect=RuntimeError("DDB unavailable"),
    )

    response = client.post("/v1/audit/auth-event", json={"action": "login", "email": "a@b.com"})

    assert response.status_code == 204


def test_category_audit_failure_does_not_break_create(mocker):
    """log_event failure doesn't prevent category creation."""
    mocker.patch(
        "documentai_api.app_document_categories.categories_util.create_category",
        return_value={
            "tenantId": "test-tenant",
            "categoryName": "tax",
            "displayName": "Tax",
            "description": "",
            "isActive": True,
            "createdAt": "2026-01-01",
            "updatedAt": "2026-01-01",
        },
    )
    mocker.patch(
        "documentai_api.utils.audit.AWSClientFactory.get_ddb_table",
        side_effect=RuntimeError("DDB unavailable"),
    )

    response = client.post(
        "/v1/admin/document-categories?tenant_id=test-tenant",
        json={"category_name": "tax", "display_name": "Tax"},
    )

    assert response.status_code == 201
