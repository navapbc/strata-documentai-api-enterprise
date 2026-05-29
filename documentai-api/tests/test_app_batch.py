"""Tests for batch upload endpoints."""

import os
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from documentai_api.config.constants import BatchStatus
from documentai_api.config.env import EnvVars
from documentai_api.schemas.document_batches import DocumentBatches


@pytest.fixture(autouse=True)
def _disable_auth(disable_auth):
    pass


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
    assert "upload_document_batch" in endpoints
    assert "upload_zip_batch" in endpoints
    assert "get_batch_status" in endpoints


def test_batch_upload_success(api_client, pdf_file):
    """Successful multi-file batch upload returns per-file job info."""
    with (
        patch.dict(
            os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-batches-table"}
        ),
        patch("documentai_api.utils.uploads.filetype.guess_mime", return_value="application/pdf"),
        patch("documentai_api.app_batch.upload_document_for_processing", new_callable=AsyncMock),
        patch("documentai_api.app_batch.insert_minimal_ddb_record"),
        patch("documentai_api.app_batch.create_batch", return_value="2026-03-02T20:00:00Z"),
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


def test_batch_upload_with_external_fields(api_client, pdf_file):
    """Batch upload passes external fields to insert_minimal_ddb_record."""
    with (
        patch.dict(
            os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-batches-table"}
        ),
        patch("documentai_api.utils.uploads.filetype.guess_mime", return_value="application/pdf"),
        patch("documentai_api.app_batch.upload_document_for_processing", new_callable=AsyncMock),
        patch("documentai_api.app_batch.insert_minimal_ddb_record") as mock_insert,
        patch("documentai_api.app_batch.create_batch", return_value="2026-03-02T20:00:00Z"),
        patch("documentai_api.app_batch.update_batch_status"),
        patch(
            "documentai_api.app_batch.get_batch",
            return_value={"batchId": "test-batch", "createdAt": "2026-03-02T20:00:00Z"},
        ),
    ):
        files = [("files", pdf_file("doc1.pdf"))]
        data = {
            "external_document_id": "test-ext-doc-id",
            "external_system_id": "test-ext-sys-id",
            "ai_consent_flag": "true",
        }
        response = api_client.post("/v1/documents/batch", files=files, data=data)

    assert response.status_code == 200
    record = mock_insert.call_args[0][0]
    assert record.external_document_id == "test-ext-doc-id"
    assert record.external_system_id == "test-ext-sys-id"
    assert record.ai_consent_flag is True


def test_batch_upload_ai_consent_declined(api_client, pdf_file):
    """Batch upload with ai_consent_flag=false skips S3 upload and marks as declined."""
    with (
        patch.dict(
            os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-batches-table"}
        ),
        patch("documentai_api.utils.uploads.filetype.guess_mime", return_value="application/pdf"),
        patch(
            "documentai_api.app_batch.upload_document_for_processing", new_callable=AsyncMock
        ) as mock_upload,
        patch("documentai_api.app_batch.insert_minimal_ddb_record"),
        patch("documentai_api.app_batch.classify_as_ai_consent_declined") as mock_classify,
        patch("documentai_api.app_batch.create_batch", return_value="2026-03-02T20:00:00Z"),
        patch("documentai_api.app_batch.update_batch_status"),
        patch(
            "documentai_api.app_batch.get_batch",
            return_value={"batchId": "test-batch", "createdAt": "2026-03-02T20:00:00Z"},
        ),
    ):
        files = [("files", pdf_file("doc1.pdf"))]
        data = {"ai_consent_flag": "false"}
        response = api_client.post("/v1/documents/batch", files=files, data=data)

    assert response.status_code == 200
    mock_upload.assert_not_called()
    mock_classify.assert_called_once()


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
        patch("documentai_api.app_batch.create_batch", return_value="2026-03-02T20:00:00Z"),
        patch("documentai_api.app_batch.update_batch_status"),
        patch("documentai_api.app_batch.get_batch", return_value=None),
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
        patch("documentai_api.app_batch.create_batch", return_value="2026-03-02T20:00:00Z"),
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


def test_get_batch_status_lazy_completion_all_success(api_client):
    """Batch status flips to COMPLETED when all jobs succeed."""
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
            {"fileName": "doc2.pdf", "jobId": "job-2", "processStatus": "success"},
        ]

        response = api_client.get("/v1/batches/test-batch")

        assert response.status_code == 200
        data = response.json()
        assert data["batchStatus"] == "completed"
        mock_update.assert_called_once_with(
            "test-batch",
            status=BatchStatus.COMPLETED,
            condition_expression=f"{DocumentBatches.BATCH_STATUS} = :expected",
            condition_values={":expected": BatchStatus.PROCESSING.value},
        )


def test_get_batch_status_lazy_completion_with_failures(api_client):
    """Batch status flips to FAILED when all jobs are terminal but some failed."""
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
        assert data["batchStatus"] == "failed"
        mock_update.assert_called_once_with(
            "test-batch",
            status=BatchStatus.FAILED,
            condition_expression=f"{DocumentBatches.BATCH_STATUS} = :expected",
            condition_values={":expected": BatchStatus.PROCESSING.value},
        )


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


def test_batch_upload_returns_uuid_batch_id(api_client, pdf_file):
    """Batch upload returns a server-generated UUID batch_id."""
    import uuid

    with (
        patch.dict(
            os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-batches-table"}
        ),
        patch("documentai_api.utils.uploads.filetype.guess_mime", return_value="application/pdf"),
        patch("documentai_api.app_batch.upload_document_for_processing", new_callable=AsyncMock),
        patch("documentai_api.app_batch.insert_minimal_ddb_record"),
        patch("documentai_api.app_batch.create_batch", return_value="2026-03-02T20:00:00Z"),
        patch("documentai_api.app_batch.update_batch_status"),
        patch(
            "documentai_api.app_batch.get_batch",
            return_value={"batchId": "test-batch", "createdAt": "2026-03-02T20:00:00Z"},
        ),
    ):
        files = [("files", pdf_file("doc1.pdf"))]
        response = api_client.post("/v1/documents/batch", files=files)

    assert response.status_code == 200
    batch_id = response.json()["batchId"]
    # batch_id is tenant-prefixed: "{tenant_id}/{uuid}"
    tenant_prefix, sep, uuid_part = batch_id.partition("/")
    assert sep == "/"
    assert tenant_prefix == "test-tenant"
    # Verify the suffix is a valid UUID
    uuid.UUID(uuid_part)


def test_upload_document_batch_exceeds_max_size(api_client, monkeypatch):
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


def test_get_batch_status_conditional_update_race(api_client):
    """When another poller already updated batch status, re-read returns their value."""
    with (
        patch("documentai_api.app_batch.get_batch") as mock_get_batch,
        patch("documentai_api.app_batch.query_jobs_by_batch_id") as mock_query_jobs,
        patch("documentai_api.app_batch.update_batch_status") as mock_update,
    ):
        # First call: initial read (processing). Second call: re-read sees winner's write.
        mock_get_batch.side_effect = [
            {
                DocumentBatches.BATCH_ID: "test-batch",
                DocumentBatches.BATCH_STATUS: "processing",
                DocumentBatches.CREATED_AT: "2026-02-27",
            },
            {
                DocumentBatches.BATCH_ID: "test-batch",
                DocumentBatches.BATCH_STATUS: "completed",
                DocumentBatches.CREATED_AT: "2026-02-27",
            },
        ]
        mock_query_jobs.return_value = [
            {"fileName": "doc1.pdf", "jobId": "job-1", "processStatus": "success"},
            {"fileName": "doc2.pdf", "jobId": "job-2", "processStatus": "success"},
        ]
        # Simulate ConditionalCheckFailedException (another poller won)
        mock_update.side_effect = Exception("ConditionalCheckFailedException")

        response = api_client.get("/v1/batches/test-batch")

        assert response.status_code == 200
        # Response reflects the winner's write, not our stale snapshot
        data = response.json()
        assert data["batchStatus"] == "completed"


def test_batch_upload_classify_as_failed_on_upload_error(api_client, pdf_file):
    """When upload_document_for_processing raises HTTPException, classify_as_failed is called."""
    with (
        patch.dict(
            os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-batches-table"}
        ),
        patch("documentai_api.utils.uploads.filetype.guess_mime", return_value="application/pdf"),
        patch(
            "documentai_api.app_batch.upload_document_for_processing", new_callable=AsyncMock
        ) as mock_upload,
        patch("documentai_api.app_batch.insert_minimal_ddb_record"),
        patch("documentai_api.app_batch.classify_as_failed") as mock_classify_failed,
        patch("documentai_api.app_batch.create_batch", return_value="2026-03-02T20:00:00Z"),
        patch("documentai_api.app_batch.update_batch_status"),
        patch("documentai_api.app_batch.get_batch", return_value={"batchId": "b"}),
    ):
        mock_upload.side_effect = HTTPException(status_code=500, detail="S3 upload failed")

        files = [("files", pdf_file("doc1.pdf"))]
        response = api_client.post("/v1/documents/batch", files=files)

    assert response.status_code == 500
    mock_classify_failed.assert_called_once()
    call_kwargs = mock_classify_failed.call_args.kwargs
    assert call_kwargs["error_message"] == "S3 upload failed"


def test_batch_upload_classify_as_conversion_failed(api_client, pdf_file):
    """When upload raises ImageConversionError, classify_as_conversion_failed is called."""
    from documentai_api.utils.uploads import ImageConversionError

    with (
        patch.dict(
            os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-batches-table"}
        ),
        patch("documentai_api.utils.uploads.filetype.guess_mime", return_value="application/pdf"),
        patch(
            "documentai_api.app_batch.upload_document_for_processing", new_callable=AsyncMock
        ) as mock_upload,
        patch("documentai_api.app_batch.insert_minimal_ddb_record"),
        patch("documentai_api.app_batch.classify_as_conversion_failed") as mock_classify_conversion,
        patch("documentai_api.app_batch.create_batch", return_value="2026-03-02T20:00:00Z"),
        patch("documentai_api.app_batch.update_batch_status"),
        patch(
            "documentai_api.app_batch.get_batch",
            return_value={"batchId": "test-batch", "createdAt": "2026-03-02T20:00:00Z"},
        ),
    ):
        mock_upload.side_effect = ImageConversionError("HEIC conversion failed")

        files = [("files", pdf_file("doc1.heic"))]
        response = api_client.post("/v1/documents/batch", files=files)

    # Conversion failure is not fatal to the batch - job is marked failed but batch continues
    assert response.status_code == 200
    mock_classify_conversion.assert_called_once()
    call_kwargs = mock_classify_conversion.call_args.kwargs
    assert "HEIC conversion failed" in call_kwargs["error_message"]


def test_batch_upload_partial_success(api_client, pdf_file):
    """When one file fails with a non-HTTP error, batch is marked FAILED but siblings' DDB records persist."""
    with (
        patch.dict(
            os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-batches-table"}
        ),
        patch("documentai_api.utils.uploads.filetype.guess_mime", return_value="application/pdf"),
        patch(
            "documentai_api.app_batch.upload_document_for_processing", new_callable=AsyncMock
        ) as mock_upload,
        patch("documentai_api.app_batch.insert_minimal_ddb_record") as mock_insert,
        patch("documentai_api.app_batch.create_batch", return_value="2026-03-02T20:00:00Z"),
        patch("documentai_api.app_batch.update_batch_status") as mock_update_status,
        patch("documentai_api.app_batch.get_batch", return_value={"batchId": "b"}),
    ):
        # First file succeeds, second file raises a non-HTTP exception
        mock_upload.side_effect = [
            None,
            RuntimeError("Unexpected S3 error"),
        ]

        files = [
            ("files", pdf_file("doc1.pdf")),
            ("files", pdf_file("doc2.pdf")),
        ]
        response = api_client.post("/v1/documents/batch", files=files)

    assert response.status_code == 500
    # Both files got DDB records created (insert called for each)
    assert mock_insert.call_count == 2
    # Batch marked FAILED
    mock_update_status.assert_called()
    final_call = mock_update_status.call_args_list[-1]
    assert final_call.kwargs.get("status") == BatchStatus.FAILED


def test_batch_upload_create_batch_fails(api_client, pdf_file):
    """When create_batch itself fails, batch status is not updated (no batch exists)."""
    with (
        patch.dict(
            os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-batches-table"}
        ),
        patch("documentai_api.utils.uploads.filetype.guess_mime", return_value="application/pdf"),
        patch("documentai_api.app_batch.create_batch") as mock_create,
        patch("documentai_api.app_batch.update_batch_status") as mock_update_status,
        patch("documentai_api.app_batch.get_batch", return_value=None),
    ):
        mock_create.side_effect = Exception("DDB write failed")

        files = [("files", pdf_file("doc1.pdf"))]
        response = api_client.post("/v1/documents/batch", files=files)

    assert response.status_code == 500
    # update_batch_status should NOT be called since get_batch returns None
    mock_update_status.assert_not_called()


def test_get_batch_status_is_classified_vs_is_completed(api_client):
    """NOT_IMPLEMENTED is terminal (is_classified) but not completed (is_completed).

    Lazy completion should trigger (all terminal) but the completed count
    should not include NOT_IMPLEMENTED jobs.
    """
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
            {"fileName": "doc2.pdf", "jobId": "job-2", "processStatus": "not_implemented"},
            {"fileName": "doc3.pdf", "jobId": "job-3", "processStatus": "not_sampled"},
        ]

        response = api_client.get("/v1/batches/test-batch")

        assert response.status_code == 200
        data = response.json()
        # All jobs are terminal (is_classified) so lazy completion triggers
        mock_update.assert_called_once()
        # Only "success" counts as completed - not_implemented and not_sampled do not
        assert data["completed"] == 1
        # All jobs are terminal so inProgress is 0
        assert data["inProgress"] == 0


def test_batch_upload_trace_id_generated(api_client, pdf_file):
    """Response includes a generated X-Trace-ID when none is provided."""
    import uuid

    with (
        patch.dict(
            os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-batches-table"}
        ),
        patch("documentai_api.utils.uploads.filetype.guess_mime", return_value="application/pdf"),
        patch("documentai_api.app_batch.upload_document_for_processing", new_callable=AsyncMock),
        patch("documentai_api.app_batch.insert_minimal_ddb_record"),
        patch("documentai_api.app_batch.create_batch", return_value="2026-03-02T20:00:00Z"),
        patch("documentai_api.app_batch.update_batch_status"),
        patch(
            "documentai_api.app_batch.get_batch",
            return_value={"batchId": "test-batch", "createdAt": "2026-03-02T20:00:00Z"},
        ),
    ):
        files = [("files", pdf_file("doc1.pdf"))]
        response = api_client.post("/v1/documents/batch", files=files)

    assert response.status_code == 200
    trace_id = response.headers.get("X-Trace-ID")
    assert trace_id is not None
    uuid.UUID(trace_id)  # valid UUID


def test_batch_upload_trace_id_echoed(api_client, pdf_file):
    """Client-supplied X-Trace-ID is echoed unchanged in response."""
    with (
        patch.dict(
            os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-batches-table"}
        ),
        patch("documentai_api.utils.uploads.filetype.guess_mime", return_value="application/pdf"),
        patch("documentai_api.app_batch.upload_document_for_processing", new_callable=AsyncMock),
        patch("documentai_api.app_batch.insert_minimal_ddb_record"),
        patch("documentai_api.app_batch.create_batch", return_value="2026-03-02T20:00:00Z"),
        patch("documentai_api.app_batch.update_batch_status"),
        patch(
            "documentai_api.app_batch.get_batch",
            return_value={"batchId": "test-batch", "createdAt": "2026-03-02T20:00:00Z"},
        ),
    ):
        files = [("files", pdf_file("doc1.pdf"))]
        response = api_client.post(
            "/v1/documents/batch", files=files, headers={"X-Trace-ID": "my-custom-trace"}
        )

    assert response.status_code == 200
    assert response.headers.get("X-Trace-ID") == "my-custom-trace"


def test_batch_upload_tenant_propagation(api_client, pdf_file):
    """Tenant ID and client name are passed to create_batch and insert_minimal_ddb_record."""
    with (
        patch.dict(
            os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-batches-table"}
        ),
        patch("documentai_api.utils.uploads.filetype.guess_mime", return_value="application/pdf"),
        patch("documentai_api.app_batch.upload_document_for_processing", new_callable=AsyncMock),
        patch("documentai_api.app_batch.insert_minimal_ddb_record") as mock_insert,
        patch(
            "documentai_api.app_batch.create_batch", return_value="2026-03-02T20:00:00Z"
        ) as mock_create,
        patch("documentai_api.app_batch.update_batch_status"),
        patch(
            "documentai_api.app_batch.get_batch",
            return_value={"batchId": "test-batch", "createdAt": "2026-03-02T20:00:00Z"},
        ),
    ):
        files = [("files", pdf_file("doc1.pdf"))]
        response = api_client.post("/v1/documents/batch", files=files)

    assert response.status_code == 200
    # create_batch receives tenant info
    create_kwargs = mock_create.call_args.kwargs
    assert create_kwargs["tenant_id"] == "test-tenant"
    assert create_kwargs["api_key_name"] == "test-client"
    # insert_minimal_ddb_record receives tenant info
    record = mock_insert.call_args[0][0]
    assert record.tenant_id == "test-tenant"
    assert record.api_key_name == "test-client"


def test_batch_upload_uploads_under_tenant_prefix(api_client, pdf_file):
    """Each batch file is written to S3 under the caller's tenant prefix."""
    with (
        patch.dict(
            os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-batches-table"}
        ),
        patch("documentai_api.utils.uploads.filetype.guess_mime", return_value="application/pdf"),
        patch(
            "documentai_api.app_batch.upload_document_for_processing", new_callable=AsyncMock
        ) as mock_upload,
        patch("documentai_api.app_batch.insert_minimal_ddb_record"),
        patch("documentai_api.app_batch.create_batch", return_value="2026-03-02T20:00:00Z"),
        patch("documentai_api.app_batch.update_batch_status"),
        patch(
            "documentai_api.app_batch.get_batch",
            return_value={"batchId": "test-batch", "createdAt": "2026-03-02T20:00:00Z"},
        ),
    ):
        files = [("files", pdf_file("doc1.pdf"))]
        response = api_client.post("/v1/documents/batch", files=files)

    assert response.status_code == 200
    dest_path = mock_upload.call_args.kwargs["dest_path"]
    assert "/test-tenant/" in dest_path


def test_batch_upload_category_propagation(api_client, pdf_file):
    """Category is passed through to create_batch and insert_minimal_ddb_record."""
    with (
        patch.dict(
            os.environ, {EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME: "test-batches-table"}
        ),
        patch("documentai_api.utils.uploads.filetype.guess_mime", return_value="application/pdf"),
        patch("documentai_api.app_batch.upload_document_for_processing", new_callable=AsyncMock),
        patch("documentai_api.app_batch.insert_minimal_ddb_record") as mock_insert,
        patch(
            "documentai_api.app_batch.create_batch", return_value="2026-03-02T20:00:00Z"
        ) as mock_create,
        patch("documentai_api.app_batch.update_batch_status"),
        patch(
            "documentai_api.app_batch.get_batch",
            return_value={"batchId": "test-batch", "createdAt": "2026-03-02T20:00:00Z"},
        ),
    ):
        files = [("files", pdf_file("doc1.pdf"))]
        data = {"category": "income"}
        response = api_client.post("/v1/documents/batch", files=files, data=data)

    assert response.status_code == 200
    # create_batch receives category
    from documentai_api.config.constants import DocumentCategory

    create_kwargs = mock_create.call_args.kwargs
    assert create_kwargs.get("category") == DocumentCategory.INCOME or (
        mock_create.call_args[0][2] == DocumentCategory.INCOME
    )
    # insert_minimal_ddb_record receives category
    record = mock_insert.call_args[0][0]
    assert record.category == DocumentCategory.INCOME


# =============================================================================
# End-to-end integration test (moto DDB + mocked S3 upload)
# =============================================================================


@pytest.mark.integration
def test_post_then_get_batch_end_to_end(
    api_client, pdf_file, ddb_batches_table, ddb_doc_metadata_table, mocker
):
    """POST /v1/documents/batch → GET /v1/batches/{id} round-trip against real DDB."""
    from documentai_api.config.constants import BatchStatus
    from documentai_api.schemas.document_batches import DocumentBatches
    from documentai_api.utils.ddb import get_batch, query_jobs_by_batch_id

    mocker.patch("documentai_api.utils.uploads.filetype.guess_mime", return_value="application/pdf")
    mocker.patch("documentai_api.app_batch.upload_document_for_processing", new_callable=AsyncMock)

    files = [
        ("files", pdf_file("doc1.pdf")),
        ("files", pdf_file("doc2.pdf")),
    ]
    data = {"category": "income"}

    # POST batch
    post_response = api_client.post("/v1/documents/batch", files=files, data=data)
    assert post_response.status_code == 200

    post_data = post_response.json()
    batch_id = post_data["batchId"]
    assert post_data["totalFiles"] == 2
    assert len(post_data["jobs"]) == 2

    # Verify batch record in DDB has tenant info
    batch_record = get_batch(batch_id)
    assert batch_record is not None
    assert batch_record[DocumentBatches.TENANT_ID] == "test-tenant"
    assert batch_record[DocumentBatches.API_KEY_NAME] == "test-client"
    assert batch_record[DocumentBatches.BATCH_STATUS] == BatchStatus.PROCESSING.value

    # Verify job records in DDB via GSI
    job_records = query_jobs_by_batch_id(batch_id)
    assert len(job_records) == 2
    for record in job_records:
        assert record["tenantId"] == "test-tenant"
        assert record["apiKeyName"] == "test-client"
        assert record["batchId"] == batch_id

    # GET batch status
    get_response = api_client.get(f"/v1/batches/{batch_id}")
    assert get_response.status_code == 200

    get_data = get_response.json()
    assert get_data["batchId"] == batch_id
    assert get_data["totalJobs"] == 2
    assert get_data["batchStatus"] == BatchStatus.PROCESSING.value
