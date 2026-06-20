"""Tests for demo router endpoints (/v1/demo/documents)."""

from unittest.mock import AsyncMock

import pytest

from documentai_api.schemas.document_metadata import DocumentMetadata


@pytest.fixture(autouse=True)
def _disable_auth(disable_auth):
    pass


def test_demo_upload_returns_202(api_client, blank_pdf_bytes, mocker):
    """POST /v1/demo/documents returns 202 with job_id."""
    mocker.patch("documentai_api.app_documents.insert_minimal_ddb_record")
    mocker.patch("documentai_api.app_documents.dispatch_upload", new_callable=AsyncMock)

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/demo/documents", files=files)

    assert response.status_code == 202
    data = response.json()
    assert "jobId" in data
    assert data["jobStatus"] == "not_started"


def test_demo_upload_sets_is_demo_true(api_client, blank_pdf_bytes, mocker):
    """POST /v1/demo/documents forces is_demo=True on the record."""
    mock_insert = mocker.patch("documentai_api.app_documents.insert_minimal_ddb_record")
    mocker.patch("documentai_api.app_documents.dispatch_upload", new_callable=AsyncMock)

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    api_client.post("/v1/demo/documents", files=files)

    record = mock_insert.call_args[0][0]
    assert record.is_demo is True


def test_demo_upload_sets_ttl(api_client, blank_pdf_bytes, mocker):
    """POST /v1/demo/documents sets 3-day TTL on the record."""
    from documentai_api.config.constants import ConfigDefaults

    mock_insert = mocker.patch("documentai_api.app_documents.insert_minimal_ddb_record")
    mocker.patch("documentai_api.app_documents.dispatch_upload", new_callable=AsyncMock)

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    api_client.post("/v1/demo/documents", files=files)

    record = mock_insert.call_args[0][0]
    assert record.ttl_days == ConfigDefaults.DEMO_DOCUMENT_TTL_DAYS


def test_demo_list_returns_empty(api_client, ddb_doc_metadata_table):
    """GET /v1/demo/documents returns empty list when no demo docs exist."""
    response = api_client.get("/v1/demo/documents")

    assert response.status_code == 200
    data = response.json()
    assert data["documents"] == []
    assert data["count"] == 0


def test_demo_list_filters_to_is_demo(api_client, ddb_doc_metadata_table):
    """GET /v1/demo/documents only returns docs with isDemo=True."""
    # Insert a demo doc and a non-demo doc for the same tenant
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "demo-doc.pdf",
            DocumentMetadata.JOB_ID: "job-demo",
            DocumentMetadata.TENANT_ID: "demo-test-sub",
            DocumentMetadata.IS_DEMO: True,
            DocumentMetadata.ORIGINAL_FILE_NAME: "demo-doc.pdf",
            DocumentMetadata.PROCESS_STATUS: "success",
            DocumentMetadata.CREATED_AT: "2024-01-01T00:00:00Z",
            DocumentMetadata.API_KEY_NAME: "test-sub",
        }
    )
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "real-doc.pdf",
            DocumentMetadata.JOB_ID: "job-real",
            DocumentMetadata.TENANT_ID: "demo-test-sub",
            DocumentMetadata.IS_DEMO: False,
            DocumentMetadata.ORIGINAL_FILE_NAME: "real-doc.pdf",
            DocumentMetadata.PROCESS_STATUS: "success",
            DocumentMetadata.CREATED_AT: "2024-01-01T00:00:01Z",
            DocumentMetadata.API_KEY_NAME: "test-sub",
        }
    )

    response = api_client.get("/v1/demo/documents")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["documents"][0]["jobId"] == "job-demo"


def test_demo_get_not_found(api_client, ddb_doc_metadata_table):
    """GET /v1/demo/documents/{jobId} returns 404 for non-existent doc."""
    response = api_client.get("/v1/demo/documents/nonexistent-job-id")

    assert response.status_code == 404


def test_demo_get_wrong_tenant_returns_404(api_client, ddb_doc_metadata_table):
    """GET /v1/demo/documents/{jobId} returns 404 if doc belongs to different tenant."""
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "other.pdf",
            DocumentMetadata.JOB_ID: "job-other",
            DocumentMetadata.TENANT_ID: "demo-other-user",
            DocumentMetadata.ORIGINAL_FILE_NAME: "other.pdf",
            DocumentMetadata.PROCESS_STATUS: "success",
            DocumentMetadata.CREATED_AT: "2024-01-01T00:00:00Z",
        }
    )

    response = api_client.get("/v1/demo/documents/job-other")

    assert response.status_code == 404


def test_demo_get_success(api_client, ddb_doc_metadata_table):
    """GET /v1/demo/documents/{jobId} returns detail for matching tenant."""
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "mine.pdf",
            DocumentMetadata.JOB_ID: "job-mine",
            DocumentMetadata.TENANT_ID: "demo-test-sub",
            DocumentMetadata.ORIGINAL_FILE_NAME: "mine.pdf",
            DocumentMetadata.PROCESS_STATUS: "success",
            DocumentMetadata.CREATED_AT: "2024-01-01T00:00:00Z",
            DocumentMetadata.API_KEY_NAME: "test-sub",
        }
    )

    response = api_client.get("/v1/demo/documents/job-mine")

    assert response.status_code == 200
    data = response.json()
    assert data["jobId"] == "job-mine"


def test_demo_preview_wrong_tenant_returns_404(api_client, ddb_doc_metadata_table):
    """GET /v1/demo/documents/{jobId}/preview returns 404 for wrong tenant."""
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "other.pdf",
            DocumentMetadata.JOB_ID: "job-other",
            DocumentMetadata.TENANT_ID: "demo-other-user",
            DocumentMetadata.CONTENT_TYPE: "application/pdf",
            DocumentMetadata.ORIGINAL_FILE_NAME: "other.pdf",
            DocumentMetadata.CREATED_AT: "2024-01-01T00:00:00Z",
        }
    )

    response = api_client.get("/v1/demo/documents/job-other/preview")

    assert response.status_code == 404


def test_demo_upload_rejects_without_auth(api_client, blank_pdf_bytes):
    """POST /v1/demo/documents returns 401 without valid credentials."""
    from documentai_api.app import app
    from documentai_api.app_demo import _resolve_demo_context

    # Remove the auth override so the real dependency runs
    app.dependency_overrides.pop(_resolve_demo_context, None)

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/demo/documents", files=files)

    assert response.status_code == 401
