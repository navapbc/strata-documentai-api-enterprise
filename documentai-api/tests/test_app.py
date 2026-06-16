"""Tests for app.py (public endpoints and shared utilities)."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from documentai_api import app as app_module
from documentai_api.utils.jobs import JobStatus, get_job_status, poll_for_completion
from documentai_api.utils.uploads import upload_document_for_processing


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

    # known API endpoints should be present (auto-generated from function names)
    assert "get_extraction_rules" in endpoints
    assert "list_schemas" in endpoints
    assert "create_document" in endpoints
    assert "create_document_wait" in endpoints

    # excluded routes should not appear
    excluded_paths = set(endpoints.values())
    assert "/health" not in excluded_paths
    assert "/config" not in excluded_paths


def test_root(api_client):
    response = api_client.get("/")
    assert response.status_code == 200
    assert "status" in response.json()


def test_get_job_status_found(ddb_doc_metadata_table):
    """Test get_job_status when job exists."""
    from documentai_api.config.constants import ProcessStatus
    from documentai_api.schemas.document_metadata import DocumentMetadata

    ddb_record = {
        DocumentMetadata.FILE_NAME: "test.pdf",
        DocumentMetadata.JOB_ID: "test-job-id",
        DocumentMetadata.PROCESS_STATUS: ProcessStatus.SUCCESS.value,
        DocumentMetadata.V1_API_RESPONSE_JSON: '{"jobStatus": "success"}',
    }

    ddb_doc_metadata_table.put_item(Item=ddb_record)

    result = get_job_status("test-job-id")

    assert result.object_key == "test.pdf"
    assert result.process_status == "success"
    assert result.v1_response_json == '{"jobStatus": "success"}'


def test_get_job_status_not_found(ddb_doc_metadata_table):
    """Test get_job_status when job doesn't exist."""
    result = get_job_status("test-job-id")

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
async def test_upload_always_saves_original_to_preprocessing(
    runtime_required_env, blank_pdf_file, s3_bucket, monkeypatch
):
    """Every upload writes the original to preprocessing, regardless of file type."""
    from documentai_api.config.constants import DocumentCategory
    from documentai_api.config.env import EnvVars

    monkeypatch.setenv(
        EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION, f"s3://{s3_bucket.name}/preprocessing"
    )

    await upload_document_for_processing(
        src_file=blank_pdf_file.open("rb"),
        dest_path=f"s3://{s3_bucket.name}/input/test-unique.pdf",
        original_file_name="test.pdf",
        content_type="application/pdf",
        user_provided_document_category=DocumentCategory.INCOME,
        job_id="test-job-id",
        trace_id="test-trace-id",
    )

    # Original saved to preprocessing
    preprocessing_obj = s3_bucket.Object("preprocessing/test-unique.pdf")
    assert preprocessing_obj.get()["Body"].read() == blank_pdf_file.read_bytes()

    # And also uploaded to input
    input_obj = s3_bucket.Object("input/test-unique.pdf")
    assert input_obj.content_type == "application/pdf"


@pytest.mark.asyncio
async def test_poll_for_completion_success(mocker):
    """Test polling returns results when processing completes."""
    mock_get_job_status = mocker.patch("documentai_api.utils.jobs.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf"},
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "test-job-id", "jobStatus": "success", "message": "Document processed successfully"}',
    )

    result = await poll_for_completion("test-job-id", timeout=10)

    assert result.job_status == "success"


@pytest.mark.asyncio
async def test_poll_for_completion_timeout(mocker):
    """Test polling timeout with object_key."""
    mock_get_job_status = mocker.patch("documentai_api.utils.jobs.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record={"fileName": "test.pdf"},
        object_key="test.pdf",
        process_status="started",
        v1_response_json=None,
    )

    mock_classify_as_failed = mocker.patch("documentai_api.utils.jobs.classify_as_failed")

    result = await poll_for_completion("test-job-id", timeout=1)

    mock_classify_as_failed.assert_called_once()
    assert result.job_status == "failed"
    assert "timeout" in result.message.lower()


@pytest.mark.asyncio
async def test_poll_for_completion_timeout_no_object_key(mocker):
    """Test polling timeout without object_key."""
    mock_get_job_status = mocker.patch("documentai_api.utils.jobs.get_job_status")
    mock_get_job_status.return_value = JobStatus(
        ddb_record=None,
        object_key=None,
        process_status=None,
        v1_response_json=None,
    )

    result = await poll_for_completion("test-job-id", timeout=1)

    assert result.job_status == "failed"
    assert "timeout" in result.message


@pytest.mark.asyncio
async def test_upload_document_for_processing_s3_failure(
    blank_pdf_file, runtime_required_env, s3_bucket
):
    """Test S3 (destination) upload failure raises HTTPException.

    The preprocessing backup is configured and succeeds; the destination bucket
    does not exist, so the dest upload is what fails.
    """
    with pytest.raises(HTTPException) as exc_info:
        await upload_document_for_processing(
            src_file=blank_pdf_file.open("rb"),
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
            src_file=blank_pdf_file.open("rb"),
            dest_path=f"s3://{s3_bucket}-foo/input/test.pdf",
            original_file_name="test.pdf",
            content_type="application/pdf",
            user_provided_document_category="invalid_string",  # should be enum
        )


@pytest.mark.asyncio
async def test_poll_for_completion_polling_error(mocker):
    """Test polling continues after DDB errors."""
    mock_get_job_status = mocker.patch("documentai_api.utils.jobs.get_job_status")
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

    result = await poll_for_completion("test-job-id", timeout=10)

    assert result.job_status == "success"


def test_config_api_url_from_env(api_client):
    """api_url in /config comes from API_BASE_URL env, not request host."""
    response = api_client.get("/config")
    data = response.json()
    assert "apiUrl" in data
    assert data["apiUrl"] == "http://localhost:8000"


def test_cors_preflight(api_client):
    """OPTIONS preflight returns correct CORS headers."""
    response = api_client.options(
        "/v1/config/extraction-rules",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "Content-Type, x-api-key, X-Trace-ID",
        },
    )

    assert response.status_code == 200
    assert "PUT" in response.headers["access-control-allow-methods"]
    assert "x-api-key" in response.headers["access-control-allow-headers"]
    assert "X-Trace-ID" in response.headers["access-control-allow-headers"]
    # Credentials should NOT be allowed (was the bug we fixed)
    assert response.headers.get("access-control-allow-credentials", "false") != "true"


def test_cors_expose_headers(api_client):
    """Actual responses expose X-Trace-ID for browser JS to read."""
    response = api_client.get("/health", headers={"Origin": "https://example.com"})

    assert response.status_code == 200
    assert "X-Trace-ID" in response.headers.get("access-control-expose-headers", "")


##############################################################################
# _require_auth_in_hosted_envs (insecure-by-default startup guard)
##############################################################################


def _patch_auth_config(*, enabled: bool, hosted: bool):
    """Patch get_app_env_config with a fake whose hosted-ness is controllable.

    The env-name / Lambda detection itself is covered by AppEnvConfig.is_hosted_env
    tests; here we only exercise the guard's branching.
    """
    cfg = SimpleNamespace(
        api_auth_enabled=enabled,
        environment="prod" if hosted else "local",
        is_hosted_env=lambda: hosted,
    )
    return patch.object(app_module, "get_app_env_config", return_value=cfg)


def test_require_auth_allows_non_hosted_without_auth():
    with _patch_auth_config(enabled=False, hosted=False):
        app_module._require_auth_in_hosted_envs()  # should not raise


def test_require_auth_rejects_hosted_without_auth():
    with (
        _patch_auth_config(enabled=False, hosted=True),
        pytest.raises(RuntimeError, match="API_AUTH_ENABLED is false"),
    ):
        app_module._require_auth_in_hosted_envs()


def test_require_auth_allows_hosted_when_auth_enabled():
    with _patch_auth_config(enabled=True, hosted=True):
        app_module._require_auth_in_hosted_envs()  # should not raise
