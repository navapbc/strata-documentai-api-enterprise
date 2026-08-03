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
    with (
        patch("documentai_api.utils.extraction_rules.upsert_rule", return_value=rule),
        patch(
            "documentai_api.app_extraction_rules.get_valid_fields",
            return_value={"ssn", "wages", "employer_name"},
        ),
    ):
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
    mocker.patch("documentai_api.app_extraction_rules.get_valid_fields", return_value={"ssn"})

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


# ==============================================================================
# ExtractionRuleRequest validators
# ==============================================================================


@pytest.fixture
def mock_valid_fields(mocker):
    """Patch get_valid_fields to return a known set of fields for 'w2'."""
    return mocker.patch(
        "documentai_api.app_extraction_rules.get_valid_fields",
        return_value={"ssn", "wages", "employer_name"},
    )


def test_validator_deduplicates_required_fields(mock_valid_fields):
    from documentai_api.app_extraction_rules import ExtractionRuleRequest

    req = ExtractionRuleRequest(
        document_type="w2", required_fields=["ssn", "ssn", "wages"], optional_fields=[]
    )

    assert req.required_fields == ["ssn", "wages"]


def test_validator_deduplicates_case_insensitive_within_list(mock_valid_fields):
    from documentai_api.app_extraction_rules import ExtractionRuleRequest

    req = ExtractionRuleRequest(
        document_type="w2", required_fields=["SSN", "ssn", "wages"], optional_fields=[]
    )

    assert req.required_fields == ["ssn", "wages"]


def test_validator_deduplicates_optional_fields(mock_valid_fields):
    from documentai_api.app_extraction_rules import ExtractionRuleRequest

    req = ExtractionRuleRequest(
        document_type="w2",
        required_fields=["ssn"],
        optional_fields=["employer_name", "employer_name"],
    )
    assert req.optional_fields == ["employer_name"]


def test_validator_rejects_unknown_document_type(mocker):
    mocker.patch(
        "documentai_api.app_extraction_rules.get_valid_fields",
        return_value=None,
    )
    from pydantic import ValidationError

    from documentai_api.app_extraction_rules import ExtractionRuleRequest

    with pytest.raises(ValidationError, match="Unknown document type"):
        ExtractionRuleRequest(document_type="unknown", required_fields=["ssn"], optional_fields=[])


def test_validator_rejects_invalid_field_names(mock_valid_fields):
    from pydantic import ValidationError

    from documentai_api.app_extraction_rules import ExtractionRuleRequest

    with pytest.raises(ValidationError, match="Unknown fields"):
        ExtractionRuleRequest(
            document_type="w2", required_fields=["not_a_field"], optional_fields=[]
        )


def test_validator_rejects_overlapping_fields(mock_valid_fields):
    from pydantic import ValidationError

    from documentai_api.app_extraction_rules import ExtractionRuleRequest

    with pytest.raises(ValidationError, match="both required and optional"):
        ExtractionRuleRequest(document_type="w2", required_fields=["ssn"], optional_fields=["ssn"])


def test_put_deduplicates_fields():
    """PUT silently deduplicates fields and returns 200."""
    rule = {
        "tenantId": "test-tenant",
        "documentType": "w2",
        "requiredFields": ["ssn"],
        "optionalFields": ["wages"],
        "createdAt": "2026-01-01",
        "updatedAt": "2026-01-01",
    }

    with (
        patch("documentai_api.utils.extraction_rules.upsert_rule", return_value=rule),
        patch(
            "documentai_api.app_extraction_rules.get_valid_fields",
            return_value={"ssn", "wages"},
        ),
    ):
        response = client.put(
            "/v1/config/extraction-rules",
            json={
                "document_type": "w2",
                "required_fields": ["ssn", "ssn"],
                "optional_fields": ["wages", "wages"],
            },
        )

    assert response.status_code == 200


def test_put_unknown_document_type_returns_422():
    with patch("documentai_api.app_extraction_rules.get_valid_fields", return_value=None):
        response = client.put(
            "/v1/config/extraction-rules",
            json={"document_type": "unknown", "required_fields": ["ssn"], "optional_fields": []},
        )

    assert response.status_code == 422


def test_put_invalid_field_names_returns_422():
    with patch("documentai_api.app_extraction_rules.get_valid_fields", return_value={"ssn"}):
        response = client.put(
            "/v1/config/extraction-rules",
            json={"document_type": "w2", "required_fields": ["not_a_field"], "optional_fields": []},
        )

    assert response.status_code == 422


def test_put_overlapping_fields_returns_422():
    with patch("documentai_api.app_extraction_rules.get_valid_fields", return_value={"ssn"}):
        response = client.put(
            "/v1/config/extraction-rules",
            json={"document_type": "w2", "required_fields": ["ssn"], "optional_fields": ["ssn"]},
        )

    assert response.status_code == 422


def test_put_non_string_document_type_returns_422():
    """Non-string document_type must return 422, not 500."""
    response = client.put(
        "/v1/config/extraction-rules",
        json={"document_type": 123, "required_fields": ["ssn"], "optional_fields": []},
    )

    assert response.status_code == 422


def test_put_string_required_fields_returns_422():
    """A string value for required_fields must be rejected, not exploded into characters."""
    response = client.put(
        "/v1/config/extraction-rules",
        json={"document_type": "w2", "required_fields": "ssn", "optional_fields": []},
    )

    assert response.status_code == 422


def test_put_case_insensitive_overlap_returns_422():
    """SSN in required and ssn in optional should be caught as overlap."""
    with patch("documentai_api.app_extraction_rules.get_valid_fields", return_value={"ssn"}):
        response = client.put(
            "/v1/config/extraction-rules",
            json={"document_type": "w2", "required_fields": ["SSN"], "optional_fields": ["ssn"]},
        )

    assert response.status_code == 422


# ==============================================================================
# Tenant-scope security
# ==============================================================================


def test_put_super_admin_missing_tenant_id_returns_400():
    """Super-admin (tenant_id=__admin__) must provide tenant_id in body."""
    from documentai_api.app import app
    from documentai_api.utils.auth import UserContext, get_user_context_with_fallback

    admin_context = UserContext(tenant_id="__admin__", api_key_name="admin-user")
    app.dependency_overrides[get_user_context_with_fallback] = lambda: admin_context
    try:
        with patch("documentai_api.app_extraction_rules.get_valid_fields", return_value={"ssn"}):
            response = client.put(
                "/v1/config/extraction-rules",
                json={"document_type": "W2", "required_fields": ["ssn"], "optional_fields": []},
            )
        assert response.status_code == 400
        assert "tenant_id is required" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_delete_super_admin_missing_tenant_id_returns_400():
    """Super-admin DELETE without tenant_id query param returns 400."""
    from documentai_api.app import app
    from documentai_api.utils.auth import UserContext, get_user_context_with_fallback

    admin_context = UserContext(tenant_id="__admin__", api_key_name="admin-user")
    app.dependency_overrides[get_user_context_with_fallback] = lambda: admin_context
    try:
        response = client.delete("/v1/config/extraction-rules?document_type=W2")
        assert response.status_code == 400
        assert "tenant_id is required" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_put_tenant_admin_body_tenant_id_ignored(mocker):
    """Tenant-admin's auth tenant is used regardless of body tenant_id."""
    mock_upsert = mocker.patch("documentai_api.utils.extraction_rules.upsert_rule")
    mock_upsert.return_value = {
        "tenantId": "test-tenant",
        "documentType": "W2",
        "requiredFields": ["ssn"],
        "optionalFields": [],
        "createdAt": "2026-01-01",
        "updatedAt": "2026-01-01",
    }
    mocker.patch("documentai_api.app_extraction_rules.get_valid_fields", return_value={"ssn"})

    # Body says "other-tenant" but auth is "test-tenant" - auth wins
    response = client.put(
        "/v1/config/extraction-rules",
        json={
            "document_type": "W2",
            "required_fields": ["ssn"],
            "optional_fields": [],
            "tenant_id": "other-tenant",
        },
    )

    assert response.status_code == 200
    assert mock_upsert.call_args[0][0] == "test-tenant"


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

        # GET - tenant A should not see tenant B's rule
        response = tenant_a_client.get("/v1/config/extraction-rules?document_type=W2")
        assert response.status_code == 404

        # DELETE - tenant A cannot delete tenant B's rule
        response = tenant_a_client.delete("/v1/config/extraction-rules?document_type=W2")
        assert response.status_code == 404

        # PUT - tenant A creates their own rule
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
