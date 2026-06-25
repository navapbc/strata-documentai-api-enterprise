"""Tests for GET /v1/admin/documents endpoints."""

import json

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from documentai_api.app import app
from documentai_api.config.env import EnvVars
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.jwt_auth import verify_jwt

DOCUMENTS_URL = "/v1/admin/documents"

SUPER_ADMIN_CLAIMS = {
    "sub": "admin-001",
    "email": "admin@example.com",
    "token_use": "access",
    "cognito:groups": ["super-admin"],
}

TENANT_ADMIN_CLAIMS = {
    "sub": "user-001",
    "email": "user@example.com",
    "token_use": "access",
    "cognito:groups": ["tenant-admin"],
    "custom:tenant_id": "test-tenant",
}


def _override_jwt(claims: dict):
    app.dependency_overrides[verify_jwt] = lambda: claims


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.pop(verify_jwt, None)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def doc_metadata_table(monkeypatch):
    """Create a moto-backed document-metadata table with tenant GSI."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="doc-metadata-test",
            KeySchema=[{"AttributeName": "fileName", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "fileName", "AttributeType": "S"},
                {"AttributeName": "jobId", "AttributeType": "S"},
                {"AttributeName": "tenantId", "AttributeType": "S"},
                {"AttributeName": "createdAt", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "job-id-index",
                    "KeySchema": [{"AttributeName": "jobId", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "tenant-index",
                    "KeySchema": [
                        {"AttributeName": "tenantId", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        monkeypatch.setenv(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME, table.name)
        monkeypatch.setenv(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_JOB_ID_INDEX_NAME, "job-id-index")
        monkeypatch.setenv(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_TENANT_INDEX_NAME, "tenant-index")
        yield table


@pytest.fixture
def seeded_docs(doc_metadata_table):
    """Seed documents across tenants."""
    doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "input/test-tenant/doc1.pdf",
            DocumentMetadata.JOB_ID: "job-aaa-111",
            DocumentMetadata.ORIGINAL_FILE_NAME: "invoice.pdf",
            DocumentMetadata.TENANT_ID: "test-tenant",
            DocumentMetadata.API_KEY_NAME: "my-key",
            DocumentMetadata.PROCESS_STATUS: "completed",
            DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY: "expenses",
            DocumentMetadata.BDA_MATCHED_BLUEPRINT_NAME: "invoice",
            DocumentMetadata.CREATED_AT: "2026-01-01T00:00:00Z",
            DocumentMetadata.PROCESSED_DATE: "2026-01-01T00:01:00Z",
        }
    )
    doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "input/test-tenant/doc2.pdf",
            DocumentMetadata.JOB_ID: "job-bbb-222",
            DocumentMetadata.ORIGINAL_FILE_NAME: "w2.pdf",
            DocumentMetadata.TENANT_ID: "test-tenant",
            DocumentMetadata.API_KEY_NAME: "my-key",
            DocumentMetadata.PROCESS_STATUS: "completed",
            DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY: "income",
            DocumentMetadata.BDA_MATCHED_BLUEPRINT_NAME: "w2-form",
            DocumentMetadata.CREATED_AT: "2026-01-02T00:00:00Z",
            DocumentMetadata.PROCESSED_DATE: "2026-01-02T00:01:00Z",
            DocumentMetadata.V1_API_RESPONSE_JSON: json.dumps(
                {
                    "jobId": "job-bbb-222",
                    "jobStatus": "completed",
                    "fields": {
                        "employeeName": {"confidence": 0.95, "value": "John"},
                        "wages": {"confidence": 0.88, "value": "50000"},
                    },
                }
            ),
            DocumentMetadata.FIELD_CONFIDENCE_SCORES: json.dumps(
                [
                    {"employeeName": 0.95},
                    {"wages": 0.88},
                ]
            ),
        }
    )
    doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "input/other-tenant/doc3.pdf",
            DocumentMetadata.JOB_ID: "job-ccc-333",
            DocumentMetadata.ORIGINAL_FILE_NAME: "passport.pdf",
            DocumentMetadata.TENANT_ID: "other-tenant",
            DocumentMetadata.API_KEY_NAME: "other-key",
            DocumentMetadata.PROCESS_STATUS: "failed",
            DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY: "identity",
            DocumentMetadata.ERROR_MESSAGE: "Processing timeout",
            DocumentMetadata.CREATED_AT: "2026-01-03T00:00:00Z",
        }
    )
    doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "input/test-tenant/doc4.pdf",
            DocumentMetadata.JOB_ID: "job-ddd-444",
            DocumentMetadata.ORIGINAL_FILE_NAME: "alt-key.pdf",
            DocumentMetadata.TENANT_ID: "test-tenant",
            DocumentMetadata.API_KEY_NAME: "my-key",
            DocumentMetadata.PROCESS_STATUS: "completed",
            DocumentMetadata.CREATED_AT: "2026-01-04T00:00:00Z",
            DocumentMetadata.V1_API_RESPONSE_JSON: json.dumps(
                {
                    "jobId": "job-ddd-444",
                    "jobStatus": "completed",
                    "fields": {
                        "ssn": {"confidence": 0.99, "value": "<redacted>"},
                    },
                }
            ),
        }
    )
    doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "input/test-tenant/doc5.pdf",
            DocumentMetadata.JOB_ID: "job-eee-555",
            DocumentMetadata.ORIGINAL_FILE_NAME: "corrupt.pdf",
            DocumentMetadata.TENANT_ID: "test-tenant",
            DocumentMetadata.API_KEY_NAME: "my-key",
            DocumentMetadata.PROCESS_STATUS: "failed",
            DocumentMetadata.CREATED_AT: "2026-01-05T00:00:00Z",
            DocumentMetadata.V1_API_RESPONSE_JSON: "not-valid-json{{",
        }
    )


##############################################################################
# GET /v1/admin/documents (list)
##############################################################################


def test_list_unauthenticated_returns_401(client):
    response = client.get(DOCUMENTS_URL)
    assert response.status_code == 401


def test_list_pending_user_returns_403(client):
    _override_jwt({**SUPER_ADMIN_CLAIMS, "cognito:groups": []})
    response = client.get(DOCUMENTS_URL)
    assert response.status_code == 403


def test_list_requires_tenant_id(client, doc_metadata_table):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(DOCUMENTS_URL)
    assert response.status_code == 400
    assert "tenant_id is required" in response.json()["detail"]


def test_list_super_admin_by_tenant(client, seeded_docs):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(DOCUMENTS_URL, params={"tenant_id": "test-tenant"})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 4
    assert all(d["tenantId"] == "test-tenant" for d in data["documents"])


def test_list_returns_descending_order(client, seeded_docs):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(DOCUMENTS_URL, params={"tenant_id": "test-tenant"})
    data = response.json()
    dates = [d["createdAt"] for d in data["documents"]]
    assert dates == sorted(dates, reverse=True)


def test_list_tenant_admin_sees_own_only(client, seeded_docs):
    _override_jwt(TENANT_ADMIN_CLAIMS)
    response = client.get(DOCUMENTS_URL)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 4
    assert all(d["tenantId"] == "test-tenant" for d in data["documents"])


def test_list_tenant_admin_cannot_query_other_tenant(client, seeded_docs):
    _override_jwt(TENANT_ADMIN_CLAIMS)
    response = client.get(DOCUMENTS_URL, params={"tenant_id": "other-tenant"})
    assert response.status_code == 403


def test_list_pagination(client, seeded_docs):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    resp1 = client.get(DOCUMENTS_URL, params={"tenant_id": "test-tenant", "limit": 2})
    data1 = resp1.json()
    assert data1["count"] == 2
    assert data1["nextCursor"] is not None

    resp2 = client.get(
        DOCUMENTS_URL,
        params={"tenant_id": "test-tenant", "limit": 2, "cursor": data1["nextCursor"]},
    )
    data2 = resp2.json()
    assert data2["count"] == 2
    assert data2["nextCursor"] is None


def test_list_status_filter(client, seeded_docs):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(
        DOCUMENTS_URL, params={"tenant_id": "test-tenant", "status_filter": "completed"}
    )
    assert response.status_code == 200
    data = response.json()
    assert all(d["processStatus"] == "completed" for d in data["documents"])
    assert data["count"] == 3


def test_list_status_filter_no_match(client, seeded_docs):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(
        DOCUMENTS_URL, params={"tenant_id": "test-tenant", "status_filter": "in_progress"}
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_invalid_cursor_returns_400(client, doc_metadata_table):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(
        DOCUMENTS_URL, params={"tenant_id": "test-tenant", "cursor": "not-valid!"}
    )
    assert response.status_code == 400
    assert "Invalid cursor" in response.json()["detail"]


##############################################################################
# GET /v1/admin/documents/{job_id} (detail)
##############################################################################


def test_detail_unauthenticated_returns_401(client):
    response = client.get(f"{DOCUMENTS_URL}/job-aaa-111")
    assert response.status_code == 401


def test_detail_not_found(client, doc_metadata_table):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(f"{DOCUMENTS_URL}/nonexistent-job")
    assert response.status_code == 404


def test_detail_super_admin_can_view_any(client, seeded_docs):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(f"{DOCUMENTS_URL}/job-aaa-111")
    assert response.status_code == 200
    data = response.json()
    assert data["jobId"] == "job-aaa-111"
    assert data["fileName"] == "invoice.pdf"
    assert data["processStatus"] == "completed"
    assert data["matchedBlueprint"] == "invoice"


def test_detail_tenant_admin_can_view_own(client, seeded_docs):
    _override_jwt(TENANT_ADMIN_CLAIMS)
    response = client.get(f"{DOCUMENTS_URL}/job-aaa-111")
    assert response.status_code == 200
    assert response.json()["tenantId"] == "test-tenant"


def test_detail_tenant_admin_cannot_view_other(client, seeded_docs):
    _override_jwt(TENANT_ADMIN_CLAIMS)
    response = client.get(f"{DOCUMENTS_URL}/job-ccc-333")
    assert response.status_code == 404


def test_detail_includes_error_message(client, seeded_docs):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(f"{DOCUMENTS_URL}/job-ccc-333")
    assert response.status_code == 200
    data = response.json()
    assert data["errorMessage"] == "Processing timeout"
    assert data["processStatus"] == "failed"


def test_detail_extracted_data(client, seeded_docs):
    """Document with fields in V1_API_RESPONSE_JSON."""
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(f"{DOCUMENTS_URL}/job-bbb-222")
    assert response.status_code == 200
    body = response.json()
    assert body["fields"]["employeeName"] == {"confidence": 0.95, "value": "John"}
    assert body["fields"]["wages"] == {"confidence": 0.88, "value": "50000"}
    assert body["fieldConfidenceScores"] == [{"employeeName": 0.95}, {"wages": 0.88}]


def test_detail_extracted_data_redacted_values(client, seeded_docs):
    """Fields with redacted values still parse correctly."""
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(f"{DOCUMENTS_URL}/job-ddd-444")
    assert response.status_code == 200
    assert response.json()["fields"] == {"ssn": {"confidence": 0.99, "value": "<redacted>"}}


def test_detail_extracted_data_nests_dotted_fields(client, doc_metadata_table):
    """Admin detail nests verbatim, dot-separated stored field names for the client."""
    doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "input/test-tenant/nested.pdf",
            DocumentMetadata.JOB_ID: "job-nested-1",
            DocumentMetadata.ORIGINAL_FILE_NAME: "lease.pdf",
            DocumentMetadata.TENANT_ID: "test-tenant",
            DocumentMetadata.PROCESS_STATUS: "completed",
            DocumentMetadata.CREATED_AT: "2026-01-06T00:00:00Z",
            DocumentMetadata.V1_API_RESPONSE_JSON: json.dumps(
                {
                    "jobId": "job-nested-1",
                    "jobStatus": "completed",
                    "fields": {
                        "amount": {"confidence": 0.9, "value": "1"},
                        "payment_details.base_rent": {"confidence": 0.91, "value": "1200"},
                    },
                }
            ),
        }
    )
    _override_jwt(SUPER_ADMIN_CLAIMS)

    response = client.get(f"{DOCUMENTS_URL}/job-nested-1")

    assert response.status_code == 200
    fields = response.json()["fields"]
    assert fields["amount"] == {"confidence": 0.9, "value": "1"}
    assert fields["payment_details"]["base_rent"]["value"] == "1200"


def test_detail_malformed_json_returns_null(client, seeded_docs):
    """Corrupt V1_API_RESPONSE_JSON yields fields: null, not 500."""
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(f"{DOCUMENTS_URL}/job-eee-555")
    assert response.status_code == 200
    assert response.json()["fields"] is None


##############################################################################
# GET /v1/admin/documents/{job_id}/preview
##############################################################################

PREVIEW_URL = "/v1/admin/documents/{job_id}/preview"


@pytest.fixture
def seeded_docs_with_content_type(doc_metadata_table, monkeypatch):
    """Seed documents with content_type for preview tests."""
    monkeypatch.setenv(EnvVars.DOCUMENTAI_INPUT_LOCATION, "s3://test-bucket/input")

    doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "abc123_invoice.pdf",
            DocumentMetadata.JOB_ID: "job-preview-pdf",
            DocumentMetadata.ORIGINAL_FILE_NAME: "invoice.pdf",
            DocumentMetadata.TENANT_ID: "test-tenant",
            DocumentMetadata.API_KEY_NAME: "my-key",
            DocumentMetadata.PROCESS_STATUS: "completed",
            DocumentMetadata.CONTENT_TYPE: "application/pdf",
            DocumentMetadata.CREATED_AT: "2026-01-01T00:00:00Z",
        }
    )
    doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "abc456_photo.jpg",
            DocumentMetadata.JOB_ID: "job-preview-img",
            DocumentMetadata.ORIGINAL_FILE_NAME: "photo.jpg",
            DocumentMetadata.TENANT_ID: "test-tenant",
            DocumentMetadata.API_KEY_NAME: "my-key",
            DocumentMetadata.PROCESS_STATUS: "completed",
            DocumentMetadata.CONTENT_TYPE: "image/jpeg",
            DocumentMetadata.CREATED_AT: "2026-01-02T00:00:00Z",
        }
    )
    doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "abc789_data.csv",
            DocumentMetadata.JOB_ID: "job-preview-csv",
            DocumentMetadata.ORIGINAL_FILE_NAME: "data.csv",
            DocumentMetadata.TENANT_ID: "test-tenant",
            DocumentMetadata.API_KEY_NAME: "my-key",
            DocumentMetadata.PROCESS_STATUS: "completed",
            DocumentMetadata.CONTENT_TYPE: "text/csv",
            DocumentMetadata.CREATED_AT: "2026-01-03T00:00:00Z",
        }
    )
    doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "other_doc.pdf",
            DocumentMetadata.JOB_ID: "job-preview-other",
            DocumentMetadata.ORIGINAL_FILE_NAME: "secret.pdf",
            DocumentMetadata.TENANT_ID: "other-tenant",
            DocumentMetadata.API_KEY_NAME: "other-key",
            DocumentMetadata.PROCESS_STATUS: "completed",
            DocumentMetadata.CONTENT_TYPE: "application/pdf",
            DocumentMetadata.CREATED_AT: "2026-01-04T00:00:00Z",
        }
    )


def test_preview_unauthenticated_returns_401(client):
    response = client.get(PREVIEW_URL.format(job_id="job-preview-pdf"))
    assert response.status_code == 401


def test_preview_not_found(client, doc_metadata_table, monkeypatch):
    monkeypatch.setenv(EnvVars.DOCUMENTAI_INPUT_LOCATION, "s3://test-bucket/input")
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(PREVIEW_URL.format(job_id="nonexistent"))
    assert response.status_code == 404


def test_preview_pdf_returns_presigned_url(client, seeded_docs_with_content_type):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(PREVIEW_URL.format(job_id="job-preview-pdf"))
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert data["contentType"] == "application/pdf"
    assert data["expiresIn"] == 300
    assert "test-bucket" in data["url"]
    assert "abc123_invoice.pdf" in data["url"]


def test_preview_image_returns_presigned_url(client, seeded_docs_with_content_type):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(PREVIEW_URL.format(job_id="job-preview-img"))
    assert response.status_code == 200
    data = response.json()
    assert data["contentType"] == "image/jpeg"
    assert "abc456_photo.jpg" in data["url"]


def test_preview_unsupported_type_returns_422(client, seeded_docs_with_content_type):
    _override_jwt(SUPER_ADMIN_CLAIMS)
    response = client.get(PREVIEW_URL.format(job_id="job-preview-csv"))
    assert response.status_code == 422
    assert "Preview not available" in response.json()["detail"]


def test_preview_tenant_admin_can_view_own(client, seeded_docs_with_content_type):
    _override_jwt(TENANT_ADMIN_CLAIMS)
    response = client.get(PREVIEW_URL.format(job_id="job-preview-pdf"))
    assert response.status_code == 200
    assert "url" in response.json()


def test_preview_tenant_admin_cannot_view_other(client, seeded_docs_with_content_type):
    _override_jwt(TENANT_ADMIN_CLAIMS)
    response = client.get(PREVIEW_URL.format(job_id="job-preview-other"))
    assert response.status_code == 404


def test_preview_logs_audit_event(client, seeded_docs_with_content_type, mocker):
    from documentai_api.schemas.audit_event import AuditAction, AuditTargetType

    mock_log = mocker.patch("documentai_api.app_admin_documents.log_event")
    _override_jwt(SUPER_ADMIN_CLAIMS)

    response = client.get(PREVIEW_URL.format(job_id="job-preview-pdf"))
    assert response.status_code == 200

    mock_log.assert_called_once_with(
        SUPER_ADMIN_CLAIMS,
        action=AuditAction.DOCUMENT_PREVIEW,
        target_type=AuditTargetType.DOCUMENT,
        target_id="job-preview-pdf",
        tenant_id="test-tenant",
    )


def test_preview_not_found_does_not_log_audit_event(
    client, doc_metadata_table, monkeypatch, mocker
):
    monkeypatch.setenv(EnvVars.DOCUMENTAI_INPUT_LOCATION, "s3://test-bucket/input")
    mock_log = mocker.patch("documentai_api.app_admin_documents.log_event")
    _override_jwt(SUPER_ADMIN_CLAIMS)

    response = client.get(PREVIEW_URL.format(job_id="nonexistent"))
    assert response.status_code == 404
    mock_log.assert_not_called()


def test_list_logs_audit_event(client, seeded_docs, mocker):
    from documentai_api.schemas.audit_event import AuditAction, AuditTargetType

    mock_log = mocker.patch("documentai_api.app_admin_documents.log_event")
    _override_jwt(SUPER_ADMIN_CLAIMS)

    response = client.get(f"{DOCUMENTS_URL}?tenant_id=test-tenant")
    assert response.status_code == 200

    mock_log.assert_called_once_with(
        SUPER_ADMIN_CLAIMS,
        action=AuditAction.DOCUMENT_LIST,
        target_type=AuditTargetType.DOCUMENT,
        target_id="test-tenant",
        tenant_id="test-tenant",
        metadata={"count": 4, "status_filter": None},
    )


def test_get_document_logs_search_and_view(client, seeded_docs, mocker):
    from documentai_api.schemas.audit_event import AuditAction, AuditTargetType

    mock_log = mocker.patch("documentai_api.app_admin_documents.log_event")
    _override_jwt(SUPER_ADMIN_CLAIMS)

    response = client.get(f"{DOCUMENTS_URL}/job-aaa-111")
    assert response.status_code == 200

    assert mock_log.call_count == 2
    mock_log.assert_any_call(
        SUPER_ADMIN_CLAIMS,
        action=AuditAction.DOCUMENT_SEARCH,
        target_type=AuditTargetType.DOCUMENT,
        target_id="job-aaa-111",
    )
    mock_log.assert_any_call(
        SUPER_ADMIN_CLAIMS,
        action=AuditAction.DOCUMENT_VIEW,
        target_type=AuditTargetType.DOCUMENT,
        target_id="job-aaa-111",
        tenant_id="test-tenant",
    )


def test_get_document_not_found_logs_search_only(client, doc_metadata_table, mocker):
    from documentai_api.schemas.audit_event import AuditAction, AuditTargetType

    mock_log = mocker.patch("documentai_api.app_admin_documents.log_event")
    _override_jwt(SUPER_ADMIN_CLAIMS)

    response = client.get(f"{DOCUMENTS_URL}/nonexistent-job")
    assert response.status_code == 404

    mock_log.assert_called_once_with(
        SUPER_ADMIN_CLAIMS,
        action=AuditAction.DOCUMENT_SEARCH,
        target_type=AuditTargetType.DOCUMENT,
        target_id="nonexistent-job",
    )


def test_get_document_bounding_box_implies_extracted_data(client, doc_metadata_table, mocker):
    """GET with include_bounding_box=true (without include_extracted_data) calls _extract_field_values with both flags."""
    _override_jwt(SUPER_ADMIN_CLAIMS)

    doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "bbox-test.pdf",
            DocumentMetadata.JOB_ID: "bbox-job-id",
            DocumentMetadata.TENANT_ID: "test-tenant",
            DocumentMetadata.PROCESS_STATUS: "success",
            DocumentMetadata.CREATED_AT: "2025-01-01T00:00:00+00:00",
            DocumentMetadata.FIELD_CONFIDENCE_SCORES: "[]",
        }
    )

    mock_extract = mocker.patch(
        "documentai_api.app_admin_documents._extract_field_values",
        return_value={},
    )

    response = client.get(f"{DOCUMENTS_URL}/bbox-job-id?include_bounding_box=true")
    assert response.status_code == 200

    # include_bounding_box=true should have promoted include_extracted_data to True
    mock_extract.assert_called_once()
    args = mock_extract.call_args
    # _extract_field_values(record, include_extracted_data=True, include_bounding_box=True)
    assert args[0][1] is True  # include_extracted_data
    assert args[0][2] is True  # include_bounding_box
