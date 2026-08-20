"""Tests for blueprint management endpoints."""

import pytest
from fastapi.testclient import TestClient

from documentai_api.app import app
from documentai_api.config.constants import BlueprintStatus
from documentai_api.utils import blueprints as blueprints_util
from tests.helpers.fixtures.claims import (
    clear_jwt_override,
    make_claims,
    override_jwt,
)

BLUEPRINTS_URL = "/v1/blueprints"
TENANT_ID = "test-tenant"
OTHER_TENANT_ID = "other-tenant"

SUPER_ADMIN = "super-admin"
TENANT_ADMIN = "tenant-admin"

NEW_BLUEPRINT = {
    "description": "Extracts employer name and EIN from a W-2",
    "document_type": "w2",
    "fields": [{"name": "employer_name", "type": "string"}],
}


# =============================================================================
# Helpers
# =============================================================================


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    clear_jwt_override()


@pytest.fixture
def client(blueprints_table, tenants_table):
    return TestClient(app)


@pytest.fixture
def tenant_record(tenants_table):
    from documentai_api.utils.tenants import create_tenant

    return create_tenant(TENANT_ID, display_name=TENANT_ID)


@pytest.fixture
def mock_bda(mocker):
    mock = mocker.MagicMock()
    mocker.patch(
        "documentai_api.utils.blueprints.AWSClientFactory.get_bda_client",
        return_value=mock,
    )
    mock.create_data_automation_project.return_value = {
        "projectArn": "arn:aws:bedrock:us-east-1:123:data-automation-project/proj"
    }
    mock.create_blueprint.return_value = {
        "blueprint": {"blueprintArn": "arn:aws:bedrock:us-east-1:123:blueprint/bp"}
    }
    return mock


@pytest.fixture
def seed_blueprint(client, tenant_record):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = client.post(BLUEPRINTS_URL, params={"tenant_id": TENANT_ID}, json=NEW_BLUEPRINT)
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def seed_published_blueprint(client, tenant_record, mock_bda):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = client.post(BLUEPRINTS_URL, params={"tenant_id": TENANT_ID}, json=NEW_BLUEPRINT)
    bp_id = response.json()["blueprintId"]
    pub = client.post(f"{BLUEPRINTS_URL}/{bp_id}/publish", params={"tenant_id": TENANT_ID})
    assert pub.status_code == 200
    return response.json()


# =============================================================================
# Auth gates
# =============================================================================


def test_blueprints_unauthenticated_returns_401(client):
    response = client.get(BLUEPRINTS_URL)
    assert response.status_code == 401


def test_blueprints_pending_user_returns_403(client):
    override_jwt(make_claims(groups=[]))
    response = client.get(BLUEPRINTS_URL)
    assert response.status_code == 403


# =============================================================================
# Create
# =============================================================================


def test_create_blueprint_returns_draft(client, tenant_record):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = client.post(BLUEPRINTS_URL, params={"tenant_id": TENANT_ID}, json=NEW_BLUEPRINT)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == BlueprintStatus.DRAFT
    assert data["tenantId"] == TENANT_ID
    assert data["documentType"] == "w2"
    assert data["description"] == NEW_BLUEPRINT["description"]


def test_create_blueprint_missing_fields_returns_422(client, tenant_record):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = client.post(BLUEPRINTS_URL, params={"tenant_id": TENANT_ID}, json={})
    assert response.status_code == 422


def test_create_blueprint_no_tenant_super_admin_returns_400(client):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = client.post(BLUEPRINTS_URL, json=NEW_BLUEPRINT)
    assert response.status_code == 400


# =============================================================================
# List / Get
# =============================================================================


def test_list_blueprints_empty(client, tenant_record):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = client.get(BLUEPRINTS_URL, params={"tenant_id": TENANT_ID})
    assert response.status_code == 200
    assert response.json()["blueprints"] == []


def test_list_blueprints_returns_created(client, seed_blueprint):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = client.get(BLUEPRINTS_URL, params={"tenant_id": TENANT_ID})
    assert response.status_code == 200
    assert len(response.json()["blueprints"]) == 1


def test_get_blueprint_returns_record(client, seed_blueprint):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    bp_id = seed_blueprint["blueprintId"]
    response = client.get(f"{BLUEPRINTS_URL}/{bp_id}", params={"tenant_id": TENANT_ID})
    assert response.status_code == 200
    assert response.json()["blueprintId"] == bp_id


def test_get_blueprint_not_found_returns_404(client, tenant_record):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = client.get(f"{BLUEPRINTS_URL}/nonexistent", params={"tenant_id": TENANT_ID})
    assert response.status_code == 404


# =============================================================================
# Update
# =============================================================================


def test_update_blueprint_description(client, seed_blueprint):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    bp_id = seed_blueprint["blueprintId"]
    response = client.put(
        f"{BLUEPRINTS_URL}/{bp_id}",
        params={"tenant_id": TENANT_ID},
        json={"description": "Updated description"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Updated description"


def test_update_blueprint_empty_body_returns_400(client, seed_blueprint):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    bp_id = seed_blueprint["blueprintId"]
    response = client.put(f"{BLUEPRINTS_URL}/{bp_id}", params={"tenant_id": TENANT_ID}, json={})
    assert response.status_code == 400


def test_update_live_blueprint_returns_400(client, seed_published_blueprint):
    bp_id = seed_published_blueprint["blueprintId"]
    blueprints_util._blueprints_table.update(TENANT_ID, bp_id, blueprintStatus=BlueprintStatus.LIVE)
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = client.put(
        f"{BLUEPRINTS_URL}/{bp_id}",
        params={"tenant_id": TENANT_ID},
        json={"description": "New desc"},
    )
    assert response.status_code == 400
    assert "offline" in response.json()["detail"]


# =============================================================================
# Delete
# =============================================================================


def test_delete_blueprint_returns_200(client, seed_blueprint):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    bp_id = seed_blueprint["blueprintId"]
    response = client.delete(f"{BLUEPRINTS_URL}/{bp_id}", params={"tenant_id": TENANT_ID})
    assert response.status_code == 200


def test_delete_blueprint_not_found_returns_404(client, tenant_record):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = client.delete(f"{BLUEPRINTS_URL}/nonexistent", params={"tenant_id": TENANT_ID})
    assert response.status_code == 404


def test_delete_live_blueprint_returns_400(client, seed_published_blueprint):
    bp_id = seed_published_blueprint["blueprintId"]
    blueprints_util._blueprints_table.update(TENANT_ID, bp_id, blueprintStatus=BlueprintStatus.LIVE)
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = client.delete(f"{BLUEPRINTS_URL}/{bp_id}", params={"tenant_id": TENANT_ID})
    assert response.status_code == 400
    assert "offline" in response.json()["detail"]


# =============================================================================
# Publish
# =============================================================================


def test_publish_blueprint_returns_arns(client, seed_blueprint, mock_bda, tenant_record):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    bp_id = seed_blueprint["blueprintId"]
    response = client.post(f"{BLUEPRINTS_URL}/{bp_id}/publish", params={"tenant_id": TENANT_ID})
    assert response.status_code == 200
    data = response.json()
    assert data["blueprintArn"].startswith("arn:aws:bedrock:")
    assert data["projectArn"].startswith("arn:aws:bedrock:")


def test_publish_nonexistent_blueprint_returns_400(client, tenant_record, mock_bda):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = client.post(f"{BLUEPRINTS_URL}/nonexistent/publish", params={"tenant_id": TENANT_ID})
    assert response.status_code == 400


# =============================================================================
# Live toggle
# =============================================================================


def test_enable_blueprint_returns_200(client, seed_published_blueprint):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    bp_id = seed_published_blueprint["blueprintId"]
    response = client.post(f"{BLUEPRINTS_URL}/{bp_id}/live", params={"tenant_id": TENANT_ID})
    assert response.status_code == 200
    assert "live" in response.json()["message"]


def test_enable_draft_blueprint_returns_400(client, seed_blueprint):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    bp_id = seed_blueprint["blueprintId"]
    response = client.post(f"{BLUEPRINTS_URL}/{bp_id}/live", params={"tenant_id": TENANT_ID})
    assert response.status_code == 400


def test_disable_blueprint_returns_200(client, seed_published_blueprint):
    bp_id = seed_published_blueprint["blueprintId"]
    blueprints_util._blueprints_table.update(TENANT_ID, bp_id, blueprintStatus=BlueprintStatus.LIVE)
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = client.delete(f"{BLUEPRINTS_URL}/{bp_id}/live", params={"tenant_id": TENANT_ID})
    assert response.status_code == 200
    assert "offline" in response.json()["message"]


# =============================================================================
# Tenant scoping
# =============================================================================


def test_tenant_admin_can_list_own_blueprints(client, seed_blueprint):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.get(BLUEPRINTS_URL)
    assert response.status_code == 200
    assert len(response.json()["blueprints"]) == 1


def test_tenant_admin_cannot_access_other_tenant(client, tenant_record):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.get(BLUEPRINTS_URL, params={"tenant_id": OTHER_TENANT_ID})
    assert response.status_code == 403


def test_tenant_admin_no_tenant_in_jwt_returns_403(client, tenant_record):
    override_jwt(make_claims(groups=[TENANT_ADMIN]))
    response = client.get(BLUEPRINTS_URL)
    assert response.status_code == 403


def test_blueprints_are_isolated_between_tenants(client, blueprints_table, tenants_table):
    from documentai_api.utils.tenants import create_tenant

    create_tenant(TENANT_ID, display_name=TENANT_ID)
    create_tenant(OTHER_TENANT_ID, display_name=OTHER_TENANT_ID)

    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    client.post(BLUEPRINTS_URL, params={"tenant_id": TENANT_ID}, json=NEW_BLUEPRINT)
    client.post(
        BLUEPRINTS_URL,
        params={"tenant_id": OTHER_TENANT_ID},
        json={**NEW_BLUEPRINT, "document_type": "1099"},
    )

    resp_a = client.get(BLUEPRINTS_URL, params={"tenant_id": TENANT_ID})
    resp_b = client.get(BLUEPRINTS_URL, params={"tenant_id": OTHER_TENANT_ID})
    assert len(resp_a.json()["blueprints"]) == 1
    assert resp_a.json()["blueprints"][0]["documentType"] == "w2"
    assert len(resp_b.json()["blueprints"]) == 1
    assert resp_b.json()["blueprints"][0]["documentType"] == "1099"


# =============================================================================
# Serialization - _to_blueprint_item round-trip
# =============================================================================


def test_blueprint_fields_round_trip(client, tenant_record):
    """BlueprintField shape must survive create -> list without ValidationError."""
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    payload = {
        "description": "Test",
        "document_type": "test-doc",
        "fields": [
            {"name": "field_a", "type": "string"},
            {
                "name": "field_b",
                "type": "string",
                "inferenceType": "explicit",
                "instruction": "hint",
            },
        ],
    }
    create_resp = client.post(BLUEPRINTS_URL, params={"tenant_id": TENANT_ID}, json=payload)
    assert create_resp.status_code == 200

    bp_id = create_resp.json()["blueprintId"]
    get_resp = client.get(f"{BLUEPRINTS_URL}/{bp_id}", params={"tenant_id": TENANT_ID})
    assert get_resp.status_code == 200
    fields = get_resp.json()["fields"]
    assert any(f["name"] == "field_b" and f.get("inferenceType") == "explicit" for f in fields)
