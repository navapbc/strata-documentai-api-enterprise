import pytest
from fastapi import HTTPException

from documentai_api.app import (
    JobStatus,
    _get_job_status,
    get_v1_document_processing_results,
    upload_document_for_processing,
)
from documentai_api.models.api_responses import JobStatusResponse


@pytest.fixture(autouse=True)
def _disable_auth(disable_auth):
    pass


def test_health(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"message": "healthy"}


def test_config(api_client):
    response = api_client.get("/config")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "supportedFileTypes" in data


def test_config_endpoints_discovered(api_client):
    response = api_client.get("/config")
    endpoints = response.json()["endpoints"]

    # known API endpoints should be present
    assert "getExtractionRules" in endpoints
    assert "getSchemaList" in endpoints
    assert "postUpload" in endpoints
    assert "postUploadSyncronous" in endpoints

    # excluded routes should not appear
    excluded_paths = set(endpoints.values())
    assert "/health" not in excluded_paths
    assert "/config" not in excluded_paths


def test_root(api_client):
    response = api_client.get("/")
    assert response.status_code == 200
    assert "status" in response.json()


def test_document_upload_no_file(api_client):
    response = api_client.post("/v1/documents")
    assert response.status_code == 422


def test_document_status_not_found(ddb_doc_metadata_table_resource, api_client):
    response = api_client.get("/v1/documents/fake-job-id")
    assert response.status_code == 404


def test_get_job_status_found(ddb_doc_metadata_table):
    """Test _get_job_status when job exists."""
    from documentai_api.config.constants import ProcessStatus
    from documentai_api.schemas.document_metadata import DocumentMetadata

    ddb_record = {
        DocumentMetadata.FILE_NAME: "test.pdf",
        DocumentMetadata.JOB_ID: "test-job-id",
        DocumentMetadata.PROCESS_STATUS: ProcessStatus.SUCCESS.value,
        DocumentMetadata.V1_API_RESPONSE_JSON: '{"jobStatus": "success"}',
    }

    ddb_doc_metadata_table.put_item(Item=ddb_record)

    result = _get_job_status("test-job-id")

    assert result.object_key == "test.pdf"
    assert result.process_status == "success"
    assert result.v1_response_json == '{"jobStatus": "success"}'


def test_get_job_status_not_found(ddb_doc_metadata_table):
    """Test _get_job_status when job doesn't exist."""
    result = _get_job_status("test-job-id")

    assert result.ddb_record is None
    assert result.object_key is None
    assert result.process_status is None
    assert result.v1_response_json is None


@pytest.mark.asyncio
async def test_upload_document_for_processing_success(
    runtime_required_env, blank_pdf_file, s3_bucket, mocker
):
    """Test successful document upload."""
    from documentai_api.config.constants import DocumentCategory

    await upload_document_for_processing(
        src_file=blank_pdf_file.open("rb"),
        dest_path=f"s3://{s3_bucket.name}/input/test-unique.pdf",
        original_file_name="test.pdf",
        content_type="application/pdf",
        user_provided_document_category=DocumentCategory.INCOME,
        job_id="test-job-id",
        trace_id="test-trace-id",
    )

    uploaded_file_in_s3 = s3_bucket.Object("input/test-unique.pdf")
    assert uploaded_file_in_s3.content_type == "application/pdf"


@pytest.mark.asyncio
async def test_get_v1_document_processing_results_success(mocker):
    """Test polling returns results when processing completes."""
    mock_get_job_status = mocker.patch("documentai_api.app._get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf"},
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "test-job-id", "jobStatus": "success", "message": "Document processed successfully"}',
    )

    result = await get_v1_document_processing_results("test-job-id", timeout=10)

    assert result.job_status == "success"


@pytest.mark.asyncio
async def test_get_v1_document_processing_results_timeout(mocker):
    """Test polling timeout with object_key."""
    mock_get_job_status = mocker.patch("documentai_api.app._get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf"},
        object_key="test.pdf",
        process_status="started",
        v1_response_json=None,
    )

    mock_classify_as_failed = mocker.patch("documentai_api.app.classify_as_failed")

    result = await get_v1_document_processing_results("test-job-id", timeout=1)

    mock_classify_as_failed.assert_called_once()
    assert result.job_status == "failed"
    assert "timeout" in result.message.lower()


@pytest.mark.asyncio
async def test_get_v1_document_processing_results_timeout_no_object_key(mocker):
    """Test polling timeout without object_key."""
    mock_get_job_status = mocker.patch("documentai_api.app._get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record=None,
        object_key=None,
        process_status=None,
        v1_response_json=None,
    )

    result = await get_v1_document_processing_results("test-job-id", timeout=1)

    assert result.job_status == "failed"
    assert "timeout" in result.message


def test_get_document_results_with_extracted_data(api_client, mocker):
    """Test getting results with extracted data."""
    mock_get_job_status = mocker.patch("documentai_api.app._get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf"},
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "test-job-id", "jobStatus": "success", "message": "Document processed successfully"}',
    )

    mock_build_api_response = mocker.patch(
        "documentai_api.utils.response_builder.build_v1_api_response"
    )
    mock_build_api_response.return_value = {
        "jobId": "test-job-id",
        "jobStatus": "success",
        "message": "Document processed successfully",
        "extractedData": {},
    }

    response = api_client.get("/v1/documents/test-job-id?include_extracted_data=true")

    assert response.status_code == 200
    mock_build_api_response.assert_called_once_with(
        object_key="test.pdf",
        job_status="success",
        include_extracted_data=True,
    )


def test_get_document_results_in_progress(api_client, mocker):
    """Test getting results for in-progress job."""
    mock_get_job_status = mocker.patch("documentai_api.app._get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf"},
        object_key="test.pdf",
        process_status="started",
        v1_response_json=None,
    )

    response = api_client.get("/v1/documents/test-job-id")

    assert response.status_code == 200
    data = response.json()
    assert data["jobStatus"] == "started"
    assert "in progress" in data["message"].lower()


@pytest.mark.asyncio
async def test_upload_document_for_processing_s3_failure(blank_pdf_file, s3_bucket):
    """Test S3 upload failure raises HTTPException."""
    with pytest.raises(HTTPException) as exc_info:
        await upload_document_for_processing(
            src_file=blank_pdf_file,
            dest_path=f"s3://{s3_bucket.name}-foo/input/test.pdf",
            original_file_name="test.pdf",
            content_type="application/pdf",
        )

    assert exc_info.value.status_code == 500
    assert "upload failed" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_upload_document_for_processing_invalid_category_type(
    blank_pdf_file, runtime_required_env, s3_bucket
):
    """Test invalid document category type raises ValueError."""
    with pytest.raises(HTTPException):
        await upload_document_for_processing(
            src_file=blank_pdf_file,
            dest_path=f"s3://{s3_bucket}-foo/input/test.pdf",
            original_file_name="test.pdf",
            content_type="application/pdf",
            user_provided_document_category="invalid_string",  # should be enum
        )


@pytest.mark.asyncio
async def test_get_v1_document_processing_results_polling_error(mocker):
    """Test polling continues after DDB errors."""
    mock_get_job_status = mocker.patch("documentai_api.app._get_job_status")
    # first call raises exception, second call returns success
    mock_get_job_status.side_effect = [
        Exception("DDB error"),
        JobStatus(
            ddb_record={"fileName": "test.pdf"},
            object_key="test.pdf",
            process_status="success",
            v1_response_json='{"jobId": "test-job-id", "jobStatus": "success", "message": "Document processed successfully"}',
        ),
    ]

    result = await get_v1_document_processing_results("test-job-id", timeout=10)

    assert result.job_status == "success"


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

    assert response.status_code == 200
    data = response.json()
    assert "jobId" in data
    assert data["jobStatus"] == "not_started"
    assert "uploaded successfully" in data["message"].lower()


def test_create_document_with_external_fields(api_client, blank_pdf_bytes, mocker):
    """Test document upload with external_document_id, external_system_id, and ai_consent_flag."""
    mock_insert = mocker.patch("documentai_api.app.insert_minimal_ddb_record")

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    data = {
        "external_document_id": "ext-doc-123",
        "external_system_id": "ext-sys-456",
        "ai_consent_flag": "true",
    }
    response = api_client.post("/v1/documents", files=files, data=data)

    assert response.status_code == 200
    call_kwargs = mock_insert.call_args.kwargs
    assert call_kwargs["external_document_id"] == "ext-doc-123"
    assert call_kwargs["external_system_id"] == "ext-sys-456"
    assert call_kwargs["ai_consent_flag"] is True


def test_create_document_ai_consent_declined(api_client, blank_pdf_bytes, mocker):
    """Test document upload with ai_consent_flag=false bypasses processing."""
    mock_insert = mocker.patch("documentai_api.app.insert_minimal_ddb_record")
    mock_classify = mocker.patch("documentai_api.app.classify_as_ai_consent_declined")
    mock_classify.return_value = {
        "response_code": "003",
        "response_message": "Document not processed - AI consent not provided",
    }
    mock_upload = mocker.patch("documentai_api.app.upload_document_for_processing")

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    data = {"ai_consent_flag": "false"}
    response = api_client.post("/v1/documents", files=files, data=data)

    assert response.status_code == 200
    result = response.json()
    assert result["jobStatus"] == "ai_consent_declined"
    assert "AI consent not provided" in result["message"]
    mock_insert.assert_called_once()
    mock_classify.assert_called_once()
    mock_upload.assert_not_called()


def test_create_document_synchronous(api_client, blank_pdf_bytes, mocker):
    """Test synchronous document upload (wait=true)."""
    mock_get_results = mocker.patch("documentai_api.app.get_v1_document_processing_results")
    mock_get_results.return_value = JobStatusResponse(
        job_id="test-id", job_status="success", message="Document processed successfully"
    )

    files = {"file": ("test.pdf", blank_pdf_bytes, "application/pdf")}
    response = api_client.post("/v1/documents?wait=true", files=files)

    assert response.status_code == 200
    assert response.json()["jobStatus"] == "success"


def test_get_document_results_error_handling(api_client, mocker):
    """Test error handling in get_document_results."""
    mock_get_job_status = mocker.patch("documentai_api.app._get_job_status")
    mock_get_job_status.side_effect = Exception("Unexpected error")

    response = api_client.get("/v1/documents/test-job-id")

    assert response.status_code == 500
    assert "Failed to retrieve results" in response.json()["detail"]


def test_search_documents_success(api_client, mocker):
    """Test searching multiple job IDs returns results."""
    from documentai_api.app import JobStatus

    mock_get_job_status = mocker.patch("documentai_api.app._get_job_status")
    mock_get_job_status.side_effect = [
        JobStatus(
            ddb_record={"fileName": "test.pdf"},
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
    from documentai_api.app import JobStatus

    mock_get_job_status = mocker.patch("documentai_api.app._get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf"},
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
    mock_get_job_status = mocker.patch("documentai_api.app._get_job_status")
    mock_get_job_status.side_effect = Exception("DDB error")

    response = api_client.post("/v1/documents/search", json={"jobIds": ["job-1"]})

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["jobStatus"] == "error"
    assert "Failed to retrieve" in results[0]["message"]


def test_delete_document_success(api_client, mocker):
    """Test successful document deletion."""
    from documentai_api.app import JobStatus

    mock_get_job_status = mocker.patch("documentai_api.app._get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf"},
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "job-1", "jobStatus": "success", "message": "Done"}',
    )
    mock_s3_delete = mocker.patch("documentai_api.services.s3.delete_object")
    mock_update_ddb = mocker.patch("documentai_api.utils.ddb.update_ddb")

    response = api_client.delete("/v1/documents/job-1")

    assert response.status_code == 204
    mock_s3_delete.assert_called_once()
    mock_update_ddb.assert_called_once()


def test_delete_document_not_found(api_client, mocker):
    """Test deleting non-existent document returns 404."""
    from documentai_api.app import JobStatus

    mock_get_job_status = mocker.patch("documentai_api.app._get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record=None, object_key=None, process_status=None, v1_response_json=None
    )

    response = api_client.delete("/v1/documents/fake-job")

    assert response.status_code == 404


def test_delete_document_still_processing(api_client, mocker):
    """Test deleting in-progress document returns 400."""
    from documentai_api.app import JobStatus

    mock_get_job_status = mocker.patch("documentai_api.app._get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf"},
        object_key="test.pdf",
        process_status="started",
        v1_response_json=None,
    )

    response = api_client.delete("/v1/documents/job-1")

    assert response.status_code == 400
    assert "still processing" in response.json()["detail"]


def test_delete_document_already_deleted(api_client, mocker):
    """Test deleting already-deleted document returns 404."""
    from documentai_api.app import JobStatus

    mock_get_job_status = mocker.patch("documentai_api.app._get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf"},
        object_key="test.pdf",
        process_status="deleted",
        v1_response_json=None,
    )

    response = api_client.delete("/v1/documents/job-1")

    assert response.status_code == 404


def test_get_document_results_deleted_returns_404(api_client, mocker):
    """Test GET on deleted document returns 404."""
    from documentai_api.app import JobStatus

    mock_get_job_status = mocker.patch("documentai_api.app._get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf"},
        object_key="test.pdf",
        process_status="deleted",
        v1_response_json='{"jobId": "job-1", "jobStatus": "deleted", "message": "Document has been deleted"}',
    )

    response = api_client.get("/v1/documents/job-1")

    assert response.status_code == 404
