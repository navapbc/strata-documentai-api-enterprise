"""Tests for document categories CRUD with tenant scoping."""

import pytest

from tests.helpers.fixtures.claims import SUPER_ADMIN, TENANT_ADMIN, make_claims, override_jwt

CATEGORIES_URL = "/v1/admin/document-categories"

TENANT_ID = "test-tenant"
OTHER_TENANT_ID = "other-tenant"
CATEGORY_NAME = "income"
NEW_CATEGORY = {
    "category_name": CATEGORY_NAME,
    "display_name": "Income Documents",
    "description": "W2s, 1099s, etc.",
}


# --- Helpers ---


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
def seed_category(api_client, document_categories_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.post(CATEGORIES_URL, params={"tenant_id": TENANT_ID}, json=NEW_CATEGORY)
    assert response.status_code == 201


# ==============================================================================
# Auth gates
# ==============================================================================


def test_categories_unauthenticated_returns_401(api_client):
    response = api_client.get(CATEGORIES_URL)
    assert response.status_code == 401


def test_categories_pending_user_returns_403(api_client):
    override_jwt(make_claims(groups=[]))
    response = api_client.get(CATEGORIES_URL)
    assert response.status_code == 403


# ==============================================================================
# Super-admin CRUD
# ==============================================================================


def test_categories_super_admin_list_empty(api_client, document_categories_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.get(CATEGORIES_URL, params={"tenant_id": TENANT_ID})
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_categories_super_admin_create_returns_201(api_client, document_categories_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.post(CATEGORIES_URL, params={"tenant_id": TENANT_ID}, json=NEW_CATEGORY)
    assert response.status_code == 201
    data = response.json()
    assert data["categoryName"] == CATEGORY_NAME
    assert data["displayName"] == "Income Documents"
    assert data["tenantId"] == TENANT_ID


def test_categories_super_admin_create_duplicate_returns_409(api_client, seed_category):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.post(CATEGORIES_URL, params={"tenant_id": TENANT_ID}, json=NEW_CATEGORY)
    assert response.status_code == 409


def test_categories_super_admin_get_returns_200(api_client, seed_category):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.get(f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID})
    assert response.status_code == 200
    assert response.json()["categoryName"] == CATEGORY_NAME


def test_categories_super_admin_get_not_found_returns_404(api_client, document_categories_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.get(f"{CATEGORIES_URL}/missing", params={"tenant_id": TENANT_ID})
    assert response.status_code == 404


def test_categories_super_admin_update_returns_200(api_client, seed_category):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.patch(
        f"{CATEGORIES_URL}/{CATEGORY_NAME}",
        params={"tenant_id": TENANT_ID},
        json={"display_name": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["displayName"] == "Updated Name"


def test_categories_super_admin_delete_returns_204(api_client, seed_category):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.delete(
        f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID}
    )
    assert response.status_code == 204


def test_categories_super_admin_delete_not_found_returns_404(api_client, document_categories_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.delete(f"{CATEGORIES_URL}/missing", params={"tenant_id": TENANT_ID})
    assert response.status_code == 404


def test_categories_super_admin_lists_all_without_tenant_id(api_client, document_categories_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.get(CATEGORIES_URL)
    assert response.status_code == 200


# ==============================================================================
# Tenant-admin scoping
# ==============================================================================


def test_categories_tenant_admin_list_own(api_client, seed_category):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.get(CATEGORIES_URL)
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_categories_tenant_admin_create_own(api_client, document_categories_table):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.post(CATEGORIES_URL, json=NEW_CATEGORY)
    assert response.status_code == 201
    assert response.json()["tenantId"] == TENANT_ID


def test_categories_tenant_admin_get_own(api_client, seed_category):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.get(f"{CATEGORIES_URL}/{CATEGORY_NAME}")
    assert response.status_code == 200


def test_categories_tenant_admin_update_own(api_client, seed_category):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.patch(
        f"{CATEGORIES_URL}/{CATEGORY_NAME}", json={"display_name": "New Name"}
    )
    assert response.status_code == 200


def test_categories_tenant_admin_delete_own(api_client, seed_category):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.delete(f"{CATEGORIES_URL}/{CATEGORY_NAME}")
    assert response.status_code == 204


def test_categories_tenant_admin_cannot_access_other_tenant(api_client, document_categories_table):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.get(CATEGORIES_URL, params={"tenant_id": OTHER_TENANT_ID})
    assert response.status_code == 403


def test_categories_tenant_admin_no_tenant_in_jwt_returns_403(
    api_client, document_categories_table
):
    override_jwt(make_claims(groups=[TENANT_ADMIN]))
    response = api_client.get(CATEGORIES_URL)
    assert response.status_code == 403


# ==============================================================================
# Edge cases
# ==============================================================================


def test_categories_create_missing_fields_returns_422(api_client, document_categories_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.post(CATEGORIES_URL, params={"tenant_id": TENANT_ID}, json={})
    assert response.status_code == 422


def test_categories_create_invalid_name_returns_422(api_client, document_categories_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.post(
        CATEGORIES_URL,
        params={"tenant_id": TENANT_ID},
        json={"category_name": "INVALID!!", "display_name": "X"},
    )
    assert response.status_code == 422


def test_categories_update_empty_body_returns_400(api_client, seed_category):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.patch(
        f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID}, json={}
    )
    assert response.status_code == 400


# ==============================================================================
# Soft-delete semantics
# ==============================================================================


def test_categories_after_delete_hidden_from_active_list(api_client, seed_category):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    api_client.delete(f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID})
    response = api_client.get(CATEGORIES_URL, params={"tenant_id": TENANT_ID})
    assert response.json()["count"] == 0


def test_categories_after_delete_visible_with_active_only_false(api_client, seed_category):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    api_client.delete(f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID})
    response = api_client.get(
        CATEGORIES_URL, params={"tenant_id": TENANT_ID, "active_only": "false"}
    )
    assert response.json()["count"] == 1
    assert response.json()["categories"][0]["isActive"] is False


def test_categories_delete_already_inactive_is_idempotent(api_client, seed_category):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    api_client.delete(f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID})
    response = api_client.delete(
        f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID}
    )
    assert response.status_code == 204


def test_categories_reactivate_via_patch(api_client, seed_category):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    api_client.delete(f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID})
    response = api_client.patch(
        f"{CATEGORIES_URL}/{CATEGORY_NAME}",
        params={"tenant_id": TENANT_ID},
        json={"is_active": True},
    )
    assert response.status_code == 200
    assert response.json()["isActive"] is True


# ==============================================================================
# Cross-tenant isolation
# ==============================================================================


def test_categories_tenant_admin_cannot_see_other_tenants_data(
    api_client, document_categories_table
):
    # Seed category for tenant A as super-admin
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    api_client.post(CATEGORIES_URL, params={"tenant_id": TENANT_ID}, json=NEW_CATEGORY)

    # Tenant B admin lists - should see nothing
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=OTHER_TENANT_ID))
    response = api_client.get(CATEGORIES_URL)
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_categories_super_admin_sees_disjoint_sets(api_client, document_categories_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    api_client.post(CATEGORIES_URL, params={"tenant_id": TENANT_ID}, json=NEW_CATEGORY)
    api_client.post(
        CATEGORIES_URL,
        params={"tenant_id": OTHER_TENANT_ID},
        json={"category_name": "expenses", "display_name": "Expenses"},
    )

    resp_a = api_client.get(CATEGORIES_URL, params={"tenant_id": TENANT_ID})
    resp_b = api_client.get(CATEGORIES_URL, params={"tenant_id": OTHER_TENANT_ID})
    assert resp_a.json()["count"] == 1
    assert resp_a.json()["categories"][0]["categoryName"] == CATEGORY_NAME
    assert resp_b.json()["count"] == 1
    assert resp_b.json()["categories"][0]["categoryName"] == "expenses"


# ==============================================================================
# Update edge cases
# ==============================================================================


def test_categories_update_not_found_returns_404(api_client, document_categories_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.patch(
        f"{CATEGORIES_URL}/missing",
        params={"tenant_id": TENANT_ID},
        json={"display_name": "X"},
    )
    assert response.status_code == 404


def test_categories_tenant_admin_update_empty_body_returns_400(api_client, seed_category):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.patch(f"{CATEGORIES_URL}/{CATEGORY_NAME}", json={})
    assert response.status_code == 400


def test_categories_deactivate_via_patch(api_client, seed_category):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.patch(
        f"{CATEGORIES_URL}/{CATEGORY_NAME}",
        params={"tenant_id": TENANT_ID},
        json={"is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["isActive"] is False


# ==============================================================================
# Validation boundaries
# ==============================================================================


def test_categories_create_empty_name_returns_422(api_client, document_categories_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.post(
        CATEGORIES_URL,
        params={"tenant_id": TENANT_ID},
        json={"category_name": "", "display_name": "X"},
    )
    assert response.status_code == 422


def test_categories_create_name_too_long_returns_422(api_client, document_categories_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.post(
        CATEGORIES_URL,
        params={"tenant_id": TENANT_ID},
        json={"category_name": "a" * 65, "display_name": "X"},
    )
    assert response.status_code == 422


def test_categories_create_uppercase_name_returns_422(api_client, document_categories_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.post(
        CATEGORIES_URL,
        params={"tenant_id": TENANT_ID},
        json={"category_name": "UPPERCASE", "display_name": "X"},
    )
    assert response.status_code == 422


def test_categories_create_display_name_too_long_returns_422(api_client, document_categories_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.post(
        CATEGORIES_URL,
        params={"tenant_id": TENANT_ID},
        json={"category_name": "valid", "display_name": "x" * 129},
    )
    assert response.status_code == 422


def test_categories_create_without_description_defaults_empty(
    api_client, document_categories_table
):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.post(
        CATEGORIES_URL,
        params={"tenant_id": TENANT_ID},
        json={"category_name": "no-desc", "display_name": "No Description"},
    )
    assert response.status_code == 201
    assert response.json()["description"] == ""


def test_categories_create_round_trips_all_fields(api_client, document_categories_table):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.post(CATEGORIES_URL, params={"tenant_id": TENANT_ID}, json=NEW_CATEGORY)
    assert response.status_code == 201
    data = response.json()
    assert data["categoryName"] == CATEGORY_NAME
    assert data["displayName"] == "Income Documents"
    assert data["description"] == "W2s, 1099s, etc."
    assert data["isActive"] is True
    assert data["tenantId"] == TENANT_ID


def test_categories_tenant_admin_create_duplicate_returns_409(api_client, seed_category):
    override_jwt(make_claims(groups=[TENANT_ADMIN], tenant_id=TENANT_ID))
    response = api_client.post(CATEGORIES_URL, json=NEW_CATEGORY)
    assert response.status_code == 409


# ==============================================================================
# isAutoRegistered
# ==============================================================================


def test_categories_manual_create_sets_is_auto_registered_false(
    api_client, document_categories_table
):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.post(CATEGORIES_URL, params={"tenant_id": TENANT_ID}, json=NEW_CATEGORY)
    assert response.status_code == 201
    assert response.json()["isAutoRegistered"] is False


def test_categories_auto_register_does_not_overwrite_manual(document_categories_table, api_client):
    from documentai_api.utils.document_categories import auto_register_category

    # Create manually first
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    api_client.post(CATEGORIES_URL, params={"tenant_id": TENANT_ID}, json=NEW_CATEGORY)

    # Simulate upload path auto-registering the same category
    auto_register_category(TENANT_ID, CATEGORY_NAME)

    response = api_client.get(f"{CATEGORIES_URL}/{CATEGORY_NAME}", params={"tenant_id": TENANT_ID})
    assert response.json()["isAutoRegistered"] is False


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
    api_client, document_categories_table, method, path
):
    override_jwt(make_claims(groups=[SUPER_ADMIN]))
    response = api_client.request(
        method, path, json=NEW_CATEGORY if method in ("POST", "PATCH") else None
    )
    assert response.status_code == 400
