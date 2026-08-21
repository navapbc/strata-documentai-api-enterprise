"""Tests for GET /v1/admin/search/documents."""

import pytest

from documentai_api.schemas.document_metadata import DocumentMetadata
from tests.helpers.fixtures.claims import (
    SUPER_ADMIN_CLAIMS,
    TENANT_ADMIN_CLAIMS,
    TENANT_ADMIN_ID,
    override_jwt,
)

SEARCH_URL = "/v1/admin/search/documents"


@pytest.fixture
def seeded_docs(ddb_doc_metadata_table):
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "Invoice_Jan-test-job-id-1.pdf",
            DocumentMetadata.JOB_ID: "test-job-id-1",
            DocumentMetadata.ORIGINAL_FILE_NAME: "Invoice_Jan.pdf",
            DocumentMetadata.ORIGINAL_FILE_NAME_LOWER: "invoice_jan.pdf",
            DocumentMetadata.TENANT_ID: TENANT_ADMIN_ID,
            DocumentMetadata.API_KEY_NAME: "test-api-key",
            DocumentMetadata.PROCESS_STATUS: "completed",
            DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY: "expenses",
            DocumentMetadata.BDA_MATCHED_BLUEPRINT_NAME: "invoice",
            DocumentMetadata.CREATED_AT: "2026-01-01T00:00:00Z",
            DocumentMetadata.PROCESSED_DATE: "2026-01-01T00:01:00Z",
        }
    )
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "W2_2025-test-job-id-2.pdf",
            DocumentMetadata.JOB_ID: "test-job-id-2",
            DocumentMetadata.ORIGINAL_FILE_NAME: "W2_2025.pdf",
            DocumentMetadata.ORIGINAL_FILE_NAME_LOWER: "w2_2025.pdf",
            DocumentMetadata.TENANT_ID: TENANT_ADMIN_ID,
            DocumentMetadata.API_KEY_NAME: "test-api-key",
            DocumentMetadata.PROCESS_STATUS: "completed",
            DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY: "income",
            DocumentMetadata.BDA_MATCHED_BLUEPRINT_NAME: "w2-form",
            DocumentMetadata.CREATED_AT: "2026-02-01T00:00:00Z",
            DocumentMetadata.PROCESSED_DATE: "2026-02-01T00:01:00Z",
        }
    )
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "Invoice_Feb-test-job-id-3.pdf",
            DocumentMetadata.JOB_ID: "test-job-id-3",
            DocumentMetadata.ORIGINAL_FILE_NAME: "Invoice_Feb.pdf",
            DocumentMetadata.ORIGINAL_FILE_NAME_LOWER: "invoice_feb.pdf",
            DocumentMetadata.TENANT_ID: TENANT_ADMIN_ID,
            DocumentMetadata.API_KEY_NAME: "test-api-key",
            DocumentMetadata.PROCESS_STATUS: "failed",
            DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY: "expenses",
            DocumentMetadata.BDA_MATCHED_BLUEPRINT_NAME: "invoice",
            DocumentMetadata.CREATED_AT: "2026-03-01T00:00:00Z",
            DocumentMetadata.PROCESSED_DATE: "2026-03-01T00:01:00Z",
        }
    )
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "passport-test-job-id-4.pdf",
            DocumentMetadata.JOB_ID: "test-job-id-4",
            DocumentMetadata.ORIGINAL_FILE_NAME: "passport.pdf",
            DocumentMetadata.ORIGINAL_FILE_NAME_LOWER: "passport.pdf",
            DocumentMetadata.TENANT_ID: "other-tenant",
            DocumentMetadata.API_KEY_NAME: "other-api-key",
            DocumentMetadata.PROCESS_STATUS: "completed",
            DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY: "identity",
            DocumentMetadata.CREATED_AT: "2026-01-15T00:00:00Z",
        }
    )


def test_search_unauthenticated_returns_401(api_client, ddb_doc_metadata_table):
    response = api_client.get(SEARCH_URL)
    assert response.status_code == 401


def test_search_pending_user_returns_403(api_client, ddb_doc_metadata_table):
    override_jwt({**SUPER_ADMIN_CLAIMS, "cognito:groups": []})
    response = api_client.get(SEARCH_URL)
    assert response.status_code == 403


def test_search_requires_tenant_id(api_client, ddb_doc_metadata_table):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(SEARCH_URL)
    assert response.status_code == 400
    assert "tenant_id is required" in response.json()["detail"]


def test_search_no_filters_returns_all(api_client, seeded_docs):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(SEARCH_URL, params={"tenant_id": TENANT_ADMIN_ID})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    assert all(d["tenantId"] == TENANT_ADMIN_ID for d in data["documents"])


def test_search_filename_case_insensitive(api_client, seeded_docs):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(
        SEARCH_URL, params={"tenant_id": TENANT_ADMIN_ID, "filename": "INVOICE"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert all("invoice" in d["fileName"].lower() for d in data["documents"])


@pytest.mark.parametrize(
    ("params", "expected_count", "expected_job_ids"),
    [
        ({"filename": "jan"}, 1, ["test-job-id-1"]),
        ({"date_from": "2026-02-01"}, 2, None),
        ({"date_to": "2026-01-01"}, 1, ["test-job-id-1"]),
        ({"user_provided_document_type": "expenses"}, 2, None),
        ({"matched_blueprint_name": "w2-form"}, 1, ["test-job-id-2"]),
        ({"filename": "nonexistent"}, 0, None),
    ],
    ids=["filename", "date_from", "date_to", "document_type", "blueprint_name", "no_match"],
)
def test_search_single_filter(api_client, seeded_docs, params, expected_count, expected_job_ids):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(SEARCH_URL, params={"tenant_id": TENANT_ADMIN_ID, **params})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == expected_count

    if expected_count == 0:
        assert data["documents"] == []

    if expected_job_ids is not None:
        assert [d["jobId"] for d in data["documents"]] == expected_job_ids


def test_search_date_to_same_day_inclusive(api_client, seeded_docs):
    """date_to must include documents whose timestamp falls on that day.

    Regression: bare date "2026-01-01" is lexicographically less than
    "2026-01-01T00:00:00Z", so a plain lte would exclude the whole day.
    """
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(
        SEARCH_URL, params={"tenant_id": TENANT_ADMIN_ID, "date_to": "2026-01-01"}
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["documents"][0]["jobId"] == "test-job-id-1"


def test_search_date_range(api_client, seeded_docs):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(
        SEARCH_URL,
        params={
            "tenant_id": TENANT_ADMIN_ID,
            "date_from": "2026-01-01",
            "date_to": "2026-02-28",
        },
    )
    assert response.status_code == 200
    assert response.json()["count"] == 2


def test_search_combined_filters(api_client, seeded_docs):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(
        SEARCH_URL,
        params={
            "tenant_id": TENANT_ADMIN_ID,
            "filename": "invoice",
            "user_provided_document_type": "expenses",
        },
    )
    assert response.status_code == 200
    assert response.json()["count"] == 2


def test_search_tenant_admin_sees_own_only(api_client, seeded_docs):
    override_jwt(TENANT_ADMIN_CLAIMS)
    response = api_client.get(SEARCH_URL)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    assert all(d["tenantId"] == "tenant-admin-id" for d in data["documents"])


def test_search_tenant_admin_cannot_query_other_tenant(api_client, seeded_docs):
    override_jwt(TENANT_ADMIN_CLAIMS)
    response = api_client.get(SEARCH_URL, params={"tenant_id": "other-tenant"})
    assert response.status_code == 403


def test_search_invalid_cursor_returns_400(api_client, ddb_doc_metadata_table):
    override_jwt(SUPER_ADMIN_CLAIMS)
    response = api_client.get(
        SEARCH_URL, params={"tenant_id": TENANT_ADMIN_ID, "cursor": "not-valid!"}
    )
    assert response.status_code == 400
    assert "Invalid cursor" in response.json()["detail"]


def test_search_pagination(api_client, seeded_docs):
    override_jwt(SUPER_ADMIN_CLAIMS)
    resp1 = api_client.get(SEARCH_URL, params={"tenant_id": TENANT_ADMIN_ID, "limit": 2})
    data1 = resp1.json()
    assert data1["count"] == 2
    assert data1["nextCursor"] is not None

    resp2 = api_client.get(
        SEARCH_URL,
        params={"tenant_id": TENANT_ADMIN_ID, "limit": 2, "cursor": data1["nextCursor"]},
    )

    data2 = resp2.json()
    assert data2["count"] == 1
    assert data2["nextCursor"] is None
