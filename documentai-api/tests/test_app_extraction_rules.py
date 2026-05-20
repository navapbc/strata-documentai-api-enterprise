import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from documentai_api.app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _disable_auth(disable_auth):
    pass


MOCK_RULE = {
    "tenantId": "t1",
    "documentType": "W2",
    "requiredFields": ["ssn", "wages"],
    "optionalFields": ["employer_name"],
    "createdAt": "2026-01-01T00:00:00+00:00",
    "updatedAt": "2026-01-01T00:00:00+00:00",
}


def test_get_extraction_rules():
    with patch("documentai_api.utils.extraction_rules.get_rules", return_value=[MOCK_RULE]):
        response = client.get("/v1/config/extraction-rules?tenant_id=t1")

    assert response.status_code == 200
    rules = response.json()["rules"]
    assert len(rules) == 1
    assert rules[0]["tenantId"] == "t1"
    assert rules[0]["documentType"] == "W2"
    assert rules[0]["requiredFields"] == ["ssn", "wages"]
    assert rules[0]["optionalFields"] == ["employer_name"]


def test_get_extraction_rules_by_document_type():
    with patch("documentai_api.utils.extraction_rules.get_rules", return_value=[MOCK_RULE]):
        response = client.get("/v1/config/extraction-rules?tenant_id=t1&document_type=W2")

    assert response.status_code == 200
    assert len(response.json()["rules"]) == 1


def test_get_extraction_rules_not_found():
    with patch("documentai_api.utils.extraction_rules.get_rules", return_value=[]):
        response = client.get("/v1/config/extraction-rules?tenant_id=t1")

    assert response.status_code == 404


def test_put_extraction_rule():
    rule = {
        "tenantId": "t1",
        "documentType": "W2",
        "requiredFields": ["ssn", "wages"],
        "optionalFields": ["employer_name"],
        "createdAt": "2026-01-01",
        "updatedAt": "2026-01-01",
    }
    with patch("documentai_api.utils.extraction_rules.upsert_rule", return_value=rule):
        response = client.put(
            "/v1/config/extraction-rules",
            data={
                "tenant_id": "t1",
                "document_type": "W2",
                "required_fields": json.dumps(["ssn", "wages"]),
                "optional_fields": json.dumps(["employer_name"]),
            },
        )

    assert response.status_code == 200
    assert response.json()["requiredFields"] == ["ssn", "wages"]
    assert response.json()["optionalFields"] == ["employer_name"]


def test_put_extraction_rule_invalid_required_fields():
    response = client.put(
        "/v1/config/extraction-rules",
        data={
            "tenant_id": "t1",
            "document_type": "W2",
            "required_fields": "not json",
            "optional_fields": "[]",
        },
    )
    assert response.status_code == 400
    assert "required_fields" in response.json()["detail"]


def test_put_extraction_rule_invalid_optional_fields():
    response = client.put(
        "/v1/config/extraction-rules",
        data={
            "tenant_id": "t1",
            "document_type": "W2",
            "required_fields": "[]",
            "optional_fields": "not json",
        },
    )
    assert response.status_code == 400
    assert "optional_fields" in response.json()["detail"]


def test_delete_extraction_rule():
    with patch("documentai_api.utils.extraction_rules.delete_rule") as mock_delete:
        response = client.delete("/v1/config/extraction-rules?tenant_id=t1&document_type=W2")

    assert response.status_code == 200
    mock_delete.assert_called_once_with("t1", "W2")
