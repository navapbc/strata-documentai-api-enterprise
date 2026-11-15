"""Tests for demo router endpoints (/v1/demo/documents)."""

from unittest.mock import AsyncMock

import pytest

from documentai_api.app import app
from documentai_api.constants.defaults import SystemDefaults
from documentai_api.routers.demo import _resolve_demo_context
from documentai_api.schemas.document_metadata import DocumentMetadata


@pytest.fixture(autouse=True)
def _disable_auth(disable_auth):
    pass


@pytest.fixture(autouse=True)
def _bypass_write_limit(mocker):
    mocker.patch("documentai_api.routers.documents.increment_and_check")


def test_demo_upload_returns_202(api_client, blank_pdf_bytes, mocker):
    """POST /v1/demo/documents returns 202 with job_id."""
    mocker.patch("documentai_api.routers.documents.insert_minimal_ddb_record")
    mocker.patch("documentai_api.routers.documents.dispatch_upload", new_callable=AsyncMock)

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/demo/documents", files=files)

    assert response.status_code == 202
    data = response.json()
    assert "jobId" in data
    assert data["jobStatus"] == "not_started"


def test_demo_upload_sets_is_demo_true(api_client, blank_pdf_bytes, mocker):
    """POST /v1/demo/documents forces is_demo=True on the record."""
    mock_insert = mocker.patch("documentai_api.routers.documents.insert_minimal_ddb_record")
    mocker.patch("documentai_api.routers.documents.dispatch_upload", new_callable=AsyncMock)

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    api_client.post("/v1/demo/documents", files=files)

    record = mock_insert.call_args[0][0]
    assert record.is_demo is True


def test_demo_upload_sets_ttl(api_client, blank_pdf_bytes, mocker):
    """POST /v1/demo/documents sets 3-day TTL on the record."""
    mock_insert = mocker.patch("documentai_api.routers.documents.insert_minimal_ddb_record")
    mocker.patch("documentai_api.routers.documents.dispatch_upload", new_callable=AsyncMock)

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    api_client.post("/v1/demo/documents", files=files)

    record = mock_insert.call_args[0][0]
    assert record.ttl_days == SystemDefaults.DEMO_DOCUMENT_TTL_DAYS


def test_demo_upload_does_not_increment_quota(api_client, blank_pdf_bytes, mocker):
    """POST /v1/demo/documents must not count against the tenant's request quota."""
    mock_increment = mocker.patch("documentai_api.routers.documents.increment_and_check")
    mocker.patch("documentai_api.routers.documents.insert_minimal_ddb_record")
    mocker.patch("documentai_api.routers.documents.dispatch_upload", new_callable=AsyncMock)

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    api_client.post("/v1/demo/documents", files=files)

    mock_increment.assert_not_called()

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
            DocumentMetadata.TENANT_ID: "test-demo-tenant-id",
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
            DocumentMetadata.TENANT_ID: "test-demo-tenant-id",
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
            DocumentMetadata.TENANT_ID: "test-demo-tenant-id",
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


@pytest.fixture
def demo_preview_doc(ddb_doc_metadata_table, monkeypatch):
    from documentai_api.generated.env_var_names_generated import EnvVarNames

    monkeypatch.setenv(EnvVarNames.DOCUMENTAI_DEMO_INPUT_LOCATION, "s3://test-bucket/demo-input")
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "mine.pdf",
            DocumentMetadata.JOB_ID: "job-demo-preview",
            DocumentMetadata.TENANT_ID: "test-demo-tenant-id",
            DocumentMetadata.CONTENT_TYPE: "application/pdf",
            DocumentMetadata.ORIGINAL_FILE_NAME: "mine.pdf",
            DocumentMetadata.CREATED_AT: "2026-01-01T00:00:00Z",
        }
    )


@pytest.mark.usefixtures("demo_preview_doc")
def test_demo_preview_missing_s3_object_returns_404(api_client, mocker):
    from botocore.exceptions import ClientError

    mocker.patch(
        "documentai_api.utils.s3.s3_service.head_object",
        side_effect=ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not Found"}}, "HeadObject"
        ),
    )
    mocker.patch(
        "documentai_api.utils.s3.s3_service.get_bucket_lifecycle_configuration",
        return_value={"Rules": []},
    )
    response = api_client.get("/v1/demo/documents/job-demo-preview/preview")
    assert response.status_code == 404
    assert "no longer exists" in response.json()["detail"]


@pytest.mark.usefixtures("demo_preview_doc")
def test_demo_preview_s3_throttle_returns_500(api_client, mocker):
    from botocore.exceptions import ClientError

    mocker.patch(
        "documentai_api.utils.s3.s3_service.head_object",
        side_effect=ClientError(
            {"Error": {"Code": "SlowDown", "Message": "Slow Down"}}, "HeadObject"
        ),
    )
    response = api_client.get("/v1/demo/documents/job-demo-preview/preview")
    assert response.status_code == 500


def test_demo_upload_rejects_without_auth(api_client, blank_pdf_bytes):
    """POST /v1/demo/documents returns 401 without valid credentials."""
    # Remove the auth override so the real dependency runs
    app.dependency_overrides.pop(_resolve_demo_context, None)

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/demo/documents", files=files)

    assert response.status_code == 401


# =============================================================================
# Presigned upload endpoint
# =============================================================================

PRESIGN_URL = "/v1/demo/documents/presigned-url"

_MOCK_POST_DATA = {
    "url": "https://test-bucket.s3.amazonaws.com/",
    "fields": {"key": "demo-input/demo-tenant/file-jobid.pdf", "Content-Type": "application/pdf"},
}


@pytest.fixture
def _demo_input_env(monkeypatch):
    from documentai_api.generated.env_var_names_generated import EnvVarNames

    monkeypatch.setenv(EnvVarNames.DOCUMENTAI_DEMO_INPUT_LOCATION, "s3://test-bucket/demo-input")


@pytest.mark.usefixtures("_demo_input_env")
def test_demo_presigned_success(api_client, mocker):
    """POST /v1/demo/documents/presigned-url returns uploadUrl, fields, and jobId."""
    mocker.patch("documentai_api.routers.demo.insert_minimal_ddb_record")
    mocker.patch("documentai_api.services.s3.generate_presigned_post", return_value=_MOCK_POST_DATA)

    response = api_client.post(
        PRESIGN_URL, data={"filename": "doc.pdf", "content_type": "application/pdf"}
    )

    assert response.status_code == 200
    result = response.json()
    assert result["uploadUrl"] == _MOCK_POST_DATA["url"]
    assert result["fields"] == _MOCK_POST_DATA["fields"]
    assert "jobId" in result


@pytest.mark.usefixtures("_demo_input_env")
def test_demo_presigned_ddb_record_is_demo(api_client, mocker):
    """DDB record has is_demo=True, PENDING_UPLOAD status, and the demo tenant_id."""
    from documentai_api.constants.processing import ProcessStatus, UploadMethod

    mock_insert = mocker.patch("documentai_api.routers.demo.insert_minimal_ddb_record")
    mocker.patch("documentai_api.services.s3.generate_presigned_post", return_value=_MOCK_POST_DATA)

    api_client.post(PRESIGN_URL, data={"filename": "doc.pdf", "content_type": "application/pdf"})

    record = mock_insert.call_args[0][0]
    assert record.is_demo is True
    assert record.process_status == ProcessStatus.PENDING_UPLOAD
    assert record.upload_method == UploadMethod.PRESIGNED
    assert record.tenant_id == "test-demo-tenant-id"


@pytest.mark.usefixtures("_demo_input_env")
def test_demo_presigned_s3_key_contains_tenant(api_client, mocker):
    """S3 object key is scoped under the demo tenant_id."""
    mocker.patch("documentai_api.routers.demo.insert_minimal_ddb_record")
    mock_generate = mocker.patch(
        "documentai_api.services.s3.generate_presigned_post", return_value=_MOCK_POST_DATA
    )

    api_client.post(PRESIGN_URL, data={"filename": "doc.pdf", "content_type": "application/pdf"})

    key = mock_generate.call_args.kwargs["key"]
    assert "test-demo-tenant-id" in key


@pytest.mark.usefixtures("_demo_input_env")
def test_demo_presigned_rejects_convertible_type(api_client):
    """HEIC and other REQUIRES_CONVERSION types return 400."""
    response = api_client.post(
        PRESIGN_URL, data={"filename": "photo.heic", "content_type": "image/heic"}
    )

    assert response.status_code == 400
    assert "direct upload endpoint" in response.json()["detail"]


def test_demo_presigned_rejects_without_auth(api_client):
    """POST /v1/demo/documents/presigned-url returns 401 without valid credentials."""
    app.dependency_overrides.pop(_resolve_demo_context, None)

    response = api_client.post(
        PRESIGN_URL, data={"filename": "doc.pdf", "content_type": "application/pdf"}
    )

    assert response.status_code == 401


@pytest.mark.usefixtures("_demo_input_env")
def test_demo_presigned_does_not_increment_quota(api_client, mocker):
    """Presigned demo upload must not count against the tenant's request quota."""
    from documentai_api.utils import write_limit

    mock_increment = mocker.patch.object(write_limit, "increment_and_check")
    mocker.patch("documentai_api.routers.demo.insert_minimal_ddb_record")
    mocker.patch("documentai_api.services.s3.generate_presigned_post", return_value=_MOCK_POST_DATA)

    api_client.post(PRESIGN_URL, data={"filename": "doc.pdf", "content_type": "application/pdf"})

    mock_increment.assert_not_called()


@pytest.mark.usefixtures("_demo_input_env")
def test_demo_presigned_signing_error_returns_500_no_ddb(api_client, mocker):
    """A signing failure returns 500 and must not write a DDB row."""
    mock_insert = mocker.patch("documentai_api.routers.demo.insert_minimal_ddb_record")
    mocker.patch(
        "documentai_api.services.s3.generate_presigned_post",
        side_effect=Exception("signing failed"),
    )

    response = api_client.post(
        PRESIGN_URL, data={"filename": "doc.pdf", "content_type": "application/pdf"}
    )

    assert response.status_code == 500
    assert "Failed to generate upload URL" in response.json()["detail"]
    mock_insert.assert_not_called()


def test_demo_presigned_missing_input_location_returns_500(api_client, mocker):
    """Missing DOCUMENTAI_DEMO_INPUT_LOCATION returns 500."""
    mocker.patch(
        "documentai_api.routers.demo.get_env_config"
    ).return_value.documentai_demo_input_location = None

    response = api_client.post(
        PRESIGN_URL, data={"filename": "doc.pdf", "content_type": "application/pdf"}
    )

    assert response.status_code == 500
    assert "Demo storage not configured" in response.json()["detail"]
