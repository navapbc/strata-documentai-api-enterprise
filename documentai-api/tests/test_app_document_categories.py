"""Tests for document categories CRUD with tenant scoping."""

import pytest
from fastapi.testclient import TestClient

from documentai_api.app import app
from documentai_api.utils.jwt_auth import verify_jwt

CATEGORIES_URL = "/v1/admin/document-categories"

TENANT_ID = "test-tenant"
OTHER_TENANT_ID = "other-tenant"
CATEGORY_NAME = "income"
NEW_CATEGORY = {
    "category_name": CATEGORY_NAME,
    "display_name": "Income Documents",
    "description": "W2s, 1099s, etc.",
}

SUPER_ADMIN = "super-admin"
TENANT_ADMIN = "tenant-admin"


# --- Helpers ---


def _make_claims(*, groups: list[str] | None = None, tenant_id: str | None = None):
    claims = {
        "sub": "test-user",
        "email": "test@example.com",
        "token_use": "access",
        "cognito:groups": groups or [],
    }
    if tenant_id:
        claims["custom:tenant_id"] = tenant_id
    return claims


def _override_jwt(claims: dict):
    app.dependency_overrides[verify_jwt] = lambda: claims


def _clear_overrides():
    app.dependency_overrides.pop(verify_jwt, None)


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    _clear_overrides()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def document_categories_table(aws_credentials, monkeypatch):
    import boto3
    from moto import mock_aws

    from documentai_api.config.env import EnvVars

    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="document-categories",
            KeySchema=[
                {"AttributeName": "tenantId", "KeyType": "HASH"},
                {"AttributeName": "categoryName", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "tenantId", "AttributeType": "S"},
                {"AttributeName": "categoryName", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        monkeypatch.setenv(EnvVars.DOCUMENT_CATEGORIES_TABLE_NAME, table.name)
        yield table


@pytest.fixture
def seed_category(client, document_categories_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(CATEGORIES_URL, params={"tenant_id": TENANT_ID}, json=NEW_CATEGORY)
    assert response.status_code == 201


# ==============================================================================
# Auth gates
# ==============================================================================


def test_categories_unauthenticated_returns_401(client):
    response = client.get(CATEGORIES_URL)
    assert response.status_code == 401


def test_categories_pending_user_returns_403(client):
    _override_jwt(_make_claims(groups=[]))
    response = client.get(CATEGORIES_URL)
    assert response.status_code == 403


# ==============================================================================
# Super-admin CRUD
# ==============================================================================


def test_categories_super_admin_list_empty(client, document_categories_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.get(CATEGORIES_URL, params={"tenant_id": TENANT_ID})
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_categories_super_admin_create_returns_201(client, document_categories_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(CATEGORIES_URL, params={"tenant_id": TENANT_ID}, json=NEW_CATEGORY)
    assert response.status_code == 201
    data = response.json()
    assert data["categoryName"] == CATEGORY_NAME
    assert data["displayName"] == "Income Documents"
    assert data["tenantId"] == TENANT_ID


def test_categories_super_admin_create_duplicate_returns_409(client, seed_category):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(CATEGORIES_URL, params={"tenant_id": TENANT_ID}, json=NEW_CATEGORY)
    assert response.status_code == 409


def test_categories_super_admin_get_returns_200(client, seed_category):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.get(f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID})
    assert response.status_code == 200
    assert response.json()["categoryName"] == CATEGORY_NAME


def test_categories_super_admin_get_not_found_returns_404(client, document_categories_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.get(f"{CATEGORIES_URL}/missing", params={"tenant_id": TENANT_ID})
    assert response.status_code == 404


def test_categories_super_admin_update_returns_200(client, seed_category):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.patch(
        f"{CATEGORIES_URL}/{CATEGORY_NAME}",
        params={"tenant_id": TENANT_ID},
        json={"display_name": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["displayName"] == "Updated Name"


def test_categories_super_admin_delete_returns_204(client, seed_category):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.delete(f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID})
    assert response.status_code == 204


def test_categories_super_admin_delete_not_found_returns_404(client, document_categories_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.delete(f"{CATEGORIES_URL}/missing", params={"tenant_id": TENANT_ID})
    assert response.status_code == 404


def test_categories_super_admin_lists_all_without_tenant_id(client, document_categories_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.get(CATEGORIES_URL)
    assert response.status_code == 200


# ==============================================================================
# Tenant-admin scoping
# ==============================================================================


def test_categories_tenant_admin_list_own(client, seed_category):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.get(CATEGORIES_URL)
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_categories_tenant_admin_create_own(client, document_categories_table):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.post(CATEGORIES_URL, json=NEW_CATEGORY)
    assert response.status_code == 201
    assert response.json()["tenantId"] == TENANT_ID


def test_categories_tenant_admin_get_own(client, seed_category):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.get(f"{CATEGORIES_URL}/{CATEGORY_NAME}")
    assert response.status_code == 200


def test_categories_tenant_admin_update_own(client, seed_category):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.patch(f"{CATEGORIES_URL}/{CATEGORY_NAME}", json={"display_name": "New Name"})
    assert response.status_code == 200


def test_categories_tenant_admin_delete_own(client, seed_category):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.delete(f"{CATEGORIES_URL}/{CATEGORY_NAME}")
    assert response.status_code == 204


def test_categories_tenant_admin_cannot_access_other_tenant(client, document_categories_table):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.get(CATEGORIES_URL, params={"tenant_id": OTHER_TENANT_ID})
    assert response.status_code == 403


def test_categories_tenant_admin_no_tenant_in_jwt_returns_403(client, document_categories_table):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN]))
    response = client.get(CATEGORIES_URL)
    assert response.status_code == 403


# ==============================================================================
# Edge cases
# ==============================================================================


def test_categories_create_missing_fields_returns_422(client, document_categories_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(CATEGORIES_URL, params={"tenant_id": TENANT_ID}, json={})
    assert response.status_code == 422


def test_categories_create_invalid_name_returns_422(client, document_categories_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(
        CATEGORIES_URL,
        params={"tenant_id": TENANT_ID},
        json={"category_name": "INVALID!!", "display_name": "X"},
    )
    assert response.status_code == 422


def test_categories_update_empty_body_returns_400(client, seed_category):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.patch(
        f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID}, json={}
    )
    assert response.status_code == 400


# ==============================================================================
# Soft-delete semantics
# ==============================================================================


def test_categories_after_delete_hidden_from_active_list(client, seed_category):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.delete(f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID})
    response = client.get(CATEGORIES_URL, params={"tenant_id": TENANT_ID})
    assert response.json()["count"] == 0


def test_categories_after_delete_visible_with_active_only_false(client, seed_category):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.delete(f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID})
    response = client.get(CATEGORIES_URL, params={"tenant_id": TENANT_ID, "active_only": "false"})
    assert response.json()["count"] == 1
    assert response.json()["categories"][0]["isActive"] is False


def test_categories_delete_already_inactive_is_idempotent(client, seed_category):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.delete(f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID})
    response = client.delete(f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID})
    assert response.status_code == 204


def test_categories_reactivate_via_patch(client, seed_category):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.delete(f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID})
    response = client.patch(
        f"{CATEGORIES_URL}/{CATEGORY_NAME}",
        params={"tenant_id": TENANT_ID},
        json={"is_active": True},
    )
    assert response.status_code == 200
    assert response.json()["isActive"] is True


# ==============================================================================
# Cross-tenant isolation
# ==============================================================================


def test_categories_tenant_admin_cannot_see_other_tenants_data(client, document_categories_table):
    # Seed category for tenant A as super-admin
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(CATEGORIES_URL, params={"tenant_id": TENANT_ID}, json=NEW_CATEGORY)

    # Tenant B admin lists — should see nothing
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=OTHER_TENANT_ID))
    response = client.get(CATEGORIES_URL)
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_categories_super_admin_sees_disjoint_sets(client, document_categories_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    client.post(CATEGORIES_URL, params={"tenant_id": TENANT_ID}, json=NEW_CATEGORY)
    client.post(
        CATEGORIES_URL,
        params={"tenant_id": OTHER_TENANT_ID},
        json={"category_name": "expenses", "display_name": "Expenses"},
    )

    resp_a = client.get(CATEGORIES_URL, params={"tenant_id": TENANT_ID})
    resp_b = client.get(CATEGORIES_URL, params={"tenant_id": OTHER_TENANT_ID})
    assert resp_a.json()["count"] == 1
    assert resp_a.json()["categories"][0]["categoryName"] == CATEGORY_NAME
    assert resp_b.json()["count"] == 1
    assert resp_b.json()["categories"][0]["categoryName"] == "expenses"


# ==============================================================================
# Update edge cases
# ==============================================================================


def test_categories_update_not_found_returns_404(client, document_categories_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.patch(
        f"{CATEGORIES_URL}/missing",
        params={"tenant_id": TENANT_ID},
        json={"display_name": "X"},
    )
    assert response.status_code == 404


def test_categories_tenant_admin_update_empty_body_returns_400(client, seed_category):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.patch(f"{CATEGORIES_URL}/{CATEGORY_NAME}", json={})
    assert response.status_code == 400


def test_categories_deactivate_via_patch(client, seed_category):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.patch(
        f"{CATEGORIES_URL}/{CATEGORY_NAME}",
        params={"tenant_id": TENANT_ID},
        json={"is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["isActive"] is False


# ==============================================================================
# Validation boundaries
# ==============================================================================


def test_categories_create_empty_name_returns_422(client, document_categories_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(
        CATEGORIES_URL,
        params={"tenant_id": TENANT_ID},
        json={"category_name": "", "display_name": "X"},
    )
    assert response.status_code == 422


def test_categories_create_name_too_long_returns_422(client, document_categories_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(
        CATEGORIES_URL,
        params={"tenant_id": TENANT_ID},
        json={"category_name": "a" * 65, "display_name": "X"},
    )
    assert response.status_code == 422


def test_categories_create_uppercase_name_returns_422(client, document_categories_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(
        CATEGORIES_URL,
        params={"tenant_id": TENANT_ID},
        json={"category_name": "UPPERCASE", "display_name": "X"},
    )
    assert response.status_code == 422


def test_categories_create_display_name_too_long_returns_422(client, document_categories_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(
        CATEGORIES_URL,
        params={"tenant_id": TENANT_ID},
        json={"category_name": "valid", "display_name": "x" * 129},
    )
    assert response.status_code == 422


def test_categories_create_without_description_defaults_empty(client, document_categories_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(
        CATEGORIES_URL,
        params={"tenant_id": TENANT_ID},
        json={"category_name": "no-desc", "display_name": "No Description"},
    )
    assert response.status_code == 201
    assert response.json()["description"] == ""


def test_categories_create_round_trips_all_fields(client, document_categories_table):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.post(CATEGORIES_URL, params={"tenant_id": TENANT_ID}, json=NEW_CATEGORY)
    assert response.status_code == 201
    data = response.json()
    assert data["categoryName"] == CATEGORY_NAME
    assert data["displayName"] == "Income Documents"
    assert data["description"] == "W2s, 1099s, etc."
    assert data["isActive"] is True
    assert data["tenantId"] == TENANT_ID


def test_categories_tenant_admin_create_duplicate_returns_409(client, seed_category):
    _override_jwt(_make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = client.post(CATEGORIES_URL, json=NEW_CATEGORY)
    assert response.status_code == 409


# ==============================================================================
# Super-admin requires tenant_id on all methods
# ==============================================================================


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", CATEGORIES_URL),
        ("GET", f"{CATEGORIES_URL}/{CATEGORY_NAME}"),
        ("PATCH", f"{CATEGORIES_URL}/{CATEGORY_NAME}"),
        ("DELETE", f"{CATEGORIES_URL}/{CATEGORY_NAME}"),
    ],
)
def test_categories_super_admin_requires_tenant_id_all_methods(
    client, document_categories_table, method, path
):
    _override_jwt(_make_claims(groups=[SUPER_ADMIN]))
    response = client.request(
        method, path, json=NEW_CATEGORY if method in ("POST", "PATCH") else None
    )
    assert response.status_code == 400
