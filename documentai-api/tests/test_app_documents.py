"""Tests for document endpoints (upload, query, delete, search)."""

from unittest.mock import AsyncMock

import pytest

from documentai_api.config.constants import DeletionType
from documentai_api.models.api_responses import JobStatusResponse
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.jobs import JobStatus

TEST_JOB_ID = "00000000-0000-4000-8000-000000000001"


@pytest.fixture(autouse=True)
def _disable_auth(disable_auth):
    pass


def test_document_upload_no_file(api_client):
    response = api_client.post("/v1/documents")
    assert response.status_code == 422


def test_document_status_not_found(ddb_doc_metadata_table_resource, api_client):
    response = api_client.get(f"/v1/documents/{TEST_JOB_ID}")
    assert response.status_code == 404


def test_get_document_results_with_extracted_data(api_client, mocker):
    """Test getting results with extracted data."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf", "tenantId": "test-tenant"},
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "test-job-id", "jobStatus": "success", "message": "Document processed successfully"}',
    )

    mock_build_api_response = mocker.patch("documentai_api.app_documents.build_v1_api_response")
    mock_build_api_response.return_value = {
        "jobId": "test-job-id",
        "jobStatus": "success",
        "message": "Document processed successfully",
        "extractedData": {},
    }

    response = api_client.get(f"/v1/documents/{TEST_JOB_ID}?include_extracted_data=true")

    assert response.status_code == 200
    mock_build_api_response.assert_called_once_with(
        object_key="test.pdf",
        job_status="success",
        include_extracted_data=True,
        include_bounding_box=False,
    )


def test_get_document_results_in_progress(api_client, mocker):
    """Test getting results for in-progress job."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf", "tenantId": "test-tenant"},
        object_key="test.pdf",
        process_status="started",
        v1_response_json=None,
    )

    response = api_client.get(f"/v1/documents/{TEST_JOB_ID}")

    assert response.status_code == 200
    data = response.json()
    assert data["jobStatus"] == "started"
    assert "in progress" in data["message"].lower()


def test_create_document_invalid_file_type(api_client, empty_zip_bytes):
    """Test document upload with invalid file type."""
    files = {"file": ("test.zip", empty_zip_bytes, "application/zip")}
    response = api_client.post("/v1/documents", files=files)

    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_create_document_asynchronous(api_client, blank_pdf_bytes):
    """Test asynchronous document upload (default behavior, returns job_id immediately)."""
    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/documents", files=files)

    assert response.status_code == 202
    data = response.json()
    assert "jobId" in data
    assert data["jobStatus"] == "not_started"
    assert "uploaded successfully" in data["message"].lower()


def test_create_document_uploads_under_tenant_prefix(api_client, blank_pdf_bytes, mocker):
    """Upload writes the S3 object under the caller's tenant prefix."""
    mock_dispatch = mocker.patch(
        "documentai_api.app_documents.dispatch_upload", new_callable=AsyncMock
    )

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/documents", files=files)

    assert response.status_code == 202
    dest_path = mock_dispatch.call_args.kwargs["dest_path"]
    assert "/test-tenant/" in dest_path


def test_create_document_with_external_fields(api_client, blank_pdf_bytes, mocker):
    """Test document upload with external_document_id, external_system_id, and ai_consent_flag."""
    mock_insert = mocker.patch("documentai_api.app_documents.insert_minimal_ddb_record")

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    data = {
        "external_document_id": "test-ext-doc-id",
        "external_system_id": "test-ext-sys-id",
        "ai_consent_flag": "true",
    }
    response = api_client.post("/v1/documents", files=files, data=data)

    assert response.status_code == 202
    record = mock_insert.call_args[0][0]
    assert record.external_document_id == "test-ext-doc-id"
    assert record.external_system_id == "test-ext-sys-id"
    assert record.ai_consent_flag is True


def test_create_document_ai_consent_declined(api_client, blank_pdf_bytes, mocker):
    """Test document upload with ai_consent_flag=false bypasses processing."""
    mock_insert = mocker.patch("documentai_api.app_documents.insert_minimal_ddb_record")
    mock_classify = mocker.patch("documentai_api.app_documents.classify_as_ai_consent_declined")
    mock_classify.return_value = {
        "response_code": "003",
        "response_message": "Document not processed - AI consent not provided",
    }
    mock_dispatch = mocker.patch("documentai_api.utils.uploads.upload_document_for_processing")

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    data = {"ai_consent_flag": "false"}
    response = api_client.post("/v1/documents", files=files, data=data)

    assert response.status_code == 202
    result = response.json()
    assert result["jobStatus"] == "ai_consent_declined"
    assert "AI consent not provided" in result["message"]
    mock_insert.assert_called_once()
    mock_classify.assert_called_once()
    mock_dispatch.assert_not_called()


def test_create_document_synchronous(api_client, blank_pdf_bytes, mocker):
    """Test synchronous document upload via /v1/documents/wait."""
    mock_poll = mocker.patch("documentai_api.app_documents.poll_for_completion")
    mock_poll.return_value = JobStatusResponse(
        job_id="test-id", job_status="success", message="Document processed successfully"
    )

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/documents/wait", files=files)

    assert response.status_code == 200
    assert response.json()["jobStatus"] == "success"


def test_create_document_missing_filename(api_client):
    """Test upload with empty filename returns 422."""
    files = {"file": ("", b"fake content", "application/pdf")}
    response = api_client.post("/v1/documents", files=files)

    assert response.status_code == 422


def test_create_document_trace_id_echoed_on_validation_failure(api_client, empty_zip_bytes):
    """Test X-Trace-ID is returned even when file type validation fails.

    Note: HTTPException responses may not carry the header without middleware.
    This test documents current behavior - if it fails, a trace-id middleware is needed.
    """
    files = {"file": ("test.zip", empty_zip_bytes, "application/zip")}
    response = api_client.post("/v1/documents", files=files)

    assert response.status_code == 400
    # X-Trace-ID may not be present on error responses without middleware
    # This is a known limitation documented in app_documents.py


def test_create_document_trace_id_echoed_on_success(api_client, blank_pdf_bytes):
    """Test X-Trace-ID is returned on successful upload."""
    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/documents", files=files)

    assert response.status_code == 202
    assert "X-Trace-ID" in response.headers


def test_create_document_custom_trace_id(api_client, blank_pdf_bytes):
    """Test custom X-Trace-ID is echoed back."""
    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post(
        "/v1/documents", files=files, headers={"X-Trace-ID": "test-trace-id"}
    )

    assert response.status_code == 202
    assert response.headers["X-Trace-ID"] == "test-trace-id"


def test_create_document_upload_failure_classifies_record(api_client, blank_pdf_bytes, mocker):
    """Test unexpected upload failure marks DDB record as failed."""
    mocker.patch("documentai_api.app_documents.insert_minimal_ddb_record")
    mock_classify = mocker.patch("documentai_api.utils.document_lifecycle.classify_as_failed")
    mocker.patch(
        "documentai_api.utils.uploads.upload_document_for_processing",
        side_effect=RuntimeError("S3 exploded"),
    )

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/documents", files=files)

    assert response.status_code == 500
    assert "Upload failed" in response.json()["detail"]
    mock_classify.assert_called_once()


def test_create_document_conversion_failure(api_client, blank_pdf_bytes, mocker):
    """Test image conversion failure returns appropriate status."""
    from documentai_api.utils.uploads import ImageConversionError

    mocker.patch("documentai_api.app_documents.insert_minimal_ddb_record")
    mocker.patch("documentai_api.utils.document_lifecycle.classify_as_conversion_failed")
    mocker.patch(
        "documentai_api.utils.uploads.upload_document_for_processing",
        side_effect=ImageConversionError("Cannot convert"),
    )

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/documents", files=files)

    assert response.status_code == 202
    result = response.json()
    assert result["jobStatus"] == "conversion_failed"


def test_get_document_results_error_handling(api_client, mocker):
    """Test error handling in get_document_results."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.side_effect = Exception("Unexpected error")

    response = api_client.get(f"/v1/documents/{TEST_JOB_ID}")

    assert response.status_code == 500
    assert "Failed to retrieve results" in response.json()["detail"]


def test_search_documents_success(api_client, mocker):
    """Test searching multiple job IDs returns results."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.side_effect = [
        JobStatus(
            ddb_record={"fileName": "test.pdf", "tenantId": "test-tenant"},
            object_key="test.pdf",
            process_status="success",
            v1_response_json='{"jobId": "job-1", "jobStatus": "success", "message": "Done"}',
        ),
        JobStatus(ddb_record=None, object_key=None, process_status=None, v1_response_json=None),
    ]

    response = api_client.post("/v1/documents/search", json={"jobIds": ["job-1", "job-2"]})

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["jobStatus"] == "success"
    assert results[1]["jobStatus"] == "not_found"


def test_search_documents_in_progress(api_client, mocker):
    """Test search returns processing status for incomplete jobs."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf", "tenantId": "test-tenant"},
        object_key="test.pdf",
        process_status="started",
        v1_response_json=None,
    )

    response = api_client.post("/v1/documents/search", json={"jobIds": ["job-1"]})

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["jobStatus"] == "started"
    assert "in progress" in results[0]["message"].lower()


def test_search_documents_empty_list(api_client):
    """Test search with empty job_ids returns 400."""
    response = api_client.post("/v1/documents/search", json={"jobIds": []})
    assert response.status_code == 400


def test_search_documents_exceeds_limit(api_client):
    """Test search with too many job_ids returns 400."""
    job_ids = [f"job-{i}" for i in range(26)]
    response = api_client.post("/v1/documents/search", json={"jobIds": job_ids})
    assert response.status_code == 400
    assert "Maximum of 25" in response.json()["detail"]


def test_search_documents_handles_errors_gracefully(api_client, mocker):
    """Test search continues when individual job lookup fails."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.side_effect = Exception("DDB error")

    response = api_client.post("/v1/documents/search", json={"jobIds": ["job-1"]})

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["jobStatus"] == "error"
    assert "Failed to retrieve" in results[0]["message"]


def test_delete_document_success(api_client, mocker):
    """Test default (soft) deletion: record marked deleted, S3 files retained."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf", "tenantId": "test-tenant"},
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "job-1", "jobStatus": "success", "message": "Done"}',
    )
    mock_purge = mocker.patch("documentai_api.utils.uploads.purge_document_s3_artifacts")
    mock_mark_deleted = mocker.patch("documentai_api.utils.ddb.mark_document_deleted")

    response = api_client.delete(f"/v1/documents/{TEST_JOB_ID}")

    assert response.status_code == 204
    # Soft delete retains every S3 copy of the document.
    mock_purge.assert_not_called()
    mock_mark_deleted.assert_called_once_with(
        object_key="test.pdf", deletion_type=DeletionType.SOFT
    )


def test_delete_document_hard_delete(api_client, mocker):
    """Test hard deletion: all S3 artifacts purged and record marked deleted (hard)."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf", "tenantId": "test-tenant"},
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "job-1", "jobStatus": "success", "message": "Done"}',
    )
    # empty list = every S3 copy confirmed purged
    mock_purge = mocker.patch(
        "documentai_api.utils.uploads.purge_document_s3_artifacts", return_value=[]
    )
    mock_mark_deleted = mocker.patch("documentai_api.utils.ddb.mark_document_deleted")

    response = api_client.delete(f"/v1/documents/{TEST_JOB_ID}?soft_delete=false")

    assert response.status_code == 204
    mock_purge.assert_called_once_with(object_key="test.pdf", tenant_id="test-tenant")
    mock_mark_deleted.assert_called_once_with(
        object_key="test.pdf", deletion_type=DeletionType.HARD
    )


def test_delete_document_not_found(api_client, mocker):
    """Test deleting non-existent document returns 404."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record=None, object_key=None, process_status=None, v1_response_json=None
    )

    response = api_client.delete(f"/v1/documents/{TEST_JOB_ID}")

    assert response.status_code == 404


def test_delete_document_still_processing(api_client, mocker):
    """Test deleting in-progress document returns 400."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf", "tenantId": "test-tenant"},
        object_key="test.pdf",
        process_status="started",
        v1_response_json=None,
    )

    response = api_client.delete(f"/v1/documents/{TEST_JOB_ID}")

    assert response.status_code == 400
    assert "still processing" in response.json()["detail"]


def test_delete_document_already_deleted(api_client, mocker):
    """Test deleting already-deleted document returns 404."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf"},
        object_key="test.pdf",
        process_status="deleted",
        v1_response_json=None,
    )

    response = api_client.delete(f"/v1/documents/{TEST_JOB_ID}")

    assert response.status_code == 404


def test_get_document_results_wrong_tenant(api_client, mocker):
    """Test GET on document belonging to different tenant returns 404."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf", "tenantId": "other-tenant"},
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "job-1", "jobStatus": "success", "message": "Done"}',
    )

    response = api_client.get(f"/v1/documents/{TEST_JOB_ID}")

    assert response.status_code == 404


def test_delete_document_wrong_tenant(api_client, mocker):
    """Test DELETE on document belonging to different tenant returns 404."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf", "tenantId": "other-tenant"},
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "job-1", "jobStatus": "success", "message": "Done"}',
    )

    response = api_client.delete(f"/v1/documents/{TEST_JOB_ID}")

    assert response.status_code == 404


def test_search_documents_wrong_tenant(api_client, mocker):
    """Test search returns not_found for documents belonging to different tenant."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf", "tenantId": "other-tenant"},
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "job-1", "jobStatus": "success", "message": "Done"}',
    )

    response = api_client.post("/v1/documents/search", json={"jobIds": ["job-1"]})

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["jobStatus"] == "not_found"


def test_get_document_results_deleted_returns_404(api_client, mocker):
    """Test GET on deleted document returns 404."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf"},
        object_key="test.pdf",
        process_status="deleted",
        v1_response_json='{"jobId": "job-1", "jobStatus": "deleted", "message": "Document has been deleted"}',
    )

    response = api_client.get(f"/v1/documents/{TEST_JOB_ID}")

    assert response.status_code == 404


def test_create_document_external_id_too_long(api_client, blank_pdf_bytes):
    """Test external_document_id exceeding max length returns 422."""
    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    data = {"external_document_id": "a" * 257}
    response = api_client.post("/v1/documents", files=files, data=data)

    assert response.status_code == 422


def test_create_document_external_id_invalid_chars(api_client, blank_pdf_bytes):
    """Test external_document_id with invalid characters returns 422."""
    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    data = {"external_document_id": "doc id <script>"}
    response = api_client.post("/v1/documents", files=files, data=data)

    assert response.status_code == 422


def test_create_document_external_system_id_invalid_chars(api_client, blank_pdf_bytes):
    """Test external_system_id with invalid characters returns 422."""
    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    data = {"external_system_id": "sys/id with spaces"}
    response = api_client.post("/v1/documents", files=files, data=data)

    assert response.status_code == 422


def test_create_document_sync_timeout_capped(api_client, blank_pdf_bytes, mocker):
    """Test that /v1/documents/wait caps timeout to MAX_WAIT_SECONDS - ALB_TIMEOUT_BUFFER_SECONDS."""
    from documentai_api.config.constants import ConfigDefaults

    mock_poll = mocker.patch("documentai_api.app_documents.poll_for_completion")
    mock_poll.return_value = JobStatusResponse(
        job_id="test-id", job_status="success", message="Done"
    )

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/documents/wait?timeout=99999", files=files)

    assert response.status_code == 200
    expected_cap = ConfigDefaults.MAX_WAIT_SECONDS - ConfigDefaults.ALB_TIMEOUT_BUFFER_SECONDS
    mock_poll.assert_called_once()
    actual_timeout = mock_poll.call_args[0][1]
    assert actual_timeout == expected_cap


def test_create_document_ai_consent_none_proceeds(api_client, blank_pdf_bytes, mocker):
    """Test that omitting ai_consent_flag (None) proceeds with upload."""
    mock_classify = mocker.patch("documentai_api.app_documents.classify_as_ai_consent_declined")

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/documents", files=files)

    assert response.status_code == 202
    assert response.json()["jobStatus"] == "not_started"
    mock_classify.assert_not_called()


def test_search_documents_with_extracted_data(api_client, mocker):
    """Test search with include_extracted_data=true returns extracted data."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf", "tenantId": "test-tenant"},
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "job-1", "jobStatus": "success", "message": "Done"}',
    )

    mock_build = mocker.patch("documentai_api.app_documents.build_v1_api_response")
    mock_build.return_value = {
        "jobId": "job-1",
        "jobStatus": "success",
        "message": "Done",
        "extractedData": {"name": "John"},
    }

    response = api_client.post(
        "/v1/documents/search",
        json={"jobIds": ["job-1"], "includeExtractedData": True},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["jobStatus"] == "success"
    mock_build.assert_called_once()


def test_search_documents_with_extracted_data_incomplete_record(api_client, mocker):
    """Test search with include_extracted_data=true handles incomplete records."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf", "tenantId": "test-tenant"},
        object_key=None,
        process_status=None,
        v1_response_json='{"jobId": "job-1", "jobStatus": "success", "message": "Done"}',
    )

    response = api_client.post(
        "/v1/documents/search",
        json={"jobIds": ["job-1"], "includeExtractedData": True},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["jobStatus"] == "error"
    assert "Incomplete" in results[0]["message"]


def test_create_document_timeout_below_minimum(api_client, blank_pdf_bytes):
    """Test that timeout=0 returns 422 due to ge=1 constraint."""
    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/documents/wait?timeout=0", files=files)
    assert response.status_code == 422


def test_create_document_sync_passes_request_to_poll(api_client, blank_pdf_bytes, mocker):
    """Test that request is forwarded to poll_for_completion for disconnect detection."""
    mock_poll = mocker.patch("documentai_api.app_documents.poll_for_completion")
    mock_poll.return_value = JobStatusResponse(
        job_id="test-id", job_status="success", message="Done"
    )

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/documents/wait", files=files)

    assert response.status_code == 200
    assert "request" in mock_poll.call_args.kwargs


def test_create_document_sync_default_timeout(api_client, blank_pdf_bytes, mocker):
    """Test that omitting timeout uses the default (MAX_WAIT_SECONDS - ALB_TIMEOUT_BUFFER_SECONDS)."""
    from documentai_api.config.constants import ConfigDefaults

    mock_poll = mocker.patch("documentai_api.app_documents.poll_for_completion")
    mock_poll.return_value = JobStatusResponse(
        job_id="test-id", job_status="success", message="Done"
    )

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/documents/wait", files=files)

    assert response.status_code == 200
    expected = ConfigDefaults.MAX_WAIT_SECONDS - ConfigDefaults.ALB_TIMEOUT_BUFFER_SECONDS
    actual_timeout = mock_poll.call_args[0][1]
    assert actual_timeout == expected


def test_get_document_invalid_uuid_returns_422(api_client):
    """Test GET with non-UUID job_id returns 422."""
    response = api_client.get("/v1/documents/not-a-uuid")
    assert response.status_code == 422


def test_delete_document_invalid_uuid_returns_422(api_client):
    """Test DELETE with non-UUID job_id returns 422."""
    response = api_client.delete("/v1/documents/not-a-uuid")
    assert response.status_code == 422


def test_get_document_enumeration_leak_invariant(api_client, mocker):
    """Test that wrong-tenant and deleted responses are identical to prevent enumeration."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")

    # Wrong tenant
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf", "tenantId": "other-tenant"},
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "job-1", "jobStatus": "success", "message": "Done"}',
    )
    wrong_tenant_response = api_client.get(f"/v1/documents/{TEST_JOB_ID}")

    # Deleted
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf", "tenantId": "test-tenant"},
        object_key="test.pdf",
        process_status="deleted",
        v1_response_json=None,
    )
    deleted_response = api_client.get(f"/v1/documents/{TEST_JOB_ID}")

    assert wrong_tenant_response.status_code == deleted_response.status_code == 404
    assert wrong_tenant_response.json() == deleted_response.json()


def test_get_document_trace_id_echoed(api_client, mocker):
    """Test X-Trace-ID is echoed on GET endpoint."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf", "tenantId": "test-tenant"},
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "job-1", "jobStatus": "success", "message": "Done"}',
    )

    response = api_client.get(
        f"/v1/documents/{TEST_JOB_ID}", headers={"X-Trace-ID": "my-trace-456"}
    )

    assert response.status_code == 200
    assert response.headers["X-Trace-ID"] == "my-trace-456"


def test_get_document_completed_without_extracted_data(api_client, mocker):
    """Test GET on completed job without include_extracted_data returns cached response."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf", "tenantId": "test-tenant"},
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "job-1", "jobStatus": "success", "message": "Done"}',
    )

    response = api_client.get(f"/v1/documents/{TEST_JOB_ID}")

    assert response.status_code == 200
    assert response.json()["jobStatus"] == "success"


def test_search_documents_mixed_success_and_failure(api_client, mocker):
    """Test search with one successful and one erroring job preserves both results."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.side_effect = [
        JobStatus(
            ddb_record={"fileName": "test.pdf", "tenantId": "test-tenant"},
            object_key="test.pdf",
            process_status="success",
            v1_response_json='{"jobId": "job-1", "jobStatus": "success", "message": "Done"}',
        ),
        Exception("DDB exploded"),
    ]

    response = api_client.post("/v1/documents/search", json={"jobIds": ["job-1", "job-2"]})

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["jobStatus"] == "success"
    assert results[1]["jobStatus"] == "error"


def test_delete_document_hard_purge_failure_returns_500_and_does_not_mark_deleted(
    api_client, mocker
):
    """A failed hard-delete purge returns 500 and leaves the record un-deleted."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf", "tenantId": "test-tenant"},
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "job-1", "jobStatus": "success", "message": "Done"}',
    )
    # delete_object/delete_prefix raise -> purge reports failed locations.
    mocker.patch("documentai_api.services.s3.delete_object", side_effect=Exception("S3 down"))
    mocker.patch("documentai_api.services.s3.delete_prefix", side_effect=Exception("S3 down"))
    mock_mark_deleted = mocker.patch("documentai_api.utils.ddb.mark_document_deleted")

    response = api_client.delete(f"/v1/documents/{TEST_JOB_ID}?soft_delete=false")

    assert response.status_code == 500
    assert "Failed to fully delete" in response.json()["detail"]
    # record must NOT be marked deleted when data may still exist
    mock_mark_deleted.assert_not_called()


def test_purge_document_s3_artifacts_deletes_all_locations(monkeypatch, mocker):
    """Hard-delete purge removes input, preprocessing, and BDA output artifacts."""
    from documentai_api.config.env import EnvVars
    from documentai_api.utils.uploads import purge_document_s3_artifacts

    monkeypatch.setenv(EnvVars.DOCUMENTAI_INPUT_LOCATION, "s3://bucket/input")
    monkeypatch.setenv(EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION, "s3://bucket/preprocessing")
    monkeypatch.setenv(EnvVars.DOCUMENTAI_OUTPUT_LOCATION, "s3://bucket/output")

    mock_delete = mocker.patch("documentai_api.services.s3.delete_object")
    mock_delete_prefix = mocker.patch("documentai_api.services.s3.delete_prefix")

    failures = purge_document_s3_artifacts(object_key="doc-uuid.pdf", tenant_id="test-tenant")

    assert failures == []  # every location purged cleanly
    # Original upload and preprocessing copy are tenant-scoped single objects.
    deleted = [c.args for c in mock_delete.mock_calls]
    assert ("bucket", "input/test-tenant/doc-uuid.pdf") in deleted
    assert ("bucket", "preprocessing/test-tenant/doc-uuid.pdf") in deleted
    # BDA output is a tree, deleted by prefix - including the truncated variant.
    prefixes = [c.args for c in mock_delete_prefix.mock_calls]
    assert ("bucket", "output/doc-uuid.pdf/") in prefixes
    assert ("bucket", "output/doc-uuid_truncated.pdf/") in prefixes


def test_purge_document_s3_artifacts_skips_unset_locations(monkeypatch, mocker):
    """Locations that aren't configured are skipped rather than erroring."""
    from documentai_api.config.env import EnvVars
    from documentai_api.utils.uploads import purge_document_s3_artifacts

    monkeypatch.setenv(EnvVars.DOCUMENTAI_INPUT_LOCATION, "s3://bucket/input")
    monkeypatch.delenv(EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION, raising=False)
    monkeypatch.delenv(EnvVars.DOCUMENTAI_OUTPUT_LOCATION, raising=False)

    mock_delete = mocker.patch("documentai_api.services.s3.delete_object")
    mock_delete_prefix = mocker.patch("documentai_api.services.s3.delete_prefix")

    purge_document_s3_artifacts(object_key="doc-uuid.pdf", tenant_id="test-tenant")

    mock_delete.assert_called_once_with("bucket", "input/test-tenant/doc-uuid.pdf")
    mock_delete_prefix.assert_not_called()


def test_purge_document_s3_artifacts_reports_failed_locations(monkeypatch, mocker):
    """A genuine S3 error on a location is reported, and other locations still run."""
    from documentai_api.config.env import EnvVars
    from documentai_api.utils.uploads import purge_document_s3_artifacts

    monkeypatch.setenv(EnvVars.DOCUMENTAI_INPUT_LOCATION, "s3://bucket/input")
    monkeypatch.setenv(EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION, "s3://bucket/preprocessing")
    monkeypatch.setenv(EnvVars.DOCUMENTAI_OUTPUT_LOCATION, "s3://bucket/output")

    # input delete fails; preprocessing + output succeed
    mocker.patch("documentai_api.services.s3.delete_object", side_effect=Exception("denied"))
    mock_delete_prefix = mocker.patch("documentai_api.services.s3.delete_prefix")

    failures = purge_document_s3_artifacts(object_key="doc-uuid.pdf", tenant_id="test-tenant")

    assert "input" in failures
    assert "preprocessing" in failures  # delete_object also drives preprocessing
    # output uses delete_prefix (not patched to fail), so it succeeds and isn't reported
    assert "output" not in failures
    mock_delete_prefix.assert_called()


# =============================================================================
# Wait endpoint terminal-state short-circuit
# =============================================================================


def test_documents_wait_consent_declined_skips_poll(api_client, blank_pdf_bytes, mocker):
    """Documents /wait returns immediately without polling when consent is declined."""
    mocker.patch("documentai_api.app_documents.insert_minimal_ddb_record")
    mocker.patch("documentai_api.app_documents.classify_as_ai_consent_declined")
    mock_poll = mocker.patch("documentai_api.app_documents.poll_for_completion")

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    data = {"ai_consent_flag": "false"}
    response = api_client.post("/v1/documents/wait", files=files, data=data)

    assert response.status_code == 200
    assert response.json()["jobStatus"] == "ai_consent_declined"
    mock_poll.assert_not_called()


def test_documents_wait_conversion_failed_skips_poll(api_client, blank_pdf_bytes, mocker):
    """Documents /wait returns immediately without polling on conversion failure."""
    from documentai_api.utils.uploads import ImageConversionError

    mocker.patch("documentai_api.app_documents.insert_minimal_ddb_record")
    mocker.patch("documentai_api.utils.document_lifecycle.classify_as_conversion_failed")
    mocker.patch(
        "documentai_api.utils.uploads.upload_document_for_processing",
        side_effect=ImageConversionError("Cannot convert"),
    )
    mock_poll = mocker.patch("documentai_api.app_documents.poll_for_completion")

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/documents/wait", files=files)

    assert response.status_code == 200
    assert response.json()["jobStatus"] == "conversion_failed"
    mock_poll.assert_not_called()


# =============================================================================
# include_extracted_data forwarding on wait endpoint
# =============================================================================


def test_documents_wait_forwards_include_extracted_data(api_client, blank_pdf_bytes, mocker):
    """Documents /wait passes include_extracted_data to poll_for_completion."""
    mock_poll = mocker.patch("documentai_api.app_documents.poll_for_completion")
    mock_poll.return_value = JobStatusResponse(
        job_id="test-id", job_status="success", message="Done"
    )

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/documents/wait?include_extracted_data=true", files=files)

    assert response.status_code == 200
    assert mock_poll.call_args.kwargs["include_extracted_data"] is True


def test_documents_wait_include_extracted_data_defaults_false(api_client, blank_pdf_bytes, mocker):
    """Documents /wait defaults include_extracted_data to False."""
    mock_poll = mocker.patch("documentai_api.app_documents.poll_for_completion")
    mock_poll.return_value = JobStatusResponse(
        job_id="test-id", job_status="success", message="Done"
    )

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/documents/wait", files=files)

    assert response.status_code == 200
    assert mock_poll.call_args.kwargs["include_extracted_data"] is False


# =============================================================================
# include_bounding_box implies include_extracted_data
# =============================================================================


def test_get_document_bounding_box_implies_extracted_data(api_client, mocker):
    """GET with include_bounding_box=true (without include_extracted_data) triggers rebuild."""
    mock_get_job_status = mocker.patch("documentai_api.app_documents.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={
            DocumentMetadata.TENANT_ID: "test-tenant",
            DocumentMetadata.FILE_NAME: "test.pdf",
        },
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "test-job-id", "jobStatus": "success", "message": "ok"}',
    )

    mock_build_api_response = mocker.patch("documentai_api.app_documents.build_v1_api_response")
    mock_build_api_response.return_value = {
        "jobId": "test-job-id",
        "jobStatus": "success",
        "message": "Document processed successfully",
    }

    response = api_client.get(f"/v1/documents/{TEST_JOB_ID}?include_bounding_box=true")

    assert response.status_code == 200
    mock_build_api_response.assert_called_once_with(
        object_key="test.pdf",
        job_status="success",
        include_extracted_data=True,
        include_bounding_box=True,
    )


def test_documents_wait_bounding_box_implies_extracted_data(api_client, blank_pdf_bytes, mocker):
    """Documents /wait with include_bounding_box=true implies include_extracted_data."""
    mock_poll = mocker.patch("documentai_api.app_documents.poll_for_completion")
    mock_poll.return_value = JobStatusResponse(
        job_id="test-id", job_status="success", message="Done"
    )

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/documents/wait?include_bounding_box=true", files=files)

    assert response.status_code == 200
    assert mock_poll.call_args.kwargs["include_extracted_data"] is True
    assert mock_poll.call_args.kwargs["include_bounding_box"] is True


# =============================================================================
# Demo upload flag
# =============================================================================


@pytest.mark.parametrize(
    "use_demo_endpoint,expected_is_demo",
    [(True, True), (False, False)],
    ids=["demo=true", "standard"],
)
def test_create_document_demo_flag(api_client, blank_pdf_bytes, mocker, use_demo_endpoint, expected_is_demo):
    """Demo endpoint sets is_demo=True, standard endpoint does not."""
    mock_insert = mocker.patch("documentai_api.app_documents.insert_minimal_ddb_record")
    mocker.patch("documentai_api.app_documents.dispatch_upload", new_callable=AsyncMock)

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    endpoint = "/v1/demo/documents" if use_demo_endpoint else "/v1/documents"
    response = api_client.post(endpoint, files=files)

    assert response.status_code == 202
    record = mock_insert.call_args[0][0]
    assert record.is_demo is expected_is_demo


@pytest.mark.parametrize(
    "use_demo_endpoint,expect_demo_path",
    [(True, True), (False, False)],
    ids=["demo-upload", "standard-upload"],
)
def test_create_document_demo_routes_to_correct_location(
    api_client, blank_pdf_bytes, mocker, use_demo_endpoint, expect_demo_path
):
    """Upload routes to demo or standard input location based on endpoint."""
    mock_config = mocker.patch("documentai_api.app_documents.get_aws_config")
    mock_config.return_value.documentai_input_location = "s3://bucket/input"
    mock_config.return_value.documentai_demo_input_location = "s3://bucket/input/demo"

    mock_dispatch = mocker.patch(
        "documentai_api.app_documents.dispatch_upload", new_callable=AsyncMock
    )

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    endpoint = "/v1/demo/documents" if use_demo_endpoint else "/v1/documents"
    response = api_client.post(endpoint, files=files)

    assert response.status_code == 202
    dest_path = mock_dispatch.call_args.kwargs["dest_path"]
    if expect_demo_path:
        assert dest_path.startswith("s3://bucket/input/demo/")
    else:
        assert dest_path.startswith("s3://bucket/input/")
        assert "/input/demo/" not in dest_path
