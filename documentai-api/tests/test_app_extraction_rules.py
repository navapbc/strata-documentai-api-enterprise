from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from documentai_api.app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _disable_auth(disable_auth):
    pass


MOCK_RULE = {
    "tenantId": "test-tenant",
    "documentType": "W2",
    "requiredFields": ["ssn", "wages"],
    "optionalFields": ["employer_name"],
    "createdAt": "2026-01-01T00:00:00+00:00",
    "updatedAt": "2026-01-01T00:00:00+00:00",
}


def test_get_extraction_rules():
    with patch("documentai_api.utils.extraction_rules.get_rules", return_value=[MOCK_RULE]):
        response = client.get("/v1/config/extraction-rules")

    assert response.status_code == 200
    rules = response.json()["rules"]
    assert len(rules) == 1
    assert rules[0]["tenantId"] == "test-tenant"
    assert rules[0]["documentType"] == "W2"
    assert rules[0]["requiredFields"] == ["ssn", "wages"]
    assert rules[0]["optionalFields"] == ["employer_name"]


def test_get_extraction_rules_by_document_type():
    with patch("documentai_api.utils.extraction_rules.get_rules", return_value=[MOCK_RULE]):
        response = client.get("/v1/config/extraction-rules?document_type=W2")

    assert response.status_code == 200
    assert len(response.json()["rules"]) == 1


def test_get_extraction_rules_not_found():
    with patch("documentai_api.utils.extraction_rules.get_rules", return_value=[]):
        response = client.get("/v1/config/extraction-rules?document_type=W2")

    assert response.status_code == 404


def test_put_extraction_rule():
    rule = {
        "tenantId": "test-tenant",
        "documentType": "W2",
        "requiredFields": ["ssn", "wages"],
        "optionalFields": ["employer_name"],
        "createdAt": "2026-01-01",
        "updatedAt": "2026-01-01",
    }
    with patch("documentai_api.utils.extraction_rules.upsert_rule", return_value=rule):
        response = client.put(
            "/v1/config/extraction-rules",
            json={
                "document_type": "W2",
                "required_fields": ["ssn", "wages"],
                "optional_fields": ["employer_name"],
            },
        )

    assert response.status_code == 200
    assert response.json()["requiredFields"] == ["ssn", "wages"]
    assert response.json()["optionalFields"] == ["employer_name"]


def test_put_extraction_rule_invalid_required_fields():
    response = client.put(
        "/v1/config/extraction-rules",
        json={
            "document_type": "W2",
            "required_fields": "not a list",
            "optional_fields": [],
        },
    )
    assert response.status_code == 422


def test_put_extraction_rule_invalid_optional_fields():
    response = client.put(
        "/v1/config/extraction-rules",
        json={
            "document_type": "W2",
            "required_fields": [],
            "optional_fields": "not a list",
        },
    )
    assert response.status_code == 422


def test_delete_extraction_rule():
    with patch(
        "documentai_api.utils.extraction_rules.delete_rule", return_value=True
    ) as mock_delete:
        response = client.delete("/v1/config/extraction-rules?document_type=W2")

    assert response.status_code == 200
    mock_delete.assert_called_once_with("test-tenant", "W2")


def test_delete_extraction_rule_not_found():
    """DELETE returns 404 when rule doesn't exist."""
    with patch("documentai_api.utils.extraction_rules.delete_rule", return_value=False):
        response = client.delete("/v1/config/extraction-rules?document_type=NonExistent")

    assert response.status_code == 404
    assert "Rule not found" in response.json()["detail"]


def test_get_extraction_rules_empty_collection():
    """GET without document_type returns 200 with empty list when no rules exist."""
    with patch("documentai_api.utils.extraction_rules.get_rules", return_value=[]):
        response = client.get("/v1/config/extraction-rules")

    assert response.status_code == 200
    assert response.json()["rules"] == []


def test_put_extraction_rule_uses_auth_tenant(mocker):
    """PUT derives tenant_id from auth, not from request body."""
    mock_upsert = mocker.patch("documentai_api.utils.extraction_rules.upsert_rule")
    mock_upsert.return_value = {
        "tenantId": "test-tenant",
        "documentType": "W2",
        "requiredFields": ["ssn"],
        "optionalFields": [],
        "createdAt": "2026-01-01",
        "updatedAt": "2026-01-01",
    }

    response = client.put(
        "/v1/config/extraction-rules",
        json={
            "document_type": "W2",
            "required_fields": ["ssn"],
            "optional_fields": [],
        },
    )

    assert response.status_code == 200
    # Verify upsert was called with auth tenant, not any client-supplied value
    call_args = mock_upsert.call_args
    assert call_args[0][0] == "test-tenant"


def test_put_extraction_rule_rejects_non_string_list():
    """PUT rejects required_fields with non-string elements."""
    response = client.put(
        "/v1/config/extraction-rules",
        json={
            "document_type": "W2",
            "required_fields": [1, 2, 3],
            "optional_fields": [],
        },
    )
    assert response.status_code == 422


@pytest.mark.integration
def test_extraction_rules_tenant_isolation(extraction_rules_table):
    """End-to-end: tenant A cannot see or delete tenant B's rules."""
    from fastapi.testclient import TestClient

    from documentai_api.app import app
    from documentai_api.utils.auth import UserContext, get_user_context_with_fallback
    from documentai_api.utils.extraction_rules import upsert_rule

    # Seed a rule for tenant B directly in DDB
    upsert_rule("tenant-b", "W2", ["ssn"], ["wages"])

    # Authenticate as tenant A
    mock_context = UserContext(tenant_id="tenant-a", api_key_name="client-a")
    app.dependency_overrides[get_user_context_with_fallback] = lambda: mock_context

    try:
        tenant_a_client = TestClient(app)

        # GET — tenant A should not see tenant B's rule
        response = tenant_a_client.get("/v1/config/extraction-rules?document_type=W2")
        assert response.status_code == 404

        # DELETE — tenant A cannot delete tenant B's rule
        response = tenant_a_client.delete("/v1/config/extraction-rules?document_type=W2")
        assert response.status_code == 404

        # PUT — tenant A creates their own rule
        response = tenant_a_client.put(
            "/v1/config/extraction-rules",
            json={
                "document_type": "W2",
                "required_fields": ["employer"],
                "optional_fields": [],
            },
        )
        assert response.status_code == 200
        assert response.json()["tenantId"] == "tenant-a"

        # Verify tenant B's rule is untouched
        from documentai_api.utils.extraction_rules import get_rules

        b_rules = get_rules("tenant-b", "W2")
        assert len(b_rules) == 1
        assert b_rules[0]["requiredFields"] == ["ssn"]
    finally:
        app.dependency_overrides.clear()
