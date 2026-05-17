"""Tests for batch upload endpoints."""

import os
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from documentai_api.app import app, verify_api_key
from documentai_api.app_batch import validate_batch_id
from documentai_api.config.constants import BatchStatus
from documentai_api.config.env import EnvVars
from documentai_api.schemas.document_batches import DocumentBatches


def _mock_verify_api_key() -> None:
    return None


@pytest.fixture(autouse=True)
def disable_auth():
    """Disable API key auth for all tests in this file."""
    app.dependency_overrides[verify_api_key] = _mock_verify_api_key
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def pdf_file():
    """Factory for a test PDF file tuple suitable for httpx files={...}."""

    def _create(
        filename: str = "test.pdf", content: bytes = b"%PDF-1.4 fake"
    ) -> tuple[str, bytes, str]:
        return (filename, content, "application/pdf")

    return _create


@pytest.fixture
def zip_with_pdfs():
    """Factory that builds a ZIP archive containing the given PDF filenames."""

    def _create(filenames: list[str]) -> BytesIO:
        from zipfile import ZipFile

        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            for filename in filenames:
                zip_file.writestr(filename, b"fake pdf content")
        zip_buffer.seek(0)
        return zip_buffer

    return _create


def test_config_includes_batch_endpoints(api_client):
    """/config response advertises the new batch endpoints."""
    response = api_client.get("/config")
    assert response.status_code == 200
    endpoints = response.json()["endpoints"]
    assert "batchUpload" in endpoints
    assert "batchUploadZip" in endpoints
    assert "batchUploadStatus" in endpoints


def test_batch_upload_success(api_client, pdf_file):
    """Successful multi-file batch upload returns per-file job info."""
    with (
        patch.dict(
            os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-batches-table"}
        ),
        patch("documentai_api.utils.uploads.filetype.guess_mime", return_value="application/pdf"),
        patch("documentai_api.app_batch.upload_document_for_processing", new_callable=AsyncMock),
        patch("documentai_api.app_batch.insert_minimal_ddb_record"),
        patch("documentai_api.app_batch.validate_batch_id"),
        patch("documentai_api.app_batch.create_batch"),
        patch("documentai_api.app_batch.update_batch_status"),
        patch(
            "documentai_api.app_batch.get_batch",
            return_value={"batchId": "test-batch", "createdAt": "2026-03-02T20:00:00Z"},
        ),
    ):
        files = [
            ("files", pdf_file("doc1.pdf")),
            ("files", pdf_file("doc2.pdf")),
        ]
        response = api_client.post("/v1/documents/batch", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "batchId" in data
    assert data["totalFiles"] == 2
    assert len(data["jobs"]) == 2


def test_batch_upload_no_files(api_client):
    """Batch upload with no files fails 422 (FastAPI form validation)."""
    response = api_client.post("/v1/documents/batch")
    assert response.status_code == 422


def test_batch_upload_invalid_file_type(api_client):
    """Batch upload with unsupported content type fails 400."""
    with (
        patch.dict(
            os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-batches-table"}
        ),
        patch("documentai_api.utils.uploads.filetype.guess_mime", return_value="text/plain"),
        patch("documentai_api.app_batch.validate_batch_id"),
        patch("documentai_api.app_batch.create_batch"),
        patch("documentai_api.app_batch.update_batch_status"),
    ):
        files = [("files", ("doc.txt", b"text", "text/plain"))]
        response = api_client.post("/v1/documents/batch", files=files)

    assert response.status_code == 400


def test_zip_upload_success(api_client, zip_with_pdfs):
    """Successful ZIP upload returns batch info."""
    with (
        patch.dict(os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-table"}),
        patch(
            "documentai_api.app_batch.extract_files_from_zip", new_callable=AsyncMock
        ) as mock_extract,
        patch(
            "documentai_api.app_batch.validate_file_type",
            new_callable=AsyncMock,
            return_value="application/pdf",
        ),
        patch("documentai_api.app_batch.upload_document_for_processing", new_callable=AsyncMock),
        patch("documentai_api.app_batch.insert_minimal_ddb_record"),
        patch("documentai_api.app_batch.validate_batch_id"),
        patch("documentai_api.app_batch.create_batch"),
        patch("documentai_api.app_batch.update_batch_status"),
        patch(
            "documentai_api.app_batch.get_batch",
            return_value={"batchId": "test-batch", "createdAt": "2026-03-02T20:00:00Z"},
        ),
    ):
        mock_file = MagicMock()
        mock_file.filename = "doc1.pdf"
        mock_file.file = BytesIO(b"fake pdf")
        mock_extract.return_value = [mock_file]

        zip_content = zip_with_pdfs(["doc1.pdf"])
        files = {"zip_file": ("batch.zip", zip_content, "application/zip")}
        response = api_client.post("/v1/documents/batch/zip", files=files)

    assert response.status_code == 200
    assert response.json()["totalFiles"] == 1


def test_zip_upload_empty(api_client):
    """ZIP upload with no valid files fails 400."""
    with (
        patch.dict(os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-table"}),
        patch(
            "documentai_api.app_batch.extract_files_from_zip", new_callable=AsyncMock
        ) as mock_extract,
        patch("documentai_api.app_batch.validate_batch_id"),
        patch("documentai_api.app_batch.create_batch"),
        patch("documentai_api.app_batch.update_batch_status"),
    ):
        mock_extract.return_value = []
        zip_content = BytesIO(b"fake zip")
        files = {"zip_file": ("empty.zip", zip_content, "application/zip")}
        response = api_client.post("/v1/documents/batch/zip", files=files)

    assert response.status_code == 400


def test_get_batch_status_success(api_client):
    """GET /v1/batches/{id} returns aggregate status + per-job list."""
    with (
        patch("documentai_api.app_batch.get_batch") as mock_get_batch,
        patch("documentai_api.app_batch.query_jobs_by_batch_id") as mock_query_jobs,
    ):
        mock_get_batch.return_value = {
            "batchId": "test-batch-id",
            "batchStatus": "processing",
            "createdAt": "2026-02-27",
        }
        mock_query_jobs.return_value = [
            {"fileName": "doc1.pdf", "jobId": "job-1", "processStatus": "success"},
            {"fileName": "doc2.pdf", "jobId": "job-2", "processStatus": "started"},
        ]

        response = api_client.get("/v1/batches/test-batch-id")

    assert response.status_code == 200
    data = response.json()
    assert data["batchId"] == "test-batch-id"
    assert data["batchStatus"] == BatchStatus.PROCESSING.value
    assert data["totalJobs"] == 2
    assert data["completed"] == 1
    assert data["inProgress"] == 1


def test_get_batch_status_not_found(api_client):
    """GET /v1/batches/{id} returns 404 when batch doesn't exist."""
    with patch("documentai_api.app_batch.get_batch", return_value=None):
        response = api_client.get("/v1/batches/fake-batch")

    assert response.status_code == 404


def test_get_batch_status_lazy_completion(api_client):
    """Batch status flips to COMPLETED when all jobs are done."""
    with (
        patch("documentai_api.app_batch.get_batch") as mock_get_batch,
        patch("documentai_api.app_batch.query_jobs_by_batch_id") as mock_query_jobs,
        patch("documentai_api.app_batch.update_batch_status") as mock_update,
    ):
        mock_get_batch.return_value = {
            DocumentBatches.BATCH_ID: "test-batch",
            DocumentBatches.BATCH_STATUS: "processing",
            DocumentBatches.CREATED_AT: "2026-02-27",
        }
        mock_query_jobs.return_value = [
            {"fileName": "doc1.pdf", "jobId": "job-1", "processStatus": "success"},
            {"fileName": "doc2.pdf", "jobId": "job-2", "processStatus": "failed"},
        ]

        response = api_client.get("/v1/batches/test-batch")

        assert response.status_code == 200
        data = response.json()
        assert data["batchStatus"] == "completed"
        mock_update.assert_called_once_with("test-batch", status=BatchStatus.COMPLETED)


def test_get_batch_status_with_failed_count(api_client):
    """Batch status response includes failed count."""
    with (
        patch("documentai_api.app_batch.get_batch") as mock_get_batch,
        patch("documentai_api.app_batch.query_jobs_by_batch_id") as mock_query_jobs,
    ):
        mock_get_batch.return_value = {
            DocumentBatches.BATCH_ID: "test-batch",
            DocumentBatches.BATCH_STATUS: "processing",
            DocumentBatches.CREATED_AT: "2026-02-27",
        }
        mock_query_jobs.return_value = [
            {"fileName": "doc1.pdf", "jobId": "job-1", "processStatus": "success"},
            {"fileName": "doc2.pdf", "jobId": "job-2", "processStatus": "failed"},
            {"fileName": "doc3.pdf", "jobId": "job-3", "processStatus": "started"},
        ]

        response = api_client.get("/v1/batches/test-batch")

        assert response.status_code == 200
        data = response.json()
        assert data["totalJobs"] == 3
        assert data["completed"] == 2
        assert data["failed"] == 1
        assert data["inProgress"] == 1


def test_get_batch_status_no_lazy_completion_when_incomplete(api_client):
    """Batch status stays processing when at least one job is still running."""
    with (
        patch("documentai_api.app_batch.get_batch") as mock_get_batch,
        patch("documentai_api.app_batch.query_jobs_by_batch_id") as mock_query_jobs,
        patch("documentai_api.app_batch.update_batch_status") as mock_update,
    ):
        mock_get_batch.return_value = {
            DocumentBatches.BATCH_ID: "test-batch",
            DocumentBatches.BATCH_STATUS: "processing",
            DocumentBatches.CREATED_AT: "2026-02-27",
        }
        mock_query_jobs.return_value = [
            {"fileName": "doc1.pdf", "jobId": "job-1", "processStatus": "success"},
            {"fileName": "doc2.pdf", "jobId": "job-2", "processStatus": "started"},
        ]

        response = api_client.get("/v1/batches/test-batch")

        assert response.status_code == 200
        data = response.json()
        assert data["batchStatus"] == "processing"
        mock_update.assert_not_called()


def test_validate_batch_id_no_existing_batch():
    """validate_batch_id passes when the batch doesn't exist yet."""
    with patch("documentai_api.app_batch.get_batch", return_value=None):
        validate_batch_id("new-batch-id")  # should not raise


@pytest.mark.asyncio
async def test_upload_document_batch_exceeds_max_size(api_client, monkeypatch):
    """Batch upload rejects > MAX_BATCH_SIZE files with 400."""
    monkeypatch.setattr("documentai_api.app_batch.MAX_BATCH_SIZE", 2)

    files = [
        ("files", ("file1.pdf", b"content1", "application/pdf")),
        ("files", ("file2.pdf", b"content2", "application/pdf")),
        ("files", ("file3.pdf", b"content3", "application/pdf")),
    ]

    response = api_client.post("/v1/documents/batch", files=files)

    assert response.status_code == 400
    assert "exceeds maximum of 2 files" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_zip_batch_exceeds_max_size(api_client, monkeypatch, zip_with_pdfs):
    """ZIP batch upload rejects > MAX_BATCH_SIZE files with 400."""
    monkeypatch.setattr("documentai_api.app_batch.MAX_BATCH_SIZE", 2)

    mock_files = []
    for i in range(3):
        mock_file = MagicMock()
        mock_file.filename = f"file{i + 1}.pdf"
        mock_file.file = BytesIO(b"fake pdf")
        mock_files.append(mock_file)

    with (
        patch.dict(os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-table"}),
        patch(
            "documentai_api.app_batch.extract_files_from_zip", new_callable=AsyncMock
        ) as mock_extract,
        patch("documentai_api.app_batch.validate_batch_id"),
    ):
        mock_extract.return_value = mock_files

        zip_content = zip_with_pdfs(["file1.pdf", "file2.pdf", "file3.pdf"])
        files = [("zip_file", ("batch.zip", zip_content, "application/zip"))]
        response = api_client.post("/v1/documents/batch/zip", files=files)

    assert response.status_code == 400
    assert "exceeds maximum of 2 files" in response.json()["detail"]
